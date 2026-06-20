"""
AI-сервис: анализ тональности и типа обращения + черновик ответа.

Провайдер — OpenAI API (chat.completions, structured JSON output).
Если ключ не задан, библиотека не установлена, истёк таймаут или провайдер
вернул ошибку — сервис НЕ падает, а прозрачно переключается на
rule-based fallback (см. _analyze_fallback). Это и есть требуемый
"graceful fallback": клиент всегда получает ответ 201, просто поле
analysis.ai_used будет false.
"""
import json
import logging

from app.config import get_settings

logger = logging.getLogger(__name__)

POSITIVE_WORDS = {
    "спасибо", "отлично", "супер", "класс", "понравилось", "хорошо", "круто",
    "great", "good", "thanks", "thank", "love", "awesome", "excellent",
}
NEGATIVE_WORDS = {
    "плохо", "ужасно", "недоволен", "проблема", "ошибка", "разочарован", "обман",
    "bad", "terrible", "hate", "issue", "problem", "awful", "disappointed", "scam",
}

SYSTEM_PROMPT = (
    "Ты — ассистент, который анализирует обращения с формы обратной связи на сайте "
    "разработчика-фрилансера. Проанализируй комментарий пользователя и верни СТРОГО "
    "валидный JSON без какого-либо текста до или после, в формате:\n"
    '{"sentiment": "positive" | "neutral" | "negative", '
    '"request_type": "question" | "complaint" | "feedback" | "proposal" | "other", '
    '"suggested_reply": "короткий вежливый черновик ответа на русском языке, 1-2 предложения"}'
)


class AIService:
    """
    Инстанс лёгкий: openai-клиент создаётся один раз при наличии ключа.
    Используется и в /api/contact (анализ), и в /api/health (флаг ai_configured).
    """

    def __init__(self):
        settings = get_settings()
        self.settings = settings
        self.client = None

        if settings.ai_provider == "openai" and settings.openai_api_key:
            try:
                from openai import OpenAI

                self.client = OpenAI(api_key=settings.openai_api_key, timeout=settings.ai_timeout_seconds)
            except ImportError:
                logger.warning("Пакет 'openai' не установлен — будет использован fallback-анализ")

    def is_configured(self) -> bool:
        return self.client is not None

    def analyze(self, comment: str) -> dict:
        if self.client:
            try:
                return self._analyze_with_openai(comment)
            except Exception as exc:  # noqa: BLE001 — намеренно широкий catch для graceful fallback
                logger.warning(f"AI-провайдер недоступен ({exc.__class__.__name__}: {exc}); переключаюсь на fallback")
        else:
            logger.info("AI-сервис не сконфигурирован (нет OPENAI_API_KEY) — используется fallback-анализ")

        return self._analyze_fallback(comment)

    def _analyze_with_openai(self, comment: str) -> dict:
        response = self.client.chat.completions.create(
            model=self.settings.openai_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": comment},
            ],
            temperature=0.3,
            max_tokens=300,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content
        data = json.loads(content)

        sentiment = data.get("sentiment", "neutral")
        request_type = data.get("request_type", "other")
        suggested_reply = data.get(
            "suggested_reply", "Спасибо за обращение! Мы свяжемся с вами в ближайшее время."
        )

        if sentiment not in {"positive", "neutral", "negative"}:
            sentiment = "neutral"
        if request_type not in {"question", "complaint", "feedback", "proposal", "other"}:
            request_type = "other"

        return {
            "sentiment": sentiment,
            "request_type": request_type,
            "suggested_reply": suggested_reply,
            "ai_used": True,
        }

    def _analyze_fallback(self, comment: str) -> dict:
        """Простой rule-based анализ — используется при недоступности AI."""
        text = comment.lower()
        pos_score = sum(1 for w in POSITIVE_WORDS if w in text)
        neg_score = sum(1 for w in NEGATIVE_WORDS if w in text)

        if pos_score > neg_score:
            sentiment = "positive"
        elif neg_score > pos_score:
            sentiment = "negative"
        else:
            sentiment = "neutral"

        if "?" in comment:
            request_type = "question"
        elif neg_score > 0:
            request_type = "complaint"
        elif pos_score > 0:
            request_type = "feedback"
        else:
            request_type = "other"

        suggested_reply = "Спасибо за ваше обращение! Мы внимательно его изучим и свяжемся с вами в ближайшее время."

        return {
            "sentiment": sentiment,
            "request_type": request_type,
            "suggested_reply": suggested_reply,
            "ai_used": False,
        }
