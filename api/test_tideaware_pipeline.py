import unittest

from .tideaware.pipeline import build_track_summary


class TideAwarePipelineTests(unittest.TestCase):
    def test_summary_exposes_original_and_corrected_layers_without_validating_them(self):
        result = {
            "bands": {
                "HHHH": {
                    "original_patches": {"type": "FeatureCollection", "features": [], "candidateAreaHa": 2.5},
                    "corrected_patches": {"type": "FeatureCollection", "features": [], "candidateAreaHa": 1.0},
                    "tide_helps": True,
                }
            },
            "warnings": [],
            "corrected_available": True,
        }
        summary, artifacts = build_track_summary(
            track="047",
            roles=[{"scene_id": "scene-1", "role": "Reference_1"}],
            tide={"status": "AVAILABLE"},
            result=result,
            layer_url_factory=lambda branch, band: f"/layers/{branch}/{band}",
        )
        self.assertEqual(summary["validation_status"], "NOT VALIDATED")
        self.assertEqual(summary["candidate_area_ha"], 2.5)
        self.assertEqual(len(summary["layers"]), 2)
        self.assertEqual(len(artifacts), 2)


if __name__ == "__main__":
    unittest.main()
