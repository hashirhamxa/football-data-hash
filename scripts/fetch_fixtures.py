"""
fetch_fixtures.py
Downloads fixture files from OpenFootball (football.json) safely.
Handles season resolution, competition status tracking, and graceful fallback.
"""

import json
import logging
import os
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")
logger = logging.getLogger("fetch_fixtures")

USER_AGENT = "FootballEventsPipeline/1.0 (Android Backend Service)"


def load_json_file(filepath: str) -> Any:
    with open(filepath, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def fetch_url_json(url: str, timeout: int = 15) -> Optional[Dict[str, Any]]:
    """Fetch JSON from a remote URL with proper user-agent headers."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            content = resp.read().decode("utf-8-sig")
            return json.loads(content)
    except urllib.error.HTTPError as e:
        logger.debug(f"HTTP Error {e.code} fetching {url}")
        return None
    except Exception as e:
        logger.warning(f"Error fetching {url}: {e}")
        return None


def discover_available_seasons(raw_base: str) -> List[str]:
    """
    Returns candidate seasons to probe in preferred order.
    Starts from the current year and falls back to previous seasons.
    """
    now = datetime.now(timezone.utc)
    current_year = now.year
    candidates = [
        f"{current_year}-{str(current_year + 1)[-2:]}",  # e.g. 2026-27
        f"{current_year - 1}-{str(current_year)[-2:]}",  # e.g. 2025-26
        f"{current_year}",                               # e.g. 2026
        f"{current_year - 1}",                           # e.g. 2025
        "2026-27",
        "2025-26",
        "2024-25"
    ]
    seen = set()
    ordered = []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            ordered.append(c)
    return ordered


def fetch_competition_fixtures(
    comp: Dict[str, Any],
    raw_base: str,
    candidate_seasons: List[str]
) -> Tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
    """
    Attempts to download fixture data for a competition.
    Returns (data_dict, status_dict).
    """
    comp_id = comp["id"]
    comp_name = comp["name"]
    source_file = comp["source_file"]
    
    if not comp.get("enabled", True):
        return None, {
            "id": comp_id,
            "name": comp_name,
            "status": "disabled",
            "reason": "Competition disabled in configuration",
            "season": None,
            "source_url": None,
            "matches_count": 0
        }

    # Probe seasons
    for season in candidate_seasons:
        url = f"{raw_base}/{season}/{source_file}"
        data = fetch_url_json(url)
        if data and "matches" in data:
            matches = data.get("matches", [])
            logger.info(f"Successfully fetched {comp_name} ({season}) - {len(matches)} total matches.")
            return data, {
                "id": comp_id,
                "name": comp_name,
                "status": "available",
                "season": season,
                "source_url": url,
                "matches_count": len(matches),
                "source_timezone": comp.get("source_timezone", "UTC"),
                "last_fetched": datetime.now(timezone.utc).isoformat()
            }

    # Also try root file path if season subfolder was not found
    root_url = f"{raw_base}/{source_file}"
    data = fetch_url_json(root_url)
    if data and "matches" in data:
        matches = data.get("matches", [])
        logger.info(f"Successfully fetched {comp_name} (root) - {len(matches)} total matches.")
        return data, {
            "id": comp_id,
            "name": comp_name,
            "status": "available",
            "season": "root",
            "source_url": root_url,
            "matches_count": len(matches),
            "source_timezone": comp.get("source_timezone", "UTC"),
            "last_fetched": datetime.now(timezone.utc).isoformat()
        }

    logger.warning(f"Competition '{comp_name}' is currently unavailable from OpenFootball.")
    return None, {
        "id": comp_id,
        "name": comp_name,
        "status": "unavailable",
        "reason": f"No active fixture file found for '{source_file}' across probed seasons ({', '.join(candidate_seasons[:3])})",
        "season": None,
        "source_url": None,
        "matches_count": 0,
        "source_timezone": comp.get("source_timezone", "UTC"),
        "last_fetched": datetime.now(timezone.utc).isoformat()
    }


def fetch_all_fixtures(
    competitions_path: str = "config/competitions.json",
    settings_path: str = "config/settings.json"
) -> Dict[str, Any]:
    """
    Main entry point for fetching fixtures across all configured competitions.
    """
    competitions = load_json_file(competitions_path)
    settings = load_json_file(settings_path)
    
    raw_base = settings["data_sources"]["fixtures"]["raw_base"]
    candidate_seasons = discover_available_seasons(raw_base)
    
    raw_fixtures = {}
    statuses = []
    
    for comp in competitions:
        data, status = fetch_competition_fixtures(comp, raw_base, candidate_seasons)
        statuses.append(status)
        if data:
            raw_fixtures[comp["id"]] = {
                "config": comp,
                "status": status,
                "data": data
            }
            
    return {
        "raw_fixtures": raw_fixtures,
        "statuses": statuses,
        "fetched_at": datetime.now(timezone.utc).isoformat()
    }


if __name__ == "__main__":
    result = fetch_all_fixtures()
    print(f"\nFetched {len(result['raw_fixtures'])} available competitions:")
    for s in result["statuses"]:
        print(f" - {s['name']}: {s['status']} ({s.get('matches_count', 0)} matches)")
