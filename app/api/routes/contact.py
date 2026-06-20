"""
Controller-слой для формы обратной связи.

Тонкий контроллер: валидация — на Pydantic-схеме, rate limiting и бизнес-логика
вынесены в сервисы. Контроллер только дирижирует вызовами и формирует HTTP-ответ.
"""
import logging

from fastapi import APIRouter, Request, status

from app.repositories.metrics_repository import MetricsRepository
from app.schemas.contact import ContactRequest, ContactResponse, ErrorResponse
from app.services.contact_service import ContactService
from app.services.rate_limiter import RateLimiter

router = APIRouter(prefix="/api", tags=["Contact"])
logger = logging.getLogger(__name__)

contact_service = ContactService()
rate_limiter = RateLimiter()
metrics_repository = MetricsRepository()


@router.post(
    "/contact",
    response_model=ContactResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Отправить форму обратной связи",
    description=(
        "Принимает обращение с лендинга, проверяет rate limit, анализирует тональность "
        "и тип запроса через AI (с graceful fallback), отправляет email-уведомления "
        "владельцу и пользователю, сохраняет обращение."
    ),
    responses={
        422: {"model": ErrorResponse, "description": "Ошибка валидации входных данных"},
        429: {"model": ErrorResponse, "description": "Превышен лимит запросов"},
        500: {"model": ErrorResponse, "description": "Внутренняя ошибка сервера"},
    },
)
async def create_contact(payload: ContactRequest, request: Request):
    client_ip = request.client.host if request.client else "unknown"

    try:
        rate_limiter.check(client_ip)
    except Exception:
        metrics_repository.record_rate_limited()
        raise

    record = contact_service.handle_contact_request(payload)

    return ContactResponse(
        id=record["id"],
        status="received",
        message="Спасибо! Ваше обращение получено, мы скоро с вами свяжемся.",
        analysis=record["analysis"],
        created_at=record["created_at"],
    )
