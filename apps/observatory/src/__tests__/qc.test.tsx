import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import OwnerQCScreen from "../app/qc/page";

/**
 * This route used to render hardcoded counts (150 expected, 142 received, 8
 * missing, per-participant completion percentages, and a collector marked
 * HEALTHY "2 mins ago") under the heading "real-time observational telemetry".
 * No QC endpoint exists in the ZonePilot API, so every one of those figures was
 * invented. These tests pin the honest replacement: the capability is declared
 * unavailable and no count is shown at all.
 */
describe("study operations QC", () => {
  it("declares the capability unavailable instead of reporting figures", () => {
    render(<OwnerQCScreen />);

    expect(screen.getByRole("heading", { level: 1, name: /study operations qc/i })).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent(/qc telemetry unavailable/i);
    expect(screen.getByText(/no study operations data is being reported/i)).toBeInTheDocument();
  });

  it("renders no fabricated counts", () => {
    const { container } = render(<OwnerQCScreen />);

    // The exact figures the page used to invent.
    for (const invented of ["150", "142", "P-101", "92%", "2 mins ago", "HEALTHY"]) {
      expect(container.textContent).not.toContain(invented);
    }
  });

  it("shows no bare numeric statistic anywhere on the page", () => {
    const { container } = render(<OwnerQCScreen />);

    // Any standalone integer would be a reported measure. The page must not
    // contain one, which is a stronger guarantee than checking known values and
    // keeps a future edit from quietly reintroducing a placeholder count.
    const standaloneNumbers = (container.textContent ?? "").match(/(?<![\w.])\d+(?![\w.%])/g);
    expect(standaloneNumbers).toBeNull();
  });

  it("marks every planned measure as not measured", () => {
    render(<OwnerQCScreen />);

    const notMeasured = screen.getAllByText("NOT MEASURED");
    expect(notMeasured.length).toBeGreaterThan(0);

    const rows = screen.getAllByRole("row");
    // Every body row carries a NOT MEASURED status; none carries a value.
    expect(notMeasured).toHaveLength(rows.length - 1);
  });

  it("keeps a main landmark and a route back to the Observatory", () => {
    render(<OwnerQCScreen />);

    expect(screen.getByRole("main")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /observatory/i })).toHaveAttribute("href", "/");
  });
});
