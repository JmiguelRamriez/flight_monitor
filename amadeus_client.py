import requests
import logging
import time
import random
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class AmadeusClient:
    """
    Cliente para interactuar con la API de Amadeus (Self-Service).
    Reemplaza a TequilaClient manteniendo compatibilidad de datos.
    """
    
    BASE_URL = "https://test.api.amadeus.com" # Cambiar a production si es necesario
    # Nota: El usuario no especificó ambiente, usaremos 'test' por defecto para devs, 
    # pero normalmente se usa production.api.amadeus.com para data real.
    # Dado que es "Flight Deal Monitoring" con "Production-ready code", 
    # asumiremos el endpoint de producción O lo haremos configurable.
    # Amadeus Self-Service Test environment tiene data limitada.
    # Usaré el host de producción si es posible, pero requiere credenciales de prod.
    # Dejaré el base url como variable de clase fácil de cambiar.
    HOST = "https://test.api.amadeus.com" 

    def __init__(self, client_id: str, client_secret: str, config: Dict[str, Any]):
        self.client_id = client_id
        self.client_secret = client_secret
        self.config = config
        self.token = None
        self.token_expiry = 0
        self.session = requests.Session()

    def _get_token(self):
        """
        Obtiene o renueva el Access Token de OAuth 2.0.
        """
        if self.token and time.time() < self.token_expiry:
            return self.token

        url = f"{self.HOST}/v1/security/oauth2/token"
        try:
            response = requests.post(url, data={
                'grant_type': 'client_credentials',
                'client_id': self.client_id,
                'client_secret': self.client_secret
            })
            response.raise_for_status()
            data = response.json()
            self.token = data['access_token']
            # Renovar 10s antes de que expire por seguridad
            self.token_expiry = time.time() + data['expires_in'] - 10
            logger.info("Token de Amadeus obtenido exitosamente.")
            return self.token
        except requests.RequestException as e:
            logger.error(f"Error autenticando con Amadeus: {e}")
            raise

    def get_headers(self):
        return {
            "Authorization": f"Bearer {self._get_token()}"
        }

    def get_top_airports(self, country_code: str, limit: int) -> List[Dict]:
        """
        Obtiene aeropuertos principales de un país usando Reference Data API.
        """
        if self.config["system"].get("use_mock_api", False):
            logger.info("Retornando aeropuertos MOCK...")
            # Retornar aeropuertos comunes según el país (ejemplo hardcodeado para demo)
            if country_code == "JP": return ["NRT", "HND", "KIX", "ITM"][:limit]
            if country_code == "FR": return ["CDG", "ORY", "NCE"][:limit]
            if country_code == "US": return ["JFK", "LAX", "ORD", "MIA"][:limit]
            return ["MOCK1", "MOCK2"][:limit]
        endpoint = f"{self.HOST}/v1/reference-data/locations"
        # Amadeus requiere keyword. Buscar 'airports in country' no es directo en location/query,
        # pero podemos usar type=AIRPORT y keyword=country_code, aunque a veces es impreciso.
        # Mejor opción: parameters: countryCode={country_code} & subType=AIRPORT
        
        params = {
            "keyword": country_code,
            "subType": "AIRPORT",
            "view": "LIGHT",
            "page[limit]": limit
        }
        
        try:
            response = self.session.get(endpoint, headers=self.get_headers(), params=params)
            # Retry logic for sort removed as we removed sort param due to permissions
                
            response.raise_for_status()
            data = response.json().get('data', [])
            
            airports = [loc['iataCode'] for loc in data if 'iataCode' in loc]
            
            # Fallback: Si no devuelve nada y el input parece un código IATA (3 letras), lo usamos directo.
            if not airports and len(country_code) == 3:
                logger.info(f"Usando '{country_code}' directamente como destino.")
                return [country_code]
                
            logger.info(f"Aeropuertos encontrados para {country_code}: {airports}")
            return airports[:limit]

        except requests.RequestException as e:
            logger.error(f"Error obteniendo aeropuertos Amadeus: {e}")
            # Fallback en excepción también
            if len(country_code) == 3:
                return [country_code]
            return []

    def _generate_mock_deals(self, origin: str, dest_airports: List[str]) -> List[Dict[str, Any]]:
        """Genera ofertas falsas para pruebas sin API key."""
        logger.info("Generando ofertas MOCK...")
        deals = []
        today = datetime.now()
        config_budget = self.config["budget"]
        
        # Oferta Garantizada "Barata" para probar notificaciones
        cheap_deal = {
            "price": 5000.0,
            "cityCodeFrom": origin,
            "cityCodeTo": dest_airports[0] if dest_airports else "MOCK",
            "dTime": int((today + timedelta(days=45)).timestamp()),
            "aTime": int((today + timedelta(days=55)).timestamp()),
            "route": ["DIRECT_FLIGHT"],
            "airlines": ["MOCK_AIR"],
            "deep_link": "https://mock-airline.com/deal",
            "source": "mock"
        }
        deals.append(cheap_deal)

        for _ in range(4): # Generar 4 ofertas random extra
            dest = random.choice(dest_airports)
            price = random.randint(15000, 30000) # Rango de precios variado
            
            # Fecha random futura
            days_out = random.randint(30, 90)
            dep_date = today + timedelta(days=days_out)
            ret_date = dep_date + timedelta(days=14)
            
            deal = {
                "price": float(price),
                "cityCodeFrom": origin,
                "cityCodeTo": dest,
                "dTime": int(dep_date.timestamp()),
                "aTime": int(ret_date.timestamp()),
                "route": ["MOCK_SEGMENT_1", "MOCK_SEGMENT_2"],
                "airlines": ["AA", "JL"],
                "deep_link": "https://example.com",
                "source": "mock"
            }
            deals.append(deal)
        return deals

    def search_flights(self, origin: str, dest_airports: List[str]) -> List[Dict[str, Any]]:
        """
        Busca vuelos simulando la lógica anterior.
        Dado que Amadeus no permite rangos de fechas amplios, iteramos por días seleccionados.
        """
        # Chequear modo Mock
        if self.config["system"].get("use_mock_api", False):
            return self._generate_mock_deals(origin, dest_airports)

        deals = []
        endpoint = f"{self.HOST}/v2/shopping/flight-offers"
        
        config_sys = self.config["system"]
        config_dates = self.config["dates"]
        config_budget = self.config["budget"]
        config_filters = self.config["filters"]

        # Generar set de fechas a probar
        # Estrategia: Probar fechas random dentro de la ventana o secuencial.
        # Para simplificar y dar variedad, probaremos N fechas de salida aleatorias en la ventana.
        
        start_delta = config_dates["travel_window_start"]
        end_delta = config_dates["travel_window_end"]
        window_days = end_delta - start_delta
        
        today = datetime.now()
        
        # Generamos (max_queries_per_run) fechas de prueba
        max_queries = config_sys["max_queries_per_run"]
        if window_days <= 0:
            logger.warning("Ventana de viaje inválida.")
            return []

        # Intentamos distribuir las queries entre los destinos
        # Si hay 3 destinos y 20 queries -> ~6 queries por destino.
        queries_per_dest = max(1, max_queries // len(dest_airports))
        total_queries = queries_per_dest * len(dest_airports)
        current_query = 0
        
        for dest in dest_airports:
            for _ in range(queries_per_dest):
                current_query += 1
                progress_pct = (current_query / total_queries) * 100
                logger.info(f"[PROGRESS] {progress_pct:.0f}%")

                # Elegir día random de salida
                rand_day = random.randint(start_delta, end_delta)
                depart_date = today + timedelta(days=rand_day)
                depart_str = depart_date.strftime("%Y-%m-%d")
                
                # Elegir duración random (o fixed si min=max)
                min_nights = config_dates["min_nights"]
                max_nights = config_dates["max_nights"]
                duration = random.randint(min_nights, max_nights)
                return_date = depart_date + timedelta(days=duration)
                return_str = return_date.strftime("%Y-%m-%d")
                
                # Comprobar aerolíneas
                included_airlines = config_filters["airlines"].get("allowed", [])
                excluded_airlines = config_filters["airlines"].get("blocked", [])
                
                params = {
                    "originLocationCode": origin,
                    "destinationLocationCode": dest,
                    "departureDate": depart_str,
                    "returnDate": return_str,
                    "adults": 1,
                    "max": 5, # Pocos resultados por fecha específica
                    "currencyCode": config_budget["currency"]
                }
                
                if included_airlines:
                    params["includedAirlineCodes"] = ",".join(included_airlines)
                if excluded_airlines:
                    params["excludedAirlineCodes"] = ",".join(excluded_airlines)
 
                # rate limit basic handling
                time.sleep(config_sys["sleep_seconds_between_requests"])
                
                try:
                    logger.info(f"Amadeus: Buscando {origin}->{dest} ({depart_str} a {return_str})")
                    response = self.session.get(endpoint, headers=self.get_headers(), params=params)
                    
                    if response.status_code == 429:
                        logger.warning("Amadeus Rate Limit (429). Pausando...")
                        time.sleep(5)
                        continue
                        
                    response.raise_for_status()
                    data = response.json().get('data', [])

                    # Normalizar resultados
                    normalized = self._normalize_results(data)
                    deals.extend(normalized)
                    
                except requests.RequestException as e:
                    logger.error(f"Fallo búsqueda Amadeus ({dest}, {depart_str}): {e}")

        logger.info(f"Búsqueda finalizada. Total ofertas encontradas: {len(deals)}")
        return deals

    def _normalize_results(self, amadeus_data: List[Dict]) -> List[Dict]:
        """
        Convierte la respuesta de Amadeus al formato dict plano esperado por scoring.py
        """
        normalized_deals = []
        for offer in amadeus_data:
            try:
                # 1. Precio
                price = float(offer['price']['total'])
                
                # 2. Itinerarios
                itineraries = offer['itineraries']
                if not itineraries:
                    continue
                
                # Ida
                outbound = itineraries[0]['segments']
                # Vuelta (si existe)
                inbound = itineraries[1]['segments'] if len(itineraries) > 1 else []
                
                first_seg = outbound[0]
                last_seg = outbound[-1]
                
                # Timestamp salida
                dep_at = first_seg['departure']['at'] # "2024-12-01T10:00:00"
                dt_obj = datetime.strptime(dep_at, "%Y-%m-%dT%H:%M:%S")
                d_time_ts = dt_obj.timestamp()
                
                # Timestamp llegada (vuelta) - approx usando primer seg de vuelta o último de ida
                # scoring.py no usa aTime críticamente más que para logs/info
                if inbound:
                    ret_at = inbound[0]['departure']['at']
                    rt_obj = datetime.strptime(ret_at, "%Y-%m-%dT%H:%M:%S")
                    a_time_ts = rt_obj.timestamp()
                else:
                    a_time_ts = 0

                # 3. Datos Ruta
                origin_code = first_seg['departure']['iataCode']
                dest_code = last_seg['arrival']['iataCode']
                
                # 4. Aerolíneas
                # validatingAirlineCodes suele ser lista de strings ['AA', 'UA']
                val_airlines = offer.get('validatingAirlineCodes', [])
                if val_airlines:
                     airlines = list(set(val_airlines))
                else:
                    # Fallback a segmentos
                    airlines = list(set([s['carrierCode'] for s in outbound]))

                # 5. Route (lista de paradas/segmentos) para display
                # El formato anterior usaba una lista de dicts. 
                # Simplificaremos a lista de strings para log o lista de objects si scoring lo requiere.
                # scoring.py usa len(deal.get("route", [])) para contar segmentos.
                # Combinamos segmentos de ida y vuelta
                all_segments = outbound + inbound
                
                # Generar link de Google Flights (Query más explícita)
                dep_date_str = dt_obj.strftime("%Y-%m-%d")
                
                # Google Flights: "Flights from ORIGIN to DEST on DATE returning DATE"
                gf_query = f"Flights from {origin_code} to {dest_code} on {dep_date_str}"
                
                # Skyscanner: https://www.skyscanner.com/transport/flights/mex/gye/240501/240510
                # Skyscanner format uses YYMMDD
                sky_dep = dt_obj.strftime("%y%m%d")
                sky_ret = ""
                
                if inbound:
                    rt_obj = datetime.strptime(inbound[0]['departure']['at'], "%Y-%m-%dT%H:%M:%S")
                    ret_str = rt_obj.strftime("%Y-%m-%d")
                    gf_query += f" returning {ret_str}"
                    
                    sky_ret = rt_obj.strftime("%y%m%d")
                
                # Construir URLs
                gf_link = f"https://www.google.com/travel/flights?q={gf_query.replace(' ', '+')}"
                sky_link = f"https://www.skyscanner.com.mx/transport/vuelos/{origin_code.lower()}/{dest_code.lower()}/{sky_dep}/{sky_ret}"

                deal_dict = {
                    "price": price,
                    "cityCodeFrom": origin_code,
                    "cityCodeTo": dest_code,
                    "dTime": int(d_time_ts),
                    "aTime": int(a_time_ts),
                    "route": all_segments, 
                    "airlines": airlines,
                    "deep_link": gf_link,
                    "backup_link": sky_link,
                    "source": "amadeus"
                }
                
                normalized_deals.append(deal_dict)

            except (KeyError, ValueError, IndexError) as e:
                logger.warning(f"Error parseando oferta Amadeus: {e}")
                continue
                
        return normalized_deals
