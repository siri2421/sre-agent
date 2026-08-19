import os
import sys
import time
import subprocess
import re
import urllib.request
import urllib.parse

def log(msg):
    print(f"\033[1;34m[TEST_RUNNER]\033[0m {msg}")

def run_cmd(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result

def main():
    log("Starting Unified SRE Investigator (Network Domain) Integration Test Scenario")
    
    # 1. Inject the chaos network policy to create the failure
    log("Applying restrictive NetworkPolicy 'chaos-block-checkoutservice' in default namespace...")
    policy_manifest = """
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: chaos-block-checkoutservice
  namespace: default
spec:
  podSelector:
    matchLabels:
      app: checkoutservice
  policyTypes:
  - Ingress
  - Egress
"""
    # Write temporary file to apply
    with open("temp_policy.yaml", "w") as f:
        f.write(policy_manifest)
        
    res = run_cmd("kubectl apply -f temp_policy.yaml")
    if res.returncode != 0:
        log(f"❌ Failed to apply NetworkPolicy: {res.stderr}")
        sys.exit(1)
    log("✅ NetworkPolicy successfully applied.")
    os.remove("temp_policy.yaml")

    # 2. Start the SRE Supervisor with the network alert
    alert_payload = "CRITICAL ALERT: NetworkPolicy 'chaos-block-checkoutservice' in namespace default is dropping ingress/egress connections"
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
            # e.g., "http://127.0.0.1:8000/callback/2c6a0c0a-..."
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
            sys.exit(1)

        # Read the remaining stdout until the process finishes
        for line in proc.stdout:
            print(line, end="")
            
        proc.wait()
        
        # 5. Assert that the NetworkPolicy has been deleted by the remediation_executor
        log("Verifying that the NetworkPolicy 'chaos-block-checkoutservice' was successfully deleted...")
        check_res = run_cmd("kubectl get networkpolicy chaos-block-checkoutservice -n default")
        if "NotFound" in check_res.stderr or check_res.returncode != 0:
            log("✅ SUCCESS: NetworkPolicy 'chaos-block-checkoutservice' has been deleted and traffic is restored.")
        else:
            log("❌ FAILED: NetworkPolicy 'chaos-block-checkoutservice' is still present in the cluster.")
            sys.exit(1)

    except KeyboardInterrupt:
        log("Interrupted. Cleaning up...")
        proc.kill()
        run_cmd("kubectl delete networkpolicy chaos-block-checkoutservice -n default")
        sys.exit(0)
    except Exception as e:
        log(f"❌ Error during test execution: {e}")
        proc.kill()
        run_cmd("kubectl delete networkpolicy chaos-block-checkoutservice -n default")
        sys.exit(1)

if __name__ == "__main__":
    main()
