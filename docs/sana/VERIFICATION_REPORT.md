# SANA Rebranding Verification Report

**Product:** SANA — Your Intelligent AI Assistant  
**Maintainer:** Q8iDevAI  
**Upstream Base:** `NousResearch/hermes-agent` (`upstream-baseline` commit `c6f410af`)  
**License:** MIT (original Nous Research copyright preserved)

---

## 1. Visual & Brand Identity

- Master SVGs authored in `branding/assets/` using `#0B0B0F` (black), `#17171C` (dark secondary), `#D4AF37` (gold), and `#FFFFFF` (white).
- Reproducible asset generator (`branding/scripts/generate_brand_assets.py`) generates multi-resolution PNGs (16–1024 px), Windows `.ico`, macOS `.icns`, MSIX `appx` tiles, macOS `icon.icon` Icon Composer assets, web/website favicons, README banner, splash graphic, and Windows installer sidebar.

## 2. Documented Compatibility Exceptions

The following legacy `hermes` / `Nous Research` references are intentionally retained:
1. **Licensing & Copyright:** `LICENSE` and copyright headers (`Copyright (c) 2025 Nous Research`).
2. **Attribution:** `README.md`, `branding/BRANDING.md`, and `apps/bootstrap-installer/src-tauri/tauri.conf.json` transparently credit Hermes Agent by Nous Research.
3. **Internal Python Packages & Environment Compatibility:** `hermes_cli`, `hermes_constants`, `hermes_state`, `hermes_platform`, `hermes_scope`, `HERMES_HOME`, and `pyproject.toml` `name = "hermes-agent"` are preserved so plugins, skills, `uv.lock`, and upstream merges remain intact.
4. **CLI Aliases & Protocol Compatibility:** `hermes`, `hermes-agent`, and `hermes-acp` remain alongside `sana` and `sana-acp`; `hermes` URL protocol remains alongside `sana`.
5. **Migration Tooling:** `hermes_cli/migrate_hermes.py` references legacy `~/.hermes` / `%LOCALAPPDATA%\hermes` paths to detect and safely import existing installations.
