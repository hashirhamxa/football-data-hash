"""
test_adapters.py
Unit tests for modular data source adapters (ESPN and OpenFootball).
"""

import unittest
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from unittest.mock import patch, MagicMock

import sys
import os
sys.path.insert(0, os.path.abspath("scripts"))

from adapters.base_adapter import BaseFixtureAdapter
from adapters.espn_adapter import ESPNFixtureAdapter
from adapters.openfootball_adapter import OpenFootballFixtureAdapter


class TestAdapters(unittest.TestCase):

    def test_espn_event_parser_valid_scheduled(self):
        adapter = ESPNFixtureAdapter()
        mock_event = {
            "id": "700100",
            "name": "Sparta Prague at Ararat-Armenia",
            "date": "2026-09-16T16:45Z",
            "status": {
                "type": {
                    "state": "pre",
                    "completed": False,
                    "description": "Scheduled",
                    "detail": "Wed, Sep 16 at 4:45 PM UTC"
                }
            },
            "competitions": [
                {
                    "notes": [{"headline": "UEFA Europa League Qualifying"}],
                    "venue": {"fullName": "Republican Stadium"},
                    "competitors": [
                        {
                            "homeAway": "home",
                            "team": {
                                "id": "20024",
                                "name": "Ararat-Armenia",
                                "displayName": "Ararat-Armenia",
                                "abbreviation": "ARA",
                                "logo": "https://a.espncdn.com/i/teamlogos/soccer/500/20024.png"
                            }
                        },
                        {
                            "homeAway": "away",
                            "team": {
                                "id": "433",
                                "name": "Sparta Prague",
                                "displayName": "Sparta Prague",
                                "abbreviation": "PRA",
                                "logo": "https://a.espncdn.com/i/teamlogos/soccer/500/433.png"
                            }
                        }
                    ]
                }
            ]
        }

        comp_config = {
            "id": "europa-league",
            "name": "UEFA Europa League",
            "espn_slug": "uefa.europa"
        }

        parsed = adapter.parse_espn_event(mock_event, comp_config)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["espn_id"], "700100")
        self.assertEqual(parsed["source_provider"], "ESPN")
        self.assertEqual(parsed["iso_utc"], "2026-09-16T16:45Z")
        self.assertEqual(parsed["time_status"], "confirmed")
        self.assertEqual(parsed["round"], "UEFA Europa League Qualifying")
        self.assertEqual(parsed["home_team"]["name"], "Ararat-Armenia")
        self.assertEqual(parsed["home_team"]["logo_url"], "https://a.espncdn.com/i/teamlogos/soccer/500/20024.png")
        self.assertEqual(parsed["away_team"]["name"], "Sparta Prague")
        self.assertEqual(parsed["away_team"]["logo_url"], "https://a.espncdn.com/i/teamlogos/soccer/500/433.png")

    def test_espn_event_parser_skips_completed(self):
        adapter = ESPNFixtureAdapter()
        mock_event = {
            "id": "700101",
            "name": "Arsenal vs Chelsea",
            "date": "2026-09-15T19:00Z",
            "status": {
                "type": {
                    "state": "post",
                    "completed": True,
                    "description": "Final"
                }
            },
            "competitions": [{"competitors": []}]
        }
        parsed = adapter.parse_espn_event(mock_event, {"id": "premier-league"})
        self.assertIsNone(parsed)

    def test_openfootball_adapter_candidate_seasons(self):
        adapter = OpenFootballFixtureAdapter()
        seasons = adapter.discover_candidate_seasons()
        self.assertIn("2026-27", seasons)
        self.assertIn("2025-26", seasons)


if __name__ == "__main__":
    unittest.main()
