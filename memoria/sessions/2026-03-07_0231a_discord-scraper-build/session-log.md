# Session Log: Discord Server Scraper — Build & First Run

**Start:** 2026-03-06 17:32 PST
**End:** 2026-03-07 02:27 PST
**Context Used:** ~76%

## Summary

First session. Built a complete Discord server scraper pipeline for extracting two-sided conversations for LLM finetuning. Went from zero code to a working tool that extracted 7,000+ messages and 700+ attachments from Zirn's game dev Discord server, outputting Obsidian-compatible Markdown with inline images and JSONL training data.

## Key Accomplishments

- Designed and built 7-module Python pipeline: config, client, extractor, anonymizer, merger, formatter, main
- Bot-based approach (Discord ToS compliant) using only stdlib (urllib, no external deps)
- Server-level auto-discovery — specify a guild ID, bot finds all text channels
- Crash-safe resume via state.json — can interrupt and continue
- Switched from anonymous [USER_N] labels to real Discord display names per Zirn's request
- Added attachment downloading with 30s timeout and retry logic
- Obsidian-compatible Markdown output with 400x300 inline image thumbnails
- Compact formatting matching Zirn's preferred style
- Successfully extracted 16 channels (1 inaccessible — "notes" channel, likely permissions)
- Moved data directory to /Users/zirn/Data/Expiscator/discord-data
- Pushed all code to https://github.com/Zirnworks/expiscator-discord-bot

## Files Created / Modified / Removed

- `src/__init__.py` — package marker
- `src/config.py` — config loading, validation, data paths
- `src/client.py` — Discord REST client with rate limiting, timeout, retry
- `src/extractor.py` — paginated message fetching with resume
- `src/anonymizer.py` — UserMapper (display names, role assignment)
- `src/merger.py` — consecutive message merging, conversation segmentation
- `src/formatter.py` — JSONL + Obsidian Markdown output
- `src/downloader.py` — attachment downloading with timeout
- `src/main.py` — CLI entry point (extract/process/status/run)
- `config.example.json` — template config
- `.gitignore` — added data/ and config.json
- `memoria/MEMORY.md` — created agent memory file

## Commits Made

- `b5b364a` — Add Discord server scraper pipeline for conversation extraction
- `0265a9b` — Use real Discord display names instead of anonymous [USER_N] labels
- `3d63c4b` — Add server-level config to auto-discover all text channels
- `345d646` — Add attachment downloading and Obsidian-compatible Markdown output
- `0426c87` — Fix hanging requests, add timeouts and retry logic
- `523d229` — Move data dir, compact Markdown, drop server prefix from filenames

## Open Threads

- `my-server/notes` channel times out consistently — bot likely lacks permission for that specific channel
- DM extraction not yet built (planned for later — requires user token approach)
- Conversation chunking/windowing for training not yet implemented (raw segmentation exists)
- `Discord Shipper - ID Stuff.md` untracked file in repo root — unclear origin, not touched
