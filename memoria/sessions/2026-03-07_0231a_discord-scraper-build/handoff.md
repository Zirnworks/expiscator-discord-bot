# Handoff — Discord Scraper Session 1

## What Happened

Built and deployed a Discord server scraper. First server successfully extracted — a game dev server with 16 text channels, ~7k messages, ~700 attachments.

## Current State

- **Code**: fully working, pushed to https://github.com/Zirnworks/expiscator-discord-bot
- **Data**: at `/Users/zirn/Data/Expiscator/discord-data/` (NOT in the repo — gitignored)
- **Config**: at `/Users/zirn/Documents/Vault/Agents/Expiscator/config.json` (contains bot token — gitignored)
- **Output**: 15 channels processed into Markdown + JSONL in `data/processed/`

## Key Files

- `src/main.py` — CLI: `python3 -m src.main [run|extract|process|status]`
- `src/config.py` — DATA_DIR hardcoded to `/Users/zirn/Data/Expiscator/discord-data`
- `src/client.py` — Discord REST client, urllib only, 30s timeout, 3 retries
- `src/anonymizer.py` — UserMapper class (despite filename, no longer anonymizes — uses real display names)

## What's Next / Pending

1. **DM extraction** — Zirn wants DMs too, but that requires user token (against ToS). Deferred.
2. **"notes" channel** — times out on every attempt. Likely a permissions issue on that specific channel. Zirn should check bot permissions for it.
3. **More servers** — Zirn has 5-20 channels total across multiple servers. Only one server done so far. Add more guild_ids to config.json `servers` array.
4. **Training data chunking** — current segmentation splits on 30min gaps / 20 turns. May need tuning for actual finetuning use.

## Gotchas

- Python 3.9 on this system — need `from __future__ import annotations` for `X | Y` type syntax
- `rm` is aliased to `trash` on this system — no `-f` flag support
- The `process` command alone doesn't know channel labels (only IDs) — use `run` to get proper filenames
- Zirn prefers compact Markdown formatting — no extra blank lines between sections
- Zirn wants real display names, not anonymized labels
