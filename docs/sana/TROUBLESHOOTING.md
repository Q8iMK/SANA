# SANA Troubleshooting Guide

## 1. Windows Application Control blocks `.venv\Scripts\python.exe` or `.pyd` extensions
If Windows Smart App Control / WDAC blocks newly downloaded binaries in `.venv`:
- Use the system Python with `.venv\Lib\site-packages` on `PYTHONPATH`:
  ```powershell
  $env:PYTHONPATH = ".;.venv\Lib\site-packages"
  python -m pytest branding/tests/ -v
  ```
- `sana.cmd` automatically configures `PYTHONPATH` to work with system `python`.
- `branding/scripts/generate_brand_assets.py` automatically falls back to Microsoft Edge headless + `.NET System.Drawing` when `resvg_py` / `Pillow` native extensions are blocked.

## 2. PowerShell `npm.ps1 cannot be loaded because running scripts is disabled`
Invoke Node package managers via `cmd /c`:
```powershell
cmd /c "npm --version"
cmd /c "pnpm --version"
```

## 3. Re-applying Branding After Pulling Changes
Run:
```bash
python branding/scripts/apply_branding.py
python branding/scripts/apply_branding.py --check
```
