import { NextResponse } from 'next/server';

export async function POST(request: Request) {
  const authHeader = request.headers.get('Authorization') || '';
  
  try {
    const data: unknown = await request.json();
    if (!data || typeof data !== "object" || Array.isArray(data)) {
      return NextResponse.json(
        { error: { code: "VALIDATION_ERROR", message: "A JSON object is required.", request_id: "proxy", details: {} } },
        { status: 422 },
      );
    }
    const isProbe =
      "assignment_id" in data &&
      typeof data.assignment_id === "string" &&
      "availability_state" in data;
    const backendBase = process.env.ZONEPILOT_API_URL ?? "http://127.0.0.1:8000";
    const backendEndpoint = new URL(isProbe ? "/v1/probes" : "/v1/events", backendBase);

    const res = await fetch(backendEndpoint, {
      method: "POST",
      headers: {
        "Authorization": authHeader,
        "Content-Type": "application/json"
      },
      body: JSON.stringify(data)
    });

    const text = await res.text();
    if (!res.ok) {
      return new NextResponse(text, { status: res.status });
    }
    return new NextResponse(text, { status: 201 });
  } catch {
    return NextResponse.json(
      {
        error: {
          code: "API_UNAVAILABLE",
          message: "ZonePilot API is unavailable.",
          request_id: "proxy",
          retryable: true,
          details: {},
        },
      },
      { status: 502 },
    );
  }
}
