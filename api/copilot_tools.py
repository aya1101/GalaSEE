from dataclasses import dataclass
from time import perf_counter
import inspect
from typing import Any, Awaitable, Callable

from pydantic import BaseModel, Field

from .copilot_models import MapContext
from .copilot_policy import validate_tool_name


class ToolResult(BaseModel):
    status: str
    data: dict[str, Any] = Field(default_factory=dict)
    provenance: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    contextVersion: int
    latencyMs: int


@dataclass(frozen=True)
class ToolContext:
    map_context: MapContext
    session_id: str


ToolHandler = Callable[[dict[str, Any], ToolContext], dict[str, Any] | Awaitable[dict[str, Any]]]


class ToolRegistry:
    def __init__(self, handlers: dict[str, ToolHandler] | None = None) -> None:
        self.handlers = handlers or {}

    def register(self, name: str, handler: ToolHandler) -> None:
        validate_tool_name(name)
        self.handlers[name] = handler

    def call(self, name: str, arguments: dict[str, Any], context: ToolContext) -> ToolResult:
        validate_tool_name(name)
        expected_version = arguments.get("contextVersion")
        if expected_version is not None and expected_version != context.map_context.contextVersion:
            raise ValueError("Stale copilot context")
        started = perf_counter()
        if name == "get_current_map_context":
            data = context.map_context.model_dump(mode="json")
            provenance = [{"source": "TideAware map context", "contextVersion": context.map_context.contextVersion}]
            status = "KNOWN"
        elif name == "get_scene_metadata":
            map_context = context.map_context
            data = {
                "sceneId": map_context.sceneId,
                "sceneDate": map_context.sceneDate,
                "band": map_context.band,
                "catalogMode": map_context.catalogMode.value,
                "assetMode": map_context.assetMode.value,
                "dataStatus": map_context.dataStatus.value,
                "hasScene": bool(map_context.sceneId),
                "hasRasterData": map_context.assetMode.value in {"live", "cached"},
                "timeline": {
                    "index": map_context.timelineIndex,
                    "count": map_context.timelineCount,
                },
            }
            provenance = [{"source": "TideAware live map context", "contextVersion": map_context.contextVersion}]
            status = "KNOWN" if map_context.sceneId else "UNKNOWN"
        elif name == "explain_layer":
            layer = arguments.get("layer")
            labels = {
                "radar": "Ảnh radar NISAR GCOV hiện đang hiển thị",
                "basemap": "Bản đồ nền tham chiếu",
                "aoi": "Ranh giới khu vực nghiên cứu",
                "candidateChange": "Vùng thay đổi ứng viên cần kiểm chứng",
            }
            if layer not in labels:
                return ToolResult(status="UNKNOWN", contextVersion=context.map_context.contextVersion, latencyMs=0, warnings=["Không có định nghĩa lớp được phê duyệt."])
            data = {"layer": layer, "label": labels[layer]}
            provenance = [{"source": "TideAware layer policy", "layer": layer}]
            status = "KNOWN"
        elif name in self.handlers:
            data = self.handlers[name](arguments, context)
            provenance = [{"source": "TideAware live tool", "tool": name}]
            status = "KNOWN" if data else "UNKNOWN"
        else:
            return ToolResult(status="UNKNOWN", contextVersion=context.map_context.contextVersion, latencyMs=0, warnings=[f"Dữ liệu cho tool {name} chưa sẵn sàng."])
        return ToolResult(
            status=status,
            data=data,
            provenance=provenance,
            contextVersion=context.map_context.contextVersion,
            latencyMs=round((perf_counter() - started) * 1000),
        )

    async def acall(self, name: str, arguments: dict[str, Any], context: ToolContext) -> ToolResult:
        """Run a tool without forcing live Earthdata handlers into sync wrappers.

        Map context and policy-only tools remain fast and synchronous through
        ``call``. Live catalog/raster tools may perform network or disk I/O, so
        the copilot stream awaits them here and preserves one common tool path.
        """
        validate_tool_name(name)
        expected_version = arguments.get("contextVersion")
        if expected_version is not None and expected_version != context.map_context.contextVersion:
            raise ValueError("Stale copilot context")
        started = perf_counter()

        if name in self.handlers:
            result = self.handlers[name](arguments, context)
            data = await result if inspect.isawaitable(result) else result
            tool_status = str(data.pop("_status", "KNOWN")) if isinstance(data, dict) else "UNKNOWN"
            tool_warnings = data.pop("_warnings", []) if isinstance(data, dict) else []
            tool_provenance = data.pop("_provenance", None) if isinstance(data, dict) else None
            provenance = tool_provenance if isinstance(tool_provenance, list) else [{"source": "TideAware live tool", "tool": name}]
            return ToolResult(
                status=tool_status if tool_status in {"KNOWN", "PARTIAL", "UNKNOWN"} else "UNKNOWN",
                data=data or {},
                provenance=provenance,
                warnings=[str(item) for item in tool_warnings] if isinstance(tool_warnings, list) else [],
                contextVersion=context.map_context.contextVersion,
                latencyMs=round((perf_counter() - started) * 1000),
            )
        if name in {"get_current_map_context", "get_scene_metadata", "explain_layer"}:
            return self.call(name, arguments, context)
        return ToolResult(
            status="UNKNOWN",
            contextVersion=context.map_context.contextVersion,
            latencyMs=0,
            warnings=[f"Dữ liệu cho tool {name} chưa sẵn sàng."],
        )
