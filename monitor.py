import os
import json
import time
import logging
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from playwright.sync_api import sync_playwright
import schedule
import config

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(config.LOG_FILE),
        logging.StreamHandler()
    ]
)

def send_email_notification(message):
    logging.info("Attempting to send email...")
    # Debug info (masked)
    logging.info(f"Config - USER: {'Set' if config.SMTP_USER else 'MISSING'}, PASS: {'Set' if config.SMTP_PASS else 'MISSING'}, TARGET: {'Set' if config.DESTINATARIO_EMAIL else 'MISSING'}")
    
    if not config.SMTP_USER or not config.SMTP_PASS or not config.DESTINATARIO_EMAIL:
        logging.warning("Email configuration missing. Skipping.")
        if os.getenv("FORCE_SEND_TEST_EMAIL") == "true":
             raise ValueError("Email configuration missing during forced test!")
        return False
    
    msg = MIMEText(message)
    msg['Subject'] = '🚨 FORMULARIO CONSULADO ABIERTO - Pedir turno YA'
    msg['From'] = config.SMTP_USER
    msg['To'] = config.DESTINATARIO_EMAIL
    
    try:
        with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT) as server:
            server.starttls()
            server.login(config.SMTP_USER, config.SMTP_PASS)
            server.send_message(msg)
        logging.info("Email notification sent.")
        return True
    except Exception as e:
        logging.error(f"Error sending email notification: {e}")
        if os.getenv("FORCE_SEND_TEST_EMAIL") == "true":
             raise e
        return False

def get_last_state():
    try:
        if os.path.exists(config.ESTADO_FILE):
            with open(config.ESTADO_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        logging.error(f"Error reading state file: {e}")
    return {"ultimo_estado": "desconocido", "ultima_verificacion": None}

def save_state(estado):
    try:
        with open(config.ESTADO_FILE, 'w') as f:
            json.dump(estado, f, indent=4)
    except Exception as e:
        logging.error(f"Error saving state file: {e}")

def check_form_status():
    logging.info(f"Checking form status at {config.FORM_URL}...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        try:
            page.goto(config.FORM_URL, wait_until="networkidle", timeout=60000)
            # Wait for content to render
            page.wait_for_timeout(8000)
            
            # Try to find the closed message by selector or text
            closed_selector = 'div[data-automation-id="form-closed-message"]'
            is_closed = page.query_selector(closed_selector) is not None
            
            inner_text = page.evaluate("document.body.innerText")
            if not is_closed:
                is_closed = "Este formulario está cerrado" in inner_text or "This form is closed" in inner_text
            
            # Double check: is there any input?
            has_inputs = page.query_selector("input, textarea, .office-form-question-content") is not None
            
            current_status = "cerrado" if is_closed else ("abierto" if has_inputs else "desconocido")
            
            if current_status == "desconocido":
                if "Crear mi propio formulario" in inner_text and not has_inputs:
                    current_status = "cerrado"
            
            logging.info(f"Current status: {current_status.upper()}")
            
            # Forced test email for cloud verification
            if os.getenv("FORCE_SEND_TEST_EMAIL") == "true":
                send_email_notification(f"✅ PRUEBA CLOUD EXITOSA: El monitor está funcionando desde GitHub.\nEstado detectado: {current_status.upper()}\nURL: {config.FORM_URL}")
            
            last_state_data = get_last_state()
            last_status = last_state_data.get("ultimo_estado")
            
            if current_status == "abierto" and last_status != "abierto":
                msg = f"🚨 ¡EL FORMULARIO ESTÁ ABIERTO!\nAccede ahora: {config.FORM_URL}"
                send_email_notification(msg)
            
            save_state({
                "ultimo_estado": current_status,
                "ultima_verificacion": datetime.now().isoformat(),
                "alerta_enviada": current_status == "abierto"
            })
            
        except Exception as e:
            logging.error(f"Error during form check: {e}")
        finally:
            browser.close()

def main():
    # Initial check
    check_form_status()
    
    # If ONE_RUN is set, exit after initial check
    if os.getenv("ONE_RUN") == "true":
        logging.info("ONE_RUN detected. Exiting.")
        return

    # Schedule
    schedule.every(config.CHECK_INTERVAL).minutes.do(check_form_status)
    logging.info(f"Monitor started. Scheduling check every {config.CHECK_INTERVAL} minutes.")
    
    while True:
        schedule.run_pending()
        time.sleep(10)

if __name__ == "__main__":
    main()
