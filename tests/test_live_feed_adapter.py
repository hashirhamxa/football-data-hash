"""
tests/test_live_feed_adapter.py
Unit tests for LiveBroadcast Top-Priority Adapter, tournament/event name resolution,
and integration with the Football Events pipeline.
"""

import os
import sys
from datetime import datetime, timezone

import pytest

# Ensure scripts package is on path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts")))

from adapters.live_feed_adapter import LiveFeedAdapter, normalize_str, decrypt_dash
from fetch_fixtures import teams_match, dates_match, enrich_match_with_live_feed
from normalize_fixtures import normalize_event
from validate_output import EventItemModel


def test_decrypt_dash_known_payload():
    """Verifies that plain or valid payloads are decrypted correctly."""
    plain = '{"category":"Football","eventName":"Premier League"}'
    assert decrypt_dash(plain) == plain


def test_live_feed_tournament_and_event_name_resolution():
    adapter = LiveFeedAdapter()

    # 1. Standard Football match where eventName is the tournament
    ev1 = {
        "category": "Football",
        "eventName": "Premier League",
        "teamAName": "Everton",
        "teamBName": "Chelsea"
    }
    t_name, e_name, team_a, team_b = adapter.resolve_tournament_and_event_name(ev1)
    assert t_name == "Premier League"
    assert e_name == "Everton vs Chelsea"
    assert team_a == "Everton"
    assert team_b == "Chelsea"

    # 2. LaLiga 2 fixture
    ev2 = {
        "category": "Football",
        "eventName": "LaLiga 2",
        "teamAName": "CD Tenerife",
        "teamBName": "Girona FC"
    }
    t_name, e_name, team_a, team_b = adapter.resolve_tournament_and_event_name(ev2)
    assert t_name == "LaLiga 2"
    assert e_name == "CD Tenerife vs Girona FC"


def test_live_feed_datetime_parsing():
    adapter = LiveFeedAdapter()

    # Standard DD/MM/YYYY date and HH:MM:SS time
    iso_utc, date_iso, time_clean = adapter.parse_feed_datetime("17/10/2026", "11:30:00")
    assert date_iso == "2026-10-17"
    assert time_clean == "11:30:00"
    assert iso_utc == "2026-10-17T11:30:00Z"

    # Single digit day/month
    iso_utc, date_iso, time_clean = adapter.parse_feed_datetime("3/6/2026", "19:00:00")
    assert date_iso == "2026-06-03"
    assert iso_utc == "2026-06-03T19:00:00Z"

    # TBD time
    iso_utc, date_iso, time_clean = adapter.parse_feed_datetime("17/10/2026", "TBD")
    assert iso_utc is None
    assert date_iso == "2026-10-17"
    assert time_clean is None


def test_teams_and_dates_match():
    assert teams_match("Everton", "Everton") is True
    assert teams_match("CD Tenerife", "Tenerife") is True
    assert teams_match("FC Barcelona", "Barcelona") is True
    assert teams_match("Preston North End", "Preston") is True
    assert teams_match("Arsenal", "Chelsea") is False

    assert dates_match("2026-10-17", "2026-10-17") is True
    assert dates_match("2026-10-17T11:30:00Z", "2026-10-17") is True
    assert dates_match("2026-10-17", "2026-10-18") is True
    assert dates_match("2026-10-17", "2026-10-25") is False


def test_live_feed_enrichment_priority():
    """Verifies that live feed tournament name and event name override ESPN default names."""
    espn_match = {
        "source_provider": "ESPN",
        "iso_utc": "2026-10-17T11:30:00Z",
        "date_str": "2026-10-17",
        "home_team": {"name": "Everton"},
        "away_team": {"name": "Chelsea"}
    }

    live_matches = [{
        "custom_tournament_name": "Premier League",
        "event_name": "Everton vs Chelsea",
        "date_str": "2026-10-17",
        "iso_utc": "2026-10-17T11:30:00Z",
        "home_team": {"name": "Everton"},
        "away_team": {"name": "Chelsea"},
        "links": "pro/test-link.txt"
    }]

    enrich_match_with_live_feed(espn_match, live_matches, comp_live_name="Premier League")

    assert espn_match["custom_tournament_name"] == "Premier League"
    assert espn_match["event_name"] == "Everton vs Chelsea"
    assert espn_match["links"] == "pro/test-link.txt"


def test_live_feed_normalization_and_validation():
    """Verifies end-to-end normalization of a live feed match into the final schema."""
    now_utc = datetime(2026, 11, 3, 12, 0, 0, tzinfo=timezone.utc)
    comp_config = {
        "id": "championship",
        "name": "English Championship",
        "country": "England"
    }
    comp_status = {
        "id": "championship",
        "name": "Championship",
        "provider": "LiveBroadcast",
        "status": "available"
    }
    match = {
        "source_provider": "LiveBroadcast",
        "custom_tournament_name": "Championship",
        "event_name": "Preston North End vs Sheffield United",
        "iso_utc": "2026-11-03T19:45:00Z",
        "round": "Regular Fixture",
        "home_team": {"name": "Preston North End", "logo_url": "https://img.sofascore.com/team1.png"},
        "away_team": {"name": "Sheffield United", "logo_url": "https://img.sofascore.com/team2.png"},
        "competition_logo_url": "https://img.sofascore.com/tourn.png",
        "links": "pro/stream123.txt"
    }

    event = normalize_event(comp_config, comp_status, match, now_utc, date_range_days=7)
    assert event is not None
    assert event["competition"]["name"] == "Championship"
    assert event["event_name"] == "Preston North End vs Sheffield United"
    assert event["stream_links"] == "pro/stream123.txt"

    # Attach pipeline step 3 & 4 fields
    event["home_team"]["logo_resolution"] = {"source": "direct", "confidence": 1.0, "is_fallback": False}
    event["away_team"]["logo_resolution"] = {"source": "direct", "confidence": 1.0, "is_fallback": False}
    event["event_image_url"] = "https://raw.githubusercontent.com/test/image.png"

    # Pydantic validation passes
    validated = EventItemModel(**event)
    assert validated.event_name == "Preston North End vs Sheffield United"
    assert validated.competition.name == "Championship"
    assert validated.stream_links == "pro/stream123.txt"
