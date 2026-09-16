"""
fetch_tomorrow_events.py
Filters and publishes upcoming football events specifically for TOMORROW in Pakistan Standard Time (PKT, Asia/Karachi, UTC+05:00).
Handles timezone boundary offsets where matches played late night in Europe fall into tomorrow in PKT.
"""

import json
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from typing import Dict, Any, List, Optional

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")
logger = logging.getLogger("tomorrow_events")

PKT_TZ = ZoneInfo("Asia/Karachi")


def load_json(filepath: str) -> Any:
    with open(filepath, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def filter_tomorrow_events(
    events: List[Dict[str, Any]],
    now_pkt: Optional[datetime] = None
) -> List[Dict[str, Any]]:
    """
    Filters events that occur on TOMORROW's date in Pakistan Standard Time (PKT).
    """
    if now_pkt is None:
        now_pkt = datetime.now(PKT_TZ)

    tomorrow_dt = now_pkt + timedelta(days=1)
    tomorrow_date_str = tomorrow_dt.strftime("%Y-%m-%d")
    tomorrow_date = tomorrow_dt.date()
    tomorrow_events = []

    for ev in events:
        start_pkt_str = ev.get("start_time_pkt")
        time_status = ev.get("time_status", "tbd")

        if time_status == "confirmed" and start_pkt_str:
            try:
                dt_pkt = datetime.fromisoformat(start_pkt_str)
                # Check if the match falls on tomorrow's calendar date in PKT
                if dt_pkt.date() == tomorrow_date:
                    tomorrow_events.append(ev)
            except Exception:
                continue
        else:
            # For TBD matches, check match_date
            if ev.get("match_date") == tomorrow_date_str:
                tomorrow_events.append(ev)

    # Sort chronologically by PKT kickoff time
    tomorrow_events.sort(
        key=lambda x: (
            x.get("start_timestamp") if x.get("start_timestamp") is not None else 9999999999,
            x["competition"]["name"],
            x["home_team"]["name"]
        )
    )
    return tomorrow_events


def generate_tomorrow_events_file(
    upcoming_events_path: str = "output/upcoming_events.json",
    output_path: str = "output/tomorrow_events.json",
    now_pkt: Optional[datetime] = None
) -> Dict[str, Any]:
    """
    Reads upcoming_events.json and writes output/tomorrow_events.json.
    """
    if now_pkt is None:
        now_pkt = datetime.now(PKT_TZ)

    tomorrow_dt = now_pkt + timedelta(days=1)

    if not os.path.exists(upcoming_events_path):
        logger.error(f"Source file {upcoming_events_path} does not exist. Run main.py first.")
        return {}

    source_data = load_json(upcoming_events_path)
    all_events = source_data.get("events", [])

    tomorrow_events = filter_tomorrow_events(all_events, now_pkt=now_pkt)

    payload = {
        "version": source_data.get("version", "1.0.0"),
        "timezone": "Asia/Karachi",
        "timezone_label": "PKT (UTC+05:00)",
        "target_date_pkt": tomorrow_dt.strftime("%Y-%m-%d"),
        "target_day_name": tomorrow_dt.strftime("%A"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_events": len(tomorrow_events),
        "events": tomorrow_events
    }

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    logger.info(f"Published {len(tomorrow_events)} TOMORROW (PKT) events to '{output_path}'.")
    return payload


if __name__ == "__main__":
    result = generate_tomorrow_events_file()
    print(f"\n--- TOMORROW'S MATCHES (PKT: {result.get('target_date_pkt')}) ---")
    print(f"Total Matches: {result.get('total_events', 0)}")
    for e in result.get("events", []):
        time_str = e.get("start_time_pkt", "TBD")[11:16] if e.get("start_time_pkt") else "TBD"
        print(f" - [{time_str} PKT] {e['competition']['name']}: {e['home_team']['name']} vs {e['away_team']['name']}")
