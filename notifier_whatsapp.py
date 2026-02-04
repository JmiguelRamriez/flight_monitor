import requests
import logging
import os
from typing import Dict, Any

logger = logging.getLogger(__name__)

class WhatsAppNotifier:
    """
    Envía notificaciones vía WhatsApp usando la API de Twilio (vía HTTP requests).
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        self.from_number = os.getenv("TWILIO_FROM_NUMBER")
        
        # Enforce 'whatsapp:' prefix for correctness
        if self.from_number and not self.from_number.startswith("whatsapp:"):
            self.from_number = f"whatsapp:{self.from_number}"
            
        raw_to = config["system"]["recipient_phone"]
        if raw_to and not str(raw_to).startswith("whatsapp:"):
            self.to_number = f"whatsapp:{raw_to}"
        else:
            self.to_number = raw_to
        
        self.is_mock = config["system"].get("use_mock_api", False)
        
        if not self.is_mock and not all([self.account_sid, self.auth_token, self.from_number]):
            logger.warning("Credenciales de Twilio no configuradas completamente en .env")

    def send_deal_alert(self, deal: Dict[str, Any], evaluation: Any):
        """
        Formatea y envía el mensaje de alerta.
        """
        if not self.is_mock and (not self.account_sid or not self.auth_token):
            logger.error("No se puede enviar alerta: Faltan credenciales Twilio.")
            return

        # Calcular porcentaje de descuento
        baseline = evaluation.baseline
        price = deal.get("price", 0)
        percentage_off = 0.0
        if baseline and baseline > 0:
            percentage_off = ((baseline - price) / baseline) * 100

        # Formatear fechas
        d_time_ts = deal.get("dTime")
        date_str = datetime.fromtimestamp(d_time_ts).strftime('%d/%m/%Y') if d_time_ts else "N/A"
        
        segments_count = len(deal.get("route", []))
        
        # Airlines
        airlines = ", ".join(deal.get("airlines", []))
        
        # Flag de confianza
        confidence_marker = ""
        if evaluation.confidence == "COLD_START":
            confidence_marker = "⚠️ LOW CONFIDENCE / CREATING BASELINE"

        # Construir mensaje
        msg_body = (
            f"✈️ *NUEVA OFERTA DE VUELO*\n"
            f"{confidence_marker}\n\n"
            f" Ruta: {deal.get('cityCodeFrom')} -> {deal.get('cityCodeTo')}\n"
            f" Fecha: {date_str}\n"
            f" Precio: ${price} {self.config.get('budget', {}).get('currency')}\n"
            f" Ahorro: {percentage_off:.1f}% vs Baseline (${baseline:.0f})\n"
            f" Segmentos: {segments_count}\n"
            f" Aerolíneas: {airlines}\n\n"
            f" Ver Oferta: {deal.get('deep_link')}"
        )
        
        if self.is_mock:
            logger.info(" [MOCK] Simulando envío de WhatsApp:")
            logger.info(f"\n{msg_body}\n")
            return

        self._send_twilio_request(msg_body, deal.get('cityCodeTo'))

    def send_summary(self, stats: Dict[str, Any]):
        """
        Envía un resumen de ejecución cuando no hubo ofertas.
        """
        if not self.is_mock and (not self.account_sid or not self.auth_token):
            return

        best_deal = stats.get("best_deal")
        routes_count = stats.get("routes_checked", 0)
        
        msg_body = (
            f"✅ *Resumen de Búsqueda*\n"
            f"Rutas Revisadas: {routes_count}\n"
            f"Ofertas Encontradas: 0\n\n"
        )
        
        if best_deal:
            d_time_ts = best_deal.get("dTime")
            date_str = datetime.fromtimestamp(d_time_ts).strftime('%d/%m/%Y') if d_time_ts else "N/A"
            price = best_deal.get("price")
            currency = self.config.get('budget', {}).get('currency')
            
            msg_body += (
                f"📉 *Mejor Alternativa:*\n"
                f"📍 {best_deal.get('cityCodeTo')} el {date_str}\n"
                f"💰 ${price} {currency}\n"
                f"🔗 {best_deal.get('deep_link', '')}\n"
            )
        else:
            msg_body += "No se encontró ninguna alternativa válida."

        self._send_twilio_request(msg_body, "Resumen")

    def _send_twilio_request(self, body_text: str, context_tag: str):
        """
        Helper para enviar la petición a Twilio, soportando Templates si están configurados.
        """
        if self.is_mock:
            logger.info(f" [MOCK] Simulando envío de WhatsApp ({context_tag}):\n{body_text}\n")
            return

        url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json"
        
        # Check for Template SID
        content_sid = self.config.get("system", {}).get("twilio_content_sid")

        data = {
            "From": self.from_number,
            "To": self.to_number
        }

        if content_sid:
            # Usando Templates (Content API)
            # Mapeamos todo el cuerpo del mensaje a la variable '1'
            import json
            data["ContentSid"] = content_sid
            # Nota: Asumimos que la plantilla espera {"1": "texto", "2": "extra"}
            # Pondremos el texto principal en "1" y una etiqueta en "2"
            data["ContentVariables"] = json.dumps({"1": body_text, "2": context_tag}) 
        else:
            # Mensaje estándar
            data["Body"] = body_text

        try:
            response = requests.post(url, data=data, auth=(self.account_sid, self.auth_token))
            response.raise_for_status()
            logger.info(f"Notificación enviada ({context_tag}). SID: {response.json().get('sid')}")
        except Exception as e:
            logger.error(f"Error enviando WhatsApp ({context_tag}): {e}")
            if 'response' in locals() and response is not None:
                logger.error(f"Twilio respuesta: {response.text}")

from datetime import datetime
