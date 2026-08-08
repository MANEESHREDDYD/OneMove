import { NextResponse } from 'next/server';

export async function POST(request: Request) {
  const data = await request.json();
  const authHeader = request.headers.get('Authorization') || '';
  
  try {
    const res = await fetch("http://127.0.0.1:8000/v1/events", {
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
  } catch (err: any) {
    return new NextResponse(err.message, { status: 500 });
  }
}
