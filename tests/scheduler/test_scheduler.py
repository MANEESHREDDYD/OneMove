import uuid

from services.api.scheduler import job_midnight, job_midnight_five


def test_midnight_job_execution_and_idempotency():
    date_str = f"2026-08-{uuid.uuid4().hex[:4]}"

    # First execution
    res1 = job_midnight(date_str)
    assert res1["status"] == "SUCCESS"
    assert res1.get("idempotent_replay") is False

    # Rerun on same date must be idempotent
    res2 = job_midnight(date_str)
    assert res2["status"] == "SUCCESS"
    assert res2.get("idempotent_replay") is True


def test_midnight_five_execution_and_idempotency():
    date_str = f"2026-08-{uuid.uuid4().hex[:4]}"

    # First execution
    res1 = job_midnight_five(date_str)
    assert res1["status"] == "SUCCESS"
    assert res1.get("idempotent_replay") is False

    # Rerun on same date must be idempotent
    res2 = job_midnight_five(date_str)
    assert res2["status"] == "SUCCESS"
    assert res2.get("idempotent_replay") is True
