# SANA — Final Rebranding Audit & Validation Report

**Product:** SANA — *Your Intelligent AI Assistant*  
**Developer / Maintainer:** Q8iDevAI (`https://github.com/Q8iMK/SANA`)  
**Upstream Base:** `NousResearch/hermes-agent` (`upstream-baseline`)  
**Primary Brand Colors:** `#0B0B0F` (Black), `#D4AF37` (Gold)  
**Audit Branch:** `fix/sana-rebranding-audit`  
**Date:** 2026-11-18  

---

## 1. Executive Summary

This audit identified and repaired remaining upstream *Hermes Agent* / *Hermes Desktop* / *Nous Research* branding, update-feed pointers, installer metadata, multilingual documentation, and verification gaps across the SANA repository while preserving full functional compatibility, upstream attribution, and MIT licensing obligations.

Key accomplishments:
- Rebranded `website/docusaurus.config.ts`, `website/static/img/sana-banner.png`, `package.json`, `apps/desktop/package.json`, and `setup.py`.
- Updated `setup-hermes.ps1` and `setup-hermes.sh` to SANA-first behavior using isolated `~/.sana` / `%LOCALAPPDATA%\sana` paths and added `setup-sana.ps1` and `setup-sana.sh` entry points; updated `hermes_cli/_launchers.py` and `hermes_cli/_install_repair.py` to publish `sana` and `sana-acp` launchers alongside compatibility aliases.
- Rebranded multilingual READMEs (`README.es.md`, `README.zh-CN.md`, `README.ur-pk.md`) to SANA / Q8iDevAI with `sana` CLI examples and explicit Nous Research upstream attribution.
- Rebranded remaining Desktop Electron/renderer, Web Dashboard, CLI subcommand, and Gateway user-facing strings.
- Isolated SANA update and release channels (`hermes_cli/source_releases.py`, `hermes_cli/update_cmd_git.py`, `scripts/releases/r2.py`, `scripts/releases/channels.py`, `scripts/install.ps1`, `scripts/install.sh`, `apps/bootstrap-installer/`) so SANA never pulls or overwrites itself with upstream Hermes Agent releases.
- Expanded `branding/manifest.json`, `branding/scripts/apply_branding.py` (with `--json-report` and `--md-report`), `branding/tests/test_sana_branding.py` (16 tests), and added `.github/workflows/sana-branding-audit.yml`.

---

## 2. File-by-File Repair & Audit Table

| File Path | Original Problem | Fix Applied | Compatibility Exception | Test Performed | Result |
|---|---|---|---|---|---|
| `website/docusaurus.config.ts` | Branded as `Hermes Agent`, `NousResearch/hermes-agent`, `hermes-agent.nousresearch.com`, `hermes-agent-banner.png` | Updated title/tagline/navbar/footer/repo links to SANA, Q8iDevAI, `Q8iMK/SANA`, and `img/sana-banner.png` | Preserved `algolia` (`appId`, `apiKey`, `indexName: 'hermes docs'`) and doc redirects | `test_docusaurus_config_branded_and_preserves_algolia` | PASS |
| `website/static/img/sana-banner.png` & `branding/scripts/generate_brand_assets.py` | `sana-banner.png` not synced to `website/static/img/` | Synced `sana-banner.png` into `website/static/img/` and added to `generate_brand_assets.py` + `manifest.json` | Kept `hermes-agent-banner.png`, `nous-logo.png`, `nous-logo-dark.png` on disk (obsolete/historical) | `apply_branding.py --check`, `test_docusaurus_config_branded_and_preserves_algolia` | PASS |
| `setup-hermes.ps1` & `setup-sana.ps1` | "Hermes Agent Setup", `~/.hermes/tools`, `~/.hermes/skills`, `hermes` next steps | SANA-first display, isolated `SANA_HOME` / `%LOCALAPPDATA%\sana` & `~/.sana/tools`, launcher publication + PATH, `sana` next steps; added `setup-sana.ps1` | Honors `HERMES_HOME` / `HERMES_RUNTIME_DIR` if explicitly set | PowerShell AST parser check + `test_setup_scripts_sana_first_and_isolated` | PASS |
| `setup-hermes.sh` & `setup-sana.sh` | "Hermes Agent Setup", `~/.hermes/tools`, `~/.hermes/skills`, `hermes` next steps | SANA-first display, isolated `$HOME/.sana` paths, `sana` next steps; added `setup-sana.sh` | Honors `HERMES_HOME` / `HERMES_RUNTIME_DIR` if explicitly set | `test_setup_scripts_sana_first_and_isolated` | PASS |
| `hermes_cli/_launchers.py` & `hermes_cli/_install_repair.py` | Published only `hermes` and `hermes-acp` launchers | Added `sana` and `sana-acp` to `WINDOWS_BIN_LAUNCHERS` and `ENTRY_POINTS` | Kept `hermes`, `hermes-agent`, `hermes-acp` compatibility aliases | `tests/hermes_cli/test_ensure_windows_bin_launchers.py` (21 passed) | PASS |
| `package.json` | Upstream `description`, `repository`, `bugs`, `homepage` | Updated metadata to SANA, `Q8iDevAI`, `Q8iMK/SANA` | Kept `"name": "hermes-agent"` for pnpm workspace & lockfile resolution | `test_package_metadata_and_setup_py` | PASS |
| `apps/desktop/package.json` | Upstream `repository.url` (`NousResearch/hermes-agent`) | Updated `repository.url` to `git+https://github.com/Q8iMK/SANA.git` | Kept `"name": "hermes"` for `pnpm --filter hermes` & `pnpm-lock.yaml` | `test_package_metadata_and_setup_py` | PASS |
| `setup.py` | "Hermes is distributed..." and upstream URL in `_BLOCK_MESSAGE` | Updated `_BLOCK_MESSAGE` and docstring to SANA / `Q8iDevAI` / `Q8iMK/SANA` | Preserved `HERMES_NIX_BUILD=1` Nix build guard | `test_package_metadata_and_setup_py` | PASS |
| `README.es.md`, `README.zh-CN.md`, `README.ur-pk.md` | Hermes Agent headings, Nous Research badges, `hermes` commands, upstream install/docs URLs | Rebranded to SANA & Q8iDevAI, `sana` CLI examples, `Q8iMK/SANA` links, local `website/docs/` links | Preserved translated content, Nous Research upstream attribution, and `Nous Portal` service links | `test_translated_readmes_branded_with_attribution` | PASS |
| `apps/desktop/electron-builder.config.cjs` | `dmg.title: 'Hermes Agent Installer'`, `linux.synopsis` referencing Hermes Agent | Updated to `${displayName} Installer` and SANA synopsis | Kept `hermes` URL scheme alongside `sana` | `pnpm --filter hermes run check:lint`, `pnpm --filter hermes run build` | PASS |
| `apps/desktop/electron/product-identity.test.ts` | Asserted old `Hermes` / `Hermes Agent` / `NousResearchInc.HermesAgent` values | Updated assertions to SANA, `SANA Light`, `Q8iDevAI.SANA`, `['sana', 'hermes']` | Preserved Nous Partner Center `publisher` GUID placeholder (see Known Limitations) | `vitest run electron/product-identity.test.ts` (10 passed) | PASS |
| `apps/desktop/electron/{main,hardening,remote-lifecycle}.ts` & `src/{sdk/index,store/gateway,store/onboarding,store/onboarding-scope,plugins/hermes-bots/i18n}.ts` & `src/i18n/*.ts` | User-facing error/status/install strings referencing `Hermes Desktop` or upstream install URL | Updated user-facing messages to `SANA` and `Q8iMK/SANA` install script URL | Preserved `Nous Cloud` / `portal.nousresearch.com` external service references | `pnpm --filter hermes run check:lint`, `pnpm --filter hermes run build` | PASS |
| `web/src/pages/ChannelsPage.tsx` | Default Telegram bot name `"Hermes Agent"` | Updated to `"SANA"` | None | `pnpm --filter web build` | PASS |
| `hermes_cli/{setup,status,uninstall,update_cmd,web_server,telegram_managed_bot}.py`, `hermes_cli/web_routers/messaging.py`, `hermes_cli/subcommands/*.py`, `gateway/{local_desktop_ui,platforms/whatsapp_common,relay/command_manifest}.py` | User-facing banners, help descriptions, WhatsApp reply prefix, default bot name, and docs URLs | Rebranded user-facing strings to SANA (`✦`), `Q8iDevAI`, and `Q8iMK/SANA` | Preserved `DEFAULT_API_URL` (`setup.hermes-agent.nousresearch.com`) in `telegram_managed_bot.py` and `# Hermes Agent` cleanup in `uninstall.py` | `sana.cmd` CLI smoke tests + `apply_branding.py --check` | PASS |
| `hermes_cli/source_releases.py`, `hermes_cli/update_cmd_git.py`, `scripts/releases/r2.py`, `scripts/releases/channels.py`, `scripts/install.ps1`, `scripts/install.sh`, `apps/bootstrap-installer/` | Defaulted update/release targets to `NousResearch/hermes-agent` and `hermes-assets.nousresearch.com` | Pointed `OFFICIAL_REPOSITORY` / `OFFICIAL_REPO_URL` / installer URLs to `Q8iMK/SANA`; removed hardcoded Nous R2 fallback; updated `preview_identity` to `SANAChannel` / `Q8iDevAI` | None | `test_update_feeds_and_releases_isolated_from_upstream` | PASS |
| `branding/manifest.json`, `branding/scripts/apply_branding.py`, `branding/tests/test_sana_branding.py` | Limited audit surface coverage; no JSON/MD report output | Expanded audit to Docusaurus, translated READMEs, setup scripts, desktop/web/CLI/gateway/release files; added `--json-report` / `--md-report` and 7 new tests | Explicit attribution/comment/service-URL exclusions | `apply_branding.py --check`, `pytest branding/tests/test_sana_branding.py` (16 passed) | PASS |
| `.github/workflows/sana-branding-audit.yml` | No automated SANA branding CI workflow | Created workflow running config, check-mode, idempotence, asset, CLI, and regression checks with JSON/MD artifact upload | None | YAML & script steps verified locally | PASS (local) |

---

## 3. Remaining Legitimate Technical Identifiers & Copyright Notices

1. **Internal Python package & module names:** `hermes_cli`, `hermes_constants`, `hermes_state`, `hermes_platform`, `hermes_scope`, `hermes_agent` — retained for plugin, skill, and upstream merge compatibility.
2. **Workspace package names:** Root `package.json` (`"name": "hermes-agent"`) and `apps/desktop/package.json` (`"name": "hermes"`) — retained for pnpm workspace filter and `pnpm-lock.yaml` compatibility.
3. **External services:** `Nous Portal` (`https://portal.nousresearch.com`), `Nous Cloud` (`backend-health.ts`), Telegram Managed Bot pairing API (`https://setup.hermes-agent.nousresearch.com`), and Algolia DocSearch index (`indexName: 'hermes docs'`).
4. **Copyright & License:** `LICENSE` (`Copyright (c) 2025 Nous Research`) and MIT license headers are preserved verbatim, with SANA attribution added for Q8iDevAI.
5. **Obsolete upstream image files:** `website/static/img/hermes-agent-banner.png`, `website/static/img/nous-logo.png`, `website/static/img/nous-logo-dark.png` remain on disk for historical/compatibility safety and are no longer referenced by `docusaurus.config.ts`.

---

## 4. Verification & Build Results

- **Branding Check (`apply_branding.py --check`):** PASSED (0 missing, 0 conflicts).
- **Branding Unit & Structural Tests (`pytest branding/tests/test_sana_branding.py -v`):** 16/16 PASSED.
- **Windows Launcher Tests (`pytest tests/hermes_cli/test_ensure_windows_bin_launchers.py -q`):** 21/21 PASSED.
- **Desktop Product Identity Tests (`pnpm --filter hermes exec vitest run electron/product-identity.test.ts`):** 10/10 PASSED.
- **Desktop Lint & TypeScript Check (`pnpm --filter hermes run check:lint`):** PASSED (0 errors; 397 pre-existing style warnings).
- **Desktop Build (`pnpm --filter hermes run build`):** PASSED (Vite renderer + Electron main/preload built).
- **Web Dashboard Build (`pnpm --filter web build`):** PASSED (`hermes_cli/web_dist/index.html` built).
- **CLI Smoke Tests (`sana.cmd --version`, `--help`, `import-hermes --help`, `setup --help`, `model --help`, `tools --help`, `gateway --help`, `update --help`, `doctor --help` in isolated temp `SANA_HOME`):** PASSED.
- **PowerShell Setup Syntax Check (`setup-hermes.ps1`, `setup-sana.ps1`):** PASSED.

### Not Executed in This Environment
- **Docusaurus Website Build (`website/`):** `website/node_modules` is not installed in this checkout; Docusaurus build was not run locally.
- **macOS / Linux Native Packaging (DMG, AppImage, MSIX signing):** Cannot build macOS DMG or Linux AppImage on Windows; Windows MSIX signing credentials (`AZURE_SIGN_*`) and Q8iDevAI Microsoft Partner Center `publisher` GUID are not configured in this environment, so packaged installers are not production-signed.

---

## 5. Known Limitations & Next Upstream Update Procedure

1. **Signing & Store Identity:** `apps/desktop/product-identity.cjs` retains the upstream Partner Center `publisher` GUID (`CN=EE6D86E4-606F-4E38-B940-AD7248C9D519`) as a placeholder for the `store` variant. Replace with Q8iDevAI's Microsoft Partner Center Publisher ID and configure `AZURE_SIGN_*` secrets before Store or signed MSIX distribution.
2. **Future Upstream Merges (`NousResearch/hermes-agent`):**
   ```bash
   git fetch upstream
   git merge upstream/main
   python branding/scripts/apply_branding.py
   python branding/scripts/apply_branding.py --check
   pytest branding/tests/test_sana_branding.py -v
   ```
   Review any new upstream user-facing strings or release URLs flagged by `apply_branding.py --check` before committing the merge.
