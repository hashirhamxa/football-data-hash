"""
test_today_tomorrow.py
Unit tests for fetch_today_events.py and fetch_tomorrow_events.py.
Tests Pakistan Standard Time (PKT, UTC+05:00) date filtering and timezone boundaries.
"""

import unittest
from datetime import datetime
from zoneinfo import ZoneInfo
from scripts.fetch_today_events import filter_today_events
from scripts.fetch_tomorrow_events import filter_tomorrow_events

PKT_TZ = ZoneInfo("Asia/Karachi")


class TestTodayTomorrowEvents(unittest.TestCase):

    def setUp(self):
        # Fixed reference time: Wednesday, 2026-09-16 19:30:00 PKT (14:30:00 UTC)
        self.ref_now_pkt = datetime(2026, 9, 16, 19, 30, 0, tzinfo=PKT_TZ)

        self.sample_events = [
            # 1. Match earlier today (passed in PKT): 17:00 PKT (12:00 UTC)
            {
                "event_id": "match-earlier-today",
                "competition": {"name": "Test League"},
                "home_team": {"name": "Team A"},
                "away_team": {"name": "Team B"},
                "match_date": "2026-09-16",
                "time_status": "confirmed",
                "start_time_utc": "2026-09-16T12:00:00Z",
                "start_time_pkt": "2026-09-16T17:00:00+05:00",
                "start_timestamp": 1789560000
            },
            # 2. Upcoming match tonight in PKT: 22:00 PKT (17:00 UTC)
            {
                "event_id": "match-tonight-pkt",
                "competition": {"name": "Test League"},
                "home_team": {"name": "Team C"},
                "away_team": {"name": "Team D"},
                "match_date": "2026-09-16",
                "time_status": "confirmed",
                "start_time_utc": "2026-09-16T17:00:00Z",
                "start_time_pkt": "2026-09-16T22:00:00+05:00",
                "start_timestamp": 1789578000
            },
            # 3. Match at 20:00 UTC on 16 Sep (which is 01:00 AM on 17 Sep TOMORROW in PKT!)
            {
                "event_id": "match-late-europe-tomorrow-pkt",
                "competition": {"name": "Test League"},
                "home_team": {"name": "Team E"},
                "away_team": {"name": "Team F"},
                "match_date": "2026-09-16",
                "time_status": "confirmed",
                "start_time_utc": "2026-09-16T20:00:00Z",
                "start_time_pkt": "2026-09-17T01:00:00+05:00",
                "start_timestamp": 1789588800
            },
            # 4. Match tomorrow evening PKT: 23:00 PKT on 17 Sep (18:00 UTC)
            {
                "event_id": "match-tomorrow-evening-pkt",
                "competition": {"name": "Test League"},
                "home_team": {"name": "Team G"},
                "away_team": {"name": "Team H"},
                "match_date": "2026-09-17",
                "time_status": "confirmed",
                "start_time_utc": "2026-09-17T18:00:00Z",
                "start_time_pkt": "2026-09-17T23:00:00+05:00",
                "start_timestamp": 1789668000
            },
            # 5. Match day after tomorrow: 18 Sep PKT
            {
                "event_id": "match-day-after-tomorrow",
                "competition": {"name": "Test League"},
                "home_team": {"name": "Team I"},
                "away_team": {"name": "Team J"},
                "match_date": "2026-09-18",
                "time_status": "confirmed",
                "start_time_utc": "2026-09-18T18:00:00Z",
                "start_time_pkt": "2026-09-18T23:00:00+05:00",
                "start_timestamp": 1789754400
            }
        ]

    def test_filter_today_events_upcoming_only(self):
        today = filter_today_events(self.sample_events, now_pkt=self.ref_now_pkt, include_past_today=False)
        # Should only include match-tonight-pkt (22:00 PKT), excluding earlier today (17:00 PKT)
        event_ids = [e["event_id"] for e in today]
        self.assertIn("match-tonight-pkt", event_ids)
        self.assertNotIn("match-earlier-today", event_ids)
        self.assertNotIn("match-late-europe-tomorrow-pkt", event_ids)
        self.assertEqual(len(today), 1)

    def test_filter_today_events_full_day(self):
        today_all = filter_today_events(self.sample_events, now_pkt=self.ref_now_pkt, include_past_today=True)
        event_ids = [e["event_id"] for e in today_all]
        self.assertIn("match-earlier-today", event_ids)
        self.assertIn("match-tonight-pkt", event_ids)
        self.assertEqual(len(today_all), 2)

    def test_filter_tomorrow_events(self):
        tomorrow = filter_tomorrow_events(self.sample_events, now_pkt=self.ref_now_pkt)
        event_ids = [e["event_id"] for e in tomorrow]
        # Should correctly catch match-late-europe-tomorrow-pkt (01:00 AM PKT on 17 Sep) and match-tomorrow-evening-pkt
        self.assertIn("match-late-europe-tomorrow-pkt", event_ids)
        self.assertIn("match-tomorrow-evening-pkt", event_ids)
        self.assertNotIn("match-tonight-pkt", event_ids)
        self.assertNotIn("match-day-after-tomorrow", event_ids)
        self.assertEqual(len(tomorrow), 2)


if __name__ == "__main__":
    unittest.main()
