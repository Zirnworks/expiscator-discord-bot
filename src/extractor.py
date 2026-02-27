"""Paginated message extraction with crash-safe resume."""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from .client import DiscordClient
from .config import RAW_DIR, STATE_PATH, ChannelConfig

logger = logging.getLogger("expiscator.extractor")


def _load_state() -> dict:
    if STATE_PATH.exists():
        with open(STATE_PATH) as f:
            return json.load(f)
    return {"channels": {}}


def _save_state(state: dict):
    with open(STATE_PATH, "w") as f:
        json.dump(state, f, indent=2)


def _append_raw(channel_id: str, messages: list):
    """Append messages to the raw JSONL file for a channel."""
    path = RAW_DIR / f"{channel_id}.jsonl"
    with open(path, "a") as f:
        for msg in messages:
            f.write(json.dumps(msg) + "\n")


def extract_channel(client: DiscordClient, channel: ChannelConfig) -> dict:
    """Extract all messages from a channel, with resume support.

    Returns a summary dict with counts and status.
    """
    state = _load_state()
    ch_state = state.get("channels", {}).get(channel.channel_id, {})

    total_fetched = 0
    new_messages = 0

    if ch_state.get("complete_history"):
        # Subsequent run: fetch only new messages
        new_messages = _fetch_new(client, channel, ch_state, state)
        return {
            "channel": channel.label,
            "mode": "incremental",
            "new_messages": new_messages,
            "total_stored": ch_state.get("total_fetched", 0) + new_messages,
        }
    else:
        # First run or interrupted: paginate backward
        total_fetched = _fetch_full_history(client, channel, ch_state, state)
        return {
            "channel": channel.label,
            "mode": "full",
            "new_messages": total_fetched,
            "total_stored": total_fetched,
        }


def _fetch_full_history(
    client: DiscordClient,
    channel: ChannelConfig,
    ch_state: dict,
    state: dict,
) -> int:
    """Paginate backward from newest to oldest. Resume from oldest_id if interrupted."""
    cursor = ch_state.get("oldest_id")  # None on first run = start from newest
    total = ch_state.get("total_fetched", 0)
    newest_id = ch_state.get("newest_id")

    if cursor:
        logger.info(
            "Resuming %s from message %s (%d already fetched)",
            channel.label, cursor, total,
        )
    else:
        logger.info("Starting full extraction of %s", channel.label)

    while True:
        messages = client.get_messages(channel.channel_id, before=cursor)
        if not messages:
            break

        # API returns newest first; store as-is (we sort during processing)
        _append_raw(channel.channel_id, messages)

        # Track newest message (first page, first message)
        if newest_id is None:
            newest_id = messages[0]["id"]

        batch_size = len(messages)
        total += batch_size
        cursor = messages[-1]["id"]  # oldest in this batch

        # Update state after each page (crash-safe)
        state.setdefault("channels", {})[channel.channel_id] = {
            "oldest_id": cursor,
            "newest_id": newest_id,
            "total_fetched": total,
            "last_run": datetime.now(timezone.utc).isoformat(),
            "complete_history": False,
        }
        _save_state(state)

        logger.info("  %s: %d messages fetched (total: %d)", channel.label, batch_size, total)

        if batch_size < 100:
            break  # reached the beginning

    # Mark complete
    state["channels"][channel.channel_id]["complete_history"] = True
    _save_state(state)
    logger.info("Completed %s: %d messages total", channel.label, total)

    return total


def _fetch_new(
    client: DiscordClient,
    channel: ChannelConfig,
    ch_state: dict,
    state: dict,
) -> int:
    """Fetch messages newer than the last known newest_id using after= parameter."""
    after_id = ch_state["newest_id"]
    total_new = 0
    newest_id = after_id

    logger.info("Fetching new messages in %s (after %s)", channel.label, after_id)

    while True:
        # after= returns oldest first
        messages = client.get_messages(channel.channel_id, after=after_id)
        if not messages:
            break

        _append_raw(channel.channel_id, messages)

        batch_size = len(messages)
        total_new += batch_size

        # Messages are oldest-first with after=, so last is newest
        newest_id = messages[-1]["id"]
        after_id = newest_id  # next page starts after this

        logger.info("  %s: %d new messages (total new: %d)", channel.label, batch_size, total_new)

        if batch_size < 100:
            break

    # Update state
    ch_state["newest_id"] = newest_id
    ch_state["total_fetched"] = ch_state.get("total_fetched", 0) + total_new
    ch_state["last_run"] = datetime.now(timezone.utc).isoformat()
    state["channels"][channel.channel_id] = ch_state
    _save_state(state)

    logger.info("Incremental update for %s: %d new messages", channel.label, total_new)
    return total_new


def load_raw_messages(channel_id: str) -> list:
    """Load and deduplicate raw messages from a channel's JSONL file.

    Returns messages sorted chronologically (oldest first).
    """
    path = RAW_DIR / f"{channel_id}.jsonl"
    if not path.exists():
        return []

    seen_ids = set()
    messages = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            msg = json.loads(line)
            if msg["id"] not in seen_ids:
                seen_ids.add(msg["id"])
                messages.append(msg)

    # Sort by message ID (snowflake IDs are chronologically ordered)
    messages.sort(key=lambda m: int(m["id"]))
    return messages


def get_extraction_status() -> dict:
    """Get extraction status for all channels."""
    state = _load_state()
    return state.get("channels", {})
