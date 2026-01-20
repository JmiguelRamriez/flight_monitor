import logging
import hashlib
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class EvaluationResult:
    is_deal: bool
    confidence: str # "HIGH", "LOW", "COLD_START"
    baseline: float
    score_details: str # Razón o detalles
    deal_hash: str

class DealScorer:
    """
    Evalúa si un vuelo es una oferta válida basada en el historial de precios (baseline).
    Implementa la lógica crítica de 'Cold Start' y rangos de descuento.
    """

    def __init__(self, config: Dict[str, Any], store):
        self.config = config
        self.store = store
        self.scoring_cfg = config["scoring"]
        self.budget_max = config["budget"]["max_price"]

    def _generate_hash(self, deal: Dict[str, Any]) -> str:
        """
        Genera un hash determinístico para deduplicación.
        Campos: route, dates, airlines, stopovers, link (o subset).
        """
        # Extraer datos clave
        city_from = deal.get("cityCodeFrom", "")
        city_to = deal.get("cityCodeTo", "")
        route_str = f"{city_from}-{city_to}"
        
        # Fechas (Unix timestamps o strings ISO)
        d_time = deal.get("dTime", 0)
        a_time = deal.get("aTime", 0) # Regreso (depende estructura exacta API, a veces es 'route')
        # Para round trip en Tequila 'data' root tiene dTime (ida). La vuelta está en 'route'.
        # Simplificación: Usaremos dTime de ida y dTime de vuelta si disponible, o deep_link.
        # El deep_link suele ser único por itinerario.
        link = deal.get("deep_link", "")
        price = deal.get("price", 0)
        airlines = ",".join(deal.get("airlines", []))
        
        # String base
        # Nota: Usamos el link como proxy fuerte de unicidad de itinerario, 
        # pero agregamos precio y fechas para robustez si el link cambia parámetros de sesión.
        # User req: hash of route + dates + airlines + stopovers + link
        raw_str = f"{route_str}|{d_time}|{airlines}|{link}"
        
        return hashlib.md5(raw_str.encode("utf-8")).hexdigest()

    def evaluate_deal(self, deal: Dict[str, Any]) -> EvaluationResult:
        """
        Aplica las reglas de negocio para determinar si es un deal.
        """
        price = deal.get("price", float('inf'))
        city_from = deal.get("cityCodeFrom", "")
        city_to = deal.get("cityCodeTo", "")
        route = f"{city_from}-{city_to}"
        
        # Fecha de viaje para buscar baseline (mes)
        d_time_ts = deal.get("dTime")
        travel_date = datetime.fromtimestamp(d_time_ts)
        
        # Hash para dedupe
        deal_hash = self._generate_hash(deal)

        # 0. Check Presupuesto Absoluto (Seguridad)
        if price > self.budget_max:
            return EvaluationResult(False, "NONE", 0.0, "Precio excede presupuesto máximo", deal_hash)

        # 1. Obtener Baseline
        baseline_days = self.scoring_cfg["baseline_days"]
        min_samples = self.scoring_cfg["min_samples"]
        
        baseline, count = self.store.get_baseline_stats(route, travel_date, baseline_days)
        
        # 2. Cold Start Logic
        if count < min_samples:
            # Caso Cold Start
            if baseline is None:
                # Caso extremo: No hay NINGÚN dato previo
                # Guardamos la muestra (se hace fuera normalmente, pero aquí evaluamos)
                # Req 8.4: Si no se puede computar baseline (null), NO notificar.
                return EvaluationResult(False, "NONE", 0.0, "Sin datos históricos suficientes (Cold Start absoluto)", deal_hash)
            
            # Si hay al menos 1 muestra (baseline no es None), aplicamos Cold Start Mandatory Fallback
            # "Apply the discount rule using the computed baseline only if mathematically valid."
            
            # Calcular límites
            discount_min = self.scoring_cfg["discount_min"]
            discount_max = self.scoring_cfg["discount_max"]
            
            # Lógica Normal pero con Flag "Low Confidence"
            lower_bound = baseline * (1 - discount_max)
            upper_bound = baseline * (1 - discount_min)
            
            if lower_bound <= price <= upper_bound:
                return EvaluationResult(True, "COLD_START", baseline, f"Deal en Cold Start (Muestras: {count})", deal_hash)
            else:
                return EvaluationResult(False, "COLD_START", baseline, "Precio fuera de rango relativo (Cold Start)", deal_hash)

        # 3. Standard Logic
        discount_min = self.scoring_cfg["discount_min"]
        discount_max = self.scoring_cfg["discount_max"]
        
        lower_bound = baseline * (1 - discount_max)
        upper_bound = baseline * (1 - discount_min)
        
        if lower_bound <= price <= upper_bound:
            return EvaluationResult(True, "HIGH", baseline, "Deal válido detectado", deal_hash)
        
        return EvaluationResult(False, "HIGH", baseline, "Precio fuera de rango relativo", deal_hash)
