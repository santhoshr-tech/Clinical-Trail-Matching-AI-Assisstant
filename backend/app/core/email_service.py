import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, List
from app.core.config import settings

logger = logging.getLogger("clinical_trial_assistant")

def send_missed_week_alert_email(
    enrollment_id: str,
    patient_id: str,
    trial_title: str,
    missed_week: int,
    missed_since_date: str,
    researcher_email: str = None,
    patient_email: str = None
) -> Dict[str, Any]:
    """
    Send missed-week email alert to both researcher and patient.
    Uses SMTP credentials if available; falls back to structured logging simulation.
    """
    target_researcher = researcher_email or settings.ALERT_RESEARCHER_EMAIL
    target_patient = patient_email or settings.ALERT_PATIENT_EMAIL

    subject = f"[URGENT ALERT] Missed Weekly Report - Enrollment {enrollment_id}"
    
    body_text = f"""
Clinical Trial Progress Monitoring Alert
=========================================
Trial: {trial_title}
Enrollment ID: {enrollment_id}
Patient ID: {patient_id}
Missed Week Number: Week {missed_week}
Next Report Was Due: {missed_since_date}

Notice:
Our system detected that the scheduled weekly progress report for Week {missed_week} has not been uploaded on time.

Action Required:
Please log in to the Clinical Research Assistant or Patient Portal to upload the pending progress report as soon as possible to ensure continuity of treatment monitoring.

Research Coordinator Email: {target_researcher}
Patient Email: {target_patient}
Timestamp: {missed_since_date}
"""

    recipients = list(set([e for e in [target_researcher, target_patient] if e]))

    if not recipients:
        return {"success": False, "message": "No recipients configured."}

    # If SMTP credentials are provided, attempt real transmission
    if settings.SMTP_USER and settings.SMTP_PASSWORD:
        try:
            msg = MIMEMultipart()
            msg["From"] = settings.SMTP_USER
            msg["To"] = ", ".join(recipients)
            msg["Subject"] = subject
            msg.attach(MIMEText(body_text, "plain"))

            server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10)
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_USER, recipients, msg.as_string())
            server.quit()

            logger.info(f"Successfully sent missed-week email alert to {recipients} for {enrollment_id}")
            return {
                "success": True,
                "mode": "smtp_live",
                "recipients": recipients,
                "enrollment_id": enrollment_id
            }
        except Exception as e:
            logger.warning(f"SMTP send failed ({e}). Falling back to logged notification mode.")

    # Simulated/Logged transmission for testing environments
    logger.info(f"=== [SIMULATED MISSED-WEEK EMAIL ALERT] ===")
    logger.info(f"Recipients: {recipients}")
    logger.info(f"Subject: {subject}")
    logger.info(body_text)
    logger.info(f"============================================")

    return {
        "success": True,
        "mode": "logged_simulation",
        "recipients": recipients,
        "enrollment_id": enrollment_id,
        "note": "SMTP credentials not provided or unreachable; email alert logged to system audit."
    }
