# SANA Installation Guide

**SANA — Your Intelligent AI Assistant**  
Developed by **Q8iDevAI**

---

## Prerequisites

- **Python:** 3.11 – 3.14 (3.14 recommended)
- **uv:** Astral `uv` (`0.13+`) for fast locked Python environments
- **Node.js:** `>= 26` and **pnpm** `^12` (for Desktop, Web Dashboard, and TUI builds)
- **Git:** `2.40+`

---

## 1. Install SANA from Source

```bash
git clone <your-sana-repo-url> SANA
cd SANA

# Create and sync the locked Python environment
uv sync --locked --group dev --group test
```

### Verify the `sana` CLI

- **POSIX (Linux / macOS / WSL2):**
  ```bash
  .venv/bin/sana --version
  .venv/bin/sana --help
  ```
- **Windows (PowerShell / CMD):**
  ```powershell
  .\sana.cmd --version
  .\sana.cmd --help
  ```

---

## 2. Install SANA Desktop & Web Dashboard Dependencies

```bash
# Install workspace JS packages
pnpm install --frozen-lockfile

# Build Web Dashboard
pnpm --filter web build

# Build Desktop App (unpacked directory)
pnpm --filter hermes pack
```

---

## 3. Data Directory Locations

| Platform | SANA Home (`SANA_HOME`) | Legacy Hermes Home (`HERMES_HOME`) |
|---|---|---|
| Windows | `%LOCALAPPDATA%\sana` | `%LOCALAPPDATA%\hermes` |
| Linux / macOS / WSL2 | `~/.sana` | `~/.hermes` |

If you already have an existing Hermes installation, see the [Migration Guide](MIGRATION.md) to import your configuration, sessions, skills, plugins, and credentials safely.
