import os
import subprocess
from typing import Optional

def run_c_dispatch_engine(orders_path: str, partners_path: str) -> Optional[str]:
    """
    Wrapper to call the C dispatch engine binary.
    If the binary is missing, returns None.
    """
    binary_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../c/dispatch-engine/dispatch_engine"))
    
    if not os.path.exists(binary_path):
        return None
        
    try:
        result = subprocess.run([binary_path, orders_path, partners_path], capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error calling C engine: {e}")
        return None
