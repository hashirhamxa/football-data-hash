"""
normalize_fixtures.py
Normalizes raw fixture data into a standardized, deterministic schema.
Handles timezone conversion (Source -> UTC and Asia/Karachi PKT),
upcoming date-window filtering, completed-match exclusion, and deterministic event IDs.
"""

import re
import unicodedata
from datetime import datetime, date, timedelta, timezone
from zoneinfo import ZoneInfo
from typing import Dict, Any, List, Optional, Tuple


def slugify(text: str) -> str:
    """Creates a URL-safe, lowercase alphanumeric hyphenated slug."""
    if not text:
        return "unknown"
    # Normalize unicode to ASCII
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    # Replace non-alphanumeric characters with hyphens
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-").lower()
    return text or "unknown"


def is_completed_match(match: Dict[str, Any]) -> bool:
    """Checks if a match has already been completed according to score or status."""
    if "score" in match and match["score"]:
        return True
    status = match.get("status", "").lower()
    if status in ["completed", "played", "finished", "ft", "aet", "pen"]:
        return True
    return False


def parse_match_datetime(
    date_str: str,
    time_str: Optional[str],
    source_tz_str: str,
    target_tz_str: str = "Asia/Karachi"
) -> Tuple[Optional[str], Optional[str], Optional[int], str]:
    """
    Parses date and time into UTC and PKT representations.
    Returns (start_time_utc, start_time_pkt, start_timestamp, time_status).
    """
    if not time_str or time_str.strip().upper() in ["TBD", "TBA", "NULL", "NONE", ""]:
        return None, None, None, "tbd"

    # Clean time string (e.g. '20:00' or '20:00:00')
    time_clean = time_str.strip()
    match = re.match(r"^(\d{1,2}):(\d{2})(?::(\d{2}))?$", time_clean)
    if not match:
        return None, None, None, "tbd"

    hour = int(match.group(1))
    minute = int(match.group(2))
    second = int(match.group(3)) if match.group(3) else 0

    try:
        source_tz = ZoneInfo(source_tz_str)
        target_tz = ZoneInfo(target_tz_str)
        
        # Parse date
        d = date.fromisoformat(date_str)
        
        # Build timezone-aware local datetime
        dt_local = datetime(d.year, d.month, d.day, hour, minute, second, tzinfo=source_tz)
        
        # Convert to UTC and Target TZ (PKT)
        dt_utc = dt_local.astimezone(timezone.utc)
        dt_target = dt_local.astimezone(target_tz)
        
        # Format strings
        start_time_utc = dt_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
        start_time_pkt = dt_target.isoformat()
        start_timestamp = int(dt_utc.timestamp())
        
        return start_time_utc, start_time_pkt, start_timestamp, "confirmed"
    except Exception:
        return None, None, None, "tbd"


def normalize_event(
    comp_config: Dict[str, Any],
    comp_status: Dict[str, Any],
    match: Dict[str, Any],
    ref_now: datetime,
    date_range_days: int = 30,
    target_tz_str: str = "Asia/Karachi"
) -> Optional[Dict[str, Any]]:
    """
    Normalizes a single raw match into the event schema if it qualifies as upcoming.
    """
    # Exclude completed matches
    if is_completed_match(match):
        return None

    # Date must exist
    date_str = match.get("date")
    if not date_str:
        return None

    try:
        match_date = date.fromisoformat(date_str)
    except ValueError:
        return None

    ref_date = ref_now.date()
    max_date = ref_date + timedelta(days=date_range_days)

    # Filter by date window [ref_date, ref_date + date_range_days]
    if match_date < ref_date or match_date > max_date:
        return None

    # Extract team names
    home_team_name = match.get("team1")
    away_team_name = match.get("team2")
    if not home_team_name or not away_team_name:
        return None

    source_tz = comp_config.get("source_timezone", "UTC")
    time_str = match.get("time")

    utc_iso, pkt_iso, timestamp, time_status = parse_match_datetime(
        date_str=date_str,
        time_str=time_str,
        source_tz_str=source_tz,
        target_tz_str=target_tz_str
    )

    # If confirmed time has already passed today, skip
    if timestamp is not None and timestamp < int(ref_now.timestamp()):
        return None

    comp_id = comp_config["id"]
    comp_name = comp_config["name"]
    round_name = match.get("round", "Regular Fixture")
    group_name = match.get("group")
    match_status = match.get("status", "scheduled").lower()

    # Deterministic event ID: {competition}-{date}-{home-team}-{away-team}
    comp_slug = slugify(comp_id)
    home_slug = slugify(home_team_name)
    away_slug = slugify(away_team_name)
    event_id = f"{comp_slug}-{date_str}-{home_slug}-{away_slug}"

    return {
        "event_id": event_id,
        "competition": {
            "id": comp_id,
            "name": comp_name,
            "country": comp_config.get("country", "Europe"),
            "round": round_name,
            "group": group_name
        },
        "match_date": date_str,
        "time_status": time_status,
        "start_time_utc": utc_iso,
        "start_time_pkt": pkt_iso,
        "start_timestamp": timestamp,
        "source_timezone": source_tz,
        "home_team": {
            "name": home_team_name,
            "slug": home_slug
        },
        "away_team": {
            "name": away_team_name,
            "slug": away_slug
        },
        "match_status": match_status,
        "data_source": {
            "provider": "OpenFootball",
            "season": comp_status.get("season", "2026-27"),
            "file": comp_config.get("source_file"),
            "source_url": comp_status.get("source_url")
        }
    }


def normalize_all_fixtures(
    raw_fixtures_data: Dict[str, Any],
    ref_now: Optional[datetime] = None,
    date_range_days: int = 30,
    target_tz_str: str = "Asia/Karachi"
) -> List[Dict[str, Any]]:
    """
    Normalizes fixtures across all downloaded competitions, deduplicates, and sorts.
    """
    if ref_now is None:
        ref_now = datetime.now(timezone.utc)

    events_map: Dict[str, Dict[str, Any]] = {}

    for comp_id, comp_obj in raw_fixtures_data.items():
        comp_config = comp_obj["config"]
        comp_status = comp_obj["status"]
        raw_json = comp_obj["data"]
        matches = raw_json.get("matches", [])

        for match in matches:
            event = normalize_event(
                comp_config=comp_config,
                comp_status=comp_status,
                match=match,
                ref_now=ref_now,
                date_range_days=date_range_days,
                target_tz_str=target_tz_str
            )
            if event:
                eid = event["event_id"]
                # Keep event with confirmed time over tbd if duplicate exists
                if eid not in events_map or (events_map[eid]["time_status"] == "tbd" and event["time_status"] == "confirmed"):
                    events_map[eid] = event

    # Sort events chronologically
    sorted_events = sorted(
        events_map.values(),
        key=lambda x: (
            x["match_date"],
            x["start_timestamp"] if x["start_timestamp"] is not None else 9999999999,
            x["competition"]["name"],
            x["home_team"]["name"]
        )
    )

    return sorted_events


if __name__ == "__main__":
    from fetch_fixtures import fetch_all_fixtures
    fetched = fetch_all_fixtures()
    events = normalize_all_fixtures(fetched["raw_fixtures"], date_range_days=30)
    print(f"\nNormalized {len(events)} upcoming events across the next 30 days:")
    for e in events[:10]:
        print(f"[{e['match_date']} {e['start_time_utc'] or 'TBD'}] {e['competition']['name']}: {e['home_team']['name']} vs {e['away_team']['name']} (ID: {e['event_id']})")
