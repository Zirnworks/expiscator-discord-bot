"""Format conversation segments into JSONL (training) and Markdown (Obsidian)."""

import json
from pathlib import Path

from .anonymizer import UserMapper
from .merger import Turn

# Image file extensions that Obsidian can render inline
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg"}


def _format_attachments_text(attachments: list) -> str:
    """Format attachments as plain text (for JSONL training data)."""
    parts = []
    for att in attachments:
        name = att.get("filename", "file")
        content_type = att.get("content_type", "unknown")
        parts.append(f"[attachment: {name} ({content_type})]")
    return "\n".join(parts)


def _format_attachments_obsidian(attachments: list, local_paths: dict,
                                  md_output_path: Path) -> str:
    """Format attachments as Obsidian-compatible Markdown.

    Images get inline embeds, other files get links.
    """
    parts = []
    for att in attachments:
        url = att.get("url", "")
        filename = att.get("filename", "file")
        local_path = local_paths.get(url)

        if local_path and local_path.exists():
            # Use relative path from the Markdown file to the attachment
            try:
                rel_path = local_path.relative_to(md_output_path.parent)
            except ValueError:
                # Different tree — use path relative to common ancestor
                rel_path = Path("..") / local_path.relative_to(md_output_path.parent.parent)

            suffix = local_path.suffix.lower()
            if suffix in IMAGE_EXTENSIONS:
                parts.append(f"![{filename}|400x300]({rel_path})")
            else:
                parts.append(f"[{filename}]({rel_path})")
        else:
            # No local file — fall back to text description
            content_type = att.get("content_type", "unknown")
            parts.append(f"[attachment: {filename} ({content_type})]")

    return "\n".join(parts)


def _format_embeds(embeds: list) -> str:
    """Format simplified embeds as inline text."""
    parts = []
    for emb in embeds:
        title = emb.get("title", "")
        url = emb.get("url", "")
        if title and url:
            parts.append(f"[embed: {title} - {url}]")
        elif title:
            parts.append(f"[embed: {title}]")
        elif url:
            parts.append(f"[embed: {url}]")
    return "\n".join(parts)


def _turn_content_text(turn: Turn) -> str:
    """Build plain text content for JSONL training data."""
    parts = []
    if turn.content:
        parts.append(turn.content)
    if turn.attachments:
        parts.append(_format_attachments_text(turn.attachments))
    if turn.embeds:
        parts.append(_format_embeds(turn.embeds))
    return "\n".join(parts)


def _turn_content_obsidian(turn: Turn, local_paths: dict, md_output_path: Path) -> str:
    """Build Obsidian Markdown content with inline images."""
    parts = []
    if turn.content:
        parts.append(turn.content)
    if turn.attachments:
        parts.append(_format_attachments_obsidian(turn.attachments, local_paths, md_output_path))
    if turn.embeds:
        parts.append(_format_embeds(turn.embeds))
    return "\n".join(parts)


def format_jsonl(
    segments: list,
    channel_label: str,
    mapper: UserMapper,
    output_path: Path,
):
    """Write conversation segments as training JSONL."""
    with open(output_path, "w") as f:
        for segment in segments:
            messages = []
            for turn in segment:
                role = mapper.get_role(turn.author_id)
                label = mapper.get_label(turn.author_id, turn.author_name)
                content = _turn_content_text(turn)

                # Prepend speaker name for non-Zirn users so model knows who's talking
                if role == "user":
                    content = f"{label}: {content}"

                messages.append({"role": role, "content": content})

            record = {
                "messages": messages,
                "metadata": {
                    "source": "discord",
                    "channel": channel_label,
                    "timestamp_start": segment[0].timestamp_start,
                    "timestamp_end": segment[-1].timestamp_end,
                    "turn_count": len(segment),
                    "message_count": sum(len(t.message_ids) for t in segment),
                },
            }
            f.write(json.dumps(record) + "\n")


def format_markdown(
    segments: list,
    channel_label: str,
    mapper: UserMapper,
    output_path: Path,
    local_paths: dict = None,
):
    """Write conversation segments as Obsidian-compatible Markdown with inline images."""
    if local_paths is None:
        local_paths = {}

    lines = [f"# {channel_label}\n"]

    current_date = None

    for segment in segments:
        # Date header
        seg_date = segment[0].timestamp_start[:10]  # YYYY-MM-DD
        if seg_date != current_date:
            current_date = seg_date
            lines.append(f"\n## {current_date}\n")

        # Time range header
        t_start = segment[0].timestamp_start[11:16]  # HH:MM
        t_end = segment[-1].timestamp_end[11:16]
        lines.append(f"\n### {t_start} - {t_end}\n")

        for turn in segment:
            label = mapper.get_label(turn.author_id, turn.author_name)
            time_str = turn.timestamp_start[11:16]
            content = _turn_content_obsidian(turn, local_paths, output_path)

            lines.append(f"**{label}** ({time_str}):")
            for line in content.split("\n"):
                lines.append(line)
            lines.append("")

        lines.append("---\n")

    with open(output_path, "w") as f:
        f.write("\n".join(lines))
