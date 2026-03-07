"""Configuration loading and validation for Expiscator."""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
CONFIG_PATH = PROJECT_ROOT / "config.json"
DATA_DIR = Path("/Users/zirn/Data/Expiscator/discord-data")
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
ATTACHMENTS_DIR = DATA_DIR / "attachments"
STATE_PATH = DATA_DIR / "state.json"
USER_MAP_PATH = DATA_DIR / "user_map.json"


@dataclass
class ChannelConfig:
    channel_id: str
    label: str
    enabled: bool = True


@dataclass
class Options:
    download_attachments: bool = False
    skip_bot_messages: bool = True
    skip_system_messages: bool = True
    max_attachment_size_mb: int = 25
    request_delay_seconds: float = 0.5
    merge_window_seconds: int = 300
    conversation_gap_minutes: int = 30
    max_turns_per_segment: int = 20


@dataclass
class ServerConfig:
    guild_id: str
    label: str
    enabled: bool = True


@dataclass
class Config:
    bot_token: str
    zirn_user_id: str
    channels: list = field(default_factory=list)
    servers: list = field(default_factory=list)
    options: Options = field(default_factory=Options)


def load_config() -> Config:
    """Load and validate configuration from config.json and environment."""
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(
            f"Config file not found: {CONFIG_PATH}\n"
            "Copy config.example.json to config.json and fill in your values."
        )

    with open(CONFIG_PATH) as f:
        raw = json.load(f)

    # Bot token: env var takes precedence
    bot_token = os.environ.get("EXPISCATOR_BOT_TOKEN", raw.get("bot_token", ""))
    if not bot_token or bot_token == "YOUR_BOT_TOKEN":
        raise ValueError(
            "Bot token not configured. Set EXPISCATOR_BOT_TOKEN env var "
            "or add bot_token to config.json."
        )

    zirn_user_id = raw.get("zirn_user_id", "")
    if not zirn_user_id:
        raise ValueError("zirn_user_id is required in config.json.")

    # Parse individual channels
    channels = []
    for ch in raw.get("channels", []):
        channels.append(ChannelConfig(
            channel_id=ch["channel_id"],
            label=ch.get("label", ch["channel_id"]),
            enabled=ch.get("enabled", True),
        ))

    # Parse servers (all text channels will be auto-discovered at runtime)
    servers = []
    for srv in raw.get("servers", []):
        servers.append(ServerConfig(
            guild_id=srv["guild_id"],
            label=srv.get("label", srv["guild_id"]),
            enabled=srv.get("enabled", True),
        ))

    if not channels and not servers:
        raise ValueError(
            "At least one channel or server is required in config.json."
        )

    # Parse options
    opts_raw = raw.get("options", {})
    options = Options(
        download_attachments=opts_raw.get("download_attachments", False),
        skip_bot_messages=opts_raw.get("skip_bot_messages", True),
        skip_system_messages=opts_raw.get("skip_system_messages", True),
        max_attachment_size_mb=opts_raw.get("max_attachment_size_mb", 25),
        request_delay_seconds=opts_raw.get("request_delay_seconds", 0.5),
        merge_window_seconds=opts_raw.get("merge_window_seconds", 300),
        conversation_gap_minutes=opts_raw.get("conversation_gap_minutes", 30),
        max_turns_per_segment=opts_raw.get("max_turns_per_segment", 20),
    )

    # Ensure data directories exist
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    ATTACHMENTS_DIR.mkdir(parents=True, exist_ok=True)

    return Config(
        bot_token=bot_token,
        zirn_user_id=zirn_user_id,
        channels=channels,
        servers=servers,
        options=options,
    )
