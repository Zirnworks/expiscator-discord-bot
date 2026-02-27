"""Persistent user anonymization for Discord messages."""

import json
from pathlib import Path

from .config import USER_MAP_PATH


class Anonymizer:
    def __init__(self, zirn_user_id: str, map_path: Path = USER_MAP_PATH):
        self.zirn_user_id = zirn_user_id
        self.map_path = map_path
        self._next_index = 1
        self._mappings: dict[str, dict] = {}
        self._load()

    def _load(self):
        if self.map_path.exists():
            with open(self.map_path) as f:
                data = json.load(f)
            self._next_index = data.get("next_index", 1)
            self._mappings = data.get("mappings", {})

    def save(self):
        data = {
            "zirn_user_id": self.zirn_user_id,
            "next_index": self._next_index,
            "mappings": self._mappings,
        }
        with open(self.map_path, "w") as f:
            json.dump(data, f, indent=2)

    def get_label(self, user_id: str, username: str = "") -> str:
        """Get the anonymized label for a user ID.

        Zirn -> "Zirn", everyone else -> "[USER_N]".
        """
        if user_id == self.zirn_user_id:
            return "Zirn"

        if user_id not in self._mappings:
            label = f"[USER_{self._next_index}]"
            self._mappings[user_id] = {"label": label, "username": username}
            self._next_index += 1

        return self._mappings[user_id]["label"]

    def get_role(self, user_id: str) -> str:
        """Get the training role for a user ID.

        Zirn -> "assistant", everyone else -> "user".
        """
        if user_id == self.zirn_user_id:
            return "assistant"
        return "user"

    def anonymize_content(self, content: str) -> str:
        """Replace any known usernames in message content with their labels.

        Handles @mentions and plain username references.
        """
        for user_id, info in self._mappings.items():
            username = info.get("username", "")
            if username and username in content:
                content = content.replace(username, info["label"])
        return content
