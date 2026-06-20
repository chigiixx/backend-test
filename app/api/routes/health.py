"""GET /api/health — проверка статуса сервиса (для аплинков/мониторинга/деплоя)."""
import time
from datetime import datetime, timezone

from fastapi import APIRouter

from app.config import get_settings
from app.schemas.contact import HealthResponse
from app.services.ai_service import AIService

router = APIRouter(prefix="/api", tags=["System"])

_start_time = time.time()
_ai_service = AIService()


@router.get("/health", response_model=HealthResponse, summary="Проверка статуса сервиса")
async def health():
    settings = get_settings()
    return HealthResponse(
        status="ok",
        timestamp=datetime.now(timezone.utc).isoformat(),
        ai_configured=_ai_service.is_configured(),
        email_backend=settings.email_backend,
        uptime_seconds=round(time.time() - _start_time, 2),
    )
