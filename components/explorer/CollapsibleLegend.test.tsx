import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { CollapsibleLegend } from "./CollapsibleLegend";

describe("CollapsibleLegend", () => {
  it("opens and closes the map legend panel", () => {
    const onToggle = vi.fn();
    const { rerender } = render(
      <CollapsibleLegend open onToggle={onToggle} title="Lớp bản đồ" closeLabel="Ẩn lớp bản đồ" openLabel="Hiện lớp bản đồ">
        <span>Chú giải</span>
      </CollapsibleLegend>,
    );

    expect(screen.getByText("Chú giải")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Ẩn lớp bản đồ" })).toHaveAttribute("aria-expanded", "true");

    fireEvent.click(screen.getByRole("button", { name: "Ẩn lớp bản đồ" }));
    expect(onToggle).toHaveBeenCalledTimes(1);

    rerender(
      <CollapsibleLegend open={false} onToggle={onToggle} title="Lớp bản đồ" closeLabel="Ẩn lớp bản đồ" openLabel="Hiện lớp bản đồ">
        <span>Chú giải</span>
      </CollapsibleLegend>,
    );

    expect(screen.queryByText("Chú giải")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Hiện lớp bản đồ" })).toHaveAttribute("aria-expanded", "false");
  });
});
