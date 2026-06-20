"""
Файловый rate limiter (fixed-ish sliding window per IP).

Реализован через JSON-файл, как и допускает задание ("можно реализовать
через файловое кеширование"). Для продакшена с несколькими воркерами
лучше Redis, но для демонстрации подхода и единственного процесса
файловой блокировки (threading.Lock) достаточно.
"""
import json
import threading
import time
from pathlib import Path
from typing import Dict, List

from app.config import get_settings
from app.core.exceptions import RateLimitExceededException

_lock = threading.Lock()


class RateLimiter:
    def __init__(self):
        settings = get_settings()
        self.max_requests = settings.rate_limit_max_requests
        self.window_seconds = settings.rate_limit_window_seconds
        self.storage_path = Path(settings.data_dir) / "storage" / "rate_limit.json"
        self._ensure_storage()

    def _ensure_storage(self) -> None:
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.storage_path.exists():
            self.storage_path.write_text("{}", encoding="utf-8")

    def _read(self) -> Dict[str, List[float]]:
        try:
            return json.loads(self.storage_path.read_text(encoding="utf-8") or "{}")
        except (json.JSONDecodeError, FileNotFoundError):
            return {}

    def _write(self, data: Dict[str, List[float]]) -> None:
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.storage_path.write_text(json.dumps(data), encoding="utf-8")

    def check(self, identifier: str) -> None:
        """Бросает RateLimitExceededException, если identifier превысил лимит."""
        now = time.time()
        with _lock:
            data = self._read()
            timestamps = [t for t in data.get(identifier, []) if now - t < self.window_seconds]

            if len(timestamps) >= self.max_requests:
                retry_after = max(int(self.window_seconds - (now - timestamps[0])), 1)
                data[identifier] = timestamps
                self._write(data)
                raise RateLimitExceededException(
                    detail=f"Слишком много запросов. Попробуйте снова через {retry_after} сек.",
                )

            timestamps.append(now)
            data[identifier] = timestamps
            self._write(data)
