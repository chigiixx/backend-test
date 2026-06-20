"""
Сервисный слой: оркестрирует полный цикл обработки обращения
(валидация уже выполнена на уровне Pydantic-схемы до вызова этого сервиса):

    AI-анализ → отправка email (владельцу + копия пользователю) → сохранение → метрики

Контроллер (app/api/routes/contact.py) не знает деталей реализации —
он только вызывает handle_contact_request и формирует HTTP-ответ.
"""
import logging

from app.repositories.contact_repository import ContactRepository
from app.repositories.metrics_repository import MetricsRepository
from app.schemas.contact import ContactRequest
from app.services.ai_service import AIService
from app.services.email_service import EmailService

logger = logging.getLogger(__name__)


class ContactService:
    def __init__(self):
        self.ai_service = AIService()
        self.email_service = EmailService()
        self.contact_repository = ContactRepository()
        self.metrics_repository = MetricsRepository()

    def handle_contact_request(self, payload: ContactRequest) -> dict:
        logger.info(f"Обработка обращения от {payload.email}")

        analysis = self.ai_service.analyze(payload.comment)
        logger.info(
            f"AI-анализ завершён: sentiment={analysis['sentiment']} "
            f"type={analysis['request_type']} ai_used={analysis['ai_used']}"
        )

        contact_dict = {
            "name": payload.name,
            "phone": payload.phone,
            "email": payload.email,
            "comment": payload.comment,
            "analysis": analysis,
        }

        # Отправка email не должна "ронять" обращение — даже если письма не ушли,
        # заявка всё равно должна быть сохранена и возвращена клиенту.
        owner_sent = self.email_service.send_owner_notification(contact_dict)
        user_sent = self.email_service.send_user_confirmation(contact_dict)

        record = self.contact_repository.save(
            name=payload.name,
            phone=payload.phone,
            email=payload.email,
            comment=payload.comment,
            analysis=analysis,
            owner_email_sent=owner_sent,
            user_email_sent=user_sent,
        )

        self.metrics_repository.record_contact(analysis)

        return record
