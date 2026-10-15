import enum
from datetime import datetime
from decimal import Decimal
from typing import Any
from app.core.enums import Medium, SourceKind

from sqlalchemy import (JSON, Column, Enum, ForeignKey, Index, Numeric, String, Table,
                        UniqueConstraint, func)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base







media_genres = Table(
    "media_genres",
    Base.metadata,
    Column("media_id", ForeignKey("media.id", ondelete="CASCADE"), primary_key=True),
    Column("genre_id", ForeignKey("genres.id", ondelete="CASCADE"), primary_key=True),
)


class Genre(Base):
    __tablename__ = "genres"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True)


class Media(Base):
    __tablename__ = "media"
    id: Mapped[int] = mapped_column(primary_key=True)
    medium: Mapped[Medium] = mapped_column(Enum(Medium))
    title: Mapped[str] = mapped_column(String(300))
    release_year: Mapped[int | None]

    # One column per external ID so each source can find "its" record
    imdb_id: Mapped[str | None] = mapped_column(String(16), unique=True)
    tmdb_id: Mapped[int | None]
    rawg_id: Mapped[int | None] = mapped_column(unique=True)
    steam_appid: Mapped[int | None] = mapped_column(unique=True)
    opencritic_id: Mapped[int | None] = mapped_column(unique=True)

    critic_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    user_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    aggregate_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    genres: Mapped[list[Genre]] = relationship(secondary=media_genres, lazy="selectin")
    snapshots: Mapped[list["ScoreSnapshot"]] = relationship(
        back_populates="media", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("medium", "tmdb_id"),  # TMDB reuses IDs across movies and TV
        Index("ix_media_filter", "medium", "release_year", "aggregate_score"),
    )


class Source(Base):
    __tablename__ = "sources"
    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(32), unique=True)  # e.g. "rotten_tomatoes"
    name: Mapped[str] = mapped_column(String(64))
    kind: Mapped[SourceKind] = mapped_column(Enum(SourceKind))
    weight: Mapped[Decimal] = mapped_column(Numeric(3, 2), default=Decimal("1.00"))
    last_run_at: Mapped[datetime | None]


class ScoreSnapshot(Base):
    __tablename__ = "score_snapshots"
    id: Mapped[int] = mapped_column(primary_key=True)
    media_id: Mapped[int] = mapped_column(ForeignKey("media.id", ondelete="CASCADE"))
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"))
    raw_value: Mapped[str] = mapped_column(String(32))        # exactly as shown: "7.8/10", "92%"
    normalized: Mapped[Decimal] = mapped_column(Numeric(5, 2))  # 0.00 – 100.00
    sample_size: Mapped[int | None]                            # number of reviews behind it
    raw_payload: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    captured_at: Mapped[datetime] = mapped_column(server_default=func.now())

    media: Mapped[Media] = relationship(back_populates="snapshots")
    source: Mapped[Source] = relationship(lazy="joined")

    __table_args__ = (Index("ix_snap_lookup", "media_id", "source_id", "captured_at"),)


class IngestRun(Base):
    __tablename__ = "ingest_runs"
    id: Mapped[int] = mapped_column(primary_key=True)
    job: Mapped[str] = mapped_column(String(32))  # e.g. "movies", "tv", "games"
    status: Mapped[str] = mapped_column(String(16), default="running")  # running/ok/failed
    items_ok: Mapped[int] = mapped_column(default=0)
    items_failed: Mapped[int] = mapped_column(default=0)
    error: Mapped[str | None] = mapped_column(String(2000))
    started_at: Mapped[datetime] = mapped_column(server_default=func.now())
    finished_at: Mapped[datetime | None]