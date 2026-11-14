import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  const target = new URL(request.url).searchParams.get("url");
  if (!target) return NextResponse.json({ error: "Missing KML URL" }, { status: 400 });
  const apiUrl = process.env.EARTHDATA_API_URL?.replace(/\/$/, "");
  if (!apiUrl) return NextResponse.json({ error: "Earthdata API is not configured" }, { status: 503 });
  try {
    const response = await fetch(`${apiUrl}/api/v1/earthdata/kml?url=${encodeURIComponent(target)}`, { cache: "no-store" });
    return new Response(response.body, {
      status: response.status,
      headers: {
        "Content-Type": response.headers.get("content-type") ?? "application/vnd.google-earth.kml+xml",
        "Cache-Control": "public, max-age=86400",
      },
    });
  } catch {
    return NextResponse.json({ error: "Unable to reach Earthdata API" }, { status: 502 });
  }
}
