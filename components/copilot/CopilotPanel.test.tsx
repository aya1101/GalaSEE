import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { CopilotPanel } from "./CopilotPanel";

const context = {
  sceneId: "scene-1",
  sceneDate: "2026-10-27T11:23:21Z",
  band: "HVHV" as const,
  aoiId: "aoi-study",
  aoiHash: "sha256:test",
  layerState: { radar: true, basemap: true },
  timelineIndex: 1,
  timelineCount: 2,
  catalogMode: "earthdata" as const,
  assetMode: "cached" as const,
  dataStatus: "ready" as const,
  contextVersion: 1,
};

describe("CopilotPanel", () => {
  it("renders the assistant and accepts a question", () => {
    render(<CopilotPanel open context={context} onClose={vi.fn()} onAction={vi.fn()} />);

    expect(screen.getByText("GalaSEE Assistant")).toBeInTheDocument();
    expect(screen.queryByText("Earthdata")).not.toBeInTheDocument();

    const input = screen.getByPlaceholderText("Hỏi về lớp dữ liệu hoặc scene đang xem…");
    fireEvent.change(input, { target: { value: "HVHV là gì?" } });
    expect(input).toHaveValue("HVHV là gì?");
  });

  it("does not render when closed", () => {
    render(<CopilotPanel open={false} context={context} onClose={vi.fn()} onAction={vi.fn()} />);
    expect(screen.queryByText("GalaSEE Assistant")).not.toBeInTheDocument();
  });

  it("renders streamed tokens, citations, and safe actions", async () => {
    const onAction = vi.fn();
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response([
      'event: status\ndata: {"stage":"reading_map_context"}',
      'event: citation\ndata: {"sourceDocumentId":"asf","title":"ASF guide","canonicalUrl":"https://example.test/asf","documentVersion":"1","sourceAnchor":"band"}',
      'event: token\ndata: {"text":"**HVHV** là phân cực chéo."}',
      'event: action\ndata: {"action":"set_radar_band","arguments":{"band":"HVHV","contextVersion":1}}',
      'event: done\ndata: {"text":"**HVHV** là phân cực chéo.","status":"KNOWN","actions":[]}'
    ].join("\n\n") + "\n\n", { headers: { "Content-Type": "text/event-stream" } })));

    render(<CopilotPanel open context={context} onClose={vi.fn()} onAction={onAction} />);
    fireEvent.change(screen.getByPlaceholderText("Hỏi về lớp dữ liệu hoặc scene đang xem…"), { target: { value: "HVHV là gì?" } });
    fireEvent.click(screen.getByRole("button", { name: "Gửi" }));

    await waitFor(() => expect(screen.getByText("HVHV", { selector: "strong" })).toBeInTheDocument());
    expect(screen.getByText("Nguồn: ASF guide")).toBeInTheDocument();
    expect(screen.queryByText("KNOWN")).not.toBeInTheDocument();
    expect(onAction).toHaveBeenCalledWith(expect.objectContaining({ action: "set_radar_band" }));
    vi.unstubAllGlobals();
  });
});
