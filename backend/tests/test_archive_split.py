"""HARD structural tests for archive.py split (v1.0.5 Seam B)."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATS_PATH = ROOT / "docs" / "v1.0.5" / "boundary_stats.json"
ARCHIVE_PATH = ROOT / "backend" / "api" / "routes" / "archive.py"

EXPECTED_ENDPOINT_TOTAL = 96
EXPECTED_ARCHIVE_ENDPOINTS = 5
ARCHIVE_LINE_CEILING = 250  # compat shell + progress compat surface


def _load_stats() -> dict:
    return json.loads(STATS_PATH.read_text(encoding="utf-8"))


class TestArchiveSplitHardEvidence:
    def test_endpoint_total_unchanged(self):
        stats = _load_stats()
        assert stats["backend"]["endpoint_total"] == EXPECTED_ENDPOINT_TOTAL

    def test_archive_compat_shell_size(self):
        stats = _load_stats()
        archive_fp = stats["backend"]["route_fingerprints"]["archive.py"]
        assert archive_fp["lines"] <= ARCHIVE_LINE_CEILING
        assert (
            stats["backend"]["endpoint_counts_by_file"]["archive.py"]
            == EXPECTED_ARCHIVE_ENDPOINTS
        )

    def test_slug_route_modules_exist(self):
        routes_dir = ROOT / "backend" / "api" / "routes"
        for name in (
            "characters.py",
            "worlds.py",
            "learner_profiles.py",
            "courses.py",
            "settings.py",
            "learning_diary.py",
        ):
            assert (routes_dir / name).is_file()

    def test_archive_aggregates_sub_routers(self):
        source = ARCHIVE_PATH.read_text(encoding="utf-8")
        for slug in ("characters", "worlds", "learner_profiles", "courses", "settings", "learning_diary"):
            assert f"include_router({slug}.router)" in source
