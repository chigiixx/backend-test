"""
Иерархия кастомных исключений приложения.

Каждое исключение знает свой HTTP-статус и машинно-читаемый error_code,
что позволяет единообразно обрабатывать ошибки в глобальном error handler'е
(см. app/main.py) и отдавать клиенту предсказуемый JSON.
"""
from typing import Optional


class AppException(Exception):
    """Базовое исключение приложения."""

    status_code = 500
    error_code = "internal_error"

    def __init__(self, detail: str, error_code: Optional[str] = None, status_code: Optional[int] = None):
        self.detail = detail
        if error_code:
            self.error_code = error_code
        if status_code:
            self.status_code = status_code
        super().__init__(detail)


class RateLimitExceededException(AppException):
    """429 — клиент превысил лимит запросов."""

    status_code = 429
    error_code = "rate_limit_exceeded"


class ServiceUnavailableException(AppException):
    """503 — внешний сервис недоступен (используется как запасной вариант,
    но в текущей реализации AI-сервис имеет graceful fallback и это исключение
    не выбрасывается наружу)."""

    status_code = 503
    error_code = "service_unavailable"


class NotFoundException(AppException):
    """404 — ресурс не найден."""

    status_code = 404
    error_code = "not_found"
