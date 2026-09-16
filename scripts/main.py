"""
main.py
End-to-End Orchestrator for the Football Events Pipeline.
Executes:
1. Fetching fixtures from OpenFootball
2. Normalizing fixtures and timezone conversions (UTC & PKT)
3. Resolving team logos with fallback handling
4. Generating matchday broadcast card graphics
5. Validating output schemas with Pydantic
6. Publishing finalized JSON deliverables and execution summary
"""

import json
import logging
import os
import sys
import time
from datetime import datetime, timezone

from fetch_fixtures import fetch_all_fixtures
from normalize_fixtures import normalize_all_fixtures
from resolve_logos import LogoResolver
from generate_event_images import generate_all_event_images
from validate_output import validate_json_file

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")
logger = logging.getLogger("pipeline_main")


def load_json(filepath: str):
    with open(filepath, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def run_pipeline():
    start_time = time.time()
    logger.info("Starting Football Events Pipeline execution...")

    # Load configuration
    settings = load_json("config/settings.json")
    competitions = load_json("config/competitions.json")
    
    date_range_days = settings.get("date_range_days", 30)
    target_tz = settings.get("target_timezone", "Asia/Karachi")
    repo_slug = settings.get("github_repo", "Bicodes/Football-Events")
    branch = settings.get("github_branch", "main")
    raw_base_url = f"https://raw.githubusercontent.com/{repo_slug}/{branch}"
    
    # 1. Fetch fixtures
    logger.info("--- Step 1: Fetching Fixtures ---")
    fetched = fetch_all_fixtures()
    raw_fixtures = fetched["raw_fixtures"]
    statuses = fetched["statuses"]

    # 2. Normalize fixtures
    logger.info("--- Step 2: Normalizing Fixtures ---")
    now_utc = datetime.now(timezone.utc)
    events = normalize_all_fixtures(
        raw_fixtures_data=raw_fixtures,
        ref_now=now_utc,
        date_range_days=date_range_days,
        target_tz_str=target_tz
    )
    logger.info(f"Discovered {len(events)} upcoming matches within {date_range_days} days.")

    # Limit events if configured
    max_events = settings.get("max_events", 150)
    if len(events) > max_events:
        logger.info(f"Trimming events list to top {max_events} matches.")
        events = events[:max_events]

    # 3. Resolve logos
    logger.info("--- Step 3: Resolving Team Logos ---")
    resolver = LogoResolver()
    
    logo_stats = {"exact": 0, "alias": 0, "fuzzy": 0, "fallback": 0, "total": 0}

    for ev in events:
        league_hint = None
        comp_id = ev["competition"]["id"]
        for c in competitions:
            if c["id"] == comp_id:
                league_hint = c.get("logo_league_dir")
                break

        # Home team logo
        home_res = resolver.resolve(ev["home_team"]["name"], league_hint)
        ev["home_team"]["logo_url"] = home_res["url"]
        ev["home_team"]["logo_resolution"] = {
            "source": home_res["source"],
            "confidence": home_res["confidence"],
            "matched_name": home_res.get("matched_name"),
            "is_fallback": home_res["is_fallback"]
        }
        logo_stats[home_res["source"].split("_")[0]] = logo_stats.get(home_res["source"].split("_")[0], 0) + 1
        logo_stats["total"] += 1

        # Away team logo
        away_res = resolver.resolve(ev["away_team"]["name"], league_hint)
        ev["away_team"]["logo_url"] = away_res["url"]
        ev["away_team"]["logo_resolution"] = {
            "source": away_res["source"],
            "confidence": away_res["confidence"],
            "matched_name": away_res.get("matched_name"),
            "is_fallback": away_res["is_fallback"]
        }
        logo_stats[away_res["source"].split("_")[0]] = logo_stats.get(away_res["source"].split("_")[0], 0) + 1
        logo_stats["total"] += 1

        # Add top-level round string for simplified Android consumption
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
        "version": settings.get("version", "1.0.0"),
        "generated_at": now_utc.isoformat(),
        "total_events": len(events),
        "date_range": {
            "start_date": now_utc.strftime("%Y-%m-%d"),
            "days_ahead": date_range_days
        },
        "data_sources": settings.get("data_sources", {}),
        "events": events
    }

    # Save JSON artifacts
    os.makedirs("output", exist_ok=True)
    events_json_path = "output/upcoming_events.json"
    with open(events_json_path, "w", encoding="utf-8") as f:
        json.dump(output_payload, f, indent=2, ensure_ascii=False)

    resolver.save_unmatched_report("output/unmatched_teams.json")

    status_json_path = "output/competition_status.json"
    with open(status_json_path, "w", encoding="utf-8") as f:
        json.dump({"statuses": statuses, "updated_at": now_utc.isoformat()}, f, indent=2, ensure_ascii=False)

    logger.info("Saved JSON deliverables to output/ directory.")

    # 6. Validate output
    logger.info("--- Step 6: Validating Output Artifacts ---")
    validation_passed = validate_json_file(events_json_path, check_images=True)

    elapsed = time.time() - start_time

    # 7. Print Execution Report
    print("\n" + "=" * 70)
    print("              FOOTBALL EVENTS PIPELINE EXECUTION REPORT")
    print("=" * 70)
    print(f"Timestamp:       {now_utc.isoformat()}")
    print(f"Execution Time:  {elapsed:.2f} seconds")
    print(f"Total Events:    {len(events)} matches")
    print(f"Validation:      {'PASSED' if validation_passed else 'FAILED'}")
    print("\n[Competitions Monitored]:")
    for s in statuses:
        status_symbol = "OK" if s["status"] == "available" else "UNAVAILABLE"
        season_info = f"({s.get('season')})" if s.get('season') else ""
        print(f"  * {s['name']:<26} [{status_symbol}] {s.get('matches_count', 0):>4} matches {season_info}")
    
    print("\n[Logo Resolution Stats]:")
    print(f"  * Exact Matches:    {logo_stats.get('exact', 0)} ({logo_stats.get('exact', 0)/max(1, logo_stats['total'])*100:.1f}%)")
    print(f"  * Alias Matches:    {logo_stats.get('alias', 0)} ({logo_stats.get('alias', 0)/max(1, logo_stats['total'])*100:.1f}%)")
    print(f"  * Fuzzy Matches:    {logo_stats.get('fuzzy', 0)} ({logo_stats.get('fuzzy', 0)/max(1, logo_stats['total'])*100:.1f}%)")
    print(f"  * Fallback Badges:  {logo_stats.get('fallback', 0)} ({logo_stats.get('fallback', 0)/max(1, logo_stats['total'])*100:.1f}%)")
    print(f"  * Total Logos:      {logo_stats['total']}")

    print("\n[Deliverable Files]:")
    print(f"  * Events JSON:       output/upcoming_events.json")
    print(f"  * Competition Log:   output/competition_status.json")
    print(f"  * Unmatched Report:  output/unmatched_teams.json")
    print(f"  * Generated Images:  output/images/ ({len(events)} images generated)")
    print(f"  * Android Raw URL:   {raw_base_url}/output/upcoming_events.json")
    print("=" * 70 + "\n")

    if not validation_passed:
        sys.exit(1)


if __name__ == "__main__":
    run_pipeline()
