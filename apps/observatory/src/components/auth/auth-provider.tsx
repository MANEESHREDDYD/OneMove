"use client";

import type { Session, User } from "@supabase/supabase-js";
import type { ReactNode } from "react";
import { createContext, useContext, useEffect, useMemo, useState } from "react";

import { getSupabaseBrowserClient, isSupabaseConfigured } from "../../lib/auth/supabase";

interface AuthContextValue {
  configured: boolean;
  loading: boolean;
  session: Session | null;
  user: User | null;
  role: string;
  workspaceId: string | null;
  signIn(email: string, password: string): Promise<void>;
  signOut(): Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

function metadataString(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value : null;
}

function sessionRole(session: Session | null): string {
  const metadata = session?.user.app_metadata;
  return (
    metadataString(metadata?.zonepilot_role) ??
    metadataString(metadata?.role) ??
    metadataString(session?.user.role) ??
    "AUTHENTICATED"
  ).toUpperCase();
}

function sessionWorkspace(session: Session | null): string | null {
  return metadataString(session?.user.app_metadata?.workspace_id);
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const configured = isSupabaseConfigured();
  const client = useMemo(() => getSupabaseBrowserClient(), []);
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(configured);

  useEffect(() => {
    if (!client) return;

    let active = true;
    void client.auth.getSession().then(({ data, error }) => {
      if (!active) return;
      setSession(error ? null : data.session);
      setLoading(false);
    });

    const {
      data: { subscription },
    } = client.auth.onAuthStateChange((_event, nextSession) => {
      if (active) {
        setSession(nextSession);
        setLoading(false);
      }
    });

    return () => {
      active = false;
      subscription.unsubscribe();
    };
  }, [client]);

  const value = useMemo<AuthContextValue>(
    () => ({
      configured,
      loading,
      session,
      user: session?.user ?? null,
      role: sessionRole(session),
      workspaceId: sessionWorkspace(session),
      async signIn(email: string, password: string) {
        if (!client) throw new Error("Supabase authentication is not configured.");
        const { error } = await client.auth.signInWithPassword({ email, password });
        if (error) throw error;
      },
      async signOut() {
        if (!client) return;
        const { error } = await client.auth.signOut();
        if (error) throw error;
      },
    }),
    [client, configured, loading, session],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}
