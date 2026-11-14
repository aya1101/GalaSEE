import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ExplorerSidebar } from "./ExplorerSidebar";

describe("ExplorerSidebar data truth", () => {
  it("labels upstream errors without presenting demo values", () => {
    render(
      <ExplorerSidebar
        scene={{ id: "scene-1", title: "Cần Giờ", dataMode: "error", assetMode: "unavailable", dataStatus: "error" }}
        layerState={{}}
        onLayerChange={vi.fn()}
        activeSection="map"
        onSectionChange={vi.fn()}
        onResizeStart={vi.fn()}
      />,
    );

    expect(screen.getByText("Nguồn dữ liệu lỗi")).toBeInTheDocument();
    expect(screen.queryByText("Dữ liệu mô phỏng")).not.toBeInTheDocument();
  });
});
