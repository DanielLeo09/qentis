# Qentis — Development Progress Log

**Project:** Qentis — Universal Blockchain-Powered Authenticity Verification
**Course:** SEN3244 Software Architecture | Spring 2026
**Team:** Daniel Leo Mbetga (Scrum Master) + Neba Mishael Amabo
**Repository:** https://github.com/DanielLeo09/qentis

---

## Service Status

| Service | Owner | Port | Status |
|---|---|---|---|
| User & Auth | Mishael | 8001 | ✅ Complete |
| Institution Management | Mishael | 8002 | 🔄 In progress |
| Item Registration | Mishael | 8003 | 🔄 In progress |
| Blockchain | Daniel | 8004 | ✅ Complete |
| Authentication Output | Daniel | 8005 | ⏳ Next |
| Verification | Mishael | 8006 | 🔄 In progress |
| Admin & Analytics | Mishael | 8007 | 🔄 In progress |

---

## Blockchain Service — Port 8004
**Owner:** Daniel | **Date:** 18 May 2026 | **Tests:** 19 passed | **Coverage:** 82%

### What it does
Only service that talks directly to the Ethereum blockchain (Ganache).
All other services call this one via HTTP to store or verify hashes.
Also keeps a backup record in PostgreSQL in case Ganache restarts.

### API Endpoints
| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/blockchain/store/` | Write item hash to blockchain |
| POST | `/api/blockchain/verify/` | Check hash — returns AUTHENTIC or NOT AUTHENTIC |
| POST | `/api/blockchain/revoke/` | Mark an item as revoked |
| GET | `/api/blockchain/health/` | Confirm service and Ganache are running |

### Verified working
- Health: `http://localhost:8004/api/blockchain/health/` → `ganache_connected: true`
- Swagger: `http://localhost:8004/api/docs/`

### Challenges and solutions

**Docker Desktop not running**
First build failed — Docker Desktop was closed.
Fix: Started Docker Desktop and waited for the whale icon in the taskbar.

**Download interrupted (unexpected EOF)**
Postgres and Ganache images cut out mid-download.
Fix: Re-ran the same command — Docker resumed from where it stopped.

**Test failed — wrong mock path**
Health check test patched `blockchain_app.views.get_web3` but that
function lives in `web3_client.py` not `views.py`.
Fix: Changed patch to `blockchain_app.web3_client.get_web3`.

**Coverage could not parse QentisRegistry.sol**
Coverage tried to read the Solidity contract as Python and crashed.
Fix: File was accidentally named `.py` — renamed to `.sol`. Created
`.coveragerc` to exclude `.sol` files and migrations from coverage.

**Coverage at 65% — below 80% requirement**
Initial tests only covered the happy paths.
Fix: Added 10 more tests for error paths (503, 404, 400 responses).
Final coverage: 82%.

**PowerShell does not support &&**
Chaining commands with `&&` failed on Windows.
Fix: Run each command separately.

**Wrong directory**
docker-compose commands failed from the root folder.
Fix: Always `cd backend` first before any docker-compose command.

---

## User & Auth Service — Port 8001
**Owner:** Mishael | **Status:** ✅ Complete
Custom User model with 4 roles. JWT via simplejwt. Sets the pattern all services follow.

---

## Authentication Output Service — Port 8005
**Owner:** Daniel | **Status:** ⏳ Starting next

---

*Updated: 18 May 2026 — Daniel*