"use client";

import { FormEvent, useState } from "react";
import { LockKeyhole } from "lucide-react";

import { useAuth } from "./auth-provider";

export function LoginForm() {
  const { signIn } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await signIn(email, password);
    } catch (caught: unknown) {
      setError(caught instanceof Error ? caught.message : "Authentication failed.");
      setSubmitting(false);
    }
  }

  return (
    <main id="main-content" className="flex min-h-screen items-center justify-center bg-slate-950 px-4 py-10">
      <section className="w-full max-w-md rounded-2xl border border-slate-700 bg-slate-900 p-6 text-slate-100 shadow-2xl sm:p-8">
        <div className="mb-7 flex h-12 w-12 items-center justify-center rounded-xl bg-blue-500/15 text-blue-300">
          <LockKeyhole aria-hidden="true" className="h-6 w-6" />
        </div>
        <p className="text-xs font-semibold uppercase tracking-[0.22em] text-blue-300">ZonePilot</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight">Observatory sign in</h1>
        <p className="mt-3 text-sm leading-6 text-slate-300">
          Use your assigned Supabase account. Access tokens are refreshed and verified for every protected API request.
        </p>

        <form className="mt-8 space-y-5" onSubmit={handleSubmit}>
          <div>
            <label className="mb-2 block text-sm font-medium" htmlFor="email">
              Email
            </label>
            <input
              autoComplete="email"
              className="min-h-11 w-full rounded-lg border border-slate-600 bg-slate-950 px-3 text-base outline-none transition focus-visible:border-blue-400 focus-visible:ring-2 focus-visible:ring-blue-400/40"
              id="email"
              onChange={(event) => setEmail(event.target.value)}
              required
              type="email"
              value={email}
            />
          </div>
          <div>
            <label className="mb-2 block text-sm font-medium" htmlFor="password">
              Password
            </label>
            <input
              autoComplete="current-password"
              className="min-h-11 w-full rounded-lg border border-slate-600 bg-slate-950 px-3 text-base outline-none transition focus-visible:border-blue-400 focus-visible:ring-2 focus-visible:ring-blue-400/40"
              id="password"
              onChange={(event) => setPassword(event.target.value)}
              required
              type="password"
              value={password}
            />
          </div>
          <p aria-live="assertive" className="min-h-5 text-sm text-red-300" role={error ? "alert" : undefined}>
            {error}
          </p>
          <button
            className="min-h-11 w-full rounded-lg bg-blue-500 px-4 font-semibold text-white transition hover:bg-blue-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-300 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900 disabled:cursor-not-allowed disabled:opacity-60"
            disabled={submitting}
            type="submit"
          >
            {submitting ? "Signing in..." : "Sign in"}
          </button>
        </form>
      </section>
    </main>
  );
}
