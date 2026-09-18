"""Fetch GitHub traffic data and merge with historical records.

This script:
1. Reads existing JSON data from the local data/ directory (downloaded from S3).
2. Fetches fresh traffic data from the GitHub API for awslabs/hcls-agent-skills.
3. Merges new data with historical data, deduplicating by timestamp for views/clones
   and storing date-keyed snapshots for referrers/paths.
4. Writes merged results back to data/*.json for subsequent S3 upload.

Output format for views.json and clones.json matches the GitHub API format:
{
  "count": <total>,
  "uniques": <total_uniques>,
  "views": [{"timestamp": "...", "count": N, "uniques": N}, ...]
}

This ensures the dashboard can render the data directly.
"""

import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

REPO = "awslabs/hcls-agent-skills"
API_BASE = f"https://api.github.com/repos/{REPO}"
DATA_DIR = Path("data")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def get_github_token() -> str:
    """Retrieve the GitHub token from the environment."""
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        logger.error("GITHUB_TOKEN environment variable is not set")
        sys.exit(1)
    return token


def github_get(endpoint: str, token: str) -> Any:
    """Make an authenticated GET request to the GitHub API.

    Args:
        endpoint: API path relative to the repo (e.g., '/traffic/views').
        token: GitHub personal access token with repo scope.

    Returns:
        Parsed JSON response.
    """
    url = f"{API_BASE}{endpoint}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    logger.info("Fetching %s", url)
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    return response.json()


def load_existing_json(filename: str) -> Any:
    """Load an existing JSON file from the data directory.

    Returns an empty dict if the file does not exist or is malformed.
    """
    path = DATA_DIR / filename
    if not path.exists():
        logger.info("No existing %s found; starting fresh", filename)
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Could not parse %s (%s); starting fresh", filename, e)
        return {}


def save_json(filename: str, data: Any) -> None:
    """Write data to a JSON file in the data directory."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = DATA_DIR / filename
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    logger.info("Wrote %s (%d bytes)", path, path.stat().st_size)


# ---------------------------------------------------------------------------
# Merge logic
# ---------------------------------------------------------------------------


def merge_timeseries(
    existing: dict[str, Any],
    fresh_response: dict[str, Any],
    series_key: str,
) -> dict[str, Any]:
    """Merge time-series traffic data (views or clones), deduplicating on timestamp.

    Accepts and outputs data in GitHub API format:
    {"count": N, "uniques": N, "<series_key>": [{timestamp, count, uniques}, ...]}

    New entries for existing timestamps will overwrite old values since GitHub
    may update counts within the rolling 14-day window.

    Args:
        existing: Previously stored data in GitHub API format.
        fresh_response: Fresh response from the GitHub API.
        series_key: 'views' or 'clones'.

    Returns:
        Merged data in GitHub API format, sorted by timestamp.
    """
    # Build a lookup from existing entries keyed by timestamp
    existing_entries = existing.get(series_key, [])
    merged_map: dict[str, dict[str, Any]] = {}

    for entry in existing_entries:
        merged_map[entry["timestamp"]] = {
            "timestamp": entry["timestamp"],
            "count": entry["count"],
            "uniques": entry["uniques"],
        }

    # Merge fresh entries (overwrites same-timestamp entries with newer data)
    fresh_entries = fresh_response.get(series_key, [])
    for entry in fresh_entries:
        merged_map[entry["timestamp"]] = {
            "timestamp": entry["timestamp"],
            "count": entry["count"],
            "uniques": entry["uniques"],
        }

    # Sort by timestamp and compute totals
    sorted_entries = sorted(merged_map.values(), key=lambda e: e["timestamp"])
    total_count = sum(e["count"] for e in sorted_entries)
    # Note: uniques can't be accurately summed across windows (users may repeat),
    # but we sum as a best-effort historical aggregate
    total_uniques = sum(e["uniques"] for e in sorted_entries)

    logger.info(
        "Merged %s: %d existing + %d fresh -> %d total entries (count=%d, uniques=%d)",
        series_key,
        len(existing_entries),
        len(fresh_entries),
        len(sorted_entries),
        total_count,
        total_uniques,
    )

    return {
        "count": total_count,
        "uniques": total_uniques,
        series_key: sorted_entries,
    }


def fetch_stargazers(token: str) -> list[dict[str, str]]:
    """Fetch all stargazers with timestamps (paginated).

    Uses the star+json media type to get starred_at timestamps.
    Returns a list of {starred_at, user} dicts, sorted by date.
    """
    stargazers: list[dict[str, str]] = []
    page = 1
    while True:
        url = f"{API_BASE}/stargazers?per_page=100&page={page}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.star+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        logger.info("Fetching stargazers page %d", page)
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        if not data:
            break
        for entry in data:
            stargazers.append({
                "starred_at": entry["starred_at"],
                "user": entry["user"]["login"],
            })
        if len(data) < 100:
            break
        page += 1

    stargazers.sort(key=lambda e: e["starred_at"])
    logger.info("Fetched %d total stargazers", len(stargazers))
    return stargazers


def merge_snapshots(
    existing: dict[str, Any], fresh_data: list[dict[str, Any]]
) -> dict[str, Any]:
    """Store point-in-time snapshot data (referrers or paths) keyed by date.

    Referrers and paths are top-10 lists that represent a point-in-time snapshot
    of the last 14 days. We store each day's snapshot separately so we can
    observe trends over time.

    Args:
        existing: Previously stored data as {date_str: [snapshot_list]}.
        fresh_data: Today's snapshot from the GitHub API.

    Returns:
        Merged dictionary with today's snapshot added/updated.
    """
    merged = dict(existing)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    merged[today] = fresh_data
    logger.info("Stored snapshot for %s (%d items)", today, len(fresh_data))
    return merged


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    """Orchestrate traffic data collection and merging."""
    token = get_github_token()

    # Record the UTC timestamp of this collection run so the dashboard can show
    # an honest "last updated" time reflecting when the workflow actually ran,
    # rather than inferring it from the latest data bucket. Persisted as a
    # top-level 'collected_at' key inside views.json (and clones.json).
    collected_at = datetime.now(timezone.utc).isoformat()

    # Ensure the data directory exists
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # --- Views ---
    try:
        views_response = github_get("/traffic/views", token)
        existing_views = load_existing_json("views.json")
        merged_views = merge_timeseries(existing_views, views_response, "views")
        # Stamp when this run collected data (see collected_at above).
        merged_views["collected_at"] = collected_at
        save_json("views.json", merged_views)
    except requests.HTTPError as e:
        logger.error("Failed to fetch views: %s", e)
        sys.exit(1)

    # --- Clones ---
    try:
        clones_response = github_get("/traffic/clones", token)
        existing_clones = load_existing_json("clones.json")
        merged_clones = merge_timeseries(existing_clones, clones_response, "clones")
        # Stamp when this run collected data (see collected_at above).
        merged_clones["collected_at"] = collected_at
        save_json("clones.json", merged_clones)
    except requests.HTTPError as e:
        logger.error("Failed to fetch clones: %s", e)
        sys.exit(1)

    # --- Referrers (point-in-time top-10 list) ---
    try:
        referrers_response = github_get("/traffic/popular/referrers", token)
        existing_referrers = load_existing_json("referrers.json")
        merged_referrers = merge_snapshots(existing_referrers, referrers_response)
        save_json("referrers.json", merged_referrers)
    except requests.HTTPError as e:
        logger.error("Failed to fetch referrers: %s", e)
        sys.exit(1)

    # --- Paths (point-in-time top-10 list) ---
    try:
        paths_response = github_get("/traffic/popular/paths", token)
        existing_paths = load_existing_json("paths.json")
        merged_paths = merge_snapshots(existing_paths, paths_response)
        save_json("paths.json", merged_paths)
    except requests.HTTPError as e:
        logger.error("Failed to fetch paths: %s", e)
        sys.exit(1)

    # --- Stargazers (full history with timestamps) ---
    # SKIP_STARGAZERS lets the local refresh (refresh_dashboard.sh) rely on the
    # stargazers.json it just synced from S3 instead of re-fetching stars live
    # and overwriting it. The scheduled GitHub Action does NOT set this var, so
    # it always collects stars.
    if os.environ.get("SKIP_STARGAZERS"):
        logger.info("SKIP_STARGAZERS is set; skipping stargazers fetch/save")
    else:
        try:
            stargazers = fetch_stargazers(token)
            save_json("stargazers.json", stargazers)
        except requests.HTTPError as e:
            logger.error("Failed to fetch stargazers: %s", e)
            sys.exit(1)

    logger.info("Traffic data collection complete")


if __name__ == "__main__":
    main()
