# SANA Development Guide

**SANA — Your Intelligent AI Assistant**  
Developed by **Q8iDevAI**

---

## 1. Repository Architecture

SANA preserves the modular Hermes Agent core while centralizing all Q8iDevAI branding and asset generation under `branding/`:

- `sana_branding.py` — Stdlib-only runtime branding accessor reading `branding/sana.config.json`.
- `branding/` — Central branding configuration, SVG masters, asset generator, idempotent rebranding script, and branding test suite.
- `hermes_cli/` — CLI entry point (`sana` / `hermes`), banner, skin engine, config, gateway, and `migrate_hermes.py`.
- `apps/desktop/` — Electron + React Desktop application (`product-identity.cjs` drives `SANA` / `SANA Light`).
- `apps/bootstrap-installer/` — Tauri + React bootstrap installer (`SANA`).
- `web/` — Web Dashboard (`SANA — Dashboard`).
- `ui-tui/` — Ink-based Terminal UI.

---

## 2. Running Tests

```bash
# Run SANA branding, asset, CLI, and migration tests
python -m pytest branding/tests/ -v

# Run core constants & CLI tests
python -m pytest tests/test_hermes_constants.py -v

# Verify branding integrity (CI check)
python branding/scripts/apply_branding.py --check
```

On Windows environments where `.venv\Scripts\python.exe` is restricted by Application Control, invoke system Python with `.venv\Lib\site-packages` on `PYTHONPATH`:

```powershell
$env:PYTHONPATH = ".;.venv\Lib\site-packages"
python -m pytest branding/tests/ -v
```

---

## 3. Regenerating Brand Assets

```bash
python branding/scripts/generate_brand_assets.py
```

This renders all PNGs (16–1024 px), Windows `.ico`, macOS `.icns`, MSIX tiles, favicons, and banners from `branding/assets/*.svg`.
