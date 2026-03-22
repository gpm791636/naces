# Monitoreo Automático de Formulario Consular

Script para verificar diariamente si el formulario de turnos del Consulado de España en Córdoba está abierto.

## Requisitos

- Python 3.12+
- Playwright (Chromium)

## Instalación Local

1. Instala las dependencias:
   ```bash
   pip install -r requirements.txt
   python -m playwright install chromium
   ```
2. Configura las variables en el archivo `.env`:
   - `SMTP_USER`: Tu email de Gmail.
   - `SMTP_PASS`: Tu contraseña de aplicación de 16 letras.
   - `DESTINATARIO_EMAIL`: `garinpablo@gmail.com`.

## Automatización en PC (Local)

Para que corra automáticamente aunque la PC esté apagada al momento del inicio:
1. Usa el **Programador de Tareas** con el archivo `run_once.bat`.
2. En las propiedades de la tarea, pestaña **Configuración**, marca: **"Ejecutar tarea lo antes posible si no se inició la ejecución programada"**.

---

## ☁️ Solución Cloud (PC Apagada)

Si deseas que el script corra **sin depender de tu PC**, la mejor opción es usar **GitHub Actions**. Es gratuito y permite ejecutar el script en la nube cada X horas.

### Pasos para GitHub Actions:
1. Crea un repositorio en GitHub.
2. Sube estos archivos.
3. Configura `SMTP_USER` y `SMTP_PASS` en **Secrets** del repositorio.
4. Crea un archivo `.github/workflows/monitor.yml`.

> [!NOTE]
> Si te interesa esta opción, avísame y puedo generarte el archivo de configuración para GitHub.
