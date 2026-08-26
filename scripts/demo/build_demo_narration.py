"""Build scene-aligned neural narration for the two OneMove demo cuts.

The Playwright recorder reads each scene file's measured duration, so the UI
advances only after its narration finishes. The combined M4A is muxed into the
final video after recording.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import shutil
import subprocess
from pathlib import Path

import edge_tts


ROOT = Path(__file__).resolve().parents[2]
STAGES = (
    "opening",
    "network",
    "live",
    "mission",
    "disruption",
    "comparison",
    "why",
    "architecture",
    "freeze",
    "evidence",
    "replay",
    "closing",
)

SCRIPTS: dict[str, dict[str, str]] = {
    "executive": {
        "opening": "OneMove is physical-commerce network decision intelligence. It turns changing network conditions into explainable, reproducible operating decisions.",
        "network": "We begin with real Bengaluru geography: more than eleven thousand roads and ninety-four canonical demand zones, rendered in the current MapLibre product.",
        "live": "Current traffic is provider-estimated. Weather is public-official. Each source shows provenance and freshness, and unavailable data is never silently replaced with zero.",
        "mission": "This controlled mission contains sixteen simulated orders on real roads. It uses no retailer, customer, merchant, or rider data.",
        "disruption": "Now we simulate a facility outage with compounded congestion. This is explicitly counterfactual, and the system evaluates a versioned scenario matrix.",
        "comparison": "Against a simulated do-nothing baseline, the solver recommends a facility set under the same snapshot, scenario, matrices, assumptions, policy, and objective. The view shows actual improvement and service tradeoffs.",
        "why": "The explanation is deterministic: selected action, service effect, objective components, largest tradeoffs, assumptions, and evidence—all derived from the result.",
        "architecture": "Public and provider evidence feeds scenarios, road routing, and CP-SAT. FastAPI, Postgres, the decision ledger, Next.js, and MapLibre carry the result through proof.",
        "freeze": "Freezing binds the recommendation to its decision time, release, policy, feature snapshot, solver output, and selected action.",
        "evidence": "The evidence view separates public geography, provider-estimated traffic, public-official weather, simulated scenarios, declared assumptions, and derived results.",
        "replay": "Finally, point-in-time replay recomputes the frozen decision and checks the action, facilities, objective, and content hash instead of replaying a canned success.",
        "closing": "Operate. Simulate. Decide. Prove. OneMove doesn't just recommend an action. It records what was known, why the decision was made, and whether that decision can be reproduced later. The goal is not another dashboard. It is a defensible decision system for physical-commerce operations.",
    },
    "technical": {
        "opening": "OneMove is physical-commerce network decision intelligence. The product connects four jobs that are normally split across maps, spreadsheets, solver notebooks, and audit logs: operate the network, simulate a disruption, decide on capacity placement, and prove later why that decision was taken. This walkthrough uses only the current MapLibre operating surface and a real API-backed workflow.",
        "network": "The base layer is a public OpenStreetMap extract for Bengaluru. It contains more than eleven thousand drivable ways and named arterials. Ninety-four H3 resolution-eight cells provide the canonical analysis geography. Candidate facility points and the order routes are product layers on the same interactive map, so the presenter can pan, zoom, inspect a route, and preserve geographic context throughout the decision journey.",
        "live": "The live-context endpoint reads normalized temporal observations from Postgres. Traffic is TomTom provider-estimated evidence; weather is Open-Meteo public-official evidence. The response carries capture time, age, observation count, failure history, and an explicit freshness verdict. If a provider is absent or outside its freshness window, OneMove returns unavailable or stale. It does not translate missing data into zero congestion or zero rainfall, and provider credentials never reach the browser.",
        "mission": "The mission overlay contains sixteen simulated orders placed on real Bengaluru coordinates, with pickup and drop-off points routed over the public road graph. Selecting an order isolates its actual routed geometry and the product states that routing is not traffic-aware. This is controlled demo evidence: there is no private retailer network, customer, merchant, rider, or order feed anywhere in the journey.",
        "disruption": "The highlighted scenario marks a simulated facility outage and uses the existing congested-outage travel matrix. That matrix is versioned and referenced by the optimization problem; it is not an observed incident. The question is now concrete: under identical inputs and policy, what is the outcome if the current simulated facility set remains unchanged, and what facility placement does the solver recommend instead?",
        "comparison": "The API submits an idempotent optimization request with a clearly labeled simulated do-nothing baseline. The worker builds the immutable problem snapshot and invokes OR-Tools CP-SAT out of process. Baseline and recommendation are evaluated under the same zones, scenarios, matrices, assumptions, graph version, and optimization policy. The executive comparison leads with the percentage improvement in the exact solver objective, coverage, expected travel, P-ninety-five travel, failure exposure, and the number of facilities. Fixed-point solver totals remain available under Engineering Details, rather than dominating the primary story.",
        "why": "The why panel is derived directly from the solver result and baseline comparison. It names the selected action and facilities, then decomposes recommendation minus baseline across expected travel, tail travel, facility cost, failure exposure, and coverage loss. Negative contributions are improvements; positive contributions expose a tradeoff. The explanation also identifies the sealed assumption version and the scenario evidence references. There is no language model inventing a rationale after the fact.",
        "architecture": "Here is the system path. The MapLibre operating surface sends authenticated, workspace-scoped requests to FastAPI. The API enforces idempotency and persists optimization jobs. A worker acquires the job and runs the versioned solver against frozen snapshot and matrix identifiers. PostgreSQL stores inputs, outputs, evidence references, and temporal metadata. The decision ledger then binds the accepted recommendation to its release and decision time. Point-in-time replay loads that lineage, excludes information that was unavailable at the original decision time, recomputes the result, and compares the action, facilities, objective, and hashes.",
        "freeze": "Freeze is not a screenshot or a presenter annotation. The endpoint reads the successful authoritative optimization job and records the selected action, exact solver objective, open facilities, dataset and network versions, assumption lineage, feature snapshot hash, evidence references, release SHA, solver version, and decision timestamp. The accepted result is therefore a stable decision record rather than an ephemeral UI state.",
        "evidence": "The evidence chain makes epistemic boundaries visible. Public-geographic network data is separate from provider-estimated traffic and public-official weather. The mission, disruption, and do-nothing baseline remain simulated. Business weights are declared assumptions. The recommendation, comparison, snapshot, and decision are derived artifacts. Each identifier points back to the actual run, capture, matrix, assumption set, or release used by this decision.",
        "replay": "The replay request is executed against the newly frozen decision. It verifies that the stored evidence was valid at the decision time, rebuilds the versioned problem, reruns the real solver, and compares the recomputed action, facility set, objective, and deterministic hash with the frozen record. A mismatch would surface as drift with an explicit difference; this successful verdict is displayed only because those checks passed in the recorded run.",
        "closing": "The pilot remains bounded to Bengaluru, simulated orders and disruption, road-network routing that is not traffic-aware, provider-dependent freshness, no modeled business economics, and no certified multi-city scale. Operate. Simulate. Decide. Prove. OneMove doesn't just recommend an action. It records what was known, why the decision was made, and whether that decision can be reproduced later. The goal is not another dashboard. It is a defensible decision system for physical-commerce operations.",
    },
}


def find_ffmpeg() -> Path:
    executable = shutil.which("ffmpeg")
    if executable:
        return Path(executable)
    local_app_data = Path(os.environ.get("LOCALAPPDATA", ""))
    matches = sorted((local_app_data / "Microsoft" / "WinGet" / "Packages").glob("Gyan.FFmpeg*/*/bin/ffmpeg.exe"))
    if not matches:
        raise RuntimeError("ffmpeg is required to assemble the narration track")
    return matches[-1]


async def build(version: str, voice: str) -> Path:
    output = ROOT / "artifacts" / "demo" / "audio" / version
    output.mkdir(parents=True, exist_ok=True)
    for stage in STAGES:
        text = SCRIPTS[version][stage]
        (output / f"{stage}.txt").write_text(text + "\n", encoding="utf-8")
        rate = "+22%" if version == "executive" else "+8%"
        await edge_tts.Communicate(text, voice, rate=rate).save(str(output / f"{stage}.mp3"))

    ffmpeg = find_ffmpeg()
    silence = output / "silence.mp3"
    subprocess.run(
        [str(ffmpeg), "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", "0.7", "-q:a", "9", str(silence)],
        check=True,
        capture_output=True,
    )
    concat = output / "concat.txt"
    concat.write_text(
        "\n".join(
            line
            for stage in STAGES
            for line in (f"file '{(output / f'{stage}.mp3').as_posix()}'", f"file '{silence.as_posix()}'")
        ) + "\n",
        encoding="utf-8",
    )
    narration = output / "narration.m4a"
    subprocess.run(
        [str(ffmpeg), "-y", "-f", "concat", "-safe", "0", "-i", str(concat), "-ar", "48000", "-ac", "1", "-c:a", "aac", "-b:a", "192k", str(narration)],
        check=True,
        capture_output=True,
    )
    return narration


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("version", choices=sorted(SCRIPTS))
    parser.add_argument("--voice", default="en-US-AndrewNeural")
    args = parser.parse_args()
    path = asyncio.run(build(args.version, args.voice))
    print(path)


if __name__ == "__main__":
    main()
