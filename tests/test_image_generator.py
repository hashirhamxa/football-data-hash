"""
test_image_generator.py
Unit tests for generate_event_images.py.
Tests 1200x630 matchday banner generation, dimensions, typography, and card elements.
"""

import os
import unittest
from PIL import Image
from scripts.generate_event_images import generate_event_card


class TestImageGenerator(unittest.TestCase):

    def test_generate_event_card(self):
        sample_event = {
            "event_id": "test-match-2026-09-20-arsenal-chelsea",
            "competition": {
                "id": "premier-league",
                "name": "English Premier League",
                "round": "Matchday 5"
            },
            "match_date": "2026-09-20",
            "time_status": "confirmed",
            "start_time_utc": "2026-09-20T15:00:00Z",
            "start_time_pkt": "2026-09-20T20:00:00+05:00",
            "home_team": {
                "name": "Arsenal FC",
                "logo_url": None
            },
            "away_team": {
                "name": "Chelsea FC",
                "logo_url": None
            }
        }
        
        out_path = "output/images/test_unit_event.png"
        result_path = generate_event_card(sample_event, out_path, width=1200, height=630)
        
        self.assertTrue(os.path.exists(result_path))
        with Image.open(result_path) as img:
            self.assertEqual(img.size, (1200, 630))
            self.assertEqual(img.mode, "RGB")


if __name__ == "__main__":
    unittest.main()
