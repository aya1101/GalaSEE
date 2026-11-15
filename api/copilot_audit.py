from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass
class AuditRecord:
    conversationId: str
    contextVersion: int
    status: str
    toolNames: list[str]
    sourceIds: list[str]
    latencyMs: int
    provider: str


class AuditSink:
    def __init__(self) -> None:
        self.records: list[dict[str, Any]] = []

    def append(self, record: AuditRecord) -> None:
        value = asdict(record)
        value["recordedAt"] = datetime.now(timezone.utc).isoformat()
        self.records.append(value)
