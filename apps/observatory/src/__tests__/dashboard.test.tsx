import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ObserverHome from "../app/page";
import { ApiError, getApiJson } from "../lib/api/client";
import { pendingForever, respondFromRoutes } from "../test/api-mock";
import {
  dataHealthResponse,
  datasetRecord,
  mapLayerListResponse,
  providerHealth,
  unavailableMapLayer,
  zoneListResponse,
  zoneSummary,
} from "../test/fixtures";

vi.mock("../lib/api/client", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../lib/api/client")>()),
  getApiJson: vi.fn(),
}));

vi.mock("../components/auth/auth-provider", () => ({
  useAuth: vi.fn(() => ({
    configured: true,
    loading: false,
    session: null,
    user: null,
    role: "OWNER",
    workspaceId: "ws-1",
    signIn: vi.fn(),
    signOut: vi.fn(),
  })),
}));

// The Leaflet canvas cannot render in jsdom, and the dashboard's contract with
// it is only that it receives the layers and zones. Its accessible text
// alternative is covered directly in layer-summary.test.tsx.
vi.mock("../components/map/network-map", () => ({
  default: ({ layers, zones }: { layers: unknown[]; zones: unknown[] }) => (
    <div data-testid="network-map">
      map: {layers.length} layers, {zones.length} zones
    </div>
  ),
}));

const HAPPY_ROUTES = {
  zones: zoneListResponse([zoneSummary()]),
  datasets: { data: [datasetRecord()] },
  "data-health": dataHealthResponse(),
  "network/map-layers": mapLayerListResponse(),
};

function respond(routes: Record<string, unknown>): void {
  vi.mocked(getApiJson).mockImplementation(respondFromRoutes(routes));
}

beforeEach(() => {
  vi.mocked(getApiJson).mockReset();
});

describe("loading state", () => {
  it("announces a busy state before any data resolves", () => {
    vi.mocked(getApiJson).mockImplementation(() => pendingForever());

    render(<ObserverHome />);

    expect(screen.getByText("Loading zones")).toBeInTheDocument();
    expect(screen.getByText("Loading datasets")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Active pilot zones" })).not.toBeInTheDocument();
  });
});

describe("loaded dashboard", () => {
  beforeEach(() => respond(HAPPY_ROUTES));

  it("renders the summary counts once every request resolves", async () => {
    render(<ObserverHome />);

    expect(await screen.findByRole("heading", { name: "Active pilot zones" })).toBeInTheDocument();
    expect(screen.getByText("Gold H3 cells").previousElementSibling).toHaveTextContent("1");
    expect(screen.getByText("Available datasets").previousElementSibling).toHaveTextContent("1");
  });

  it("passes the fetched layers and zones to the map", async () => {
    render(<ObserverHome />);

    expect(await screen.findByTestId("network-map")).toHaveTextContent("1 layers, 1 zones");
  });

  it("states plainly that zone-level traffic is unavailable", async () => {
    render(<ObserverHome />);

    expect(
      await screen.findByText("ZONE-LEVEL TRAFFIC DATA UNAVAILABLE"),
    ).toBeInTheDocument();
  });
});

describe("data-health provider states", () => {
  it("renders every canonical provider state as text", async () => {
    respond(HAPPY_ROUTES);
    render(<ObserverHome />);

    const section = await screen.findByRole("region", { name: /provider data health/i });
    for (const state of ["FRESH", "DEGRADED", "STALE", "UNAVAILABLE"]) {
      expect(within(section).getByText(state)).toBeInTheDocument();
    }
  });

  it("counts every non-fresh provider as needing attention", async () => {
    respond(HAPPY_ROUTES);
    render(<ObserverHome />);

    // The fixture carries one provider in each of the four states.
    const label = await screen.findByText("Non-fresh providers");
    expect(label.previousElementSibling).toHaveTextContent("3");
  });

  it("says so when a provider has never collected successfully", async () => {
    respond({
      ...HAPPY_ROUTES,
      "data-health": dataHealthResponse({
        data: [providerHealth({ state: "UNAVAILABLE", last_successful_collection: null })],
      }),
    });
    render(<ObserverHome />);

    expect(await screen.findByText("No successful collection")).toBeInTheDocument();
  });
});

describe("empty state", () => {
  it("reports unavailable network data instead of an empty grid", async () => {
    respond({ ...HAPPY_ROUTES, zones: zoneListResponse([]) });
    render(<ObserverHome />);

    expect(await screen.findByText("NETWORK DATA UNAVAILABLE")).toBeInTheDocument();
    expect(screen.getByText("No verified pilot zones are mounted.")).toBeInTheDocument();
  });

  it("does not invent a traffic layer when the API returns none", async () => {
    respond({ ...HAPPY_ROUTES, "network/map-layers": mapLayerListResponse([]) });
    render(<ObserverHome />);

    expect(await screen.findByTestId("network-map")).toHaveTextContent("0 layers");
  });
});

describe("error state", () => {
  it("shows the API envelope message in an alert with a retry control", async () => {
    respond({
      ...HAPPY_ROUTES,
      "data-health": new ApiError("Gold dataset is not ready.", 503, "DATASET_NOT_READY", "req-5"),
    });
    render(<ObserverHome />);

    const alert = await screen.findByRole("alert");
    expect(within(alert).getByText("Observatory data unavailable")).toBeInTheDocument();
    expect(within(alert).getByText(/Gold dataset is not ready\./)).toBeInTheDocument();
    expect(within(alert).getByText(/Request req-5\./)).toBeInTheDocument();
    expect(within(alert).getByRole("button", { name: /retry/i })).toBeInTheDocument();
  });

  it("hides the dashboard body while the error is showing", async () => {
    respond({ ...HAPPY_ROUTES, zones: new ApiError("Upstream down.", 502, "API_UNAVAILABLE", null) });
    render(<ObserverHome />);

    await screen.findByRole("alert");
    expect(screen.queryByRole("heading", { name: "Active pilot zones" })).not.toBeInTheDocument();
  });

  it("recovers when retry succeeds", async () => {
    const user = userEvent.setup();
    vi.mocked(getApiJson).mockImplementation(
      respondFromRoutes({ ...HAPPY_ROUTES, zones: new ApiError("Flaky.", 500, "BOOM", null) }),
    );
    render(<ObserverHome />);

    const alert = await screen.findByRole("alert");
    respond(HAPPY_ROUTES);
    await user.click(within(alert).getByRole("button", { name: /retry/i }));

    expect(await screen.findByRole("heading", { name: "Active pilot zones" })).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("degrades to a generic message for a non-ApiError failure", async () => {
    respond({ ...HAPPY_ROUTES, datasets: new TypeError("Failed to fetch") });
    render(<ObserverHome />);

    expect(await screen.findByText("Failed to fetch")).toBeInTheDocument();
  });
});

describe("evidence honesty", () => {
  it("renders no literal 'null' for a layer with no evidence class", async () => {
    respond({
      ...HAPPY_ROUTES,
      "network/map-layers": mapLayerListResponse([unavailableMapLayer()]),
      zones: zoneListResponse([zoneSummary({ evidence_class: null })]),
    });
    const { container } = render(<ObserverHome />);

    await screen.findByRole("heading", { name: "Active pilot zones" });
    expect(container.textContent).not.toMatch(/\bnull\b/);
  });

  it("labels a zone whose evidence class is absent", async () => {
    respond({ ...HAPPY_ROUTES, zones: zoneListResponse([zoneSummary({ evidence_class: null })]) });
    render(<ObserverHome />);

    await screen.findByRole("heading", { name: "Active pilot zones" });
    expect(screen.getByText("No evidence class")).toBeInTheDocument();
  });
});

describe("dashboard accessibility", () => {
  beforeEach(() => respond(HAPPY_ROUTES));

  it("exposes one main landmark and a single h1", async () => {
    render(<ObserverHome />);

    await screen.findByRole("heading", { name: "Active pilot zones" });
    expect(screen.getByRole("main")).toBeInTheDocument();
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
  });

  it("names every section region for screen reader navigation", async () => {
    render(<ObserverHome />);

    await screen.findByRole("heading", { name: "Active pilot zones" });
    expect(screen.getByRole("region", { name: /network summary/i })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: /evidence map/i })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: /provider data health/i })).toBeInTheDocument();
  });

  it("gives the zone capture links a destination that names the zone", async () => {
    render(<ObserverHome />);

    await screen.findByRole("heading", { name: "Active pilot zones" });
    const link = screen.getByRole("link", { name: /capture evidence for zone/i });
    expect(link).toHaveAttribute("href", "/capture?zone_id=8861086b0dfffff");
  });
});
