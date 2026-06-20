"""
Email-сервис: отправка уведомления владельцу + копии пользователю.

По умолчанию работает в режиме EMAIL_BACKEND=mock — реальные письма НЕ
отправляются, вместо этого текст письма сохраняется в data/emails/*.txt
и пишется в лог (удобно для демонстрации и тестов без реальных SMTP-данных).

Если задать EMAIL_BACKEND=smtp и заполнить SMTP_* в .env, сервис отправит
настоящие письма через smtplib — переключение бэкенда не требует
изменения кода в остальных частях приложения (Strategy-подобный подход).
"""
import logging
import smtplib
from datetime import datetime, timezone
from email.mime.text import MIMEText
from pathlib import Path

from app.config import get_settings

logger = logging.getLogger(__name__)


class EmailService:
    def __init__(self):
        settings = get_settings()
        self.settings = settings
        self.backend = settings.email_backend
        self.emails_dir = Path(settings.data_dir) / "emails"
        self.emails_dir.mkdir(parents=True, exist_ok=True)

    def send_owner_notification(self, contact: dict) -> bool:
        subject = f"Новая заявка с лендинга от {contact['name']}"
        body = (
            f"Имя: {contact['name']}\n"
            f"Телефон: {contact['phone']}\n"
            f"Email: {contact['email']}\n"
            f"Тональность (AI): {contact['analysis']['sentiment']}\n"
            f"Тип обращения (AI): {contact['analysis']['request_type']}\n\n"
            f"Комментарий:\n{contact['comment']}"
        )
        return self._send(self.settings.owner_email, subject, body, label="owner")

    def send_user_confirmation(self, contact: dict) -> bool:
        subject = "Ваша заявка получена"
        body = (
            f"Здравствуйте, {contact['name']}!\n\n"
            f"Спасибо за обращение. Мы получили ваше сообщение и скоро свяжемся с вами.\n\n"
            f"{contact['analysis']['suggested_reply']}\n\n"
            f"Ваш комментарий:\n{contact['comment']}"
        )
        return self._send(contact["email"], subject, body, label="user")

    def _send(self, to: str, subject: str, body: str, label: str) -> bool:
        if self.backend == "smtp":
            try:
                return self._send_smtp(to, subject, body)
            except Exception as exc:  # noqa: BLE001 — email не должен ронять основной флоу
                logger.error(f"Не удалось отправить email через SMTP ({label} -> {to}): {exc}")
                return False

        return self._send_mock(to, subject, body, label)

    def _send_mock(self, to: str, subject: str, body: str, label: str) -> bool:
        self.emails_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
        file_path = self.emails_dir / f"{timestamp}_{label}.txt"
        file_path.write_text(
            f"To: {to}\nSubject: {subject}\nDate: {datetime.now(timezone.utc).isoformat()}\n\n{body}\n",
            encoding="utf-8",
        )
        logger.info(f'[MOCK EMAIL] Письмо "{subject}" отправлено на {to} (сохранено в {file_path.name})')
        return True

    def _send_smtp(self, to: str, subject: str, body: str) -> bool:
        s = self.settings
        if not s.smtp_host:
            raise RuntimeError("SMTP_HOST не задан в .env")

        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = s.smtp_from
        msg["To"] = to

        with smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=10) as server:
            if s.smtp_use_tls:
                server.starttls()
            if s.smtp_user and s.smtp_password:
                server.login(s.smtp_user, s.smtp_password)
            server.sendmail(s.smtp_from, [to], msg.as_string())

        logger.info(f'[SMTP] Письмо "{subject}" отправлено на {to}')
        return True
