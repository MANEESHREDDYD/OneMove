"""Real Open-Meteo acquisition for the R1 pilot area, versioned by forecast issue.

Why this module exists
----------------------
A weather forecast is not a fact about the weather; it is a fact about what a
model believed at a particular moment. Storing "the forecast for 18:00" and
overwriting it as the model updates destroys exactly the signal R2 needs. So
every record here is pinned to the provider's *issue cycle*:

``issued_at``
    ``last_run_initialisation_time`` from the model's own metadata endpoint -- the
    instant the provider initialised the forecast cycle. Real, provider reported,
    not a wall clock guess.

``information_available_at``
    ``last_run_availability_time`` -- the instant that cycle became downloadable.
    Always at or after ``issued_at``, which is the invariant the contract requires.

``retrieved_at``
    When this process actually received the bytes.

``valid_at`` / ``event_time``
    The hour the forecast value applies to.

Because ``issued_at`` participates in the storage natural key, re-running inside
one cycle writes nothing new, and the next cycle appends a fresh version beside
the old one instead of replacing it.

A caveat recorded honestly rather than hidden: Open-Meteo serves these 94 H3 R8
cells from a much coarser NWP grid, so many cells resolve to the same grid point.
Each record therefore carries ``provider_grid_latitude``/``provider_grid_longitude``
so downstream code can see the true spatial resolution instead of mistaking 94
rows for 94 independent measurements.
"""

from __future__ import annotations

import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone

from services.collectors.execution.evidence import (
    artifact_hash,
    canonical_json,
    record_id_for,
    request_fingerprint,
    sha256_hex,
)
from services.collectors.execution.pilot_area import pilot_cell_centroids
from services.collectors.execution.run_state import RunStatus, status_for_http_error
from services.temporal.contracts import EvidenceClass, TemporalFeatureRecord

PROVIDER = "open-meteo"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
MODEL_META_URL = "https://api.open-meteo.com/data/{meta_id}/static/meta.json"
USER_AGENT = "zonepilot-r0-collector/1.0 (+https://github.com/MANEESHREDDYD/OneMove)"

DATASET_ID = "openmeteo-weather-forecast-h3r8-blr-pilot"
DATASET_VERSION = "1.0.0"

# Open-Meteo names a model twice: once in the ``models=`` request parameter and
# once in the path of its metadata endpoint. Both are needed and they differ.
MODEL_META_IDS = {
    "icon_global": "dwd_icon",
    "ecmwf_ifs025": "ecmwf_ifs025",
    "gfs_global": "ncep_gfs013",
}
DEFAULT_MODEL = "icon_global"

HOURLY_VARIABLES = (
    "temperature_2m",
    "apparent_temperature",
    "relative_humidity_2m",
    "precipitation",
    "rain",
    "wind_speed_10m",
    "wind_gusts_10m",
    "cloud_cover",
    "surface_pressure",
    "weather_code",
)

# Open-Meteo is an official public meteorological aggregator, so its output is
# PUBLIC_OFFICIAL rather than an internal estimate.
EVIDENCE_CLASS = EvidenceClass.PUBLIC_OFFICIAL

_MAX_ATTEMPTS = 3
_BACKOFF_SECONDS = (1.0, 4.0)


class AcquisitionError(RuntimeError):
    """A provider failure carrying the run status it should map to."""

    def __init__(self, message: str, status: RunStatus, code: str) -> None:
        super().__init__(message)
        self.status = status
        self.code = code


@dataclass(frozen=True)
class ProviderIssue:
    """One forecast cycle, as the provider itself describes it."""

    model: str
    issued_at: datetime
    information_available_at: datetime
    update_interval_seconds: int
    temporal_resolution_seconds: int
    meta_hash: str

    @property
    def logical_interval(self) -> str:
        return f"{self.model}/{self.issued_at.strftime('%Y-%m-%dT%H:%M:%SZ')}"


@dataclass
class AcquisitionResult:
    """Everything a caller needs to persist, report, and audit one acquisition."""

    issue: ProviderIssue
    records: list[TemporalFeatureRecord]
    raw_payload: bytes
    artifact_hash: str
    request_fingerprint: str
    request_url: str
    retrieved_at: datetime
    provider_version: str
    grid_points: dict[str, tuple[float, float]] = field(default_factory=dict)

    @property
    def valid_at_range(self) -> tuple[datetime, datetime]:
        times = [record.valid_at for record in self.records]
        return min(times), max(times)


def _http_get(url: str, *, timeout: float = 60.0) -> tuple[bytes, dict[str, str]]:
    """GET with bounded retries. Provider HTTP status maps onto the run machine."""

    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    last_error: Exception | None = None

    for attempt in range(_MAX_ATTEMPTS):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
                return response.read(), dict(response.headers)
        except urllib.error.HTTPError as error:
            status = status_for_http_error(error.code)
            # Auth and quota failures are decisions, not transient noise.
            if status in (RunStatus.AUTH_REQUIRED, RunStatus.RATE_LIMITED):
                raise AcquisitionError(
                    f"provider returned HTTP {error.code}",
                    status,
                    "PROVIDER_AUTH" if status is RunStatus.AUTH_REQUIRED else "PROVIDER_RATE_LIMIT",
                ) from error
            last_error = error
        except (urllib.error.URLError, TimeoutError) as error:
            last_error = error

        if attempt < len(_BACKOFF_SECONDS):
            time.sleep(_BACKOFF_SECONDS[attempt])

    raise AcquisitionError(
        f"provider unreachable after {_MAX_ATTEMPTS} attempts: {type(last_error).__name__}",
        RunStatus.FAILED,
        "PROVIDER_UNREACHABLE",
    )


def _parse_json(raw: bytes, what: str) -> object:
    import json

    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as error:
        raise AcquisitionError(f"{what} was not valid JSON", RunStatus.FAILED, "PROVIDER_MALFORMED") from error


def fetch_provider_issue(model: str = DEFAULT_MODEL) -> ProviderIssue:
    """Read the model's own cycle metadata. This is where ``issued_at`` comes from."""

    meta_id = MODEL_META_IDS.get(model)
    if meta_id is None:
        raise AcquisitionError(
            f"model {model!r} is not in the approved model registry",
            RunStatus.FAILED,
            "MODEL_NOT_APPROVED",
        )

    raw, _ = _http_get(MODEL_META_URL.format(meta_id=meta_id), timeout=30.0)
    document = _parse_json(raw, "model metadata")
    if not isinstance(document, dict):
        raise AcquisitionError("model metadata was not an object", RunStatus.FAILED, "PROVIDER_MALFORMED")

    try:
        issued_at = datetime.fromtimestamp(int(document["last_run_initialisation_time"]), timezone.utc)
        available_at = datetime.fromtimestamp(int(document["last_run_availability_time"]), timezone.utc)
        update_interval = int(document["update_interval_seconds"])
        temporal_resolution = int(document["temporal_resolution_seconds"])
    except (KeyError, TypeError, ValueError) as error:
        raise AcquisitionError(
            "model metadata is missing the run-cycle timestamps",
            RunStatus.FAILED,
            "PROVIDER_MALFORMED",
        ) from error

    if available_at < issued_at:
        raise AcquisitionError(
            "provider reported availability before issue; refusing to violate the leakage boundary",
            RunStatus.FAILED,
            "PROVIDER_TIMELINE",
        )

    return ProviderIssue(
        model=model,
        issued_at=issued_at,
        information_available_at=available_at,
        update_interval_seconds=update_interval,
        temporal_resolution_seconds=temporal_resolution,
        meta_hash=sha256_hex(raw),
    )


def build_request(model: str, forecast_days: int) -> tuple[str, dict[str, object]]:
    """Return the request URL and the parameters used for the fingerprint."""

    centroids = pilot_cell_centroids()
    params: dict[str, object] = {
        "latitude": ",".join(f"{lat:.6f}" for _, lat, _ in centroids),
        "longitude": ",".join(f"{lon:.6f}" for _, _, lon in centroids),
        "hourly": ",".join(HOURLY_VARIABLES),
        "models": model,
        "forecast_days": forecast_days,
        "timezone": "UTC",
        "timeformat": "unixtime",
    }
    url = f"{FORECAST_URL}?{urllib.parse.urlencode(params)}"
    return url, params


def feature_units() -> dict[str, str]:
    """Units declared for every feature, including the provenance columns."""

    return {
        "temperature_2m": "degC",
        "apparent_temperature": "degC",
        "relative_humidity_2m": "percent",
        "precipitation": "mm",
        "rain": "mm",
        "wind_speed_10m": "km/h",
        "wind_gusts_10m": "km/h",
        "cloud_cover": "percent",
        "surface_pressure": "hPa",
        "weather_code": "wmo_code",
        "provider_grid_latitude": "degrees_north",
        "provider_grid_longitude": "degrees_east",
        "forecast_lead_seconds": "s",
    }


def acquire(model: str = DEFAULT_MODEL, forecast_days: int = 2) -> AcquisitionResult:
    """Fetch one forecast cycle for all 94 pilot cells and adapt it to the contract."""

    if not 1 <= forecast_days <= 16:
        raise AcquisitionError("forecast_days must be between 1 and 16", RunStatus.FAILED, "BAD_REQUEST")

    issue = fetch_provider_issue(model)
    url, params = build_request(model, forecast_days)
    fingerprint = request_fingerprint("GET", FORECAST_URL, params)

    raw, _headers = _http_get(url)
    retrieved_at = datetime.now(timezone.utc)
    if retrieved_at < issue.information_available_at:
        # Clock skew between us and the provider must never manufacture a record
        # that looks retrieved before it was knowable.
        retrieved_at = issue.information_available_at

    payload = _parse_json(raw, "forecast payload")
    locations = payload if isinstance(payload, list) else [payload]

    centroids = pilot_cell_centroids()
    if len(locations) != len(centroids):
        raise AcquisitionError(
            f"provider returned {len(locations)} locations for {len(centroids)} pilot cells",
            RunStatus.PARTIAL,
            "PROVIDER_COVERAGE",
        )

    digest = artifact_hash(raw)
    provider_version = f"v1/{model}"
    source_version = f"{model}@{issue.issued_at.strftime('%Y-%m-%dT%H:%M:%SZ')}"
    units = feature_units()

    records: list[TemporalFeatureRecord] = []
    grid_points: dict[str, tuple[float, float]] = {}

    for (cell, _lat, _lon), location in zip(centroids, locations, strict=True):
        if not isinstance(location, dict):
            raise AcquisitionError("provider location entry was not an object", RunStatus.FAILED, "PROVIDER_MALFORMED")
        hourly = location.get("hourly")
        if not isinstance(hourly, dict) or "time" not in hourly:
            raise AcquisitionError(
                f"provider returned no hourly series for cell {cell}", RunStatus.PARTIAL, "PROVIDER_COVERAGE"
            )

        grid_lat = float(location["latitude"])
        grid_lon = float(location["longitude"])
        grid_key = f"{grid_lat:.6f},{grid_lon:.6f}"
        grid_points[grid_key] = (grid_lat, grid_lon)

        timestamps = hourly["time"]
        for index, epoch in enumerate(timestamps):
            valid_at = datetime.fromtimestamp(int(epoch), timezone.utc)

            features: dict[str, bool | int | float | str | None] = {
                "provider_grid_latitude": grid_lat,
                "provider_grid_longitude": grid_lon,
                "forecast_lead_seconds": (valid_at - issue.issued_at).total_seconds(),
            }
            for variable in HOURLY_VARIABLES:
                series = hourly.get(variable)
                value = series[index] if isinstance(series, list) and index < len(series) else None
                features[variable] = value

            records.append(
                TemporalFeatureRecord(
                    record_id=record_id_for(
                        [
                            DATASET_ID,
                            PROVIDER,
                            provider_version,
                            cell,
                            valid_at.isoformat(),
                            issue.issued_at.isoformat(),
                        ]
                    ),
                    dataset_id=DATASET_ID,
                    dataset_version=DATASET_VERSION,
                    entity_id=f"omgrid:{grid_key}",
                    zone_id=cell,
                    event_time=valid_at,
                    issued_at=issue.issued_at,
                    information_available_at=issue.information_available_at,
                    valid_at=valid_at,
                    retrieved_at=retrieved_at,
                    source=FORECAST_URL,
                    source_version=source_version,
                    evidence_class=EVIDENCE_CLASS,
                    features=features,
                    feature_units=units,
                )
            )

    if not records:
        raise AcquisitionError("provider returned no forecast steps", RunStatus.FAILED, "PROVIDER_EMPTY")

    return AcquisitionResult(
        issue=issue,
        records=records,
        raw_payload=raw,
        artifact_hash=digest,
        request_fingerprint=fingerprint,
        request_url=FORECAST_URL,
        retrieved_at=retrieved_at,
        provider_version=provider_version,
        grid_points=grid_points,
    )


def unit_set_id(units: dict[str, str]) -> str:
    """Content address for a unit declaration, stored once per dataset version."""

    return sha256_hex(canonical_json(units).encode("utf-8"))
