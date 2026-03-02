"""Discord REST API client using only urllib (zero external dependencies)."""

from __future__ import annotations

import json
import logging
import time
import urllib.request
import urllib.error

logger = logging.getLogger("expiscator.client")

BASE_URL = "https://discord.com/api/v9"


class DiscordAPIError(Exception):
    def __init__(self, status: int, message: str):
        self.status = status
        super().__init__(f"HTTP {status}: {message}")


class DiscordClient:
    def __init__(self, bot_token: str, delay: float = 0.5):
        self.bot_token = bot_token
        self.delay = delay

    def _request(self, url: str) -> list | dict:
        """Make an authenticated GET request to the Discord API."""
        req = urllib.request.Request(url)
        req.add_header("Authorization", f"Bot {self.bot_token}")
        req.add_header("User-Agent", "Expiscator/1.0")

        try:
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                self._handle_rate_limit(resp.headers)
                return data
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            if e.code == 429:
                retry_info = json.loads(body)
                retry_after = retry_info.get("retry_after", 1.0)
                logger.warning("Rate limited. Sleeping %.1fs", retry_after)
                time.sleep(retry_after)
                return self._request(url)
            elif e.code == 403:
                raise DiscordAPIError(403, f"Forbidden — missing permissions for {url}")
            elif e.code == 404:
                raise DiscordAPIError(404, f"Not found: {url}")
            else:
                raise DiscordAPIError(e.code, body)

    def _handle_rate_limit(self, headers):
        """Sleep if approaching rate limit, otherwise apply politeness delay."""
        remaining = headers.get("X-RateLimit-Remaining")
        if remaining is not None and int(remaining) <= 1:
            reset_after = float(headers.get("X-RateLimit-Reset-After", 1.0))
            logger.info("Rate limit near. Sleeping %.1fs", reset_after)
            time.sleep(reset_after)
        else:
            time.sleep(self.delay)

    def get_messages(
        self,
        channel_id: str,
        before: str | None = None,
        after: str | None = None,
        limit: int = 100,
    ) -> list:
        """Fetch messages from a channel.

        Args:
            channel_id: The channel to fetch from.
            before: Get messages before this message ID (newest first).
            after: Get messages after this message ID (oldest first).
            limit: Max messages per request (1-100, default 100).

        Returns:
            List of message dicts from the Discord API.
        """
        url = f"{BASE_URL}/channels/{channel_id}/messages?limit={limit}"
        if before:
            url += f"&before={before}"
        if after:
            url += f"&after={after}"
        return self._request(url)

    def get_channel(self, channel_id: str) -> dict:
        """Fetch channel metadata."""
        return self._request(f"{BASE_URL}/channels/{channel_id}")

    def get_guild_channels(self, guild_id: str) -> list:
        """Fetch all channels in a server (guild).

        Returns only text channels (type 0) and announcement channels (type 5).
        """
        channels = self._request(f"{BASE_URL}/guilds/{guild_id}/channels")
        # Type 0 = text, 5 = announcement — both contain readable messages
        return [ch for ch in channels if ch.get("type") in (0, 5)]
