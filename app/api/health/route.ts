import { NextResponse } from "next/server";

export function GET() {
  return NextResponse.json({
    status: "ok",
    service: "tideaware-web",
    timestamp: new Date().toISOString(),
  });
}
