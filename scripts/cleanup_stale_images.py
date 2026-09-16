"""
cleanup_stale_images.py
Safe cleanup script to purge unreferenced and obsolete event image PNGs from output/images/.
Ensures output directory does not accumulate stale images across changing fixtures.

Safety Rules:
- Only scans and deletes PNG files directly inside output/images/
- Never deletes fallback badges (output/images/fallbacks/)
- Never deletes theme previews (output/theme_previews/)
- Verifies references across upcoming_events.json, today_events.json, tomorrow_events.json,
  and all competition tournament feeds (output/competitions/*/*.json).
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
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Deletes PNG files in `images_dir` that are not referenced by any current deliverable JSON.
    Never deletes subdirectory files such as fallback badges.
    """
    if not os.path.exists(images_dir):
        logger.warning(f"Images directory '{images_dir}' does not exist.")
        return {"total_scanned": 0, "kept": 0, "deleted_count": 0, "deleted_files": []}

    referenced = get_all_referenced_image_filenames(output_dir=output_dir)
    logger.info(f"Identified {len(referenced)} actively referenced event images in JSON feeds.")

    deleted_files: List[str] = []
    scanned_count = 0
    kept_count = 0

    # Only scan direct files in images_dir (ignore subfolders like fallbacks)
    for entry in os.scandir(images_dir):
        if not entry.is_file():
            continue
        if not entry.name.lower().endswith(".png"):
            continue

        scanned_count += 1
        filename = entry.name

        if filename not in referenced:
            if not dry_run:
                try:
                    os.remove(entry.path)
                    deleted_files.append(filename)
                except Exception as ex:
                    logger.error(f"Failed to remove stale image '{entry.path}': {ex}")
            else:
                deleted_files.append(filename)
        else:
            kept_count += 1

    action_label = "Dry-run: would delete" if dry_run else "Successfully removed"
    logger.info(f"{action_label} {len(deleted_files)} stale/unreferenced images. Kept {kept_count} active images.")

    return {
        "total_scanned": scanned_count,
        "kept": kept_count,
        "deleted_count": len(deleted_files),
        "deleted_files": deleted_files
    }


if __name__ == "__main__":
    cleanup_stale_images()
