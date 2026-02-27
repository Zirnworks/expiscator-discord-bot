"""Merge consecutive messages into turns and segment into conversations."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


# Discord message types that contain conversational content
CONTENT_TYPES = {0, 19}  # 0=DEFAULT, 19=REPLY


@dataclass
class Turn:
    author_id: str
    author_name: str
    content: str
    timestamp_start: str
    timestamp_end: str
    message_ids: list = field(default_factory=list)
    attachments: list = field(default_factory=list)
    embeds: list = field(default_factory=list)
    is_reply: bool = False
    reply_to_message_id: str = ""


def _parse_timestamp(ts: str) -> datetime:
    """Parse an ISO 8601 timestamp from the Discord API."""
    # Discord uses formats like 2025-06-15T14:30:00.000000+00:00
    # Strip sub-second precision for compatibility with Python 3.9
    if "." in ts:
        base, rest = ts.split(".", 1)
        # Find timezone offset
        for sep in ("+", "-"):
            if sep in rest[1:]:  # skip first char (could be part of fractional)
                idx = rest.index(sep, 1)
                tz_part = rest[idx:]
                ts = base + tz_part
                break
        else:
            ts = base + "+00:00"
    return datetime.fromisoformat(ts)


def _simplify_embeds(embeds: list) -> list:
    """Extract just the useful fields from embed objects."""
    simplified = []
    for embed in embeds:
        # Skip auto-generated link previews (they have 'url' matching a URL in content)
        if embed.get("type") == "rich" or embed.get("title"):
            simplified.append({
                "title": embed.get("title", ""),
                "description": embed.get("description", ""),
                "url": embed.get("url", ""),
            })
    return simplified


def merge_messages(
    messages: list,
    merge_window_seconds: int = 300,
    skip_bots: bool = True,
    skip_system: bool = True,
) -> list:
    """Merge consecutive same-author messages into turns.

    Args:
        messages: Raw API message dicts, sorted oldest-first.
        merge_window_seconds: Max gap between consecutive messages to merge.
        skip_bots: Filter out bot messages.
        skip_system: Filter out system messages (joins, pins, etc.).

    Returns:
        List of Turn objects.
    """
    turns = []
    current: Turn | None = None
    current_ts: datetime | None = None

    for msg in messages:
        msg_type = msg.get("type", 0)

        # Filter
        if skip_system and msg_type not in CONTENT_TYPES:
            continue
        if skip_bots and msg.get("author", {}).get("bot", False):
            continue

        # Skip truly empty messages (no content, no attachments, no embeds)
        content = msg.get("content", "")
        attachments = msg.get("attachments", [])
        embeds = msg.get("embeds", [])
        if not content and not attachments and not embeds:
            continue

        author_id = msg["author"]["id"]
        timestamp = _parse_timestamp(msg["timestamp"])

        should_merge = (
            current is not None
            and current.author_id == author_id
            and current_ts is not None
            and (timestamp - current_ts).total_seconds() <= merge_window_seconds
            and msg_type != 19  # replies always start a new turn
        )

        if should_merge:
            if content:
                current.content += "\n" + content if current.content else content
            current.timestamp_end = msg["timestamp"]
            current.message_ids.append(msg["id"])
            current.attachments.extend(attachments)
            current.embeds.extend(_simplify_embeds(embeds))
            current_ts = timestamp
        else:
            if current is not None:
                turns.append(current)

            current = Turn(
                author_id=author_id,
                author_name=msg["author"].get("username", "unknown"),
                content=content,
                timestamp_start=msg["timestamp"],
                timestamp_end=msg["timestamp"],
                message_ids=[msg["id"]],
                attachments=list(attachments),
                embeds=_simplify_embeds(embeds),
                is_reply=(msg_type == 19),
                reply_to_message_id=(
                    msg.get("message_reference", {}).get("message_id", "")
                    if msg_type == 19 else ""
                ),
            )
            current_ts = timestamp

    if current is not None:
        turns.append(current)

    return turns


def segment_conversations(
    turns: list,
    gap_minutes: int = 30,
    max_turns: int = 20,
) -> list:
    """Split a list of turns into conversation segments.

    A new segment starts when:
    - The gap between consecutive turns exceeds gap_minutes
    - The current segment reaches max_turns

    Returns:
        List of lists of Turn objects.
    """
    if not turns:
        return []

    segments = []
    current_segment = [turns[0]]
    prev_ts = _parse_timestamp(turns[0].timestamp_end)

    for turn in turns[1:]:
        turn_ts = _parse_timestamp(turn.timestamp_start)
        gap_seconds = (turn_ts - prev_ts).total_seconds()

        if gap_seconds > gap_minutes * 60 or len(current_segment) >= max_turns:
            segments.append(current_segment)
            current_segment = []

        current_segment.append(turn)
        prev_ts = _parse_timestamp(turn.timestamp_end)

    if current_segment:
        segments.append(current_segment)

    return segments
