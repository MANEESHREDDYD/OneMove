"""Deterministic point-in-time joins with an explicit availability cutoff."""

from __future__ import annotations

from enum import Enum
from typing import Sequence

from pydantic import Field, model_validator

from services.temporal.contracts import PointInTimeQuery, StrictContract, TemporalFeatureRecord


class JoinStatus(str, Enum):
    MATCHED = "MATCHED"
    NO_MATCH = "NO_MATCH"


class PointInTimeJoinResult(StrictContract):
    query_id: str = Field(min_length=1)
    status: JoinStatus
    feature_record: TemporalFeatureRecord | None = None

    @model_validator(mode="after")
    def status_matches_payload(self) -> "PointInTimeJoinResult":
        if self.status is JoinStatus.MATCHED and self.feature_record is None:
            raise ValueError("matched joins require a feature record")
        if self.status is JoinStatus.NO_MATCH and self.feature_record is not None:
            raise ValueError("unmatched joins must not include a feature record")
        return self


def point_in_time_join(
    queries: Sequence[PointInTimeQuery],
    feature_records: Sequence[TemporalFeatureRecord],
) -> tuple[PointInTimeJoinResult, ...]:
    """Select the newest eligible feature version for each query.

    A record is eligible only if it matches the entity and zone, its information
    was available by the decision time, and its validity timestamp is no later
    than the query's validity cutoff. The explicit cutoff supports both current
    state joins and forecasts for a future target time without weakening the
    information-availability invariant.
    """

    query_ids = [query.query_id for query in queries]
    if len(query_ids) != len(set(query_ids)):
        raise ValueError("query_id values must be unique")

    results: list[PointInTimeJoinResult] = []
    for query in queries:
        eligible = [
            record
            for record in feature_records
            if record.entity_id == query.entity_id
            and record.zone_id == query.zone_id
            and record.information_available_at <= query.decision_time
            and record.valid_at <= query.validity_cutoff
            and (query.dataset_id is None or record.dataset_id == query.dataset_id)
            and (query.dataset_version is None or record.dataset_version == query.dataset_version)
        ]

        if not eligible:
            results.append(PointInTimeJoinResult(query_id=query.query_id, status=JoinStatus.NO_MATCH))
            continue

        selected = max(
            eligible,
            key=lambda record: (
                record.valid_at,
                record.information_available_at,
                record.issued_at,
                record.retrieved_at,
                record.record_id,
            ),
        )
        if selected.information_available_at > query.decision_time:
            raise AssertionError("point-in-time join selected information from the future")
        results.append(
            PointInTimeJoinResult(
                query_id=query.query_id,
                status=JoinStatus.MATCHED,
                feature_record=selected,
            )
        )

    return tuple(results)
