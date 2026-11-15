from typing import Any


ALLOWED_TOOLS = {
    "get_current_map_context",
    "search_scenes",
    "get_scene_metadata",
    "get_radar_profile",
    "get_region_stats",
    "get_pixel_values",
    "explain_layer",
}

ALLOWED_UI_ACTIONS = {
    "set_radar_band",
    "toggle_layer",
    "select_scene",
    "set_timeline_index",
    "open_region_stats",
    "open_pixel_inspector",
}


def validate_tool_name(name: str) -> str:
    if name not in ALLOWED_TOOLS:
        raise ValueError(f"Tool is not allowed in copilot MVP: {name}")
    return name


def validate_action(action: dict[str, Any]) -> dict[str, Any]:
    name = action.get("action")
    if name not in ALLOWED_UI_ACTIONS:
        raise ValueError(f"UI action is not allowed in copilot MVP: {name}")
    arguments = action.get("arguments") or {}
    if not isinstance(arguments, dict):
        raise ValueError("Action arguments must be an object")
    if name == "set_radar_band" and arguments.get("band") not in {"HHHH", "HVHV", "COMPOSITE"}:
        raise ValueError("Invalid radar band")
    return {"action": name, "arguments": arguments}
