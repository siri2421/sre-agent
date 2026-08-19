import os
import sys
import time
import subprocess
import re
import urllib.request
import urllib.parse
import json

def log(msg):
    print(f"\033[1;32m[TEST_RUNNER]\033[0m {msg}")

def run_cmd(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result

def main():
    log("Starting GKE Service Routing Triage Integration Test Scenario")
    
    # 1. Trigger the chaos simulation locally using kubectl
    log("Triggering local chaos simulation on GKE service routing...")
    patch_res = run_cmd("kubectl patch service checkoutservice -p '{\"spec\":{\"selector\":{\"app\":\"broken-selector\"}}}'")
    if patch_res.returncode != 0:
        log(f"❌ Failed to patch service selector: {patch_res.stderr}")
        sys.exit(1)
    log("✅ Chaos simulation successfully triggered.")

    # Verify that selector is broken locally
    log("Verifying broken service selector on checkoutservice Service...")
    svc_res = run_cmd("kubectl get service checkoutservice -o jsonpath='{.spec.selector.app}'")
    if svc_res.stdout.strip() != "broken-selector":
        log(f"❌ Service selector is not broken: '{svc_res.stdout.strip()}'")
        # Cleanup
        run_cmd("kubectl patch service checkoutservice -p '{\"spec\":{\"selector\":{\"app\":\"checkoutservice\"}}}'")
        sys.exit(1)
    log("✅ Confirmed checkoutservice selector is broken (app=broken-selector).")

    # 2. Start the SRE Supervisor with the network alert
    alert_payload = "CRITICAL ALERT: GKE Service 'checkoutservice' ingress routing in namespace default is dropping connections. Traffic cannot reach healthy pods."
    log(f"Spawning SRE Supervisor process with alert: '{alert_payload}'")
    
    # Run the supervisor using Python in unbuffered mode
    env = os.environ.copy()
    env["GOOGLE_API_USE_CLIENT_CERTIFICATE"] = "false"
    env["GOOGLE_API_USE_MTLS_ENDPOINT"] = "never"
    cmd = [".venv/bin/python", "-u", "-m", "app.sre_supervisor", "--alert", alert_payload]
    proc = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)

    session_id = None
    hitl_detected = False
    
    # 3. Read stdout line by line to detect HITL safety gate activation
    try:
        for line in proc.stdout:
            print(line, end="") # Forward logs to console
            
            # Extract session ID from the callback URL example in logs
            match = re.search(r"http://127.0.0.1:8000/callback/([a-f0-9\-]+)\?decision=APPROVED", line)
            if match:
                session_id = match.group(1)
                log(f"Detected HITL Session ID: {session_id}")
                
            if "Awaiting operator callback" in line:
                hitl_detected = True
                break
                
        if not hitl_detected or not session_id:
            log("❌ HITL Safety Gate was not activated or session ID was not found.")
            proc.kill()
            # Restore selector
            run_cmd("kubectl patch service checkoutservice -p '{\"spec\":{\"selector\":{\"app\":\"checkoutservice\"}}}'")
            sys.exit(1)
            
        # 4. Trigger the HITL approval callback
        log(f"Approving remediation action for session {session_id}...")
        url = f"http://127.0.0.1:8000/callback/{session_id}?decision=APPROVED"
        req = urllib.request.Request(url, method="POST")
        try:
            with urllib.request.urlopen(req) as response:
                resp_data = response.read().decode('utf-8')
                log(f"Callback Response: {resp_data}")
        except Exception as e:
            log(f"❌ Callback request failed: {e}")
            proc.kill()
            # Restore selector
            run_cmd("kubectl patch service checkoutservice -p '{\"spec\":{\"selector\":{\"app\":\"checkoutservice\"}}}'")
            sys.exit(1)

        # Read the remaining stdout until the process finishes
        for line in proc.stdout:
            print(line, end="")
            
        proc.wait()
        
        # 5. Assert that the service selector has been restored by the remediation_executor
        log("Verifying that the Service selector of 'checkoutservice' was restored...")
        svc_res = run_cmd("kubectl get service checkoutservice -o jsonpath='{.spec.selector.app}'")
        if svc_res.stdout.strip() == "checkoutservice":
            log("✅ SUCCESS: Service selector of 'checkoutservice' has been restored and traffic is restored.")
        else:
            log(f"❌ FAILED: Service selector is still: '{svc_res.stdout.strip()}'")
            sys.exit(1)

    except KeyboardInterrupt:
        log("Interrupted. Cleaning up...")
        proc.kill()
        run_cmd("kubectl patch service checkoutservice -p '{\"spec\":{\"selector\":{\"app\":\"checkoutservice\"}}}'")
        sys.exit(0)
    except Exception as e:
        log(f"❌ Error during test execution: {e}")
        proc.kill()
        run_cmd("kubectl patch service checkoutservice -p '{\"spec\":{\"selector\":{\"app\":\"checkoutservice\"}}}'")
        sys.exit(1)

if __name__ == "__main__":
    main()
