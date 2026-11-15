import tempfile
import unittest
from pathlib import Path

from api.knowledge_base import KnowledgeBase


class KnowledgeBaseTests(unittest.TestCase):
    def test_approved_claim_is_searchable_with_citation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "knowledge").mkdir()
            (root / "knowledge" / "sources.json").write_text(
                '[{"documentId":"asf-gcov-guide","title":"ASF GCOV","authority":"ASF/NASA","canonicalUrl":"https://example.test/gcov","documentVersion":"v1","status":"approved","topics":["GCOV"]}]',
                encoding="utf-8",
            )
            (root / "knowledge" / "claims.json").write_text(
                '[{"claimId":"gcov-hvhv","statement":"HVHV is a cross-polarized covariance term.","sourceDocumentId":"asf-gcov-guide","sourceAnchor":"data-layers/hvhv","allowedAnswerTypes":["explanation"],"reviewStatus":"approved"}]',
                encoding="utf-8",
            )

            results = KnowledgeBase(root / "knowledge").search("HVHV")

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].sourceDocumentId, "asf-gcov-guide")
        self.assertEqual(results[0].canonicalUrl, "https://example.test/gcov")
        self.assertEqual(results[0].sourceAnchor, "data-layers/hvhv")

    def test_unapproved_and_deprecated_sources_are_excluded(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "knowledge"
            root.mkdir()
            (root / "sources.json").write_text(
                '[{"documentId":"bad","title":"Bad","authority":"unknown","canonicalUrl":"https://bad.test","documentVersion":"v1","status":"deprecated","topics":[]}]',
                encoding="utf-8",
            )
            (root / "claims.json").write_text(
                '[{"claimId":"bad-claim","statement":"HVHV secret.","sourceDocumentId":"bad","sourceAnchor":"x","allowedAnswerTypes":["explanation"],"reviewStatus":"approved"}]',
                encoding="utf-8",
            )

            results = KnowledgeBase(root).search("HVHV")

        self.assertEqual(results, [])

    def test_vietnamese_question_words_do_not_block_retrieval(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "knowledge"
            root.mkdir()
            (root / "sources.json").write_text(
                '[{"documentId":"asf-gcov-guide","title":"ASF GCOV","authority":"ASF/NASA","canonicalUrl":"https://example.test/gcov","documentVersion":"v1","status":"approved","topics":["GCOV","HVHV"]}]',
                encoding="utf-8",
            )
            (root / "claims.json").write_text(
                '[{"claimId":"gcov-hvhv","statement":"HVHV là thành phần covariance phân cực chéo.","sourceDocumentId":"asf-gcov-guide","sourceAnchor":"data-layers/hvhv","allowedAnswerTypes":["explanation"],"reviewStatus":"approved"}]',
                encoding="utf-8",
            )

            results = KnowledgeBase(root).search("HVHV là gì?")

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].sourceAnchor, "data-layers/hvhv")

    def test_query_with_only_stop_words_returns_no_claim(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "knowledge"
            root.mkdir()
            (root / "sources.json").write_text("[]", encoding="utf-8")
            (root / "claims.json").write_text("[]", encoding="utf-8")

            results = KnowledgeBase(root).search("là gì?")

        self.assertEqual(results, [])


if __name__ == "__main__":
    unittest.main()
