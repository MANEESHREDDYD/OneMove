import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { MapLayerSummary, describeLayer, describeLayers } from "../components/map/layer-summary";
import { availableMapLayer, unavailableMapLayer, zoneSummary } from "../test/fixtures";

describe("describeLayer", () => {
  it("reports an available layer with its evidence class and counts", () => {
    const description = describeLayer(
      "Road geometries",
      availableMapLayer({ returned_feature_count: 900, total_feature_count: 12500 }),
    );

    expect(description.availability).toBe("AVAILABLE");
    expect(description.features).toBe("900 of 12,500 features");
    expect(description.provenance).toContain("PUBLIC_GEOGRAPHIC");
  });

  it("never stringifies a null evidence class", () => {
    const description = describeLayer("POIs", unavailableMapLayer());

    expect(description.availability).toBe("UNAVAILABLE");
    expect(description.provenance).not.toContain("null");
    expect(description.provenance).toContain("no evidence class");
  });

  it("names the missing pieces when provenance fields are null", () => {
    const description = describeLayer("POIs", unavailableMapLayer());

    expect(description.provenance).toContain("unversioned");
    expect(description.provenance).toContain("timestamp unavailable");
  });

  it("treats a wholly absent layer as unavailable rather than empty", () => {
    const description = describeLayer("Intersections", undefined);

    expect(description.availability).toBe("UNAVAILABLE");
    expect(description.features).toBe("No mounted artifact");
    expect(description.provenance).toBe("Layer metadata unavailable");
  });

  it("does not borrow an evidence class from an unavailable layer", () => {
    // A malformed payload could carry a class on an UNAVAILABLE layer. The
    // layer's state is the authority on whether an observation exists.
    const description = describeLayer(
      "POIs",
      unavailableMapLayer({ evidence_class: "OBSERVED" }),
    );

    expect(description.provenance).toContain("no evidence class");
    expect(description.provenance).not.toContain("OBSERVED");
  });
});

describe("describeLayers", () => {
  it("marks H3 cells unavailable when no zones are mounted", () => {
    const cells = describeLayers([], []).find((item) => item.label === "H3 R8 cells");

    expect(cells?.availability).toBe("UNAVAILABLE");
    expect(cells?.features).toBe("No mounted cells");
  });

  it("always reports traffic as unavailable, since no artifact is joined", () => {
    const traffic = describeLayers([availableMapLayer()], [zoneSummary()]).find(
      (item) => item.label === "Traffic",
    );

    expect(traffic?.availability).toBe("UNAVAILABLE");
  });
});

describe("MapLayerSummary", () => {
  it("exposes the map as a table so it is reachable without seeing the canvas", () => {
    render(<MapLayerSummary layers={[availableMapLayer()]} zones={[zoneSummary()]} />);

    const table = screen.getByRole("table");
    expect(within(table).getByRole("columnheader", { name: /layer/i })).toBeInTheDocument();
    expect(within(table).getByRole("rowheader", { name: "Road geometries" })).toBeInTheDocument();
    expect(within(table).getByRole("rowheader", { name: "Traffic" })).toBeInTheDocument();
  });

  it("renders availability as text, not colour alone", () => {
    render(
      <MapLayerSummary
        layers={[availableMapLayer(), unavailableMapLayer()]}
        zones={[zoneSummary()]}
      />,
    );

    expect(screen.getAllByText("AVAILABLE").length).toBeGreaterThan(0);
    expect(screen.getAllByText("UNAVAILABLE").length).toBeGreaterThan(0);
  });

  it("renders no literal 'null' anywhere for an unavailable layer", () => {
    const { container } = render(
      <MapLayerSummary layers={[unavailableMapLayer()]} zones={[zoneSummary()]} />,
    );

    expect(container.textContent).not.toMatch(/\bnull\b/);
  });

  it("reports feature counts for an available layer", () => {
    render(
      <MapLayerSummary
        layers={[availableMapLayer({ returned_feature_count: 42, total_feature_count: 99 })]}
        zones={[zoneSummary()]}
      />,
    );

    expect(screen.getByText("42 of 99 features")).toBeInTheDocument();
  });

  it("summarises how many layers are available", () => {
    render(
      <MapLayerSummary
        layers={[availableMapLayer(), unavailableMapLayer()]}
        zones={[zoneSummary()]}
      />,
    );

    // Pilot boundary, H3 cells, and roads are available; POIs, intersections
    // and traffic are not.
    expect(screen.getByText(/3 of 6 layers are\s+available/)).toBeInTheDocument();
  });
});
