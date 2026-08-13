import { NextResponse } from "next/server";

const FORWARDED_HEADERS = ["authorization", "x-request-id", "x-workspace-id"] as const;

function upstreamUrl(path: string[], request: Request): URL {
  const base = process.env.ZONEPILOT_API_URL ?? "http://127.0.0.1:8000";
  const encodedPath = path.map((segment) => encodeURIComponent(segment)).join("/");
  const upstream = new URL(`/api/v1/${encodedPath}`, base);
  upstream.search = new URL(request.url).search;
  return upstream;
}

export async function GET(request: Request, { params }: { params: Promise<{ path: string[] }> }) {
  const { path } = await params;
  if (path.some((segment) => segment === "." || segment === "..")) {
    return NextResponse.json(
      { error: { code: "INVALID_PATH", message: "Invalid API path.", request_id: "proxy", details: {} } },
      { status: 400 },
    );
  }

  const headers = new Headers();
  for (const name of FORWARDED_HEADERS) {
    const value = request.headers.get(name);
    if (value) headers.set(name, value);
  }

  try {
    const response = await fetch(upstreamUrl(path, request), {
      cache: "no-store",
      headers,
    });
    const responseHeaders = new Headers({ "content-type": response.headers.get("content-type") ?? "application/json" });
    const requestId = response.headers.get("x-request-id");
    if (requestId) responseHeaders.set("x-request-id", requestId);
    return new NextResponse(response.body, { status: response.status, headers: responseHeaders });
  } catch {
    return NextResponse.json(
      {
        error: {
          code: "API_UNAVAILABLE",
          message: "ZonePilot API is unavailable.",
          request_id: request.headers.get("x-request-id") ?? "proxy",
          retryable: true,
          details: {},
        },
      },
      { status: 502 },
    );
  }
}
