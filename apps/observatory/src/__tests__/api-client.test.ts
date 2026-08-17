import type { Session, SupabaseClient, User } from "@supabase/supabase-js";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError, getApiJson } from "../lib/api/client";
import { getSupabaseBrowserClient } from "../lib/auth/supabase";
import { dataHealthResponse } from "../test/fixtures";

vi.mock("../lib/auth/supabase", () => ({
  getSupabaseBrowserClient: vi.fn(),
  isSupabaseConfigured: vi.fn(() => true),
}));

function testUser(appMetadata: Record<string, unknown> = {}): User {
  return {
    id: "user-1",
    app_metadata: appMetadata,
    user_metadata: {},
    aud: "authenticated",
    created_at: "2026-01-01T00:00:00Z",
  };
}

function testSession(overrides: Partial<Session> = {}): Session {
  return {
    access_token: "access-token-1",
    refresh_token: "refresh-token-1",
    expires_in: 3600,
    token_type: "bearer",
    user: testUser(),
    ...overrides,
  };
}

interface AuthDouble {
  auth: {
    getSession: () => Promise<{ data: { session: Session | null }; error: Error | null }>;
    refreshSession: () => Promise<{ data: { session: Session | null } }>;
  };
}

/**
 * `getApiJson` touches only `auth.getSession` and `auth.refreshSession`. A full
 * SupabaseClient cannot be constructed in a test, so the double is narrowed
 * here — the cast is confined to this boundary and never reaches app code.
 */
function installClient(double: AuthDouble | null): void {
  vi.mocked(getSupabaseBrowserClient).mockReturnValue(
    double === null ? null : (double as unknown as SupabaseClient),
  );
}

function signedIn(session: Session = testSession()): AuthDouble {
  return {
    auth: {
      getSession: async () => ({ data: { session }, error: null }),
      refreshSession: async () => ({ data: { session } }),
    },
  };
}

function jsonResponse(body: unknown, init: ResponseInit = {}): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "content-type": "application/json" },
    ...init,
  });
}

/** The canonical ZonePilot error envelope. */
function errorEnvelope(code: string, message: string, requestId = "req-abc") {
  return { error: { code, message, request_id: requestId, details: {} } };
}

let fetchMock: ReturnType<typeof vi.fn>;

beforeEach(() => {
  fetchMock = vi.fn();
  vi.stubGlobal("fetch", fetchMock);
  installClient(signedIn());
});

describe("getApiJson success path", () => {
  it("returns the parsed body and calls the proxy route", async () => {
    const payload = dataHealthResponse();
    fetchMock.mockResolvedValue(jsonResponse(payload));

    await expect(getApiJson("data-health")).resolves.toEqual(payload);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/zonepilot/data-health",
      expect.objectContaining({ cache: "no-store" }),
    );
  });

  it("sends the bearer token and the workspace header", async () => {
    installClient(signedIn(testSession({ user: testUser({ workspace_id: "ws-9" }) })));
    fetchMock.mockResolvedValue(jsonResponse({ data: [] }));

    await getApiJson("zones");

    const init = fetchMock.mock.calls[0]?.[1] as RequestInit;
    const headers = new Headers(init.headers);
    expect(headers.get("authorization")).toBe("Bearer access-token-1");
    expect(headers.get("x-workspace-id")).toBe("ws-9");
  });

  it("omits the workspace header when the session carries no workspace", async () => {
    fetchMock.mockResolvedValue(jsonResponse({ data: [] }));

    await getApiJson("zones");

    const init = fetchMock.mock.calls[0]?.[1] as RequestInit;
    expect(new Headers(init.headers).has("x-workspace-id")).toBe(false);
  });
});

describe("canonical error envelope", () => {
  it("surfaces the envelope message, code and request id", async () => {
    fetchMock.mockResolvedValue(
      jsonResponse(errorEnvelope("VALIDATION_ERROR", "zone_id is required."), { status: 422 }),
    );

    const error = await getApiJson("zones").catch((caught: unknown) => caught);

    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({
      message: "zone_id is required.",
      code: "VALIDATION_ERROR",
      status: 422,
      requestId: "req-abc",
    });
  });

  it("produces a usable message when the body is not JSON at all", async () => {
    fetchMock.mockResolvedValue(
      new Response("<html>502 Bad Gateway</html>", {
        status: 502,
        headers: { "content-type": "text/html" },
      }),
    );

    const error = await getApiJson<unknown>("zones").catch((caught: unknown) => caught);

    expect(error).toBeInstanceOf(ApiError);
    // Not empty, and not "undefined" leaking into the UI.
    expect((error as ApiError).message).toBe(
      "ZonePilot API request failed with status 502.",
    );
    expect((error as ApiError).code).toBe("API_REQUEST_FAILED");
  });

  it("falls back to the x-request-id header when the envelope omits it", async () => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ error: { code: "BOOM", message: "Broke." } }), {
        status: 500,
        headers: { "content-type": "application/json", "x-request-id": "hdr-77" },
      }),
    );

    const error = await getApiJson("zones").catch((caught: unknown) => caught);

    expect((error as ApiError).requestId).toBe("hdr-77");
  });
});

describe("DATASET_NOT_READY is distinguishable from a hard failure", () => {
  it("carries the 503 status and the DATASET_NOT_READY code", async () => {
    fetchMock.mockResolvedValue(
      jsonResponse(
        errorEnvelope("DATASET_NOT_READY", "The Gold dataset is still being built."),
        { status: 503 },
      ),
    );

    const error = await getApiJson("datasets").catch((caught: unknown) => caught);

    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).status).toBe(503);
    expect((error as ApiError).code).toBe("DATASET_NOT_READY");
    expect((error as ApiError).message).toContain("still being built");
  });

  it("does not share a code with an unavailable upstream", async () => {
    fetchMock.mockResolvedValue(
      jsonResponse(errorEnvelope("DATASET_NOT_READY", "Not ready."), { status: 503 }),
    );
    const notReady = (await getApiJson("datasets").catch((c: unknown) => c)) as ApiError;

    fetchMock.mockResolvedValue(
      jsonResponse(errorEnvelope("API_UNAVAILABLE", "ZonePilot API is unavailable."), {
        status: 502,
      }),
    );
    const hardFailure = (await getApiJson("datasets").catch((c: unknown) => c)) as ApiError;

    expect(notReady.code).not.toBe(hardFailure.code);
    expect(notReady.status).not.toBe(hardFailure.status);
  });
});

describe("authentication handling", () => {
  it("reports an unconfigured Supabase rather than fetching", async () => {
    installClient(null);

    const error = await getApiJson("zones").catch((caught: unknown) => caught);

    expect((error as ApiError).code).toBe("AUTH_NOT_CONFIGURED");
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("reports an expired session when there is none", async () => {
    installClient({
      auth: {
        getSession: async () => ({ data: { session: null }, error: null }),
        refreshSession: async () => ({ data: { session: null } }),
      },
    });

    const error = await getApiJson("zones").catch((caught: unknown) => caught);

    expect((error as ApiError).code).toBe("UNAUTHORIZED");
    expect((error as ApiError).status).toBe(401);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("refreshes once and retries when the proxy answers 401", async () => {
    const refreshed = testSession({ access_token: "access-token-2" });
    installClient({
      auth: {
        getSession: async () => ({ data: { session: testSession() }, error: null }),
        refreshSession: async () => ({ data: { session: refreshed } }),
      },
    });
    fetchMock
      .mockResolvedValueOnce(new Response(null, { status: 401 }))
      .mockResolvedValueOnce(jsonResponse({ data: [] }));

    await expect(getApiJson("zones")).resolves.toEqual({ data: [] });

    expect(fetchMock).toHaveBeenCalledTimes(2);
    const retry = fetchMock.mock.calls[1]?.[1] as RequestInit;
    expect(new Headers(retry.headers).get("authorization")).toBe("Bearer access-token-2");
  });

  it("surfaces the 401 when the refresh yields no session", async () => {
    installClient({
      auth: {
        getSession: async () => ({ data: { session: testSession() }, error: null }),
        refreshSession: async () => ({ data: { session: null } }),
      },
    });
    fetchMock.mockResolvedValue(
      jsonResponse(errorEnvelope("UNAUTHORIZED", "Token rejected."), { status: 401 }),
    );

    const error = await getApiJson("zones").catch((caught: unknown) => caught);

    expect((error as ApiError).status).toBe(401);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});
