"""Download Discord message attachments to local storage."""

from __future__ import annotations

import logging
import urllib.request
import urllib.error
from pathlib import Path

from .config import ATTACHMENTS_DIR

logger = logging.getLogger("expiscator.downloader")


def download_attachment(url: str, channel_id: str, message_id: str, filename: str,
                        max_size_mb: int = 25) -> Path | None:
    """Download a single attachment and return the local path.

    Files are stored as: data/attachments/{channel_id}/{message_id}_{filename}
    Skips if already downloaded. Returns None on failure.
    """
    channel_dir = ATTACHMENTS_DIR / channel_id
    channel_dir.mkdir(parents=True, exist_ok=True)

    local_path = channel_dir / f"{message_id}_{filename}"

    # Skip if already downloaded
    if local_path.exists():
        return local_path

    try:
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "Expiscator/1.0")

        with urllib.request.urlopen(req) as resp:
            # Check size before downloading
            content_length = resp.headers.get("Content-Length")
            if content_length and int(content_length) > max_size_mb * 1024 * 1024:
                logger.warning("Skipping %s — too large (%s bytes)", filename, content_length)
                return None

            with open(local_path, "wb") as f:
                f.write(resp.read())

        logger.debug("Downloaded: %s", local_path)
        return local_path

    except (urllib.error.URLError, urllib.error.HTTPError, OSError) as e:
        logger.warning("Failed to download %s: %s", filename, e)
        return None


def download_turn_attachments(turn_attachments: list, channel_id: str,
                               message_ids: list, max_size_mb: int = 25) -> dict:
    """Download all attachments for a turn.

    Returns a dict mapping attachment URLs to local file paths.
    """
    url_to_path = {}

    for att in turn_attachments:
        url = att.get("url", "")
        filename = att.get("filename", "file")
        # Use the first message ID as the anchor
        msg_id = message_ids[0] if message_ids else "unknown"

        local_path = download_attachment(url, channel_id, msg_id, filename, max_size_mb)
        if local_path:
            url_to_path[url] = local_path

    return url_to_path
