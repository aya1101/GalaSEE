import { NextResponse } from "next/server";
import { demoGeoJson } from "@/lib/geojson";

export const dynamic = "force-dynamic";

export async function GET() {
  const apiUrl = process.env.EARTHDATA_API_URL?.replace(/\/$/, "");
  if (!apiUrl) {
    return NextResponse.json(demoGeoJson, {
      headers: {
        "X-TideAware-Data-Source": "demo",
        "X-TideAware-Catalog-Mode": "demo",
        "X-TideAware-Asset-Mode": "unavailable",
        "X-TideAware-Data-Status": "unknown",
      },
    });
  }
  try {
    const response = await fetch(`${apiUrl}/api/v1/earthdata/geojson`, { cache: "no-store" });
    const catalogMode = response.ok ? "earthdata" : "error";
    return new Response(response.body, {
      status: response.status,
      headers: {
        "Content-Type": response.headers.get("content-type") ?? "application/geo+json",
        "Cache-Control": "no-store",
        "X-TideAware-Data-Source": catalogMode,
        "X-TideAware-Catalog-Mode": catalogMode,
        // Catalog success does not mean that a GeoTIFF asset is available.
        // The selected scene must be probed separately and/or found in the
        // local cache before the asset is marked ready.
        "X-TideAware-Asset-Mode": "unavailable",
        "X-TideAware-Data-Status": response.ok ? "partial" : "error",
      },
    });
  } catch {
    return NextResponse.json({ error: "Earthdata proxy unavailable" }, {
      status: 502,
      headers: {
        "X-TideAware-Data-Source": "error",
        "X-TideAware-Catalog-Mode": "error",
        "X-TideAware-Asset-Mode": "unavailable",
        "X-TideAware-Data-Status": "error",
      },
    });
  }
}
