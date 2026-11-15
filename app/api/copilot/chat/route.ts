import { serverApiUrl } from "@/lib/server-api";

export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  const apiUrl = serverApiUrl();
  if (!apiUrl) return Response.json({ error: "Copilot backend is not configured" }, { status: 503 });
  try {
    const upstream = await fetch(`${apiUrl}/api/v1/copilot/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
      body: await request.text(),
      cache: "no-store",
    });
    return new Response(upstream.body, {
      status: upstream.status,
      headers: { "Content-Type": "text/event-stream", "Cache-Control": "no-cache", Connection: "keep-alive", "X-Accel-Buffering": "no" },
    });
  } catch {
    return Response.json({ error: "Copilot backend unavailable" }, { status: 502 });
  }
}
