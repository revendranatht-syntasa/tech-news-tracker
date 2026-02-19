"""
Entry point — run the tracker and write results to cache.

Usage:
    python main.py
    python main.py --source OpenAI
"""

import asyncio
import sys
import json
from datetime import datetime, timezone
from pathlib import Path

import nest_asyncio
from dotenv import load_dotenv


from news_pipeline import NewsTracker, TrackerConfig  # noqa: E402


async def main(source_name: str = "OpenAI") -> None:
    nest_asyncio.apply()
    load_dotenv(override=True)

    tracker = NewsTracker()
    state   = await tracker.run(source_name)

    # Print final report to stdout
    if state.get("final_report"):
        print("\n" + state["final_report"])

    # Write cache
    cache_dir  = Path(".cached")
    cache_dir.mkdir(exist_ok=True)
    cache_file = cache_dir / "cache.json"
    data       = {"last_run": datetime.now(timezone.utc).isoformat()}
    with cache_file.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    print(f"\nCache updated: {data['last_run']}")


if __name__ == "__main__":
    import argparse

    config = TrackerConfig()
    parser = argparse.ArgumentParser(description="AI News Tracker")
    parser.add_argument(
        "--source",
        default="OpenAI",
        choices=list(config.sources.keys()),
        help="Which source to run (default: OpenAI)",
    )
    args = parser.parse_args()
    asyncio.get_event_loop().run_until_complete(main())