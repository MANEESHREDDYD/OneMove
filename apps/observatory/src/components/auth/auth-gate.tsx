"use client";

import { LogOut } from "lucide-react";
import type { ReactNode } from "react";
import { useState } from "react";

import { useAuth } from "./auth-provider";
import { LoginForm } from "./login-form";

export function AuthGate({ children }: { children: ReactNode }) {
  const { configured, loading, role, session, signOut, user, workspaceId } = useAuth();
  const [signOutError, setSignOutError] = useState<string | null>(null);

  if (!configured) {
    return (
      <main id="main-content" className="flex min-h-screen items-center justify-center bg-slate-100 px-4">
        <section className="max-w-xl rounded-xl border border-amber-300 bg-amber-50 p-6 text-amber-950" role="alert">
          <h1 className="text-xl font-semibold">Authentication configuration required</h1>
          <p className="mt-2 text-sm leading-6">
            Set <code>NEXT_PUBLIC_SUPABASE_URL</code> and <code>NEXT_PUBLIC_SUPABASE_ANON_KEY</code> for this environment.
            The Observatory will not create or use a development JWT.
          </p>
        </section>
      </main>
    );
  }

  if (loading) {
    return (
      <main id="main-content" className="flex min-h-screen items-center justify-center bg-slate-100">
        <p aria-live="polite" className="text-sm font-medium text-slate-700">
          Verifying Supabase session...
        </p>
      </main>
    );
  }

  if (!session || !user) return <LoginForm />;

  async function handleSignOut() {
    setSignOutError(null);
    try {
      await signOut();
    } catch (caught: unknown) {
      setSignOutError(caught instanceof Error ? caught.message : "Sign out failed.");
    }
  }

  return (
    <>
      <a
        className="sr-only z-50 rounded bg-white px-4 py-2 text-slate-950 focus:not-sr-only focus:absolute focus:left-4 focus:top-4"
        href="#main-content"
      >
        Skip to main content
      </a>
      <div className="flex min-h-12 flex-wrap items-center justify-between gap-3 border-b border-slate-800 bg-slate-950 px-4 py-2 text-slate-100">
        <div className="min-w-0 text-xs sm:text-sm">
          <span className="font-semibold">{role}</span>
          <span className="mx-2 text-slate-500" aria-hidden="true">/</span>
          <span className="truncate text-slate-300">{workspaceId ? `Workspace ${workspaceId}` : user.email}</span>
        </div>
        <button
          aria-label="Sign out of ZonePilot Observatory"
          className="flex min-h-10 items-center gap-2 rounded-lg border border-slate-700 px-3 text-sm font-medium hover:bg-slate-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-400"
          onClick={handleSignOut}
          type="button"
        >
          <LogOut aria-hidden="true" className="h-4 w-4" />
          Sign out
        </button>
        {signOutError && <p className="w-full text-right text-xs text-red-300" role="alert">{signOutError}</p>}
      </div>
      {children}
    </>
  );
}
