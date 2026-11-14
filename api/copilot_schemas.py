from typing import Any, Literal

from pydantic import BaseModel, Field


class Citation(BaseModel):
    sourceDocumentId: str
    title: str
    canonicalUrl: str
    documentVersion: str
    sourceAnchor: str


class UiAction(BaseModel):
    action: Literal[
        "set_radar_band",
        "toggle_layer",
        "select_scene",
        "set_timeline_index",
        "open_region_stats",
        "open_pixel_inspector",
    ]
    arguments: dict[str, Any] = Field(default_factory=dict)
    requiresConfirmation: bool = False
    undoable: bool = True


class CopilotAnswer(BaseModel):
    text: str
    status: Literal["KNOWN", "PARTIAL", "UNKNOWN", "BLOCKED", "ERROR"]
    citations: list[Citation] = Field(default_factory=list)
    provenance: list[dict[str, Any]] = Field(default_factory=list)
    actions: list[UiAction] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ToolCall(BaseModel):
    id: str
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
