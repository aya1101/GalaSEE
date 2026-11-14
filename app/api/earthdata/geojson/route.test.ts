import { afterEach, describe, expect, it, vi } from "vitest";
import { GET } from "./route";

describe("Earthdata GeoJSON proxy truth", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.unstubAllEnvs();
  });

  it("labels an upstream failure as error instead of demo fallback", async () => {
    vi.stubEnv("EARTHDATA_API_URL", "http://localhost:8000");
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));

    const response = await GET();

    expect(response.status).toBe(502);
    expect(response.headers.get("X-TideAware-Data-Source")).toBe("error");
    expect(response.headers.get("X-TideAware-Catalog-Mode")).toBe("error");
  });

  it("keeps an empty successful catalog as Earthdata", async () => {
    vi.stubEnv("EARTHDATA_API_URL", "http://localhost:8000");
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ features: [] }), { status: 200 })));

    const response = await GET();

    expect(response.status).toBe(200);
    expect(response.headers.get("X-TideAware-Data-Source")).toBe("earthdata");
    // A successful ASF catalog response does not prove that the selected
    // scene's GeoTIFF asset is already cached.
    expect(response.headers.get("X-TideAware-Data-Status")).toBe("partial");
  });
});
