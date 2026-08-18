import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import CaptureScreen from "../app/capture/page";

// vi.mock factories are hoisted above the module body, so the doubles they
// close over have to be hoisted too.
const { saveToOutbox, syncOutbox } = vi.hoisted(() => ({
  saveToOutbox: vi.fn<(payload: Record<string, unknown>) => Promise<void>>(),
  syncOutbox: vi.fn<() => Promise<void>>(),
}));

const params = vi.hoisted(() => ({ current: new URLSearchParams() }));

vi.mock("../lib/outbox", () => ({ saveToOutbox, syncOutbox }));

vi.mock("next/navigation", () => ({
  useSearchParams: () => params.current,
}));

beforeEach(() => {
  saveToOutbox.mockReset().mockResolvedValue(undefined);
  syncOutbox.mockReset().mockResolvedValue(undefined);
  params.current = new URLSearchParams();
});

describe("capture form accessibility", () => {
  it("exposes a main landmark and a named back link", async () => {
    render(<CaptureScreen />);

    expect(await screen.findByRole("main")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /back to observatory/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 1, name: "Capture Probe" })).toBeInTheDocument();
  });

  /**
   * Every control must be reachable by its visible label. Previously the
   * labels were plain text next to the inputs, so `getByLabelText` could not
   * find them and neither could a screen reader.
   */
  it("associates every visible label with its control", async () => {
    render(<CaptureScreen />);

    expect(await screen.findByLabelText("Availability")).toHaveRole("combobox");
    expect(screen.getByLabelText("ETA Low (min)")).toHaveRole("spinbutton");
    expect(screen.getByLabelText("ETA High (min)")).toHaveRole("spinbutton");
    expect(screen.getByLabelText("Option Count")).toHaveRole("spinbutton");
    expect(screen.getByLabelText("Basket Price")).toHaveRole("spinbutton");
  });

  it("hides logistics fields when the basket is unavailable", async () => {
    const user = userEvent.setup();
    render(<CaptureScreen />);

    await user.selectOptions(await screen.findByLabelText("Availability"), "UNAVAILABLE");

    expect(screen.queryByLabelText("ETA Low (min)")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Basket Price")).not.toBeInTheDocument();
  });
});

describe("capture validation", () => {
  /**
   * The regression this pins: validation used to set an `errors` object that
   * was never rendered. The only feedback was a red border, so the reason for
   * the rejection was unavailable to assistive tech and to anyone who cannot
   * distinguish the colour.
   */
  it("renders each validation message and links it to its field", async () => {
    const user = userEvent.setup();
    params.current = new URLSearchParams({ assignment_id: "assign-1" });
    render(<CaptureScreen />);

    await user.click(await screen.findByRole("button", { name: /save observation/i }));

    const etaLow = screen.getByLabelText("ETA Low (min)");
    expect(etaLow).toHaveAttribute("aria-invalid", "true");

    const describedBy = etaLow.getAttribute("aria-describedby");
    expect(describedBy).toBeTruthy();
    expect(document.getElementById(describedBy as string)).toHaveTextContent(
      "Enter a valid number of minutes.",
    );

    expect(screen.getByText("Enter a valid option count.")).toBeInTheDocument();
    expect(screen.getByText("Enter a valid basket price.")).toBeInTheDocument();
    expect(saveToOutbox).not.toHaveBeenCalled();
  });

  it("rejects an inverted ETA range with an explanatory message", async () => {
    const user = userEvent.setup();
    params.current = new URLSearchParams({ assignment_id: "assign-1" });
    render(<CaptureScreen />);

    await user.type(await screen.findByLabelText("ETA Low (min)"), "40");
    await user.type(screen.getByLabelText("ETA High (min)"), "10");
    await user.type(screen.getByLabelText("Option Count"), "3");
    await user.type(screen.getByLabelText("Basket Price"), "450");
    await user.click(screen.getByRole("button", { name: /save observation/i }));

    expect(
      screen.getByText("High ETA must be greater than or equal to Low ETA."),
    ).toBeInTheDocument();
    expect(saveToOutbox).not.toHaveBeenCalled();
  });

  it("refuses to capture without an assignment and says so in an alert", async () => {
    const user = userEvent.setup();
    render(<CaptureScreen />);

    await user.click(await screen.findByRole("button", { name: /save observation/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      /open this form from an active assignment/i,
    );
    expect(saveToOutbox).not.toHaveBeenCalled();
  });

  it("queues a valid observation and announces it politely", async () => {
    const user = userEvent.setup();
    params.current = new URLSearchParams({ assignment_id: "assign-1" });
    render(<CaptureScreen />);

    await user.type(await screen.findByLabelText("ETA Low (min)"), "10");
    await user.type(screen.getByLabelText("ETA High (min)"), "20");
    await user.type(screen.getByLabelText("Option Count"), "3");
    await user.type(screen.getByLabelText("Basket Price"), "450");
    await user.click(screen.getByRole("button", { name: /save observation/i }));

    const status = await screen.findByTestId("outbox-status");
    expect(status).toHaveTextContent("Observation queued in outbox for sync.");
    expect(status).toHaveAttribute("aria-live", "polite");

    expect(saveToOutbox).toHaveBeenCalledTimes(1);
    expect(saveToOutbox.mock.calls[0]?.[0]).toMatchObject({
      assignment_id: "assign-1",
      eta_low_min: 10,
      eta_high_min: 20,
      option_count: 3,
      availability_state: "IN_STOCK",
      reference_basket_price: 450,
    });
  });
});
