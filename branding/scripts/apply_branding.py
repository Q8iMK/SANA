#!/usr/bin/env python3
"""Idempotent SANA rebranding & verification tool.

Usage:
    python branding/scripts/apply_branding.py           # Apply SANA branding & regenerate assets
    python branding/scripts/apply_branding.py --check   # Verify branding without modifying files
    python branding/scripts/apply_branding.py --skip-assets  # Skip raster asset regeneration

Designed to survive future upstream Hermes Agent merges/rebases cleanly.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BRANDING_DIR = REPO_ROOT / "branding"
CONFIG_PATH = BRANDING_DIR / "sana.config.json"
MANIFEST_PATH = BRANDING_DIR / "manifest.json"


@dataclass
class BrandingReport:
    updated: list[str] = field(default_factory=list)
    already_branded: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    audit_warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.missing and not self.conflicts


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Required branding file missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _update_html_title(path: Path, title: str, *, theme_color: str | None = None, check: bool, report: BrandingReport) -> None:
    if not path.is_file():
        report.missing.append(str(path.relative_to(REPO_ROOT)))
        return
    original = path.read_text(encoding="utf-8")
    updated = re.sub(r"<title>[^<]*</title>", f"<title>{title}</title>", original, count=1)
    if theme_color:
        updated = re.sub(
            r'(<meta\s+name="theme-color"\s+content=")[^"]*(")',
            rf"\g<1>{theme_color}\2",
            updated,
            count=1,
        )
    rel = str(path.relative_to(REPO_ROOT))
    if updated == original:
        if f"<title>{title}</title>" in original:
            report.already_branded.append(rel)
        else:
            report.conflicts.append(f"{rel}: <title> tag not found")
        return
    if check:
        report.conflicts.append(f"{rel}: title/theme out of sync with SANA branding")
        return
    path.write_text(updated, encoding="utf-8")
    report.updated.append(rel)


def _update_json_fields(path: Path, updates: dict[str, Any], *, check: bool, report: BrandingReport) -> None:
    if not path.is_file():
        report.missing.append(str(path.relative_to(REPO_ROOT)))
        return
    original = path.read_text(encoding="utf-8")
    data = json.loads(original)
    changed = False

    def _apply(obj: dict[str, Any], patch: dict[str, Any]) -> None:
        nonlocal changed
        for k, v in patch.items():
            if isinstance(v, dict) and isinstance(obj.get(k), dict):
                _apply(obj[k], v)
            elif obj.get(k) != v:
                obj[k] = v
                changed = True

    _apply(data, updates)
    rel = str(path.relative_to(REPO_ROOT))
    if not changed:
        report.already_branded.append(rel)
        return
    if check:
        report.conflicts.append(f"{rel}: JSON metadata out of sync with SANA branding")
        return
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    report.updated.append(rel)


def _ensure_pyproject_scripts(path: Path, cfg: dict[str, Any], *, check: bool, report: BrandingReport) -> None:
    if not path.is_file():
        report.missing.append(str(path.relative_to(REPO_ROOT)))
        return
    text = path.read_text(encoding="utf-8")
    cli_cmd = cfg["cli"]["command"]
    acp_cmd = cfg["cli"]["acpCommand"]
    rel = str(path.relative_to(REPO_ROOT))

    has_sana = re.search(rf'^\s*{re.escape(cli_cmd)}\s*=\s*"hermes_cli\.main:main"', text, re.MULTILINE) is not None
    has_acp = re.search(rf'^\s*{re.escape(acp_cmd)}\s*=\s*"acp_adapter\.entry:main"', text, re.MULTILINE) is not None

    if has_sana and has_acp:
        report.already_branded.append(rel)
        return
    if check:
        report.conflicts.append(f"{rel}: missing '{cli_cmd}' or '{acp_cmd}' in [project.scripts]")
        return

    anchor = "[project.scripts]\n"
    if anchor not in text:
        report.conflicts.append(f"{rel}: [project.scripts] section not found")
        return
    inserts = []
    if not has_sana:
        inserts.append(f'{cli_cmd} = "hermes_cli.main:main"')
    if not has_acp:
        inserts.append(f'{acp_cmd} = "acp_adapter.entry:main"')
    updated = text.replace(anchor, anchor + "\n".join(inserts) + "\n", 1)
    path.write_text(updated, encoding="utf-8")
    report.updated.append(rel)


def _verify_desktop_identity(path: Path, cfg: dict[str, Any], report: BrandingReport) -> None:
    if not path.is_file():
        report.missing.append(str(path.relative_to(REPO_ROOT)))
        return
    text = path.read_text(encoding="utf-8")
    rel = str(path.relative_to(REPO_ROOT))
    expected_display = cfg["desktop"]["displayName"]
    expected_org = cfg["desktop"]["appIdPrefix"].rsplit(".", 1)[0] + "."
    if expected_display in text and expected_org in text:
        report.already_branded.append(rel)
    else:
        report.conflicts.append(f"{rel}: missing SANA displayName ({expected_display}) or appIdPrefix ({expected_org})")


def _rebrand_i18n_files(*, check: bool, report: BrandingReport) -> None:
    """Rebrand user-facing i18n string literals across desktop and web locales."""
    i18n_dirs = [
        REPO_ROOT / "apps" / "desktop" / "src" / "i18n",
        REPO_ROOT / "web" / "src" / "i18n",
    ]
    skip_tokens = (
        "~/.hermes",
        "hermes-",
        "hermes:",
        "HERMES_",
        "hermes ",
        "Hermes.app",
        "hermes.app",
        "Hermes_",
        "requiresHermes",
        "hermesCloud",
        "nousresearch.com",
        "github.com/NousResearch",
    )

    for folder in i18n_dirs:
        if not folder.is_dir():
            continue
        for path in sorted(folder.glob("*.ts")):
            if ".test." in path.name:
                continue
            orig = path.read_text(encoding="utf-8")
            lines = orig.splitlines(keepends=True)
            out: list[str] = []
            changed = False
            for line in lines:
                s = line.lstrip()
                if s.startswith(("//", "/*", "*")):
                    out.append(line)
                    continue
                new_line = line
                if ":" in new_line or s.startswith(("'", '"', "`")):
                    new_line = re.sub(r"\bHermes Desktop\b", "SANA", new_line)
                    new_line = re.sub(r"\bHermes desktop\b", "SANA", new_line)
                    new_line = re.sub(r"\bHermes Agent\b", "SANA", new_line)
                    new_line = re.sub(r"(appName:\s*['\"])Hermes(['\"])", r"\g<1>SANA\2", new_line)
                    new_line = re.sub(r"(brand:\s*['\"])Hermes(['\"])", r"\g<1>SANA\2", new_line)
                    new_line = re.sub(r"(org:\s*['\"])Nous Research(['\"])", r"\g<1>Q8iDevAI\2", new_line)
                    new_line = re.sub(r"Nous Research", "Q8iDevAI", new_line)
                    if path.name.startswith(("en", "ar")) and not any(tok in new_line for tok in skip_tokens):
                        new_line = re.sub(
                            r"(?<![a-zA-Z0-9_./-])Hermes(?:'s)?(?![a-zA-Z0-9_/-])",
                            "SANA",
                            new_line,
                        )
                if new_line != line:
                    changed = True
                out.append(new_line)
            if not changed:
                continue
            rel = str(path.relative_to(REPO_ROOT))
            if check:
                report.conflicts.append(f"{rel}: contains unbranded i18n display strings")
            else:
                path.write_text("".join(out), encoding="utf-8")
                report.updated.append(rel)


def _audit_user_facing_surfaces(manifest: dict[str, Any], report: BrandingReport) -> None:
    """Scan primary user-facing entry files for unattributed upstream branding."""
    forbidden = manifest.get("validation", {}).get("forbiddenUserFacingPatterns", [])
    surfaces = [
        REPO_ROOT / "README.md",
        REPO_ROOT / "apps" / "desktop" / "index.html",
        REPO_ROOT / "apps" / "desktop" / "package.json",
        REPO_ROOT / "apps" / "bootstrap-installer" / "index.html",
        REPO_ROOT / "apps" / "bootstrap-installer" / "src-tauri" / "tauri.conf.json",
        REPO_ROOT / "web" / "index.html",
    ]
    for path in surfaces:
        if not path.is_file():
            continue
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        rel = str(path.relative_to(REPO_ROOT))
        for lineno, line in enumerate(lines, start=1):
            lower = line.lower()
            # Attribution/copyright lines referencing upstream Hermes Agent are explicitly allowed
            if "based on" in lower or "upstream" in lower or "copyright" in lower:
                continue
            for pat in forbidden:
                if pat in line:
                    report.audit_warnings.append(f"{rel}:{lineno}: contains '{pat}'")


def run_apply_branding(*, check: bool = False, skip_assets: bool = False) -> BrandingReport:
    cfg = load_json(CONFIG_PATH)
    manifest = load_json(MANIFEST_PATH)
    report = BrandingReport()

    # 1. Validate required core branding files
    for req in manifest.get("validation", {}).get("requiredFiles", []):
        if not (REPO_ROOT / req).is_file():
            report.missing.append(req)

    # 2. Apply/verify structural branding targets
    _ensure_pyproject_scripts(REPO_ROOT / "pyproject.toml", cfg, check=check, report=report)
    _verify_desktop_identity(REPO_ROOT / "apps" / "desktop" / "product-identity.cjs", cfg, report)

    _update_json_fields(
        REPO_ROOT / "apps" / "desktop" / "package.json",
        {
            "productName": cfg["desktop"]["displayName"],
            "description": cfg["desktop"]["description"],
            "author": cfg["desktop"]["author"],
        },
        check=check,
        report=report,
    )
    _update_html_title(
        REPO_ROOT / "apps" / "desktop" / "index.html",
        cfg["desktop"]["displayName"],
        theme_color=cfg["theme"]["black"],
        check=check,
        report=report,
    )
    _update_html_title(
        REPO_ROOT / "web" / "index.html",
        cfg["web"]["title"],
        check=check,
        report=report,
    )
    _update_html_title(
        REPO_ROOT / "apps" / "bootstrap-installer" / "index.html",
        cfg["installer"]["productName"],
        check=check,
        report=report,
    )

    tauri_conf = REPO_ROOT / "apps" / "bootstrap-installer" / "src-tauri" / "tauri.conf.json"
    _update_json_fields(
        tauri_conf,
        {
            "productName": cfg["installer"]["productName"],
            "identifier": cfg["installer"]["identifier"],
            "bundle": {
                "shortDescription": cfg["installer"]["shortDescription"],
                "longDescription": cfg["installer"]["longDescription"],
                "publisher": cfg["installer"]["publisher"],
                "copyright": cfg["installer"]["copyright"],
            },
        },
        check=check,
        report=report,
    )

    # 3. i18n locale strings
    _rebrand_i18n_files(check=check, report=report)

    # 4. Assets
    if not skip_assets:
        sys.path.insert(0, str(BRANDING_DIR / "scripts"))
        import generate_brand_assets

        try:
            generate_brand_assets.generate_all(check_only=check)
        except (FileNotFoundError, RuntimeError, OSError) as exc:
            report.conflicts.append(f"Asset generation/check failed: {exc}")

    # 4. Audit user-facing surfaces
    _audit_user_facing_surfaces(manifest, report)
    if report.audit_warnings:
        report.conflicts.extend(report.audit_warnings)

    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply or verify SANA branding across the repository.")
    parser.add_argument("--check", action="store_true", help="Verify branding without modifying files.")
    parser.add_argument("--skip-assets", action="store_true", help="Skip raster asset generation/check.")
    args = parser.parse_args()

    report = run_apply_branding(check=args.check, skip_assets=args.skip_assets)

    print(f"[SANA Branding] Already branded: {len(report.already_branded)}")
    if report.updated:
        print(f"[SANA Branding] Updated ({len(report.updated)}): {', '.join(report.updated)}")
    if report.missing:
        print(f"[SANA Branding] Missing ({len(report.missing)}): {', '.join(report.missing)}", file=sys.stderr)
    if report.conflicts:
        print("[SANA Branding] Conflicts / Drift detected:", file=sys.stderr)
        for c in report.conflicts:
            print(f"  - {c}", file=sys.stderr)

    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
