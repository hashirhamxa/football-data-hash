"""
test_competition_feeds.py
Unit tests for generate_competition_feeds.py.
Tests grouping of events by tournament directory and valid creation of today.json, tomorrow.json, and upcoming.json.
"""

import json
import os
import unittest
from datetime import datetime
from zoneinfo import ZoneInfo
from scripts.generate_competition_feeds import generate_all_competition_feeds

PKT_TZ = ZoneInfo("Asia/Karachi")


class TestCompetitionFeeds(unittest.TestCase):

    def test_generate_competition_feeds(self):
        ref_now_pkt = datetime(2026, 9, 16, 19, 30, 0, tzinfo=PKT_TZ)
        test_out_dir = "output/test_images/test_competitions"
        stats = generate_all_competition_feeds(now_pkt=ref_now_pkt, output_base_dir=test_out_dir)

        self.assertIn("la-liga", stats)
        self.assertIn("premier-league", stats)
        self.assertIn("carabao-cup", stats)

        # Verify physical files exist
        for comp_id in ["la-liga", "premier-league", "carabao-cup", "serie-a", "bundesliga", "ligue-1"]:
            for feed_name in ["today.json", "tomorrow.json", "upcoming.json"]:
                fpath = os.path.join(test_out_dir, comp_id, feed_name)
                self.assertTrue(os.path.exists(fpath), f"Missing feed file: {fpath}")

                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.assertEqual(data["competition"]["id"], comp_id)
                    self.assertIn("total_events", data)
                    self.assertIn("events", data)


if __name__ == "__main__":
    unittest.main()
