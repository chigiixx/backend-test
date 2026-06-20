"""
Точка входа приложения.

Здесь собирается всё вместе: CORS, middleware логирования запросов,
глобальные обработчики ошибок (3 уровня — кастомные AppException,
ошибки валидации Pydantic, и "поймать всё остальное"), роутеры,
и автогенерируемая Swagger/OpenAPI документация (/docs, /redoc).
"""
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import contact, health, metrics
from app.config import get_settings
from app.core.exceptions import AppException
from app.core.logging_config import setup_logging
from app.core.middleware import request_logging_middleware

setup_logging()
logger = logging.getLogger(__name__)
settings = get_settings()

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info(f"{settings.app_name} запущен в режиме '{settings.app_env}'")
    yield
    logger.info(f"{settings.app_name} останавливается")


app = FastAPI(
    title=settings.app_name,
    description=(
        "Backend API для лендинг-презентации разработчика: форма обратной связи "
        "с AI-анализом обращений (тональность, тип запроса), email-уведомлениями, "
        "rate limiting и файловым логированием."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Request logging + X-Request-ID ---
app.middleware("http")(request_logging_middleware)


# --- Глобальная обработка ошибок ---
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    logger.warning(f"AppException: {exc.error_code} - {exc.detail} | path={request.url.path}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.error_code,
            "detail": exc.detail,
            "request_id": getattr(request.state, "request_id", None),
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # exc.errors() может содержать в ctx сырые исключения (например ValueError
    # из наших @field_validator) — они не сериализуются в JSON напрямую,
    # поэтому собираем только безопасные для сериализации поля.
    safe_errors = [
        {"loc": list(err.get("loc", [])), "msg": err.get("msg"), "type": err.get("type")} for err in exc.errors()
    ]
    logger.info(f"Validation error | path={request.url.path} | errors={safe_errors}")
    return JSONResponse(
        status_code=422,
        content={
            "error": "validation_error",
            "detail": safe_errors,
            "request_id": getattr(request.state, "request_id", None),
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled exception | path={request.url.path}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_error",
            "detail": "Внутренняя ошибка сервера. Попробуйте позже.",
            "request_id": getattr(request.state, "request_id", None),
        },
    )


# --- Роутеры ---
app.include_router(health.router)
app.include_router(metrics.router)
app.include_router(contact.router)


@app.get("/api/info", tags=["System"], summary="Информация о сервисе")
async def api_info():
    return {"service": settings.app_name, "status": "running", "docs": "/docs"}


# --- Лендинг (frontend/) ---
# Если папка frontend существует (она входит в поставку проекта), отдаём её
# как статический сайт прямо с того же origin — это значит, что один деплой
# (например, на Render) даёт сразу и рабочий API, и живую демо-страницу с
# формой, которая реально стучится в этот же backend. Если папки нет (например,
# при минимальном API-only деплое) — backend продолжает работать как чистый API,
# а корень "/" просто не смонтирован (используйте /docs).
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
else:
    logger.warning(f"Папка frontend не найдена ({FRONTEND_DIR}) — сайт не будет раздаваться, доступен только API")
