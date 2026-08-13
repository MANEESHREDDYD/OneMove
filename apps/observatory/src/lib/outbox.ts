import { get, update } from "idb-keyval";

import { getSupabaseBrowserClient } from "./auth/supabase";

export type OutboxStatus = "PENDING_LOCAL" | "SYNCING" | "ACKNOWLEDGED" | "RETRYABLE_ERROR" | "PERMANENT_REJECT";

export interface OutboxEvent {
  client_event_id: string;
  payload: Record<string, unknown>;
  status: OutboxStatus;
  created_at: string;
  retry_count: number;
  last_error?: string;
}

const OUTBOX_KEY = "zonepilot_outbox";

export async function saveToOutbox(payload: Record<string, unknown>): Promise<OutboxEvent> {
  const event: OutboxEvent = {
    client_event_id: crypto.randomUUID(),
    payload,
    status: "PENDING_LOCAL",
    created_at: new Date().toISOString(),
    retry_count: 0
  };

  await update(OUTBOX_KEY, (val: OutboxEvent[] = []) => [...val, event]);
  return event;
}

export async function getPendingEvents(): Promise<OutboxEvent[]> {
  const events: OutboxEvent[] = await get(OUTBOX_KEY) || [];
  return events.filter(e => e.status === "PENDING_LOCAL" || e.status === "RETRYABLE_ERROR");
}

export async function markEventStatus(client_event_id: string, status: OutboxStatus, error?: string) {
  await update(OUTBOX_KEY, (val: OutboxEvent[] = []) => {
    return val.map(event => {
      if (event.client_event_id === client_event_id) {
        return { 
          ...event, 
          status, 
          last_error: error,
          retry_count: status === "RETRYABLE_ERROR" ? event.retry_count + 1 : event.retry_count
        };
      }
      return event;
    });
  });
}

export async function cleanupAcknowledged() {
  await update(OUTBOX_KEY, (val: OutboxEvent[] = []) => {
    return val.filter(e => e.status !== "ACKNOWLEDGED");
  });
}

export async function syncOutbox() {
  if (!navigator.onLine) return;

  const pending = await getPendingEvents();
  const client = getSupabaseBrowserClient();
  if (!client) return;
  const currentSession = await client.auth.getSession();
  if (!currentSession.data.session) return;
  let token = currentSession.data.session.access_token;

  for (const event of pending) {
    if (event.retry_count > 5) continue;

    await markEventStatus(event.client_event_id, "SYNCING");
    
    try {
      const submit = (accessToken: string) => fetch("/api/events", {
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          "Authorization": "Bearer " + accessToken
        },
        body: JSON.stringify({
          client_event_id: event.client_event_id,
          ...event.payload
        })
      });
      let res = await submit(token);
      if (res.status === 401) {
        const refreshed = await client.auth.refreshSession();
        if (refreshed.data.session) {
          token = refreshed.data.session.access_token;
          res = await submit(token);
        }
      }

      if (res.ok) {
        await markEventStatus(event.client_event_id, "ACKNOWLEDGED");
      } else if (res.status >= 400 && res.status < 500) {
        await markEventStatus(event.client_event_id, "PERMANENT_REJECT", await res.text());
      } else {
        await markEventStatus(event.client_event_id, "RETRYABLE_ERROR", await res.text());
      }
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err);
      await markEventStatus(event.client_event_id, "RETRYABLE_ERROR", message);
    }
  }

  await cleanupAcknowledged();
}
