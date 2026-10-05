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
        center_style="nations_league_vs",
        font_family="montserrat",
        crest_container_style="glass_plate"
    ),

    # 5b. Spanish La Liga 2: Deep slate/charcoal base, coral-red & golden motion spectrum
    "la-liga-2": CompetitionTheme(
        competition_id="la-liga-2",
        name="Spanish La Liga 2",
        background_top=(18, 16, 26),
        background_bottom=(12, 10, 18),
        primary=(255, 75, 55),
        secondary=(255, 190, 30),
        highlight=(255, 150, 50),
        text_primary=(255, 255, 255),
        text_secondary=(240, 215, 195),
        panel_color=(26, 22, 34, 225),
        panel_border=(255, 75, 55, 180),
        pattern="laliga_radial_spectrum",
        center_style="nations_league_vs",
        font_family="montserrat",
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
        panel_color=(38, 16, 28, 225),
        panel_border=(235, 180, 50, 185),
        pattern="worldcup_global_arcs",
        center_style="nations_league_vs",
        font_family="montserrat",
        crest_container_style="flag_rounded_card"
    ),

    # 12. UEFA Women's Champions League: Deep midnight indigo, vibrant magenta & electric cyan
    "womens-champions-league": CompetitionTheme(
        competition_id="womens-champions-league",
        name="UEFA Women's Champions League",
        background_top=(12, 10, 36),
        background_bottom=(24, 12, 44),
        primary=(235, 30, 120),
        secondary=(0, 210, 255),
        highlight=(255, 225, 245),
        text_primary=(255, 255, 255),
        text_secondary=(230, 190, 230),
        panel_color=(24, 18, 48, 225),
        panel_border=(235, 30, 120, 180),
        pattern="champions_stars",
        center_style="champions_divider",
        font_family="montserrat",
        crest_container_style="halo"
    ),

    # 13. UEFA Nations League: Deep midnight navy, mosaic geometry, wide flag cards & lightning VS
    "nations-league": CompetitionTheme(
        competition_id="nations-league",
        name="UEFA Nations League",
        background_top=(24, 38, 68),
        background_bottom=(14, 22, 42),
        primary=(0, 180, 255),
        secondary=(235, 30, 60),
        highlight=(255, 255, 255),
        text_primary=(255, 255, 255),
        text_secondary=(185, 205, 235),
        panel_color=(16, 28, 54, 225),
        panel_border=(0, 180, 255, 180),
        pattern="nations_league_mosaic",
        center_style="nations_league_vs",
        font_family="montserrat",
        crest_container_style="flag_rounded_card"
    ),

    # 14. Arabian Gulf Cup: Deep emerald night, warm desert bronze, rich Arabian gold
    "gulf-cup": CompetitionTheme(
        competition_id="gulf-cup",
        name="Arabian Gulf Cup",
        background_top=(14, 28, 20),
        background_bottom=(28, 20, 12),
        primary=(220, 180, 60),
        secondary=(0, 160, 90),
        highlight=(255, 240, 200),
        text_primary=(255, 255, 255),
        text_secondary=(240, 230, 200),
        panel_color=(18, 28, 20, 225),
        panel_border=(220, 180, 60, 180),
        pattern="worldcup_global_arcs",
        center_style="nations_league_vs",
        font_family="montserrat",
        crest_container_style="flag_rounded_card"
    ),

    # 15. Major League Soccer (MLS): Modern crimson red, dynamic navy blue, sleek silver geometry
    "mls": CompetitionTheme(
        competition_id="mls",
        name="Major League Soccer",
        background_top=(10, 14, 28),
        background_bottom=(20, 12, 30),
        primary=(235, 30, 45),
        secondary=(0, 120, 240),
        highlight=(245, 250, 255),
        text_primary=(255, 255, 255),
        text_secondary=(190, 205, 230),
        panel_color=(20, 26, 44, 230),
        panel_border=(235, 30, 45, 185),
        pattern="carabao_cup_geometry",
        center_style="champions_divider",
        font_family="montserrat",
        crest_container_style="modern_frame"
    ),

    # 16. Africa Cup of Nations (AFCON): Rich Sahara gold, CAF emerald green, bright energetic highlights
    "africa-cup-of-nations": CompetitionTheme(
        competition_id="africa-cup-of-nations",
        name="Africa Cup of Nations",
        background_top=(12, 24, 18),
        background_bottom=(26, 20, 10),
        primary=(245, 166, 35),
        secondary=(0, 135, 81),
        highlight=(255, 235, 180),
        text_primary=(255, 255, 255),
        text_secondary=(240, 230, 200),
        panel_color=(22, 28, 20, 225),
        panel_border=(245, 166, 35, 180),
        pattern="worldcup_global_arcs",
        center_style="nations_league_vs",
        font_family="montserrat",
        crest_container_style="flag_rounded_card"
    ),

    # 17. Africa Cup of Nations Qualifying: Deep pitch green, athletic amber gold, sharp kinetic geometry
    "afcon-qualifying": CompetitionTheme(
        competition_id="afcon-qualifying",
        name="Africa Cup of Nations Qualifying",
        background_top=(10, 22, 16),
        background_bottom=(18, 16, 24),
        primary=(0, 150, 90),
        secondary=(245, 180, 40),
        highlight=(220, 255, 230),
        text_primary=(255, 255, 255),
        text_secondary=(200, 235, 215),
        panel_color=(16, 26, 20, 225),
        panel_border=(0, 150, 90, 180),
        pattern="carabao_cup_geometry",
        center_style="nations_league_vs",
        font_family="archivo",
        crest_container_style="flag_rounded_card"
    ),

    # 18. International Friendlies: Global azure blue, vivid cyan, clean luminous silver
    "international-friendlies": CompetitionTheme(
        competition_id="international-friendlies",
        name="International Friendlies",
        background_top=(10, 18, 32),
        background_bottom=(16, 24, 44),
        primary=(0, 130, 240),
        secondary=(0, 200, 180),
        highlight=(225, 245, 255),
        text_primary=(255, 255, 255),
        text_secondary=(180, 215, 245),
        panel_color=(16, 24, 44, 225),
        panel_border=(0, 130, 240, 180),
        pattern="worldcup_global_arcs",
        center_style="nations_league_vs",
        font_family="inter",
        crest_container_style="flag_rounded_card"
    ),

    # 19. UEFA European U-21 Championship Qualifiers: Deep European midnight blue, electric UEFA cyan & radiant gold, energetic national flag cards
    "uefa-u21-qualifying": CompetitionTheme(
        competition_id="uefa-u21-qualifying",
        name="UEFA European U-21 Championship Qualifiers",
        background_top=(16, 28, 64),
        background_bottom=(8, 14, 38),
        primary=(0, 195, 255),
        secondary=(255, 205, 30),
        highlight=(230, 250, 255),
        text_primary=(255, 255, 255),
        text_secondary=(185, 215, 245),
        panel_color=(18, 28, 56, 225),
        panel_border=(0, 195, 255, 180),
        pattern="nations_league_mosaic",
        center_style="nations_league_vs",
        font_family="montserrat",
        crest_container_style="flag_rounded_card"
    ),

    # 20. CONCACAF Nations League: Deep midnight navy, radiant CONCACAF amber gold & electric cyan, energetic flag cards
    "concacaf-nations-league": CompetitionTheme(
        competition_id="concacaf-nations-league",
        name="CONCACAF Nations League",
        background_top=(10, 20, 48),
        background_bottom=(18, 12, 38),
        primary=(245, 166, 35),
        secondary=(0, 195, 255),
        highlight=(255, 255, 255),
        text_primary=(255, 255, 255),
        text_secondary=(245, 225, 195),
        panel_color=(18, 24, 48, 225),
        panel_border=(245, 166, 35, 180),
        pattern="nations_league_mosaic",
        center_style="nations_league_vs",
        font_family="montserrat",
        crest_container_style="flag_rounded_card"
    ),

    # 21. CONCACAF Champions Cup: Deep obsidian & sapphire, brilliant trophy gold, modern crest frames
    "concacaf-champions-cup": CompetitionTheme(
        competition_id="concacaf-champions-cup",
        name="CONCACAF Champions Cup",
        background_top=(8, 14, 30),
        background_bottom=(16, 20, 36),
        primary=(235, 180, 50),
        secondary=(0, 110, 220),
        highlight=(230, 240, 255),
        text_primary=(255, 255, 255),
        text_secondary=(220, 210, 190),
        panel_color=(18, 26, 46, 225),
        panel_border=(235, 180, 50, 180),
        pattern="champions_stars",
        center_style="champions_divider",
        font_family="montserrat",
        crest_container_style="modern_frame"
    ),

    # 22. CONCACAF Gold Cup: Rich Aztec gold & midnight navy, fiery crimson accents, prestige flag cards
    "concacaf-gold-cup": CompetitionTheme(
        competition_id="concacaf-gold-cup",
        name="CONCACAF Gold Cup",
        background_top=(28, 18, 8),
        background_bottom=(12, 16, 34),
        primary=(255, 185, 20),
        secondary=(220, 30, 50),
        highlight=(255, 245, 210),
        text_primary=(255, 255, 255),
        text_secondary=(245, 225, 190),
        panel_color=(26, 20, 16, 225),
        panel_border=(255, 185, 20, 180),
        pattern="worldcup_global_arcs",
        center_style="nations_league_vs",
        font_family="montserrat",
        crest_container_style="flag_rounded_card"
    ),

    # 23. Spanish Liga F: Deep violet & midnight slate base, Spanish coral-magenta & golden radial spectrum, modern glass crest plates
    "liga-f": CompetitionTheme(
        competition_id="liga-f",
        name="Spanish Liga F",
        background_top=(24, 12, 36),
        background_bottom=(12, 10, 22),
        primary=(255, 45, 85),
        secondary=(255, 195, 30),
        highlight=(255, 255, 255),
        text_primary=(255, 255, 255),
        text_secondary=(245, 215, 230),
        panel_color=(28, 18, 38, 225),
        panel_border=(255, 45, 85, 180),
        pattern="laliga_radial_spectrum",
        center_style="nations_league_vs",
        font_family="montserrat",
        crest_container_style="glass_plate"
    ),

    # 24. English Women's Super League: Deep cyan & midnight navy base, electric turquoise & vibrant magenta trails, modern crest frames
    "womens-super-league": CompetitionTheme(
        competition_id="womens-super-league",
        name="English Women's Super League",
        background_top=(12, 24, 44),
        background_bottom=(18, 12, 34),
        primary=(0, 225, 235),
        secondary=(255, 30, 115),
        highlight=(255, 255, 255),
        text_primary=(255, 255, 255),
        text_secondary=(190, 230, 245),
        panel_color=(18, 26, 48, 225),
        panel_border=(0, 225, 235, 180),
        pattern="pl_modern_light_trails",
        center_style="nations_league_vs",
        font_family="montserrat",
        crest_container_style="modern_frame"
    ),

    # 25. Saudi Pro League: Royal emerald green & gold, midnight dark-forest base
    "saudi-pro-league": CompetitionTheme(
        competition_id="saudi-pro-league",
        name="Saudi Pro League",
        background_top=(6, 26, 16),
        background_bottom=(10, 36, 24),
        primary=(0, 185, 115),
        secondary=(240, 190, 45),
        highlight=(220, 255, 235),
        text_primary=(255, 255, 255),
        text_secondary=(180, 230, 205),
        panel_color=(14, 32, 22, 225),
        panel_border=(0, 185, 115, 180),
        pattern="neutral_sleek_graphite",
        center_style="nations_league_vs",
        font_family="montserrat",
        crest_container_style="modern_frame"
    ),

    # 26. Coppa Italia: Italian Azure & vibrant gold/crimson
    "coppa-italia": CompetitionTheme(
        competition_id="coppa-italia",
        name="Coppa Italia",
        background_top=(8, 20, 38),
        background_bottom=(16, 12, 28),
        primary=(0, 130, 235),
        secondary=(225, 35, 55),
        highlight=(245, 200, 50),
        text_primary=(255, 255, 255),
        text_secondary=(200, 220, 245),
        panel_color=(16, 24, 44, 225),
        panel_border=(0, 130, 235, 180),
        pattern="seriea_hex_geometry",
        center_style="seriea_dynamic_center",
        font_family="montserrat",
        crest_container_style="modern_frame"
    ),

    # 27. Brazilian Série A: Canary yellow & tropical green / deep obsidian
    "brazilian-serie-a": CompetitionTheme(
        competition_id="brazilian-serie-a",
        name="Brazilian Série A",
        background_top=(12, 26, 18),
        background_bottom=(8, 14, 24),
        primary=(255, 215, 0),
        secondary=(0, 170, 90),
        highlight=(255, 255, 255),
        text_primary=(255, 255, 255),
        text_secondary=(245, 235, 180),
        panel_color=(16, 28, 22, 225),
        panel_border=(255, 215, 0, 180),
        pattern="worldcup_global_arcs",
        center_style="nations_league_vs",
        font_family="montserrat",
        crest_container_style="modern_frame"
    ),

    # 28. 2. Bundesliga: Gunmetal & flame red/silver
    "2-bundesliga": CompetitionTheme(
        competition_id="2-bundesliga",
        name="2. Bundesliga",
        background_top=(18, 18, 24),
        background_bottom=(26, 14, 16),
        primary=(225, 40, 45),
        secondary=(180, 195, 215),
        highlight=(255, 255, 255),
        text_primary=(255, 255, 255),
        text_secondary=(225, 200, 200),
        panel_color=(26, 22, 24, 225),
        panel_border=(225, 40, 45, 180),
        pattern="bundesliga_diagonal_slashes",
        center_style="bundesliga_diamond_center",
        font_family="archivo",
        crest_container_style="metallic"
    ),

    # 29. English League One: Deep indigo & bright cyan/crimson
    "league-one": CompetitionTheme(
        competition_id="league-one",
        name="English League One",
        background_top=(14, 18, 38),
        background_bottom=(10, 12, 26),
        primary=(0, 195, 245),
        secondary=(235, 40, 75),
        highlight=(255, 255, 255),
        text_primary=(255, 255, 255),
        text_secondary=(200, 225, 250),
        panel_color=(18, 24, 46, 225),
        panel_border=(0, 195, 245, 180),
        pattern="pl_modern_light_trails",
        center_style="nations_league_vs",
        font_family="montserrat",
        crest_container_style="glass_plate"
    ),

    # 30. Scottish Championship: Royal navy & thistle silver/gold
    "scottish-championship": CompetitionTheme(
        competition_id="scottish-championship",
        name="Scottish Championship",
        background_top=(10, 18, 40),
        background_bottom=(16, 12, 30),
        primary=(25, 95, 215),
        secondary=(215, 180, 80),
        highlight=(255, 255, 255),
        text_primary=(255, 255, 255),
        text_secondary=(200, 215, 245),
        panel_color=(16, 24, 48, 225),
        panel_border=(25, 95, 215, 180),
        pattern="neutral_sleek_graphite",
        center_style="nations_league_vs",
        font_family="montserrat",
        crest_container_style="modern_frame"
    ),

    # 31. English FA Trophy: Heritage navy & trophy gold
    "fa-trophy": CompetitionTheme(
        competition_id="fa-trophy",
        name="English FA Trophy",
        background_top=(12, 16, 32),
        background_bottom=(24, 18, 10),
        primary=(240, 185, 45),
        secondary=(20, 85, 185),
        highlight=(255, 245, 205),
        text_primary=(255, 255, 255),
        text_secondary=(235, 220, 190),
        panel_color=(20, 22, 34, 225),
        panel_border=(240, 185, 45, 180),
        pattern="champions_stars",
        center_style="champions_divider",
        font_family="montserrat",
        crest_container_style="modern_frame"
    ),

    # 32. AFC Champions League Elite: Imperial gold & deep midnight indigo
    "afc-champions-league-elite": CompetitionTheme(
        competition_id="afc-champions-league-elite",
        name="AFC Champions League Elite",
        background_top=(8, 14, 36),
        background_bottom=(16, 20, 48),
        primary=(245, 190, 35),
        secondary=(0, 145, 235),
        highlight=(255, 245, 215),
        text_primary=(255, 255, 255),
        text_secondary=(230, 220, 200),
        panel_color=(18, 26, 52, 225),
        panel_border=(245, 190, 35, 180),
        pattern="champions_stars",
        center_style="champions_divider",
        font_family="montserrat",
        crest_container_style="halo"
    ),

    # 33. AFC Champions League Two: Electric sapphire & gold
    "afc-champions-league-two": CompetitionTheme(
        competition_id="afc-champions-league-two",
        name="AFC Champions League Two",
        background_top=(10, 16, 34),
        background_bottom=(14, 18, 42),
        primary=(0, 160, 240),
        secondary=(240, 185, 40),
        highlight=(215, 240, 255),
        text_primary=(255, 255, 255),
        text_secondary=(200, 225, 250),
        panel_color=(18, 24, 46, 225),
        panel_border=(0, 160, 240, 180),
        pattern="champions_stars",
        center_style="champions_divider",
        font_family="montserrat",
        crest_container_style="modern_frame"
    ),

    # 34. ASEAN Championship: Vibrant ruby red & ocean cyan
    "asean-cup": CompetitionTheme(
        competition_id="asean-cup",
        name="ASEAN Championship",
        background_top=(28, 12, 18),
        background_bottom=(10, 20, 34),
        primary=(235, 35, 60),
        secondary=(0, 185, 220),
        highlight=(255, 255, 255),
        text_primary=(255, 255, 255),
        text_secondary=(245, 215, 225),
        panel_color=(28, 18, 26, 225),
        panel_border=(235, 35, 60, 180),
        pattern="worldcup_global_arcs",
        center_style="nations_league_vs",
        font_family="montserrat",
        crest_container_style="flag_rounded_card"
    ),

    # 35. UEFA Youth League: UEFA electric cyan & star navy
    "uefa-youth-league": CompetitionTheme(
        competition_id="uefa-youth-league",
        name="UEFA Youth League",
        background_top=(8, 16, 38),
        background_bottom=(12, 22, 50),
        primary=(0, 210, 255),
        secondary=(65, 105, 235),
        highlight=(215, 245, 255),
        text_primary=(255, 255, 255),
        text_secondary=(190, 225, 250),
        panel_color=(16, 26, 56, 225),
        panel_border=(0, 210, 255, 180),
        pattern="champions_stars",
        center_style="champions_divider",
        font_family="montserrat",
        crest_container_style="modern_frame"
    ),

    # 36. Asian Games Men U23: Torch gold & jade green
    "asian-games-men-u23": CompetitionTheme(
        competition_id="asian-games-men-u23",
        name="Asian Games Men U23",
        background_top=(14, 24, 28),
        background_bottom=(10, 16, 24),
        primary=(245, 180, 30),
        secondary=(0, 180, 130),
        highlight=(255, 250, 215),
        text_primary=(255, 255, 255),
        text_secondary=(225, 240, 230),
        panel_color=(18, 28, 30, 225),
        panel_border=(245, 180, 30, 180),
        pattern="worldcup_global_arcs",
        center_style="nations_league_vs",
        font_family="montserrat",
        crest_container_style="flag_rounded_card"
    ),

    # 37. Asian Games Women: Torch gold & coral pink
    "asian-games-women": CompetitionTheme(
        competition_id="asian-games-women",
        name="Asian Games Women",
        background_top=(28, 14, 24),
        background_bottom=(12, 12, 26),
        primary=(255, 60, 115),
        secondary=(245, 180, 30),
        highlight=(255, 255, 255),
        text_primary=(255, 255, 255),
        text_secondary=(245, 215, 230),
        panel_color=(30, 18, 28, 225),
        panel_border=(255, 60, 115, 180),
        pattern="worldcup_global_arcs",
        center_style="nations_league_vs",
        font_family="montserrat",
        crest_container_style="flag_rounded_card"
    ),

    # 38. Liga Profesional de Fútbol (Argentina): Albiceleste sky blue & solar gold, midnight navy base
    "liga-profesional-argentina": CompetitionTheme(
        competition_id="liga-profesional-argentina",
        name="Liga Profesional de Fútbol",
        background_top=(10, 18, 38),
        background_bottom=(16, 28, 54),
        primary=(116, 172, 223),
        secondary=(246, 180, 14),
        highlight=(255, 255, 255),
        text_primary=(255, 255, 255),
        text_secondary=(200, 225, 250),
        panel_color=(16, 26, 52, 225),
        panel_border=(116, 172, 223, 180),
        pattern="worldcup_global_arcs",
        center_style="nations_league_vs",
        font_family="montserrat",
        crest_container_style="modern_frame"
    ),

    # 39. Neutral / Unknown Fallback: Sleek graphite/slate, ice-blue/platinum accents
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
