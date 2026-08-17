"use client";

import { useCallback, useEffect, useState } from "react";
import {
  ArrowLeft,
  CheckCircle2,
  CircleAlert,
  Database,
  Network,
  RefreshCw,
  ServerCog,
  ShieldCheck,
  TriangleAlert,
} from "lucide-react";
import Link from "next/link";

import { ApiError, getApiJson } from "../../lib/api/client";
import type {
  DataHealthResponse,
  ProviderHealth,
  ReleaseIdentity,
  ReleaseIdentityResponse,
} from "../../lib/api/types";

type ResourceState<T> =
  | { state: "AVAILABLE"; data: T }
  | { state: "UNAVAILABLE"; message: string };

interface HealthSnapshot {
  release: ResourceState<ReleaseIdentity>;
  providers: ResourceState<DataHealthResponse>;
}

function unavailableMessage(reason: unknown): string {
  if (reason instanceof ApiError) {
    return `${reason.message}${reason.requestId ? ` Request ${reason.requestId}.` : ""}`;
  }
  return reason instanceof Error ? reason.message : "The service did not return a verified response.";
}

function resourceState<T>(result: PromiseSettledResult<T>): ResourceState<T> {
  return result.status === "fulfilled"
    ? { state: "AVAILABLE", data: result.value }
    : { state: "UNAVAILABLE", message: unavailableMessage(result.reason) };
}

function providerStateClass(state: ProviderHealth["state"]): string {
  if (state === "FRESH") return "border-emerald-300 bg-emerald-50 text-emerald-900";
  if (state === "DEGRADED") return "border-amber-300 bg-amber-50 text-amber-950";
  if (state === "STALE") return "border-orange-300 bg-orange-50 text-orange-950";
  return "border-slate-300 bg-slate-100 text-slate-900";
}

function formatTimestamp(value: string | null): string {
  if (!value) return "No successful collection";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

export default function SystemHealthPage() {
  const [snapshot, setSnapshot] = useState<HealthSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [reloadKey, setReloadKey] = useState(0);

  const load = useCallback(async (signal: AbortSignal) => {
    setLoading(true);
    const [releaseResult, providersResult] = await Promise.allSettled([
      getApiJson<ReleaseIdentityResponse>("version", signal),
      getApiJson<DataHealthResponse>("data-health", signal),
    ]);
    if (signal.aborted) return;
    const releaseResponse = resourceState(releaseResult);
    setSnapshot({
      release: releaseResponse.state === "AVAILABLE"
        ? { state: "AVAILABLE", data: releaseResponse.data.data }
        : releaseResponse,
      providers: resourceState(providersResult),
    });
    setLoading(false);
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    const task = window.setTimeout(() => void load(controller.signal), 0);
    return () => {
      window.clearTimeout(task);
      controller.abort();
    };
  }, [load, reloadKey]);

  const nonFreshProviders = snapshot?.providers.state === "AVAILABLE"
    ? snapshot.providers.data.data.filter((provider) => provider.state !== "FRESH").length
    : null;
  const releaseVerified = snapshot?.release.state === "AVAILABLE";
  const providersVerified = snapshot?.providers.state === "AVAILABLE"
    && snapshot.providers.data.data.length > 0
    && nonFreshProviders === 0;
  const overallState = !releaseVerified ? "UNAVAILABLE" : providersVerified ? "VERIFIED" : "ATTENTION";

  return (
    <main id="main-content" className="min-h-screen bg-slate-100 px-4 py-6 text-slate-950 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-6xl">
        <header className="border-b border-slate-300 pb-6">
          <Link
            className="inline-flex min-h-11 items-center gap-2 rounded-lg px-2 text-sm font-semibold text-blue-800 hover:bg-blue-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600"
            href="/"
          >
            <ArrowLeft aria-hidden="true" className="h-4 w-4" /> Observatory
          </Link>
          <div className="mt-3 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.22em] text-blue-700">Release evidence</p>
              <h1 className="mt-2 text-3xl font-semibold tracking-tight sm:text-4xl">System health</h1>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
                Authenticated application, Gold dataset, graph, and provider identities. Unverified values are never substituted.
              </p>
            </div>
            <button
              className="flex min-h-11 cursor-pointer items-center justify-center gap-2 rounded-lg border border-slate-400 bg-white px-4 text-sm font-semibold hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 disabled:cursor-wait disabled:opacity-50"
              disabled={loading}
              onClick={() => setReloadKey((key) => key + 1)}
              type="button"
            >
              <RefreshCw aria-hidden="true" className={`h-4 w-4 ${loading ? "animate-spin motion-reduce:animate-none" : ""}`} />
              {loading ? "Checking" : "Check again"}
            </button>
          </div>
        </header>

        <section aria-live="polite" className="mt-8">
          {loading && !snapshot ? <HealthSkeleton /> : (
            <div className={`rounded-xl border p-5 ${overallState === "VERIFIED" ? "border-emerald-300 bg-emerald-50" : overallState === "ATTENTION" ? "border-amber-300 bg-amber-50" : "border-red-300 bg-red-50"}`}>
              <div className="flex items-start gap-3">
                {overallState === "VERIFIED"
                  ? <ShieldCheck aria-hidden="true" className="mt-0.5 h-6 w-6 shrink-0 text-emerald-800" />
                  : <TriangleAlert aria-hidden="true" className={`mt-0.5 h-6 w-6 shrink-0 ${overallState === "ATTENTION" ? "text-amber-900" : "text-red-800"}`} />}
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wider">{overallState}</p>
                  <h2 className="mt-1 text-lg font-semibold">
                    {overallState === "VERIFIED" && "Release identity and provider health are verified"}
                    {overallState === "ATTENTION" && "Release verified; provider health needs attention"}
                    {overallState === "UNAVAILABLE" && "Release identity is unavailable"}
                  </h2>
                  <p className="mt-1 text-sm leading-6">
                    {overallState === "VERIFIED" && "All reported providers are fresh at the evaluation time below."}
                    {overallState === "ATTENTION" && "The release is verified, but provider evidence is unavailable, empty, degraded, stale, or unavailable."}
                    {overallState === "UNAVAILABLE" && "The service could not prove one complete application, Gold, and graph identity."}
                  </p>
                </div>
              </div>
            </div>
          )}
        </section>

        {!loading || snapshot ? (
          <>
            <section className="mt-8" aria-labelledby="release-title">
              <div className="flex items-center gap-3">
                <ServerCog aria-hidden="true" className="h-5 w-5 text-blue-700" />
                <h2 className="text-xl font-semibold" id="release-title">Verified release identity</h2>
              </div>
              {snapshot?.release.state === "AVAILABLE" ? (
                <div className="mt-4 grid gap-4 lg:grid-cols-3">
                  <IdentityCard icon={CheckCircle2} title="Application">
                    <IdentityRow label="Version" value={snapshot.release.data.app_version} />
                    <IdentityRow label="Schema" value={snapshot.release.data.schema_version} />
                    <IdentityRow label="Exact Git SHA" mono value={snapshot.release.data.git_sha} />
                  </IdentityCard>
                  <IdentityCard icon={Database} title="Gold dataset">
                    <IdentityRow label="Dataset" value={snapshot.release.data.gold.dataset_id} />
                    <IdentityRow label="Version" value={snapshot.release.data.gold.dataset_version} />
                    <IdentityRow label="Schema" value={snapshot.release.data.gold.schema_version} />
                    <IdentityRow label="Records" value={snapshot.release.data.gold.record_count.toLocaleString()} />
                    <IdentityRow label="Artifact SHA-256" mono value={snapshot.release.data.gold.artifact_sha256} />
                  </IdentityCard>
                  <IdentityCard icon={Network} title="Routing graph">
                    <IdentityRow label="Version" value={snapshot.release.data.graph.graph_version} />
                    <IdentityRow label="Topology SHA-256" mono value={snapshot.release.data.graph.topology_sha256} />
                    <IdentityRow label="Bundle SHA-256" mono value={snapshot.release.data.graph.bundle_sha256} />
                  </IdentityCard>
                </div>
              ) : (
                <UnavailableCard
                  message={snapshot?.release.state === "UNAVAILABLE" ? snapshot.release.message : "Release identity has not been verified."}
                  title="RELEASE IDENTITY UNAVAILABLE"
                />
              )}
            </section>

            <section className="mt-10" aria-labelledby="providers-title">
              <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
                <div>
                  <h2 className="text-xl font-semibold" id="providers-title">Provider data health</h2>
                  <p className="mt-1 text-sm text-slate-600">Reported from collection manifests and configured freshness thresholds.</p>
                </div>
                {snapshot?.providers.state === "AVAILABLE" && (
                  <p className="text-xs text-slate-500">Evaluated {formatTimestamp(snapshot.providers.data.evaluated_at)}</p>
                )}
              </div>
              {snapshot?.providers.state === "AVAILABLE" ? (
                snapshot.providers.data.data.length > 0 ? (
                  <div className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                    {snapshot.providers.data.data.map((provider) => (
                      <article className={`rounded-xl border p-5 ${providerStateClass(provider.state)}`} key={provider.provider}>
                        <div className="flex items-center justify-between gap-3">
                          <h3 className="font-semibold capitalize">{provider.provider}</h3>
                          <span className="inline-flex items-center gap-1.5 rounded-full border border-current/20 px-2.5 py-1 text-xs font-semibold">
                            {provider.state === "FRESH"
                              ? <CheckCircle2 aria-hidden="true" className="h-3.5 w-3.5" />
                              : <CircleAlert aria-hidden="true" className="h-3.5 w-3.5" />}
                            {provider.state}
                          </span>
                        </div>
                        <dl className="mt-4 space-y-3 text-sm">
                          <IdentityRow label="Last success" value={formatTimestamp(provider.last_successful_collection)} />
                          <IdentityRow label="DQ result" value={provider.dq_result} />
                          <IdentityRow label="Run status" value={provider.latest_run_status ?? "No run status"} />
                          <IdentityRow label="Datasets" value={provider.dataset_ids.length.toLocaleString()} />
                        </dl>
                      </article>
                    ))}
                  </div>
                ) : (
                  <UnavailableCard message="The endpoint returned no provider evidence to evaluate." title="PROVIDER EVIDENCE EMPTY" />
                )
              ) : (
                <UnavailableCard
                  message={snapshot?.providers.state === "UNAVAILABLE" ? snapshot.providers.message : "Provider health has not been evaluated."}
                  title="PROVIDER HEALTH UNAVAILABLE"
                />
              )}
            </section>
          </>
        ) : null}
      </div>
    </main>
  );
}

function HealthSkeleton() {
  return (
    <div className="space-y-4" role="status">
      <div className="h-28 animate-pulse rounded-xl bg-slate-200 motion-reduce:animate-none" />
      <div className="grid gap-4 md:grid-cols-3">
        {["application", "gold", "graph"].map((item) => (
          <div className="h-48 animate-pulse rounded-xl bg-slate-200 motion-reduce:animate-none" key={item} />
        ))}
      </div>
      <span className="sr-only">Checking release identity and provider health.</span>
    </div>
  );
}

function IdentityCard({
  children,
  icon: Icon,
  title,
}: {
  children: React.ReactNode;
  icon: typeof CheckCircle2;
  title: string;
}) {
  return (
    <article className="min-w-0 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-center gap-2">
        <Icon aria-hidden="true" className="h-5 w-5 text-blue-700" />
        <h3 className="font-semibold">{title}</h3>
      </div>
      <dl className="mt-5 space-y-3 text-sm">{children}</dl>
    </article>
  );
}

function IdentityRow({ label, mono = false, value }: { label: string; mono?: boolean; value: string }) {
  return (
    <div>
      <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</dt>
      <dd className={`mt-1 break-all text-slate-950 ${mono ? "font-mono text-xs leading-5" : "font-medium"}`}>{value}</dd>
    </div>
  );
}

function UnavailableCard({ message, title }: { message: string; title: string }) {
  return (
    <div className="mt-4 rounded-xl border border-red-300 bg-red-50 p-5 text-red-950" role="alert">
      <div className="flex items-start gap-3">
        <TriangleAlert aria-hidden="true" className="mt-0.5 h-5 w-5 shrink-0" />
        <div>
          <h3 className="font-semibold">{title}</h3>
          <p className="mt-1 text-sm leading-6">{message}</p>
          <p className="mt-1 text-sm leading-6">Use &quot;Check again&quot; after deployment configuration or artifact evidence is restored.</p>
        </div>
      </div>
    </div>
  );
}
