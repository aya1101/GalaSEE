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
    expect(screen.queryByText("Study area")).not.toBeInTheDocument();
    expect(screen.queryByText("Earthdata live")).not.toBeInTheDocument();
  });

  it("keeps map as the only area-navigation tab", () => {
    render(
      <ExplorerSidebar
        layerState={{}}
        onLayerChange={vi.fn()}
        activeSection="layers"
        onSectionChange={vi.fn()}
        onResizeStart={vi.fn()}
      />,
    );

    expect(screen.getByText("Bản đồ")).toBeInTheDocument();
    expect(screen.queryByText("Khu vực nghiên cứu")).not.toBeInTheDocument();
  });

  it("opens the tide-aware engine as its own analysis tab", () => {
    const onSectionChange = vi.fn();
    render(
      <ExplorerSidebar
        layerState={{}}
        onLayerChange={vi.fn()}
        activeSection="map"
        onSectionChange={onSectionChange}
        onResizeStart={vi.fn()}
      />,
    );

    fireEvent.click(screen.getByText("Theo triều"));
    expect(onSectionChange).toHaveBeenCalledWith("engine");
  });
});
