import { NextRequest, NextResponse } from "next/server";
import { serverApiUrl } from "@/lib/server-api";

type RouteContext = { params: Promise<{ path: string[] }> };

async function forward(request: NextRequest, context: RouteContext) {
  const { path } = await context.params;
  const targetRoot = serverApiUrl() || "http://127.0.0.1:8000";
  const target = `${targetRoot}/api/v1/tideaware/${path.map((part) => encodeURIComponent(part)).join("/")}${request.nextUrl.search}`;
  const headers = new Headers();
  const contentType = request.headers.get("content-type");
  if (contentType) headers.set("content-type", contentType);
  const response = await fetch(target, { method: request.method, headers, body: request.method === "GET" || request.method === "HEAD" ? undefined : await request.arrayBuffer(), cache: "no-store" });
  const responseHeaders = new Headers();
  const responseType = response.headers.get("content-type");
  if (responseType) responseHeaders.set("content-type", responseType);
  return new NextResponse(response.body, { status: response.status, headers: responseHeaders });
}

export async function GET(request: NextRequest, context: RouteContext) { return forward(request, context); }
export async function POST(request: NextRequest, context: RouteContext) { return forward(request, context); }
