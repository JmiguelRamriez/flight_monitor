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
        self.to_number = config["system"]["recipient_phone"]
        
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
            f"📍 Ruta: {deal.get('cityCodeFrom')} ➡️ {deal.get('cityCodeTo')}\n"
            f"📅 Fecha: {date_str}\n"
            f"💰 Precio: ${price} {self.config.get('budget', {}).get('currency')}\n"
            f"📉 Ahorro: {percentage_off:.1f}% vs Baseline (${baseline:.0f})\n"
            f"🛑 Segmentos: {segments_count}\n"
            f"✈️ Aerolíneas: {airlines}\n\n"
            f"🔗 Ver Oferta: {deal.get('deep_link')}"
        )
        
        if self.is_mock:
            logger.info(" [MOCK] Simulando envío de WhatsApp:")
            logger.info(f"\n{msg_body}\n")
            return

        url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json"
        data = {
            "From": self.from_number,
            "To": self.to_number,
            "Body": msg_body
        }

        try:
            response = requests.post(url, data=data, auth=(self.account_sid, self.auth_token))
            response.raise_for_status()
            logger.info(f"Notificación enviada para {deal.get('cityCodeTo')} - SID: {response.json().get('sid')}")
        except requests.RequestException as e:
            logger.error(f"Error enviando WhatsApp: {e}")
            if response is not None:
                logger.error(f"Twilio respuesta: {response.text}")

from datetime import datetime
