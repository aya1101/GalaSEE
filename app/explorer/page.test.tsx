import { describe, expect, it, vi } from "vitest";

const { explorerShell } = vi.hoisted(() => ({
  explorerShell: vi.fn((props: { region: string }) => props),
}));

vi.mock("@/components/explorer/ExplorerShell", () => ({
  ExplorerShell: explorerShell,
}));

import ExplorerPage from "./page";

describe("explorer route", () => {
  it("passes the requested region to the explorer shell", async () => {
    const element = await ExplorerPage({
      searchParams: Promise.resolve({ region: "can-gio" }),
    });

    expect(element.props.region).toBe("can-gio");
  });

  it("uses a valid default region when the query is missing", async () => {
    const element = await ExplorerPage({ searchParams: Promise.resolve({}) });

    expect(element.props.region).toBe("can-gio");
  });
});
