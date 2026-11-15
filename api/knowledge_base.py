import json
import re
import unicodedata
from pathlib import Path

from .knowledge_models import ClaimRecord, KnowledgeChunk, SourceRecord


STOP_WORDS = {
    "a", "an", "and", "các", "cho", "có", "của", "để", "được", "gì", "giải", "hay",
    "hiện", "khi", "là", "một", "nào", "này", "như", "ở", "phải", "ra", "sao", "thế",
    "the", "theo", "trong", "tôi", "và", "về", "với", "xem", "ý", "nghĩa",
}


def _tokens(value: str) -> set[str]:
    normalized = unicodedata.normalize("NFKC", value).lower()
    return {token for token in re.findall(r"[^\W_]+", normalized, flags=re.UNICODE) if token not in STOP_WORDS and len(token) > 1}


class KnowledgeBase:
    def __init__(self, root: Path | str | None = None) -> None:
        self.root = Path(root or Path(__file__).resolve().parent.parent / "knowledge")
        self.sources = self._load_sources()
        self.claims = self._load_claims()

    def _load_sources(self) -> dict[str, SourceRecord]:
        path = self.root / "sources.json"
        if not path.exists():
            return {}
        values = json.loads(path.read_text(encoding="utf-8"))
        return {item.documentId: item for item in (SourceRecord.model_validate(value) for value in values) if item.status == "approved"}

    def _load_claims(self) -> list[ClaimRecord]:
        path = self.root / "claims.json"
        if not path.exists():
            return []
        values = json.loads(path.read_text(encoding="utf-8"))
        return [item for item in (ClaimRecord.model_validate(value) for value in values) if item.reviewStatus == "approved" and item.sourceDocumentId in self.sources]

    def search(self, query: str, topics: list[str] | None = None, limit: int = 5) -> list[KnowledgeChunk]:
        terms = _tokens(query)
        if not terms:
            return []
        topic_filter = {topic.lower() for topic in topics or []}
        ranked_chunks: list[tuple[int, int, KnowledgeChunk]] = []
        for claim in self.claims:
            source = self.sources[claim.sourceDocumentId]
            haystack = f"{claim.statement} {claim.claimId} {' '.join(source.topics)}"
            haystack_tokens = _tokens(haystack)
            matched_terms = terms.intersection(haystack_tokens)
            if terms and not matched_terms:
                continue
            if topic_filter and not topic_filter.intersection({topic.lower() for topic in source.topics}):
                continue
            chunk = KnowledgeChunk(
                chunkId=f"{claim.sourceDocumentId}:{claim.claimId}",
                text=claim.statement,
                sourceDocumentId=source.documentId,
                title=source.title,
                authority=source.authority,
                canonicalUrl=source.canonicalUrl,
                documentVersion=source.documentVersion,
                sourceAnchor=claim.sourceAnchor,
                metadata={"claimId": claim.claimId, "allowedAnswerTypes": claim.allowedAnswerTypes},
            )
            # Prefer claims matching more query terms; preserve claim order for ties.
            ranked_chunks.append((len(matched_terms), -len(haystack_tokens), chunk))
        ranked_chunks.sort(key=lambda item: (item[0], item[1]), reverse=True)
        return [item[2] for item in ranked_chunks[:limit]]

    def get_claim(self, claim_id: str) -> ClaimRecord | None:
        return next((claim for claim in self.claims if claim.claimId == claim_id), None)
