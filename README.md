# Flight Deal Monitor ✈️

A configuration-driven, robust flight monitoring system powered by Python and the **Amadeus Self-Service API**. Designed to detect round-trip flight deals based on historical baseline prices and flexible user constraints.

## Features

- **Configuration-First**: All parameters (destinations, dates, budgets, thresholds) are managed in `config.yaml`.
- **Smart Scoring**: Uses a statistics-based approach (median filtering) to identify real deals (10-25% discount).
- **Cold Start Protection**: Safely handles routes with no history by building baselines on the fly while enforcing strict budgets.
- **Deduplication**: Prevents spamming deeply checks if specific itineraries have already been notified.
- **WhatsApp Alerts**: Instant notifications via Twilio.

## Setup

### Prerequisites
- Python 3.11+
- **Amadeus Self-Service API Credentials** (Client ID & Secret).
- Twilio Account (SID, Token, WhatsApp Sandbox/Sender).

### Installation

1. Install dependencies:
   ```bash
   pip install requests python-dotenv PyYAML
   ```
   *(Note: `sqlite3` is included in Python standard library)*

2. Configure Environment:
   Copy `.env.example` to `.env` and fill in your credentials.
   ```bash
   cp .env.example .env
   # Add AMADEUS_CLIENT_ID and AMADEUS_CLIENT_SECRET
   ```

3. Configure Logic:
   Edit `config.yaml` to set your travel preferences.

## Usage

Run the script manually or via cron/scheduler:

```bash
python main.py
```

### Amadeus API Limitations
- **Date Search**: Unlike the previous Tequila backend, Amadeus does not natively search "All dates in a 3 month window" in a single call.
- **Strategy**: The script now intelligently iterates through random dates within your configured window during each run, respecting `max_queries_per_run`. Run the script frequently (e.g. hourly) to cover more date combinations over time.
- **Deep Links**: Amadeus does not provide direct booking links (Deep Links). The notification will contain the deal details but no clickable purchase link.

### Config Guide (`config.yaml`)

This file controls the entire behavior. Key sections:
- `travel`: Origin/Destination countries.
- `dates`: Window of search (e.g. next 30-150 days).
- `filters`: Stopovers, airlines, baggage.
- `budget`: Max absolute price.
- `scoring`: Statistical rules for defining a "deal".

*(Nota: Los comentarios dentro de `config.yaml` están en español para facilitar la configuración)*

## Data Logic

### Baseline & Scoring
The system calculates a historical baseline (Median P50) for every Route + Month pair.
- **Normal Operation**: Matches if price is 10%-25% below baseline.
- **Cold Start**: If historical samples < `min_samples` (default 5):
  - Uses strictly available data.
  - **MUST** be below `budget.max_price`.
  - Notifications are tagged as `LOW CONFIDENCE`.

### Persistence
- `deals.db` (SQLite) stores:
  - `price_history`: Simplified price samples for baseline calc.
  - `notifications`: Hash of sent deals to prevent duplicates.
