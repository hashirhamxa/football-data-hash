"""
test_midnight_boundary.py
Verifies timezone conversion accuracy and midnight boundary crossing into Pakistan Standard Time (PKT, UTC+05:00).
"""

import unittest
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import sys
import os

sys.path.insert(0, os.path.abspath("scripts"))

from normalize_fixtures import parse_datetime_flexible, normalize_event
from fetch_today_events import filter_today_events
from fetch_tomorrow_events import filter_tomorrow_events


class TestMidnightBoundary(unittest.TestCase):

    def test_utc_1645_stays_same_day_in_pkt(self):
        """16:45 UTC on Sept 16 -> 21:45 (9:45 PM) PKT on Sept 16."""
        (
            match_date_utc,
            match_date_pkt,
            start_time_utc,
            start_time_pkt,
            start_timestamp,
            time_status,
            display_date,
            display_time
        ) = parse_datetime_flexible(iso_utc_str="2026-09-16T16:45:00Z", target_tz_str="Asia/Karachi")

        self.assertEqual(match_date_utc, "2026-09-16")
        self.assertEqual(match_date_pkt, "2026-09-16")
        self.assertEqual(display_date, "2026-09-16")
        self.assertEqual(display_time, "09:45 PM")
        self.assertEqual(start_time_utc, "2026-09-16T16:45:00Z")
        self.assertTrue(start_time_pkt.startswith("2026-09-16T21:45:00+05:00"))
        self.assertEqual(time_status, "confirmed")

    def test_utc_1900_crosses_midnight_to_next_day_in_pkt(self):
        """19:00 UTC on Sept 16 -> 00:00 (12:00 AM) PKT on Sept 17."""
        (
            match_date_utc,
            match_date_pkt,
            start_time_utc,
            start_time_pkt,
            start_timestamp,
            time_status,
            display_date,
            display_time
        ) = parse_datetime_flexible(iso_utc_str="2026-09-16T19:00:00Z", target_tz_str="Asia/Karachi")

        self.assertEqual(match_date_utc, "2026-09-16")
        self.assertEqual(match_date_pkt, "2026-09-17")
        self.assertEqual(display_date, "2026-09-17")
        self.assertEqual(display_time, "12:00 AM")
        self.assertEqual(start_time_utc, "2026-09-16T19:00:00Z")
        self.assertTrue(start_time_pkt.startswith("2026-09-17T00:00:00+05:00"))
        self.assertEqual(time_status, "confirmed")

    def test_today_and_tomorrow_feed_partitioning_across_midnight(self):
        """
        Given reference time 2026-09-16 12:00:00 PKT:
        - Match A at 16:45 UTC (21:45 PKT Sept 16) is TODAY
        - Match B at 19:00 UTC (00:00 PKT Sept 17) is TOMORROW
        """
        ref_now_pkt = datetime(2026, 9, 16, 12, 0, 0, tzinfo=ZoneInfo("Asia/Karachi"))

        match_today = {
            "event_id": "europa-league-2026-09-16-match-a",
            "competition": {"name": "UEFA Europa League"},
            "home_team": {"name": "Ararat-Armenia"},
            "time_status": "confirmed",
            "start_time_utc": "2026-09-16T16:45:00Z",
            "start_time_pkt": "2026-09-16T21:45:00+05:00",
            "match_date_utc": "2026-09-16",
            "match_date_pkt": "2026-09-16",
            "start_timestamp": 1789577100
        }

        match_tomorrow = {
            "event_id": "europa-league-2026-09-16-match-b",
            "competition": {"name": "UEFA Europa League"},
            "home_team": {"name": "Roma"},
            "time_status": "confirmed",
            "start_time_utc": "2026-09-16T19:00:00Z",
            "start_time_pkt": "2026-09-17T00:00:00+05:00",
            "match_date_utc": "2026-09-16",
            "match_date_pkt": "2026-09-17",
            "start_timestamp": 1789585200
        }

        all_events = [match_today, match_tomorrow]

        today_filtered = filter_today_events(all_events, now_pkt=ref_now_pkt)
        tomorrow_filtered = filter_tomorrow_events(all_events, now_pkt=ref_now_pkt)

        self.assertEqual(len(today_filtered), 1)
        self.assertEqual(today_filtered[0]["event_id"], "europa-league-2026-09-16-match-a")

        self.assertEqual(len(tomorrow_filtered), 1)
        self.assertEqual(tomorrow_filtered[0]["event_id"], "europa-league-2026-09-16-match-b")


if __name__ == "__main__":
    unittest.main()
