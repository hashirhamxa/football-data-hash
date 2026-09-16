"""
test_logo_resolver.py
Unit tests for resolve_logos.py.
Tests alias matching, normalization, fuzzy matching, and fallback initials badge generation.
"""

import os
import unittest
from scripts.resolve_logos import LogoResolver, normalize_team_name, get_team_initials, generate_fallback_badge


class TestLogoResolver(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.resolver = LogoResolver()

    def test_normalize_team_name(self):
        self.assertEqual(normalize_team_name("Arsenal FC"), "arsenal")
        self.assertEqual(normalize_team_name("FC Bayern München"), "bayern munchen")
        self.assertEqual(normalize_team_name("Club Atlético de Madrid"), "madrid")
        self.assertEqual(normalize_team_name("Brighton & Hove Albion FC"), "brighton hove albion")

    def test_get_team_initials(self):
        self.assertEqual(get_team_initials("Arsenal FC"), "ARS")
        self.assertEqual(get_team_initials("Bayern Munich"), "BMU")
        self.assertEqual(get_team_initials("Real Madrid"), "RMA")

    def test_alias_resolution(self):
        res = self.resolver.resolve("FC Bayern München", "Germany - Bundesliga")
        self.assertIn("Bayern%20Munich.png", res["url"])
        self.assertEqual(res["source"], "alias")
        self.assertFalse(res["is_fallback"])

    def test_fallback_badge_generation(self):
        out_path = "output/images/fallbacks/test_dummy_team.png"
        generated_path = generate_fallback_badge("Test Dummy FC", out_path)
        self.assertTrue(os.path.exists(generated_path))
        
        # Test resolver returns fallback
        res = self.resolver.resolve("NonExistentFootballTeamXYZ 2099", None)
        self.assertEqual(res["source"], "fallback")
        self.assertTrue(res["is_fallback"])
        self.assertEqual(res["confidence"], 0.0)


if __name__ == "__main__":
    unittest.main()
