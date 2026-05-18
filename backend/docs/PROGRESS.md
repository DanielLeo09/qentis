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

---

## Key Concepts — For the Project Report

### What is Blockchain?
A blockchain is a type of database that is distributed across thousands
of computers simultaneously, immutable (records cannot be changed once
written), and decentralized (no single person or company controls it).
It removes the need to trust any single organisation — the data is
secured by mathematics, not by human integrity.

### What is Ethereum?
Ethereum is one specific implementation of blockchain technology, created
by Vitalik Buterin in 2015. What makes Ethereum unique is that it
introduced smart contracts — programs that live on the blockchain itself,
execute automatically, and cannot be altered or stopped by anyone.

Bitcoin (the other well-known blockchain) can only transfer currency.
Ethereum can run business logic directly on the blockchain.

### What is a Smart Contract?
A smart contract is a program deployed on the Ethereum blockchain. Once
deployed, its rules are permanent and execute automatically without human
intervention. In Qentis, the QentisRegistry smart contract enforces:
- A hash can only be stored once — no duplicates
- Once stored, a record can never be deleted or modified
- Revocation is permanent and transparent
- Anyone can verify any record without permission

### What is Solidity?
Solidity is the programming language used to write smart contracts for
Ethereum. It is the industry standard for smart contract development.
Our QentisRegistry.sol file is written in Solidity.

### What is Ganache?
Ganache is a tool that simulates a private local Ethereum blockchain on
a developer's machine. It behaves identically to the real Ethereum
network but is free, instant, and fully under the developer's control.
It is used during development and testing. In production, Ganache would
be replaced by the real Ethereum network or a Layer-2 solution like
Polygon or SKALE to handle scale and reduce transaction costs.

### What is web3.py?
web3.py is the Python library that allows Django to communicate with
Ethereum. It is the official Python interface for Ethereum interaction.
It handles connecting to Ganache, deploying smart contracts, calling
contract functions, and reading blockchain records.

### Why Ethereum for Qentis specifically?
1. Smart contracts — Qentis needs business rules on the blockchain
   (store once, never delete). Only Ethereum-compatible chains support this.
2. Solidity — most documented and supported smart contract language.
3. web3.py — mature Python library, perfect for our Django backend.
4. Ganache — free local simulation for development with no real ETH needed.
5. Industry standard — platforms like Verix, Blockcerts, and MediLedger
   all use Ethereum or Ethereum-compatible chains.

### Why Blockchain and not just a normal database?
A normal database can be edited by whoever controls the server —
including Qentis administrators. The blockchain record cannot be changed
by anyone once written. The verification result does not depend on
trusting Qentis — it depends on the Ethereum blockchain which nobody
controls. This is critical in contexts like Cameroon where institutional
records may be vulnerable to manipulation.

### Port numbering in microservices
Ports are like door numbers on a computer. Port numbers 8001-8007 were
a deliberate team decision — chosen sequentially for clarity. Django's
default is 8000 so we started from 8001. Each service gets its own
port so they can all run simultaneously without conflict.
Format in docker-compose: "machine_port:container_port" e.g. "8004:8004"

### Docker vs Virtual Environment
Normally Python developers use virtual environments to isolate packages
per project. In a Docker-based microservices setup, the Docker container
itself IS the isolation. Each service runs in its own container with its
own Python installation and packages. No virtual environment is needed.

### What does makemigrations vs migrate do?
- `makemigrations` — reads your models.py and generates a migration file
  describing what database changes need to be made
- `migrate` — takes that migration file and actually executes the changes
  against the PostgreSQL database, creating or modifying tables