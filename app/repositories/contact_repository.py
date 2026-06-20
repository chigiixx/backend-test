"""
Repository-слой: всё, что касается хранения обращений в файловой системе,
изолировано здесь. Сервисный слой не знает, что данные лежат в JSON-файле —
завтра это можно заменить на БД, поменяв только этот класс.
"""
import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

from app.config import get_settings

_lock = threading.Lock()


class ContactRepository:
    def __init__(self):
        settings = get_settings()
        self.storage_path = Path(settings.data_dir) / "storage" / "contacts.json"
        self._ensure_storage()

    def _ensure_storage(self) -> None:
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.storage_path.exists():
            self.storage_path.write_text("[]", encoding="utf-8")

    def save(
        self,
        name: str,
        phone: str,
        email: str,
        comment: str,
        analysis: dict,
        owner_email_sent: bool,
        user_email_sent: bool,
    ) -> Dict:
        record = {
            "id": str(uuid.uuid4()),
            "name": name,
            "phone": phone,
            "email": email,
            "comment": comment,
            "analysis": analysis,
            "owner_email_sent": owner_email_sent,
            "user_email_sent": user_email_sent,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        with _lock:
            data = self._read()
            data.append(record)
            self._write(data)
        return record

    def all(self) -> List[Dict]:
        with _lock:
            return self._read()

    def _read(self) -> List[Dict]:
        try:
            return json.loads(self.storage_path.read_text(encoding="utf-8") or "[]")
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def _write(self, data: List[Dict]) -> None:
        self._ensure_storage()
        self.storage_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
