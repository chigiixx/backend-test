"""
Базовые тесты API.

Запуск AI-провайдера не сконфигурирован в тестовом окружении (нет
OPENAI_API_KEY) — это намеренно: так мы проверяем, что graceful fallback
действительно работает и сервис остаётся работоспособным без внешнего AI.
"""
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

TEST_DATA_DIR = Path("data_test")

VALID_PAYLOAD = {
    "name": "Иван Иванов",
    "phone": "+7 999 123-45-67",
    "email": "ivan@example.com",
    "comment": "Отличный сайт, хочу обсудить разработку лендинга!",
}


@pytest.fixture(autouse=True)
def clean_test_env(monkeypatch):
    """Изолирует каждый тест: своя папка данных, предсказуемый rate limit."""
    monkeypatch.setenv("DATA_DIR", str(TEST_DATA_DIR))
    monkeypatch.setenv("RATE_LIMIT_MAX_REQUESTS", "3")
    monkeypatch.setenv("RATE_LIMIT_WINDOW_SECONDS", "60")
    monkeypatch.setenv("OPENAI_API_KEY", "")  # форсируем fallback-анализ

    from app.config import get_settings

    get_settings.cache_clear()

    if TEST_DATA_DIR.exists():
        shutil.rmtree(TEST_DATA_DIR)

    yield

    if TEST_DATA_DIR.exists():
        shutil.rmtree(TEST_DATA_DIR)


@pytest.fixture
def client():
    from app.main import app

    return TestClient(app)


def test_root_serves_frontend(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "<title>" in response.text


def test_api_info(client):
    response = client.get("/api/info")
    assert response.status_code == 200
    assert response.json()["status"] == "running"


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["ai_configured"] is False  # ключ не задан в тестах


def test_contact_success_with_ai_fallback(client):
    response = client.post("/api/contact", json=VALID_PAYLOAD)
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "received"
    assert data["analysis"]["sentiment"] in {"positive", "neutral", "negative"}
    assert data["analysis"]["request_type"] in {"question", "complaint", "feedback", "proposal", "other"}
    assert data["analysis"]["ai_used"] is False  # fallback, т.к. нет ключа


def test_contact_invalid_email(client):
    payload = dict(VALID_PAYLOAD, email="not-an-email")
    response = client.post("/api/contact", json=payload)
    assert response.status_code == 422
    assert response.json()["error"] == "validation_error"


def test_contact_invalid_phone(client):
    payload = dict(VALID_PAYLOAD, phone="abc")
    response = client.post("/api/contact", json=payload)
    assert response.status_code == 422


def test_contact_short_comment(client):
    payload = dict(VALID_PAYLOAD, comment="ok")
    response = client.post("/api/contact", json=payload)
    assert response.status_code == 422


def test_contact_missing_fields(client):
    response = client.post("/api/contact", json={"name": "Иван"})
    assert response.status_code == 422


def test_rate_limiting(client):
    for _ in range(3):
        response = client.post("/api/contact", json=VALID_PAYLOAD)
        assert response.status_code == 201

    response = client.post("/api/contact", json=VALID_PAYLOAD)
    assert response.status_code == 429
    assert response.json()["error"] == "rate_limit_exceeded"


def test_metrics_reflect_contact(client):
    client.post("/api/contact", json=VALID_PAYLOAD)
    response = client.get("/api/metrics")
    assert response.status_code == 200
    data = response.json()
    assert data["total_received"] >= 1
    assert data["ai_fallback_count"] >= 1
