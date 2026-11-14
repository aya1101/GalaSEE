import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function GET(_request: Request, { params }: { params: Promise<{ previewId: string }> }) {
  const { previewId } = await params;
  const apiUrl = process.env.EARTHDATA_API_URL?.replace(/\/$/, "");
  if (!apiUrl) return NextResponse.json({ error: "Earthdata API is not configured" }, { status: 503 });
  try {
    const response = await fetch(`${apiUrl}/api/v1/earthdata/gcov/preview/file/${encodeURIComponent(previewId)}`, { cache: "no-store" });
    return new Response(response.body, { status: response.status, headers: { "Content-Type": response.headers.get("content-type") ?? "image/png", "Cache-Control": response.headers.get("cache-control") ?? "public, max-age=86400" } });
  } catch {
    return NextResponse.json({ error: "Unable to reach Earthdata API" }, { status: 502 });
  }
}
