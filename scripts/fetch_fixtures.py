"""
fetch_fixtures.py
Multi-source orchestrator for downloading football fixtures.
Tier 1 (Top Priority): Live Broadcast Scoreboard Feed (live_feed_adapter.py)
Tier 2 (Secondary / Full Calendar): ESPN Public Scoreboard API (site.api.espn.com)
Tier 3 (Fallback): OpenFootball (football.json raw repo)
"""

import json
import logging
import os
import re
import sys
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

try:
    from adapters.live_feed_adapter import LiveFeedAdapter, TOURNAMENT_NAME_MAP, normalize_str
    from adapters.espn_adapter import ESPNFixtureAdapter
    from adapters.openfootball_adapter import OpenFootballFixtureAdapter
except ImportError:
    from scripts.adapters.live_feed_adapter import LiveFeedAdapter, TOURNAMENT_NAME_MAP, normalize_str
    from scripts.adapters.espn_adapter import ESPNFixtureAdapter
    from scripts.adapters.openfootball_adapter import OpenFootballFixtureAdapter

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")
logger = logging.getLogger("fetch_fixtures")


def load_json_file(filepath: str) -> Any:
    with open(filepath, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def teams_match(team1: str, team2: str) -> bool:
    """Fuzzy/substring check for matching team names across providers."""
    if not team1 or not team2:
        return False
    n1 = normalize_str(team1)
    n2 = normalize_str(team2)
    if n1 == n2:
        return True
    if n1 in n2 or n2 in n1:
        return True
    stop = {"fc", "cf", "cd", "ca", "sc", "rc", "afc", "ac", "de", "the", "club", "city", "town", "united"}
    w1 = set(re.findall(r"\w+", n1)) - stop
    w2 = set(re.findall(r"\w+", n2)) - stop
    if w1 and w2 and w1.intersection(w2):
        return True
    return False


def dates_match(d1: Optional[str], d2: Optional[str]) -> bool:
    """Matches dates with +/- 1 day boundary tolerance."""
    if not d1 or not d2:
        return False
    c1 = d1[:10]
    c2 = d2[:10]
    if c1 == c2:
        return True
    try:
        dt1 = datetime.fromisoformat(c1).date()
        dt2 = datetime.fromisoformat(c2).date()
        return abs((dt1 - dt2).days) <= 1
    except Exception:
        return False


def enrich_match_with_live_feed(
    match: Dict[str, Any],
    live_matches: List[Dict[str, Any]],
    comp_live_name: Optional[str]
) -> None:
    """
    Applies live feed tournament name and event name as top priority over upstream data.
    """
    if comp_live_name:
        match["custom_tournament_name"] = comp_live_name

    m_home = match.get("home_team", {}).get("name", "")
    m_away = match.get("away_team", {}).get("name", "")
    m_date = match.get("date_str") or (match.get("iso_utc")[:10] if match.get("iso_utc") else None)

    matched = False
    for lf in live_matches:
        lf_home = lf.get("home_team", {}).get("name", "")
        lf_away = lf.get("away_team", {}).get("name", "")
        lf_date = lf.get("date_str") or (lf.get("iso_utc")[:10] if lf.get("iso_utc") else None)

        if dates_match(m_date, lf_date):
            if (teams_match(m_home, lf_home) and teams_match(m_away, lf_away)) or (
                teams_match(m_home, lf_away) and teams_match(m_away, lf_home)
            ):
                match["custom_tournament_name"] = lf.get("custom_tournament_name") or comp_live_name
                match["event_name"] = lf.get("event_name")
                if lf.get("links"):
                    match["links"] = lf.get("links")
                if lf.get("link_names"):
                    match["link_names"] = lf.get("link_names")
                if lf.get("competition_logo_url"):
                    match["competition_logo_url"] = lf.get("competition_logo_url")
                matched = True
                break

    if not matched:
        match.setdefault("event_name", f"{m_home} vs {m_away}" if m_home and m_away else match.get("event_name"))
        if comp_live_name:
            match.setdefault("custom_tournament_name", comp_live_name)


def fetch_all_fixtures(
    competitions_path: str = "config/competitions.json",
    settings_path: str = "config/settings.json",
    start_date: Optional[datetime] = None,
    days_ahead: int = 30
) -> Dict[str, Any]:
    """
    Main entry point for fetching fixtures across all configured competitions
    using the multi-source adapter architecture with live broadcast feed as Top Priority.
    """
    if start_date is None:
        start_date = datetime.now(timezone.utc)

    competitions = load_json_file(competitions_path)
    settings = load_json_file(settings_path)

    openfootball_raw_base = settings.get("data_sources", {}).get("fallback_fixtures", {}).get(
        "raw_base", "https://raw.githubusercontent.com/openfootball/football.json/master"
    )

    feed_settings = settings.get("data_sources", {}).get("priority_fixtures", {})
    api_url = feed_settings.get("api_url")

    # Initialize Adapters
    live_adapter = LiveFeedAdapter(timeout=10, api_host=api_url)
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

        # 1. Tier 1 (Top Priority): Live Broadcast Feed
        live_result = live_adapter.fetch_fixtures_for_competition(
            competition=comp,
            start_date=start_date,
            days_ahead=days_ahead
        )
        live_matches = live_result.get("matches", [])
        live_status = live_result.get("status", {})
        comp_live_name = live_status.get("name") if live_status.get("status") == "available" else None

        # 2. Tier 2 (Full Calendar & Extended Schedules): ESPN
        espn_result = espn_adapter.fetch_fixtures_for_competition(
            competition=comp,
            start_date=start_date,
            days_ahead=days_ahead
        )
        espn_matches = espn_result.get("matches", [])
        espn_status = espn_result.get("status", {})

        # Merge & Apply Live Feed Priority
        if espn_matches and len(espn_matches) > 0:
            logger.info(f"[Tier 2 - ESPN] Ingested {len(espn_matches)} fixtures for '{comp_name}'. Enriching with live broadcast top priority...")
            for em in espn_matches:
                enrich_match_with_live_feed(em, live_matches, comp_live_name)

            # Include any live feed matches that were not in ESPN's calendar
            unmatched_live = []
            for lf in live_matches:
                lf_home = lf.get("home_team", {}).get("name", "")
                lf_away = lf.get("away_team", {}).get("name", "")
                lf_date = lf.get("date_str")
                in_espn = any(
                    dates_match(em.get("date_str") or (em.get("iso_utc")[:10] if em.get("iso_utc") else None), lf_date)
                    and (teams_match(em.get("home_team", {}).get("name", ""), lf_home) or teams_match(em.get("away_team", {}).get("name", ""), lf_away))
                    for em in espn_matches
                )
                if not in_espn:
                    unmatched_live.append(lf)

            combined_matches = espn_matches + unmatched_live
            effective_name = comp_live_name or comp_name
            status = {
                **espn_status,
                "name": effective_name,
                "priority_source": "LiveBroadcast",
                "matches_count": len(combined_matches),
                "live_matches_count": len(live_matches)
            }

            raw_fixtures[comp_id] = {
                "config": comp,
                "status": status,
                "source": "ESPN (Live Broadcast Prioritized)" if live_matches else "ESPN",
                "matches": combined_matches
            }
            statuses.append(status)
            continue

        # 3. If ESPN returned 0 matches, but Live Feed has matches -> adopt Live Feed directly
        if live_matches and len(live_matches) > 0:
            logger.info(f"[Tier 1 - LiveBroadcast] Adopted {len(live_matches)} fixtures directly for '{comp_name}' (Tournament: '{comp_live_name}').")
            raw_fixtures[comp_id] = {
                "config": comp,
                "status": live_status,
                "source": "LiveBroadcast",
                "matches": live_matches
            }
            statuses.append(live_status)
            continue

        # 4. Tier 3 Fallback: OpenFootball
        logger.info(f"Live feed & ESPN returned 0 fixtures for '{comp_name}'. Attempting OpenFootball fallback...")
        of_result = openfootball_adapter.fetch_fixtures_for_competition(
            competition=comp,
            start_date=start_date,
            days_ahead=days_ahead
        )

        of_matches = of_result.get("matches", [])
        of_status = of_result.get("status", {})

        if of_matches and len(of_matches) > 0:
            logger.info(f"[Fallback - OpenFootball] Fetched {len(of_matches)} fixtures for '{comp_name}'.")
            for ofm in of_matches:
                enrich_match_with_live_feed(ofm, live_matches, comp_live_name)
            raw_fixtures[comp_id] = {
                "config": comp,
                "status": of_status,
                "source": "OpenFootball",
                "matches": of_matches
            }
            statuses.append(of_status)
        else:
            final_status = {
                "id": comp_id,
                "name": comp_name,
                "status": "no_fixtures_found",
                "live_status": live_status.get("status"),
                "espn_status": espn_status.get("status"),
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
        print(f" - {s['name']}: {s['status']} ({s.get('matches_count', 0)} matches from {s.get('provider', s.get('priority_source', 'None'))})")
