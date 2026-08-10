from services.collectors.dq import check_no_staging_contamination, check_temporal_semantics, to_ts


def test_dq_temporal_case_a():
    """
    Case A:
    issued 09:00
    information_available_at 09:01
    decision 09:05
    valid_at 10:00
    -> PASS.
    """
    records = [{
        "issued_at": "2026-08-09T09:00:00Z",
        "information_available_at": "2026-08-09T09:01:00Z",
        "valid_at": "2026-08-09T10:00:00Z"
    }]
    decision_time_ts = to_ts("2026-08-09T09:05:00Z")
    assert check_temporal_semantics(records, decision_time_ts) is True

def test_dq_temporal_case_b():
    """
    Case B:
    issued 09:10
    information_available_at 09:10
    decision 09:05
    valid_at 10:00
    -> FAIL leakage.
    """
    records = [{
        "issued_at": "2026-08-09T09:10:00Z",
        "information_available_at": "2026-08-09T09:10:00Z",
        "valid_at": "2026-08-09T10:00:00Z"
    }]
    decision_time_ts = to_ts("2026-08-09T09:05:00Z")
    assert check_temporal_semantics(records, decision_time_ts) is False

def test_dq_temporal_case_c():
    """
    Case C:
    historical observation event 09:00
    arrives 09:20
    decision 09:10
    -> unavailable at decision (fails check if tested for use at 09:10).
    """
    records = [{
        "event_time": "2026-08-09T09:00:00Z",
        "information_available_at": "2026-08-09T09:20:00Z"
    }]
    decision_time_ts = to_ts("2026-08-09T09:10:00Z")
    assert check_temporal_semantics(records, decision_time_ts) is False

def test_dq_temporal_case_d():
    """
    Case D:
    late-arriving data used for later replay only
    -> permitted when replay information cutoff >= arrival.
    arrival: 09:20. Replay cutoff: 09:30.
    """
    records = [{
        "event_time": "2026-08-09T09:00:00Z",
        "information_available_at": "2026-08-09T09:20:00Z"
    }]
    decision_time_ts = to_ts("2026-08-09T09:30:00Z")
    assert check_temporal_semantics(records, decision_time_ts) is True

def test_dq_contamination_metadata():
    # TEST_ONLY should fail
    records_fail = [{"evidence_class": "TEST_ONLY", "name": "real data"}]
    assert check_no_staging_contamination(records_fail) is False
    
    # STAGING_DO_NOT_USE should fail
    records_fail2 = [{"evidence_class": "STAGING_DO_NOT_USE"}]
    assert check_no_staging_contamination(records_fail2) is False
    
    # Clean data should pass
    records_pass = [{"evidence_class": "PUBLIC_GEOGRAPHIC", "name": "BTM Layout"}]
    assert check_no_staging_contamination(records_pass) is True
