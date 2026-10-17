from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# Each query counts rows that break a rule. Zero means healthy.
CHECKS: dict[str, str] = {
    "score_out_of_range": ("SELECT COUNT(*) FROM score_snapshots WHERE normalized < 0 OR normalized > 100"),
    "aggregate_without_snapshots": (
        "SELECT COUNT(*) FROM media m WHERE m.aggregate_score IS NOT NULL "
        "AND NOT EXISTS (SELECT 1 FROM score_snapshots s WHERE s.media_id = m.id)"
    ),
    "duplicate_titles": (
        "SELECT COUNT(*) FROM (SELECT medium, title, release_year FROM media "
        "GROUP BY medium, title, release_year HAVING COUNT(*) > 1) d"
    ),
    "stale_sources": (
        "SELECT COUNT(*) FROM sources WHERE last_run_at IS NULL OR last_run_at < NOW() - INTERVAL 36 HOUR"
    ),
    "failed_runs_last_24h": (
        "SELECT COUNT(*) FROM ingest_runs WHERE status <> 'ok' AND started_at > NOW() - INTERVAL 24 HOUR"
    ),
}


async def run_checks(session: AsyncSession) -> dict[str, int]:
    return {name: int(await session.scalar(text(sql)) or 0) for name, sql in CHECKS.items()}
