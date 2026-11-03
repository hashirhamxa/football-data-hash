"""
fetch_fixtures.py
Multi-source orchestrator for downloading football fixtures.
Tier 1 (Top Priority): Live Broadcast Scoreboard Feed (ak47 / live_feed_adapter.py)
Incoming matches are added and updated exclusively from Tier 1 (ak47).
Tier 2 (ESPN): Used strictly to enrich incoming ak47 matches with detailed metadata.
"""

import json
import logging
import os
import re
import sys
import unicodedata
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


def slugify(text: str) -> str:
    """Creates a URL-safe, lowercase alphanumeric hyphenated slug."""
    if not text:
        return "unknown"
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-").lower()
    return text or "unknown"


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


def update_ak47_match_with_espn(
    live_match: Dict[str, Any],
    espn_matches: List[Dict[str, Any]]
) -> None:
    """
    Enriches / updates an incoming match from ak47 with metadata from ESPN when matching.
    """
    lf_home = live_match.get("home_team", {}).get("name", "")
    lf_away = live_match.get("away_team", {}).get("name", "")
    lf_date = live_match.get("date_str") or (live_match.get("iso_utc")[:10] if live_match.get("iso_utc") else None)

    for em in espn_matches:
        em_home = em.get("home_team", {}).get("name", "")
        em_away = em.get("away_team", {}).get("name", "")
        em_date = em.get("date_str") or (em.get("iso_utc")[:10] if em.get("iso_utc") else None)

        if dates_match(lf_date, em_date):
            if (teams_match(lf_home, em_home) and teams_match(lf_away, em_away)) or (
                teams_match(lf_home, em_away) and teams_match(lf_away, em_home)
            ):
                if em.get("espn_id"):
                    live_match["espn_id"] = em.get("espn_id")
                if em.get("round") and em.get("round") != "Regular Fixture":
                    live_match["round"] = em.get("round")
                if (not live_match.get("iso_utc") or live_match.get("time_status") == "tbd") and em.get("iso_utc"):
                    live_match["iso_utc"] = em.get("iso_utc")
                    live_match["time_status"] = "confirmed"
                if em.get("home_team", {}).get("logo_url") and not live_match.get("home_team", {}).get("logo_url"):
                    live_match["home_team"]["logo_url"] = em["home_team"]["logo_url"]
                if em.get("away_team", {}).get("logo_url") and not live_match.get("away_team", {}).get("logo_url"):
                    live_match["away_team"]["logo_url"] = em["away_team"]["logo_url"]
                live_match["espn_matched"] = True
                break


def enrich_match_with_live_feed(
    match: Dict[str, Any],
    live_matches: List[Dict[str, Any]],
    comp_live_name: Optional[str]
) -> None:
    """
    Applies live feed tournament name and event name as top priority over upstream data.
    Preserved for backwards-compatibility with existing tests and modules.
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
    Main entry point for fetching fixtures across configured and incoming competitions.
    Incoming matches are added/updated ONLY from ak47 (Tier-1 Live Broadcast Feed).
    ESPN (Tier-2) is utilized exclusively to enrich matching incoming ak47 fixtures.
    """
    if start_date is None:
        start_date = datetime.now(timezone.utc)

    competitions = load_json_file(competitions_path)
    settings = load_json_file(settings_path)

    feed_settings = settings.get("data_sources", {}).get("priority_fixtures", {})
    api_url = feed_settings.get("api_url")

    # Initialize Adapters
    live_adapter = LiveFeedAdapter(timeout=10, api_host=api_url)
    espn_adapter = ESPNFixtureAdapter(timeout=12, max_workers=20)

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

        # 1. Tier 1 (Top Priority): Live Broadcast Feed (ak47)
        live_result = live_adapter.fetch_fixtures_for_competition(
            competition=comp,
            start_date=start_date,
            days_ahead=days_ahead
        )
        live_matches = live_result.get("matches", [])
        live_status = live_result.get("status", {})
        comp_live_name = live_status.get("name") if live_status.get("status") == "available" else None

        # Only incoming matches from ak47 are added/updated
        if not live_matches:
            status = {
                "id": comp_id,
                "name": comp_name,
                "status": "no_fixtures_in_window",
                "provider": "LiveBroadcast",
                "matches_count": 0,
                "last_fetched": datetime.now(timezone.utc).isoformat()
            }
            statuses.append(status)
            continue

        # 2. Tier 2: ESPN (used strictly to enrich matching ak47 incoming matches)
        try:
            espn_result = espn_adapter.fetch_fixtures_for_competition(
                competition=comp,
                start_date=start_date,
                days_ahead=days_ahead
            )
            espn_matches = espn_result.get("matches", [])
        except Exception as e:
            logger.debug(f"ESPN enrichment fetch skipped for {comp_name}: {e}")
            espn_matches = []

        if espn_matches:
            logger.info(f"[Tier 1 - ak47] Updating {len(live_matches)} incoming matches for '{comp_name}' with ESPN metadata...")
            for lm in live_matches:
                update_ak47_match_with_espn(lm, espn_matches)
        else:
            logger.info(f"[Tier 1 - ak47] Ingested {len(live_matches)} incoming matches for '{comp_name}' directly from ak47.")

        effective_name = comp_live_name or comp_name
        status = {
            "id": comp_id,
            "name": effective_name,
            "provider": "LiveBroadcast",
            "priority_source": "LiveBroadcast",
            "status": "available",
            "matches_count": len(live_matches),
            "last_fetched": datetime.now(timezone.utc).isoformat()
        }

        raw_fixtures[comp_id] = {
            "config": comp,
            "status": status,
            "source": "LiveBroadcast (ESPN Enriched)" if any(m.get("espn_matched") for m in live_matches) else "LiveBroadcast",
            "matches": live_matches
        }
        statuses.append(status)

    # 3. Add any remaining incoming football matches present in ak47 that were not captured above
    all_fb_events = live_adapter.get_all_football_events()
    processed_match_keys = set()
    for c_id, c_data in raw_fixtures.items():
        for m in c_data.get("matches", []):
            h = m.get("home_team", {}).get("name", "")
            a = m.get("away_team", {}).get("name", "")
            d = m.get("date_str", "")
            processed_match_keys.add((h.lower(), a.lower(), d))

    unprocessed_by_tourn: Dict[str, List[Dict[str, Any]]] = {}
    for m in all_fb_events:
        h = m.get("home_team", {}).get("name", "")
        a = m.get("away_team", {}).get("name", "")
        d = m.get("date_str", "")
        if (h.lower(), a.lower(), d) not in processed_match_keys and (a.lower(), h.lower(), d) not in processed_match_keys:
            tourn = m.get("custom_tournament_name") or "Football Tournament"
            unprocessed_by_tourn.setdefault(tourn, []).append(m)

    for tourn, m_list in unprocessed_by_tourn.items():
        dyn_comp_id = m_list[0].get("comp_id") or slugify(tourn)
        dyn_comp = {
            "id": dyn_comp_id,
            "name": tourn,
            "country": "International",
            "logo_url": m_list[0].get("competition_logo_url"),
            "enabled": True
        }
        status = {
            "id": dyn_comp_id,
            "name": tourn,
            "provider": "LiveBroadcast",
            "priority_source": "LiveBroadcast",
            "status": "available",
            "matches_count": len(m_list),
            "last_fetched": datetime.now(timezone.utc).isoformat()
        }
        raw_fixtures[dyn_comp_id] = {
            "config": dyn_comp,
            "status": status,
            "source": "LiveBroadcast",
            "matches": m_list
        }
        statuses.append(status)
        logger.info(f"[Tier 1 - ak47] Dynamically added {len(m_list)} incoming matches for '{tourn}' (comp_id: {dyn_comp_id}).")

    return {
        "raw_fixtures": raw_fixtures,
        "statuses": statuses,
        "fetched_at": datetime.now(timezone.utc).isoformat()
    }


if __name__ == "__main__":
    result = fetch_all_fixtures()
    print(f"\nFetched incoming matches across {len(result['raw_fixtures'])} competitions (exclusively from ak47):")
    for s in result["statuses"]:
        if s.get("matches_count", 0) > 0:
            print(f" - {s['name']}: {s['status']} ({s.get('matches_count', 0)} matches from {s.get('provider', 'None')})")
