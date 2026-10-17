import json
from pathlib import Path

import allure

from app.ingest.clients import omdb

pytestmark = [allure.feature("Source contracts")]


def test_omdb_to_scores_maps_all_three_sources() -> None:
    data = json.loads((Path(__file__).parent / "fixtures" / "omdb_inception.json").read_text())
    slugs = {s.source for s in omdb.to_scores(data)}
    assert slugs == {"imdb", "rotten_tomatoes", "metacritic"}
