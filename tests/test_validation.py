"""
test_validation.py
Unit tests for validate_output.py and Pydantic data schemas.
"""

import unittest
from scripts.validate_output import EventItemModel, UpcomingEventsRootModel, validate_json_file


class TestValidation(unittest.TestCase):

    def test_valid_event_item_model(self):
        valid_data = {
            "event_id": "premier-league-2026-09-20-arsenal-fc-chelsea-fc",
            "competition": {
                "id": "premier-league",
                "name": "English Premier League",
                "country": "England",
                "round": "Matchday 5"
            },
            "round": "Matchday 5",
            "home_team": {
                "name": "Arsenal FC",
                "slug": "arsenal-fc",
                "logo_url": "https://example.com/arsenal.png",
                "logo_resolution": {
                    "source": "exact",
                    "confidence": 1.0,
                    "matched_name": "Arsenal FC",
                    "is_fallback": False
                }
            },
            "away_team": {
                "name": "Chelsea FC",
                "slug": "chelsea-fc",
                "logo_url": "https://example.com/chelsea.png",
                "logo_resolution": {
                    "source": "exact",
                    "confidence": 1.0,
                    "matched_name": "Chelsea FC",
                    "is_fallback": False
                }
            },
            "event_image_url": "https://example.com/img.png",
            "match_date": "2026-09-20",
            "start_time_utc": "2026-09-20T15:00:00Z",
            "start_time_pkt": "2026-09-20T20:00:00+05:00",
            "start_timestamp": 1789916400,
            "time_status": "confirmed",
            "data_source": {
                "provider": "OpenFootball",
                "season": "2026-27",
                "file": "en.1.json"
            },
            "last_updated": "2026-09-16T12:00:00Z"
        }
        item = EventItemModel.model_validate(valid_data)
        self.assertEqual(item.event_id, "premier-league-2026-09-20-arsenal-fc-chelsea-fc")

    def test_invalid_event_id(self):
        invalid_data = {
            "event_id": "INVALID SLUG WITH SPACES!",
            "competition": {"id": "pl", "name": "PL", "country": "England"},
            "round": "Matchday 1",
            "home_team": {"name": "A", "slug": "a", "logo_url": "", "logo_resolution": {"source": "exact", "confidence": 1.0, "is_fallback": False}},
            "away_team": {"name": "B", "slug": "b", "logo_url": "", "logo_resolution": {"source": "exact", "confidence": 1.0, "is_fallback": False}},
            "event_image_url": "http://img.png",
            "match_date": "2026-09-20",
            "time_status": "tbd",
            "data_source": {"provider": "OpenFootball", "season": "2026-27"},
            "last_updated": "2026-09-16T12:00:00Z"
        }
        with self.assertRaises(ValueError):
            EventItemModel.model_validate(invalid_data)

    def test_output_json_file_validation(self):
        success = validate_json_file("output/upcoming_events.json", check_images=True)
        self.assertTrue(success)


if __name__ == "__main__":
    unittest.main()
