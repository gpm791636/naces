import os
import json
import time
import logging
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from playwright.sync_api import sync_playwright
import schedule
import config

# ── Logging ──────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(config.LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# ── Email ─────────────────────────────────────────────────────────────────
def send_email_notification(subject: str, body: str) -> bool:
    """Send an HTML-capable email notification."""
    if not config.SMTP_USER or not config.SMTP_PASS or not config.DESTINATARIO_EMAIL:
        logging.warning("Email configuration missing. Skipping notification.")
        return False

    msg = MIMEMultipart("alternative")
    msg['Subject'] = subject
    msg['From'] = config.SMTP_USER
    msg['To'] = config.DESTINATARIO_EMAIL

    # Plain-text fallback
    msg.attach(MIMEText(body, "plain", "utf-8"))
    # HTML version
    html_body = body.replace("\n", "<br>")
    html = f"""
    <html><body style="font-family:Arial,sans-serif;font-size:15px;">
    <div style="background:#fff3cd;border-left:6px solid #ff9800;padding:16px;border-radius:4px;">
      <h2 style="color:#e65100;margin:0 0 8px;">🚨 FORMULARIO DEL CONSULADO ABIERTO</h2>
      <p>{html_body}</p>
      <a href="{config.FORM_URL}" style="display:inline-block;margin-top:12px;padding:10px 20px;
         background:#e65100;color:#fff;text-decoration:none;border-radius:4px;font-weight:bold;">
        ➡ Acceder al formulario ahora
      </a>
    </div>
    </body></html>
    """
    msg.attach(MIMEText(html, "html", "utf-8"))

    try:
        with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT) as server:
            server.starttls()
            server.login(config.SMTP_USER, config.SMTP_PASS)
            server.send_message(msg)
        logging.info("✅ Email notification sent successfully.")
        return True
    except Exception as e:
        logging.error(f"❌ Error sending email: {e}")
        return False

# ── State persistence ─────────────────────────────────────────────────────
def get_last_state() -> dict:
    try:
        if os.path.exists(config.ESTADO_FILE):
            with open(config.ESTADO_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logging.error(f"Error reading state file: {e}")
    return {"ultimo_estado": "desconocido", "ultima_verificacion": None, "alerta_enviada": False}

def save_state(estado: dict) -> None:
    try:
        with open(config.ESTADO_FILE, 'w', encoding='utf-8') as f:
            json.dump(estado, f, indent=4, ensure_ascii=False)
    except Exception as e:
        logging.error(f"Error saving state file: {e}")

# ── Form check ────────────────────────────────────────────────────────────
def _scrape_form(page) -> str:
    """
    Returns 'abierto', 'cerrado', or 'desconocido'.
    Isolated so it can be retried cleanly.
    """
    page.goto(config.FORM_URL, wait_until="networkidle", timeout=60000)
    page.wait_for_timeout(8000)  # Let React/Angular finish rendering

    inner_text = page.evaluate("document.body.innerText")

    # 1. Explicit closed message (selector)
    closed_selector = 'div[data-automation-id="form-closed-message"]'
    if page.query_selector(closed_selector):
        return "cerrado"

    # 2. Explicit closed message (text)
    closed_phrases = [
        "Este formulario está cerrado",
        "This form is closed",
        "Este formulário está fechado",
    ]
    if any(phrase in inner_text for phrase in closed_phrases):
        return "cerrado"

    # 3. Active inputs → form is open
    if page.query_selector("input, textarea, .office-form-question-content"):
        return "abierto"

    # 4. Fallback heuristic: generic MS Forms "create your own" footer without inputs
    if "Crear mi propio formulario" in inner_text or "Create my own form" in inner_text:
        return "cerrado"

    return "desconocido"

def check_form_status(retries: int = 2) -> None:
    logging.info(f"🔍 Checking form status at {config.FORM_URL}...")

    current_status = "desconocido"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            )
        )
        page = context.new_page()

        for attempt in range(1, retries + 1):
            try:
                current_status = _scrape_form(page)
                logging.info(f"  Attempt {attempt}: status = {current_status.upper()}")
                if current_status != "desconocido":
                    break
                # If still unknown, wait a bit and retry
                if attempt < retries:
                    logging.warning("  Status undetermined, retrying in 15 s...")
                    time.sleep(15)
            except Exception as e:
                logging.error(f"  Attempt {attempt} failed: {e}")
                if attempt < retries:
                    time.sleep(15)

        browser.close()

    logging.info(f"📋 Final status: {current_status.upper()}")

    last_state_data = get_last_state()
    last_status = last_state_data.get("ultimo_estado")

    # Only alert when transitioning TO open (avoids repeat emails)
    if current_status == "abierto" and last_status != "abierto":
        subject = "🚨 FORMULARIO CONSULADO ABIERTO - Pedir turno YA"
        body = (
            f"¡EL FORMULARIO ESTÁ ABIERTO!\n\n"
            f"Accedé ahora antes de que se llene:\n{config.FORM_URL}\n\n"
            f"Verificado el {datetime.now().strftime('%d/%m/%Y a las %H:%M')} hs (ART)"
        )
        send_email_notification(subject, body)
    elif current_status == "desconocido":
        logging.warning(
            "⚠️  Could not determine form status after all retries. "
            "State NOT updated to avoid false positives."
        )
        # Do not overwrite last known good state
        return

    save_state({
        "ultimo_estado": current_status,
        "ultima_verificacion": datetime.now().isoformat(),
        "alerta_enviada": current_status == "abierto" and last_status != "abierto",
    })

# ── Entry point ───────────────────────────────────────────────────────────
def main():
    check_form_status()

    if os.getenv("ONE_RUN") == "true":
        logging.info("ONE_RUN mode — exiting after single check.")
        return

    schedule.every(config.CHECK_INTERVAL).minutes.do(check_form_status)
    logging.info(f"🕒 Monitor running. Next check in {config.CHECK_INTERVAL} min.")

    while True:
        schedule.run_pending()
        time.sleep(10)

if __name__ == "__main__":
    main()
