"""
main.py
End-to-End Orchestrator for the Football Events Pipeline.
Executes:
1. Fetching fixtures via Multi-Source Architecture (ESPN Primary + OpenFootball Fallback)
2. Normalizing fixtures and precision timezone conversions (UTC & PKT Asia/Karachi)
3. Resolving team logos with ESPN direct URL preservation and fallback handling
4. Generating 1200x630 matchday broadcast banner cards
5. Generating Global Today & Tomorrow PKT event feeds
6. Generating Tournament-specific category folders (Today, Tomorrow, Upcoming per league)
7. Validating output schemas with Pydantic
8. Publishing finalized JSON deliverables and execution summary
"""

import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from fetch_fixtures import fetch_all_fixtures
from normalize_fixtures import normalize_all_fixtures
from resolve_logos import LogoResolver
from generate_event_images import generate_all_event_images
from validate_output import validate_json_file
from fetch_today_events import generate_today_events_file
from fetch_tomorrow_events import generate_tomorrow_events_file
from generate_competition_feeds import generate_all_competition_feeds

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")
logger = logging.getLogger("pipeline_main")

PKT_TZ = ZoneInfo("Asia/Karachi")


def load_json(filepath: str):
    with open(filepath, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def run_pipeline():
    start_time = time.time()
    logger.info("Starting Football Events Pipeline execution (Multi-Source ESPN + Fallbacks)...")

    # Load configuration
    settings = load_json("config/settings.json")
    competitions = load_json("config/competitions.json")
    
    date_range_days = settings.get("date_range_days", 30)
    target_tz = settings.get("target_timezone", "Asia/Karachi")
    repo_slug = os.environ.get("GITHUB_REPOSITORY", settings.get("github_repo", "hashirhamxa/football-data-hash"))
    branch = os.environ.get("GITHUB_REF_NAME", settings.get("github_branch", "main"))
    raw_base_url = f"https://raw.githubusercontent.com/{repo_slug}/{branch}"
    
    # 1. Fetch fixtures via multi-source adapter
    logger.info("--- Step 1: Fetching Fixtures (ESPN Primary + Fallbacks) ---")
    now_utc = datetime.now(timezone.utc)
    now_pkt = datetime.now(PKT_TZ)

    fetched = fetch_all_fixtures(start_date=now_utc, days_ahead=date_range_days)
    raw_fixtures = fetched["raw_fixtures"]
    statuses = fetched["statuses"]

    # 2. Normalize fixtures
    logger.info("--- Step 2: Normalizing Fixtures & PKT Timezones ---")
    events = normalize_all_fixtures(
        raw_fixtures_data=raw_fixtures,
        ref_now=now_utc,
        date_range_days=date_range_days,
        target_tz_str=target_tz
    )
    logger.info(f"Discovered {len(events)} upcoming matches within {date_range_days} days.")

    # Limit events if configured
    max_events = settings.get("max_events", 250)
    if len(events) > max_events:
        logger.info(f"Trimming events list to top {max_events} matches.")
        events = events[:max_events]

    # 3. Resolve logos
    logger.info("--- Step 3: Resolving Team Logos ---")
    resolver = LogoResolver()
    
    logo_stats = {"espn_direct": 0, "exact": 0, "alias": 0, "fuzzy": 0, "fallback": 0, "total": 0}

    for ev in events:
        league_hint = None
        comp_id = ev["competition"]["id"]
        for c in competitions:
            if c["id"] == comp_id:
                league_hint = c.get("logo_league_dir")
                break

        # Home team logo
        home_res = resolver.resolve_team(ev["home_team"], league_hint)
        ev["home_team"]["logo_url"] = home_res["url"]
        ev["home_team"]["logo_resolution"] = {
            "source": home_res["source"],
            "confidence": home_res["confidence"],
            "matched_name": home_res.get("matched_name"),
            "is_fallback": home_res["is_fallback"]
        }
        source_key = home_res["source"].split("_")[0] if "_" in home_res["source"] else home_res["source"]
        logo_stats[source_key] = logo_stats.get(source_key, 0) + 1
        logo_stats["total"] += 1

        # Away team logo
        away_res = resolver.resolve_team(ev["away_team"], league_hint)
        ev["away_team"]["logo_url"] = away_res["url"]
        ev["away_team"]["logo_resolution"] = {
            "source": away_res["source"],
            "confidence": away_res["confidence"],
            "matched_name": away_res.get("matched_name"),
            "is_fallback": away_res["is_fallback"]
        }
        source_key = away_res["source"].split("_")[0] if "_" in away_res["source"] else away_res["source"]
        logo_stats[source_key] = logo_stats.get(source_key, 0) + 1
        logo_stats["total"] += 1

        ev["round"] = ev["competition"].get("round", "Regular Fixture")
        ev["last_updated"] = now_utc.isoformat()

    # 4. Generate matchday images
    logger.info("--- Step 4: Generating Matchday Event Images ---")
    events = generate_all_event_images(
        events=events,
        output_dir="output/images",
        raw_base_url=raw_base_url
    )

    # 5. Build output payload
    output_payload = {
        "version": settings.get("version", "1.1.0"),
        "generated_at": now_utc.isoformat(),
        "total_events": len(events),
        "date_range": {
            "start_date": now_utc.strftime("%Y-%m-%d"),
            "days_ahead": date_range_days
        },
        "data_sources": settings.get("data_sources", {}),
        "events": events
    }

    # Save upcoming_events.json
    os.makedirs("output", exist_ok=True)
    events_json_path = "output/upcoming_events.json"
    with open(events_json_path, "w", encoding="utf-8") as f:
        json.dump(output_payload, f, indent=2, ensure_ascii=False)

    resolver.save_unmatched_report("output/unmatched_teams.json")

    status_json_path = "output/competition_status.json"
    with open(status_json_path, "w", encoding="utf-8") as f:
        json.dump({"statuses": statuses, "updated_at": now_utc.isoformat()}, f, indent=2, ensure_ascii=False)

    # 6. Generate Global Today & Tomorrow PKT feeds
    logger.info("--- Step 5: Generating Global Today & Tomorrow PKT Feeds ---")
    today_res = generate_today_events_file(upcoming_events_path=events_json_path, output_path="output/today_events.json", now_pkt=now_pkt)
    tomorrow_res = generate_tomorrow_events_file(upcoming_events_path=events_json_path, output_path="output/tomorrow_events.json", now_pkt=now_pkt)

    # 7. Generate Tournament-Specific Category Feeds
    logger.info("--- Step 6: Generating Category Feeds by Tournament ---")
    comp_stats = generate_all_competition_feeds(upcoming_events_path=events_json_path, output_base_dir="output/competitions", now_pkt=now_pkt)

    logger.info("Saved JSON deliverables to output/ directory.")

    # 8. Validate output
    logger.info("--- Step 7: Validating Output Artifacts ---")
    validation_passed = validate_json_file(events_json_path, check_images=True)

    elapsed = time.time() - start_time

    # 9. Print Execution Report
    print("\n" + "=" * 70)
    print("              FOOTBALL EVENTS PIPELINE EXECUTION REPORT")
    print("=" * 70)
    print(f"Timestamp (UTC):  {now_utc.isoformat()}")
    print(f"Timestamp (PKT):  {now_pkt.isoformat()}")
    print(f"Execution Time:   {elapsed:.2f} seconds")
    print(f"Total Upcoming:   {len(events)} matches (Next {date_range_days} Days)")
    print(f"Today (PKT):      {today_res.get('total_events', 0)} matches ({now_pkt.strftime('%Y-%m-%d')})")
    print(f"Tomorrow (PKT):   {tomorrow_res.get('total_events', 0)} matches ({tomorrow_res.get('target_date_pkt')})")
    print(f"Validation:       {'PASSED' if validation_passed else 'FAILED'}")
    
    print("\n[Tournament Folders & Feeds (output/competitions/{id}/)]:")
    for cid, cinfo in comp_stats.items():
        print(f"  * {cid:<18} -> Today: {cinfo['today_count']:>2} | Tomorrow: {cinfo['tomorrow_count']:>2} | 30-Day: {cinfo['upcoming_count']:>3}")

    print("\n[Deliverable Endpoints]:")
    print(f"  * All Upcoming:      {raw_base_url}/output/upcoming_events.json")
    print(f"  * Today (PKT):       {raw_base_url}/output/today_events.json")
    print(f"  * Tomorrow (PKT):    {raw_base_url}/output/tomorrow_events.json")
    print(f"  * League Today:      {raw_base_url}/output/competitions/{{league_id}}/today.json")
    print(f"  * League Tomorrow:   {raw_base_url}/output/competitions/{{league_id}}/tomorrow.json")
    print(f"  * League Upcoming:   {raw_base_url}/output/competitions/{{league_id}}/upcoming.json")
    print(f"  * Generated Images:  {raw_base_url}/output/images/{{event_id}}.png")
    print("=" * 70 + "\n")

    if not validation_passed:
        sys.exit(1)


if __name__ == "__main__":
    run_pipeline()
