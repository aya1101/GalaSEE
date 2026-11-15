import unittest

from .tideaware.report import build_report_payload, render_report_html


class TideAwareReportTests(unittest.TestCase):
    def test_report_is_explicitly_unvalidated_and_contains_track_findings(self):
        state = {
            "id": "run-1",
            "status": "ready",
            "validation_status": "NOT VALIDATED",
            "tracks": [{"track": "047", "status": "ready", "candidate_area_ha": 1.25, "warnings": []}],
            "provenance": {"source": "live ASF + UHSLC + cached GeoTIFF"},
        }
        payload = build_report_payload(state)
        self.assertEqual(payload["validationStatus"], "NOT VALIDATED")
        self.assertEqual(payload["tracks"][0]["candidateAreaHa"], 1.25)
        html = render_report_html(payload)
        self.assertIn("Potential findings", html)
        self.assertIn("NOT VALIDATED", html)
        self.assertIn("run-1", html)


if __name__ == "__main__":
    unittest.main()
