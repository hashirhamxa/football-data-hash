"""
espn_adapter.py
Primary adapter for fetching live and upcoming football fixtures from ESPN public scoreboards.
Endpoints:
- Base Scoreboard: https://site.api.espn.com/apis/site/v2/sports/soccer/{slug}/scoreboard
- Date Scoreboard: https://site.api.espn.com/apis/site/v2/sports/soccer/{slug}/scoreboard?dates=YYYYMMDD
"""

import json
import logging
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional

from .base_adapter import BaseFixtureAdapter

logger = logging.getLogger("espn_adapter")
USER_AGENT = "Mozilla/5.0"


class ESPNFixtureAdapter(BaseFixtureAdapter):
    """
    Ingests live fixture schedules, official logos, and kickoff times from ESPN.
    """

    def __init__(self, timeout: int = 12, max_workers: int = 10):
        super().__init__(name="ESPN Public API")
        self.timeout = timeout
        self.max_workers = max_workers
        self.base_url = "https://site.api.espn.com/apis/site/v2/sports/soccer"

    def fetch_url_json(self, url: str, max_retries: int = 3) -> Optional[Dict[str, Any]]:
        """
        Fetches JSON from ESPN endpoint with clean browser headers and automatic retry.
        """
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json, text/plain, */*"
            }
        )
        for attempt in range(max_retries):
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    content = resp.read().decode("utf-8")
                    return json.loads(content)
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    return None
                logger.debug(f"HTTP {e.code} fetching {url} (attempt {attempt + 1}/{max_retries})")
            except Exception as e:
                logger.debug(f"Error fetching {url}: {e} (attempt {attempt + 1}/{max_retries})")
        return None

    def fetch_date_scoreboard(self, slug: str, date_str: str) -> Optional[Dict[str, Any]]:
        url = f"{self.base_url}/{slug}/scoreboard?dates={date_str}"
        return self.fetch_url_json(url)

    def fetch_current_scoreboard(self, slug: str) -> Optional[Dict[str, Any]]:
        url = f"{self.base_url}/{slug}/scoreboard"
        return self.fetch_url_json(url)

    def parse_espn_event(self, event: Dict[str, Any], comp_config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Parses a single ESPN event into a standardized raw match dict.
        """
        status = event.get("status", {})
        status_type = status.get("type", {})
        state = status_type.get("state", "pre").lower()
        is_completed = status_type.get("completed", False)
        if state == "post" or is_completed:
            return None

        iso_date = event.get("date")
        if not iso_date:
            return None

        competitions = event.get("competitions", [])
        if not competitions:
            return None

        main_comp = competitions[0]
        competitors = main_comp.get("competitors", [])
        if len(competitors) < 2:
            return None

        home_competitor = None
        away_competitor = None

        for c in competitors:
            if c.get("homeAway") == "home":
                home_competitor = c
            elif c.get("homeAway") == "away":
                away_competitor = c

        if not home_competitor or not away_competitor:
            home_competitor = competitors[0]
            away_competitor = competitors[1]

        home_team = home_competitor.get("team", {})
        away_team = away_competitor.get("team", {})

        home_name = home_team.get("displayName") or home_team.get("name")
        away_name = away_team.get("displayName") or away_team.get("name")

        if not home_name or not away_name:
            return None

        home_logo = home_team.get("logo")
        away_logo = away_team.get("logo")

        round_name = "Regular Fixture"
        notes = main_comp.get("notes", [])
        if notes and isinstance(notes, list) and len(notes) > 0:
            headline = notes[0].get("headline")
            if headline:
                round_name = headline
        elif "season" in event and "type" in event.get("season", {}):
            season_type = event["season"].get("type")
            if season_type == 3:
                round_name = "Playoffs / Knockout"

        time_status = "confirmed"
        if status_type.get("detail", "").upper() in ["TBD", "TBA"]:
            time_status = "tbd"

        return {
            "source_provider": "ESPN",
            "espn_id": event.get("id"),
            "event_name": event.get("name"),
            "iso_utc": iso_date,
            "time_status": time_status,
            "round": round_name,
            "home_team": {
                "name": home_name,
                "espn_id": home_team.get("id"),
                "abbreviation": home_team.get("abbreviation"),
                "logo_url": home_logo
            },
            "away_team": {
                "name": away_name,
                "espn_id": away_team.get("id"),
                "abbreviation": away_team.get("abbreviation"),
                "logo_url": away_logo
            },
            "venue": main_comp.get("venue", {}).get("fullName"),
            "raw_data": event
        }

    def fetch_fixtures_for_competition(
        self,
        competition: Dict[str, Any],
        start_date: datetime,
        days_ahead: int = 30
    ) -> Dict[str, Any]:
        """
        Fetches fixtures across active scoreboard, monthly calendars, and upcoming dates.
        """
        slug = competition.get("espn_slug")
        comp_id = competition["id"]
        comp_name = competition["name"]

        if not slug or not competition.get("enabled", True):
            return {
                "status": {
                    "id": comp_id,
                    "name": comp_name,
                    "provider": "ESPN",
                    "status": "disabled" if not competition.get("enabled", True) else "no_espn_slug",
                    "matches_count": 0,
                    "last_fetched": datetime.now(timezone.utc).isoformat()
                },
                "matches": []
            }

        all_matches = []
        seen_espn_ids = set()

        def add_event(ev: Dict[str, Any]):
            parsed = self.parse_espn_event(ev, competition)
            if parsed:
                eid = parsed.get("espn_id")
                if eid and eid not in seen_espn_ids:
                    seen_espn_ids.add(eid)
                    all_matches.append(parsed)
                elif not eid:
                    all_matches.append(parsed)

        # 1. Fetch current scoreboard (active round/gameweek)
        curr_data = self.fetch_current_scoreboard(slug)
        if curr_data:
            for ev in curr_data.get("events", []):
                add_event(ev)

        # 2. Collect monthly queries (YYYYMM) covering the entire date window
        # (e.g. 202609 and 202610 for a 30-day window starting mid-September)
        query_dates = set()
        month_keys = set()
        for i in range(days_ahead + 1):
            d = start_date + timedelta(days=i)
            month_keys.add(d.strftime("%Y%m"))
            # Also include direct dates for immediate 7 days for precision
            if i <= 7:
                query_dates.add(d.strftime("%Y%m%d"))

        # Combine monthly keys and key direct dates
        all_query_params = list(month_keys) + list(query_dates)

        with ThreadPoolExecutor(max_workers=min(self.max_workers, len(all_query_params) or 1)) as executor:
            future_to_param = {
                executor.submit(self.fetch_date_scoreboard, slug, param): param
                for param in all_query_params
            }

            for future in as_completed(future_to_param):
                data = future.result()
                if not data:
                    continue
                for ev in data.get("events", []):
                    add_event(ev)

        league_logo_url = None
        if curr_data and "leagues" in curr_data and curr_data["leagues"]:
            logos = curr_data["leagues"][0].get("logos", [])
            if logos and isinstance(logos, list) and len(logos) > 0:
                league_logo_url = logos[0].get("href")

        logger.info(f"ESPN Adapter fetched {len(all_matches)} upcoming matches for {comp_name} ({slug}).")

        status_result = {
            "id": comp_id,
            "name": comp_name,
            "provider": "ESPN",
            "espn_slug": slug,
            "logo_url": league_logo_url or competition.get("logo_url"),
            "status": "available" if len(all_matches) > 0 else "no_fixtures_in_window",
            "matches_count": len(all_matches),
            "last_fetched": datetime.now(timezone.utc).isoformat()
        }

        return {
            "status": status_result,
            "matches": all_matches
        }
