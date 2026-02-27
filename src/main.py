"""CLI entry point for Expiscator Discord scraper."""

import logging
import sys

from .anonymizer import Anonymizer
from .client import DiscordClient
from .config import PROCESSED_DIR, load_config
from .extractor import extract_channel, get_extraction_status, load_raw_messages
from .formatter import format_jsonl, format_markdown
from .merger import merge_messages, segment_conversations

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("expiscator")


def cmd_extract(config):
    """Extract raw messages from Discord."""
    client = DiscordClient(config.bot_token, delay=config.options.request_delay_seconds)
    results = []

    for channel in config.channels:
        if not channel.enabled:
            logger.info("Skipping disabled channel: %s", channel.label)
            continue

        logger.info("Extracting: %s", channel.label)
        result = extract_channel(client, channel)
        results.append(result)
        logger.info(
            "  %s: %s mode, %d new messages, %d total stored",
            result["channel"], result["mode"],
            result["new_messages"], result["total_stored"],
        )

    return results


def cmd_process(config):
    """Process raw messages into training JSONL and browsable Markdown."""
    anonymizer = Anonymizer(config.zirn_user_id)
    results = []

    for channel in config.channels:
        if not channel.enabled:
            continue

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

        # Generate safe filename from label
        safe_label = channel.label.replace("/", "_").replace(" ", "-")

        # Write JSONL
        jsonl_path = PROCESSED_DIR / f"{safe_label}.jsonl"
        format_jsonl(segments, channel.label, anonymizer, jsonl_path)
        logger.info("  Wrote %s", jsonl_path)

        # Write Markdown
        md_path = PROCESSED_DIR / f"{safe_label}.md"
        format_markdown(segments, channel.label, anonymizer, md_path)
        logger.info("  Wrote %s", md_path)

        results.append({
            "channel": channel.label,
            "messages": len(messages),
            "turns": len(turns),
            "segments": len(segments),
        })

    # Save anonymizer state
    anonymizer.save()
    logger.info("Anonymization map saved (%d users mapped)", anonymizer._next_index - 1)

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
        cmd_extract(config)
        cmd_process(config)
    else:
        print(f"Unknown command: {command}")
        print("Usage: python3 -m src.main [extract|process|status|run]")
        sys.exit(1)

    print("\nDone.")


if __name__ == "__main__":
    main()
