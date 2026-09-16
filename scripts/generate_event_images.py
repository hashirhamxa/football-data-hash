"""
generate_event_images.py
Generates broadcast-grade 1200x630 matchday banner cards for every fixture using Pillow.
Features:
- Dark stadium/broadcast aesthetic with gradients, subtle field lines, and glowing cards
- High-res team crests with aspect-ratio preservation and drop-shadows
- Multi-threaded logo pre-fetching for lightning-fast batch processing
- Competition & Matchday badges
- Match date and dual timezone kickoff times (UTC and Asia/Karachi PKT)
- Automatic logo caching and fallback handling
"""

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
from PIL import Image, ImageDraw, ImageFont, ImageFilter

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")
logger = logging.getLogger("generate_event_images")

USER_AGENT = "FootballEventsPipeline/1.0 (Image Generator)"
CACHE_DIR = ".cache/logos"


def get_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    """Finds and loads the best available system font across Windows, Linux, and macOS."""
    candidates = []
    if bold:
        candidates = [
            "C:/Windows/Fonts/segoeuib.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/calibrib.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf",
            "/System/Library/Fonts/HelveticaNeue-Bold.otf"
        ]
    else:
        candidates = [
            "C:/Windows/Fonts/segoeui.ttf",
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/calibri.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf",
            "/System/Library/Fonts/HelveticaNeue.otf"
        ]
    for p in candidates:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size=size)
            except Exception:
                continue
    return ImageFont.load_default()


def get_cache_path(team_name: str) -> str:
    os.makedirs(CACHE_DIR, exist_ok=True)
    clean_name = re.sub(r"[^a-zA-Z0-9]+", "_", team_name).lower()
    return os.path.join(CACHE_DIR, f"{clean_name}.png")


def download_or_cache_logo(url: str, team_name: str) -> Optional[Image.Image]:
    """Downloads team logo with local caching and returns a PIL Image."""
    if not url:
        return None
        
    cache_file = get_cache_path(team_name)
    if os.path.exists(cache_file):
        try:
            return Image.open(cache_file).convert("RGBA")
        except Exception:
            pass

    if os.path.exists(url):
        try:
            img = Image.open(url).convert("RGBA")
            img.save(cache_file)
            return img
        except Exception:
            return None

    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = resp.read()
            img = Image.open(io.BytesIO(data)).convert("RGBA")
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
            team = ev[t_key]
            name = team["name"]
            url = team.get("logo_url") or team.get("logo_resolution", {}).get("url")
            if name not in unique_teams and url:
                unique_teams[name] = (url, name)

    logger.info(f"Pre-fetching {len(unique_teams)} distinct team logos with {max_workers} worker threads...")
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(download_or_cache_logo, url, name): name for name, (url, name) in unique_teams.items()}
        for future in as_completed(futures):
            pass
    logger.info("Finished pre-fetching team logos.")


def create_stadium_background(width: int = 1200, height: int = 630) -> Image.Image:
    """Creates a broadcast gradient background with subtle pitch line aesthetics."""
    img = Image.new("RGBA", (width, height), (11, 15, 25, 255))
    draw = ImageDraw.Draw(img)

    top_color = (13, 20, 36)
    bottom_color = (8, 11, 18)
    for y in range(height):
        factor = y / height
        r = int(top_color[0] + (bottom_color[0] - top_color[0]) * factor)
        g = int(top_color[1] + (bottom_color[1] - top_color[1]) * factor)
        b = int(top_color[2] + (bottom_color[2] - top_color[2]) * factor)
        draw.line([(0, y), (width, y)], fill=(r, g, b, 255))

    flare = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    flare_draw = ImageDraw.Draw(flare)
    center_x, center_y = width // 2, height // 2 - 20
    max_radius = 450
    for r in range(max_radius, 0, -20):
        alpha = int((1.0 - (r / max_radius)) * 25)
        flare_draw.ellipse(
            [center_x - r, center_y - r * 0.7, center_x + r, center_y + r * 0.7],
            fill=(30, 80, 160, alpha)
        )
    img = Image.alpha_composite(img, flare)

    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    
    overlay_draw.ellipse(
        [center_x - 180, center_y - 180, center_x + 180, center_y + 180],
        outline=(255, 255, 255, 12),
        width=2
    )
    overlay_draw.line([(center_x, 80), (center_x, height - 100)], fill=(255, 255, 255, 10), width=2)
    overlay_draw.arc([-100, -100, 300, 300], 0, 90, fill=(0, 200, 255, 20), width=2)
    overlay_draw.arc([width - 300, height - 300, width + 100, height + 100], 180, 270, fill=(0, 200, 255, 20), width=2)

    img = Image.alpha_composite(img, overlay)
    return img


def draw_logo_card(
    base: Image.Image,
    logo_img: Optional[Image.Image],
    team_name: str,
    cx: int,
    cy: int,
    card_size: int = 180
):
    """Renders a team logo inside a glowing card plate."""
    card = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(card)

    x0 = cx - card_size // 2
    y0 = cy - card_size // 2
    x1 = cx + card_size // 2
    y1 = cy + card_size // 2

    shadow_pad = 8
    draw.rounded_rectangle(
        [x0 - shadow_pad, y0 - shadow_pad, x1 + shadow_pad, y1 + shadow_pad],
        radius=24,
        fill=(0, 0, 0, 80)
    )

    draw.rounded_rectangle(
        [x0, y0, x1, y1],
        radius=20,
        fill=(22, 30, 48, 220),
        outline=(50, 70, 110, 200),
        width=2
    )

    base.alpha_composite(card)

    if logo_img:
        max_logo_size = card_size - 40
        w, h = logo_img.size
        ratio = min(max_logo_size / w, max_logo_size / h)
        new_w = max(1, int(w * ratio))
        new_h = max(1, int(h * ratio))
        
        resized_logo = logo_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        pos_x = cx - new_w // 2
        pos_y = cy - new_h // 2
        base.paste(resized_logo, (pos_x, pos_y), resized_logo)
    else:
        initials = team_name[:3].upper()
        f = get_font(40, bold=True)
        draw_base = ImageDraw.Draw(base)
        bbox = draw_base.textbbox((0, 0), initials, font=f)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        draw_base.text((cx - tw // 2, cy - th // 2), initials, fill=(255, 255, 255, 240), font=f)


def format_date_display(date_str: str) -> str:
    """Formats '2026-09-20' into 'SUNDAY, 20 SEP 2026'."""
    try:
        d = date.fromisoformat(date_str)
        return d.strftime("%A, %d %b %Y").upper()
    except Exception:
        return date_str.upper()


def generate_event_card(
    event: Dict[str, Any],
    output_path: str,
    width: int = 1200,
    height: int = 630
) -> str:
    """Renders and saves the complete fixture event graphic."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    comp = event["competition"]
    home = event["home_team"]
    away = event["away_team"]
    
    img = create_stadium_background(width, height)
    draw = ImageDraw.Draw(img)

    header_font = get_font(26, bold=True)
    comp_title = comp.get("name", "FOOTBALL FIXTURE").upper()
    round_title = comp.get("round", "").upper()
    
    pill_text = f"{comp_title}  •  {round_title}" if round_title else comp_title
    bbox = draw.textbbox((0, 0), pill_text, font=header_font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    
    pill_w = tw + 48
    pill_h = th + 24
    pill_x0 = (width - pill_w) // 2
    pill_y0 = 36
    
    draw.rounded_rectangle(
        [pill_x0, pill_y0, pill_x0 + pill_w, pill_y0 + pill_h],
        radius=pill_h // 2,
        fill=(18, 25, 42, 230),
        outline=(0, 200, 255, 160),
        width=2
    )
    draw.text((pill_x0 + 24, pill_y0 + 10), pill_text, fill=(240, 245, 255), font=header_font)

    left_cx = width // 4 + 20
    right_cx = width * 3 // 4 - 20
    center_y = height // 2 - 10

    home_logo_url = home.get("logo_url") or (home.get("logo_resolution", {}).get("url"))
    away_logo_url = away.get("logo_url") or (away.get("logo_resolution", {}).get("url"))
    
    home_img = download_or_cache_logo(home_logo_url, home["name"])
    away_img = download_or_cache_logo(away_logo_url, away["name"])

    draw_logo_card(img, home_img, home["name"], left_cx, center_y, card_size=170)
    draw_logo_card(img, away_img, away["name"], right_cx, center_y, card_size=170)

    vs_cx = width // 2
    vs_cy = center_y
    vs_radius = 42
    
    draw.ellipse(
        [vs_cx - vs_radius - 4, vs_cy - vs_radius - 4, vs_cx + vs_radius + 4, vs_cy + vs_radius + 4],
        fill=(255, 180, 0, 40)
    )
    draw.ellipse(
        [vs_cx - vs_radius, vs_cy - vs_radius, vs_cx + vs_radius, vs_cy + vs_radius],
        fill=(24, 20, 15, 240),
        outline=(255, 190, 0, 230),
        width=3
    )
    vs_font = get_font(32, bold=True)
    bbox_vs = draw.textbbox((0, 0), "VS", font=vs_font)
    vsw = bbox_vs[2] - bbox_vs[0]
    vsh = bbox_vs[3] - bbox_vs[1]
    draw.text((vs_cx - vsw // 2, vs_cy - vsh // 2 - 2), "VS", fill=(255, 215, 0), font=vs_font)

    team_name_font = get_font(24, bold=True)
    
    def render_team_name(name: str, cx: int, top_y: int):
        display_name = name
        if len(display_name) > 26:
            display_name = display_name[:24] + "..."
        bbox = draw.textbbox((0, 0), display_name, font=team_name_font)
        nw = bbox[2] - bbox[0]
        draw.text((cx - nw // 2, top_y), display_name, fill=(255, 255, 255), font=team_name_font)

    render_team_name(home["name"], left_cx, center_y + 105)
    render_team_name(away["name"], right_cx, center_y + 105)

    footer_y = height - 90
    footer_w = 680
    footer_h = 56
    fx0 = (width - footer_w) // 2
    
    draw.rounded_rectangle(
        [fx0, footer_y, fx0 + footer_w, footer_y + footer_h],
        radius=14,
        fill=(14, 20, 34, 240),
        outline=(40, 60, 90, 180),
        width=1
    )

    date_label = format_date_display(event.get("match_date", ""))
    
    if event.get("time_status") == "confirmed" and event.get("start_time_utc") and event.get("start_time_pkt"):
        utc_str = event["start_time_utc"][11:16] + " UTC"
        pkt_str = event["start_time_pkt"][11:16] + " PKT"
        footer_text = f"📅 {date_label}   |   ⏰ {utc_str}  /  {pkt_str}"
    else:
        footer_text = f"📅 {date_label}   |   ⏰ KICKOFF TIME TBD"

    footer_font = get_font(20, bold=True)
    bbox_f = draw.textbbox((0, 0), footer_text, font=footer_font)
    fw = bbox_f[2] - bbox_f[0]
    fh = bbox_f[3] - bbox_f[1]
    
    draw.text((fx0 + (footer_w - fw) // 2, footer_y + (footer_h - fh) // 2 - 2), footer_text, fill=(220, 235, 255), font=footer_font)

    img = img.convert("RGB")
    img.save(output_path, format="PNG", optimize=True)
    return output_path


def generate_all_event_images(
    events: list,
    output_dir: str = "output/images",
    raw_base_url: str = "https://raw.githubusercontent.com/Bicodes/Football-Events/main",
    max_workers: int = 8
) -> list:
    """Generates event cards for all upcoming events concurrently and populates URLs."""
    os.makedirs(output_dir, exist_ok=True)
    total = len(events)
    logger.info(f"Generating event graphics for {total} matches...")

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
                logger.info(f"Rendered {completed}/{total} event images.")

    return events
