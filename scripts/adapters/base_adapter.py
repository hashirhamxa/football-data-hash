"""
base_adapter.py
Abstract base class defining the contract for football fixture adapters.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime


class BaseFixtureAdapter(ABC):
    """
    Abstract Base Class that every fixture data adapter must implement.
    """

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def fetch_fixtures_for_competition(
        self,
        competition: Dict[str, Any],
        start_date: datetime,
        days_ahead: int = 30
    ) -> Dict[str, Any]:
        """
        Fetches fixtures for a single competition within the specified date range.

        Returns:
            Dict containing:
                - "status": Dict summarizing adapter status, success/failure, count
                - "matches": List[Dict] of normalized intermediate match records
        """
        pass
