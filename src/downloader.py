"""Download Discord message attachments to local storage."""

from __future__ import annotations

import logging
import urllib.request
import urllib.error
from pathlib import Path

from .config import ATTACHMENTS_DIR

logger = logging.getLogger("expiscator.downloader")


def _find_channel_dir(channel_id: str, channel_name: str = "") -> Path:
    """Find or create the attachment directory for a channel.

    Uses channelname_channelid format. Falls back to just channelid.
    """
    # Check for existing folder with this channel ID suffix
    for existing in ATTACHMENTS_DIR.iterdir():
        if existing.is_dir() and existing.name.endswith(channel_id):
            return existing

    # Create new folder
    if channel_name:
        dirname = f"{channel_name}_{channel_id}"
    else:
        dirname = channel_id
    channel_dir = ATTACHMENTS_DIR / dirname
    channel_dir.mkdir(parents=True, exist_ok=True)
    return channel_dir


def download_attachment(url: str, channel_id: str, message_id: str, filename: str,
                        max_size_mb: int = 25, channel_name: str = "") -> Path | None:
    """Download a single attachment and return the local path.

    Files are stored as: data/attachments/{channelname_channelid}/{message_id}_{filename}
    Skips if already downloaded. Returns None on failure.
    """
    channel_dir = _find_channel_dir(channel_id, channel_name)
    channel_dir.mkdir(parents=True, exist_ok=True)

    local_path = channel_dir / f"{message_id}_{filename}"

    # Skip if already downloaded
    if local_path.exists():
        return local_path

    try:
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "Expiscator/1.0")

        with urllib.request.urlopen(req, timeout=30) as resp:
            # Check size before downloading
            content_length = resp.headers.get("Content-Length")
            if content_length and int(content_length) > max_size_mb * 1024 * 1024:
                logger.warning("Skipping %s — too large (%s bytes)", filename, content_length)
                return None

            with open(local_path, "wb") as f:
                f.write(resp.read())

        logger.info("  Downloaded: %s", filename)
        return local_path

    except (urllib.error.URLError, urllib.error.HTTPError, OSError) as e:
        logger.warning("Failed to download %s: %s", filename, e)
        return None


def download_turn_attachments(turn_attachments: list, channel_id: str,
                               message_ids: list, max_size_mb: int = 25,
                               channel_name: str = "") -> dict:
    """Download all attachments for a turn.

    Returns a dict mapping attachment URLs to local file paths.
    """
    url_to_path = {}

    for att in turn_attachments:
        url = att.get("url", "")
        filename = att.get("filename", "file")
        # Use the first message ID as the anchor
        msg_id = message_ids[0] if message_ids else "unknown"

        local_path = download_attachment(url, channel_id, msg_id, filename, max_size_mb,
                                         channel_name=channel_name)
        if local_path:
            url_to_path[url] = local_path

    return url_to_path
