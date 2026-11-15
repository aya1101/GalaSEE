import unittest
from api.copilot_models import CatalogResult

from api.main import catalog_result_from_payload


class EarthdataTruthTests(unittest.TestCase):
    def test_empty_success_is_not_upstream_error(self):
        result = catalog_result_from_payload(200, {"features": []})
        self.assertEqual(result.status, "ok")
        self.assertEqual(result.records, [])

    def test_upstream_status_is_explicit_error(self):
        result = catalog_result_from_payload(504, {"error": "timeout"})
        self.assertEqual(result.status, "error")
        self.assertEqual(result.errorCode, "UPSTREAM_HTTP_ERROR")

    def test_non_feature_payload_is_empty_success(self):
        result = catalog_result_from_payload(200, {"items": []})
        self.assertIsInstance(result, CatalogResult)
        self.assertEqual(result.records, [])


if __name__ == "__main__":
    unittest.main()
