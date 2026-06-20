"""
Pydantic-схемы запросов и ответов.

Валидация (имя/телефон/email/комментарий) выполняется декларативно —
FastAPI автоматически вернёт 422 с детальным описанием ошибок, если
данные не прошли проверку (см. global validation_exception_handler в main.py).
"""
import re
from typing import Dict, Literal, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

PHONE_REGEX = re.compile(r"^\+?[0-9\s\-()]{7,20}$")


class ContactRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, examples=["Иван Иванов"])
    phone: str = Field(..., examples=["+7 999 123-45-67"])
    email: EmailStr = Field(..., examples=["ivan@example.com"])
    comment: str = Field(
        ..., min_length=5, max_length=2000, examples=["Хочу обсудить разработку лендинга для моего проекта"]
    )

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Имя не может быть пустым")
        return v

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        v = v.strip()
        if not PHONE_REGEX.match(v):
            raise ValueError("Некорректный формат телефона. Пример: +7 999 123-45-67")
        digits_only = re.sub(r"\D", "", v)
        if not (7 <= len(digits_only) <= 15):
            raise ValueError("Телефон должен содержать от 7 до 15 цифр")
        return v

    @field_validator("comment")
    @classmethod
    def comment_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Комментарий не может быть пустым")
        return v


class AIAnalysis(BaseModel):
    sentiment: Literal["positive", "neutral", "negative"]
    request_type: Literal["question", "complaint", "feedback", "proposal", "other"]
    suggested_reply: str
    ai_used: bool = Field(..., description="true — ответ дал внешний AI-провайдер, false — сработал fallback")


class ContactResponse(BaseModel):
    id: str
    status: Literal["received"]
    message: str
    analysis: AIAnalysis
    created_at: str


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    timestamp: str
    ai_configured: bool
    email_backend: str
    uptime_seconds: float


class MetricsResponse(BaseModel):
    total_received: int
    total_rate_limited: int
    by_sentiment: Dict[str, int]
    by_request_type: Dict[str, int]
    ai_used_count: int
    ai_fallback_count: int
    last_updated: Optional[str]


class ErrorResponse(BaseModel):
    error: str
    detail: str
    request_id: Optional[str] = None
