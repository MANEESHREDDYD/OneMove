from onemove_intelligence.data_quality.checks import run_all_checks

def test_run_all_checks():
    assert run_all_checks() is True
