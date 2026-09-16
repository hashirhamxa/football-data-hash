"""
generate_competition_feeds.py
Generates competition-specific feeds organized by tournament directory:
output/competitions/{competition_id}/
  ├── today.json      (Today's matches for this competition in PKT)
  ├── tomorrow.json   (Tomorrow's matches for this competition in PKT)
  └── upcoming.json   (All upcoming 30-day matches for this competition)
"""

import json
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from typing import Dict, Any, List, Optional

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")
logger = logging.getLogger("competition_feeds")

PKT_TZ = ZoneInfo("Asia/Karachi")


def load_json(filepath: str) -> Any:
    with open(filepath, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def generate_all_competition_feeds(
    upcoming_events_path: str = "output/upcoming_events.json",
    competitions_config_path: str = "config/competitions.json",
    output_base_dir: str = "output/competitions",
    now_pkt: Optional[datetime] = None
) -> Dict[str, Dict[str, Any]]:
    """
    Groups matches by competition and generates today.json, tomorrow.json, and upcoming.json
    inside output/competitions/{competition_id}/.
    """
    if now_pkt is None:
        now_pkt = datetime.now(PKT_TZ)

    if not os.path.exists(upcoming_events_path):
        logger.error(f"Source file '{upcoming_events_path}' does not exist. Run main.py first.")
        return {}

    source_data = load_json(upcoming_events_path)
    all_events: List[Dict[str, Any]] = source_data.get("events", [])
    competitions_config = load_json(competitions_config_path)

    today_date = now_pkt.date()
    tomorrow_dt = now_pkt + timedelta(days=1)
    tomorrow_date = tomorrow_dt.date()

    today_date_str = now_pkt.strftime("%Y-%m-%d")
    tomorrow_date_str = tomorrow_dt.strftime("%Y-%m-%d")

    # Map events by competition ID
    events_by_comp: Dict[str, List[Dict[str, Any]]] = {}
    for comp in competitions_config:
        events_by_comp[comp["id"]] = []

    for ev in all_events:
        comp_id = ev.get("competition", {}).get("id")
        if comp_id:
            events_by_comp.setdefault(comp_id, []).append(ev)

    summary_stats = {}

    for comp in competitions_config:
        comp_id = comp["id"]
        comp_name = comp["name"]
        comp_events = events_by_comp.get(comp_id, [])

        comp_dir = os.path.join(output_base_dir, comp_id)
        os.makedirs(comp_dir, exist_ok=True)

        # 1. Filter Today's matches (PKT)
        today_matches = []
        for ev in comp_events:
            start_pkt_str = ev.get("start_time_pkt")
            time_status = ev.get("time_status", "tbd")
            match_date_pkt = ev.get("match_date_pkt") or ev.get("match_date")

            if time_status == "confirmed" and start_pkt_str:
                try:
                    dt_pkt = datetime.fromisoformat(start_pkt_str)
                    if dt_pkt.date() == today_date and dt_pkt >= now_pkt:
                        today_matches.append(ev)
                except Exception:
                    continue
            else:
                if match_date_pkt == today_date_str:
                    today_matches.append(ev)

        today_matches.sort(
            key=lambda x: (
                x.get("start_timestamp") if x.get("start_timestamp") is not None else 9999999999,
                x["home_team"]["name"]
            )
        )

        # 2. Filter Tomorrow's matches (PKT)
        tomorrow_matches = []
        for ev in comp_events:
            start_pkt_str = ev.get("start_time_pkt")
            time_status = ev.get("time_status", "tbd")
            match_date_pkt = ev.get("match_date_pkt") or ev.get("match_date")

            if time_status == "confirmed" and start_pkt_str:
                try:
                    dt_pkt = datetime.fromisoformat(start_pkt_str)
                    if dt_pkt.date() == tomorrow_date:
                        tomorrow_matches.append(ev)
                except Exception:
                    continue
            else:
                if match_date_pkt == tomorrow_date_str:
                    tomorrow_matches.append(ev)

        tomorrow_matches.sort(
            key=lambda x: (
                x.get("start_timestamp") if x.get("start_timestamp") is not None else 9999999999,
                x["home_team"]["name"]
            )
        )

        # Base header metadata
        base_meta = {
            "version": source_data.get("version", "1.1.0"),
            "competition": {
                "id": comp_id,
                "name": comp_name,
                "country": comp.get("country", "Europe")
            },
            "timezone": "Asia/Karachi",
            "timezone_label": "PKT (UTC+05:00)",
            "generated_at": datetime.now(timezone.utc).isoformat()
        }

        # Write today.json
        today_payload = {
            **base_meta,
            "feed_type": "today",
            "target_date_pkt": today_date_str,
            "target_day_name": now_pkt.strftime("%A"),
            "total_events": len(today_matches),
            "events": today_matches
        }
        with open(os.path.join(comp_dir, "today.json"), "w", encoding="utf-8") as f:
            json.dump(today_payload, f, indent=2, ensure_ascii=False)

        # Write tomorrow.json
        tomorrow_payload = {
            **base_meta,
            "feed_type": "tomorrow",
            "target_date_pkt": tomorrow_date_str,
            "target_day_name": tomorrow_dt.strftime("%A"),
            "total_events": len(tomorrow_matches),
            "events": tomorrow_matches
        }
        with open(os.path.join(comp_dir, "tomorrow.json"), "w", encoding="utf-8") as f:
            json.dump(tomorrow_payload, f, indent=2, ensure_ascii=False)

        # Write upcoming.json
        upcoming_payload = {
            **base_meta,
            "feed_type": "upcoming_30_days",
            "total_events": len(comp_events),
            "events": comp_events
        }
        with open(os.path.join(comp_dir, "upcoming.json"), "w", encoding="utf-8") as f:
            json.dump(upcoming_payload, f, indent=2, ensure_ascii=False)

        summary_stats[comp_id] = {
            "name": comp_name,
            "today_count": len(today_matches),
            "tomorrow_count": len(tomorrow_matches),
            "upcoming_count": len(comp_events)
        }

    logger.info(f"Generated category feeds for {len(competitions_config)} competitions inside '{output_base_dir}/'.")
    return summary_stats


if __name__ == "__main__":
    stats = generate_all_competition_feeds()
    print("\n" + "=" * 65)
    print("      TOURNAMENT-SPECIFIC CATEGORY FEEDS (PKT)")
    print("=" * 65)
    for cid, data in stats.items():
        print(f"[{cid:<18}] {data['name']:<24} | Today: {data['today_count']:>2} | Tomorrow: {data['tomorrow_count']:>2} | 30-Day: {data['upcoming_count']:>3}")
    print("=" * 65 + "\n")
