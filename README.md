
# ✈️ Flight Deal Monitor

Un sistema inteligente en Python que monitorea precios de vuelos utilizando la API de Amadeus y notifica vía WhatsApp (Twilio) cuando encuentra ofertas que cumplen tus criterios o te envía un resumen diario con la mejor opción disponible.

## ✨ Características

- **Búsqueda Automatizada**: Escanea múltiples fechas y aeropuertos automáticamente.
- **Lógica de "Gangas"**: Filtra ofertas basándose en un precio máximo y un descuento relativo estacional.
- **Interfaz Gráfica (GUI)**:
  - Lanzador moderno con modo oscuro.
  - Configuración fácil de origen, destino, fechas y presupuesto.
  - **Barra de Progreso** en tiempo real.
  - Consola de logs integrada.
- **Notificaciones Inteligentes**:
  - Alerta inmediata si encuentra una oferta por debajo de tu presupuesto.
  - **Resumen Diario**: Si no hay ofertas, te avisa que terminó y te muestra la "Mejor Alternativa" encontrada.
  - **Links Directos**: Incluye enlaces a Google Flights para reservar rápidamente.
- **Multi-Hilo**: La interfaz no se congela mientras busca.

## 🚀 Instalación

1. **Clonar el repositorio**:
   ```bash
   git clone https://github.com/tu-usuario/flight_monitor.git
   cd flight_monitor
   ```

2. **Instalar dependencias**:
   ```bash
   pip install -r requirements.txt
   ```
   *(Si no existe requirements.txt, las principales son: `requests`, `pyyaml`, `python-dotenv`, `customtkinter`)*

3. **Configurar Credenciales (.env)**:
   Crea un archivo `.env` en la raíz con tus claves API:
   ```env
   AMADEUS_CLIENT_ID=tu_client_id
   AMADEUS_CLIENT_SECRET=tu_client_secret
   TWILIO_ACCOUNT_SID=tu_sid
   TWILIO_AUTH_TOKEN=tu_token
   TWILIO_FROM_NUMBER=whatsapp:+14155238886
   ```

## ⚙️ Configuración (config.yaml)

El archivo `config.yaml` controla toda la lógica (presupuesto, filtros, fechas). 
**¡Pero no necesitas editarlo manualmente!** Usa la GUI para cambiar lo más importante:
- Origen / Destino
- Ventana de fechas
- Presupuesto Máximo

## 🖥️ Uso

Simplemente ejecuta el lanzador:

```bash
python gui_launcher.py
```

1. Ajusta tus preferencias en el panel izquierdo.
2. Marca **"Enable Daily Summary"** si quieres recibir reporte aunque no haya gangas.
3. Presiona **"RUN SEARCH"**.
4. Observa el progreso y espera tu WhatsApp. 📲

## 📋 Requisitos de API

- **Amadeus for Developers**: Crear cuenta y app para obtener Keys (Entorno Test o Production).
- **Twilio**: Cuenta con WhatsApp Sandbox activado. (Recuerda enviar el código `join ...` a tu número de Sandbox cada 3 días).

---
Hecho con 🐍 Python.
