"""
fetch_fixtures.py
Multi-source orchestrator for downloading football fixtures.
Primary Source: ESPN Public Scoreboard API (site.api.espn.com)
Secondary Fallback: OpenFootball (football.json raw repo)
"""

import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

from adapters.espn_adapter import ESPNFixtureAdapter
from adapters.openfootball_adapter import OpenFootballFixtureAdapter

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")
logger = logging.getLogger("fetch_fixtures")


def load_json_file(filepath: str) -> Any:
    with open(filepath, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def fetch_all_fixtures(
    competitions_path: str = "config/competitions.json",
    settings_path: str = "config/settings.json",
    start_date: Optional[datetime] = None,
    days_ahead: int = 30
) -> Dict[str, Any]:
    """
    Main entry point for fetching fixtures across all configured competitions
    using the multi-source adapter architecture.
    """
    if start_date is None:
        start_date = datetime.now(timezone.utc)

    competitions = load_json_file(competitions_path)
    settings = load_json_file(settings_path)

    openfootball_raw_base = settings.get("data_sources", {}).get("fallback_fixtures", {}).get(
        "raw_base", "https://raw.githubusercontent.com/openfootball/football.json/master"
    )

    espn_adapter = ESPNFixtureAdapter(timeout=12, max_workers=20)
    openfootball_adapter = OpenFootballFixtureAdapter(raw_base=openfootball_raw_base, timeout=15)

    raw_fixtures: Dict[str, Any] = {}
    statuses: List[Dict[str, Any]] = []

    for comp in competitions:
        comp_id = comp["id"]
        comp_name = comp["name"]

        if not comp.get("enabled", True):
            statuses.append({
                "id": comp_id,
                "name": comp_name,
                "status": "disabled",
                "reason": "Competition disabled in configuration",
                "matches_count": 0,
                "last_fetched": datetime.now(timezone.utc).isoformat()
            })
            continue

        # 1. Attempt Primary: ESPN
        espn_result = espn_adapter.fetch_fixtures_for_competition(
            competition=comp,
            start_date=start_date,
            days_ahead=days_ahead
        )

        matches = espn_result.get("matches", [])
        status = espn_result.get("status", {})

        # 2. If ESPN has fixtures, adopt ESPN data
        if matches and len(matches) > 0:
            logger.info(f"[Primary - ESPN] Successfully fetched {len(matches)} fixtures for '{comp_name}'.")
            raw_fixtures[comp_id] = {
                "config": comp,
                "status": status,
                "source": "ESPN",
                "matches": matches
            }
            statuses.append(status)
            continue

        # 3. Fallback to OpenFootball if ESPN returned 0 matches or had no slug
        logger.info(f"ESPN returned 0 fixtures for '{comp_name}'. Attempting secondary fallback (OpenFootball)...")
        of_result = openfootball_adapter.fetch_fixtures_for_competition(
            competition=comp,
            start_date=start_date,
            days_ahead=days_ahead
        )

        of_matches = of_result.get("matches", [])
        of_status = of_result.get("status", {})

        if of_matches and len(of_matches) > 0:
            logger.info(f"[Fallback - OpenFootball] Fetched {len(of_matches)} fixtures for '{comp_name}'.")
            raw_fixtures[comp_id] = {
                "config": comp,
                "status": of_status,
                "source": "OpenFootball",
                "matches": of_matches
            }
            statuses.append(of_status)
        else:
            # Neither provider returned fixtures
            final_status = {
                "id": comp_id,
                "name": comp_name,
                "status": "no_fixtures_found",
                "espn_status": status.get("status"),
                "openfootball_status": of_status.get("status"),
                "matches_count": 0,
                "last_fetched": datetime.now(timezone.utc).isoformat()
            }
            statuses.append(final_status)
            logger.warning(f"No fixtures available from any provider for '{comp_name}'.")

    return {
        "raw_fixtures": raw_fixtures,
        "statuses": statuses,
        "fetched_at": datetime.now(timezone.utc).isoformat()
    }


if __name__ == "__main__":
    result = fetch_all_fixtures()
    print(f"\nFetched fixtures across {len(result['raw_fixtures'])} competitions:")
    for s in result["statuses"]:
        print(f" - {s['name']}: {s['status']} ({s.get('matches_count', 0)} matches from {s.get('provider', 'None')})")
