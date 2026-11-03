"""
live_feed_adapter.py
Top-Priority fixture adapter for ingesting tournament names, event names,
schedules, and stream metadata directly from live broadcast scoreboards.
"""

import base64
import json
import logging
import os
import re
import unicodedata
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple

import requests
import urllib3
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

try:
    from .base_adapter import BaseFixtureAdapter
except ImportError:
    from scripts.adapters.base_adapter import BaseFixtureAdapter

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
logger = logging.getLogger("live_feed_adapter")

# Secure broadcast feed endpoint and protocol keys
DEFAULT_API_HOST = "https://hellobabu.xyz/"
KEY_BYTES = b"az1sUE8zNnNUVXpN"
IV_BYTES = b"dz00QVhsNmZZU0Fw"

# Optional environment-based local data path
ENV_LOCAL_DATA_DIR = os.environ.get("SPORTS_FEED_DATA_DIR")

# Canonical mapping of tournament names / categories to competition IDs
TOURNAMENT_NAME_MAP = {
    "premier league": "premier-league",
    "epl": "premier-league",
    "english premier league": "premier-league",
    "championship": "championship",
    "english championship": "championship",
    "laliga": "la-liga",
    "la liga": "la-liga",
    "spanish la liga": "la-liga",
    "laliga 2": "la-liga-2",
    "la liga 2": "la-liga-2",
    "spanish la liga 2": "la-liga-2",
    "serie a": "serie-a",
    "italian serie a": "serie-a",
    "serie b": "serie-b",
    "italian serie b": "serie-b",
    "bundesliga": "bundesliga",
    "german bundesliga": "bundesliga",
    "2. bundesliga": "2-bundesliga",
    "ligue 1": "ligue-1",
    "french ligue 1": "ligue-1",
    "ligue 2": "ligue-2",
    "french ligue 2": "ligue-2",
    "champions league": "champions-league",
    "uefa champions league": "champions-league",
    "europa league": "europa-league",
    "uefa europa league": "europa-league",
    "conference league": "conference-league",
    "uefa conference league": "conference-league",
    "saudi pro league": "saudi-pro-league",
    "scottish premiership": "scottish-championship",
    "scottish championship": "scottish-championship",
    "vriendenloterij eredivisie": "eredivisie",
    "eredivisie": "eredivisie",
    "liga profesional de futbol": "liga-profesional-argentina",
    "liga profesional de fútbol": "liga-profesional-argentina",
    "lpf": "liga-profesional-argentina",
    "campeonato brasileiro serie a": "brazilian-serie-a",
    "campeonato brasileiro série a": "brazilian-serie-a",
    "brazilian serie a": "brazilian-serie-a",
    "brazilian série a": "brazilian-serie-a",
    "trendyol super lig": "turkish-super-lig",
    "trendyol süper lig": "turkish-super-lig",
    "turkish super lig": "turkish-super-lig",
    "a-league men": "a-league-men",
    "australian a-league men": "a-league-men",
    "allsvenskan": "swedish-allsvenskan",
    "swedish allsvenskan": "swedish-allsvenskan",
    "women's super league": "womens-super-league",
    "copa del rey": "copa-del-rey",
    "coppa italia": "coppa-italia",
    "dfb-pokal": "dfb-pokal",
    "carabao cup": "carabao-cup",
    "mls": "mls",
    "major league soccer": "mls",
    "liga mx": "liga-mx",
    "liga mx, apertura": "liga-mx",
    "liga mx, clausura": "liga-mx",
    "colombian primera a": "colombian-primera-a",
    "conmebol libertadores": "conmebol-libertadores",
    "conmebol sudamericana": "conmebol-sudamericana",
    "afc champions league elite": "afc-champions-league-elite",
    "afc champions league two": "afc-champions-league-two",
    "concacaf champions cup": "concacaf-champions-cup",
}


def normalize_str(s: str) -> str:
    """Removes accents and lowercases for robust matching."""
    if not s:
        return ""
    normalized = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    return normalized.lower().strip()


def decrypt_dash(raw_str: str) -> str:
    """
    AES-128-CBC decryption matching broadcast feed encoding.
    """
    trimmed = raw_str.strip()
    if trimmed.startswith("{") or trimmed.startswith("["):
        return trimmed
    try:
        b1 = bytearray(base64.b64decode(trimmed))
        for i in range(1, len(b1), 2):
            b1[i - 1], b1[i] = b1[i], b1[i - 1]
        b1.reverse()
        ciphertext = base64.b64decode(bytes(b1))
        cipher = AES.new(KEY_BYTES, AES.MODE_CBC, IV_BYTES)
        decrypted = cipher.decrypt(ciphertext)
        return unpad(decrypted, 16).decode("utf-8")
    except Exception as e:
        logger.debug(f"Decryption error: {e}")
        return ""


class LiveFeedAdapter(BaseFixtureAdapter):
    """
    Top-Priority Adapter ingesting tournament names and event names from the live broadcast network.
    """

    def __init__(self, timeout: int = 8, local_dir: Optional[str] = None, api_host: Optional[str] = None):
        super().__init__(name="LiveBroadcast")
        self.timeout = timeout
        self.local_dir = local_dir or ENV_LOCAL_DATA_DIR
        self.api_host = api_host or DEFAULT_API_HOST
        self._all_events_cache: Optional[List[Dict[str, Any]]] = None

    def _fetch_live_or_cached_events(self) -> List[Dict[str, Any]]:
        """
        Attempts to fetch live decrypted events; falls back to local JSON cache.
        """
        if self._all_events_cache is not None:
            return self._all_events_cache

        events_json = None

        # 1. Attempt live network fetch
        try:
            if self.api_host.endswith(".txt"):
                url = self.api_host
            else:
                url = self.api_host.rstrip("/") + "/events.txt"
            r = requests.get(url, timeout=self.timeout, verify=False)
            if r.status_code == 200 and r.text.strip():
                decrypted_str = decrypt_dash(r.text)
                if decrypted_str:
                    events_json = json.loads(decrypted_str)
                    logger.info(f"Successfully fetched & decrypted {len(events_json)} live events from broadcast feed.")
                    # Cache locally for offline resilience
                    try:
                        cache_path = os.path.join(os.path.dirname(__file__), "..", "..", ".cache", "live_feed_events.json")
                        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
                        with open(cache_path, "w", encoding="utf-8") as f:
                            json.dump(events_json, f)
                    except Exception:
                        pass
        except Exception as e:
            logger.info(f"Live broadcast feed fetch skipped ({e}), checking cache/local fallback...")

        # 2. Fallback to local files if network was unavailable
        if not events_json:
            fallback_candidates = [
                os.path.join(os.path.dirname(__file__), "..", "..", ".cache", "live_feed_events.json"),
            ]
            if self.local_dir:
                fallback_candidates.insert(0, os.path.join(self.local_dir, "debug", "events_decrypted.json"))
                fallback_candidates.insert(1, os.path.join(self.local_dir, "events_decrypted.json"))

            for path in fallback_candidates:
                if os.path.exists(path):
                    try:
                        with open(path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            if isinstance(data, list):
                                events_json = data
                                logger.info(f"Loaded {len(events_json)} events from local cache: {path}")
                                break
                    except Exception as e:
                        logger.debug(f"Failed loading cache {path}: {e}")

        if not events_json:
            logger.warning("Could not load events from live feed or local cache.")
            self._all_events_cache = []
            return []

        # Parse wrapped event strings if needed
        parsed_events: List[Dict[str, Any]] = []
        for item in events_json:
            raw = item.get("event")
            if isinstance(raw, str):
                try:
                    ev = json.loads(raw)
                    parsed_events.append(ev)
                except Exception:
                    continue
            elif isinstance(raw, dict):
                parsed_events.append(raw)
            elif isinstance(item, dict) and "eventName" in item:
                parsed_events.append(item)

        self._all_events_cache = parsed_events
        return self._all_events_cache

    def resolve_tournament_and_event_name(self, ev: Dict[str, Any]) -> Tuple[str, str, str, str]:
        """
        Determines:
        - tournament_name (e.g. "Premier League", "LaLiga")
        - event_name (e.g. "Everton vs Chelsea")
        - team_a (e.g. "Everton")
        - team_b (e.g. "Chelsea")
        """
        event_name_field = ev.get("eventName", "").strip()
        category_field = ev.get("category", "").strip()
        team_a = ev.get("teamAName", "").strip()
        team_b = ev.get("teamBName", "").strip()

        norm_ev_name = normalize_str(event_name_field)
        norm_cat = normalize_str(category_field)

        if norm_ev_name in TOURNAMENT_NAME_MAP:
            tournament_name = event_name_field
        elif norm_cat in TOURNAMENT_NAME_MAP:
            tournament_name = category_field
        elif " vs " in event_name_field.lower():
            tournament_name = category_field if category_field and category_field.lower() != "football" else "Football Tournament"
        else:
            tournament_name = event_name_field or category_field or "Football Tournament"

        if team_a and team_b and team_a.lower() != "null" and team_b.lower() != "null" and team_a.lower() != team_b.lower():
            event_name = f"{team_a} vs {team_b}"
        elif " vs " in event_name_field.lower():
            event_name = event_name_field
        elif team_a and team_b and team_a.lower() == team_b.lower() and team_a.lower() not in ["null", "live evento"]:
            event_name = team_a
        else:
            event_name = event_name_field or (f"{team_a} vs {team_b}" if team_a and team_b else "Match Fixture")

        return tournament_name, event_name, team_a, team_b

    def parse_feed_datetime(self, date_str: Optional[str], time_str: Optional[str]) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Parses DD/MM/YYYY date and HH:MM:SS time (UTC) into:
        (iso_utc, date_str_iso, time_str)
        """
        if not date_str:
            return None, None, None

        date_clean = date_str.strip()
        m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})$", date_clean)
        if not m:
            m2 = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})$", date_clean)
            if m2:
                year, month, day = m2.group(1), m2.group(2).zfill(2), m2.group(3).zfill(2)
            else:
                return None, None, None
        else:
            day, month, year = m.group(1).zfill(2), m.group(2).zfill(2), m.group(3)

        date_iso = f"{year}-{month}-{day}"

        if not time_str or time_str.strip().upper() in ["NULL", "TBD", "TBA", ""]:
            return None, date_iso, None

        time_clean = time_str.strip()
        if len(time_clean.split(":")) == 2:
            time_clean += ":00"

        iso_utc = f"{date_iso}T{time_clean}Z"
        return iso_utc, date_iso, time_clean

    def get_all_football_events(self) -> List[Dict[str, Any]]:
        """
        Returns all parsed football events from the live feed.
        """
        raw_events = self._fetch_live_or_cached_events()
        football_matches = []

        for ev in raw_events:
            category = ev.get("category", "")
            event_name_field = ev.get("eventName", "")
            norm_cat = normalize_str(category)
            norm_name = normalize_str(event_name_field)

            is_football = (
                norm_cat == "football"
                or norm_name in TOURNAMENT_NAME_MAP
                or norm_cat in TOURNAMENT_NAME_MAP
            )
            if not is_football:
                continue

            tournament_name, event_name, team_a, team_b = self.resolve_tournament_and_event_name(ev)
            date_str = ev.get("date")
            time_str = ev.get("time")
            iso_utc, date_iso, time_clean = self.parse_feed_datetime(date_str, time_str)

            if team_a.lower() in ["live evento", "null"] and team_b.lower() in ["live evento", "null"]:
                continue

            comp_id = TOURNAMENT_NAME_MAP.get(norm_name) or TOURNAMENT_NAME_MAP.get(norm_cat)

            match_record = {
                "source_provider": "LiveBroadcast",
                "custom_tournament_name": tournament_name,
                "event_name": event_name,
                "comp_id": comp_id,
                "iso_utc": iso_utc,
                "date_str": date_iso,
                "time_str": time_clean,
                "time_status": "confirmed" if iso_utc else "tbd",
                "round": "Regular Fixture",
                "home_team": {
                    "name": team_a,
                    "logo_url": ev.get("teamAFlag")
                },
                "away_team": {
                    "name": team_b,
                    "logo_url": ev.get("teamBFlag")
                },
                "competition_logo_url": ev.get("eventLogo"),
                "links": ev.get("links"),
                "link_names": ev.get("link_names", []),
                "raw_data": ev
            }
            football_matches.append(match_record)

        return football_matches

    def fetch_fixtures_for_competition(
        self,
        competition: Dict[str, Any],
        start_date: datetime,
        days_ahead: int = 30
    ) -> Dict[str, Any]:
        """
        Fetches fixtures for a specific competition from the live broadcast feed.
        """
        comp_id = competition["id"]
        comp_name = competition.get("name", "")
        norm_target_name = normalize_str(comp_name)

        all_fb = self.get_all_football_events()
        matched: List[Dict[str, Any]] = []

        end_date = start_date + timedelta(days=days_ahead)

        for m in all_fb:
            m_comp_id = m.get("comp_id")
            m_tourn_norm = normalize_str(m.get("custom_tournament_name", ""))

            is_match = False
            if m_comp_id:
                is_match = (m_comp_id == comp_id)
            elif m_tourn_norm:
                is_match = (m_tourn_norm == norm_target_name)

            if not is_match:
                continue

            d_str = m.get("date_str")
            if d_str:
                try:
                    m_date = datetime.fromisoformat(d_str).date()
                    if m_date < start_date.date() or m_date > end_date.date():
                        continue
                except Exception:
                    pass

            matched.append(m)

        tournament_display_name = matched[0]["custom_tournament_name"] if matched else comp_name
        logger.info(f"LiveFeed Adapter found {len(matched)} fixtures for '{comp_name}' (Tournament: '{tournament_display_name}').")

        status_result = {
            "id": comp_id,
            "name": tournament_display_name,
            "provider": "LiveBroadcast",
            "logo_url": matched[0].get("competition_logo_url") if matched else competition.get("logo_url"),
            "status": "available" if len(matched) > 0 else "no_fixtures_in_window",
            "matches_count": len(matched),
            "last_fetched": datetime.now(timezone.utc).isoformat()
        }

        return {
            "status": status_result,
            "matches": matched
        }
