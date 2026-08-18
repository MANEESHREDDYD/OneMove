"use client";

import { useState, Suspense, useEffect, useId } from "react";
import type { ReactNode } from "react";
import { ArrowLeft, Save } from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { saveToOutbox, syncOutbox } from "../../lib/outbox";

const FIELD_CLASS =
  "w-full rounded-lg border p-2.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600";

/**
 * A labelled numeric field.
 *
 * The label is associated with the control by id rather than by proximity, and
 * a validation failure is announced three ways: `aria-invalid`, a message tied
 * to the field through `aria-describedby`, and a red border. The border alone
 * was the previous signal, which is invisible to a screen reader and to anyone
 * who cannot distinguish the colour (WCAG 1.4.1, Use of Color).
 */
function NumericField({
  error,
  label,
  onChange,
  step,
  value,
}: {
  error: string | undefined;
  label: string;
  onChange: (next: string) => void;
  step?: string;
  value: string;
}) {
  const fieldId = useId();
  const errorId = `${fieldId}-error`;
  return (
    <div>
      <label className="mb-1 block text-sm font-medium text-gray-700" htmlFor={fieldId}>
        {label}
      </label>
      <input
        aria-describedby={error ? errorId : undefined}
        aria-invalid={error ? true : undefined}
        className={`${FIELD_CLASS} ${error ? "border-red-600" : "border-gray-300"}`}
        id={fieldId}
        inputMode="decimal"
        onChange={(event) => onChange(event.target.value)}
        step={step}
        type="number"
        value={value}
      />
      {error && (
        <p className="mt-1 text-sm font-medium text-red-700" id={errorId}>
          {error}
        </p>
      )}
    </div>
  );
}

function Panel({ children, title }: { children: ReactNode; title: string }) {
  return (
    <section className="rounded-xl border bg-white p-4 shadow-sm">
      <h2 className="mb-4 font-semibold text-gray-800">{title}</h2>
      {children}
    </section>
  );
}

function CaptureForm() {
  const searchParams = useSearchParams();
  const assignmentId = searchParams.get("assignment_id");
  const availabilityId = useId();

  useEffect(() => {
    window.addEventListener("online", syncOutbox);
    syncOutbox();
    return () => window.removeEventListener("online", syncOutbox);
  }, []);

  const [formData, setFormData] = useState({
    etaLow: "",
    etaHigh: "",
    optionCount: "",
    availability: "AVAILABLE",
    substitutionStatus: "EXACT_MATCH",
    basketPrice: "",
    deliveryFee: "",
    platformFee: "",
    otherFee: "",
  });

  const [errors, setErrors] = useState<Record<string, string>>({});
  const [outboxMessage, setOutboxMessage] = useState("");

  const validate = () => {
    const newErrors: Record<string, string> = {};
    if (!formData.etaLow || isNaN(Number(formData.etaLow))) {
      newErrors.etaLow = "Enter a valid number of minutes.";
    }
    if (!formData.etaHigh || isNaN(Number(formData.etaHigh))) {
      newErrors.etaHigh = "Enter a valid number of minutes.";
    }
    if (Number(formData.etaLow) > Number(formData.etaHigh)) {
      newErrors.etaHigh = "High ETA must be greater than or equal to Low ETA.";
    }
    if (!formData.optionCount || isNaN(Number(formData.optionCount))) {
      newErrors.optionCount = "Enter a valid option count.";
    }
    if (formData.availability === "AVAILABLE") {
      if (!formData.basketPrice || isNaN(Number(formData.basketPrice))) {
        newErrors.basketPrice = "Enter a valid basket price.";
      }
    }
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setOutboxMessage("");
    if (!assignmentId) {
      setErrors({ assignment: "Open this form from an active assignment before capturing evidence." });
      return;
    }
    if (validate()) {
      const eventPayload = {
        assignment_id: assignmentId,
        observed_at_device: new Date().toISOString(),
        eta_low_min: formData.etaLow ? parseInt(formData.etaLow, 10) : null,
        eta_high_min: formData.etaHigh ? parseInt(formData.etaHigh, 10) : null,
        option_count: formData.optionCount ? parseInt(formData.optionCount, 10) : null,
        availability_state: formData.availability === "AVAILABLE" ? "IN_STOCK" : "UNAVAILABLE",
        reference_basket_price: formData.basketPrice ? parseFloat(formData.basketPrice) : null,
      };

      saveToOutbox(eventPayload).then(() => {
        setOutboxMessage("Observation queued in outbox for sync.");
        syncOutbox();
      });
    }
  };

  const showLogistics = formData.availability === "AVAILABLE";

  return (
    <form className="space-y-6 p-4" noValidate onSubmit={handleSubmit}>
      {errors.assignment && (
        <div className="rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm text-amber-950" role="alert">
          {errors.assignment}
        </div>
      )}

      <Panel title="Reference Basket">
        <div className="mb-4 rounded-lg bg-blue-50 p-3 text-sm text-blue-900">
          Items: 1x Biryani, 1x Coke (500ml)
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700" htmlFor={availabilityId}>
            Availability
          </label>
          <select
            className="w-full rounded-lg border border-gray-300 bg-gray-50 p-2.5 shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600"
            id={availabilityId}
            onChange={(e) => setFormData({ ...formData, availability: e.target.value })}
            value={formData.availability}
          >
            <option value="AVAILABLE">Available</option>
            <option value="UNAVAILABLE">Unavailable</option>
          </select>
        </div>
      </Panel>

      {showLogistics && (
        <>
          <Panel title="Delivery Logistics">
            <div className="grid grid-cols-2 gap-4">
              <NumericField
                error={errors.etaLow}
                label="ETA Low (min)"
                onChange={(etaLow) => setFormData({ ...formData, etaLow })}
                value={formData.etaLow}
              />
              <NumericField
                error={errors.etaHigh}
                label="ETA High (min)"
                onChange={(etaHigh) => setFormData({ ...formData, etaHigh })}
                value={formData.etaHigh}
              />
            </div>
            <div className="mt-4">
              <NumericField
                error={errors.optionCount}
                label="Option Count"
                onChange={(optionCount) => setFormData({ ...formData, optionCount })}
                value={formData.optionCount}
              />
            </div>
          </Panel>

          <Panel title="Financials (INR)">
            <NumericField
              error={errors.basketPrice}
              label="Basket Price"
              onChange={(basketPrice) => setFormData({ ...formData, basketPrice })}
              step="0.01"
              value={formData.basketPrice}
            />
          </Panel>
        </>
      )}

      <p aria-live="polite" className="text-sm font-semibold text-green-700" data-testid="outbox-status">
        {outboxMessage}
      </p>

      <button
        className="mb-4 flex min-h-11 w-full items-center justify-center rounded-xl bg-blue-700 px-4 py-4 font-bold text-white hover:bg-blue-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2"
        type="submit"
      >
        <Save aria-hidden="true" className="mr-2 h-5 w-5" />
        Save Observation
      </button>
    </form>
  );
}

export default function CaptureScreen() {
  return (
    <main className="min-h-screen bg-gray-50 pb-20" id="main-content">
      <header className="sticky top-0 z-10 flex items-center border-b bg-white px-4 py-3">
        <Link
          className="mr-4 flex min-h-11 min-w-11 items-center justify-center rounded-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600"
          href="/"
        >
          <ArrowLeft aria-hidden="true" className="h-6 w-6 text-gray-700" />
          <span className="sr-only">Back to Observatory</span>
        </Link>
        <h1 className="text-lg font-bold">Capture Probe</h1>
      </header>
      <Suspense fallback={<p className="p-4 text-sm text-gray-700">Loading capture form</p>}>
        <CaptureForm />
      </Suspense>
    </main>
  );
}
