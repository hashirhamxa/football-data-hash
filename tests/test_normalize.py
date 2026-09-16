"""
test_normalize.py
Unit tests for normalize_fixtures.py.
Tests timezone handling, slugification, date window filtering, and deduplication.
"""

import unittest
from datetime import datetime, timezone
from scripts.normalize_fixtures import slugify, parse_match_datetime, is_completed_match, normalize_event, normalize_all_fixtures


class TestNormalizeFixtures(unittest.TestCase):

    def test_slugify(self):
        self.assertEqual(slugify("Arsenal FC"), "arsenal-fc")
        self.assertEqual(slugify("FC Bayern München"), "fc-bayern-munchen")
        self.assertEqual(slugify("Brighton & Hove Albion FC"), "brighton-hove-albion-fc")
        self.assertEqual(slugify("  Real  Madrid -- CF! "), "real-madrid-cf")

    def test_confirmed_match_datetime_conversion(self):
        # Match in London at 15:00 BST (Europe/London UTC+1 in September)
        utc_iso, pkt_iso, timestamp, status = parse_match_datetime(
            date_str="2026-09-20",
            time_str="15:00",
            source_tz_str="Europe/London",
            target_tz_str="Asia/Karachi"
        )
        self.assertEqual(status, "confirmed")
        self.assertEqual(utc_iso, "2026-09-20T14:00:00Z")
        self.assertEqual(pkt_iso, "2026-09-20T19:00:00+05:00")
        self.assertIsInstance(timestamp, int)

    def test_tbd_match_datetime(self):
        for tbd_val in [None, "", "TBD", "TBA", "null"]:
            utc_iso, pkt_iso, timestamp, status = parse_match_datetime(
                date_str="2026-09-20",
                time_str=tbd_val,
                source_tz_str="Europe/London"
            )
            self.assertEqual(status, "tbd")
            self.assertIsNone(utc_iso)
            self.assertIsNone(pkt_iso)
            self.assertIsNone(timestamp)

    def test_is_completed_match(self):
        completed_match = {
            "team1": "Arsenal FC",
            "team2": "Chelsea FC",
            "score": {"ft": [2, 1]}
        }
        self.assertTrue(is_completed_match(completed_match))

        upcoming_match = {
            "team1": "Arsenal FC",
            "team2": "Chelsea FC"
        }
        self.assertFalse(is_completed_match(upcoming_match))

    def test_normalize_event_window(self):
        ref_now = datetime(2026, 9, 16, 12, 0, tzinfo=timezone.utc)
        comp_config = {
            "id": "premier-league",
            "name": "English Premier League",
            "country": "England",
            "source_timezone": "Europe/London",
            "source_file": "en.1.json"
        }
        comp_status = {"season": "2026-27", "source_url": "https://example.com/en.1.json"}

        # Fixture within 30 days
        valid_match = {
            "round": "Matchday 5",
            "date": "2026-09-20",
            "time": "15:00",
            "team1": "Arsenal FC",
            "team2": "Chelsea FC"
        }
        ev = normalize_event(comp_config, comp_status, valid_match, ref_now, date_range_days=30)
        self.assertIsNotNone(ev)
        self.assertEqual(ev["event_id"], "premier-league-2026-09-20-arsenal-fc-chelsea-fc")
        self.assertEqual(ev["time_status"], "confirmed")

        # Fixture far in future (outside 30 days)
        far_match = {
            "round": "Matchday 30",
            "date": "2027-04-10",
            "time": "15:00",
            "team1": "Arsenal FC",
            "team2": "Chelsea FC"
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
        comp_status = {"season": "2026-27"}
        
        matches = [
            {"date": "2026-09-25", "time": "15:00", "team1": "Liverpool FC", "team2": "Everton FC"},
            {"date": "2026-09-20", "time": "15:00", "team1": "Arsenal FC", "team2": "Chelsea FC"},
            {"date": "2026-09-20", "time": "15:00", "team1": "Arsenal FC", "team2": "Chelsea FC"} # duplicate
        ]
        
        raw_fixtures = {"premier-league": {"config": comp_config, "status": comp_status, "data": {"matches": matches}}}
        events = normalize_all_fixtures(raw_fixtures, ref_now=ref_now, date_range_days=30)
        
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0]["event_id"], "premier-league-2026-09-20-arsenal-fc-chelsea-fc")
        self.assertEqual(events[1]["event_id"], "premier-league-2026-09-25-liverpool-fc-everton-fc")


if __name__ == "__main__":
    unittest.main()
