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


def test_docusaurus_config_branded_and_preserves_algolia():
    text = (REPO_ROOT / "website" / "docusaurus.config.ts").read_text(encoding="utf-8")
    assert "title: 'SANA'" in text
    assert "tagline: 'Your Intelligent AI Assistant'" in text
    assert "organizationName: 'Q8iMK'" in text
    assert "projectName: 'SANA'" in text
    assert "image: 'img/sana-banner.png'" in text
    assert "Q8iDevAI" in text
    # Algolia technical index must be preserved
    assert "indexName: 'hermes docs'" in text
    # Website banner & logos must exist and be non-empty
    for asset in ("logo.png", "logo-dark.png", "sana-banner.png"):
        p = REPO_ROOT / "website" / "static" / "img" / asset
        assert p.is_file() and p.stat().st_size > 0


def test_translated_readmes_branded_with_attribution():
    for name in ("README.es.md", "README.zh-CN.md", "README.ur-pk.md"):
        text = (REPO_ROOT / name).read_text(encoding="utf-8")
        assert "# SANA" in text
        assert "Q8iDevAI" in text
        assert "Q8iMK/SANA" in text
        assert "sana " in text or "`sana`" in text
        # Must acknowledge Nous Research as original upstream
        assert "Nous Research" in text
        # Must not point install commands at upstream site
        assert "hermes-agent.nousresearch.com/install" not in text
        assert "Built%20by-Nous%20Research" not in text
        assert "Creado%20por-Nous%20Research" not in text


def test_setup_scripts_sana_first_and_isolated():
    for name in ("setup-hermes.ps1", "setup-hermes.sh", "setup-sana.ps1", "setup-sana.sh"):
        assert (REPO_ROOT / name).is_file()
    ps1 = (REPO_ROOT / "setup-hermes.ps1").read_text(encoding="utf-8")
    assert "SANA Setup" in ps1
    assert "Q8iDevAI" in ps1
    assert "SANA_HOME" in ps1
    assert "sana setup" in ps1
    sh = (REPO_ROOT / "setup-hermes.sh").read_text(encoding="utf-8")
    assert "SANA Setup" in sh
    assert "Q8iDevAI" in sh
    assert "SANA_HOME" in sh
    assert "sana setup" in sh


def test_package_metadata_and_setup_py():
    root_pkg = json.loads((REPO_ROOT / "package.json").read_text(encoding="utf-8"))
    assert root_pkg["name"] == "hermes-agent"  # pnpm workspace compat
    assert "SANA" in root_pkg["description"]
    assert "Q8iDevAI" in root_pkg["description"]
    assert "Q8iMK/SANA" in root_pkg["repository"]["url"]
    assert "Q8iMK/SANA" in root_pkg["bugs"]["url"]
    assert "Q8iMK/SANA" in root_pkg["homepage"]

    desk_pkg = json.loads((REPO_ROOT / "apps" / "desktop" / "package.json").read_text(encoding="utf-8"))
    assert desk_pkg["name"] == "hermes"  # pnpm workspace filter compat
    assert desk_pkg["productName"] == "SANA"
    assert "Q8iMK/SANA" in desk_pkg["repository"]["url"]

    setup_py = (REPO_ROOT / "setup.py").read_text(encoding="utf-8")
    assert "SANA" in setup_py
    assert "Q8iDevAI" in setup_py
    assert "hermes-agent.nousresearch.com" not in setup_py


def test_update_feeds_and_releases_isolated_from_upstream():
    from hermes_cli import source_releases, update_cmd_git

    assert source_releases.OFFICIAL_REPOSITORY == "Q8iMK/SANA"
    assert "nousresearch.com" not in source_releases._PUBLIC_BASE
    assert "Q8iMK/SANA" in update_cmd_git.OFFICIAL_REPO_URL
    assert all("Q8iMK/SANA" in u for u in update_cmd_git.OFFICIAL_REPO_URLS)

    r2_text = (REPO_ROOT / "scripts" / "releases" / "r2.py").read_text(encoding="utf-8")
    assert 'DEFAULT_PUBLIC_URL = "https://hermes-assets.nousresearch.com"' not in r2_text

    channels_text = (REPO_ROOT / "scripts" / "releases" / "channels.py").read_text(encoding="utf-8")
    assert "SANAChannel" in channels_text
    assert "Q8iDevAI." in channels_text


def test_audit_fails_on_visible_hermes_regression(tmp_path):
    sys.path.insert(0, str(REPO_ROOT / "branding" / "scripts"))
    import apply_branding

    bad = tmp_path / "bad_ui.ts"
    bad.write_text('export const msg = "Update Hermes Desktop now";\n', encoding="utf-8")
    manifest = json.loads((REPO_ROOT / "branding" / "manifest.json").read_text(encoding="utf-8"))
    report = apply_branding.BrandingReport()
    # Simulate scanning a user-facing file with unattributed Hermes Desktop text
    for lineno, line in enumerate(bad.read_text(encoding="utf-8").splitlines(), 1):
        for pat in manifest["validation"]["forbiddenUserFacingPatterns"]:
            if pat in line:
                report.audit_warnings.append(f"bad_ui.ts:{lineno}: contains '{pat}'")
    assert report.audit_warnings, "Regression check must catch unbranded display strings"


def test_check_mode_writes_json_and_md_reports(tmp_path):
    json_out = tmp_path / "report.json"
    md_out = tmp_path / "report.md"
    res = subprocess.run(
        [
            sys.executable,
            "branding/scripts/apply_branding.py",
            "--check",
            "--skip-assets",
            "--json-report",
            str(json_out),
            "--md-report",
            str(md_out),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert res.returncode == 0, res.stdout + res.stderr
    data = json.loads(json_out.read_text(encoding="utf-8"))
    assert data["ok"] is True
    assert data["conflicts"] == []
    assert "PASS" in md_out.read_text(encoding="utf-8")
