"""
Repository для агрегированной статистики (GET /api/metrics).

Счётчики обновляются инкрементально при каждом обращении, поэтому
эндпоинт остаётся быстрым даже при большом количестве записей —
не нужно пересчитывать всё из contacts.json на каждый запрос.
"""
import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict

from app.config import get_settings

_lock = threading.Lock()

_DEFAULT_METRICS = {
    "total_received": 0,
    "total_rate_limited": 0,
    "by_sentiment": {"positive": 0, "neutral": 0, "negative": 0},
    "by_request_type": {"question": 0, "complaint": 0, "feedback": 0, "proposal": 0, "other": 0},
    "ai_used_count": 0,
    "ai_fallback_count": 0,
    "last_updated": None,
}


class MetricsRepository:
    def __init__(self):
        settings = get_settings()
        self.storage_path = Path(settings.data_dir) / "storage" / "metrics.json"
        self._ensure_storage()

    def _ensure_storage(self) -> None:
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.storage_path.exists():
            self._write(json.loads(json.dumps(_DEFAULT_METRICS)))

    def _read(self) -> Dict:
        try:
            data = json.loads(self.storage_path.read_text(encoding="utf-8") or "{}")
            merged = json.loads(json.dumps(_DEFAULT_METRICS))
            merged.update(data)
            return merged
        except (json.JSONDecodeError, FileNotFoundError):
            return json.loads(json.dumps(_DEFAULT_METRICS))

    def _write(self, data: Dict) -> None:
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.storage_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def record_contact(self, analysis: dict) -> None:
        with _lock:
            data = self._read()
            data["total_received"] += 1
            data["by_sentiment"][analysis["sentiment"]] = data["by_sentiment"].get(analysis["sentiment"], 0) + 1
            data["by_request_type"][analysis["request_type"]] = (
                data["by_request_type"].get(analysis["request_type"], 0) + 1
            )
            if analysis["ai_used"]:
                data["ai_used_count"] += 1
            else:
                data["ai_fallback_count"] += 1
            data["last_updated"] = datetime.now(timezone.utc).isoformat()
            self._write(data)

    def record_rate_limited(self) -> None:
        with _lock:
            data = self._read()
            data["total_rate_limited"] += 1
            data["last_updated"] = datetime.now(timezone.utc).isoformat()
            self._write(data)

    def get(self) -> Dict:
        with _lock:
            return self._read()
