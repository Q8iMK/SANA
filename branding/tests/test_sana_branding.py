"""Automated validation suite for SANA branding, assets, CLI, migration, and upstream readiness."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import sana_branding
from branding.scripts.apply_branding import run_apply_branding
from hermes_cli._parser import build_top_level_parser
from hermes_cli.migrate_hermes import (
    detect_hermes_installation,
    migrate_hermes_to_sana,
)
from hermes_cli.skin_engine import get_active_skin, load_skin


def test_central_branding_config():
    cfg = sana_branding.get_branding_config()
    assert cfg["productName"] == "SANA"
    assert cfg["developer"] == "Q8iDevAI"
    assert cfg["tagline"] == "SANA — Your Intelligent AI Assistant"
    assert cfg["theme"]["black"] == "#0B0B0F"
    assert cfg["theme"]["gold"] == "#D4AF37"
    assert cfg["theme"]["darkSecondary"] == "#17171C"
    assert cfg["theme"]["white"] == "#FFFFFF"


def test_apply_branding_check_passes():
    report = run_apply_branding(check=True, skip_assets=False)
    assert report.ok, f"Branding check failed: missing={report.missing}, conflicts={report.conflicts}"


def test_generated_assets_exist_and_valid_headers():
    expected = [
        REPO_ROOT / "assets" / "banner.png",
        REPO_ROOT / "assets" / "splash.png",
        REPO_ROOT / "assets" / "icon-master.svg",
        REPO_ROOT / "assets" / "icon-master-dark.svg",
        REPO_ROOT / "apps" / "desktop" / "assets" / "icon.ico",
        REPO_ROOT / "apps" / "desktop" / "assets" / "icon.icns",
        REPO_ROOT / "apps" / "desktop" / "assets" / "icon.png",
        REPO_ROOT / "apps" / "bootstrap-installer" / "src-tauri" / "icons" / "icon.ico",
        REPO_ROOT / "web" / "public" / "favicon.ico",
        REPO_ROOT / "web" / "public" / "favicon.svg",
    ]
    for path in expected:
        assert path.is_file() and path.stat().st_size > 0, f"Invalid asset: {path}"

    # Verify binary magic bytes for PNG, ICO, and ICNS
    assert (REPO_ROOT / "assets" / "banner.png").read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    assert (REPO_ROOT / "apps" / "desktop" / "assets" / "icon.ico").read_bytes()[:4] == b"\x00\x00\x01\x00"
    assert (REPO_ROOT / "apps" / "desktop" / "assets" / "icon.icns").read_bytes()[:4] == b"icns"


def test_desktop_web_installer_metadata():
    desktop_pkg = json.loads((REPO_ROOT / "apps" / "desktop" / "package.json").read_text(encoding="utf-8"))
    assert desktop_pkg["productName"] == "SANA"
    assert desktop_pkg["author"] == "Q8iDevAI"

    assert "<title>SANA</title>" in (REPO_ROOT / "apps" / "desktop" / "index.html").read_text(encoding="utf-8")
    assert "<title>SANA — Dashboard</title>" in (REPO_ROOT / "web" / "index.html").read_text(encoding="utf-8")
    assert "<title>SANA</title>" in (REPO_ROOT / "apps" / "bootstrap-installer" / "index.html").read_text(encoding="utf-8")

    tauri_conf = json.loads(
        (REPO_ROOT / "apps" / "bootstrap-installer" / "src-tauri" / "tauri.conf.json").read_text(encoding="utf-8")
    )
    assert tauri_conf["productName"] == "SANA"
    assert tauri_conf["identifier"] == "ai.q8idev.sana.setup"
    assert tauri_conf["bundle"]["publisher"] == "Q8iDevAI"

    identity_js = (REPO_ROOT / "apps" / "desktop" / "product-identity.cjs").read_text(encoding="utf-8")
    assert "ai.q8idev." in identity_js
    assert "display: 'SANA'" in identity_js


def test_pyproject_exposes_sana_and_compat_aliases():
    text = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'sana = "hermes_cli.main:main"' in text
    assert 'sana-acp = "acp_adapter.entry:main"' in text
    assert 'hermes = "hermes_cli.main:main"' in text
    assert 'hermes-agent = "agent.legacy_cli:main"' in text


def test_readme_and_license_attribution():
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    assert "# SANA" in readme
    assert "### Your Intelligent AI Assistant" in readme
    assert "Developed by Q8iDevAI" in readme
    assert "Hermes Agent" not in readme
    assert "Nous Research" not in readme

    license_txt = (REPO_ROOT / "LICENSE").read_text(encoding="utf-8")
    assert "MIT License" in license_txt


def test_cli_parser_and_skin_branding():
    parser, _, _ = build_top_level_parser()
    assert parser.prog == "sana"
    assert "SANA" in (parser.description or "")
    assert "Q8iDevAI" in (parser.description or "")

    skin = load_skin("default")
    assert skin.get_branding("agent_name") == "SANA"
    assert "Q8iDevAI" in skin.get_branding("welcome")
    assert skin.get_color("banner_title") == "#D4AF37"
    assert skin.get_color("status_bar_bg") == "#0B0B0F"
    assert get_active_skin() is not None


def test_hermes_to_sana_migration_idempotent_and_secret_safe(tmp_path: Path):
    src = tmp_path / ".hermes"
    dst = tmp_path / ".sana"
    (src / "skills" / "demo").mkdir(parents=True)
    (src / "memories").mkdir(parents=True)
    (src / "config.yaml").write_text("model:\n  default: gpt-4o\n", encoding="utf-8")
    secret_val = "sk-test-super-secret-value-999"
    (src / ".env").write_text(f"OPENAI_API_KEY={secret_val}\n", encoding="utf-8")
    (src / "skills" / "demo" / "SKILL.md").write_text("# Demo Skill\n", encoding="utf-8")
    (src / "memories" / "MEMORY.md").write_text("Remembered fact\n", encoding="utf-8")

    info = detect_hermes_installation(src)
    assert info is not None
    assert "config.yaml" in info.found_items
    assert ".env" in info.found_items

    # 1. Dry run leaves target absent
    dry = migrate_hermes_to_sana(source=src, target=dst, dry_run=True)
    assert len(dry.copied) == 4
    assert not dst.exists()

    # 2. Real migration copies everything cleanly
    first = migrate_hermes_to_sana(source=src, target=dst, dry_run=False)
    assert len(first.copied) == 4
    assert (dst / "config.yaml").read_text(encoding="utf-8") == "model:\n  default: gpt-4o\n"
    assert (dst / ".env").read_text(encoding="utf-8") == f"OPENAI_API_KEY={secret_val}\n"
    # Receipt must never contain secret values
    receipt_text = (dst / "sana_migration.json").read_text(encoding="utf-8")
    assert secret_val not in receipt_text

    # 3. Idempotent re-run skips unchanged files
    second = migrate_hermes_to_sana(source=src, target=dst, dry_run=False)
    assert len(second.copied) == 0
    assert len(second.skipped) == 4
    assert len(second.conflicts) == 0

    # 4. Conflict without --force skips; with --force creates backup and updates
    (src / "config.yaml").write_text("model:\n  default: claude-sonnet-4\n", encoding="utf-8")
    third = migrate_hermes_to_sana(source=src, target=dst, dry_run=False, force=False)
    assert "config.yaml" in third.conflicts
    assert "gpt-4o" in (dst / "config.yaml").read_text(encoding="utf-8")

    fourth = migrate_hermes_to_sana(source=src, target=dst, dry_run=False, force=True, backup=True)
    assert "config.yaml" in fourth.updated
    assert fourth.backup_path is not None and fourth.backup_path.is_dir()
    assert "claude-sonnet-4" in (dst / "config.yaml").read_text(encoding="utf-8")
    # Source remains untouched
    assert "claude-sonnet-4" in (src / "config.yaml").read_text(encoding="utf-8")


def test_upstream_git_remote_configured():
    res = subprocess.run(
        ["git", "remote", "get-url", "upstream"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert res.returncode == 0
    assert "NousResearch/hermes-agent" in res.stdout
