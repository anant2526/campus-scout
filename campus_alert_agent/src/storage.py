"""
Persistent storage for duplicate detection.

DESIGN: Uses a flat JSON file (seen_results.json) instead of SQLite.
Why? Because GitHub Actions runners are ephemeral — SQLite databases
can't be committed and diffed in git. A JSON file:
  1. Can be committed to the repo and persisted across runs.
  2. Is human-readable (easy to audit what was already seen).
  3. Diffs cleanly in git history.

The file structure:
{
    "https://url.com": {
        "content_hash": "sha256...",
        "first_seen": "2026-04-13T09:00:00Z",
        "last_checked": "2026-04-13T17:00:00Z"
    },
    ...
}

SAFETY: Writes use atomic rename (write to temp → rename) so a crash
mid-write never corrupts the existing file.
"""
import json
import os
import tempfile
import logging
from datetime import datetime, timezone

import config


def load_seen_results() -> dict:
    """
    Load previously seen results from disk.
    Returns empty dict if the file doesn't exist or is corrupted.
    """
    filepath = config.SEEN_RESULTS_FILE
    if not os.path.exists(filepath):
        logging.info("No existing seen_results.json found — starting fresh.")
        return {}

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        logging.info(f"Loaded {len(data)} previously seen results.")
        return data
    except (json.JSONDecodeError, ValueError) as e:
        # Corrupted JSON — log it, back up the broken file, start fresh.
        logging.warning(f"Corrupted seen_results.json: {e}. Backing up and starting fresh.")
        backup = filepath + ".corrupt_backup"
        try:
            os.rename(filepath, backup)
        except OSError:
            pass
        return {}


def save_seen_results(seen: dict) -> None:
    """
    Atomically save seen results to disk.
    Uses write-to-temp-then-rename pattern to prevent corruption.
    """
    filepath = config.SEEN_RESULTS_FILE

    try:
        # Write to a temporary file in the same directory
        dir_name = os.path.dirname(filepath) or "."
        fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(seen, f, indent=2, sort_keys=True)

        # Atomic rename (on POSIX; best-effort on Windows/CI)
        os.replace(tmp_path, filepath)
        logging.info(f"Saved {len(seen)} seen results to {filepath}.")
    except Exception as e:
        logging.error(f"Failed to save seen_results.json: {e}")
        # Clean up temp file if it exists
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def is_new_result(seen: dict, url: str, content_hash: str) -> bool:
    """
    Check if this URL + content_hash combination has been seen before.
    Returns True if the result is NEW (not seen before).
    """
    entry = seen.get(url)
    if entry is None:
        return True
    return entry.get("content_hash") != content_hash


def mark_as_seen(seen: dict, url: str, content_hash: str) -> dict:
    """
    Mark a URL + content_hash as seen. Updates the dict in-place and returns it.
    Preserves first_seen timestamp if URL was seen before with different content.
    """
    now = datetime.now(timezone.utc).isoformat()
    existing = seen.get(url, {})

    seen[url] = {
        "content_hash": content_hash,
        "first_seen": existing.get("first_seen", now),
        "last_checked": now,
    }
    return seen
