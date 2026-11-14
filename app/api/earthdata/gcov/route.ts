import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  const params = new URL(request.url).searchParams;
  const scene = params.get("scene");
  const collection = params.get("collection") ?? "C3622241360-ASF";
  const variable = params.get("variable") ?? "HHHH";
  const frequency = params.get("frequency") ?? "auto";
  if (!scene) return NextResponse.json({ error: "Missing scene" }, { status: 400 });
  const apiUrl = process.env.EARTHDATA_API_URL?.replace(/\/$/, "");
  if (!apiUrl) return NextResponse.json({ error: "Earthdata API is not configured" }, { status: 503 });
  try {
    const response = await fetch(`${apiUrl}/api/v1/earthdata/gcov?scene=${encodeURIComponent(scene)}&collection=${encodeURIComponent(collection)}&variable=${encodeURIComponent(variable)}&frequency=${encodeURIComponent(frequency)}`, { cache: "no-store" });
    return new Response(response.body, { status: response.status, headers: { "Content-Type": response.headers.get("content-type") ?? "application/json", "Cache-Control": "no-store" } });
  } catch {
    return NextResponse.json({ error: "Unable to reach Earthdata API" }, { status: 502 });
  }
}
