"""
cleanup_stale_images.py
Image auditing module for event image PNGs in output/images/.
Per user instruction, image deletion is disabled so that all historical and active
matchday images remain permanently available (preventing 404 errors on existing URLs).
"""

import glob
import json
import logging
import os
from typing import Dict, Set, Any, List

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")
logger = logging.getLogger("cleanup_stale_images")


def get_all_referenced_image_filenames(output_dir: str = "output") -> Set[str]:
    """
    Collects all PNG filenames actively referenced across all JSON deliverable feeds.
    """
    referenced_filenames: Set[str] = set()

    json_targets: List[str] = [
        os.path.join(output_dir, "upcoming_events.json"),
        os.path.join(output_dir, "today_events.json"),
        os.path.join(output_dir, "tomorrow_events.json"),
    ]
    # Add tournament feeds
    json_targets.extend(glob.glob(os.path.join(output_dir, "competitions", "*", "*.json")))

    for jpath in json_targets:
        if not os.path.exists(jpath):
            continue
        try:
            with open(jpath, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
            events = data.get("events", []) if isinstance(data, dict) else []
            for ev in events:
                if not isinstance(ev, dict):
                    continue
                eid = ev.get("event_id")
                if eid:
                    referenced_filenames.add(f"{eid}.png")
                img_url = ev.get("event_image_url")
                if img_url:
                    base_name = os.path.basename(img_url)
                    if base_name.endswith(".png"):
                        referenced_filenames.add(base_name)
        except Exception as ex:
            logger.warning(f"Could not parse '{jpath}' for image references: {ex}")

    return referenced_filenames


def cleanup_stale_images(
    images_dir: str = "output/images",
    output_dir: str = "output",
    dry_run: bool = True
) -> Dict[str, Any]:
    """
    Audits images in `images_dir`.
    NOTE: Image deletion is intentionally disabled (dry_run=True by default)
    to guarantee all match URLs stay permanently reachable without 404s.
    """
    if not os.path.exists(images_dir):
        logger.warning(f"Images directory '{images_dir}' does not exist.")
        return {"total_scanned": 0, "kept": 0, "deleted_count": 0, "deleted_files": []}

    referenced = get_all_referenced_image_filenames(output_dir=output_dir)
    logger.info(f"Identified {len(referenced)} actively referenced event images in JSON feeds.")

    unreferenced_files: List[str] = []
    scanned_count = 0
    kept_count = 0

    for entry in os.scandir(images_dir):
        if not entry.is_file():
            continue
        if not entry.name.lower().endswith(".png"):
            continue

        scanned_count += 1
        filename = entry.name

        if filename not in referenced:
            unreferenced_files.append(filename)
        else:
            kept_count += 1

    logger.info(f"Permanent Retention Policy Active: Kept all {scanned_count} images ({len(unreferenced_files)} archived/historical, {kept_count} active). Zero files deleted.")

    return {
        "total_scanned": scanned_count,
        "kept": scanned_count,
        "deleted_count": 0,
        "deleted_files": []
    }


if __name__ == "__main__":
    cleanup_stale_images()
