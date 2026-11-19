"""
tests/test_live_feed_adapter.py
Unit tests for LiveBroadcast Top-Priority Adapter, tournament/event name resolution,
and integration with the Football Events pipeline.
"""

import os
import sys
import unittest
from datetime import datetime, timezone

# Ensure scripts package is on path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts")))

from adapters.live_feed_adapter import LiveFeedAdapter, normalize_str, decrypt_dash
from fetch_fixtures import teams_match, dates_match, enrich_match_with_live_feed
from normalize_fixtures import normalize_event
from validate_output import EventItemModel


class TestLiveFeedAdapter(unittest.TestCase):

    def test_decrypt_dash_known_payload(self):
        """Verifies that plain or valid payloads are decrypted correctly."""
        plain = '{"category":"Football","eventName":"Premier League"}'
        self.assertEqual(decrypt_dash(plain), plain)

    def test_live_feed_tournament_and_event_name_resolution(self):
        adapter = LiveFeedAdapter()

        # 1. Standard Football match where eventName is the tournament
        ev1 = {
            "category": "Football",
            "eventName": "Premier League",
            "teamAName": "Everton",
            "teamBName": "Chelsea"
        }
        t_name, e_name, team_a, team_b = adapter.resolve_tournament_and_event_name(ev1)
        self.assertEqual(t_name, "Premier League")
        self.assertEqual(e_name, "Everton vs Chelsea")
        self.assertEqual(team_a, "Everton")
        self.assertEqual(team_b, "Chelsea")

        # 2. LaLiga 2 fixture
        ev2 = {
            "category": "Football",
            "eventName": "LaLiga 2",
            "teamAName": "CD Tenerife",
            "teamBName": "Girona FC"
        }
        t_name, e_name, team_a, team_b = adapter.resolve_tournament_and_event_name(ev2)
        self.assertEqual(t_name, "LaLiga 2")
        self.assertEqual(e_name, "CD Tenerife vs Girona FC")

    def test_live_feed_datetime_parsing(self):
        adapter = LiveFeedAdapter()

        # Standard DD/MM/YYYY date and HH:MM:SS time
        iso_utc, date_iso, time_clean = adapter.parse_feed_datetime("17/10/2026", "11:30:00")
        self.assertEqual(date_iso, "2026-10-17")
        self.assertEqual(time_clean, "11:30:00")
        self.assertEqual(iso_utc, "2026-10-17T11:30:00Z")

        # Single digit day/month
        iso_utc, date_iso, time_clean = adapter.parse_feed_datetime("3/6/2026", "19:00:00")
        self.assertEqual(date_iso, "2026-06-03")
        self.assertEqual(iso_utc, "2026-06-03T19:00:00Z")

        # TBD time
        iso_utc, date_iso, time_clean = adapter.parse_feed_datetime("17/10/2026", "TBD")
        self.assertIsNone(iso_utc)
        self.assertEqual(date_iso, "2026-10-17")
        self.assertIsNone(time_clean)

    def test_teams_and_dates_match(self):
        self.assertTrue(teams_match("Everton", "Everton"))
        self.assertTrue(teams_match("CD Tenerife", "Tenerife"))
        self.assertTrue(teams_match("FC Barcelona", "Barcelona"))
        self.assertTrue(teams_match("Preston North End", "Preston"))
        self.assertFalse(teams_match("Arsenal", "Chelsea"))

        self.assertTrue(dates_match("2026-10-17", "2026-10-17"))
        self.assertTrue(dates_match("2026-10-17T11:30:00Z", "2026-10-17"))
        self.assertTrue(dates_match("2026-10-17", "2026-10-18"))
        self.assertFalse(dates_match("2026-10-17", "2026-10-25"))

    def test_live_feed_enrichment_priority(self):
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

        self.assertEqual(espn_match["custom_tournament_name"], "Premier League")
        self.assertEqual(espn_match["event_name"], "Everton vs Chelsea")
        self.assertEqual(espn_match["links"], "pro/test-link.txt")

    def test_live_feed_normalization_and_validation(self):
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
        self.assertIsNotNone(event)
        self.assertEqual(event["competition"]["name"], "Championship")
        self.assertEqual(event["event_name"], "Preston North End vs Sheffield United")
        self.assertEqual(event["stream_links"], "pro/stream123.txt")

        # Attach pipeline step 3 & 4 fields
        event["home_team"]["logo_resolution"] = {"source": "direct", "confidence": 1.0, "is_fallback": False}
        event["away_team"]["logo_resolution"] = {"source": "direct", "confidence": 1.0, "is_fallback": False}
        event["event_image_url"] = "https://raw.githubusercontent.com/test/image.png"

        # Pydantic validation passes
        validated = EventItemModel(**event)
        self.assertEqual(validated.event_name, "Preston North End vs Sheffield United")
        self.assertEqual(validated.competition.name, "Championship")
        self.assertEqual(validated.stream_links, "pro/stream123.txt")


if __name__ == "__main__":
    unittest.main()
