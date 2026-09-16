"""
resolve_logos.py
Resolves team logos deterministically using:
1. Explicit mappings (mappings/team_aliases.json)
2. Exact normalized team name matching against bundled & cached logo indices
3. Safe fuzzy matching above a strict configurable threshold
4. Secondary fallback repository
5. Generated fallback badge containing team initials

Logs unresolved or low-confidence teams to output/unmatched_teams.json.
"""

import hashlib
import json
import logging
import os
import re
import unicodedata
import urllib.parse
from difflib import SequenceMatcher
from typing import Dict, Any, List, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")
logger = logging.getLogger("resolve_logos")

USER_AGENT = "FootballEventsPipeline/1.0 (Logo Resolver)"
INDEX_FILE_PATH = "mappings/logo_index.json"
CACHE_FILE_PATH = ".cache/logo_index.json"


def clean_unicode(text: str) -> str:
    """Removes diacritics and converts to plain ASCII."""
    if not text:
        return ""
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(c for c in normalized if not unicodedata.combining(c))


def normalize_team_name(name: str) -> str:
    """
    Standardizes a football team name by removing common prefixes, suffixes,
    diacritics, and punctuation to enable high-accuracy matching.
    """
    if not name:
        return ""
    
    text = clean_unicode(name).lower()
    text = re.sub(r"[\.\,\'\`\-\_\(\)\/\&\@\+]", " ", text)
    
    stop_words = {
        "fc", "afc", "cf", "sc", "ac", "ssc", "bc", "as", "ogc", "rc", "cd", "ca",
        "ud", "rcd", "aj", "bsc", "sv", "vfb", "vfl", "tsv", "fsv", "sk", "gnk",
        "hnk", "nk", "fk", "bk", "aik", "if", "cska", "sparta", "dinamo", "dynamo",
        "club", "calcio", "balompie", "football", "de", "del", "la", "el",
        "le", "les", "du", "des", "1901", "1909", "1899", "1848", "1846", "1910",
        "1913", "1893", "1902", "1905", "1907", "1923", "1948", "04", "05", "07", "09",
        "1", "2", "3", "ev", "e.v", "athletic", "atletico"
    }
    
    tokens = [t for t in text.split() if t and t not in stop_words]
    if not tokens:
        tokens = [t for t in text.split() if t]
        
    return " ".join(tokens)


def get_core_team_stem(name: str) -> str:
    """Extracts the unique city/core stem (stripping generic words like United, City, Wanderers, Rovers, etc.)."""
    stem = normalize_team_name(name)
    generic_words = {"wanderers", "rovers", "city", "united", "town", "athletic", "albion", "county", "hotspur", "forest", "wednesday", "argyle", "north", "end", "calcio", "racing"}
    core_tokens = [t for t in stem.split() if t not in generic_words]
    return " ".join(core_tokens) if core_tokens else stem


def get_team_initials(name: str) -> str:
    """Generates 2-3 letter initials for a team name."""
    clean = clean_unicode(name)
    words = [w for w in re.split(r"[\s\-_]+", clean) if w]
    meaningful = [w for w in words if w.upper() not in ["FC", "AFC", "CF", "SC", "AC", "DE", "LA", "EL", "THE", "OF", "1.", "1901", "1909", "1899", "04", "05"]]
    if not meaningful:
        meaningful = words
        
    if len(meaningful) == 1:
        return meaningful[0][:3].upper()
    elif len(meaningful) == 2:
        return (meaningful[0][:1] + meaningful[1][:2]).upper()
    else:
        return ("".join(w[0] for w in meaningful[:3])).upper()


def get_team_color_palette(name: str) -> Tuple[Tuple[int, int, int], Tuple[int, int, int]]:
    """Generates a deterministic stylish color pair (background, accent) from team name hash."""
    h = hashlib.md5(name.encode("utf-8")).hexdigest()
    palettes = [
        ((220, 20, 60), (255, 255, 255)),    # Crimson & White
        ((0, 51, 153), (255, 215, 0)),       # Royal Blue & Gold
        ((16, 124, 65), (255, 255, 255)),    # Emerald & White
        ((112, 25, 44), (108, 171, 221)),    # Claret & Sky Blue
        ((255, 140, 0), (0, 0, 0)),          # Amber & Black
        ((26, 35, 126), (255, 255, 255)),    # Deep Navy & White
        ((136, 14, 79), (255, 215, 0)),      # Maroon & Gold
        ((0, 137, 123), (255, 255, 255)),    # Teal & White
        ((66, 66, 66), (255, 215, 0)),       # Charcoal & Gold
        ((183, 28, 28), (255, 255, 255)),    # Scarlet & White
        ((30, 136, 229), (255, 255, 255)),   # Light Blue & White
        ((46, 125, 50), (255, 235, 59))      # Forest Green & Yellow
    ]
    idx = int(h, 16) % len(palettes)
    return palettes[idx]


def generate_fallback_badge(team_name: str, output_path: str, size: int = 256) -> str:
    """Creates a fallback badge image with team initials and saves to disk."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    bg_color, text_color = get_team_color_palette(team_name)
    initials = get_team_initials(team_name)
    
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    pad = 12
    draw.ellipse([pad, pad, size - pad, size - pad], fill=bg_color, outline=(255, 255, 255, 180), width=6)
    
    inner_pad = 22
    draw.ellipse([inner_pad, inner_pad, size - inner_pad, size - inner_pad], outline=(255, 255, 255, 100), width=2)
    
    try:
        font_paths = [
            "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/segoeuib.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
        ]
        font = None
        for fp in font_paths:
            if os.path.exists(fp):
                font = ImageFont.truetype(fp, size=int(size * 0.38))
                break
        if not font:
            font = ImageFont.load_default()
    except Exception:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), initials, font=font)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    x = (size - w) / 2 - bbox[0]
    y = (size - h) / 2 - bbox[1]
    
    draw.text((x, y), initials, fill=text_color, font=font)
    img.save(output_path, format="PNG")
    return output_path


class LogoResolver:
    def __init__(
        self,
        settings_path: str = "config/settings.json",
        aliases_path: str = "mappings/team_aliases.json"
    ):
        with open(settings_path, "r", encoding="utf-8-sig") as f:
            self.settings = json.load(f)
            
        with open(aliases_path, "r", encoding="utf-8-sig") as f:
            self.aliases = json.load(f).get("aliases", {})
            
        self.primary_raw_base = self.settings["data_sources"]["primary_logos"]["raw_base"]
        self.fallback_raw_base = self.settings["data_sources"]["fallback_logos"]["raw_base"]
        self.fuzzy_threshold = self.settings.get("fuzzy_match_threshold", 0.80)
        
        self.repo_slug = self.settings.get("github_repo", "Bicodes/Football-Events")
        self.branch = self.settings.get("github_branch", "main")
        
        self.indexed_logos: List[Dict[str, Any]] = []
        self.unmatched_teams: Dict[str, Dict[str, Any]] = {}
        
        self._load_logo_index()

    def _load_logo_index(self):
        """Loads logo index from bundled file or cache."""
        for path in [INDEX_FILE_PATH, CACHE_FILE_PATH]:
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8-sig") as f:
                        data = json.load(f)
                        if isinstance(data, list) and len(data) > 0:
                            self.indexed_logos = data
                            logger.info(f"Loaded {len(self.indexed_logos)} indexed logos from '{path}'.")
                            return
                except Exception as e:
                    logger.warning(f"Failed to read index from {path}: {e}")

    def resolve(self, team_name: str, league_dir_hint: Optional[str] = None) -> Dict[str, Any]:
        """Resolves logo URL for a team name."""
        if not team_name:
            team_name = "Unknown"

        # 1. Explicit Alias lookup
        if team_name in self.aliases:
            alias_target = self.aliases[team_name]
            alias_norm = normalize_team_name(alias_target)
            
            # Match in preferred league
            for item in sorted(self.indexed_logos, key=lambda x: x.get("priority", 1)):
                if league_dir_hint and item.get("league_dir") == league_dir_hint:
                    if item["raw_name"].lower() == alias_target.lower() or item["norm_name"] == alias_norm:
                        return {
                            "url": item["raw_url"],
                            "source": "alias",
                            "confidence": 1.0,
                            "matched_name": item["raw_name"],
                            "is_fallback": False
                        }
            # Match anywhere in index
            for item in sorted(self.indexed_logos, key=lambda x: x.get("priority", 1)):
                if item["raw_name"].lower() == alias_target.lower() or item["norm_name"] == alias_norm:
                    return {
                        "url": item["raw_url"],
                        "source": "alias",
                        "confidence": 1.0,
                        "matched_name": item["raw_name"],
                        "is_fallback": False
                    }
            # If not in index, construct direct URL
            league_path = f"logos/{league_dir_hint}" if league_dir_hint else "logos/England - Premier League"
            direct_url = f"{self.primary_raw_base}/{urllib.parse.quote(league_path)}/{urllib.parse.quote(alias_target)}.png"
            return {
                "url": direct_url,
                "source": "alias",
                "confidence": 0.95,
                "matched_name": alias_target,
                "is_fallback": False
            }

        norm_query = normalize_team_name(team_name)
        raw_query_lower = clean_unicode(team_name).lower()
        stem_query = get_core_team_stem(team_name)

        # 2. Exact match in preferred league
        if league_dir_hint:
            for item in self.indexed_logos:
                if item.get("league_dir") == league_dir_hint:
                    if item["raw_name"].lower() == raw_query_lower or item["norm_name"] == norm_query:
                        return {
                            "url": item["raw_url"],
                            "source": "exact",
                            "confidence": 1.0,
                            "matched_name": item["raw_name"],
                            "is_fallback": False
                        }

        # 3. Exact match anywhere in index
        for item in sorted(self.indexed_logos, key=lambda x: x.get("priority", 1)):
            if item["raw_name"].lower() == raw_query_lower or item["norm_name"] == norm_query:
                return {
                    "url": item["raw_url"],
                    "source": "exact",
                    "confidence": 0.98,
                    "matched_name": item["raw_name"],
                    "is_fallback": False
                }

        # 4. Fuzzy match against catalog (ensuring stem similarity)
        best_match = None
        best_score = 0.0
        
        for item in self.indexed_logos:
            if stem_query and item.get("stem"):
                stem_ratio = SequenceMatcher(None, stem_query, item["stem"]).ratio()
                if stem_ratio < 0.65 and len(stem_query) > 3 and len(item["stem"]) > 3:
                    continue

            score1 = SequenceMatcher(None, norm_query, item["norm_name"]).ratio()
            score2 = SequenceMatcher(None, raw_query_lower, item["raw_name"].lower()).ratio()
            score = max(score1, score2)
            
            if league_dir_hint and item.get("league_dir") == league_dir_hint:
                score += 0.05
                
            if score > best_score:
                best_score = score
                best_match = item

        if best_match and best_score >= self.fuzzy_threshold:
            conf = min(round(best_score, 2), 0.95)
            logger.info(f"Fuzzy matched '{team_name}' -> '{best_match['raw_name']}' ({conf})")
            return {
                "url": best_match["raw_url"],
                "source": "fuzzy",
                "confidence": conf,
                "matched_name": best_match["raw_name"],
                "is_fallback": False
            }

        # 5. Generated Fallback Logo
        team_slug = re.sub(r"[^a-z0-9]+", "-", clean_unicode(team_name).lower()).strip("-")
        fallback_filename = f"{team_slug}.png"
        fallback_local_path = f"output/images/fallbacks/{fallback_filename}"
        generate_fallback_badge(team_name, fallback_local_path)
        
        fallback_raw_url = f"https://raw.githubusercontent.com/{self.repo_slug}/{self.branch}/output/images/fallbacks/{fallback_filename}"
        
        self.unmatched_teams[team_name] = {
            "team_name": team_name,
            "normalized_query": norm_query,
            "league_hint": league_dir_hint,
            "best_fuzzy_candidate": best_match["raw_name"] if best_match else None,
            "best_fuzzy_score": round(best_score, 2) if best_match else 0.0,
            "fallback_url": fallback_raw_url
        }
        
        logger.info(f"Generated fallback logo badge for team: '{team_name}'")
        return {
            "url": fallback_raw_url,
            "source": "fallback",
            "confidence": 0.0,
            "matched_name": None,
            "is_fallback": True,
            "fallback_local_path": fallback_local_path
        }

    def save_unmatched_report(self, output_path: str = "output/unmatched_teams.json"):
        """Writes all unmatched or fallback teams to output/unmatched_teams.json."""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        report = {
            "total_unmatched": len(self.unmatched_teams),
            "teams": list(self.unmatched_teams.values())
        }
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
