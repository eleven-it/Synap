"""
Genera iconos PWA en theme/static/img/pwa/ desde logo AdministraNET/Synap.

Fuente (prioridad):
1. Logo más reciente Logo_Signo_administraNET* en MEDIA/empresas/logos
2. Fallback theme/static/img/brand/logo_signo_administranet.png
3. --source /path/logo.png

Uso: docker exec Synap_app python manage.py generate_pwa_icons
"""
import os
import re
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from PIL import Image, ImageDraw, ImageFont


ICON_SIZES = (72, 96, 128, 144, 152, 180, 192, 384, 512)
MASKABLE_SIZES = {192, 512}
MASKABLE_SAFE_RATIO = 0.80
BRAND_FALLBACK_REL = Path("theme/static/img/brand/logo_signo_administranet.png")
PWA_OUT_REL = Path("theme/static/img/pwa")


def _project_root() -> Path:
    return Path(settings.BASE_DIR)


def _resolve_logo_from_media() -> Path | None:
    logos_dir = Path(settings.MEDIA_ROOT) / "empresas" / "logos"
    if not logos_dir.is_dir():
        return None
    candidates = []
    for filename in logos_dir.iterdir():
        if not filename.is_file():
            continue
        name = filename.name
        if "Logo_Signo_administraNET" in name and name.lower().endswith(
            (".png", ".jpg", ".jpeg", ".webp")
        ):
            candidates.append((filename.stat().st_mtime, filename))
    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates[0][1]


def _extract_png_from_svg(svg_path: Path, dest: Path) -> bool:
    try:
        text = svg_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return False
    match = re.search(
        r'xlink:href="data:image/png;base64,([^"]+)"',
        text,
    )
    if not match:
        return False
    import base64

    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(base64.b64decode(match.group(1)))
    return dest.is_file()


def _ensure_brand_fallback(root: Path) -> Path:
    fallback = root / BRAND_FALLBACK_REL
    if fallback.is_file():
        return fallback

    media_logo = _resolve_logo_from_media()
    if media_logo and media_logo.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"):
        fallback.parent.mkdir(parents=True, exist_ok=True)
        with Image.open(media_logo) as img:
            img.convert("RGBA").save(fallback, format="PNG")
        return fallback

    synap_svg = Path(settings.MEDIA_ROOT) / "empresas" / "logos" / "Logo_Synap.svg"
    if synap_svg.is_file() and _extract_png_from_svg(synap_svg, fallback):
        return fallback

    fallback.parent.mkdir(parents=True, exist_ok=True)
    size = 512
    img = Image.new("RGBA", (size, size), (127, 19, 236, 255))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 220)
    except OSError:
        font = ImageFont.load_default()
    draw.text((size // 2, size // 2), "S", fill=(255, 255, 255, 255), font=font, anchor="mm")
    img.save(fallback, format="PNG")
    return fallback


def _open_logo(source: Path) -> Image.Image:
    with Image.open(source) as img:
        return img.convert("RGBA")


def _fit_logo(canvas: Image.Image, logo: Image.Image, safe_ratio: float) -> None:
    cw, ch = canvas.size
    max_w = int(cw * safe_ratio)
    max_h = int(ch * safe_ratio)
    lw, lh = logo.size
    scale = min(max_w / lw, max_h / lh)
    new_size = (max(1, int(lw * scale)), max(1, int(lh * scale)))
    resized = logo.resize(new_size, Image.Resampling.LANCZOS)
    x = (cw - new_size[0]) // 2
    y = (ch - new_size[1]) // 2
    canvas.paste(resized, (x, y), resized)


def _render_icon(logo: Image.Image, size: int, *, maskable: bool) -> Image.Image:
    canvas = Image.new("RGBA", (size, size), (127, 19, 236, 255))
    ratio = MASKABLE_SAFE_RATIO if maskable else 0.92
    _fit_logo(canvas, logo, ratio)
    return canvas


class Command(BaseCommand):
    help = "Genera iconos PWA PNG en theme/static/img/pwa/"

    def add_arguments(self, parser):
        parser.add_argument(
            "--source",
            type=str,
            default="",
            help="Ruta opcional al logo fuente (PNG/JPG)",
        )

    def handle(self, *args, **options):
        root = _project_root()
        out_dir = root / PWA_OUT_REL
        out_dir.mkdir(parents=True, exist_ok=True)

        source_opt = (options.get("source") or "").strip()
        if source_opt:
            source = Path(source_opt)
            if not source.is_file():
                self.stderr.write(self.style.ERROR(f"Fuente no encontrada: {source}"))
                return
        else:
            source = _resolve_logo_from_media()
            if source is None:
                source = _ensure_brand_fallback(root)
            self.stdout.write(f"Logo fuente: {source}")

        logo = _open_logo(source)
        generated = []
        for size in ICON_SIZES:
            maskable = size in MASKABLE_SIZES
            icon = _render_icon(logo, size, maskable=maskable)
            out_path = out_dir / f"icon-{size}.png"
            icon.save(out_path, format="PNG")
            generated.append(out_path.name)

        self.stdout.write(
            self.style.SUCCESS(
                f"Generados {len(generated)} iconos en {out_dir}: {', '.join(generated)}"
            )
        )
