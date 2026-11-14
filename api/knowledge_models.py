from typing import Any

from pydantic import BaseModel, Field


class SourceRecord(BaseModel):
    documentId: str
    title: str
    authority: str
    canonicalUrl: str
    documentVersion: str
    status: str
    topics: list[str] = Field(default_factory=list)
    retrievedAt: str | None = None
    contentHash: str | None = None
    snapshotPath: str | None = None


class ClaimRecord(BaseModel):
    claimId: str
    statement: str
    sourceDocumentId: str
    sourceAnchor: str
    allowedAnswerTypes: list[str] = Field(default_factory=list)
    reviewStatus: str


class KnowledgeChunk(BaseModel):
    chunkId: str
    text: str
    sourceDocumentId: str
    title: str
    authority: str
    canonicalUrl: str
    documentVersion: str
    sourceAnchor: str
    metadata: dict[str, Any] = Field(default_factory=dict)
