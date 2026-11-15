import { NextResponse } from "next/server";
import { serverApiUrl } from "@/lib/server-api";

export const dynamic = "force-dynamic";

export async function GET(_request: Request, context: { params: Promise<{ jobId: string }> }) {
  const { jobId } = await context.params;
  const apiUrl = serverApiUrl();
  if (!apiUrl) return NextResponse.json({ error: "Earthdata API is not configured" }, { status: 503 });
  try {
    const response = await fetch(`${apiUrl}/api/v1/earthdata/gcov/${encodeURIComponent(jobId)}/file`, { cache: "no-store" });
    return new Response(response.body, { status: response.status, headers: { "Content-Type": response.headers.get("content-type") ?? "image/tiff", "Cache-Control": "no-store" } });
  } catch {
    return NextResponse.json({ error: "Unable to reach Earthdata API" }, { status: 502 });
  }
}
