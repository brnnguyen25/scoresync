import asyncio
from decimal import Decimal

from sqlalchemy import select

from app.db.models import Source, SourceKind
from app.db.session import SessionLocal

SOURCES = [
    ("imdb", "IMDb user rating", SourceKind.user, "1.00"),
    ("rotten_tomatoes", "Rotten Tomatoes Tomatometer", SourceKind.critic, "1.00"),
    ("metacritic", "Metacritic Metascore", SourceKind.critic, "1.00"),
    ("tmdb", "TMDB user score", SourceKind.user, "0.50"),
    ("opencritic", "OpenCritic Top Critic Average", SourceKind.critic, "1.00"),
    ("rawg", "RAWG user rating", SourceKind.user, "0.75"),
    ("steam", "Steam user reviews", SourceKind.user, "1.00"),
]


async def main() -> None:
    async with SessionLocal() as s:
        existing = set((await s.scalars(select(Source.slug))).all())
        for slug, name, kind, weight in SOURCES:
            if slug not in existing:
                s.add(Source(slug=slug, name=name, kind=kind, weight=Decimal(weight)))
        await s.commit()


if __name__ == "__main__":
    asyncio.run(main())
