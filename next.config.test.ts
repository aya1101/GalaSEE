import { describe, expect, it } from "vitest";
import nextConfig from "./next.config";

describe("Next.js development tunnel configuration", () => {
  it("allows ngrok development origins for client-side assets", () => {
    expect(nextConfig.allowedDevOrigins).toEqual(["*.ngrok-free.dev", "*.ngrok.io"]);
  });
});
