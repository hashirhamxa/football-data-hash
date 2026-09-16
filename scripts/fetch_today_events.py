"""
fetch_today_events.py
Filters and publishes upcoming football events specifically for TODAY in Pakistan Standard Time (PKT, Asia/Karachi, UTC+05:00).
Handles timezone boundary offsets where matches played late night in Europe fall into early morning PKT.
"""

import json
import logging
import os
import sys
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from typing import Dict, Any, List, Optional

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")
logger = logging.getLogger("today_events")

PKT_TZ = ZoneInfo("Asia/Karachi")


def load_json(filepath: str) -> Any:
    with open(filepath, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def filter_today_events(
    events: List[Dict[str, Any]],
    now_pkt: Optional[datetime] = None,
    include_past_today: bool = False
) -> List[Dict[str, Any]]:
    """
    Filters events that occur on TODAY's date in Pakistan Standard Time (PKT).
    By default, only keeps fixtures whose kickoff in PKT is upcoming (has not already passed).
    """
    if now_pkt is None:
        now_pkt = datetime.now(PKT_TZ)

    today_date_str = now_pkt.strftime("%Y-%m-%d")
    today_date = now_pkt.date()
    today_events = []

    for ev in events:
        start_pkt_str = ev.get("start_time_pkt")
        time_status = ev.get("time_status", "tbd")

        if time_status == "confirmed" and start_pkt_str:
            try:
                dt_pkt = datetime.fromisoformat(start_pkt_str)
                # Check if the match takes place on today's calendar date in PKT
                if dt_pkt.date() == today_date:
                    if include_past_today or dt_pkt >= now_pkt:
                        today_events.append(ev)
            except Exception:
                continue
        else:
            # For TBD matches, check if match_date matches today
            if ev.get("match_date") == today_date_str:
                today_events.append(ev)

    # Sort chronologically by PKT kickoff time
    today_events.sort(
        key=lambda x: (
            x.get("start_timestamp") if x.get("start_timestamp") is not None else 9999999999,
            x["competition"]["name"],
            x["home_team"]["name"]
        )
    )
    return today_events


def generate_today_events_file(
    upcoming_events_path: str = "output/upcoming_events.json",
    output_path: str = "output/today_events.json",
    now_pkt: Optional[datetime] = None
) -> Dict[str, Any]:
    """
    Reads upcoming_events.json and writes output/today_events.json.
    """
    if now_pkt is None:
        now_pkt = datetime.now(PKT_TZ)

    if not os.path.exists(upcoming_events_path):
        logger.error(f"Source file {upcoming_events_path} does not exist. Run main.py first.")
        return {}

    source_data = load_json(upcoming_events_path)
    all_events = source_data.get("events", [])

    today_events = filter_today_events(all_events, now_pkt=now_pkt)

    payload = {
        "version": source_data.get("version", "1.0.0"),
        "timezone": "Asia/Karachi",
        "timezone_label": "PKT (UTC+05:00)",
        "target_date_pkt": now_pkt.strftime("%Y-%m-%d"),
        "target_day_name": now_pkt.strftime("%A"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_events": len(today_events),
        "events": today_events
    }

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    logger.info(f"Published {len(today_events)} TODAY (PKT) events to '{output_path}'.")
    return payload


if __name__ == "__main__":
    result = generate_today_events_file()
    print(f"\n--- TODAY'S UPCOMING MATCHES (PKT: {result.get('target_date_pkt')}) ---")
    print(f"Total Matches: {result.get('total_events', 0)}")
    for e in result.get("events", []):
        time_str = e.get("start_time_pkt", "TBD")[11:16] if e.get("start_time_pkt") else "TBD"
        print(f" - [{time_str} PKT] {e['competition']['name']}: {e['home_team']['name']} vs {e['away_team']['name']}")
