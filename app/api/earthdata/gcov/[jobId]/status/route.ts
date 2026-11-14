import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function GET(_request: Request, context: { params: Promise<{ jobId: string }> }) {
  const { jobId } = await context.params;
  const apiUrl = process.env.EARTHDATA_API_URL?.replace(/\/$/, "");
  if (!apiUrl) return NextResponse.json({ error: "Earthdata API is not configured" }, { status: 503 });
  try {
    const response = await fetch(`${apiUrl}/api/v1/earthdata/gcov/${encodeURIComponent(jobId)}/status`, { cache: "no-store" });
    return new Response(response.body, { status: response.status, headers: { "Content-Type": "application/json", "Cache-Control": "no-store" } });
  } catch {
    return NextResponse.json({ error: "Unable to reach Earthdata API" }, { status: 502 });
  }
}
