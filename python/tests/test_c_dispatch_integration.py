import os
import pytest
from onemove_intelligence.integrations.c_dispatch import run_c_dispatch_engine

def test_c_dispatch_optional_integration():
    """
    Tests the C integration wrapper. If the C binary is not compiled, skips the test gracefully.
    """
    orders_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../c/dispatch-engine/data/sample_orders.csv"))
    partners_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../c/dispatch-engine/data/sample_partners.csv"))
    
    output = run_c_dispatch_engine(orders_path, partners_path)
    
    if output is None:
        pytest.skip("C dispatch_engine binary not found. Skipping optional integration test.")
    else:
        assert "Successfully dispatched" in output
