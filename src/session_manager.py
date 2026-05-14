import json
import os
from datetime import datetime

class SessionManager:
    def __init__(self, storage_path="data/session_history.json"):
        self.storage_path = storage_path
        self._ensure_dir()
        self.history = self._load_history()

    def _ensure_dir(self):
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)

    def _load_history(self):
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return []
        return []

    def _save_history(self):
        try:
            with open(self.storage_path, 'w') as f:
                json.dump(self.history, f, indent=4)
        except IOError:
            pass

    def add_record(self, release_id, artist, title, year, price, available, verdict, reason, media_condition="Near Mint", sleeve_condition="Near Mint"):
        record = {
            "timestamp": datetime.now().isoformat(),
            "release_id": int(release_id),
            "artist": artist,
            "title": title,
            "year": year,
            "price": float(price),
            "available": int(available),
            "verdict": verdict,
            "reason": reason,
            "media_condition": media_condition,
            "sleeve_condition": sleeve_condition,
            "comments_accept_offer": "N",
            "location": "",
            "external_id": ""
        }
        self.history.append(record)
        self._save_history()
        return record

    def get_all_records(self):
        return self.history

    def clear_history(self):
        self.history = []
        self._save_history()
