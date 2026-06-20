"""
Middleware для логирования каждого HTTP-запроса и добавления X-Request-ID,
который затем используется в логах и в теле ошибок — упрощает отладку
по жалобе пользователя ("у меня была ошибка, вот request_id").
"""
import time
import uuid

from fastapi import Request

from app.core.logging_config import get_access_logger

access_logger = get_access_logger()


async def request_logging_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    start = time.perf_counter()

    response = await call_next(request)

    duration_ms = round((time.perf_counter() - start) * 1000, 2)
    client_ip = request.client.host if request.client else "unknown"

    access_logger.info(
        f'{client_ip} "{request.method} {request.url.path}" '
        f"{response.status_code} {duration_ms}ms req_id={request_id}"
    )

    response.headers["X-Request-ID"] = request_id
    return response
