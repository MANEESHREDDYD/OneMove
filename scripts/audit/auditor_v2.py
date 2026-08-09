import os
import json
import subprocess
import datetime
import hashlib
import sys

def run_auditor():
    print("=== ZONEPILOT REMOTE EVIDENCE AUDITOR V2 ===")
    
    verdicts = {}
    p0_issues = []
    
    data_root = os.environ.get('ZONEPILOT_DATA_ROOT', os.path.join(os.getcwd(), 'data_root'))
    
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
        
    # CI Checks Verification
    required_workflows = ["Node.js CI", "SQL Quality", "Polyglot CI", "Python CI", "ZonePilot Release Validation"]
    
    if checks:
        # Check actual status
        missing = []
        failed = []
        found_workflows = [c.get("name") or c.get("context") for c in checks]
        for req in required_workflows:
            req_check = next((c for c in checks if (c.get("name") == req or c.get("context") == req)), None)
            if not req_check:
                missing.append(req)
                continue
            
            status = req_check.get("status")
            conclusion = req_check.get("conclusion")
            if status != "COMPLETED" or conclusion != "SUCCESS":
                failed.append(f"{req} (status={status}, conclusion={conclusion})")
        
        if missing or failed:
            verdicts["REMOTE_CI"] = "FALSE_CLAIM"
            p0_issues.append(f"Missing CI checks: {missing}")
            p0_issues.append(f"Failed CI checks: {failed}")
        else:
            verdicts["REMOTE_CI"] = "VERIFIED"
    else:
        verdicts["REMOTE_CI"] = "UNVERIFIED"
        p0_issues.append("No CI checks found in GitHub API response.")

    # 2. Check Committed Implementation (Security tests)
    sec_test_path = "tests/api/test_jwt_security.py"
    with open(sec_test_path, "r") as f:
        sec_content = f.read()
        if "pass" in sec_content or "TODO" in sec_content:
            verdicts["SECURITY_TESTS"] = "FALSE_CLAIM"
            p0_issues.append("Fake security tests detected (contains 'pass' or 'TODO')")
        else:
            # We must use actual executed Pytest result.
            # For the local script we'll parse a pytest report if it exists.
            report_path = "pytest_report.json"
            if os.path.exists(report_path):
                with open(report_path, "r") as rep_f:
                    rep = json.load(rep_f)
                    if rep.get("summary", {}).get("failed", 0) > 0:
                        verdicts["SECURITY_TESTS"] = "FALSE_CLAIM"
                        p0_issues.append("Security tests failed in executed pytest report.")
                    else:
                        verdicts["SECURITY_TESTS"] = "VERIFIED"
            else:
                verdicts["SECURITY_TESTS"] = "UNVERIFIED"

    # 3. Check Runtime Evidence (Gold, Bundle, OSRM)
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

    # 4. Daily Bundle check with recomputing hash
    today = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    public_manifests = os.path.join(data_root, "public", "manifests")
    bundle_manifest_path = os.path.join(public_manifests, f"{today}_bundle_manifest.json")
    
    if os.path.exists(bundle_manifest_path):
        with open(bundle_manifest_path, "r") as f:
            bundle_man = json.load(f)
            expected_hash = bundle_man.get("output_bundle_hash")
            
            # Recompute
            actual_bundle_path = os.path.join(data_root, "private", "official", "checkpoints", f"{today}_bundle.json")
            if os.path.exists(actual_bundle_path):
                with open(actual_bundle_path, "r") as bf:
                    actual_bundle = json.load(bf)
                bundle_str = json.dumps(actual_bundle, sort_keys=True)
                computed_hash = hashlib.sha256(bundle_str.encode('utf-8')).hexdigest()
                
                if computed_hash == expected_hash:
                    verdicts["DAILY_BUNDLE"] = "VERIFIED"
                else:
                    verdicts["DAILY_BUNDLE"] = "FALSE_CLAIM"
                    p0_issues.append(f"Daily bundle hash mismatch! Expected {expected_hash}, got {computed_hash}")
            else:
                verdicts["DAILY_BUNDLE"] = "FALSE_CLAIM"
                p0_issues.append("Daily bundle output file missing.")
    else:
        verdicts["DAILY_BUNDLE"] = "FALSE_CLAIM"
        p0_issues.append("Daily bundle manifest missing")

    # 5. OSRM smoke evidence
    osrm_evidence = os.path.join(data_root, "private", "official", "manifests", "osrm_smoke_manifest.json")
    if os.path.exists(osrm_evidence):
        with open(osrm_evidence, "r") as f:
            ev = json.load(f)
            if ev.get("distance_m", 0) > 0 and ev.get("null_cells", 1) == 0:
                verdicts["OSRM_SMOKE"] = "VERIFIED"
            else:
                verdicts["OSRM_SMOKE"] = "FALSE_CLAIM"
                p0_issues.append("OSRM smoke manifest invalid or null cells present.")
    else:
        verdicts["OSRM_SMOKE"] = "FALSE_CLAIM"
        p0_issues.append("OSRM smoke evidence missing.")

    # 6. Contamination
    contamination_hits = 0
    forbidden = [b"faker", b"demo", b"synthetic", b"mock", b"staging", b"seed"]
    for root, dirs, files in os.walk(os.path.join(data_root, 'private', 'official')):
        for f in files:
            if f.endswith('.osm.pbf'): continue 
            filepath = os.path.join(root, f)
            try:
                with open(filepath, 'rb') as file:
                    content = file.read().lower()
                    # Check structured evidence class first if JSON
                    if f.endswith(".json") or f.endswith(".geojson"):
                        try:
                            jdata = json.loads(content.decode("utf-8"))
                            ev_class = jdata.get("evidence_class", "")
                            if ev_class in ["TEST_ONLY", "STAGING_DO_NOT_USE", "DEMO_SYNTHETIC"]:
                                contamination_hits += 1
                        except Exception:
                            pass

                    # String scanning secondary
                    content = content.replace(b'mockaholic', b'')
                    for term in forbidden:
                        if term in content:
                            contamination_hits += 1
            except Exception:
                pass

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
        sys.exit(1)
            
if __name__ == "__main__":
    run_auditor()
