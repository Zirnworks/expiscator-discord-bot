"""User identity mapping for Discord messages."""

import json
from pathlib import Path

from .config import USER_MAP_PATH


class UserMapper:
    """Maps Discord user IDs to display labels.

    Zirn -> "Zirn", everyone else -> their Discord display name.
    """

    def __init__(self, zirn_user_id: str, map_path: Path = USER_MAP_PATH):
        self.zirn_user_id = zirn_user_id
        self.map_path = map_path
        self._mappings: dict[str, dict] = {}
        self._load()

    def _load(self):
        if self.map_path.exists():
            with open(self.map_path) as f:
                data = json.load(f)
            self._mappings = data.get("mappings", {})

    def save(self):
        data = {
            "zirn_user_id": self.zirn_user_id,
            "mappings": self._mappings,
        }
        with open(self.map_path, "w") as f:
            json.dump(data, f, indent=2)

    def get_label(self, user_id: str, username: str = "") -> str:
        """Get the display label for a user ID.

        Zirn -> "Zirn", everyone else -> their Discord username.
        """
        if user_id == self.zirn_user_id:
            return "Zirn"

        if user_id not in self._mappings:
            self._mappings[user_id] = {"label": username or f"user_{user_id[:8]}"}

        # Update label if we now have a better username than before
        if username and self._mappings[user_id]["label"].startswith("user_"):
            self._mappings[user_id]["label"] = username

        return self._mappings[user_id]["label"]

    def get_role(self, user_id: str) -> str:
        """Get the training role for a user ID.

        Zirn -> "assistant", everyone else -> "user".
        """
        if user_id == self.zirn_user_id:
            return "assistant"
        return "user"
