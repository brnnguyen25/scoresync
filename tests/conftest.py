import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

TESTS_DIR = Path(__file__).parent
LAYERS = {"unit", "contract", "integration", "e2e", "smoke"}
_containers: list[Any] = []


def _needs_database(config: pytest.Config) -> bool:
    expr = config.option.markexpr or ""
    return not expr or "integration" in expr  # full run, or integration selected


def pytest_configure(config: pytest.Config) -> None:
    if "DATABASE_URL" in os.environ:  # CI service containers, or your own override
        return
    if not _needs_database(config):
        os.environ["DATABASE_URL"] = "mysql+asyncmy://unused:unused@localhost/unused"
        return
    from testcontainers.mysql import MySqlContainer
    from testcontainers.redis import RedisContainer

    mysql = MySqlContainer("mysql:8.4", username="test", password="test", dbname="scoresync_test").start()
    redis = RedisContainer("redis:7-alpine").start()
    _containers.extend([mysql, redis])
    host, port = mysql.get_container_host_ip(), mysql.get_exposed_port(3306)
    os.environ["DATABASE_URL"] = f"mysql+asyncmy://test:test@{host}:{port}/scoresync_test"
    os.environ["REDIS_URL"] = f"redis://{redis.get_container_host_ip()}:{redis.get_exposed_port(6379)}/0"
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], check=True)
    subprocess.run([sys.executable, "-m", "app.db.seed"], check=True)


def pytest_unconfigure(config: pytest.Config) -> None:
    for container in _containers:
        container.stop()


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Mark each test by its folder, so `pytest -m unit` works without decorating every test."""
    for item in items:
        layer = item.path.relative_to(TESTS_DIR).parts[0]
        if layer in LAYERS:
            item.add_marker(getattr(pytest.mark, layer))
