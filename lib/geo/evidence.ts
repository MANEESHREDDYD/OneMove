/**
 * Evidence classes for anything a map draws.
 *
 * This list is closed. It is exactly the project's vocabulary — in particular
 * there is no `PROJECTED` class, and a value carrying one is not "close enough"
 * to `DERIVED`: it is an unknown class and must degrade to UNAVAILABLE so the
 * mislabelling is visible on screen instead of being silently laundered into a
 * class that looks trustworthy.
 */
export const EVIDENCE_CLASSES = [
  'OBSERVED',
  'PUBLIC_OFFICIAL',
  'PUBLIC_GEOGRAPHIC',
  'PROVIDER_ESTIMATED',
  'DERIVED',
  'SIMULATED',
  'ASSUMPTION',
  'STAGING_DO_NOT_USE',
  'TEST_ONLY',
] as const;

export type EvidenceClass = (typeof EVIDENCE_CLASSES)[number];

/**
 * The sentinel for "we have no evidence class". It is deliberately NOT a member
 * of EvidenceClass: absence is a distinct state from every real class, the same
 * way an absent number is distinct from zero.
 */
export const UNAVAILABLE = 'UNAVAILABLE' as const;
export type EvidenceState = EvidenceClass | typeof UNAVAILABLE;

const VALID = new Set<string>(EVIDENCE_CLASSES);

export function isEvidenceClass(value: unknown): value is EvidenceClass {
  return typeof value === 'string' && VALID.has(value);
}

/** Any unrecognised or missing class becomes UNAVAILABLE. Never guesses. */
export function evidenceState(value: unknown): EvidenceState {
  return isEvidenceClass(value) ? value : UNAVAILABLE;
}

/**
 * Classes that describe the world as it actually was or is.
 * SIMULATED, ASSUMPTION, STAGING_DO_NOT_USE and TEST_ONLY are not among them.
 */
const REAL_WORLD = new Set<EvidenceClass>([
  'OBSERVED',
  'PUBLIC_OFFICIAL',
  'PUBLIC_GEOGRAPHIC',
  'PROVIDER_ESTIMATED',
  'DERIVED',
]);

/** True only for a class that reports the real world. UNAVAILABLE is false. */
export function describesRealWorld(state: EvidenceState): boolean {
  return isEvidenceClass(state) && REAL_WORLD.has(state);
}

/**
 * True when the state must be announced as not-real before a viewer reads the
 * pixels as an observation. UNAVAILABLE counts: an absent class is not a licence
 * to present something as measured.
 */
export function requiresSyntheticWarning(state: EvidenceState): boolean {
  return !describesRealWorld(state);
}

/** Short human sentence naming what the viewer is looking at. */
export function evidenceCaption(state: EvidenceState): string {
  switch (state) {
    case 'OBSERVED':
      return 'Observed measurement';
    case 'PUBLIC_OFFICIAL':
      return 'Published by an official source';
    case 'PUBLIC_GEOGRAPHIC':
      return 'Public geographic data';
    case 'PROVIDER_ESTIMATED':
      return 'Estimated by a third-party provider — not a direct measurement';
    case 'DERIVED':
      return 'Computed from other evidence';
    case 'SIMULATED':
      return 'Simulated — this did not happen';
    case 'ASSUMPTION':
      return 'Assumption — not evidence';
    case 'STAGING_DO_NOT_USE':
      return 'Staging artifact — do not use';
    case 'TEST_ONLY':
      return 'Test fixture — not operational data';
    default:
      return 'No evidence class — value unavailable';
  }
}

/** Tailwind ring/text/bg triple. UNAVAILABLE is deliberately colourless. */
export const EVIDENCE_TONE: Record<EvidenceState, string> = {
  OBSERVED: 'bg-emerald-500/15 text-emerald-300 ring-emerald-400/30',
  PUBLIC_OFFICIAL: 'bg-sky-500/15 text-sky-300 ring-sky-400/30',
  PUBLIC_GEOGRAPHIC: 'bg-teal-500/15 text-teal-300 ring-teal-400/30',
  PROVIDER_ESTIMATED: 'bg-violet-500/15 text-violet-300 ring-violet-400/30',
  DERIVED: 'bg-blue-500/15 text-blue-300 ring-blue-400/30',
  SIMULATED: 'bg-orange-500/20 text-orange-200 ring-orange-400/50',
  ASSUMPTION: 'bg-amber-500/15 text-amber-300 ring-amber-400/30',
  STAGING_DO_NOT_USE: 'bg-rose-500/20 text-rose-200 ring-rose-400/50',
  TEST_ONLY: 'bg-fuchsia-500/15 text-fuchsia-300 ring-fuchsia-400/30',
  UNAVAILABLE: 'bg-slate-600/25 text-slate-300 ring-slate-500/40',
};

/**
 * Renders a numeric measurement, keeping "absent" distinct from zero.
 * `0` is a real reading and prints as `0`; null/undefined/NaN print UNAVAILABLE.
 */
export function measurement(
  value: number | null | undefined,
  unit?: string,
): string {
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return UNAVAILABLE;
  }
  return unit ? `${value} ${unit}` : String(value);
}
