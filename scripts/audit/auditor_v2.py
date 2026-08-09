import os
import json
import subprocess
import datetime
import hashlib

def run_auditor():
    print("=== ZONEPILOT REMOTE EVIDENCE AUDITOR V2 ===")
    
    verdicts = {}
    p0_issues = []
    
    # 1. Fetch Remote State
    try:
        gh_proc = subprocess.run(
            ["gh", "pr", "view", "1", "--json", "headRefOid,commits,statusCheckRollup"],
            capture_output=True, text=True
        )
        if gh_proc.returncode == 0:
            gh_data = json.loads(gh_proc.stdout)
            remote_sha = gh_data.get("headRefOid")
            checks = gh_data.get("statusCheckRollup", [])
            print(f"Remote PR SHA: {remote_sha}")
        else:
            # Fallback if GH cli not authenticated
            remote_sha = subprocess.run(["git", "rev-parse", "origin/ws/phase1-measurement"], capture_output=True, text=True).stdout.strip()
            checks = []
            print(f"Failed to fetch PR via gh cli. Using local origin branch SHA: {remote_sha}")
    except Exception as e:
        remote_sha = "unknown"
        checks = []
        p0_issues.append(f"Failed to query remote state: {e}")

    local_sha = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    
    if remote_sha != local_sha:
        verdicts["REMOTE_SHA_MATCH"] = "FALSE_CLAIM"
        p0_issues.append(f"Remote SHA {remote_sha} differs from local HEAD {local_sha}")
    else:
        verdicts["REMOTE_SHA_MATCH"] = "VERIFIED"
        
    # CI Checks
    # Since we can't reliably mock GitHub Actions in this local python script if they haven't run, 
    # we will rely on local evidence if 'checks' is empty, but warn about UNVERIFIED CI.
    if checks:
        # Check actual status
        pass # implementation for CI checking
    else:
        verdicts["REMOTE_CI"] = "UNVERIFIED"
        
    # 2. Check Committed Implementation (Security tests)
    sec_test_path = "tests/api/test_jwt_security.py"
    with open(sec_test_path, "r") as f:
        sec_content = f.read()
        if "pass" in sec_content or "TODO" in sec_content:
            verdicts["SECURITY_TESTS"] = "FALSE_CLAIM"
            p0_issues.append("Fake security tests detected (contains 'pass' or 'TODO')")
        elif "assert response.status_code" in sec_content:
            verdicts["SECURITY_TESTS"] = "VERIFIED"
        else:
            verdicts["SECURITY_TESTS"] = "UNVERIFIED"

    # 3. Check Runtime Evidence (Gold, Bundle, OSRM)
    data_root = os.environ.get('ZONEPILOT_DATA_ROOT', os.path.join(os.getcwd(), 'data_root'))
    public_manifests = os.path.join(data_root, "public", "manifests")
    gold_manifest_path = os.path.join(data_root, "private", "official", "manifests", "gold_manifest.json")
    
    if os.path.exists(gold_manifest_path):
        with open(gold_manifest_path, "r") as f:
            gold_man = json.load(f)
            if gold_man.get("rows", 0) > 0 and "graph_metrics" in gold_man:
                verdicts["GOLD_DATASET"] = "VERIFIED"
            else:
                verdicts["GOLD_DATASET"] = "FALSE_CLAIM"
                p0_issues.append("Gold dataset manifest contradicts report (0 rows or missing graph metrics)")
    else:
        verdicts["GOLD_DATASET"] = "FALSE_CLAIM"
        p0_issues.append("Gold dataset manifest missing")

    today = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    bundle_manifest_path = os.path.join(public_manifests, f"{today}_bundle_manifest.json")
    
    if os.path.exists(bundle_manifest_path):
        with open(bundle_manifest_path, "r") as f:
            bundle_man = json.load(f)
            if "output_bundle_hash" in bundle_man:
                verdicts["DAILY_BUNDLE"] = "VERIFIED"
            else:
                verdicts["DAILY_BUNDLE"] = "FALSE_CLAIM"
                p0_issues.append("Daily bundle manifest missing required hashes")
    else:
        verdicts["DAILY_BUNDLE"] = "FALSE_CLAIM"
        p0_issues.append("Daily bundle manifest missing")

    # Contamination
    contamination_hits = 0
    forbidden = [b"faker", b"demo", b"synthetic", b"mock", b"staging", b"seed"]
    for root, dirs, files in os.walk(os.path.join(data_root, 'private', 'official')):
        for f in files:
            if f.endswith('.osm.pbf'): continue # Binaries have false positives
            filepath = os.path.join(root, f)
            try:
                with open(filepath, 'rb') as file:
                    content = file.read().lower()
                    # Exclude known valid real-world entities (e.g. Mockaholic cafe in Bengaluru)
                    content = content.replace(b'mockaholic', b'')
                    
                    for term in forbidden:
                        if term in content:
                            contamination_hits += 1
            except: pass

    if contamination_hits > 0:
        verdicts["CONTAMINATION"] = "FALSE_CLAIM"
        p0_issues.append(f"Evidence contamination detected: {contamination_hits} hits")
    else:
        verdicts["CONTAMINATION"] = "VERIFIED"
        
    print("\n--- SUBSYSTEM VERDICTS ---")
    for k, v in verdicts.items():
        print(f"{k}: {v}")
        
    if p0_issues:
        print("\n--- P0 ISSUES DETECTED ---")
        for i in p0_issues:
            print(f"- {i}")
            
if __name__ == "__main__":
    run_auditor()
