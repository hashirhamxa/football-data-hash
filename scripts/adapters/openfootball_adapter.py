"""
openfootball_adapter.py
Secondary / fallback adapter for fetching fixtures from OpenFootball (football.json).
"""

import json
import logging
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from .base_adapter import BaseFixtureAdapter

logger = logging.getLogger("openfootball_adapter")
USER_AGENT = "FootballEventsPipeline/1.0 (OpenFootball Fallback Adapter)"


class OpenFootballFixtureAdapter(BaseFixtureAdapter):
    """
    Ingests fixtures from OpenFootball (football.json) raw GitHub repository.
    """

    def __init__(self, raw_base: str = "https://raw.githubusercontent.com/openfootball/football.json/master", timeout: int = 15):
        super().__init__(name="OpenFootball")
        self.raw_base = raw_base
        self.timeout = timeout

    def fetch_url_json(self, url: str) -> Optional[Dict[str, Any]]:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                content = resp.read().decode("utf-8-sig")
                return json.loads(content)
        except Exception as e:
            logger.debug(f"OpenFootball error fetching {url}: {e}")
            return None

    def discover_candidate_seasons(self) -> List[str]:
        now = datetime.now(timezone.utc)
        cy = now.year
        return [
            f"{cy}-{str(cy + 1)[-2:]}",
            f"{cy - 1}-{str(cy)[-2:]}",
            f"{cy}",
            f"{cy - 1}",
            "2026-27",
            "2025-26",
            "2024-25"
        ]

    def fetch_fixtures_for_competition(
        self,
        competition: Dict[str, Any],
        start_date: datetime,
        days_ahead: int = 30
    ) -> Dict[str, Any]:
        comp_id = competition["id"]
        comp_name = competition["name"]
        source_file = competition.get("source_file")

        if not source_file or not competition.get("enabled", True):
            return {
                "status": {
                    "id": comp_id,
                    "name": comp_name,
                    "provider": "OpenFootball",
                    "status": "disabled" if not competition.get("enabled", True) else "no_source_file",
                    "matches_count": 0,
                    "last_fetched": datetime.now(timezone.utc).isoformat()
                },
                "matches": []
            }

        candidate_seasons = self.discover_candidate_seasons()
        data = None
        used_season = None
        source_url = None

        for season in candidate_seasons:
            url = f"{self.raw_base}/{season}/{source_file}"
            data = self.fetch_url_json(url)
            if data and "matches" in data:
                used_season = season
                source_url = url
                break

        if not data:
            root_url = f"{self.raw_base}/{source_file}"
            data = self.fetch_url_json(root_url)
            if data and "matches" in data:
                used_season = "root"
                source_url = root_url

        if not data or "matches" not in data:
            return {
                "status": {
                    "id": comp_id,
                    "name": comp_name,
                    "provider": "OpenFootball",
                    "status": "unavailable",
                    "reason": f"File '{source_file}' not found in probed seasons",
                    "matches_count": 0,
                    "last_fetched": datetime.now(timezone.utc).isoformat()
                },
                "matches": []
            }

        raw_matches = data.get("matches", [])
        parsed_matches = []

        for m in raw_matches:
            # Skip played/completed matches
            if m.get("score") or m.get("status") in ["completed", "played", "finished", "FT", "AET"]:
                continue

            date_str = m.get("date")
            time_str = m.get("time")
            team1 = m.get("team1")
            team2 = m.get("team2")

            if not date_str or not team1 or not team2:
                continue

            # Build intermediate format
            parsed_matches.append({
                "source_provider": "OpenFootball",
                "event_name": f"{team1} vs {team2}",
                "date_str": date_str,
                "time_str": time_str,
                "round": m.get("round", "Regular Fixture"),
                "group": m.get("group"),
                "home_team": {
                    "name": team1,
                    "espn_id": None,
                    "logo_url": None
                },
                "away_team": {
                    "name": team2,
                    "espn_id": None,
                    "logo_url": None
                },
                "source_url": source_url,
                "season": used_season,
                "raw_data": m
            })

        logger.info(f"OpenFootball Adapter fetched {len(parsed_matches)} matches for {comp_name}.")

        return {
            "status": {
                "id": comp_id,
                "name": comp_name,
                "provider": "OpenFootball",
                "season": used_season,
                "source_url": source_url,
                "status": "available",
                "matches_count": len(parsed_matches),
                "last_fetched": datetime.now(timezone.utc).isoformat()
            },
            "matches": parsed_matches
        }
