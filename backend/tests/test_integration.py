"""
Qentis Integration Tests
========================
Tests the full flow across multiple services running together.
Run with: python tests/test_integration.py

Requirements:
- All services must be running: docker-compose up
- Run from the backend/ folder
"""

import requests
import sys

BASE_AUTH         = "http://localhost:8001"
BASE_INSTITUTION  = "http://localhost:8002"
BASE_ITEMS        = "http://localhost:8003"
BASE_BLOCKCHAIN   = "http://localhost:8004"
BASE_OUTPUT       = "http://localhost:8005"
BASE_VERIFICATION = "http://localhost:8006"
BASE_ADMIN        = "http://localhost:8007"

PASSED = []
FAILED = []


def log_pass(test_name):
    print(f"  ✅ PASS — {test_name}")
    PASSED.append(test_name)


def log_fail(test_name, reason):
    print(f"  ❌ FAIL — {test_name}: {reason}")
    FAILED.append(test_name)


def print_header(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


# ── Test 1: Health checks on all services ─────────────────────

def test_all_services_healthy():
    print_header("TEST 1 — All services health check")

    services = [
        ("User & Auth",       f"{BASE_AUTH}/api/auth/health/"),
        ("Institution",       f"{BASE_INSTITUTION}/api/institution/health/"),
        ("Item Registration", f"{BASE_ITEMS}/api/items/health/"),
        ("Blockchain",        f"{BASE_BLOCKCHAIN}/api/blockchain/health/"),
        ("Auth Output",       f"{BASE_OUTPUT}/api/output/health/"),
        ("Verification",      f"{BASE_VERIFICATION}/api/verification/health/"),
        ("Admin & Analytics", f"{BASE_ADMIN}/api/admin/health/"),
    ]

    for name, url in services:
        try:
            res = requests.get(url, timeout=5)
            if res.status_code == 200:
                log_pass(f"{name} is healthy")
            elif res.status_code == 404:
                log_pass(f"{name} is running (no health endpoint)")
            else:
                log_fail(f"{name} health check", f"Status {res.status_code}")
        except Exception as e:
            log_fail(f"{name} health check", f"Connection failed — {str(e)}")


# ── Test 2: User registration and login ───────────────────────

def test_auth_flow():
    print_header("TEST 2 — User registration and login flow")

    payload = {
        "name":             "Integration Test Issuer",
        "email":            "integration@qentis.cm",
        "password":         "IntTest2026!",
        "password_confirm": "IntTest2026!",
        "role":             "ISSUER",
        "institution_name": "Test University",
        "institution_type": "university"
    }

    try:
        res = requests.post(f"{BASE_AUTH}/api/auth/register/", json=payload)
        if res.status_code in [200, 201]:
            log_pass("Issuer registration")
        elif res.status_code == 400 and "email" in res.text:
            log_pass("Issuer registration (user already exists — expected on re-run)")
        else:
            log_fail("Issuer registration", f"Status {res.status_code} — {res.text[:100]}")
            return None
    except Exception as e:
        log_fail("Issuer registration", str(e))
        return None

    try:
        res = requests.post(f"{BASE_AUTH}/api/auth/login/", json={
            "email":    "integration@qentis.cm",
            "password": "IntTest2026!"
        })
        if res.status_code == 200:
            token = res.json().get("tokens", {}).get("access")
            if token:
                log_pass("Issuer login — JWT token received")
                return token
            else:
                log_fail("Issuer login", "No access token in response")
                return None
        else:
            log_fail("Issuer login", f"Status {res.status_code} — {res.text[:100]}")
            return None
    except Exception as e:
        log_fail("Issuer login", str(e))
        return None


# ── Test 3: Blockchain health and Ganache connection ──────────

def test_blockchain_ganache():
    print_header("TEST 3 — Blockchain service and Ganache connection")

    try:
        res = requests.get(f"{BASE_BLOCKCHAIN}/api/blockchain/health/")
        if res.status_code == 200:
            data = res.json()
            if data.get("ganache_connected"):
                log_pass("Blockchain service connected to Ganache")
            else:
                log_fail("Ganache connection", "ganache_connected is False")
        else:
            log_fail("Blockchain health check", f"Status {res.status_code}")
    except Exception as e:
        log_fail("Blockchain health check", str(e))


# ── Test 4: Store and verify a hash on blockchain ─────────────

def test_blockchain_store_and_verify():
    print_header("TEST 4 — Store and verify hash on blockchain")

    test_hash = "a" * 64

    try:
        res = requests.post(f"{BASE_BLOCKCHAIN}/api/blockchain/store/", json={
            "item_hash":   test_hash,
            "category":    "ACADEMIC",
            "issuer_id":   "integration-test-issuer",
            "issuer_name": "Test University"
        })
        if res.status_code in [200, 201]:
            log_pass("Hash stored on blockchain")
        elif res.status_code == 409:
            log_pass("Hash store (already exists — expected on re-run)")
        else:
            log_fail("Hash store", f"Status {res.status_code} — {res.text[:150]}")
            return None
    except Exception as e:
        log_fail("Hash store", str(e))
        return None

    try:
        res = requests.post(f"{BASE_BLOCKCHAIN}/api/blockchain/verify/", json={
            "item_hash": test_hash
        })
        if res.status_code == 200:
            data = res.json()
            if data.get("status") == "AUTHENTIC":
                log_pass("Hash verified on blockchain — AUTHENTIC")
                return test_hash
            else:
                log_fail("Hash verify", f"Expected AUTHENTIC got {data.get('status')}")
                return None
        else:
            log_fail("Hash verify", f"Status {res.status_code} — {res.text[:150]}")
            return None
    except Exception as e:
        log_fail("Hash verify", str(e))
        return None


# ── Test 5: Auth Output — generate QR and serial number ───────

def test_output_generation():
    print_header("TEST 5 — Auth Output Service — QR code and serial number")

    try:
        res = requests.post(f"{BASE_OUTPUT}/api/output/generate/", json={
            "item_id":   "integration-test-item-001",
            "item_hash": "b" * 64,
            "category":  "ACADEMIC",
            "issuer_id": "integration-test-issuer",
            "item_name": "BSc Computer Science"
        })
        if res.status_code in [200, 201]:
            data    = res.json()
            outputs = data.get("outputs", {})
            if "serial_number" in outputs:
                log_pass(f"Serial number generated — {outputs['serial_number']}")
            else:
                log_fail("Serial number generation", "No serial_number in response")
            if "qr_code_path" in outputs:
                log_pass("QR code generated")
            else:
                log_fail("QR code generation", "No qr_code_path in response")
            if "signature_path" in outputs:
                log_pass("Digital signature generated (ACADEMIC category)")
        else:
            log_fail("Output generation", f"Status {res.status_code} — {res.text[:150]}")
    except Exception as e:
        log_fail("Output generation", str(e))


# ── Test 6: Admin & Analytics — log and retrieve activity ─────

def test_admin_activity():
    print_header("TEST 6 — Admin & Analytics — activity logging")

    try:
        res = requests.post(f"{BASE_ADMIN}/api/admin/activity/create/", json={
            "event_type":  "REGISTRATION",
            "description": "Integration test — item registered",
            "actor_id":    "integration-test-issuer",
            "item_hash":   "c" * 64
        })
        if res.status_code in [200, 201]:
            log_pass("Activity log created")
        else:
            log_fail("Activity log creation",
                     f"Status {res.status_code} — {res.text[:100]}")
            return
    except Exception as e:
        log_fail("Activity log creation", str(e))
        return

    try:
        res = requests.get(f"{BASE_ADMIN}/api/admin/activity/")
        if res.status_code == 200:
            logs = res.json()
            if len(logs) > 0:
                log_pass(f"Activity logs retrieved — {len(logs)} entries found")
            else:
                log_fail("Activity log retrieval", "No logs found")
        else:
            log_fail("Activity log retrieval", f"Status {res.status_code}")
    except Exception as e:
        log_fail("Activity log retrieval", str(e))


# ── Test 7: Admin fraud alert flow ────────────────────────────

def test_fraud_alert_flow():
    print_header("TEST 7 — Admin fraud alert creation and resolution")

    try:
        res = requests.post(f"{BASE_ADMIN}/api/admin/fraud-alerts/create/", json={
            "item_hash":          "d" * 64,
            "item_id":            "integration-test-item-002",
            "issuer_id":          "integration-test-issuer",
            "verification_count": 55
        })
        if res.status_code in [200, 201]:
            alert_id = res.json().get("id")
            log_pass(f"Fraud alert created — id: {str(alert_id)[:18]}...")
        else:
            log_fail("Fraud alert creation",
                     f"Status {res.status_code} — {res.text[:100]}")
            return
    except Exception as e:
        log_fail("Fraud alert creation", str(e))
        return

    try:
        res = requests.get(f"{BASE_ADMIN}/api/admin/fraud-alerts/?status=OPEN")
        if res.status_code == 200 and len(res.json()) > 0:
            log_pass("Fraud alerts retrieved — OPEN alerts found")
        else:
            log_fail("Fraud alert retrieval", "No open alerts found")
    except Exception as e:
        log_fail("Fraud alert retrieval", str(e))


# ── Test 8: Full registration flow (pending Mishael's fix) ────

def test_full_registration_flow(token):
    print_header("TEST 8 — Full registration flow (pending Mishael's UUID fix)")

    if not token:
        log_fail("Full registration flow", "No token available — skipping")
        return

    try:
        res = requests.post(
            f"{BASE_ITEMS}/api/items/register/",
            json={
                "category":        "ACADEMIC",
                "student_name":    "Daniel Leo",
                "degree":          "BSc Computer Science",
                "institution":     "ICT University",
                "graduation_date": "2026-05-19"
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        if res.status_code in [200, 201]:
            log_pass(f"Item registered successfully")
        else:
            log_fail("Item registration",
                     f"Status {res.status_code} — {res.text[:150]}")
    except Exception as e:
        log_fail("Item registration", str(e))


# ── Run all tests ─────────────────────────────────────────────

if __name__ == "__main__":
    print("\n" + "="*60)
    print("  QENTIS INTEGRATION TESTS")
    print("  Make sure all services are running: docker-compose up")
    print("="*60)

    test_all_services_healthy()
    token = test_auth_flow()
    test_blockchain_ganache()
    test_blockchain_store_and_verify()
    test_output_generation()
    test_admin_activity()
    test_fraud_alert_flow()
    test_full_registration_flow(token)

    print("\n" + "="*60)
    print(f"  RESULTS: {len(PASSED)} passed, {len(FAILED)} failed")
    print("="*60)
    if FAILED:
        print("\n  Failed tests:")
        for f in FAILED:
            print(f"    - {f}")
    print()

    import sys
    sys.exit(0 if len(FAILED) == 0 else 1)