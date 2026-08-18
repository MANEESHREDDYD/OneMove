import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import SystemHealthPage from "../app/system-health/page";
import { ApiError, getApiJson } from "../lib/api/client";
import { respondFromRoutes } from "../test/api-mock";
import { dataHealthResponse, providerHealth, releaseIdentityResponse } from "../test/fixtures";

vi.mock("../lib/api/client", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../lib/api/client")>()),
  getApiJson: vi.fn(),
}));

function respond(routes: Record<string, unknown>): void {
  vi.mocked(getApiJson).mockImplementation(respondFromRoutes(routes));
}

const ALL_FRESH = {
  version: releaseIdentityResponse(),
  "data-health": dataHealthResponse({ data: [providerHealth({ state: "FRESH" })] }),
};

beforeEach(() => {
  vi.mocked(getApiJson).mockReset();
});

describe("verified release", () => {
  it("reports VERIFIED when the release and every provider check out", async () => {
    respond(ALL_FRESH);
    render(<SystemHealthPage />);

    expect(await screen.findByText("VERIFIED")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Release identity and provider health are verified" }),
    ).toBeInTheDocument();
  });

  it("shows the exact git SHA and artifact hashes without truncating them away", async () => {
    respond(ALL_FRESH);
    render(<SystemHealthPage />);

    expect(
      await screen.findByText("666ade66f965df76097c557cdf419501b683db75"),
    ).toBeInTheDocument();
    expect(screen.getByText("a".repeat(64))).toBeInTheDocument();
    expect(screen.getByText("b".repeat(64))).toBeInTheDocument();
  });
});

describe("provider states", () => {
  it("renders each canonical provider state as text", async () => {
    respond({ version: releaseIdentityResponse(), "data-health": dataHealthResponse() });
    render(<SystemHealthPage />);

    const section = await screen.findByRole("region", { name: /provider data health/i });
    for (const state of ["FRESH", "DEGRADED", "STALE", "UNAVAILABLE"]) {
      expect(within(section).getByText(state)).toBeInTheDocument();
    }
  });

  it("drops to ATTENTION when any provider is not fresh", async () => {
    respond({
      version: releaseIdentityResponse(),
      "data-health": dataHealthResponse({ data: [providerHealth({ state: "STALE" })] }),
    });
    render(<SystemHealthPage />);

    expect(await screen.findByText("ATTENTION")).toBeInTheDocument();
  });

  it("distinguishes empty provider evidence from a failed call", async () => {
    respond({
      version: releaseIdentityResponse(),
      "data-health": dataHealthResponse({ data: [] }),
    });
    render(<SystemHealthPage />);

    expect(await screen.findByText("PROVIDER EVIDENCE EMPTY")).toBeInTheDocument();
    expect(screen.queryByText("PROVIDER HEALTH UNAVAILABLE")).not.toBeInTheDocument();
  });

  it("names a provider that has no run status instead of leaving it blank", async () => {
    respond({
      version: releaseIdentityResponse(),
      "data-health": dataHealthResponse({
        data: [providerHealth({ state: "UNAVAILABLE", latest_run_status: null })],
      }),
    });
    render(<SystemHealthPage />);

    expect(await screen.findByText("No run status")).toBeInTheDocument();
  });
});

describe("DATASET_NOT_READY versus a hard failure", () => {
  it("shows the 503 not-ready message from the envelope", async () => {
    respond({
      version: releaseIdentityResponse(),
      "data-health": new ApiError(
        "The Gold dataset is still being built.",
        503,
        "DATASET_NOT_READY",
        "req-77",
      ),
    });
    render(<SystemHealthPage />);

    const alert = await screen.findByRole("alert");
    expect(within(alert).getByText("PROVIDER HEALTH UNAVAILABLE")).toBeInTheDocument();
    expect(within(alert).getByText(/still being built/)).toBeInTheDocument();
    expect(within(alert).getByText(/Request req-77\./)).toBeInTheDocument();
    // The release itself is still verified, so the page must not claim otherwise.
    expect(screen.queryByText("RELEASE IDENTITY UNAVAILABLE")).not.toBeInTheDocument();
  });

  it("treats an unreachable API as a release-level failure", async () => {
    respond({
      version: new ApiError("ZonePilot API is unavailable.", 502, "API_UNAVAILABLE", null),
      "data-health": new ApiError("ZonePilot API is unavailable.", 502, "API_UNAVAILABLE", null),
    });
    render(<SystemHealthPage />);

    expect(await screen.findByText("UNAVAILABLE")).toBeInTheDocument();
    expect(screen.getByText("RELEASE IDENTITY UNAVAILABLE")).toBeInTheDocument();
    expect(screen.getByText("PROVIDER HEALTH UNAVAILABLE")).toBeInTheDocument();
  });

  it("keeps one surface unavailable without hiding the other", async () => {
    respond({
      version: new ApiError("No verified release.", 503, "DATASET_NOT_READY", null),
      "data-health": dataHealthResponse({ data: [providerHealth({ state: "FRESH" })] }),
    });
    render(<SystemHealthPage />);

    expect(await screen.findByText("RELEASE IDENTITY UNAVAILABLE")).toBeInTheDocument();
    expect(screen.getByText("open-meteo")).toBeInTheDocument();
  });

  it("never substitutes a placeholder identity", async () => {
    respond({
      version: new ApiError("No verified release.", 503, "DATASET_NOT_READY", null),
      "data-health": dataHealthResponse(),
    });
    render(<SystemHealthPage />);

    await screen.findByText("RELEASE IDENTITY UNAVAILABLE");
    // Scoped to the release region on purpose: the provider table legitimately
    // renders the canonical dq_result value "UNKNOWN", which is reported
    // evidence rather than a substituted placeholder.
    const release = screen.getByRole("region", { name: /verified release identity/i });
    expect(release.textContent).not.toMatch(/unknown|N\/A|—/i);
  });
});

describe("refresh control", () => {
  it("re-requests both surfaces and recovers", async () => {
    const user = userEvent.setup();
    respond({
      version: new ApiError("Temporarily down.", 502, "API_UNAVAILABLE", null),
      "data-health": new ApiError("Temporarily down.", 502, "API_UNAVAILABLE", null),
    });
    render(<SystemHealthPage />);

    await screen.findByText("RELEASE IDENTITY UNAVAILABLE");
    respond(ALL_FRESH);
    await user.click(screen.getByRole("button", { name: /check again/i }));

    expect(await screen.findByText("VERIFIED")).toBeInTheDocument();
  });
});

describe("system health accessibility", () => {
  it("exposes a main landmark, one h1, and named regions", async () => {
    respond(ALL_FRESH);
    render(<SystemHealthPage />);

    await screen.findByText("VERIFIED");
    expect(screen.getByRole("main")).toBeInTheDocument();
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(screen.getByRole("region", { name: /verified release identity/i })).toBeInTheDocument();
  });

  it("links back to the Observatory", async () => {
    respond(ALL_FRESH);
    render(<SystemHealthPage />);

    await screen.findByText("VERIFIED");
    expect(screen.getByRole("link", { name: /observatory/i })).toHaveAttribute("href", "/");
  });
});
