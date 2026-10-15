from pathlib import Path

import pytest

TESTS_DIR = Path(__file__).parent
LAYERS = {"unit", "contract", "integration", "e2e", "smoke"}


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Mark each test by its folder, so `pytest -m unit` works without decorating every test."""
    for item in items:
        layer = item.path.relative_to(TESTS_DIR).parts[0]
        if layer in LAYERS:
            item.add_marker(getattr(pytest.mark, layer))
