import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ExplorerSidebar } from "./ExplorerSidebar";

describe("ExplorerSidebar", () => {
  it("keeps upstream status details out of the navigation rail", () => {
    render(
      <ExplorerSidebar
        layerState={{}}
        onLayerChange={vi.fn()}
        activeSection="map"
        onSectionChange={vi.fn()}
        onResizeStart={vi.fn()}
      />,
    );

    expect(screen.queryByText("Nguồn dữ liệu lỗi")).not.toBeInTheDocument();
    expect(screen.queryByText("Cần Giờ")).not.toBeInTheDocument();
  });

  it("switches the explorer navigation to English", () => {
    render(
      <ExplorerSidebar
        language="en"
        layerState={{}}
        onLayerChange={vi.fn()}
        activeSection="map"
        onSectionChange={vi.fn()}
        onResizeStart={vi.fn()}
      />,
    );

    expect(screen.getByText("Map")).toBeInTheDocument();
    expect(screen.getByText("Data layers")).toBeInTheDocument();
    expect(screen.getByText("Study area")).toBeInTheDocument();
    expect(screen.queryByText("Earthdata live")).not.toBeInTheDocument();
  });

  it("returns to the scene inspector from the study area tab", () => {
    const onSectionChange = vi.fn();
    const onStudyAreaFocus = vi.fn();
    render(
      <ExplorerSidebar
        layerState={{}}
        onLayerChange={vi.fn()}
        activeSection="layers"
        onSectionChange={onSectionChange}
        onStudyAreaFocus={onStudyAreaFocus}
        onResizeStart={vi.fn()}
      />,
    );

    fireEvent.click(screen.getByText("Khu vực nghiên cứu"));
    expect(onSectionChange).toHaveBeenCalledWith("map");
    expect(onStudyAreaFocus).toHaveBeenCalledOnce();
  });
});
