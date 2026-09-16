"""
generate_event_images.py
High-performance, broadcast-grade matchday graphic generator for football fixtures using Pillow.
Features:
- Modular, competition-specific theme engine with distinct palettes, geometries, and center devices
- 2x supersampled internal rendering (2400x1260 -> 1200x630 Lanczos) for razor-sharp antialiasing
- High-res team crests with aspect-ratio preservation, transparent border trimming, and back-glow
- Intelligent text-fitting and multi-line wrapping (no ugly blunt truncation)
- Vector-drawn calendar and clock icons (eliminating missing-glyph square boxes)
- Multi-threaded logo prefetching and concurrent rendering
- Preview gallery and contact sheet generator
"""

import hashlib
import io
import json
import logging
import math
import os
import re
import urllib.request
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, date
from typing import Dict, Any, Optional, Tuple, List, Set
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps

from image_themes import get_competition_theme, CompetitionTheme, THEMES_REGISTRY

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")
logger = logging.getLogger("generate_event_images")

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
CACHE_DIR = ".cache/logos"
FONT_DIR = "assets/fonts"


# ==============================================================================
# 1. Typography & Font Loading Engine
# ==============================================================================

def get_font(
    size: int,
    weight: str = "bold",
    family: str = "inter"
) -> ImageFont.FreeTypeFont:
    """
    Loads font with priority for bundled repository fonts (Inter, Montserrat, Archivo),
    applying the requested weight ('regular', 'semibold', 'bold', 'extrabold', 'black').
    """
    bundled_map = {
        "inter": os.path.join(FONT_DIR, "Inter.ttf"),
        "montserrat": os.path.join(FONT_DIR, "Montserrat.ttf"),
        "archivo": os.path.join(FONT_DIR, "Archivo.ttf")
    }

    target_path = bundled_map.get(family.lower(), bundled_map["inter"])
    if not os.path.exists(target_path):
        for b_path in bundled_map.values():
            if os.path.exists(b_path):
                target_path = b_path
                break

    if os.path.exists(target_path):
        try:
            f = ImageFont.truetype(target_path, size=size)
            # Map requested weight to font variation
            weight_map = {
                "regular": "Regular",
                "medium": "Medium",
                "semibold": "SemiBold",
                "bold": "Bold",
                "extrabold": "ExtraBold",
                "black": "Black"
            }
            target_var = weight_map.get(weight.lower(), "Bold")
            var_names = [v.decode() for v in f.get_variation_names()] if hasattr(f, "get_variation_names") else []
            if target_var in var_names:
                f.set_variation_by_name(target_var)
            elif "Bold" in var_names and weight != "regular":
                f.set_variation_by_name("Bold")
            return f
        except Exception:
            pass

    # Fallback to system fonts
    is_bold = weight.lower() in ["bold", "extrabold", "black", "semibold"]
    if is_bold:
        system_candidates = [
            "C:/Windows/Fonts/segoeuib.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/calibrib.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf",
            "/System/Library/Fonts/HelveticaNeue-Bold.otf"
        ]
    else:
        system_candidates = [
            "C:/Windows/Fonts/segoeui.ttf",
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/calibri.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf",
            "/System/Library/Fonts/HelveticaNeue.otf"
        ]

    for p in system_candidates:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size=size)
            except Exception:
                continue

    return ImageFont.load_default()


def fit_team_name_lines(
    name: str,
    max_width: int,
    initial_size: int = 60,
    min_size: int = 34,
    family: str = "inter"
) -> Tuple[List[str], ImageFont.FreeTypeFont, int]:
    """
    Intelligently fits a team name into 1 or 2 lines with optimal font sizing.
    Returns (lines_of_text, font_object, total_height).
    """
    clean_name = re.sub(r"\s+", " ", name.strip())

    # 1. Try single line with decreasing font sizes
    for size in range(initial_size, min_size - 1, -2):
        f = get_font(size=size, weight="bold", family=family)
        dummy_img = Image.new("RGBA", (1, 1))
        draw = ImageDraw.Draw(dummy_img)
        bbox = draw.textbbox((0, 0), clean_name, font=f)
        w = bbox[2] - bbox[0]
        if w <= max_width:
            h = bbox[3] - bbox[1]
            return [clean_name], f, h

    # 2. Split into two balanced lines
    words = clean_name.split(" ")
    if len(words) > 1:
        mid = (len(words) + 1) // 2
        line1 = " ".join(words[:mid])
        line2 = " ".join(words[mid:])

        for size in range(initial_size - 6, min_size - 1, -2):
            f = get_font(size=size, weight="bold", family=family)
            dummy_img = Image.new("RGBA", (1, 1))
            draw = ImageDraw.Draw(dummy_img)
            bbox1 = draw.textbbox((0, 0), line1, font=f)
            bbox2 = draw.textbbox((0, 0), line2, font=f)
            w1 = bbox1[2] - bbox1[0]
            w2 = bbox2[2] - bbox2[0]
            if max(w1, w2) <= max_width:
                h1 = bbox1[3] - bbox1[1]
                h2 = bbox2[3] - bbox2[1]
                return [line1, line2], f, h1 + h2 + 10

    # 3. Truncate with ellipsis at min_size as absolute final fallback
    f = get_font(size=min_size, weight="bold", family=family)
    truncated = clean_name
    dummy_img = Image.new("RGBA", (1, 1))
    draw = ImageDraw.Draw(dummy_img)
    while len(truncated) > 3:
        bbox = draw.textbbox((0, 0), truncated + "...", font=f)
        if (bbox[2] - bbox[0]) <= max_width:
            h = bbox[3] - bbox[1]
            return [truncated + "..."], f, h
        truncated = truncated[:-1]

    return [clean_name], f, 40


# ==============================================================================
# 2. Logo Caching and Pre-Processing
# ==============================================================================

def get_cache_path(team_name: str) -> str:
    os.makedirs(CACHE_DIR, exist_ok=True)
    clean_name = re.sub(r"[^a-zA-Z0-9]+", "_", team_name).lower()
    return os.path.join(CACHE_DIR, f"{clean_name}.png")


def autocrop_transparent_margins(img: Image.Image, padding: int = 6) -> Image.Image:
    """Removes empty transparent border around logos to maximize crest clarity and size."""
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    bbox = img.getbbox()
    if bbox:
        w, h = img.size
        x0 = max(0, bbox[0] - padding)
        y0 = max(0, bbox[1] - padding)
        x1 = min(w, bbox[2] + padding)
        y1 = min(h, bbox[3] + padding)
        return img.crop((x0, y0, x1, y1))
    return img


def download_or_cache_logo(url: str, team_name: str) -> Optional[Image.Image]:
    """Downloads team logo with local caching and returns a PIL Image."""
    if not url:
        return None

    cache_file = get_cache_path(team_name)
    if os.path.exists(cache_file):
        try:
            img = Image.open(cache_file).convert("RGBA")
            return autocrop_transparent_margins(img)
        except Exception:
            pass

    if os.path.exists(url):
        try:
            img = Image.open(url).convert("RGBA")
            img = autocrop_transparent_margins(img)
            img.save(cache_file)
            return img
        except Exception:
            return None

    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = resp.read()
            img = Image.open(io.BytesIO(data)).convert("RGBA")
            img = autocrop_transparent_margins(img)
            img.save(cache_file)
            return img
    except Exception as e:
        logger.debug(f"Could not download logo for {team_name} from {url}: {e}")
        return None


def prefetch_all_logos(events: List[Dict[str, Any]], max_workers: int = 16):
    """Pre-downloads all distinct team logos concurrently."""
    unique_teams: Dict[str, Tuple[str, str]] = {}
    for ev in events:
        for t_key in ["home_team", "away_team"]:
            team = ev.get(t_key, {})
            name = team.get("name")
            url = team.get("logo_url") or team.get("logo_resolution", {}).get("url")
            if name and name not in unique_teams and url:
                unique_teams[name] = (url, name)

    logger.info(f"Pre-fetching {len(unique_teams)} distinct team logos with {max_workers} worker threads...")
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(download_or_cache_logo, url, name): name for name, (url, name) in unique_teams.items()}
        for future in as_completed(futures):
            pass
    logger.info("Finished pre-fetching team logos.")


# ==============================================================================
# 3. Vector Icon Drawing (No Emoji Boxes)
# ==============================================================================

def draw_vector_calendar_icon(draw: ImageDraw.Draw, x: int, y: int, size: int = 36, color: Tuple[int, int, int] = (255, 255, 255)):
    """Renders a clean vector calendar icon directly with Pillow."""
    w = size
    h = int(size * 0.88)
    draw.rounded_rectangle([x, y + 6, x + w, y + h + 6], radius=6, fill=(color[0], color[1], color[2], 35), outline=color, width=3)
    draw.line([(x, y + 16), (x + w, y + 16)], fill=color, width=3)
    draw.line([(x + 8, y + 1), (x + 8, y + 9)], fill=color, width=3)
    draw.line([(x + w - 8, y + 1), (x + w - 8, y + 9)], fill=color, width=3)
    for gx in [x + 9, x + w // 2, x + w - 9]:
        for gy in [y + 24, y + 31]:
            draw.point((gx, gy), fill=color)


def draw_vector_clock_icon(draw: ImageDraw.Draw, x: int, y: int, size: int = 36, color: Tuple[int, int, int] = (255, 255, 255)):
    """Renders a clean vector clock icon directly with Pillow."""
    r = size // 2
    cx, cy = x + r, y + r + 3
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(color[0], color[1], color[2], 30), outline=color, width=3)
    draw.line([(cx, cy), (cx, cy - r + 6)], fill=color, width=3)
    draw.line([(cx, cy), (cx + r - 7, cy)], fill=color, width=3)
    draw.ellipse([cx - 3, cy - 3, cx + 3, cy + 3], fill=color)


# ==============================================================================
# 4. Procedural Background Generator
# ==============================================================================

def create_themed_background(
    theme: CompetitionTheme,
    width: int = 2400,
    height: int = 1260,
    seed_str: str = ""
) -> Image.Image:
    """
    Creates a layered procedural background tailored to the competition theme.
    All random visual elements are seeded deterministically from seed_str.
    """
    h_val = int(hashlib.md5((theme.competition_id + seed_str).encode("utf-8")).hexdigest()[:8], 16)

    # 1. Base Vertical Multi-stop Gradient
    img = Image.new("RGBA", (width, height), (theme.background_top[0], theme.background_top[1], theme.background_top[2], 255))
    draw = ImageDraw.Draw(img)

    r1, g1, b1 = theme.background_top
    r2, g2, b2 = theme.background_bottom
    for y in range(height):
        factor = y / height
        r = int(r1 + (r2 - r1) * factor)
        g = int(g1 + (g2 - g1) * factor)
        b = int(b1 + (b2 - b1) * factor)
        draw.line([(0, y), (width, y)], fill=(r, g, b, 255))

    # 2. Team Crest Soft Spotlights (left and right)
    spotlights = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    spot_draw = ImageDraw.Draw(spotlights)

    left_cx = width // 4 + 30
    right_cx = width * 3 // 4 - 30
    center_y = height // 2 - 40

    spot_r = 440
    pr, pg, pb = theme.primary
    sr, sg, sb = theme.secondary
    hr, hg, hb = theme.highlight

    for r in range(spot_r, 0, -20):
        alpha = int((1.0 - (r / spot_r)) * 48)
        spot_draw.ellipse([left_cx - r, center_y - r * 0.85, left_cx + r, center_y + r * 0.85], fill=(pr, pg, pb, alpha))
        spot_draw.ellipse([right_cx - r, center_y - r * 0.85, right_cx + r, center_y + r * 0.85], fill=(sr, sg, sb, alpha))

    img = Image.alpha_composite(img, spotlights)

    # 3. Competition-Specific Procedural Graphics
    pattern_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    pdraw = ImageDraw.Draw(pattern_layer)

    p = theme.pattern

    if p == "champions_stars":
        # Constellation lines & luminous silver particles
        stars = [
            (width * 0.12, height * 0.18), (width * 0.26, height * 0.12), (width * 0.38, height * 0.28),
            (width * 0.62, height * 0.28), (width * 0.74, height * 0.12), (width * 0.88, height * 0.18),
            (width * 0.5, height * 0.15), (width * 0.5, height * 0.78), (width * 0.18, height * 0.82),
            (width * 0.82, height * 0.82), (width * 0.34, height * 0.74), (width * 0.66, height * 0.74)
        ]
        for i in range(len(stars) - 1):
            pdraw.line([stars[i], stars[i + 1]], fill=(hr, hg, hb, 40), width=3)
        pdraw.line([stars[2], stars[6]], fill=(hr, hg, hb, 35), width=2)
        pdraw.line([stars[3], stars[6]], fill=(hr, hg, hb, 35), width=2)
        for sx, sy in stars:
            pdraw.ellipse([sx - 6, sy - 6, sx + 6, sy + 6], fill=(hr, hg, hb, 240))
            pdraw.ellipse([sx - 16, sy - 16, sx + 16, sy + 16], fill=(hr, hg, hb, 60))

    elif p == "europa_energy_ribbons":
        # Sweeping dynamic angular energy ribbons in warm amber/orange
        for i in range(6):
            offset_y = i * 140
            pts = [
                (0, height * 0.85 - offset_y),
                (width * 0.32, height * 0.62 - offset_y),
                (width * 0.68, height * 0.72 - offset_y),
                (width, height * 0.42 - offset_y)
            ]
            alpha = 25 + (i * 8)
            pdraw.line(pts, fill=(pr, pg, pb, alpha), width=10 + i * 2)

    elif p == "conference_curved_geometry":
        # Concentric dynamic curved turquoise & electric green waves
        for rad in range(260, 1100, 110):
            pdraw.arc([width // 2 - rad, -200, width // 2 + rad, height + 400], 0, 180, fill=(pr, pg, pb, 35), width=4)
            pdraw.arc([width // 2 - rad + 40, -160, width // 2 + rad + 40, height + 440], 0, 180, fill=(sr, sg, sb, 28), width=3)

    elif p == "pl_modern_light_trails":
        # Bold modern angled geometric polygons and cyan light trails
        pdraw.polygon([(0, 0), (width * 0.32, 0), (width * 0.16, height), (0, height)], fill=(pr, pg, pb, 20))
        pdraw.polygon([(width * 0.68, 0), (width, 0), (width, height), (width * 0.84, height)], fill=(sr, sg, sb, 20))
        pdraw.line([(width * 0.32, 0), (width * 0.16, height)], fill=(pr, pg, pb, 90), width=5)
        pdraw.line([(width * 0.68, 0), (width * 0.84, height)], fill=(sr, sg, sb, 90), width=5)

    elif p == "laliga_radial_spectrum":
        # Circular radial arcs with vivid multi-colour Spanish spectrum
        colors = [(255, 59, 48), (255, 204, 0), (48, 209, 88), (255, 140, 0)]
        for i, c in enumerate(colors):
            r_arc = 380 + i * 110
            pdraw.arc([width // 2 - r_arc, height // 2 - r_arc - 40, width // 2 + r_arc, height // 2 + r_arc - 40], -60 + i * 90, 45 + i * 90, fill=(c[0], c[1], c[2], 65), width=5)

    elif p == "seriea_metallic_angles":
        # Sharp diamond-cut architectural bevels and vertical metallic beams
        pdraw.line([(left_cx, 60), (left_cx, height - 100)], fill=(pr, pg, pb, 35), width=8)
        pdraw.line([(right_cx, 60), (right_cx, height - 100)], fill=(pr, pg, pb, 35), width=8)
        pdraw.polygon([(width // 2, 70), (width // 2 + 220, height // 2 - 40), (width // 2, height - 90), (width // 2 - 220, height // 2 - 40)], outline=(hr, hg, hb, 35), width=3)

    elif p == "bundesliga_diagonal_dynamics":
        # Aggressive dynamic diagonal slash blocks and red speed stripes
        for i in range(-2, 9):
            x_start = i * 320
            pdraw.line([(x_start, 0), (x_start + 450, height)], fill=(pr, pg, pb, 26), width=24)
        pdraw.polygon([(0, height - 160), (width * 0.45, height), (0, height)], fill=(pr, pg, pb, 35))

    elif p == "ligue1_geometric_frames":
        # Modern geometric framing and electric lime light guides
        pdraw.rectangle([70, 70, width - 70, height - 70], outline=(pr, pg, pb, 35), width=4)
        c_len = 110
        for cx_b, cy_b, dx, dy in [(70, 70, 1, 1), (width - 70, 70, -1, 1), (70, height - 70, 1, -1), (width - 70, height - 70, -1, -1)]:
            pdraw.line([(cx_b, cy_b), (cx_b + dx * c_len, cy_b)], fill=(pr, pg, pb, 190), width=6)
            pdraw.line([(cx_b, cy_b), (cx_b, cy_b + dy * c_len)], fill=(pr, pg, pb, 190), width=6)

    elif p == "championship_stadium_atmosphere":
        # Powerful stadium floodlight beam overlay & steel grid lines
        pdraw.polygon([(0, 0), (left_cx + 140, height), (left_cx - 140, height)], fill=(255, 255, 255, 22))
        pdraw.polygon([(width, 0), (right_cx + 140, height), (right_cx - 140, height)], fill=(255, 255, 255, 22))
        pdraw.line([(0, height // 2 - 40), (width, height // 2 - 40)], fill=(pr, pg, pb, 45), width=3)

    elif p == "worldcup_global_arcs":
        # Regal planetary longitude/latitude arcs with celestial gold
        pdraw.ellipse([width // 2 - 540, height // 2 - 580, width // 2 + 540, height // 2 + 500], outline=(pr, pg, pb, 50), width=4)
        pdraw.ellipse([width // 2 - 270, height // 2 - 580, width // 2 + 270, height // 2 + 500], outline=(pr, pg, pb, 35), width=3)
        pdraw.line([(width // 2 - 540, height // 2 - 40), (width // 2 + 540, height // 2 - 40)], fill=(pr, pg, pb, 50), width=3)

    else:
        # Sleek neutral graphite mesh
        pdraw.ellipse([width // 2 - 420, height // 2 - 460, width // 2 + 420, height // 2 + 380], outline=(pr, pg, pb, 30), width=3)
        pdraw.line([(0, height // 2 - 40), (width, height // 2 - 40)], fill=(pr, pg, pb, 25), width=3)

    img = Image.alpha_composite(img, pattern_layer)

    # 4. Outer Accent Border
    border_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    bdraw = ImageDraw.Draw(border_layer)
    bdraw.rectangle([0, 0, width, height], outline=(theme.primary[0], theme.primary[1], theme.primary[2], 90), width=6)
    img = Image.alpha_composite(img, border_layer)

    return img


# ==============================================================================
# 5. Themed Crest Card / Plate Renderer
# ==============================================================================

def draw_themed_crest_plate(
    base: Image.Image,
    logo_img: Optional[Image.Image],
    team_name: str,
    cx: int,
    cy: int,
    theme: CompetitionTheme,
    card_size: int = 420
):
    """
    Renders a prominent team logo inside a theme-matched visual plate with drop-shadow,
    theme-specific container styles, and back-glow. All coordinates in 2x supersampled space.
    """
    card = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(card)

    x0 = cx - card_size // 2
    y0 = cy - card_size // 2
    x1 = cx + card_size // 2
    y1 = cy + card_size // 2

    # Drop shadow
    shadow_pad = 22
    draw.rounded_rectangle(
        [x0 - shadow_pad, y0 - shadow_pad + 8, x1 + shadow_pad, y1 + shadow_pad + 8],
        radius=52,
        fill=(0, 0, 0, 135)
    )

    style = theme.crest_container_style

    if style == "halo":
        # Luminous celestial outer halo ring (UCL, World Cup)
        halo_pad = 24
        draw.rounded_rectangle(
            [x0 - halo_pad, y0 - halo_pad, x1 + halo_pad, y1 + halo_pad],
            radius=60,
            outline=(theme.highlight[0], theme.highlight[1], theme.highlight[2], 75),
            width=3
        )
        draw.rounded_rectangle(
            [x0, y0, x1, y1],
            radius=44,
            fill=theme.panel_color,
            outline=theme.panel_border,
            width=5
        )
    elif style == "metallic":
        # 3D bevel / chamfered plate (UEL, Serie A)
        draw.rounded_rectangle(
            [x0 - 4, y0 - 4, x1 + 4, y1 + 4],
            radius=48,
            outline=(theme.primary[0], theme.primary[1], theme.primary[2], 110),
            width=4
        )
        draw.rounded_rectangle(
            [x0, y0, x1, y1],
            radius=44,
            fill=theme.panel_color,
            outline=theme.panel_border,
            width=5
        )
    elif style == "modern_frame":
        # Sharp technical framing with corner ticks (Premier League, Bundesliga)
        draw.rounded_rectangle(
            [x0, y0, x1, y1],
            radius=36,
            fill=theme.panel_color,
            outline=theme.panel_border,
            width=5
        )
        tick_len = 32
        draw.line([(x0, y0), (x0 + tick_len, y0)], fill=theme.highlight, width=6)
        draw.line([(x0, y0), (x0, y0 + tick_len)], fill=theme.highlight, width=6)
        draw.line([(x1, y1), (x1 - tick_len, y1)], fill=theme.highlight, width=6)
        draw.line([(x1, y1), (x1, y1 - tick_len)], fill=theme.highlight, width=6)
    else:
        # Polished glass plate
        draw.rounded_rectangle(
            [x0, y0, x1, y1],
            radius=44,
            fill=theme.panel_color,
            outline=theme.panel_border,
            width=5
        )

    # Subtle inner gloss reflection
    draw.rounded_rectangle(
        [x0 + 6, y0 + 6, x1 - 6, y0 + (card_size // 3)],
        radius=38,
        fill=(255, 255, 255, 12)
    )

    base.alpha_composite(card)

    # Draw Crest Logo or Initials
    if logo_img:
        max_logo_size = card_size - 80
        w, h = logo_img.size
        ratio = min(max_logo_size / w, max_logo_size / h)
        new_w = max(1, int(w * ratio))
        new_h = max(1, int(h * ratio))

        resized_logo = logo_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        pos_x = cx - new_w // 2
        pos_y = cy - new_h // 2

        base.paste(resized_logo, (pos_x, pos_y), resized_logo)
    else:
        initials = team_name[:3].upper() if team_name else "FC"
        f = get_font(size=96, weight="extrabold", family=theme.font_family)
        draw_base = ImageDraw.Draw(base)
        bbox = draw_base.textbbox((0, 0), initials, font=f)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        draw_base.text((cx - tw // 2, cy - th // 2 - 4), initials, fill=theme.text_primary, font=f)


# ==============================================================================
# 6. Themed Central Match Device (Prominent PKT Time, Zero "VS")
# ==============================================================================

def draw_themed_center_divider(
    draw: ImageDraw.Draw,
    cx: int,
    cy: int,
    theme: CompetitionTheme,
    pkt_time_text: str = "MATCHDAY",
    is_confirmed: bool = True
):
    """
    Renders an elegant, theme-specific central match device that prominently displays
    the PKT kickoff time (or 'MATCHDAY' if unconfirmed). Completely eliminates 'VS'.
    All coordinates in 2x supersampled space.
    """
    pr, pg, pb = theme.primary
    hr, hg, hb = theme.highlight
    sr, sg, sb = theme.secondary
    style = theme.center_style

    display_time = pkt_time_text.strip().upper() if pkt_time_text else "MATCHDAY"

    main_font_size = 36 if len(display_time) <= 8 else 30
    f_main = get_font(main_font_size, weight="extrabold", family=theme.font_family)
    f_pkt_label = get_font(18, weight="bold", family=theme.font_family)

    bbox_main = draw.textbbox((0, 0), display_time, font=f_main)
    tw = bbox_main[2] - bbox_main[0]
    th = bbox_main[3] - bbox_main[1]

    bw = max(220, tw + 56)
    bh = 100 if is_confirmed else 82

    bx0 = cx - bw // 2
    by0 = cy - bh // 2
    bx1 = cx + bw // 2
    by1 = cy + bh // 2

    if style == "champions_divider":
        # UEFA Champions League: Luminous starry indigo/silver capsule with vertical celestial light beams
        draw.line([(cx, cy - 200), (cx, by0 - 12)], fill=(hr, hg, hb, 190), width=4)
        draw.line([(cx, by1 + 12), (cx, cy + 200)], fill=(hr, hg, hb, 190), width=4)
        for pip_y in [cy - 200, cy + 200]:
            draw.ellipse([cx - 5, pip_y - 5, cx + 5, pip_y + 5], fill=(hr, hg, hb, 240))
        draw.rounded_rectangle([bx0 - 6, by0 - 6, bx1 + 6, by1 + 6], radius=24, fill=(hr, hg, hb, 35))
        draw.rounded_rectangle([bx0, by0, bx1, by1], radius=20, fill=(14, 24, 60, 245), outline=(hr, hg, hb, 220), width=4)

    elif style == "europa_energy_divider":
        # UEFA Europa League: Dynamic angular speed badge with energetic orange beams
        draw.line([(cx - 24, cy - 190), (cx - 10, by0 - 10)], fill=(pr, pg, pb, 220), width=5)
        draw.line([(cx + 10, by1 + 10), (cx + 24, cy + 190)], fill=(pr, pg, pb, 220), width=5)
        poly_pts = [(bx0 - 14, by0), (bx1 + 14, by0), (bx1 - 4, by1), (bx0 - 24, by1)]
        draw.polygon(poly_pts, fill=(34, 20, 14, 245), outline=(pr, pg, pb, 240), width=4)

    elif style == "conference_minimal_v":
        # UEFA Conference League: Electric green / turquoise modern neon pill
        draw.line([(cx, cy - 180), (cx, by0 - 12)], fill=(pr, pg, pb, 200), width=4)
        draw.line([(cx, by1 + 12), (cx, cy + 180)], fill=(pr, pg, pb, 200), width=4)
        draw.rounded_rectangle([bx0 - 4, by0 - 4, bx1 + 4, by1 + 4], radius=bh // 2 + 4, fill=(pr, pg, pb, 35))
        draw.rounded_rectangle([bx0, by0, bx1, by1], radius=bh // 2, fill=(14, 34, 24, 245), outline=(pr, pg, pb, 230), width=4)

    elif style == "pl_matchday_device":
        # Premier League: Bold modern matchday device with cyan/magenta accent lines
        draw.line([(cx, cy - 190), (cx, by0 - 12)], fill=(pr, pg, pb, 220), width=5)
        draw.line([(cx, by1 + 12), (cx, cy + 190)], fill=(sr, sg, sb, 220), width=5)
        draw.rounded_rectangle([bx0, by0, bx1, by1], radius=16, fill=(28, 14, 46, 245), outline=(pr, pg, pb, 230), width=4)
        draw.line([(bx0 + 16, by0 + 3), (bx1 - 16, by0 + 3)], fill=(pr, pg, pb, 240), width=4)

    elif style == "laliga_minimal_v":
        # La Liga: Vivid multi-accented Spanish spectrum stadium capsule
        draw.line([(cx, cy - 180), (cx, by0 - 12)], fill=(255, 59, 48, 210), width=4)
        draw.line([(cx, by1 + 12), (cx, cy + 180)], fill=(255, 204, 0, 210), width=4)
        draw.rounded_rectangle([bx0, by0, bx1, by1], radius=22, fill=(26, 26, 34, 245), outline=(255, 140, 0, 230), width=4)

    elif style == "seriea_vertical_beam":
        # Serie A: Platinum & Azzurro metallic octagonal bevel shield
        draw.line([(cx, cy - 190), (cx, by0 - 12)], fill=(hr, hg, hb, 210), width=5)
        draw.line([(cx, by1 + 12), (cx, cy + 190)], fill=(hr, hg, hb, 210), width=5)
        draw.polygon([(bx0 + 18, by0), (bx1 - 18, by0), (bx1, by0 + 18), (bx1, by1 - 18), (bx1 - 18, by1), (bx0 + 18, by1), (bx0, by1 - 18), (bx0, by0 + 18)], fill=(12, 24, 52, 245), outline=(hr, hg, hb, 220), width=4)

    elif style == "bundesliga_slash_divider":
        # Bundesliga: Dynamic angled red-accented carbon box
        draw.line([(cx - 20, cy - 185), (cx - 10, by0 - 10)], fill=(pr, pg, pb, 230), width=5)
        draw.line([(cx + 10, by1 + 10), (cx + 20, cy + 185)], fill=(pr, pg, pb, 230), width=5)
        poly_pts = [(bx0 - 10, by0), (bx1 + 10, by0), (bx1, by1), (bx0 - 20, by1)]
        draw.polygon(poly_pts, fill=(28, 20, 22, 245), outline=(227, 6, 19, 240), width=4)

    elif style == "worldcup_arc_divider":
        # World Cup: Celestial golden disc with concentric planetary rings
        draw.line([(cx, cy - 190), (cx, by0 - 12)], fill=(pr, pg, pb, 200), width=4)
        draw.line([(cx, by1 + 12), (cx, cy + 190)], fill=(pr, pg, pb, 200), width=4)
        draw.rounded_rectangle([bx0, by0, bx1, by1], radius=bh // 2, fill=(38, 16, 28, 245), outline=(pr, pg, pb, 240), width=4)

    else:
        # Ligue 1, Championship, Neutral: Sleek glass capsule
        draw.line([(cx, cy - 180), (cx, by0 - 12)], fill=(pr, pg, pb, 190), width=4)
        draw.line([(cx, by1 + 12), (cx, cy + 180)], fill=(pr, pg, pb, 190), width=4)
        draw.rounded_rectangle([bx0, by0, bx1, by1], radius=18, fill=(20, 28, 42, 245), outline=(pr, pg, pb, 210), width=4)

    # Render Text Inside Device
    if is_confirmed:
        time_y = by0 + 16
        draw.text((cx - tw // 2, time_y), display_time, fill=theme.text_primary, font=f_main)

        pkt_lbl = "PKT"
        bbox_lbl = draw.textbbox((0, 0), pkt_lbl, font=f_pkt_label)
        lbl_w = bbox_lbl[2] - bbox_lbl[0]
        lbl_y = time_y + th + 8
        draw.text((cx - lbl_w // 2, lbl_y), pkt_lbl, fill=theme.highlight, font=f_pkt_label)
    else:
        draw.text((cx - tw // 2, cy - th // 2 - 4), display_time, fill=theme.text_primary, font=f_main)



# ==============================================================================
# 7. Complete Event Card Renderer
# ==============================================================================

def format_date_display(date_str: str) -> str:
    """Formats '2026-09-20' into 'SUNDAY, 20 SEP 2026'."""
    try:
        d = date.fromisoformat(date_str)
        return d.strftime("%A, %d %b %Y").upper()
    except Exception:
        return date_str.upper() if date_str else "UPCOMING FIXTURE"


def generate_event_card(
    event: Dict[str, Any],
    output_path: str,
    width: int = 1200,
    height: int = 630
) -> str:
    """
    Renders and saves the complete fixture event graphic using 2x supersampling.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    comp = event.get("competition", {})
    comp_id = comp.get("id", "neutral-fallback")
    theme = get_competition_theme(comp_id)

    home = event.get("home_team", {})
    away = event.get("away_team", {})

    # 2x supersampling dimensions for razor-sharp rendering
    w2 = width * 2
    h2 = height * 2

    img2 = create_themed_background(
        theme=theme,
        width=w2,
        height=h2,
        seed_str=event.get("event_id", "")
    )
    draw2 = ImageDraw.Draw(img2)

    # 1. Header Competition & Round Badge
    comp_title = comp.get("name") or theme.name
    round_title = comp.get("round") or event.get("round", "")
    if round_title.lower() in ["regular fixture", "regular", ""]:
        round_title = ""

    header_text = f"{comp_title.upper()}  •  {round_title.upper()}" if round_title else comp_title.upper()

    # Scale header font dynamically so long names never overflow
    header_font_size = 52
    header_font = get_font(header_font_size, weight="extrabold", family=theme.font_family)
    bbox_h = draw2.textbbox((0, 0), header_text, font=header_font)
    while (bbox_h[2] - bbox_h[0]) > (w2 - 360) and header_font_size > 30:
        header_font_size -= 2
        header_font = get_font(header_font_size, weight="extrabold", family=theme.font_family)
        bbox_h = draw2.textbbox((0, 0), header_text, font=header_font)

    hw = bbox_h[2] - bbox_h[0]
    hh = bbox_h[3] - bbox_h[1]

    pill_w = hw + 90
    pill_h = hh + 46
    pill_x0 = (w2 - pill_w) // 2
    pill_y0 = 60

    # Outer glow
    draw2.rounded_rectangle(
        [pill_x0 - 4, pill_y0 - 4, pill_x0 + pill_w + 4, pill_y0 + pill_h + 4],
        radius=pill_h // 2 + 4,
        fill=(theme.primary[0], theme.primary[1], theme.primary[2], 30)
    )
    # Header badge pill
    draw2.rounded_rectangle(
        [pill_x0, pill_y0, pill_x0 + pill_w, pill_y0 + pill_h],
        radius=pill_h // 2,
        fill=theme.panel_color,
        outline=theme.panel_border,
        width=4
    )
    draw2.text((pill_x0 + 45, pill_y0 + 18), header_text, fill=theme.text_primary, font=header_font)

    # 2. Team Crest Cards & Logos
    left_cx = w2 // 4 + 30
    right_cx = w2 * 3 // 4 - 30
    center_y = h2 // 2 - 40

    home_logo_url = home.get("logo_url") or home.get("logo_resolution", {}).get("url")
    away_logo_url = away.get("logo_url") or away.get("logo_resolution", {}).get("url")

    home_img = download_or_cache_logo(home_logo_url, home.get("name", "Home"))
    away_img = download_or_cache_logo(away_logo_url, away.get("name", "Away"))

    draw_themed_crest_plate(img2, home_img, home.get("name", "Home"), left_cx, center_y, theme, card_size=420)
    draw_themed_crest_plate(img2, away_img, away.get("name", "Away"), right_cx, center_y, theme, card_size=420)

    # 3. Central Match Device (Prominent PKT Kickoff Time, Zero VS)
    time_status = event.get("time_status", "tbd")
    is_confirmed = (time_status == "confirmed") and bool(event.get("start_time_pkt"))

    if is_confirmed:
        pkt_raw = event.get("display_time")
        if not pkt_raw and event.get("start_time_pkt"):
            try:
                dt_pkt = datetime.fromisoformat(event["start_time_pkt"])
                pkt_raw = dt_pkt.strftime("%I:%M %p").lstrip("0")
            except Exception:
                pkt_raw = event["start_time_pkt"][11:16]
        center_time_text = pkt_raw if pkt_raw else "MATCHDAY"
    else:
        center_time_text = "MATCHDAY"

    draw_themed_center_divider(
        draw2,
        cx=w2 // 2,
        cy=center_y,
        theme=theme,
        pkt_time_text=center_time_text,
        is_confirmed=is_confirmed
    )

    # 4. Fitted Team Names Below Crests
    team_name_max_width = 540

    # Home team name
    h_lines, h_font, _ = fit_team_name_lines(home.get("name", "Home Team"), team_name_max_width, initial_size=62, min_size=32, family=theme.font_family)
    h_top_y = center_y + 240
    for line in h_lines:
        b = draw2.textbbox((0, 0), line, font=h_font)
        lw = b[2] - b[0]
        draw2.text((left_cx - lw // 2, h_top_y), line, fill=theme.text_primary, font=h_font)
        h_top_y += (b[3] - b[1]) + 10

    # Away team name
    a_lines, a_font, _ = fit_team_name_lines(away.get("name", "Away Team"), team_name_max_width, initial_size=62, min_size=32, family=theme.font_family)
    a_top_y = center_y + 240
    for line in a_lines:
        b = draw2.textbbox((0, 0), line, font=a_font)
        lw = b[2] - b[0]
        draw2.text((right_cx - lw // 2, a_top_y), line, fill=theme.text_primary, font=a_font)
        a_top_y += (b[3] - b[1]) + 10

    # 5. Footer: Match Date + UTC Kickoff Time (Vector Icons, No Emoji)
    footer_y = h2 - 180
    footer_w = 1520
    footer_h = 110
    fx0 = (w2 - footer_w) // 2

    # Outer subtle footer shadow & plate
    draw2.rounded_rectangle(
        [fx0 - 4, footer_y - 4, fx0 + footer_w + 4, footer_y + footer_h + 4],
        radius=28,
        fill=(0, 0, 0, 100)
    )
    draw2.rounded_rectangle(
        [fx0, footer_y, fx0 + footer_w, footer_y + footer_h],
        radius=26,
        fill=theme.panel_color,
        outline=theme.panel_border,
        width=4
    )

    display_date = event.get("display_date") or event.get("match_date_pkt") or event.get("match_date", "")
    date_str = format_date_display(display_date)

    if is_confirmed and event.get("start_time_utc"):
        utc_str = event["start_time_utc"][11:16] + " UTC"
        time_text = utc_str
    else:
        time_text = "KICKOFF TIME TBD"

    footer_font = get_font(38, weight="bold", family=theme.font_family)
    divider_font = get_font(38, weight="regular", family=theme.font_family)

    # Draw left section (Vector calendar + Date)
    sec1_x = fx0 + 55
    draw_vector_calendar_icon(draw2, sec1_x, footer_y + 36, size=38, color=theme.highlight)
    draw2.text((sec1_x + 54, footer_y + 30), date_str, fill=theme.text_primary, font=footer_font)

    # Central pipe divider
    pipe_x = fx0 + footer_w // 2 - 10
    draw2.text((pipe_x, footer_y + 28), "|", fill=(theme.text_secondary[0], theme.text_secondary[1], theme.text_secondary[2], 140), font=divider_font)

    # Draw right section (Vector clock + Time)
    sec2_x = pipe_x + 55
    draw_vector_clock_icon(draw2, sec2_x, footer_y + 36, size=38, color=theme.highlight)
    draw2.text((sec2_x + 54, footer_y + 30), time_text, fill=theme.text_primary, font=footer_font)

    # 6. Downsample from 2400x1260 to 1200x630 using Lanczos for flawless antialiasing
    final_img = img2.resize((width, height), Image.Resampling.LANCZOS).convert("RGB")
    final_img.save(output_path, format="PNG", optimize=True)
    return output_path


def generate_all_event_images(
    events: list,
    output_dir: str = "output/images",
    raw_base_url: str = "https://raw.githubusercontent.com/hashirhamxa/football-data-hash/main",
    max_workers: int = 8
) -> list:
    """Generates themed event cards for all upcoming events concurrently."""
    os.makedirs(output_dir, exist_ok=True)
    total = len(events)
    logger.info(f"Generating themed event graphics for {total} matches...")

    # 1. Pre-fetch logos concurrently
    prefetch_all_logos(events, max_workers=16)

    # 2. Render cards concurrently
    def render_single_event(ev: Dict[str, Any]):
        eid = ev["event_id"]
        fname = f"{eid}.png"
        fpath = os.path.join(output_dir, fname)
        generate_event_card(ev, fpath)
        ev["event_image_url"] = f"{raw_base_url}/output/images/{fname}"
        return eid

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(render_single_event, ev) for ev in events]
        completed = 0
        for f in as_completed(futures):
            completed += 1
            if completed % 30 == 0 or completed == total:
                logger.info(f"Rendered {completed}/{total} themed event images.")

    return events


# ==============================================================================
# 8. Preview Gallery & Contact Sheet Generator
# ==============================================================================

def generate_theme_previews(output_base_dir: str = "output/theme_previews") -> List[str]:
    """
    Generates preview cards for each of the 10 supported competitions + fallback,
    and stitches them into a labeled contact-sheet.png.
    """
    os.makedirs(output_base_dir, exist_ok=True)

    sample_matches = [
        {
            "event_id": "champions-league-preview",
            "competition": {"id": "champions-league", "name": "UEFA Champions League", "round": "Group Stage • MD 1"},
            "home_team": {"name": "Real Madrid", "logo_url": "https://a.espncdn.com/i/teamlogos/soccer/500/86.png"},
            "away_team": {"name": "Manchester City", "logo_url": "https://a.espncdn.com/i/teamlogos/soccer/500/382.png"},
            "match_date": "2026-09-16",
            "match_date_pkt": "2026-09-17",
            "display_date": "2026-09-17",
            "display_time": "12:00 AM",
            "start_time_utc": "2026-09-16T19:00:00Z",
            "start_time_pkt": "2026-09-17T00:00:00+05:00",
            "time_status": "confirmed"
        },
        {
            "event_id": "europa-league-preview",
            "competition": {"id": "europa-league", "name": "UEFA Europa League", "round": "League Phase • Matchday 1"},
            "home_team": {"name": "AC Milan", "logo_url": "https://a.espncdn.com/i/teamlogos/soccer/500/103.png"},
            "away_team": {"name": "Benfica", "logo_url": "https://a.espncdn.com/i/teamlogos/soccer/500/1929.png"},
            "match_date": "2026-09-16",
            "match_date_pkt": "2026-09-17",
            "display_date": "2026-09-17",
            "display_time": "12:00 AM",
            "start_time_utc": "2026-09-16T19:00:00Z",
            "start_time_pkt": "2026-09-17T00:00:00+05:00",
            "time_status": "confirmed"
        },
        {
            "event_id": "conference-league-preview",
            "competition": {"id": "conference-league", "name": "UEFA Conference League", "round": "League Phase • Matchday 1"},
            "home_team": {"name": "Chelsea", "logo_url": "https://a.espncdn.com/i/teamlogos/soccer/500/363.png"},
            "away_team": {"name": "Fiorentina", "logo_url": "https://a.espncdn.com/i/teamlogos/soccer/500/109.png"},
            "match_date": "2026-10-01",
            "match_date_pkt": "2026-10-01",
            "display_date": "2026-10-01",
            "display_time": "09:45 PM",
            "start_time_utc": "2026-10-01T16:45:00Z",
            "start_time_pkt": "2026-10-01T21:45:00+05:00",
            "time_status": "confirmed"
        },
        {
            "event_id": "premier-league-preview",
            "competition": {"id": "premier-league", "name": "English Premier League", "round": "Matchday 5"},
            "home_team": {"name": "Arsenal", "logo_url": "https://a.espncdn.com/i/teamlogos/soccer/500/359.png"},
            "away_team": {"name": "Tottenham Hotspur", "logo_url": "https://a.espncdn.com/i/teamlogos/soccer/500/367.png"},
            "match_date": "2026-09-19",
            "match_date_pkt": "2026-09-19",
            "display_date": "2026-09-19",
            "display_time": "09:30 PM",
            "start_time_utc": "2026-09-19T16:30:00Z",
            "start_time_pkt": "2026-09-19T21:30:00+05:00",
            "time_status": "confirmed"
        },
        {
            "event_id": "la-liga-preview",
            "competition": {"id": "la-liga", "name": "Spanish La Liga", "round": "Jornada 5"},
            "home_team": {"name": "Barcelona", "logo_url": "https://a.espncdn.com/i/teamlogos/soccer/500/83.png"},
            "away_team": {"name": "Atlético Madrid", "logo_url": "https://a.espncdn.com/i/teamlogos/soccer/500/1068.png"},
            "match_date": "2026-09-20",
            "match_date_pkt": "2026-09-21",
            "display_date": "2026-09-21",
            "display_time": "12:00 AM",
            "start_time_utc": "2026-09-20T19:00:00Z",
            "start_time_pkt": "2026-09-21T00:00:00+05:00",
            "time_status": "confirmed"
        },
        {
            "event_id": "serie-a-preview",
            "competition": {"id": "serie-a", "name": "Italian Serie A", "round": "Giornata 4"},
            "home_team": {"name": "Juventus", "logo_url": "https://a.espncdn.com/i/teamlogos/soccer/500/111.png"},
            "away_team": {"name": "Inter Milan", "logo_url": "https://a.espncdn.com/i/teamlogos/soccer/500/110.png"},
            "match_date": "2026-09-19",
            "match_date_pkt": "2026-09-19",
            "display_date": "2026-09-19",
            "display_time": "11:45 PM",
            "start_time_utc": "2026-09-19T18:45:00Z",
            "start_time_pkt": "2026-09-19T23:45:00+05:00",
            "time_status": "confirmed"
        },
        {
            "event_id": "bundesliga-preview",
            "competition": {"id": "bundesliga", "name": "German Bundesliga", "round": "Spieltag 4"},
            "home_team": {"name": "Bayern Munich", "logo_url": "https://a.espncdn.com/i/teamlogos/soccer/500/132.png"},
            "away_team": {"name": "Borussia Dortmund", "logo_url": "https://a.espncdn.com/i/teamlogos/soccer/500/124.png"},
            "match_date": "2026-09-19",
            "match_date_pkt": "2026-09-19",
            "display_date": "2026-09-19",
            "display_time": "09:30 PM",
            "start_time_utc": "2026-09-19T16:30:00Z",
            "start_time_pkt": "2026-09-19T21:30:00+05:00",
            "time_status": "confirmed"
        },
        {
            "event_id": "ligue-1-preview",
            "competition": {"id": "ligue-1", "name": "French Ligue 1", "round": "Journée 5"},
            "home_team": {"name": "Paris Saint-Germain", "logo_url": "https://a.espncdn.com/i/teamlogos/soccer/500/160.png"},
            "away_team": {"name": "Marseille", "logo_url": "https://a.espncdn.com/i/teamlogos/soccer/500/166.png"},
            "match_date": "2026-09-20",
            "match_date_pkt": "2026-09-20",
            "display_date": "2026-09-20",
            "display_time": "11:45 PM",
            "start_time_utc": "2026-09-20T18:45:00Z",
            "start_time_pkt": "2026-09-20T23:45:00+05:00",
            "time_status": "confirmed"
        },
        {
            "event_id": "championship-preview",
            "competition": {"id": "championship", "name": "English Championship", "round": "Matchday 6"},
            "home_team": {"name": "Leeds United", "logo_url": "https://a.espncdn.com/i/teamlogos/soccer/500/357.png"},
            "away_team": {"name": "Sheffield United", "logo_url": "https://a.espncdn.com/i/teamlogos/soccer/500/398.png"},
            "match_date": "2026-09-19",
            "match_date_pkt": "2026-09-19",
            "display_date": "2026-09-19",
            "display_time": "07:00 PM",
            "start_time_utc": "2026-09-19T14:00:00Z",
            "start_time_pkt": "2026-09-19T19:00:00+05:00",
            "time_status": "confirmed"
        },
        {
            "event_id": "world-cup-preview",
            "competition": {"id": "world-cup", "name": "FIFA World Cup", "round": "Group Stage"},
            "home_team": {"name": "Brazil", "logo_url": "https://a.espncdn.com/i/teamlogos/soccer/500/205.png"},
            "away_team": {"name": "France", "logo_url": "https://a.espncdn.com/i/teamlogos/soccer/500/478.png"},
            "match_date": "2026-06-15",
            "match_date_pkt": "2026-06-16",
            "display_date": "2026-06-16",
            "display_time": "12:00 AM",
            "start_time_utc": "2026-06-15T19:00:00Z",
            "start_time_pkt": "2026-06-16T00:00:00+05:00",
            "time_status": "confirmed"
        },
        {
            "event_id": "neutral-fallback-preview",
            "competition": {"id": "unknown-cup", "name": "International Club Friendly", "round": "Pre-Season"},
            "home_team": {"name": "Ajax", "logo_url": "https://a.espncdn.com/i/teamlogos/soccer/500/139.png"},
            "away_team": {"name": "Porto", "logo_url": "https://a.espncdn.com/i/teamlogos/soccer/500/1920.png"},
            "match_date": "2026-09-22",
            "match_date_pkt": "2026-09-22",
            "display_date": "2026-09-22",
            "display_time": "08:00 PM",
            "start_time_utc": "2026-09-22T15:00:00Z",
            "start_time_pkt": "2026-09-22T20:00:00+05:00",
            "time_status": "confirmed"
        }
    ]

    generated_paths = []
    for ev in sample_matches:
        cid = ev["competition"]["id"]
        fname = f"{cid}.png"
        out_p = os.path.join(output_base_dir, fname)
        generate_event_card(ev, out_p)
        generated_paths.append(out_p)
        logger.info(f"Generated preview for '{cid}' -> {out_p}")

    # Build Contact Sheet (3 columns x 4 rows)
    cols = 3
    rows = (len(sample_matches) + cols - 1) // cols
    card_w, card_h = 600, 315 # half scale for contact sheet
    padding = 36
    title_h = 75

    sheet_w = cols * card_w + (cols + 1) * padding
    sheet_h = rows * (card_h + title_h) + (rows + 1) * padding

    sheet = Image.new("RGB", (sheet_w, sheet_h), (8, 12, 18))
    sdraw = ImageDraw.Draw(sheet)
    f_title = get_font(30, weight="extrabold", family="montserrat")

    for idx, (ev, img_p) in enumerate(zip(sample_matches, generated_paths)):
        r_idx = idx // cols
        c_idx = idx % cols

        x = padding + c_idx * (card_w + padding)
        y = padding + r_idx * (card_h + title_h + padding)

        # Draw Title
        c_name = ev["competition"]["name"]
        sdraw.text((x + 6, y + 8), c_name.upper(), fill=(235, 245, 255), font=f_title)

        # Open rendered image, resize and paste
        with Image.open(img_p) as card_img:
            small_card = card_img.resize((card_w, card_h), Image.Resampling.LANCZOS)
            sheet.paste(small_card, (x, y + title_h - 15))

    contact_sheet_path = os.path.join(output_base_dir, "contact-sheet.png")
    sheet.save(contact_sheet_path, format="PNG", optimize=True)
    logger.info(f"Generated master theme contact sheet -> {contact_sheet_path}")

    return generated_paths + [contact_sheet_path]


if __name__ == "__main__":
    generate_theme_previews()
