import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  const params = new URL(request.url).searchParams;
  const scene = params.get("scene");
  if (!scene) return NextResponse.json({ error: "Missing scene" }, { status: 400 });
  const apiUrl = process.env.EARTHDATA_API_URL?.replace(/\/$/, "");
  if (!apiUrl) return NextResponse.json({ error: "Earthdata API is not configured" }, { status: 503 });
  const query = new URLSearchParams({
    scene,
    collection: params.get("collection") ?? "C3622241360-ASF",
    variable: params.get("variable") ?? "HHHH",
    mode: params.get("mode") ?? "grayscale",
    low: params.get("low") ?? "2",
    high: params.get("high") ?? "98",
  });
  try {
    const response = await fetch(`${apiUrl}/api/v1/earthdata/gcov/preview?${query.toString()}`, { cache: "no-store" });
    return new Response(response.body, { status: response.status, headers: { "Content-Type": response.headers.get("content-type") ?? "application/json", "Cache-Control": "no-store" } });
  } catch {
    return NextResponse.json({ error: "Unable to reach Earthdata API" }, { status: 502 });
  }
}
