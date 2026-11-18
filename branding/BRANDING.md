# SANA Branding & Upstream Architecture

**SANA** — *Your Intelligent AI Assistant*  
Developed and maintained by **Q8iDevAI** (MIT License).

---

## 1. Visual Identity

- **Primary Black:** `#0B0B0F`
- **Primary Gold:** `#D4AF37` (Highlight `#E8C967`, Dim `#9E8022`)
- **Dark Secondary:** `#17171C`
- **Primary White:** `#FFFFFF`
- **Symbol:** Geometric interlocking **S** ribbon with an intelligent neural network nexus and orbital ring.

### Master Vector Assets (`branding/assets/`)

| File | Purpose |
|---|---|
| `sana-symbol-gold.svg` | Gold emblem on transparent background |
| `sana-symbol-black.svg` | Monochrome black emblem for light surfaces |
| `sana-symbol-white.svg` | Monochrome white emblem for dark/tinted surfaces |
| `sana-icon-dark.svg` | Dark squircle app icon (`#0B0B0F` + `#D4AF37`) |
| `sana-icon-light.svg` | Light squircle app icon (`#FFFFFF` + `#0B0B0F` + `#D4AF37`) |
| `sana-logo-primary.svg` | Horizontal dark lockup (`SANA` + tagline + `Q8iDevAI`) |
| `sana-logo-light.svg` | Horizontal light lockup |
| `sana-logo-secondary.svg` | Vertical stacked lockup |
| `sana-banner.svg` | 1280×360 README & hero banner |
| `sana-splash.svg` | 800×500 splash/loading graphic |
| `sana-installer-sidebar.svg` | 164×314 Windows installer sidebar |

Generated raster assets (PNG at 16–1024 px, multi-res `.ico`, `.icns`, MSIX tiles, favicons) live in `branding/assets/rendered/` and are synced into `assets/`, `apps/desktop/`, `apps/bootstrap-installer/`, `web/`, and `website/`.

---

## 2. Central Configuration & Idempotent Rebranding

- **`branding/sana.config.json`**: Single source of truth for names, taglines, developer attribution, CLI command, desktop bundle IDs, installer metadata, and theme hex values.
- **`sana_branding.py`**: Import-safe Python module reading `branding/sana.config.json` with built-in defaults.
- **`branding/scripts/generate_brand_assets.py`**: Reproducible SVG → PNG/ICO/ICNS/MSIX generator.
- **`branding/scripts/apply_branding.py`**: Idempotent rebranding tool.

### Commands

```bash
# Apply SANA branding and regenerate assets (safe to run repeatedly)
python branding/scripts/apply_branding.py

# Verify branding state without modifying files (CI / post-merge check)
python branding/scripts/apply_branding.py --check
```

---

## 3. Compatibility & Exception Policy

To preserve 100% compatibility with upstream plugins, skills, tests, and safe migration from existing Hermes installations:

1. **Internal Python package names** (`hermes_cli`, `hermes_constants`, `hermes_state`, `hermes_platform`, `hermes_scope`) are preserved.
2. **CLI entry points:** `sana` and `sana-acp` are the primary commands; `hermes`, `hermes-agent`, and `hermes-acp` remain as backward-compatible aliases.
3. **Environment & Data directories:** `SANA_HOME` (`~/.sana` on POSIX, `%LOCALAPPDATA%\sana` on Windows) is primary; `HERMES_HOME` is honored when explicitly set for compatibility.
4. **Licensing & Attribution:** `LICENSE` (MIT © 2025 Nous Research) and upstream copyright notices are preserved verbatim.
