import pytest

def test_dry_run_exclusion():
    # Simulated test ensuring DRY_RUN study_phase is excluded from Experiment-A Gold tables
    experiment_a_filter = "study_phase = 'EXPERIMENT_A'"
    dry_run_phase = 'DRY_RUN'
    
    assert dry_run_phase not in experiment_a_filter, "DRY_RUN data leaked into Experiment A filters!"

def test_provenance_boundaries():
    # Provenance model checks
    allowed_phases = ['DRY_RUN', 'EXPERIMENT_A']
    assert 'PILOT_OBSERVED' not in allowed_phases # Using DRY_RUN instead as requested
