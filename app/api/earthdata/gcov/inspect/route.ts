import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  const params = new URL(request.url).searchParams;
  const scene = params.get("scene") ?? "";
  const collection = params.get("collection") ?? "C3622241360-ASF";
  const refresh = params.get("refresh") === "true";
  const apiUrl = process.env.EARTHDATA_API_URL?.replace(/\/$/, "");
  if (!apiUrl) return NextResponse.json({ error: "Earthdata API is not configured" }, { status: 503 });
  try {
    const target = `${apiUrl}/api/v1/earthdata/gcov/inspect?scene=${encodeURIComponent(scene)}&collection=${encodeURIComponent(collection)}&refresh=${refresh}`;
    const response = await fetch(target, { cache: "no-store" });
    return new Response(response.body, { status: response.status, headers: { "Content-Type": response.headers.get("content-type") ?? "application/json", "Cache-Control": "no-store" } });
  } catch {
    return NextResponse.json({ error: "Unable to reach Earthdata API" }, { status: 502 });
  }
}
