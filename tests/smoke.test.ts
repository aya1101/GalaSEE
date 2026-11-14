import { describe, expect, it } from "vitest";

describe("frontend test harness", () => {
  it("loads the jsdom test environment", () => {
    expect(document).toBeDefined();
  });
});
