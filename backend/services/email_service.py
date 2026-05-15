import os
import smtplib
import traceback
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

from config import config

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "email_templates"

_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
)


def _render(template_name: str, **ctx) -> str:
    return _env.get_template(template_name).render(**ctx)


def _send(to_email: str, subject: str, html_body: str, text_fallback: Optional[str] = None) -> bool:
    if not config.SMTP_USER or not config.SMTP_PASSWORD:
        print(f"⚠️  SMTP not configured; skipping email to {to_email} ({subject!r})")
        return False
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{config.SMTP_FROM_NAME} <{config.SMTP_USER}>"
        msg["To"] = to_email
        if text_fallback:
            msg.attach(MIMEText(text_fallback, "plain"))
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=20) as server:
            server.starttls()
            server.login(config.SMTP_USER, config.SMTP_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"❌ Email send failed to {to_email}: {e}")
        traceback.print_exc()
        return False


def send_otp(to_email: str, otp: str) -> bool:
    html = _render("otp.html", otp=otp, base_url=config.BASE_URL)
    return _send(to_email, "Your StockSense verification code", html,
                 text_fallback=f"Your StockSense verification code is: {otp}")


def send_welcome(to_email: str, name: Optional[str] = None) -> bool:
    html = _render("welcome.html", name=name or to_email, base_url=config.BASE_URL)
    return _send(to_email, "Welcome to StockSense", html)


def send_password_reset(to_email: str, token: str) -> bool:
    reset_url = f"{config.BASE_URL}/reset-password?token={token}"
    html = _render("password_reset.html", reset_url=reset_url, base_url=config.BASE_URL)
    return _send(to_email, "Reset your StockSense password", html,
                 text_fallback=f"Reset link: {reset_url}")


def send_alert(to_email: str, alert: dict) -> bool:
    """alert dict: symbol, name, price, change_pct, alert_type, threshold, currency"""
    html = _render("alert.html", alert=alert, base_url=config.BASE_URL)
    subject = f"📊 {alert['symbol']} alert: {alert.get('headline', 'Price movement')}"
    return _send(to_email, subject, html)


def send_digest(to_email: str, digest: dict) -> bool:
    """digest dict: name, period, watchlist_rows, top_picks, totals"""
    html = _render("digest.html", digest=digest, base_url=config.BASE_URL)
    period = digest.get("period", "Daily")
    return _send(to_email, f"📈 Your StockSense {period} Digest", html)
