
import os
import requests
import base64
from dotenv import load_dotenv
import logging
import yaml

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TwilioDebug")

def test_twilio():
    load_dotenv()
    
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    from_number = os.getenv("TWILIO_FROM_NUMBER")
    
    # Leer config.yaml
    with open("config.yaml", "r") as f:
        config = yaml.safe_load(f)
    to_number = config["system"]["recipient_phone"]

    logger.info(f"Testing Twilio (via requests)...")
    logger.info(f"Account: {account_sid[:5]}...")
    logger.info(f"From: {from_number}")
    logger.info(f"To: {to_number}")

    if not account_sid or not auth_token:
        logger.error(" Faltan credenciales en .env")
        return

    url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
    
    # Intento 2: Usando Templates (Content API)
    logger.info("Intento 2: Enviando mensaje con TEMPLATE (ContentSid)...")
    
    # SID proporcionado por el usuario
    content_sid = "HXb5b62575e6e4ff6129ad7c8efe1f983e" 
    content_variables = '{"1":"TestDate","2":"TestPrice"}' # Variables de ejemplo
    
    data = {
        "From": from_number,
        "To": to_number,
        "ContentSid": content_sid,
        "ContentVariables": content_variables
    }
    
    try:
        response = requests.post(url, data=data, auth=(account_sid, auth_token))
        
        if response.status_code == 201:
            logger.info(f" Mensaje TEMPLATE enviado! SID: {response.json().get('sid')}")
            print("\n¡ÉXITO! Mensaje de plantilla enviado. Revisa tu WhatsApp.")
        else:
            logger.error(f" Falló Twilio Template: {response.status_code}")
            # Escribir error completo a archivo
            with open("twilio_error.log", "w", encoding="utf-8") as f:
                f.write(response.text)
            print(f"\nFALLÓ. Revisa twilio_error.log para detalles.")
            
    except Exception as e:
        logger.error(f" Error de conexión: {e}")
        with open("twilio_error.log", "w", encoding="utf-8") as f:
            f.write(str(e))

if __name__ == "__main__":
    test_twilio()
