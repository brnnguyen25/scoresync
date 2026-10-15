import asyncio

from sqlalchemy import select

from app.db.models import Media
from app.db.session import SessionLocal
from app.ingest.pipeline import recompute


async def main() -> None:
    async with SessionLocal() as s:
        for media in (await s.scalars(select(Media))).all():
            await recompute(s, media)
        await s.commit()


if __name__ == "__main__":
    asyncio.run(main())
