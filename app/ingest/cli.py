import argparse
import asyncio
import logging

from app.core.enums import Medium
from app.db.session import SessionLocal
from app.ingest import jobs


async def main() -> None:
    parser = argparse.ArgumentParser(description="Run one ingestion job")
    parser.add_argument("job", choices=["movies", "tv", "games"])
    parser.add_argument("--pages", type=int, default=1)
    args = parser.parse_args()
    if args.job == "games":
        run = await jobs.ingest_games(SessionLocal, args.pages)
    else:
        medium = Medium.movie if args.job == "movies" else Medium.tv
        run = await jobs.ingest_screen(SessionLocal, medium, args.pages)
    print(f"{run.job}: {run.status} — {run.items_ok} saved, {run.items_failed} failed")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)  # its INFO lines print API keys in URLs
    asyncio.run(main())
