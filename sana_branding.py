"""Central SANA branding configuration loader.

Import-safe, stdlib-only module that exposes SANA product identity, developer
attribution, and theme constants from ``branding/sana.config.json`` with
built-in fallbacks so CLI, TUI, web, and gateway surfaces share one source of
truth without duplicating hardcoded strings.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

_DEFAULT_CONFIG: dict[str, Any] = {
    "productName": "SANA",
    "fullName": "SANA",
    "tagline": "SANA — Your Intelligent AI Assistant",
    "shortTagline": "Your Intelligent AI Assistant",
    "developer": "Q8iDevAI",
    "attribution": "Developed by Q8iDevAI",
    "upstreamAttribution": "Based on Hermes Agent by Nous Research. Customized and maintained by Q8iDevAI.",
    "upstream": {
        "name": "Hermes Agent",
        "organization": "Nous Research",
        "repository": "https://github.com/NousResearch/hermes-agent",
        "gitUrl": "https://github.com/NousResearch/hermes-agent.git",
        "remoteName": "upstream",
        "license": "MIT",
    },
    "cli": {
        "command": "sana",
        "acpCommand": "sana-acp",
        "legacyAliases": ["hermes", "hermes-agent", "hermes-acp"],
        "homeEnvVar": "SANA_HOME",
        "legacyHomeEnvVar": "HERMES_HOME",
        "dataDirName": "sana",
        "legacyDataDirName": "hermes",
        "promptSymbol": "❯",
        "emblem": "✦",
    },
    "theme": {
        "black": "#0B0B0F",
        "gold": "#D4AF37",
        "goldBright": "#E8C967",
        "goldDim": "#9E8022",
        "darkSecondary": "#17171C",
        "white": "#FFFFFF",
        "mutedText": "#9CA3AF",
    },
}


@lru_cache(maxsize=1)
def get_branding_config() -> dict[str, Any]:
    """Load ``branding/sana.config.json`` merged onto safe built-in defaults."""
    config_path = Path(__file__).resolve().parent / "branding" / "sana.config.json"
    merged = dict(_DEFAULT_CONFIG)
    if config_path.is_file():
        try:
            loaded = json.loads(config_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                for key, val in loaded.items():
                    if isinstance(val, dict) and isinstance(merged.get(key), dict):
                        merged[key] = {**merged[key], **val}
                    else:
                        merged[key] = val
        except (OSError, ValueError):
            pass
    return merged


PRODUCT_NAME: str = str(get_branding_config()["productName"])
TAGLINE: str = str(get_branding_config()["tagline"])
SHORT_TAGLINE: str = str(get_branding_config()["shortTagline"])
DEVELOPER_NAME: str = str(get_branding_config()["developer"])
ATTRIBUTION: str = str(get_branding_config()["attribution"])
UPSTREAM_ATTRIBUTION: str = str(get_branding_config()["upstreamAttribution"])
CLI_COMMAND: str = str(get_branding_config()["cli"]["command"])
EMBLEM: str = str(get_branding_config()["cli"]["emblem"])
PROMPT_SYMBOL: str = str(get_branding_config()["cli"]["promptSymbol"])
THEME_COLORS: dict[str, str] = dict(get_branding_config()["theme"])
