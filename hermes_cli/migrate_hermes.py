"""Safe, idempotent migration from an existing Hermes installation to SANA.

Preserves settings, memory, sessions, skills, plugins, schedules, skins,
profiles, and credentials without ever mutating the source Hermes directory or
logging secret values.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

MIGRATION_ITEMS: tuple[str, ...] = (
    "config.yaml",
    ".env",
    "SOUL.md",
    "state.db",
    "memories",
    "sessions",
    "skills",
    "plugins",
    "cron",
    "skins",
    "profiles",
)

SENSITIVE_FILENAMES: frozenset[str] = frozenset({".env", "auth.json", "credentials.json"})


def get_sana_home() -> Path:
    """Return SANA's data directory (``SANA_HOME`` -> platform default)."""
    env_val = os.environ.get("SANA_HOME", "").strip()
    if env_val:
        return Path(os.path.expanduser(os.path.expandvars(env_val)))
    suffix = os.environ.get("SANA_DATA_DIR_SUFFIX", "")
    if sys.platform == "win32":
        local_appdata = os.environ.get("LOCALAPPDATA", "").strip()
        base = Path(local_appdata) if local_appdata else Path.home() / "AppData" / "Local"
        return base / ("sana" + suffix)
    return Path.home() / (".sana" + suffix)


def get_legacy_hermes_home() -> Path:
    """Return the legacy Hermes data directory (``HERMES_HOME`` -> platform default)."""
    env_val = os.environ.get("HERMES_HOME", "").strip()
    if env_val:
        return Path(os.path.expanduser(os.path.expandvars(env_val)))
    suffix = os.environ.get("HERMES_DATA_DIR_SUFFIX", "")
    if sys.platform == "win32":
        local_appdata = os.environ.get("LOCALAPPDATA", "").strip()
        base = Path(local_appdata) if local_appdata else Path.home() / "AppData" / "Local"
        return base / ("hermes" + suffix)
    return Path.home() / (".hermes" + suffix)


@dataclass(frozen=True)
class HermesInstallInfo:
    """Summary of a detected Hermes installation."""

    path: Path
    found_items: tuple[str, ...]


@dataclass
class MigrationReport:
    """Structured result of a Hermes -> SANA migration run."""

    source: Path
    target: Path
    dry_run: bool
    backup_path: Path | None = None
    copied: list[str] = field(default_factory=list)
    updated: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "source": str(self.source),
            "target": str(self.target),
            "dry_run": self.dry_run,
            "backup_path": str(self.backup_path) if self.backup_path else None,
            "copied_count": len(self.copied),
            "updated_count": len(self.updated),
            "skipped_count": len(self.skipped),
            "conflicts_count": len(self.conflicts),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


def detect_hermes_installation(source: Path | None = None) -> HermesInstallInfo | None:
    """Detect an existing Hermes installation without modifying anything."""
    candidate = source if source is not None else get_legacy_hermes_home()
    if not candidate.is_dir():
        return None
    found = tuple(item for item in MIGRATION_ITEMS if (candidate / item).exists())
    if not found:
        return None
    return HermesInstallInfo(path=candidate, found_items=found)


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _iter_source_files(source: Path, items: Iterable[str]) -> list[tuple[Path, Path]]:
    pairs: list[tuple[Path, Path]] = []
    for item in items:
        src = source / item
        if not src.exists():
            continue
        if src.is_file():
            pairs.append((src, Path(item)))
        elif src.is_dir():
            for child in sorted(src.rglob("*")):
                if child.is_file():
                    pairs.append((child, child.relative_to(source)))
    return pairs


def create_backup(target: Path) -> Path | None:
    """Create a timestamped backup of an existing SANA directory before migration."""
    if not target.exists() or not any(target.iterdir()):
        return None
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_dir = target.parent / f"{target.name}.backup.{stamp}"
    shutil.copytree(target, backup_dir, dirs_exist_ok=True)
    return backup_dir


def migrate_hermes_to_sana(
    *,
    source: Path | None = None,
    target: Path | None = None,
    dry_run: bool = False,
    backup: bool = True,
    force: bool = False,
) -> MigrationReport:
    """Idempotently migrate data from Hermes to SANA.

    - Never deletes or modifies *source*.
    - Never logs file contents or secret values.
    - Creates a backup of *target* before overwriting conflicting files when *backup* is True.
    """
    src_root = (source if source is not None else get_legacy_hermes_home()).resolve()
    dst_root = (target if target is not None else get_sana_home()).resolve()

    if src_root == dst_root:
        raise ValueError("Source and target directories must be different.")
    if not src_root.is_dir():
        raise FileNotFoundError(f"Hermes installation not found at: {src_root}")

    report = MigrationReport(source=src_root, target=dst_root, dry_run=dry_run)
    file_pairs = _iter_source_files(src_root, MIGRATION_ITEMS)

    needs_backup = False
    if not dry_run:
        dst_root.mkdir(parents=True, exist_ok=True)

    for src_file, rel_path in file_pairs:
        dst_file = dst_root / rel_path
        rel_str = rel_path.as_posix()

        if not dst_file.exists():
            report.copied.append(rel_str)
            if not dry_run:
                dst_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_file, dst_file)
            continue

        if _sha256_file(src_file) == _sha256_file(dst_file):
            report.skipped.append(rel_str)
            continue

        if not force:
            report.conflicts.append(rel_str)
            continue

        if backup and not needs_backup and not dry_run:
            report.backup_path = create_backup(dst_root)
            needs_backup = True

        report.updated.append(rel_str)
        if not dry_run:
            dst_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_file, dst_file)

    if not dry_run:
        receipt = dst_root / "sana_migration.json"
        receipt.write_text(json.dumps(report.to_dict(), indent=2) + "\n", encoding="utf-8")

    return report


def build_import_hermes_parser(subparsers) -> None:
    """Register the ``sana import-hermes`` subcommand."""
    import_p = subparsers.add_parser(
        "import-hermes",
        help="Safely import settings, sessions, skills, plugins, and credentials from Hermes into SANA",
    )
    import_p.add_argument("--source", help="Source Hermes home directory (default: auto-detect)")
    import_p.add_argument("--target", help="Target SANA home directory (default: ~/.sana or %%LOCALAPPDATA%%\\sana)")
    import_p.add_argument("--dry-run", action="store_true", help="Preview migration without copying files")
    import_p.add_argument("--force", action="store_true", help="Overwrite conflicting files (creates a backup first)")
    import_p.add_argument("--no-backup", action="store_true", help="Skip backup when --force is used")
    import_p.add_argument("-y", "--yes", action="store_true", help="Skip confirmation prompt")
    import_p.set_defaults(func=cmd_migrate)


def cmd_migrate(args) -> int:
    """CLI handler for ``sana migrate``."""
    src = Path(args.source).expanduser() if getattr(args, "source", None) else None
    dst = Path(args.target).expanduser() if getattr(args, "target", None) else None
    dry_run = bool(getattr(args, "dry_run", False))
    backup = not bool(getattr(args, "no_backup", False))
    force = bool(getattr(args, "force", False))

    info = detect_hermes_installation(src)
    if info is None:
        checked = src or get_legacy_hermes_home()
        print(f"No existing Hermes installation found at {checked}.")
        return 0

    target_dir = dst or get_sana_home()
    print(f"Detected Hermes installation at: {info.path}")
    print(f"Target SANA home: {target_dir}")
    print(f"Items found: {', '.join(info.found_items)}")

    if not dry_run and not getattr(args, "yes", False):
        reply = input("Proceed with migration? [y/N]: ").strip().lower()
        if reply not in {"y", "yes"}:
            print("Migration cancelled. No files were modified.")
            return 0

    report = migrate_hermes_to_sana(
        source=info.path,
        target=target_dir,
        dry_run=dry_run,
        backup=backup,
        force=force,
    )
    prefix = "[DRY RUN] " if dry_run else ""
    print(
        f"{prefix}Migration complete: "
        f"{len(report.copied)} copied, "
        f"{len(report.updated)} updated, "
        f"{len(report.skipped)} unchanged, "
        f"{len(report.conflicts)} conflicts."
    )
    if report.backup_path:
        print(f"Backup created at: {report.backup_path}")
    if report.conflicts:
        print("Skipped conflicting files (re-run with --force to overwrite with backup):")
        for c in report.conflicts[:20]:
            print(f"  - {c}")
    return 0
