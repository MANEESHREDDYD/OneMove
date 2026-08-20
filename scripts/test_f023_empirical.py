import asyncio
import httpx
import subprocess
import time
import sys

async def run_empirical_test():
    print("Starting instance A on port 8001...")
    proc_a = subprocess.Popen(["python", "-m", "uvicorn", "services.api.main:app", "--port", "8001"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    print("Starting instance B on port 8002...")
    proc_b = subprocess.Popen(["python", "-m", "uvicorn", "services.api.main:app", "--port", "8002"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    print("Waiting for instances to boot...")
    await asyncio.sleep(5)
    
    async with httpx.AsyncClient() as client:
        # We assume ZONEPILOT_AUTH_RATE_LIMIT_PER_MINUTE=10 for this test.
        # Sending 5 to A, 5 to B, then 11th to either
        
        headers = {"Authorization": "Bearer testtoken", "X-Forwarded-For": "10.0.0.1"}
        url_a = "http://localhost:8001/api/v1/auth/login"
        url_b = "http://localhost:8002/api/v1/auth/login"
        
        print("Sending 5 requests to Instance A...")
        for i in range(5):
            res = await client.post(url_a, headers=headers)
            print(f"A {i+1}: {res.status_code}")
            
        print("Sending 5 requests to Instance B...")
        for i in range(5):
            res = await client.post(url_b, headers=headers)
            print(f"B {i+1}: {res.status_code}")
            
        print("Sending 11th request to Instance A (should be 429)...")
        res = await client.post(url_a, headers=headers)
        print(f"11th: {res.status_code}")
        if res.status_code == 429:
            print("SUCCESS: Rate limit was enforced across instances.")
        else:
            print(f"FAILURE: Expected 429, got {res.status_code}")
            
    print("Cleaning up...")
    proc_a.terminate()
    proc_b.terminate()

if __name__ == "__main__":
    asyncio.run(run_empirical_test())
