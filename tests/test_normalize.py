"""
test_normalize.py
Unit tests for normalize_fixtures.py.
Tests timezone handling, slugification, date window filtering, and deduplication.
"""

import unittest
from datetime import datetime, timezone
import sys
import os

sys.path.insert(0, os.path.abspath("scripts"))

from normalize_fixtures import (
    slugify,
    parse_datetime_flexible,
    normalize_event,
    normalize_all_fixtures
)


class TestNormalizeFixtures(unittest.TestCase):

    def test_slugify(self):
        self.assertEqual(slugify("Arsenal FC"), "arsenal-fc")
        self.assertEqual(slugify("FC Bayern München"), "fc-bayern-munchen")
        self.assertEqual(slugify("Brighton & Hove Albion FC"), "brighton-hove-albion-fc")
        self.assertEqual(slugify("  Real  Madrid -- CF! "), "real-madrid-cf")

    def test_confirmed_match_datetime_conversion(self):
        (
            match_date_utc,
            match_date_pkt,
            start_time_utc,
            start_time_pkt,
            timestamp,
            status,
            display_date,
            display_time
        ) = parse_datetime_flexible(
            date_str="2026-09-20",
            time_str="15:00",
            source_tz_str="Europe/London",
            target_tz_str="Asia/Karachi"
        )
        self.assertEqual(status, "confirmed")
        self.assertEqual(start_time_utc, "2026-09-20T14:00:00Z")
        self.assertEqual(start_time_pkt, "2026-09-20T19:00:00+05:00")
        self.assertIsInstance(timestamp, int)
        self.assertEqual(display_date, "2026-09-20")
        self.assertEqual(display_time, "07:00 PM")

    def test_tbd_match_datetime(self):
        for tbd_val in [None, "", "TBD", "TBA", "null"]:
            (
                match_date_utc,
                match_date_pkt,
                start_time_utc,
                start_time_pkt,
                timestamp,
                status,
                display_date,
                display_time
            ) = parse_datetime_flexible(
                date_str="2026-09-20",
                time_str=tbd_val,
                source_tz_str="Europe/London"
            )
            self.assertEqual(status, "tbd")
            self.assertIsNone(start_time_utc)
            self.assertIsNone(start_time_pkt)
            self.assertIsNone(timestamp)
            self.assertEqual(display_time, "TBD")

    def test_normalize_event_window(self):
        ref_now = datetime(2026, 9, 16, 12, 0, tzinfo=timezone.utc)
        comp_config = {
            "id": "premier-league",
            "name": "English Premier League",
            "country": "England",
            "source_timezone": "Europe/London",
            "source_file": "en.1.json"
        }
        comp_status = {"season": "2026-27", "provider": "OpenFootball", "source_url": "https://example.com/en.1.json"}

        # Fixture within 30 days
        valid_match = {
            "round": "Matchday 5",
            "date_str": "2026-09-20",
            "time_str": "15:00",
            "home_team": {"name": "Arsenal FC"},
            "away_team": {"name": "Chelsea FC"}
        }
        ev = normalize_event(comp_config, comp_status, valid_match, ref_now, date_range_days=30)
        self.assertIsNotNone(ev)
        self.assertEqual(ev["event_id"], "premier-league-2026-09-20-arsenal-fc-chelsea-fc")
        self.assertEqual(ev["time_status"], "confirmed")

        # Fixture far in future (outside 30 days)
        far_match = {
            "round": "Matchday 30",
            "date_str": "2027-04-10",
            "time_str": "15:00",
            "home_team": {"name": "Arsenal FC"},
            "away_team": {"name": "Chelsea FC"}
        }
        ev_far = normalize_event(comp_config, comp_status, far_match, ref_now, date_range_days=30)
        self.assertIsNone(ev_far)

    def test_deduplication_and_sorting(self):
        ref_now = datetime(2026, 9, 16, 12, 0, tzinfo=timezone.utc)
        comp_config = {
            "id": "premier-league",
            "name": "English Premier League",
            "source_timezone": "Europe/London",
            "source_file": "en.1.json"
        }
        comp_status = {"season": "2026-27", "provider": "OpenFootball"}

        matches = [
            {"date_str": "2026-09-25", "time_str": "15:00", "home_team": {"name": "Liverpool FC"}, "away_team": {"name": "Everton FC"}},
            {"date_str": "2026-09-20", "time_str": "15:00", "home_team": {"name": "Arsenal FC"}, "away_team": {"name": "Chelsea FC"}},
            {"date_str": "2026-09-20", "time_str": "15:00", "home_team": {"name": "Arsenal FC"}, "away_team": {"name": "Chelsea FC"}} # duplicate
        ]

        raw_fixtures = {"premier-league": {"config": comp_config, "status": comp_status, "matches": matches}}
        events = normalize_all_fixtures(raw_fixtures, ref_now=ref_now, date_range_days=30)

        self.assertEqual(len(events), 2)
        self.assertEqual(events[0]["event_id"], "premier-league-2026-09-20-arsenal-fc-chelsea-fc")
        self.assertEqual(events[1]["event_id"], "premier-league-2026-09-25-liverpool-fc-everton-fc")


if __name__ == "__main__":
    unittest.main()
