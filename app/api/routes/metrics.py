"""GET /api/metrics — агрегированная статистика обращений (хранится в data/storage/metrics.json)."""
from fastapi import APIRouter

from app.repositories.metrics_repository import MetricsRepository
from app.schemas.contact import MetricsResponse

router = APIRouter(prefix="/api", tags=["System"])

metrics_repository = MetricsRepository()


@router.get("/metrics", response_model=MetricsResponse, summary="Статистика обращений")
async def metrics():
    data = metrics_repository.get()
    return MetricsResponse(**data)
