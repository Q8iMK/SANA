# Migrating from Hermes Agent to SANA

SANA provides a safe, explicit, idempotent migration command (`sana import-hermes`) that imports your existing Hermes data without modifying or deleting your original Hermes installation.

---

## What Gets Migrated

- `config.yaml` (model, gateway, display, terminal, and tool settings)
- `.env` (API keys and tokens — never logged or printed)
- `SOUL.md` (persona configuration)
- `state.db` (conversation history and FTS5 search index)
- `memories/`, `sessions/`, `skills/`, `plugins/`, `cron/`, `skins/`, `profiles/`

---

## Usage

### 1. Preview Migration (Dry Run)

```bash
sana import-hermes --dry-run
```

### 2. Run Migration

```bash
sana import-hermes
```

Use `-y` / `--yes` for non-interactive runs, and `--force` to overwrite conflicting files in SANA's directory (a timestamped backup `<target>.backup.<UTC>` is automatically created first unless `--no-backup` is passed).

### 3. Custom Paths

```bash
sana import-hermes --source /path/to/.hermes --target /path/to/.sana
```

---

## Safety Guarantees

1. **Non-destructive:** The source Hermes directory is read-only during migration.
2. **No secret leakage:** `.env` and credential files are copied directly on disk and never logged.
3. **Idempotent:** Identical files (matching SHA-256) are skipped on subsequent runs.
4. **Backup & Recovery:** Conflicting target files are backed up to `<target>.backup.<timestamp>` before replacement.
5. **Receipt:** A summary (counts and timestamps only, no secrets) is written to `<target>/sana_migration.json`.
