// Server-side proxy to the external backend.
// Forwards method, body, and Authorization header to NEXT_PUBLIC_API_BASE_URL.
// This avoids CORS issues and centralizes the single integration point.

import { type NextRequest, NextResponse } from "next/server"

const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL

async function handler(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  const { path } = await ctx.params
  const targetPath = "/" + path.join("/")

  if (!BASE_URL) {
    // No backend configured. Signal "unavailable" so the client can use
    // its temporary demo fallback during preview.
    return NextResponse.json({ error: "BACKEND_UNAVAILABLE", message: "NEXT_PUBLIC_API_BASE_URL is not set." }, { status: 503 })
  }

  const url = new URL(targetPath, BASE_URL)
  // Preserve query string.
  url.search = req.nextUrl.search

  const headers = new Headers()
  headers.set("content-type", "application/json")
  const auth = req.headers.get("authorization")
  if (auth) headers.set("authorization", auth)

  let body: string | undefined
  if (req.method !== "GET" && req.method !== "HEAD") {
    body = await req.text()
  }

  try {
    const upstream = await fetch(url.toString(), {
      method: req.method,
      headers,
      body,
      cache: "no-store",
    })

    const text = await upstream.text()
    const contentType = upstream.headers.get("content-type") ?? "application/json"

    return new NextResponse(text, {
      status: upstream.status,
      headers: { "content-type": contentType },
    })
  } catch {
    // Network failure reaching the backend -> let the client fall back.
    return NextResponse.json(
      { error: "BACKEND_UNAVAILABLE", message: "Could not reach the backend." },
      { status: 503 },
    )
  }
}

export {
  handler as GET,
  handler as POST,
  handler as PATCH,
  handler as PUT,
  handler as DELETE,
}
