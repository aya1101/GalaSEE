import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from api.tideaware.live_tide import TideObservation, TideSeries, evaluate_tide_coverage, fetch_uhslc_hourly, interpolate_tide, tide_window


class LiveTideTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.source = Path(self.directory.name) / "tide.csv"
        self.source.write_text(
            "year,month,day,hour,sea_level_mm\n"
            "2026,01,01,00,1000\n"
            "2026,01,01,01,2000\n"
            "2026,01,01,02,-32768\n"
            "2026,01,01,03,3000\n",
            encoding="utf-8",
        )

    def tearDown(self):
        self.directory.cleanup()

    def test_reads_millimetres_as_metres_and_drops_sentinel_rows(self):
        series = fetch_uhslc_hourly(str(self.source))
        self.assertEqual(len(series.observations), 3)
        self.assertAlmostEqual(series.observations[0].level_m, 1.0)
        self.assertEqual(series.start.year, 2026)

    def test_interpolates_inside_coverage_and_marks_outside_missing(self):
        series = fetch_uhslc_hourly(str(self.source))
        inside = interpolate_tide(series, datetime(2026, 1, 1, 0, 30, tzinfo=timezone.utc))
        self.assertTrue(inside.covered)
        self.assertAlmostEqual(inside.level_m, 1.5)
        outside = interpolate_tide(series, datetime(2025, 12, 31, 23, tzinfo=timezone.utc))
        self.assertFalse(outside.covered)
        self.assertIsNone(outside.level_m)

    def test_coverage_is_partial_when_one_scene_is_not_covered(self):
        series = fetch_uhslc_hourly(str(self.source))
        samples = [
            interpolate_tide(series, datetime(2026, 1, 1, 0, tzinfo=timezone.utc)),
            interpolate_tide(series, datetime(2027, 1, 1, 0, tzinfo=timezone.utc)),
        ]
        coverage = evaluate_tide_coverage(samples, scene_ids=["scene-a", "scene-b"])
        self.assertEqual(coverage.status, "PARTIAL")
        self.assertEqual(coverage.missing_scene_ids, ["scene-b"])

    def test_tide_window_is_centered_on_scene_time(self):
        series = TideSeries(
            observations=[TideObservation(datetime(2026, 1, 1, hour, tzinfo=timezone.utc), float(hour)) for hour in range(10)],
            source="fixture",
        )
        window = tide_window(series, datetime(2026, 1, 1, 5, tzinfo=timezone.utc), hours=2)
        self.assertEqual(window[0].timestamp.hour, 3)
        self.assertEqual(window[-1].timestamp.hour, 7)


if __name__ == "__main__":
    unittest.main()
