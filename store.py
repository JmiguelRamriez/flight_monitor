import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Tuple, Dict, Optional

# Configuración de logging
logger = logging.getLogger(__name__)

class DealStore:
    """
    Maneja la persistencia de datos en SQLite.
    Responsable de guardar historial de precios y rastrear notificaciones previas.
    """

    def __init__(self, db_path: str = "deals.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """
        Inicializa el esquema de la base de datos si no existe.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Tabla de historial de precios para calcular baselines
        # Route es: ORG-DST (ej. SLP-NRT)
        # Month es: YYYY-MM del viaje de ida
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                route TEXT NOT NULL,
                travel_month TEXT NOT NULL,
                price REAL NOT NULL,
                currency TEXT NOT NULL,
                recorded_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Tabla para deduplicación de notificaciones
        # Deal hash debe ser único para un conjunto de vuelo específico
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notifications (
                deal_hash TEXT PRIMARY KEY,
                last_price REAL NOT NULL,
                last_notified_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        conn.commit()
        conn.close()

    def add_price_sample(self, route: str, travel_date: datetime, price: float, currency: str):
        """
        Guarda un muestreo de precio para futuras comparaciones (baseline).
        """
        travel_month = travel_date.strftime("%Y-%m")
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO price_history (route, travel_month, price, currency)
                VALUES (?, ?, ?, ?)
            ''', (route, travel_month, price, currency))
            conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Error guardando precio: {e}")
        finally:
            conn.close()

    def get_baseline_stats(self, route: str, travel_date: datetime, days_back: int) -> Tuple[Optional[float], int]:
        """
        Calcula la mediana (baseline) y cuenta las muestras en los últimos `days_back` días.
        Retorna: (mediana, num_muestras)
        """
        travel_month = travel_date.strftime("%Y-%m")
        # Fecha límite para considerar historial (window)
        cutoff_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d %H:%M:%S")

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Seleccionar precios para esa ruta y mes registrados recientemente
        cursor.execute('''
            SELECT price FROM price_history
            WHERE route = ? 
            AND travel_month = ?
            AND recorded_at >= ?
            ORDER BY price
        ''', (route, travel_month, cutoff_date))
        
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return None, 0

        prices = [r[0] for r in rows]
        count = len(prices)
        
        # Cálculo de mediana simple
        if count % 2 == 1:
            median = prices[count // 2]
        else:
            mid = count // 2
            median = (prices[mid - 1] + prices[mid]) / 2.0
            
        return median, count

    def get_last_notification(self, deal_hash: str) -> Optional[Dict]:
        """
        Obtiene información de la última notificación para este deal específico.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT last_price, last_notified_at FROM notifications WHERE deal_hash = ?', (deal_hash,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                "last_price": row[0],
                "last_notified_at": row[1]
            }
        return None

    def record_notification(self, deal_hash: str, price: float):
        """
        Registra (o actualiza) que se envió una notificación para prevenir spam.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO notifications (deal_hash, last_price, last_notified_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(deal_hash) DO UPDATE SET
                    last_price = excluded.last_price,
                    last_notified_at = CURRENT_TIMESTAMP
            ''', (deal_hash, price))
            conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Error registrando notificación: {e}")
        finally:
            conn.close()
