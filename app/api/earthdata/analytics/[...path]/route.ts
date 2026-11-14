import { NextRequest, NextResponse } from "next/server";
import { apiBaseUrl } from "@/lib/config";

type RouteContext = { params: Promise<{ path: string[] }> };

async function forward(request: NextRequest, context: RouteContext) {
  const { path } = await context.params;
  const targetRoot = apiBaseUrl || "http://127.0.0.1:8000";
  const target = `${targetRoot}/api/v1/${path.map((part) => encodeURIComponent(part)).join("/")}${request.nextUrl.search}`;
  const headers = new Headers();
  const contentType = request.headers.get("content-type");
  if (contentType) headers.set("content-type", contentType);
  const accept = request.headers.get("accept");
  if (accept) headers.set("accept", accept);
  const response = await fetch(target, {
    method: request.method,
    headers,
    body: request.method === "GET" || request.method === "HEAD" ? undefined : await request.arrayBuffer(),
    cache: "no-store",
  });
  const responseHeaders = new Headers();
  const responseType = response.headers.get("content-type");
  if (responseType) responseHeaders.set("content-type", responseType);
  const source = response.headers.get("x-tideaware-data-source");
  if (source) responseHeaders.set("x-tideaware-data-source", source);
  return new NextResponse(response.body, { status: response.status, headers: responseHeaders });
}

export async function GET(request: NextRequest, context: RouteContext) { return forward(request, context); }
export async function POST(request: NextRequest, context: RouteContext) { return forward(request, context); }
