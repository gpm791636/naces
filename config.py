import os
from dotenv import load_dotenv

load_dotenv()

# Form URL
FORM_URL = "https://forms.office.com/e/QnKb5J4cQ8"

# Notification Settings - Email Only
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
DESTINATARIO_EMAIL = os.getenv("DESTINATARIO_EMAIL", "garinpablo@gmail.com")

# Check interval (in minutes)
# Default is 1440 (24 hours). 
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "1440"))

# File paths
ESTADO_FILE = "estado.json"
LOG_FILE = "monitor.log"
