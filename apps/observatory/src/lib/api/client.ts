import type { Session } from "@supabase/supabase-js";

import { getSupabaseBrowserClient } from "../auth/supabase";

interface ErrorEnvelope {
  error?: {
    code?: string;
    message?: string;
    request_id?: string;
  };
}

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly code: string,
    readonly requestId: string | null,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

function workspaceFromSession(session: Session): string | null {
  const value = session.user.app_metadata?.workspace_id;
  return typeof value === "string" && value.trim() ? value : null;
}

async function parseError(response: Response): Promise<ApiError> {
  let envelope: ErrorEnvelope = {};
  try {
    envelope = (await response.json()) as ErrorEnvelope;
  } catch {
    // A non-JSON upstream failure still becomes a stable client error.
  }
  return new ApiError(
    envelope.error?.message ?? `ZonePilot API request failed with status ${response.status}.`,
    response.status,
    envelope.error?.code ?? "API_REQUEST_FAILED",
    envelope.error?.request_id ?? response.headers.get("x-request-id"),
  );
}

async function authenticatedFetch(path: string, session: Session, signal?: AbortSignal): Promise<Response> {
  const headers = new Headers({ Authorization: `Bearer ${session.access_token}` });
  const workspaceId = workspaceFromSession(session);
  if (workspaceId) headers.set("x-workspace-id", workspaceId);
  return fetch(`/api/zonepilot/${path.replace(/^\/+/, "")}`, {
    cache: "no-store",
    headers,
    signal,
  });
}

export async function getApiJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const client = getSupabaseBrowserClient();
  if (!client) throw new ApiError("Supabase authentication is not configured.", 500, "AUTH_NOT_CONFIGURED", null);

  const { data, error } = await client.auth.getSession();
  if (error || !data.session) throw new ApiError("Your session has expired. Sign in again.", 401, "UNAUTHORIZED", null);

  let response = await authenticatedFetch(path, data.session, signal);
  if (response.status === 401) {
    const refreshed = await client.auth.refreshSession();
    if (refreshed.data.session) {
      response = await authenticatedFetch(path, refreshed.data.session, signal);
    }
  }
  if (!response.ok) throw await parseError(response);
  return (await response.json()) as T;
}
