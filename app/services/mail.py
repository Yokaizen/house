import logging
import smtplib
from email.message import EmailMessage

from app.config import get_settings

log = logging.getLogger(__name__)


def envoyer(destinataire: str | None, sujet: str, corps: str) -> bool:
    """Envoie un e-mail texte. Sans SMTP configuré, se contente de journaliser."""
    s = get_settings()
    if not destinataire:
        return False
    if not s.smtp_host:
        log.info("[e-mail non envoyé, SMTP non configuré] à=%s sujet=%s", destinataire, sujet)
        return False
    msg = EmailMessage()
    msg["From"] = s.smtp_from
    msg["To"] = destinataire
    msg["Subject"] = sujet
    msg.set_content(corps)
    try:
        with smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=20) as smtp:
            if s.smtp_starttls:
                smtp.starttls()
            if s.smtp_user:
                smtp.login(s.smtp_user, s.smtp_password)
            smtp.send_message(msg)
        return True
    except (smtplib.SMTPException, OSError) as e:
        log.error("Échec d'envoi d'e-mail à %s : %s", destinataire, e)
        return False
