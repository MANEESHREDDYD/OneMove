import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import React from "react";

// Mock Supabase
vi.mock("../lib/auth/supabase", () => ({
  getSupabaseBrowserClient: () => ({
    auth: {
      getSession: async () => ({
        data: {
          session: {
            access_token: "test-token",
            user: { app_metadata: { workspace_id: "ws-blr-01", role: "analyst" } },
          },
        },
        error: null,
      }),
      refreshSession: async () => ({ data: { session: null } }),
    },
  }),
}));

// Mock NavigationHeader
vi.mock("../components/navigation", () => ({
  NavigationHeader: () => <header data-testid="nav-header">ZonePilot Observatory</header>,
}));

// Mock NetworkMap component
vi.mock("../components/map/network-map", () => ({
  default: () => <div data-testid="network-map">Mock Network Map</div>,
}));

import ExperimentsPage from "../app/experiments/page";
import AssistantPage from "../app/assistant/page";
import EvidencePage from "../app/evidence/page";

describe("Observatory Product Routes", () => {
  it("renders Experiments page with EXP-01..04 suite", () => {
    render(<ExperimentsPage />);
    expect(screen.getByText(/Experiment Registry \(EXP-01\.\.04\)/i)).toBeInTheDocument();
    expect(screen.getByText("EXP-01")).toBeInTheDocument();
    expect(screen.getByText("EXP-02")).toBeInTheDocument();
    expect(screen.getByText("EXP-03")).toBeInTheDocument();
    expect(screen.getByText("EXP-04")).toBeInTheDocument();
  });

  it("renders Typed Assistant page with prompt samples and evidence lineage", () => {
    render(<AssistantPage />);
    expect(screen.getByText(/Typed Operational Assistant \(R8\)/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Ask/i })).toBeInTheDocument();
  });

  it("renders Evidence Inspector page with taxonomy classes", () => {
    render(<EvidencePage />);
    expect(screen.getByText(/Evidence Inspector/i)).toBeInTheDocument();
    expect(screen.getByText("OBSERVED")).toBeInTheDocument();
    expect(screen.getByText("PUBLIC_GEOGRAPHIC")).toBeInTheDocument();
  });
});
