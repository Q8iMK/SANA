#!/usr/bin/env python3
"""Generate all SANA visual assets (PNG, ICO, ICNS, MSIX tiles, web/desktop/installer icons).

Usage:
    python branding/scripts/generate_brand_assets.py [--check]

Uses ``resvg_py`` + ``Pillow`` when available, and automatically falls back on
Windows to Microsoft Edge headless (SVG -> PNG) + .NET ``System.Drawing``
(high-quality bicubic resize/composite) + pure-Python ICO/ICNS containers when
native Python wheels are unavailable or restricted by App Control.
"""

from __future__ import annotations

import argparse
import io
import os
import shutil
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    import resvg_py
    from PIL import Image

    _HAS_NATIVE_RENDERER = True
except (ImportError, OSError):
    _HAS_NATIVE_RENDERER = False

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BRAND_ASSETS = REPO_ROOT / "branding" / "assets"
RENDERED_DIR = BRAND_ASSETS / "rendered"

ICO_SIZES = [16, 24, 32, 48, 64, 128, 256]
FAVICON_SIZES = [16, 32, 48]
ICNS_CHUNKS: list[tuple[int, bytes]] = [
    (16, b"icp4"),
    (32, b"icp5"),
    (64, b"icp6"),
    (128, b"ic07"),
    (256, b"ic08"),
    (512, b"ic09"),
    (1024, b"ic10"),
]

APPX_SCALES = [
    ("100", 1.0, ""),
    ("125", 1.25, ".scale-125"),
    ("150", 1.5, ".scale-150"),
    ("200", 2.0, ".scale-200"),
    ("400", 4.0, ".scale-400"),
]
APPX_TARGET_SIZES = [16, 20, 24, 30, 32, 36, 40, 48, 60, 64, 72, 80, 96, 256]


def _find_edge_binary() -> str | None:
    candidates = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        shutil.which("msedge") or "",
        shutil.which("chrome") or "",
    ]
    for c in candidates:
        if c and Path(c).is_file():
            return c
    return None


def _render_svg_edge(svg_path: Path, width: int, height: int, dest_png: Path) -> None:
    edge = _find_edge_binary()
    if not edge:
        raise RuntimeError("Neither resvg_py/PIL nor Microsoft Edge/Chrome was found for SVG rendering.")
    dest_png.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="sana_svg_") as tmp:
        tmp_dir = Path(tmp)
        html_path = tmp_dir / "render.html"
        ud_dir = tmp_dir / "ud"
        svg_uri = svg_path.resolve().as_uri()
        html_path.write_text(
            (
                "<style>html,body{margin:0;padding:0;background:transparent;overflow:hidden}</style>"
                f'<img src="{svg_uri}" width="{width}" height="{height}">'
            ),
            encoding="utf-8",
        )
        cmd = [
            edge,
            "--headless",
            "--disable-gpu",
            f"--user-data-dir={ud_dir}",
            "--default-background-color=00000000",
            f"--window-size={width},{height}",
            f"--screenshot={dest_png}",
            html_path.resolve().as_uri(),
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=120)
        if res.returncode != 0 or not dest_png.is_file():
            raise RuntimeError(f"Edge SVG render failed for {svg_path.name}: {res.stderr}")


def _ps_resize_batch(jobs: list[tuple[Path, Path, int, int, str]]) -> None:
    """Batch-resize PNGs (and optionally save BMP) using .NET System.Drawing."""
    if not jobs:
        return
    lines = [
        "Add-Type -AssemblyName System.Drawing",
        "function Resize-Img($src, $dst, $w, $h, $fmt) {",
        "  $dir = Split-Path -Parent $dst",
        "  if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }",
        "  $img = [System.Drawing.Image]::FromFile($src)",
        "  $bmp = New-Object System.Drawing.Bitmap($w, $h)",
        "  $g = [System.Drawing.Graphics]::FromImage($bmp)",
        "  $g.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic",
        "  $g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::HighQuality",
        "  $g.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality",
        "  $g.Clear([System.Drawing.Color]::Transparent)",
        "  $g.DrawImage($img, 0, 0, $w, $h)",
        "  if ($fmt -eq 'BMP') { $bmp.Save($dst, [System.Drawing.Imaging.ImageFormat]::Bmp) }",
        "  else { $bmp.Save($dst, [System.Drawing.Imaging.ImageFormat]::Png) }",
        "  $g.Dispose(); $bmp.Dispose(); $img.Dispose()",
        "}",
    ]
    for src, dst, w, h, fmt in jobs:
        s = str(src).replace("'", "''")
        d = str(dst).replace("'", "''")
        lines.append(f"Resize-Img '{s}' '{d}' {w} {h} '{fmt}'")

    with tempfile.NamedTemporaryFile("w", suffix=".ps1", delete=False, encoding="utf-8") as tf:
        tf.write("\n".join(lines))
        ps_path = tf.name
    try:
        res = subprocess.run(
            ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", ps_path],
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
        if res.returncode != 0:
            raise RuntimeError(f"PowerShell resize failed: {res.stderr}\n{res.stdout}")
    finally:
        try:
            os.unlink(ps_path)
        except OSError:
            pass


def _ps_wide_tile(src_icon: Path, dst: Path, w: int, h: int) -> None:
    """Create a wide MSIX tile with #0B0B0F background and centered icon."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    icon_dim = int(h * 0.72)
    x = (w - icon_dim) // 2
    y = (h - icon_dim) // 2
    s = str(src_icon).replace("'", "''")
    d = str(dst).replace("'", "''")
    script = (
        "Add-Type -AssemblyName System.Drawing; "
        f"$img = [System.Drawing.Image]::FromFile('{s}'); "
        f"$bmp = New-Object System.Drawing.Bitmap({w}, {h}); "
        "$g = [System.Drawing.Graphics]::FromImage($bmp); "
        "$g.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic; "
        "$g.Clear([System.Drawing.Color]::FromArgb(255, 11, 11, 15)); "
        f"$g.DrawImage($img, {x}, {y}, {icon_dim}, {icon_dim}); "
        f"$bmp.Save('{d}', [System.Drawing.Imaging.ImageFormat]::Png); "
        "$g.Dispose(); $bmp.Dispose(); $img.Dispose()"
    )
    subprocess.run(
        ["powershell.exe", "-NoProfile", "-Command", script],
        check=True,
        capture_output=True,
        timeout=120,
    )


def write_ico_from_pngs(sized_pngs: list[tuple[int, bytes]], dest: Path) -> None:
    """Build a standard Vista+ PNG-backed multi-resolution .ico file."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    count = len(sized_pngs)
    header = struct.pack("<HHH", 0, 1, count)
    offset = 6 + 16 * count
    entries = bytearray()
    payload = bytearray()
    for size, data in sized_pngs:
        dim = 0 if size >= 256 else size
        entries.extend(struct.pack("<BBBBHHII", dim, dim, 0, 0, 1, 32, len(data), offset))
        payload.extend(data)
        offset += len(data)
    dest.write_bytes(header + bytes(entries) + bytes(payload))


def write_icns_from_pngs(png_by_size: dict[int, bytes], dest: Path) -> None:
    """Build a standard macOS .icns container from PNG chunks."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    body = bytearray()
    for size, ostype in ICNS_CHUNKS:
        data = png_by_size.get(size)
        if not data:
            continue
        body.extend(ostype)
        body.extend(struct.pack(">I", 8 + len(data)))
        body.extend(data)
    total_len = 8 + len(body)
    dest.write_bytes(b"icns" + struct.pack(">I", total_len) + bytes(body))


def _generate_with_native() -> list[Path]:
    """Fast path using resvg_py + Pillow."""
    def render(svg: Path, w: int, h: int) -> Image.Image:
        png = resvg_py.svg_to_bytes(svg_string=svg.read_text(encoding="utf-8"), width=w, height=h)
        return Image.open(io.BytesIO(png)).convert("RGBA")

    def png_bytes(img: Image.Image, size: int) -> bytes:
        buf = io.BytesIO()
        resized = img.resize((size, size), Image.Resampling.LANCZOS) if img.size != (size, size) else img
        resized.save(buf, format="PNG")
        return buf.getvalue()

    def save_png(img: Image.Image, dest: Path, size: tuple[int, int] | None = None) -> None:
        dest.parent.mkdir(parents=True, exist_ok=True)
        out = img.resize(size, Image.Resampling.LANCZOS) if size and img.size != size else img
        out.save(dest, format="PNG")

    icon_dark = render(BRAND_ASSETS / "sana-icon-dark.svg", 1024, 1024)
    icon_light = render(BRAND_ASSETS / "sana-icon-light.svg", 1024, 1024)
    sym_gold = render(BRAND_ASSETS / "sana-symbol-gold.svg", 1024, 1024)
    sym_black = render(BRAND_ASSETS / "sana-symbol-black.svg", 1024, 1024)
    sym_white = render(BRAND_ASSETS / "sana-symbol-white.svg", 1024, 1024)
    banner = render(BRAND_ASSETS / "sana-banner.svg", 1280, 360)
    splash = render(BRAND_ASSETS / "sana-splash.svg", 800, 500)
    logo_p = render(BRAND_ASSETS / "sana-logo-primary.svg", 960, 260)
    logo_l = render(BRAND_ASSETS / "sana-logo-light.svg", 960, 260)
    logo_s = render(BRAND_ASSETS / "sana-logo-secondary.svg", 512, 512)
    sidebar = render(BRAND_ASSETS / "sana-installer-sidebar.svg", 164, 314)

    RENDERED_DIR.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for sz in [16, 24, 32, 48, 64, 128, 180, 256, 512, 1024]:
        for tag, im in [("dark", icon_dark), ("light", icon_light)]:
            p = RENDERED_DIR / f"sana-icon-{tag}-{sz}.png"
            save_png(im, p, (sz, sz))
            written.append(p)

    for fn, im in [
        ("sana-banner.png", banner),
        ("sana-splash.png", splash),
        ("sana-logo-primary.png", logo_p),
        ("sana-logo-light.png", logo_l),
        ("sana-logo-secondary.png", logo_s),
        ("sana-installer-sidebar.png", sidebar),
    ]:
        p = RENDERED_DIR / fn
        save_png(im, p)
        written.append(p)
    sidebar.convert("RGB").save(RENDERED_DIR / "sana-installer-sidebar.bmp", format="BMP")

    dark_ico = [(s, png_bytes(icon_dark, s)) for s in ICO_SIZES]
    light_ico = [(s, png_bytes(icon_light, s)) for s in ICO_SIZES]
    fav_ico = [(s, png_bytes(icon_dark, s)) for s in FAVICON_SIZES]
    dark_icns = {s: png_bytes(icon_dark, s) for s, _ in ICNS_CHUNKS}
    light_icns = {s: png_bytes(icon_light, s) for s, _ in ICNS_CHUNKS}

    write_ico_from_pngs(dark_ico, RENDERED_DIR / "sana-dark.ico")
    write_ico_from_pngs(light_ico, RENDERED_DIR / "sana-light.ico")
    write_icns_from_pngs(dark_icns, RENDERED_DIR / "sana-dark.icns")
    write_icns_from_pngs(light_icns, RENDERED_DIR / "sana-light.icns")

    _sync_targets_from_rendered(
        icon_dark_1024=RENDERED_DIR / "sana-icon-dark-1024.png",
        icon_light_1024=RENDERED_DIR / "sana-icon-light-1024.png",
        dark_ico=dark_ico,
        fav_ico=fav_ico,
        dark_icns=dark_icns,
        sym_gold_fn=lambda p: save_png(sym_gold, p, (1024, 1024)),
        sym_black_fn=lambda p: save_png(sym_black, p, (1024, 1024)),
        sym_white_fn=lambda p: save_png(sym_white.convert("LA").convert("RGBA"), p, (1024, 1024)),
        resize_fn=lambda src, dst, w, h: save_png(Image.open(src), dst, (w, h)),
        wide_tile_fn=lambda src, dst, w, h: _native_wide_tile(Image.open(src), dst, w, h),
    )
    return written


def _native_wide_tile(mark: Image.Image, dst: Path, w: int, h: int) -> None:
    canvas = Image.new("RGBA", (w, h), (11, 11, 15, 255))
    icon_dim = int(h * 0.72)
    resized = mark.resize((icon_dim, icon_dim), Image.Resampling.LANCZOS)
    canvas.alpha_composite(resized, ((w - icon_dim) // 2, (h - icon_dim) // 2))
    dst.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(dst, format="PNG")


def _generate_with_edge() -> list[Path]:
    """Windows fallback renderer using Microsoft Edge headless + .NET System.Drawing."""
    RENDERED_DIR.mkdir(parents=True, exist_ok=True)
    dark_1024 = RENDERED_DIR / "sana-icon-dark-1024.png"
    light_1024 = RENDERED_DIR / "sana-icon-light-1024.png"

    with tempfile.TemporaryDirectory(prefix="sana_sym_") as tmp:
        tmp_dir = Path(tmp)
        sym_gold_1024 = tmp_dir / "sym-gold.png"
        sym_black_1024 = tmp_dir / "sym-black.png"
        sym_white_1024 = tmp_dir / "sym-white.png"

        renders = [
            (BRAND_ASSETS / "sana-icon-dark.svg", 1024, 1024, dark_1024),
            (BRAND_ASSETS / "sana-icon-light.svg", 1024, 1024, light_1024),
            (BRAND_ASSETS / "sana-symbol-gold.svg", 1024, 1024, sym_gold_1024),
            (BRAND_ASSETS / "sana-symbol-black.svg", 1024, 1024, sym_black_1024),
            (BRAND_ASSETS / "sana-symbol-white.svg", 1024, 1024, sym_white_1024),
            (BRAND_ASSETS / "sana-banner.svg", 1280, 360, RENDERED_DIR / "sana-banner.png"),
            (BRAND_ASSETS / "sana-splash.svg", 800, 500, RENDERED_DIR / "sana-splash.png"),
            (BRAND_ASSETS / "sana-logo-primary.svg", 960, 260, RENDERED_DIR / "sana-logo-primary.png"),
            (BRAND_ASSETS / "sana-logo-light.svg", 960, 260, RENDERED_DIR / "sana-logo-light.png"),
            (BRAND_ASSETS / "sana-logo-secondary.svg", 512, 512, RENDERED_DIR / "sana-logo-secondary.png"),
            (BRAND_ASSETS / "sana-installer-sidebar.svg", 164, 314, RENDERED_DIR / "sana-installer-sidebar.png"),
        ]
        for svg, w, h, dst in renders:
            _render_svg_edge(svg, w, h, dst)

        resize_jobs: list[tuple[Path, Path, int, int, str]] = [
            (RENDERED_DIR / "sana-installer-sidebar.png", RENDERED_DIR / "sana-installer-sidebar.bmp", 164, 314, "BMP")
        ]
        for sz in [16, 24, 32, 48, 64, 128, 180, 256, 512]:
            resize_jobs.append((dark_1024, RENDERED_DIR / f"sana-icon-dark-{sz}.png", sz, sz, "PNG"))
            resize_jobs.append((light_1024, RENDERED_DIR / f"sana-icon-light-{sz}.png", sz, sz, "PNG"))
        _ps_resize_batch(resize_jobs)

        dark_ico = [(s, (RENDERED_DIR / f"sana-icon-dark-{s}.png").read_bytes()) for s in ICO_SIZES]
        light_ico = [(s, (RENDERED_DIR / f"sana-icon-light-{s}.png").read_bytes()) for s in ICO_SIZES]
        fav_ico = [(s, (RENDERED_DIR / f"sana-icon-dark-{s}.png").read_bytes()) for s in FAVICON_SIZES]
        dark_icns = {s: (RENDERED_DIR / f"sana-icon-dark-{s}.png").read_bytes() for s, _ in ICNS_CHUNKS}
        light_icns = {s: (RENDERED_DIR / f"sana-icon-light-{s}.png").read_bytes() for s, _ in ICNS_CHUNKS}

        write_ico_from_pngs(dark_ico, RENDERED_DIR / "sana-dark.ico")
        write_ico_from_pngs(light_ico, RENDERED_DIR / "sana-light.ico")
        write_icns_from_pngs(dark_icns, RENDERED_DIR / "sana-dark.icns")
        write_icns_from_pngs(light_icns, RENDERED_DIR / "sana-light.icns")

        deferred_resizes: list[tuple[Path, Path, int, int, str]] = []
        deferred_wide: list[tuple[Path, Path, int, int]] = []

        _sync_targets_from_rendered(
            icon_dark_1024=dark_1024,
            icon_light_1024=light_1024,
            dark_ico=dark_ico,
            fav_ico=fav_ico,
            dark_icns=dark_icns,
            sym_gold_fn=lambda p: (p.parent.mkdir(parents=True, exist_ok=True), shutil.copyfile(sym_gold_1024, p)),
            sym_black_fn=lambda p: (p.parent.mkdir(parents=True, exist_ok=True), shutil.copyfile(sym_black_1024, p)),
            sym_white_fn=lambda p: (p.parent.mkdir(parents=True, exist_ok=True), shutil.copyfile(sym_white_1024, p)),
            resize_fn=lambda src, dst, w, h: deferred_resizes.append((src, dst, w, h, "PNG")),
            wide_tile_fn=lambda src, dst, w, h: deferred_wide.append((src, dst, w, h)),
        )
        _ps_resize_batch(deferred_resizes)
        for src, dst, w, h in deferred_wide:
            _ps_wide_tile(src, dst, w, h)

    return sorted(RENDERED_DIR.glob("*"))


def _sync_targets_from_rendered(
    *,
    icon_dark_1024: Path,
    icon_light_1024: Path,
    dark_ico: list[tuple[int, bytes]],
    fav_ico: list[tuple[int, bytes]],
    dark_icns: dict[int, bytes],
    sym_gold_fn,
    sym_black_fn,
    sym_white_fn,
    resize_fn,
    wide_tile_fn,
) -> None:
    # Root assets/
    root_assets = REPO_ROOT / "assets"
    shutil.copyfile(BRAND_ASSETS / "sana-icon-light.svg", root_assets / "icon-master.svg")
    shutil.copyfile(BRAND_ASSETS / "sana-icon-dark.svg", root_assets / "icon-master-dark.svg")
    shutil.copyfile(RENDERED_DIR / "sana-banner.png", root_assets / "banner.png")
    shutil.copyfile(RENDERED_DIR / "sana-splash.png", root_assets / "splash.png")
    resize_fn(icon_dark_1024, root_assets / "dmg-volume.png", 512, 512)

    # Desktop app
    desktop_assets = REPO_ROOT / "apps" / "desktop" / "assets"
    shutil.copyfile(icon_dark_1024, desktop_assets / "icon.png")
    shutil.copyfile(icon_dark_1024, desktop_assets / "icon-dark.png")
    shutil.copyfile(icon_dark_1024, desktop_assets / "icon-mac.png")
    write_ico_from_pngs(dark_ico, desktop_assets / "icon.ico")
    write_ico_from_pngs(dark_ico, desktop_assets / "icon-dark.ico")
    write_icns_from_pngs(dark_icns, desktop_assets / "icon.icns")
    write_icns_from_pngs(dark_icns, desktop_assets / "icon-dark.icns")

    dmg_icns = REPO_ROOT / "apps" / "desktop" / "packaging" / "dmg-volume.icns"
    if dmg_icns.parent.exists():
        write_icns_from_pngs(dark_icns, dmg_icns)

    icon_composer = desktop_assets / "icon.icon" / "Assets"
    if icon_composer.exists():
        sym_gold_fn(icon_composer / "art-dark.png")
        sym_black_fn(icon_composer / "art-light.png")
        sym_white_fn(icon_composer / "mono.png")

    appx_dir = desktop_assets / "appx"
    if appx_dir.exists():
        for _, factor, suffix in APPX_SCALES:
            for base_name, base_dim in [("Square150x150Logo", 150), ("Square44x44Logo", 44), ("StoreLogo", 50)]:
                dim = round(base_dim * factor)
                resize_fn(icon_dark_1024, appx_dir / f"{base_name}{suffix}.png", dim, dim)
            wide_tile_fn(icon_dark_1024, appx_dir / f"Wide310x150Logo{suffix}.png", round(310 * factor), round(150 * factor))
        for size in APPX_TARGET_SIZES:
            resize_fn(icon_dark_1024, appx_dir / f"Square44x44Logo.targetsize-{size}.png", size, size)
            resize_fn(icon_dark_1024, appx_dir / f"Square44x44Logo.targetsize-{size}_altform-unplated.png", size, size)
            resize_fn(icon_light_1024, appx_dir / f"Square44x44Logo.targetsize-{size}_altform-lightunplated.png", size, size)

    desktop_public = REPO_ROOT / "apps" / "desktop" / "public"
    if desktop_public.exists():
        resize_fn(icon_dark_1024, desktop_public / "apple-touch-icon.png", 180, 180)
        resize_fn(icon_dark_1024, desktop_public / "sana-mark.png", 256, 256)
        resize_fn(icon_light_1024, desktop_public / "sana-mark-light.png", 256, 256)
        resize_fn(icon_light_1024, desktop_public / "nous-girl.png", 256, 256)
        resize_fn(icon_dark_1024, desktop_public / "nous-girl-dark.png", 256, 256)

    # Bootstrap installer
    tauri_icons = REPO_ROOT / "apps" / "bootstrap-installer" / "src-tauri" / "icons"
    if tauri_icons.exists():
        resize_fn(icon_dark_1024, tauri_icons / "32x32.png", 32, 32)
        resize_fn(icon_dark_1024, tauri_icons / "128x128.png", 128, 128)
        resize_fn(icon_dark_1024, tauri_icons / "128x128@2x.png", 256, 256)
        write_ico_from_pngs(dark_ico, tauri_icons / "icon.ico")
        write_icns_from_pngs(dark_icns, tauri_icons / "icon.icns")
        tauri_composer = tauri_icons / "icon.icon" / "Assets"
        if tauri_composer.exists():
            sym_gold_fn(tauri_composer / "art-dark.png")
            sym_black_fn(tauri_composer / "art-light.png")
            sym_white_fn(tauri_composer / "mono.png")

    installer_public = REPO_ROOT / "apps" / "bootstrap-installer" / "public"
    if installer_public.exists():
        resize_fn(icon_dark_1024, installer_public / "sana-mark.png", 256, 256)
        resize_fn(icon_dark_1024, installer_public / "nous-girl.png", 256, 256)

    # Web dashboard
    web_public = REPO_ROOT / "web" / "public"
    if web_public.exists():
        write_ico_from_pngs(fav_ico, web_public / "favicon.ico")
        shutil.copyfile(BRAND_ASSETS / "sana-icon-dark.svg", web_public / "favicon.svg")
        resize_fn(icon_dark_1024, web_public / "apple-touch-icon.png", 180, 180)

    # Website docs
    website_img = REPO_ROOT / "website" / "static" / "img"
    if website_img.exists():
        sym_black_fn(website_img / "logo.png")
        sym_gold_fn(website_img / "logo-dark.png")
        resize_fn(icon_light_1024, website_img / "nous-logo.png", 150, 150)
        resize_fn(icon_dark_1024, website_img / "nous-logo-dark.png", 150, 150)
        resize_fn(icon_dark_1024, website_img / "favicon-16x16.png", 16, 16)
        resize_fn(icon_dark_1024, website_img / "favicon-32x32.png", 32, 32)
        resize_fn(icon_dark_1024, website_img / "apple-touch-icon.png", 180, 180)
        write_ico_from_pngs(fav_ico, website_img / "favicon.ico")
        shutil.copyfile(BRAND_ASSETS / "sana-icon-dark.svg", website_img / "favicon.svg")


def generate_all(check_only: bool = False) -> list[Path]:
    required_svgs = [
        "sana-symbol-gold.svg",
        "sana-symbol-black.svg",
        "sana-symbol-white.svg",
        "sana-icon-dark.svg",
        "sana-icon-light.svg",
        "sana-logo-primary.svg",
        "sana-logo-light.svg",
        "sana-logo-secondary.svg",
        "sana-banner.svg",
        "sana-splash.svg",
        "sana-installer-sidebar.svg",
    ]
    for name in required_svgs:
        p = BRAND_ASSETS / name
        if not p.exists():
            raise FileNotFoundError(f"Missing SANA SVG master: {p}")

    if check_only:
        expected = [
            REPO_ROOT / "assets" / "banner.png",
            REPO_ROOT / "assets" / "icon-master.svg",
            REPO_ROOT / "assets" / "icon-master-dark.svg",
            REPO_ROOT / "apps" / "desktop" / "assets" / "icon.ico",
            REPO_ROOT / "apps" / "desktop" / "assets" / "icon.icns",
            REPO_ROOT / "apps" / "desktop" / "assets" / "icon.png",
            REPO_ROOT / "apps" / "desktop" / "assets" / "icon-dark.png",
            REPO_ROOT / "apps" / "bootstrap-installer" / "src-tauri" / "icons" / "icon.ico",
            REPO_ROOT / "web" / "public" / "favicon.ico",
            RENDERED_DIR / "sana-icon-dark-1024.png",
            RENDERED_DIR / "sana-dark.ico",
            RENDERED_DIR / "sana-dark.icns",
        ]
        missing = [p for p in expected if not p.exists()]
        if missing:
            raise FileNotFoundError("Missing generated assets: " + ", ".join(str(m) for m in missing))
        return expected

    if _HAS_NATIVE_RENDERER:
        return _generate_with_native()
    return _generate_with_edge()


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate SANA brand assets.")
    parser.add_argument("--check", action="store_true", help="Verify generated assets exist.")
    args = parser.parse_args()
    paths = generate_all(check_only=args.check)
    mode = "Verified" if args.check else "Generated"
    print(f"[SANA Branding] {mode} brand assets ({len(paths)} artifacts).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
