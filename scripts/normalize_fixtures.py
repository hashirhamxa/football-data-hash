"""
normalize_fixtures.py
Normalizes fixture data from multi-source adapters into a standardized, deterministic schema.
Handles:
- Timezone conversions (Source/UTC -> UTC & Asia/Karachi PKT)
- Midnight boundary detection (e.g., 19:00 UTC -> 12:00 AM next day PKT)
- High-res logo preservation (ESPN direct logos)
- Deterministic event IDs
- Strict chronological sorting
"""

import re
import unicodedata
from datetime import datetime, date, timedelta, timezone
from zoneinfo import ZoneInfo
from typing import Dict, Any, List, Optional, Tuple

PKT_TZ = ZoneInfo("Asia/Karachi")


def slugify(text: str) -> str:
    """Creates a URL-safe, lowercase alphanumeric hyphenated slug."""
    if not text:
        return "unknown"
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-").lower()
    return text or "unknown"


def format_display_time(dt: datetime) -> str:
    """Formats datetime into 12-hour format with AM/PM (e.g. '12:00 AM', '09:45 PM')."""
    return dt.strftime("%I:%M %p")


def parse_datetime_flexible(
    iso_utc_str: Optional[str] = None,
    date_str: Optional[str] = None,
    time_str: Optional[str] = None,
    source_tz_str: str = "UTC",
    target_tz_str: str = "Asia/Karachi"
) -> Tuple[Optional[str], Optional[str], Optional[int], str, Optional[str], Optional[str], Optional[str], Optional[str]]:
    """
    Parses datetime into comprehensive UTC and PKT fields.

    Returns:
        (match_date_utc, match_date_pkt, start_time_utc, start_time_pkt,
         start_timestamp, time_status, display_date, display_time)
    """
    target_tz = ZoneInfo(target_tz_str)

    # 1. ISO UTC string provided (from ESPN)
    if iso_utc_str:
        clean_iso = iso_utc_str.strip()
        try:
            # Handle '2026-09-16T19:00Z' or '2026-09-16T19:00:00Z'
            if clean_iso.endswith("Z"):
                clean_iso = clean_iso[:-1] + "+00:00"
            dt_utc = datetime.fromisoformat(clean_iso).astimezone(timezone.utc)
            dt_pkt = dt_utc.astimezone(target_tz)

            match_date_utc = dt_utc.strftime("%Y-%m-%d")
            match_date_pkt = dt_pkt.strftime("%Y-%m-%d")
            start_time_utc = dt_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
            start_time_pkt = dt_pkt.isoformat()
            start_timestamp = int(dt_utc.timestamp())
            display_date = match_date_pkt
            display_time = format_display_time(dt_pkt)

            return (
                match_date_utc,
                match_date_pkt,
                start_time_utc,
                start_time_pkt,
                start_timestamp,
                "confirmed",
                display_date,
                display_time
            )
        except Exception:
            pass

    # 2. Date + Time strings provided (from OpenFootball or fallback)
    if not date_str:
        return (None, None, None, None, None, "tbd", None, "TBD")

    if not time_str or time_str.strip().upper() in ["TBD", "TBA", "NULL", "NONE", ""]:
        # TBD match
        return (date_str, date_str, None, None, None, "tbd", date_str, "TBD")

    time_clean = time_str.strip()
    match = re.match(r"^(\d{1,2}):(\d{2})(?::(\d{2}))?$", time_clean)
    if not match:
        return (date_str, date_str, None, None, None, "tbd", date_str, "TBD")

    hour = int(match.group(1))
    minute = int(match.group(2))
    second = int(match.group(3)) if match.group(3) else 0

    try:
        source_tz = ZoneInfo(source_tz_str)
        d = date.fromisoformat(date_str)
        dt_local = datetime(d.year, d.month, d.day, hour, minute, second, tzinfo=source_tz)

        dt_utc = dt_local.astimezone(timezone.utc)
        dt_pkt = dt_local.astimezone(target_tz)

        match_date_utc = dt_utc.strftime("%Y-%m-%d")
        match_date_pkt = dt_pkt.strftime("%Y-%m-%d")
        start_time_utc = dt_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
        start_time_pkt = dt_pkt.isoformat()
        start_timestamp = int(dt_utc.timestamp())
        display_date = match_date_pkt
        display_time = format_display_time(dt_pkt)

        return (
            match_date_utc,
            match_date_pkt,
            start_time_utc,
            start_time_pkt,
            start_timestamp,
            "confirmed",
            display_date,
            display_time
        )
    except Exception:
        return (date_str, date_str, None, None, None, "tbd", date_str, "TBD")


def normalize_event(
    comp_config: Dict[str, Any],
    comp_status: Dict[str, Any],
    match: Dict[str, Any],
    ref_now: datetime,
    date_range_days: int = 30,
    target_tz_str: str = "Asia/Karachi"
) -> Optional[Dict[str, Any]]:
    """
    Normalizes a single intermediate match into the final event schema.
    """
    provider = match.get("source_provider", comp_status.get("provider", "Unknown"))
    source_tz = comp_config.get("source_timezone", "UTC")

    iso_utc = match.get("iso_utc")
    date_str = match.get("date_str")
    time_str = match.get("time_str")

    (
        match_date_utc,
        match_date_pkt,
        start_time_utc,
        start_time_pkt,
        start_timestamp,
        time_status,
        display_date,
        display_time
    ) = parse_datetime_flexible(
        iso_utc_str=iso_utc,
        date_str=date_str,
        time_str=time_str,
        source_tz_str=source_tz,
        target_tz_str=target_tz_str
    )

    if not match_date_utc:
        return None

    # Check if match has already concluded
    if start_timestamp is not None and start_timestamp < int(ref_now.timestamp()):
        return None

    # Check date range boundary (against UTC or PKT date)
    try:
        m_date_obj = date.fromisoformat(match_date_utc)
    except ValueError:
        return None

    ref_date = ref_now.date()
    max_date = ref_date + timedelta(days=date_range_days)

    if m_date_obj < ref_date or m_date_obj > max_date:
        return None

    home_raw = match.get("home_team", {})
    away_raw = match.get("away_team", {})

    home_name = home_raw.get("name")
    away_name = away_raw.get("name")

    if not home_name or not away_name:
        return None

    home_slug = slugify(home_name)
    away_slug = slugify(away_name)
    comp_id = comp_config["id"]
    comp_name = comp_config["name"]
    round_name = match.get("round", "Regular Fixture")
    group_name = match.get("group")

    # Deterministic event ID based on UTC date & team slugs
    event_id = f"{slugify(comp_id)}-{match_date_utc}-{home_slug}-{away_slug}"

    # Build home/away team dicts
    home_team_dict = {
        "name": home_name,
        "slug": home_slug,
        "espn_id": home_raw.get("espn_id"),
        "logo_url": home_raw.get("logo_url")
    }

    away_team_dict = {
        "name": away_name,
        "slug": away_slug,
        "espn_id": away_raw.get("espn_id"),
        "logo_url": away_raw.get("logo_url")
    }

    # Data source metadata
    data_source_meta = {
        "provider": provider,
        "season": comp_status.get("season", "2026-27"),
        "source_url": comp_status.get("source_url") or (
            f"https://site.api.espn.com/apis/site/v2/sports/soccer/{comp_config.get('espn_slug')}/scoreboard"
            if provider == "ESPN" else None
        )
    }

    comp_logo_url = comp_status.get("logo_url") or comp_config.get("logo_url")
    return {
        "event_id": event_id,
        "competition": {
            "id": comp_id,
            "name": comp_name,
            "country": comp_config.get("country", "Europe"),
            "round": round_name,
            "group": group_name,
            "logo_url": comp_logo_url
        },
        "round": round_name,
        "source_date": match_date_utc,
        "match_date": match_date_utc,  # Standard UTC match date
        "match_date_utc": match_date_utc,
        "match_date_pkt": match_date_pkt,
        "start_time_utc": start_time_utc,
        "start_time_pkt": start_time_pkt,
        "start_timestamp": start_timestamp,
        "display_date": display_date,
        "display_time": display_time,
        "display_timezone": target_tz_str,
        "time_status": time_status,
        "home_team": home_team_dict,
        "away_team": away_team_dict,
        "data_source": data_source_meta,
        "last_updated": datetime.now(timezone.utc).isoformat()
    }


def normalize_all_fixtures(
    raw_fixtures_data: Dict[str, Any],
    ref_now: Optional[datetime] = None,
    date_range_days: int = 30,
    target_tz_str: str = "Asia/Karachi"
) -> List[Dict[str, Any]]:
    """
    Normalizes fixtures from all fetched competitions into deduplicated, chronologically sorted events.
    """
    if ref_now is None:
        ref_now = datetime.now(timezone.utc)

    events_map: Dict[str, Dict[str, Any]] = {}

    for comp_id, comp_obj in raw_fixtures_data.items():
        comp_config = comp_obj["config"]
        comp_status = comp_obj["status"]
        matches = comp_obj.get("matches", [])

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
                # Keep ESPN / confirmed over TBD
                if eid not in events_map or (events_map[eid]["time_status"] == "tbd" and event["time_status"] == "confirmed"):
                    events_map[eid] = event

    # Sort events chronologically:
    # 1. start_timestamp (or future timestamp for TBD)
    # 2. match_date_utc
    # 3. competition name
    # 4. home team name
    sorted_events = sorted(
        events_map.values(),
        key=lambda x: (
            x["start_timestamp"] if x["start_timestamp"] is not None else 9999999999,
            x["match_date_utc"],
            x["competition"]["name"],
            x["home_team"]["name"]
        )
    )

    return sorted_events
