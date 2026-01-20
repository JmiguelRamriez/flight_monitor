import yaml
import os
import logging
import time
from datetime import datetime
from collections import defaultdict
from dotenv import load_dotenv

from store import DealStore
from amadeus_client import AmadeusClient
from scoring import DealScorer
from notifier_whatsapp import WhatsAppNotifier

# Configuración básica de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("flight_monitor.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("Main")

def load_config(path: str = "config.yaml"):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config file not found at {path}")
    with open(path, 'r') as f:
        return yaml.safe_load(f)

def run():
    # 1. Cargar Entorno y Config
    load_dotenv()
    config = load_config()
    
    # 2. Inicializar Componentes
    store = DealStore()
    
    amadeus_id = os.getenv("AMADEUS_CLIENT_ID")
    amadeus_secret = os.getenv("AMADEUS_CLIENT_SECRET")
    
    if not config["system"].get("use_mock_api", False):
        if not amadeus_id or not amadeus_secret:
            logger.error("Faltan credenciales AMADEUS en .env")
            return
    else:
        if not amadeus_id:
            logger.warning("Modo MOCK habilitado: Ejecutando sin credenciales reales.")

    client = AmadeusClient(amadeus_id, amadeus_secret, config)

    scorer = DealScorer(config, store)
    notifier = WhatsAppNotifier(config)

    # 3. Datos de Viaje
    origin_country = config["travel"]["origin_country"]
    dest_country = config["travel"]["destination_country"]
    airports_limit = config["travel"]["destination_airports_limit"]

    logger.info(" Iniciando ejecución del Monitor de Vuelos...")

    # 4. Resolver Aeropuertos
    # Resolver ambos para tener códigos concretos si es necesario, 
    # pero el user code usa Country code origin directo normalmente.
    # Solo resolvemos destino según reglas.
    dest_airports = client.get_top_airports(dest_country, airports_limit)
    if not dest_airports:
        logger.error("No se pudieron resolver aeropuertos destino. Abortando.")
        return

    # 5. Buscar Vuelos
    # Tequila Client maneja la iteración o batch query
    deals = client.search_flights(origin_country, dest_airports)
    
    if not deals:
        logger.info("No se encontraron vuelos en esta búsqueda.")
        return

    # 6. Procesar Resultados para Historial (Sampling)
    # Agrupamos por Ruta + Mes para sacar el precio representativo (mínimo) de hoy
    # Esto evita guardar 50 precios duplicados de la misma búsqueda.
    min_prices_map = defaultdict(float) # Key: (route, month) -> min_price
    
    for deal in deals:
        price = deal.get("price")
        city_from = deal.get("cityCodeFrom")
        city_to = deal.get("cityCodeTo")
        route = f"{city_from}-{city_to}"
        
        d_time = deal.get("dTime")
        if not d_time or not price:
            continue
            
        date_obj = datetime.fromtimestamp(d_time)
        month_key = date_obj.strftime("%Y-%m")
        
        key = (route, month_key)
        if key not in min_prices_map or price < min_prices_map[key]:
            min_prices_map[key] = price

    # Guardar muestras en DB
    logger.info(f"Guardando {len(min_prices_map)} muestras de precio base (mínimos).")
    for (route, month_key), price in min_prices_map.items():
        # Reconstruimos una fecha aproximada (primer día del mes) para la API del store
        # aunque store toma la fecha real, internally format to month.
        # Usamos la fecha actual para 'add_price_sample' timestamp si queremos,
        # pero store.add_price_sample pide 'travel_date'.
        # Parseamos month_key
        dt = datetime.strptime(month_key, "%Y-%m")
        store.add_price_sample(route, dt, price, config["budget"]["currency"])

    # 7. Evaluar Ofertas Individuales (Scoring & Notificación)
    logger.info("Evaluando ofertas...")
    notifications_sent = 0
    
    # Tracking de la mejor alternativa global (Lowest Price Found)
    best_alternative = None
    
    # Ordenamos deals por precio para evaluar los mejores primero
    deals.sort(key=lambda x: x.get("price", float('inf')))

    for deal in deals:
        # Track global best
        if best_alternative is None or deal["price"] < best_alternative["price"]:
            best_alternative = deal
            
        result = scorer.evaluate_deal(deal)
        
        if result.is_deal:
            # Chequear deduplicación
            last_notif = store.get_last_notification(result.deal_hash)
            should_notify = True
            
            if last_notif:
                last_price = last_notif["last_price"]
                current_price = deal["price"]
                drop_pct = config["scoring"]["dedupe_drop_pct"]
                
                # Solo notificar de nuevo si el precio bajó X% extra
                # Logic: last_price * (1 - drop) >= current_price
                if current_price > last_price * (1 - drop_pct):
                    should_notify = False
                    logger.info(f"Deal {result.deal_hash} ignorado (Ya notificado y no bajó suficiente).")

            if should_notify:
                logger.info(f"!!! DEAL ENCONTRADO !!! {deal['cityCodeTo']} por {deal['price']} (Conf: {result.confidence})")
                logger.info(f"Link: {deal.get('deep_link', 'N/A')}")
                notifier.send_deal_alert(deal, result)
                store.record_notification(result.deal_hash, deal["price"])
                notifications_sent += 1
        else:
            # Logging verbose o para debug
            pass

    # Siempre mostrar la mejor alternativa en consola si existe
    if best_alternative:
        logger.info(f"🔎 Mejor opción encontrada: {best_alternative.get('cityCodeTo')} - ${best_alternative.get('price')}")
        logger.info(f"🔗 Google Flights: {best_alternative.get('deep_link', 'N/A')}")
        logger.info(f"✈️ Skyscanner:    {best_alternative.get('backup_link', 'N/A')}")

    # 8. Reporte de Ejecución (Si no hubo ofertas)
    if notifications_sent == 0 and config["system"].get("send_summary_if_no_deals", True):
        logger.info("No se encontraron ofertas. Enviando resumen de ejecución...")
        stats = {
            "routes_checked": len(min_prices_map), # Approx routes checked
            "best_deal": best_alternative
        }  
        notifier.send_summary(stats)

    logger.info(f"Ejecución finalizada. Notificaciones enviadas: {notifications_sent}")

if __name__ == "__main__":
    try:
        run()
    except Exception as e:
        logger.exception("Error crítico en la ejecución del script.")
        exit(1)
