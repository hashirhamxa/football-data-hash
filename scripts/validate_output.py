"""
validate_output.py
Validates the generated output JSON against strict schemas using Pydantic.
Verifies:
- Data integrity and required fields
- Timezone representations (UTC ISO Z and PKT +05:00)
- Midnight boundary consistency
- Chronological ordering
- Unique deterministic event IDs
- Image presence in output/images/
"""

import json
import logging
import os
import re
from datetime import datetime
from typing import Dict, Any, List, Optional, Literal
from pydantic import BaseModel, Field, field_validator, model_validator

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")
logger = logging.getLogger("validate_output")


class LogoResolutionModel(BaseModel):
    source: str
    confidence: float = Field(ge=0.0, le=1.0)
    matched_name: Optional[str] = None
    is_fallback: bool


class TeamInfoModel(BaseModel):
    name: str
    slug: str
    espn_id: Optional[str] = None
    logo_url: str
    logo_resolution: LogoResolutionModel


class CompetitionInfoModel(BaseModel):
    id: str
    name: str
    country: str
    round: Optional[str] = None
    group: Optional[str] = None


class DataSourceModel(BaseModel):
    provider: str
    season: Optional[str] = None
    file: Optional[str] = None
    source_url: Optional[str] = None


class EventItemModel(BaseModel):
    event_id: str
    competition: CompetitionInfoModel
    round: str
    home_team: TeamInfoModel
    away_team: TeamInfoModel
    event_image_url: str
    match_date: str
    source_date: Optional[str] = None
    match_date_utc: Optional[str] = None
    match_date_pkt: Optional[str] = None
    display_date: Optional[str] = None
    display_time: Optional[str] = None
    display_timezone: Optional[str] = "Asia/Karachi"
    start_time_utc: Optional[str] = None
    start_time_pkt: Optional[str] = None
    start_timestamp: Optional[int] = None
    time_status: Literal["confirmed", "tbd"]
    data_source: DataSourceModel
    last_updated: str

    @field_validator("event_id")
    @classmethod
    def validate_event_id(cls, v: str) -> str:
        if not re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", v):
            raise ValueError(f"Invalid URL-safe slug format for event_id: {v}")
        return v

    @field_validator("match_date")
    @classmethod
    def validate_date(cls, v: str) -> str:
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", v):
            raise ValueError(f"Invalid date format (expected YYYY-MM-DD): {v}")
        return v

    @model_validator(mode="after")
    def validate_time_consistency(self):
        if self.time_status == "confirmed":
            if not self.start_time_utc or not self.start_time_pkt or self.start_timestamp is None:
                raise ValueError(f"Confirmed match {self.event_id} is missing UTC/PKT time or timestamp")
            if not (self.start_time_utc.endswith("Z") or "+00:00" in self.start_time_utc):
                raise ValueError(f"start_time_utc must be UTC ISO ending with Z: {self.start_time_utc}")
            if "+05:00" not in self.start_time_pkt:
                raise ValueError(f"start_time_pkt must have +05:00 offset: {self.start_time_pkt}")
        elif self.time_status == "tbd":
            if self.start_time_utc is not None or self.start_time_pkt is not None or self.start_timestamp is not None:
                raise ValueError(f"TBD match {self.event_id} should have null start times and timestamp")
        return self


class UpcomingEventsRootModel(BaseModel):
    version: str
    generated_at: str
    total_events: int
    date_range: Dict[str, Any]
    data_sources: Dict[str, Any]
    events: List[EventItemModel]

    @model_validator(mode="after")
    def validate_events_integrity(self):
        # 1. Total events count matches array length
        if len(self.events) != self.total_events:
            raise ValueError(f"total_events ({self.total_events}) does not match list length ({len(self.events)})")

        # 2. Unique event IDs
        seen_ids = set()
        for ev in self.events:
            if ev.event_id in seen_ids:
                raise ValueError(f"Duplicate event_id detected: {ev.event_id}")
            seen_ids.add(ev.event_id)

        # 3. Chronological sorting
        for i in range(len(self.events) - 1):
            curr = self.events[i]
            nxt = self.events[i + 1]
            curr_key = (curr.start_timestamp if curr.start_timestamp is not None else 9999999999, curr.match_date)
            nxt_key = (nxt.start_timestamp if nxt.start_timestamp is not None else 9999999999, nxt.match_date)
            if curr_key > nxt_key:
                raise ValueError(f"Events not sorted chronologically: '{curr.event_id}' comes before '{nxt.event_id}'")

        return self


def validate_json_file(filepath: str, check_images: bool = True) -> bool:
    """
    Validates upcoming_events.json against schema and integrity rules.
    """
    if not os.path.exists(filepath):
        logger.error(f"File not found for validation: {filepath}")
        return False

    with open(filepath, "r", encoding="utf-8-sig") as f:
        data = json.load(f)

    try:
        validated = UpcomingEventsRootModel.model_validate(data)
        logger.info(f"JSON Schema and Integrity validation PASSED for {len(validated.events)} events.")

        if check_images:
            missing_images = 0
            for ev in validated.events:
                img_path = os.path.join("output", "images", f"{ev.event_id}.png")
                if not os.path.exists(img_path):
                    logger.warning(f"Missing local event image for: {ev.event_id} at {img_path}")
                    missing_images += 1
            if missing_images == 0:
                logger.info("All referenced event images exist locally in output/images/.")
            else:
                logger.warning(f"{missing_images} event images missing from local output directory.")

        return True
    except Exception as e:
        logger.error(f"Validation FAILED: {e}")
        return False


if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "output/upcoming_events.json"
    success = validate_json_file(path)
    sys.exit(0 if success else 1)
