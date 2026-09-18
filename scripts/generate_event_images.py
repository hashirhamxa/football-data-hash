"""
generate_event_images.py
High-performance, broadcast-grade matchday graphic generator for football fixtures using Pillow.
Features:
- Modular, competition-specific theme engine with distinct palettes, geometries, and center devices
- 2x supersampled internal rendering (2400x1260 -> 1200x630 Lanczos) for razor-sharp antialiasing
- Dedicated competition logo caching and rendering in header
- High-res team crests with aspect-ratio preservation, transparent border trimming, and back-glow
- Intelligent text-fitting and multi-line wrapping (no blunt truncation)
- Vector-drawn calendar icon in centered footer (pure date display, zero kickoff time or clock icons)
- Pure decorative central dividers per competition theme (zero 'VS' or time text)
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
COMP_LOGO_CACHE_DIR = ".cache/competition-logos"
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


def get_competition_logo_cache_path(comp_id: str) -> str:
    os.makedirs(COMP_LOGO_CACHE_DIR, exist_ok=True)
    clean_id = re.sub(r"[^a-zA-Z0-9_-]+", "_", comp_id).lower()
    return os.path.join(COMP_LOGO_CACHE_DIR, f"{clean_id}.png")


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


def download_or_cache_logo(url: Optional[str], team_name: str) -> Optional[Image.Image]:
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


def download_or_cache_competition_logo(comp_id: str, url: Optional[str] = None) -> Optional[Image.Image]:
    """Downloads competition logo with dedicated local caching in .cache/competition-logos/."""
    if not comp_id:
        return None

    cache_file = get_competition_logo_cache_path(comp_id)
    if os.path.exists(cache_file):
        try:
            img = Image.open(cache_file).convert("RGBA")
            return autocrop_transparent_margins(img, padding=4)
        except Exception:
            pass

    if not url:
        return None

    if os.path.exists(url):
        try:
            img = Image.open(url).convert("RGBA")
            img = autocrop_transparent_margins(img, padding=4)
            img.save(cache_file)
            return img
        except Exception:
            return None

    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = resp.read()
            img = Image.open(io.BytesIO(data)).convert("RGBA")
            img = autocrop_transparent_margins(img, padding=4)
            img.save(cache_file)
            return img
    except Exception as e:
        logger.debug(f"Could not download competition logo for {comp_id} from {url}: {e}")
        return None


def prefetch_all_logos(events: List[Dict[str, Any]], max_workers: int = 16):
    """Pre-downloads all distinct team and competition logos concurrently."""
    unique_teams: Dict[str, Tuple[str, str]] = {}
    unique_comps: Dict[str, Tuple[str, str]] = {}

    for ev in events:
        # Teams
        for t_key in ["home_team", "away_team"]:
            team = ev.get(t_key, {})
            name = team.get("name")
            url = team.get("logo_url") or team.get("logo_resolution", {}).get("url")
            if name and name not in unique_teams and url:
                unique_teams[name] = (url, name)

        # Competitions
        comp = ev.get("competition", {})
        cid = comp.get("id")
        curl = comp.get("logo_url")
        if cid and cid not in unique_comps and curl:
            unique_comps[cid] = (curl, cid)

    logger.info(f"Pre-fetching {len(unique_teams)} team logos and {len(unique_comps)} competition logos...")
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(download_or_cache_logo, url, name)
            for name, (url, name) in unique_teams.items()
        ]
        futures += [
            executor.submit(download_or_cache_competition_logo, cid, curl)
            for cid, (curl, cid) in unique_comps.items()
        ]
        for future in as_completed(futures):
            pass
    logger.info("Finished pre-fetching logos.")


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

    elif p == "carabao_cup_geometry":
        # Dynamic angular trophy and speed-line geometry in crimson and silver metallic
        pdraw.polygon([(width * 0.5 - 180, 0), (width * 0.5 + 180, 0), (width * 0.5 + 80, height), (width * 0.5 - 80, height)], fill=(pr, pg, pb, 22))
        pdraw.line([(width * 0.5 - 180, 0), (width * 0.5 - 80, height)], fill=(pr, pg, pb, 75), width=4)
        pdraw.line([(width * 0.5 + 180, 0), (width * 0.5 + 80, height)], fill=(pr, pg, pb, 75), width=4)
        for i in range(4):
            offset = i * 160
            pdraw.line([(0, int(height * 0.3 + offset)), (int(width * 0.35), int(height * 0.45 + offset))], fill=(hr, hg, hb, 30), width=3)
            pdraw.line([(width, int(height * 0.3 + offset)), (int(width * 0.65), int(height * 0.45 + offset))], fill=(hr, hg, hb, 30), width=3)

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
        # Sharp technical framing with corner ticks (Premier League, Bundesliga, Carabao Cup)
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
# 6. Themed Pure Decorative Central Divider (Zero Text, Zero "VS", Zero Kickoff Time)
# ==============================================================================

def draw_themed_center_divider(
    draw: ImageDraw.Draw,
    cx: int,
    cy: int,
    theme: CompetitionTheme
):
    """
    Renders an elegant, theme-specific central decorative separator between team crests.
    Completely eliminates 'VS', time text, clock icons, or placeholders.
    All coordinates in 2x supersampled space.
    """
    pr, pg, pb = theme.primary
    hr, hg, hb = theme.highlight
    sr, sg, sb = theme.secondary
    style = theme.center_style

    if style == "champions_divider":
        # UEFA Champions League: Luminous starry celestial vertical beam with diamond core
        draw.line([(cx, cy - 180), (cx, cy + 180)], fill=(hr, hg, hb, 190), width=4)
        draw.line([(cx - 12, cy - 110), (cx - 12, cy + 110)], fill=(pr, pg, pb, 130), width=2)
        draw.line([(cx + 12, cy - 110), (cx + 12, cy + 110)], fill=(pr, pg, pb, 130), width=2)
        for pip_y in [cy - 180, cy + 180]:
            draw.ellipse([cx - 5, pip_y - 5, cx + 5, pip_y + 5], fill=(hr, hg, hb, 240))
        # Center celestial diamond
        dia_pts = [(cx, cy - 28), (cx + 22, cy), (cx, cy + 28), (cx - 22, cy)]
        draw.polygon(dia_pts, fill=(14, 24, 60, 245), outline=(hr, hg, hb, 230), width=3)
        draw.ellipse([cx - 4, cy - 4, cx + 4, cy + 4], fill=(255, 255, 255, 240))

    elif style == "europa_energy_divider":
        # UEFA Europa League: Dynamic angled warm amber/orange dual energy blades
        draw.line([(cx - 16, cy - 180), (cx + 16, cy + 180)], fill=(pr, pg, pb, 220), width=5)
        draw.line([(cx + 16, cy - 180), (cx - 16, cy + 180)], fill=(sr, sg, sb, 190), width=4)
        dia_pts = [(cx, cy - 32), (cx + 34, cy), (cx, cy + 32), (cx - 34, cy)]
        draw.polygon(dia_pts, fill=(34, 20, 14, 245), outline=(pr, pg, pb, 240), width=3)
        draw.ellipse([cx - 5, cy - 5, cx + 5, cy + 5], fill=(hr, hg, hb, 240))

    elif style == "conference_minimal_v":
        # UEFA Conference League: Electric green / turquoise modern neon light tube
        draw.line([(cx, cy - 180), (cx, cy + 180)], fill=(pr, pg, pb, 210), width=4)
        draw.line([(cx - 10, cy - 100), (cx - 10, cy + 100)], fill=(sr, sg, sb, 120), width=2)
        draw.line([(cx + 10, cy - 100), (cx + 10, cy + 100)], fill=(sr, sg, sb, 120), width=2)
        draw.rounded_rectangle([cx - 14, cy - 26, cx + 14, cy + 26], radius=12, fill=(14, 34, 24, 245), outline=(pr, pg, pb, 230), width=3)
        draw.ellipse([cx - 4, cy - 4, cx + 4, cy + 4], fill=(sr, sg, sb, 240))

    elif style == "pl_matchday_device":
        # Premier League: Bold modern matchday device with cyan & magenta dual rails
        draw.line([(cx - 12, cy - 180), (cx - 12, cy + 180)], fill=(pr, pg, pb, 220), width=4)
        draw.line([(cx + 12, cy - 180), (cx + 12, cy + 180)], fill=(sr, sg, sb, 220), width=4)
        draw.line([(cx - 24, cy - 30), (cx + 24, cy - 30)], fill=(pr, pg, pb, 240), width=4)
        draw.line([(cx - 24, cy + 30), (cx + 24, cy + 30)], fill=(sr, sg, sb, 240), width=4)
        draw.rounded_rectangle([cx - 18, cy - 18, cx + 18, cy + 18], radius=8, fill=(28, 14, 46, 245), outline=(hr, hg, hb, 220), width=3)

    elif style == "laliga_minimal_v":
        # La Liga: Vivid multi-accented Spanish spectrum stadium blade
        draw.line([(cx, cy - 180), (cx, cy + 180)], fill=(255, 59, 48, 220), width=4)
        draw.line([(cx - 8, cy - 110), (cx - 8, cy + 110)], fill=(255, 204, 0, 180), width=2)
        draw.line([(cx + 8, cy - 110), (cx + 8, cy + 110)], fill=(255, 140, 0, 180), width=2)
        dia_pts = [(cx, cy - 26), (cx + 22, cy), (cx, cy + 26), (cx - 22, cy)]
        draw.polygon(dia_pts, fill=(26, 26, 34, 245), outline=(255, 204, 0, 230), width=3)

    elif style == "seriea_vertical_beam":
        # Serie A: Platinum & Azzurro metallic architectural vertical blade
        draw.line([(cx, cy - 180), (cx, cy + 180)], fill=(hr, hg, hb, 210), width=4)
        draw.line([(cx - 14, cy - 120), (cx - 14, cy + 120)], fill=(pr, pg, pb, 150), width=3)
        draw.line([(cx + 14, cy - 120), (cx + 14, cy + 120)], fill=(pr, pg, pb, 150), width=3)
        shield_pts = [(cx, cy - 30), (cx + 24, cy - 10), (cx + 18, cy + 24), (cx, cy + 34), (cx - 18, cy + 24), (cx - 24, cy - 10)]
        draw.polygon(shield_pts, fill=(12, 24, 52, 245), outline=(hr, hg, hb, 230), width=3)

    elif style == "bundesliga_slash_divider":
        # Bundesliga: Dynamic angled red-accented carbon slash beam
        draw.line([(cx - 24, cy - 180), (cx + 24, cy + 180)], fill=(pr, pg, pb, 230), width=5)
        draw.line([(cx - 36, cy - 100), (cx + 12, cy + 100)], fill=(sr, sg, sb, 140), width=3)
        draw.polygon([(cx - 18, cy - 24), (cx + 24, cy - 14), (cx + 18, cy + 24), (cx - 24, cy + 14)], fill=(28, 20, 22, 245), outline=(pr, pg, pb, 240), width=3)

    elif style == "ligue1_minimal_device":
        # Ligue 1: Precision electric lime vertical guide with crosshair ticks
        draw.line([(cx, cy - 180), (cx, cy + 180)], fill=(pr, pg, pb, 210), width=4)
        for tick_y in [cy - 90, cy, cy + 90]:
            draw.line([(cx - 16, tick_y), (cx + 16, tick_y)], fill=(pr, pg, pb, 230), width=3)
        draw.ellipse([cx - 8, cy - 8, cx + 8, cy + 8], fill=(16, 24, 40, 245), outline=(pr, pg, pb, 240), width=3)

    elif style == "championship_cross_divider":
        # English Championship: Steel blue & crimson dual vertical stadium floodlight beam
        draw.line([(cx - 10, cy - 180), (cx - 10, cy + 180)], fill=(pr, pg, pb, 210), width=4)
        draw.line([(cx + 10, cy - 180), (cx + 10, cy + 180)], fill=(sr, sg, sb, 210), width=4)
        draw.line([(cx - 28, cy), (cx + 28, cy)], fill=(hr, hg, hb, 210), width=4)
        draw.rectangle([cx - 14, cy - 14, cx + 14, cy + 14], fill=(20, 28, 45, 245), outline=(hr, hg, hb, 220), width=3)

    elif style == "carabao_trophy_divider":
        # English Carabao Cup: Silver metallic & crimson red vertical dual beam with angular cup chevron
        draw.line([(cx, cy - 180), (cx, cy + 180)], fill=(hr, hg, hb, 220), width=4)
        draw.line([(cx - 14, cy - 110), (cx - 14, cy + 110)], fill=(pr, pg, pb, 160), width=3)
        draw.line([(cx + 14, cy - 110), (cx + 14, cy + 110)], fill=(pr, pg, pb, 160), width=3)
        chev_pts = [(cx - 26, cy - 24), (cx, cy - 8), (cx + 26, cy - 24), (cx, cy + 32)]
        draw.polygon(chev_pts, fill=(22, 28, 42, 245), outline=(pr, pg, pb, 240), width=3)

    elif style == "worldcup_arc_divider":
        # World Cup: Celestial golden disc with concentric planetary rings
        draw.line([(cx, cy - 180), (cx, cy + 180)], fill=(pr, pg, pb, 200), width=4)
        draw.ellipse([cx - 30, cy - 30, cx + 30, cy + 30], fill=(38, 16, 28, 245), outline=(pr, pg, pb, 240), width=3)
        draw.ellipse([cx - 12, cy - 12, cx + 12, cy + 12], fill=(hr, hg, hb, 230))

    else:
        # Neutral Fallback: Sleek minimalist ice-blue vertical line with center glowing node
        draw.line([(cx, cy - 180), (cx, cy + 180)], fill=(pr, pg, pb, 200), width=4)
        draw.rounded_rectangle([cx - 12, cy - 22, cx + 12, cy + 22], radius=10, fill=(20, 26, 38, 245), outline=(hr, hg, hb, 220), width=3)
        draw.ellipse([cx - 4, cy - 4, cx + 4, cy + 4], fill=(hr, hg, hb, 240))


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
    Hierarchy:
    1. Competition logo
    2. Competition name and round
    3. Team A crest
    4. Team B crest
    5. Team names
    6. Match date (centered footer, zero kickoff time or clock icons)
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

    # --------------------------------------------------------------------------
    # 1. Header: Competition Logo + Competition Name and Round
    # --------------------------------------------------------------------------
    comp_title = comp.get("name") or theme.name
    round_title = comp.get("round") or event.get("round", "")
    if round_title.lower() in ["regular fixture", "regular", ""]:
        round_title = ""

    header_text = f"{comp_title.upper()}  •  {round_title.upper()}" if round_title else comp_title.upper()

    # Load competition logo if available
    comp_logo_url = comp.get("logo_url")
    comp_logo_img = download_or_cache_competition_logo(comp_id, comp_logo_url)

    # Scale header font dynamically so long names never overflow
    header_font_size = 50
    header_font = get_font(header_font_size, weight="extrabold", family=theme.font_family)
    bbox_h = draw2.textbbox((0, 0), header_text, font=header_font)
    max_text_width = w2 - 500 if comp_logo_img else w2 - 360

    while (bbox_h[2] - bbox_h[0]) > max_text_width and header_font_size > 30:
        header_font_size -= 2
        header_font = get_font(header_font_size, weight="extrabold", family=theme.font_family)
        bbox_h = draw2.textbbox((0, 0), header_text, font=header_font)

    hw = bbox_h[2] - bbox_h[0]
    hh = bbox_h[3] - bbox_h[1]

    # Calculate logo dimensions if present
    logo_w, logo_h = 0, 0
    resized_comp_logo = None
    if comp_logo_img:
        max_lh = 54
        max_lw = 72
        lw, lh = comp_logo_img.size
        ratio = min(max_lw / lw, max_lh / lh)
        logo_w = max(1, int(lw * ratio))
        logo_h = max(1, int(lh * ratio))
        resized_comp_logo = comp_logo_img.resize((logo_w, logo_h), Image.Resampling.LANCZOS)

    # Determine pill dimensions
    if resized_comp_logo:
        pill_content_w = logo_w + 20 + hw
        pill_w = pill_content_w + 80
        pill_h = max(hh + 44, logo_h + 36, 88)
    else:
        pill_content_w = hw
        pill_w = hw + 90
        pill_h = hh + 44

    pill_x0 = (w2 - pill_w) // 2
    pill_y0 = 55

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

    # Render Logo + Text in header
    if resized_comp_logo:
        logo_x = pill_x0 + 38
        logo_y = pill_y0 + (pill_h - logo_h) // 2
        img2.paste(resized_comp_logo, (logo_x, logo_y), resized_comp_logo)

        text_x = logo_x + logo_w + 18
        text_y = pill_y0 + (pill_h - hh) // 2 - 4
        draw2.text((text_x, text_y), header_text, fill=theme.text_primary, font=header_font)
    else:
        text_x = pill_x0 + (pill_w - hw) // 2
        text_y = pill_y0 + (pill_h - hh) // 2 - 4
        draw2.text((text_x, text_y), header_text, fill=theme.text_primary, font=header_font)

    # --------------------------------------------------------------------------
    # 2. Team Crest Cards & Logos
    # --------------------------------------------------------------------------
    left_cx = w2 // 4 + 30
    right_cx = w2 * 3 // 4 - 30
    center_y = h2 // 2 - 35

    home_logo_url = home.get("logo_url") or home.get("logo_resolution", {}).get("url")
    away_logo_url = away.get("logo_url") or away.get("logo_resolution", {}).get("url")

    home_img = download_or_cache_logo(home_logo_url, home.get("name", "Home"))
    away_img = download_or_cache_logo(away_logo_url, away.get("name", "Away"))

    draw_themed_crest_plate(img2, home_img, home.get("name", "Home"), left_cx, center_y, theme, card_size=420)
    draw_themed_crest_plate(img2, away_img, away.get("name", "Away"), right_cx, center_y, theme, card_size=420)

    # --------------------------------------------------------------------------
    # 3. Pure Decorative Central Divider (Zero Text, Zero "VS", Zero Kickoff Time)
    # --------------------------------------------------------------------------
    draw_themed_center_divider(
        draw2,
        cx=w2 // 2,
        cy=center_y,
        theme=theme
    )

    # --------------------------------------------------------------------------
    # 4. Fitted Team Names Below Crests
    # --------------------------------------------------------------------------
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

    # --------------------------------------------------------------------------
    # 5. Centered Footer: Match Date Only (Vector Calendar Icon, No Clock / UTC Time)
    # --------------------------------------------------------------------------
    display_date = event.get("display_date") or event.get("match_date_pkt") or event.get("match_date", "")
    date_str = format_date_display(display_date)

    footer_font = get_font(38, weight="bold", family=theme.font_family)
    bbox_date = draw2.textbbox((0, 0), date_str, font=footer_font)
    date_w = bbox_date[2] - bbox_date[0]
    date_h = bbox_date[3] - bbox_date[1]

    cal_icon_size = 38
    cal_spacing = 20
    footer_content_w = cal_icon_size + cal_spacing + date_w

    footer_w = max(680, footer_content_w + 110)
    footer_h = 100
    footer_y = h2 - 170
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

    # Centered Vector calendar + Date inside footer
    content_start_x = (w2 - footer_content_w) // 2
    draw_vector_calendar_icon(draw2, content_start_x, footer_y + 31, size=cal_icon_size, color=theme.highlight)
    draw2.text((content_start_x + cal_icon_size + cal_spacing, footer_y + 26), date_str, fill=theme.text_primary, font=footer_font)

    # --------------------------------------------------------------------------
    # 6. Downsample from 2400x1260 to 1200x630 using Lanczos
    # --------------------------------------------------------------------------
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
        try:
            generate_event_card(ev, fpath)
        except Exception as e:
            logger.error(f"Failed to generate event card for '{eid}': {e}")
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
    Generates preview cards for each of the 11 supported competitions + fallback,
    and stitches them into a labeled contact-sheet.png.
    """
    os.makedirs(output_base_dir, exist_ok=True)

    sample_matches = [
        {
            "event_id": "champions-league-preview",
            "competition": {
                "id": "champions-league",
                "name": "UEFA Champions League",
                "round": "Group Stage • MD 1",
                "logo_url": "https://a.espncdn.com/i/leaguelogos/soccer/500/2.png"
            },
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
            "competition": {
                "id": "europa-league",
                "name": "UEFA Europa League",
                "round": "League Phase • Matchday 1",
                "logo_url": "https://a.espncdn.com/i/leaguelogos/soccer/500/2310.png"
            },
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
            "competition": {
                "id": "conference-league",
                "name": "UEFA Conference League",
                "round": "League Phase • Matchday 1",
                "logo_url": "https://a.espncdn.com/i/leaguelogos/soccer/500/20296.png"
            },
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
            "competition": {
                "id": "premier-league",
                "name": "English Premier League",
                "round": "Matchday 5",
                "logo_url": "https://a.espncdn.com/i/leaguelogos/soccer/500/23.png"
            },
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
            "event_id": "carabao-cup-preview",
            "competition": {
                "id": "carabao-cup",
                "name": "English Carabao Cup",
                "round": "Third Round",
                "logo_url": "https://a.espncdn.com/i/leaguelogos/soccer/500/41.png"
            },
            "home_team": {"name": "Liverpool", "logo_url": "https://a.espncdn.com/i/teamlogos/soccer/500/364.png"},
            "away_team": {"name": "West Ham United", "logo_url": "https://a.espncdn.com/i/teamlogos/soccer/500/371.png"},
            "match_date": "2026-09-23",
            "match_date_pkt": "2026-09-24",
            "display_date": "2026-09-24",
            "display_time": "12:00 AM",
            "start_time_utc": "2026-09-23T19:00:00Z",
            "start_time_pkt": "2026-09-24T00:00:00+05:00",
            "time_status": "confirmed"
        },
        {
            "event_id": "la-liga-preview",
            "competition": {
                "id": "la-liga",
                "name": "Spanish La Liga",
                "round": "Jornada 5",
                "logo_url": "https://a.espncdn.com/i/leaguelogos/soccer/500/15.png"
            },
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
            "competition": {
                "id": "serie-a",
                "name": "Italian Serie A",
                "round": "Giornata 4",
                "logo_url": "https://a.espncdn.com/i/leaguelogos/soccer/500/12.png"
            },
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
            "competition": {
                "id": "bundesliga",
                "name": "German Bundesliga",
                "round": "Spieltag 4",
                "logo_url": "https://a.espncdn.com/i/leaguelogos/soccer/500/10.png"
            },
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
            "competition": {
                "id": "ligue-1",
                "name": "French Ligue 1",
                "round": "Journée 5",
                "logo_url": "https://a.espncdn.com/i/leaguelogos/soccer/500/9.png"
            },
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
            "competition": {
                "id": "championship",
                "name": "English Championship",
                "round": "Matchday 6",
                "logo_url": "https://a.espncdn.com/i/leaguelogos/soccer/500/24.png"
            },
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
            "competition": {
                "id": "world-cup",
                "name": "FIFA World Cup",
                "round": "Group Stage",
                "logo_url": "https://a.espncdn.com/i/leaguelogos/soccer/500/4.png"
            },
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
            "competition": {
                "id": "unknown-cup",
                "name": "International Club Friendly",
                "round": "Pre-Season",
                "logo_url": None
            },
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
