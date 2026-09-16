"""
image_themes.py
Dedicated theme configuration model and registry for football fixture event banners.
Defines competition-specific color palettes, procedural patterns, typography choices,
and center divider styles.
"""

from dataclasses import dataclass
from typing import Dict, Tuple, Optional


@dataclass(frozen=True)
class CompetitionTheme:
    """
    Encapsulates all visual styling tokens for a specific competition.
    """
    competition_id: str
    name: str
    background_top: Tuple[int, int, int]
    background_bottom: Tuple[int, int, int]
    primary: Tuple[int, int, int]              # Main brand color
    secondary: Tuple[int, int, int]            # Complementary brand color
    highlight: Tuple[int, int, int]            # Bright accent / glow
    text_primary: Tuple[int, int, int]         # Main title & team text
    text_secondary: Tuple[int, int, int]       # Sub-label & meta text
    panel_color: Tuple[int, int, int, int]     # RGBA card fill
    panel_border: Tuple[int, int, int, int]    # RGBA card border
    pattern: str                               # Background procedural pattern ID
    center_style: str                          # Central divider style ID
    font_family: str = "inter"                 # "inter", "montserrat", or "archivo"
    crest_container_style: str = "glass_plate" # "glass_plate", "halo", "pedestal", "metallic", "modern_frame"


# Registry of all competition-specific themes
THEMES_REGISTRY: Dict[str, CompetitionTheme] = {
    # 1. UEFA Champions League: Prestigious deep midnight blue/indigo, constellation geometry, silver-white highlights
    "champions-league": CompetitionTheme(
        competition_id="champions-league",
        name="UEFA Champions League",
        background_top=(6, 12, 34),
        background_bottom=(12, 18, 48),
        primary=(45, 95, 235),
        secondary=(90, 50, 190),
        highlight=(215, 235, 255),
        text_primary=(255, 255, 255),
        text_secondary=(170, 195, 240),
        panel_color=(16, 26, 62, 210),
        panel_border=(75, 120, 230, 180),
        pattern="champions_stars",
        center_style="champions_divider",
        font_family="montserrat",
        crest_container_style="halo"
    ),

    # 2. UEFA Europa League: Charcoal-black, energetic warm orange/amber, angular energy ribbons
    "europa-league": CompetitionTheme(
        competition_id="europa-league",
        name="UEFA Europa League",
        background_top=(14, 14, 18),
        background_bottom=(26, 18, 12),
        primary=(255, 102, 0),
        secondary=(230, 60, 20),
        highlight=(255, 185, 30),
        text_primary=(255, 255, 255),
        text_secondary=(245, 190, 140),
        panel_color=(28, 22, 18, 225),
        panel_border=(255, 120, 20, 190),
        pattern="europa_energy_ribbons",
        center_style="europa_energy_divider",
        font_family="archivo",
        crest_container_style="metallic"
    ),

    # 3. UEFA Conference League: Deep black/dark-green, electric neon-green & turquoise, curved shapes
    "conference-league": CompetitionTheme(
        competition_id="conference-league",
        name="UEFA Conference League",
        background_top=(8, 18, 14),
        background_bottom=(12, 28, 20),
        primary=(0, 230, 130),
        secondary=(0, 190, 200),
        highlight=(160, 255, 210),
        text_primary=(255, 255, 255),
        text_secondary=(160, 230, 200),
        panel_color=(14, 30, 22, 220),
        panel_border=(0, 220, 140, 180),
        pattern="conference_curved_geometry",
        center_style="conference_minimal_v",
        font_family="inter",
        crest_container_style="glass_plate"
    ),

    # 4. English Premier League: Deep purple/navy base, electric cyan & neon magenta, bold editorial
    "premier-league": CompetitionTheme(
        competition_id="premier-league",
        name="English Premier League",
        background_top=(24, 6, 38),
        background_bottom=(10, 12, 32),
        primary=(0, 240, 255),
        secondary=(255, 0, 128),
        highlight=(0, 255, 145),
        text_primary=(255, 255, 255),
        text_secondary=(210, 200, 240),
        panel_color=(25, 18, 45, 225),
        panel_border=(0, 225, 255, 180),
        pattern="pl_modern_light_trails",
        center_style="pl_matchday_device",
        font_family="montserrat",
        crest_container_style="modern_frame"
    ),

    # 5. Spanish La Liga: Dark neutral base, vivid multi-color accent spectrum, circular/radial motion
    "la-liga": CompetitionTheme(
        competition_id="la-liga",
        name="Spanish La Liga",
        background_top=(16, 18, 24),
        background_bottom=(10, 12, 16),
        primary=(255, 59, 48),
        secondary=(255, 204, 0),
        highlight=(255, 140, 0),
        text_primary=(255, 255, 255),
        text_secondary=(240, 220, 190),
        panel_color=(24, 26, 34, 225),
        panel_border=(255, 75, 55, 175),
        pattern="laliga_radial_spectrum",
        center_style="laliga_minimal_v",
        font_family="inter",
        crest_container_style="glass_plate"
    ),

    # 6. Italian Serie A: Deep sapphire/royal blue, cool metallic lighting, sharp Italian angles
    "serie-a": CompetitionTheme(
        competition_id="serie-a",
        name="Italian Serie A",
        background_top=(8, 20, 48),
        background_bottom=(4, 10, 26),
        primary=(0, 120, 230),
        secondary=(0, 160, 255),
        highlight=(240, 248, 255),
        text_primary=(255, 255, 255),
        text_secondary=(180, 210, 245),
        panel_color=(15, 28, 56, 225),
        panel_border=(0, 140, 245, 185),
        pattern="seriea_metallic_angles",
        center_style="seriea_vertical_beam",
        font_family="archivo",
        crest_container_style="metallic"
    ),

    # 7. German Bundesliga: Deep graphite/black, bold crimson red, high-energy diagonal motion
    "bundesliga": CompetitionTheme(
        competition_id="bundesliga",
        name="German Bundesliga",
        background_top=(14, 14, 16),
        background_bottom=(22, 22, 26),
        primary=(227, 6, 19),
        secondary=(255, 215, 0),
        highlight=(255, 255, 255),
        text_primary=(255, 255, 255),
        text_secondary=(225, 205, 205),
        panel_color=(28, 24, 26, 230),
        panel_border=(227, 6, 19, 190),
        pattern="bundesliga_diagonal_dynamics",
        center_style="bundesliga_slash_divider",
        font_family="archivo",
        crest_container_style="modern_frame"
    ),

    # 8. French Ligue 1: Dark navy, electric lime/yellow-green highlight, sleek geometric framing
    "ligue-1": CompetitionTheme(
        competition_id="ligue-1",
        name="French Ligue 1",
        background_top=(10, 16, 30),
        background_bottom=(6, 10, 20),
        primary=(198, 242, 27),
        secondary=(0, 215, 185),
        highlight=(230, 255, 100),
        text_primary=(255, 255, 255),
        text_secondary=(200, 235, 190),
        panel_color=(16, 24, 40, 225),
        panel_border=(198, 242, 27, 185),
        pattern="ligue1_geometric_frames",
        center_style="ligue1_minimal_device",
        font_family="inter",
        crest_container_style="glass_plate"
    ),

    # 9. English Championship: Dark navy & steel blue, white & red accents, authentic matchday
    "championship": CompetitionTheme(
        competition_id="championship",
        name="English Championship",
        background_top=(12, 18, 30),
        background_bottom=(20, 28, 44),
        primary=(218, 41, 28),
        secondary=(45, 95, 170),
        highlight=(245, 245, 245),
        text_primary=(255, 255, 255),
        text_secondary=(190, 205, 225),
        panel_color=(20, 28, 45, 225),
        panel_border=(80, 120, 180, 175),
        pattern="championship_stadium_atmosphere",
        center_style="championship_cross_divider",
        font_family="inter",
        crest_container_style="glass_plate"
    ),

    # 10. English Carabao Cup: Deep graphite & navy, dynamic crimson & silver trophy accents
    "carabao-cup": CompetitionTheme(
        competition_id="carabao-cup",
        name="English Carabao Cup",
        background_top=(14, 18, 28),
        background_bottom=(8, 12, 22),
        primary=(235, 30, 45),
        secondary=(0, 166, 81),
        highlight=(230, 240, 255),
        text_primary=(255, 255, 255),
        text_secondary=(195, 210, 230),
        panel_color=(22, 28, 42, 230),
        panel_border=(235, 30, 45, 190),
        pattern="carabao_cup_geometry",
        center_style="carabao_trophy_divider",
        font_family="montserrat",
        crest_container_style="modern_frame"
    ),

    # 11. FIFA World Cup: Deep royal burgundy & navy, celestial gold, global arcs
    "world-cup": CompetitionTheme(
        competition_id="world-cup",
        name="FIFA World Cup",
        background_top=(42, 10, 24),
        background_bottom=(14, 18, 36),
        primary=(235, 180, 50),
        secondary=(180, 30, 60),
        highlight=(255, 225, 120),
        text_primary=(255, 255, 255),
        text_secondary=(245, 225, 190),
        panel_color=(38, 16, 28, 230),
        panel_border=(235, 180, 50, 190),
        pattern="worldcup_global_arcs",
        center_style="worldcup_arc_divider",
        font_family="montserrat",
        crest_container_style="halo"
    ),

    # 12. Neutral / Unknown Fallback: Sleek graphite/slate, ice-blue/platinum accents
    "neutral-fallback": CompetitionTheme(
        competition_id="neutral-fallback",
        name="Football Fixture",
        background_top=(14, 18, 26),
        background_bottom=(8, 10, 16),
        primary=(50, 130, 240),
        secondary=(80, 95, 120),
        highlight=(210, 225, 250),
        text_primary=(255, 255, 255),
        text_secondary=(185, 200, 220),
        panel_color=(20, 26, 38, 225),
        panel_border=(60, 90, 140, 175),
        pattern="neutral_sleek_graphite",
        center_style="neutral_minimal_divider",
        font_family="inter",
        crest_container_style="glass_plate"
    )
}


def get_competition_theme(competition_id: Optional[str]) -> CompetitionTheme:
    """
    Resolves the CompetitionTheme for a given competition ID.
    Falls back to a polished neutral fallback theme if unknown.
    """
    if not competition_id:
        return THEMES_REGISTRY["neutral-fallback"]

    clean_id = competition_id.strip().lower()
    return THEMES_REGISTRY.get(clean_id, THEMES_REGISTRY["neutral-fallback"])
