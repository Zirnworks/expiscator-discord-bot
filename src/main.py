"""CLI entry point for Expiscator Discord scraper."""

import logging
import sys

from .anonymizer import UserMapper
from .client import DiscordClient
from .config import ChannelConfig, PROCESSED_DIR, RAW_DIR, load_config
from .downloader import download_turn_attachments
from .extractor import extract_channel, get_extraction_status, load_raw_messages
from .formatter import format_jsonl, format_markdown
from .merger import merge_messages, segment_conversations

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("expiscator")


def _resolve_channels(config, client: DiscordClient) -> list:
    """Build the full channel list from explicit channels + server auto-discovery."""
    channels = [ch for ch in config.channels if ch.enabled]

    for server in config.servers:
        if not server.enabled:
            logger.info("Skipping disabled server: %s", server.label)
            continue

        logger.info("Discovering channels in server: %s", server.label)
        api_channels = client.get_guild_channels(server.guild_id)
        for ch in api_channels:
            channel_name = ch.get("name", ch["id"])
            label = f"{server.label}/{channel_name}"
            channels.append(ChannelConfig(
                channel_id=ch["id"],
                label=label,
                enabled=True,
            ))
            logger.info("  Found: %s", label)

    return channels


def cmd_extract(config):
    """Extract raw messages from Discord.

    Returns the resolved list of ChannelConfig objects (including server-discovered ones).
    """
    client = DiscordClient(config.bot_token, delay=config.options.request_delay_seconds)
    channels = _resolve_channels(config, client)
    results = []

    for channel in channels:
        logger.info("Extracting: %s", channel.label)
        result = extract_channel(client, channel)
        results.append(result)
        logger.info(
            "  %s: %s mode, %d new messages, %d total stored",
            result["channel"], result["mode"],
            result["new_messages"], result["total_stored"],
        )

    return channels


def cmd_process(config, channels=None):
    """Process raw messages into training JSONL and browsable Markdown.

    If channels is provided (e.g., from a prior extract), use that list.
    Otherwise, process all raw files found in data/raw/.
    """
    mapper = UserMapper(config.zirn_user_id)
    results = []

    if channels is None:
        # Build channel list from whatever raw data exists
        known = {ch.channel_id: ch for ch in config.channels}
        channels = []
        for raw_file in sorted(RAW_DIR.glob("*.jsonl")):
            ch_id = raw_file.stem
            if ch_id in known:
                channels.append(known[ch_id])
            else:
                # Server-discovered channel — use ID as label
                channels.append(ChannelConfig(channel_id=ch_id, label=ch_id))

    for channel in channels:
        logger.info("Processing: %s", channel.label)

        # Load raw messages (deduped, sorted oldest-first)
        messages = load_raw_messages(channel.channel_id)
        if not messages:
            logger.warning("  No raw data found for %s", channel.label)
            continue

        # Merge into turns
        turns = merge_messages(
            messages,
            merge_window_seconds=config.options.merge_window_seconds,
            skip_bots=config.options.skip_bot_messages,
            skip_system=config.options.skip_system_messages,
        )
        logger.info("  %d messages -> %d turns", len(messages), len(turns))

        # Segment into conversations
        segments = segment_conversations(
            turns,
            gap_minutes=config.options.conversation_gap_minutes,
            max_turns=config.options.max_turns_per_segment,
        )
        logger.info("  %d turns -> %d conversation segments", len(turns), len(segments))

        # Download attachments if enabled
        local_paths = {}
        if config.options.download_attachments:
            logger.info("  Downloading attachments...")
            for turn in turns:
                if turn.attachments:
                    paths = download_turn_attachments(
                        turn.attachments,
                        channel.channel_id,
                        turn.message_ids,
                        max_size_mb=config.options.max_attachment_size_mb,
                    )
                    local_paths.update(paths)
            logger.info("  Downloaded %d attachments", len(local_paths))

        # Generate safe filename from label
        safe_label = channel.label.replace("/", "_").replace(" ", "-")

        # Write JSONL
        jsonl_path = PROCESSED_DIR / f"{safe_label}.jsonl"
        format_jsonl(segments, channel.label, mapper, jsonl_path)
        logger.info("  Wrote %s", jsonl_path)

        # Write Markdown (with inline images for Obsidian)
        md_path = PROCESSED_DIR / f"{safe_label}.md"
        format_markdown(segments, channel.label, mapper, md_path, local_paths=local_paths)
        logger.info("  Wrote %s", md_path)

        results.append({
            "channel": channel.label,
            "messages": len(messages),
            "turns": len(turns),
            "segments": len(segments),
        })

    # Save user map
    mapper.save()
    logger.info("User map saved (%d users mapped)", len(mapper._mappings))

    return results


def cmd_status():
    """Show extraction status for all channels."""
    status = get_extraction_status()
    if not status:
        print("No channels extracted yet.")
        return

    print(f"{'Channel ID':<22} {'Messages':>10} {'Complete':>10} {'Last Run':<25}")
    print("-" * 70)
    for ch_id, info in status.items():
        print(
            f"{ch_id:<22} {info.get('total_fetched', 0):>10} "
            f"{'yes' if info.get('complete_history') else 'no':>10} "
            f"{info.get('last_run', 'never'):<25}"
        )


def main():
    command = sys.argv[1] if len(sys.argv) > 1 else "run"

    if command == "status":
        cmd_status()
        return

    config = load_config()

    if command == "extract":
        cmd_extract(config)
    elif command == "process":
        cmd_process(config)
    elif command == "run":
        channels = cmd_extract(config)
        cmd_process(config, channels=channels)
    else:
        print(f"Unknown command: {command}")
        print("Usage: python3 -m src.main [extract|process|status|run]")
        sys.exit(1)

    print("\nDone.")


if __name__ == "__main__":
    main()
