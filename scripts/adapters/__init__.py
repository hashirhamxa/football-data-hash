"""
scripts/adapters package
Provides modular data source adapters for fetching football fixtures.
"""
from .base_adapter import BaseFixtureAdapter
from .espn_adapter import ESPNFixtureAdapter
from .openfootball_adapter import OpenFootballFixtureAdapter

__all__ = ["BaseFixtureAdapter", "ESPNFixtureAdapter", "OpenFootballFixtureAdapter"]
