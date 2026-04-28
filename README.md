# Qentis

> Universal Blockchain-Powered Authenticity Verification Platform

Qentis is a microservices-based web platform that enables organizations 
to register items for authentication and allows anyone to verify those 
items instantly using blockchain technology to ensure every record is 
permanent, tamper-proof, and independently verifiable.

---

## The Problem

Imagine you graduate from ICT University and get your diploma. You apply 
for a job. The employer asks: "Is this diploma real?" How do they verify 
it? They call the university. The university checks their records manually. 
This takes days, sometimes weeks. And in many cases in Africa, people 
present fake diplomas and nobody catches it because the verification 
process is slow, manual, and unreliable.

This problem is not limited to certificates. Counterfeit medicines kill 
patients. Fraudulent land titles destroy families. Fake jewelry is sold 
as genuine gold. Counterfeit banknotes circulate through markets. Qentis 
solves all of this in one platform.

---

## What Qentis Authenticates

| Category | Examples |
|---|---|
| Academic Certificates | Diplomas, degrees, training certificates |
| Pharmaceutical Products | Drug batches, medicine packaging |
| Official Documents | Land titles, birth certificates, contracts |
| High-Value Jewelry | Gold, silver, diamond, gemstone pieces |
| Currency / Banknotes | Banknote series registered by central banks |

---

## Authentication Methods

- QR Code scan
- NFC tag tap
- Serial number (manual entry)
- Digital signature (document upload)
- OCR photo scan (banknotes)
- Watermark detection (documents and certificates)

---

## Architecture

Qentis is built on a **microservices architecture** with 9 independent 
services communicating through an API Gateway and an event bus.

**Services:**
- User and Authentication Service
- Institution Management Service
- Item Registration Service
- Blockchain Interaction Service
- Authentication Output Service
- Verification Service
- AI Fraud Detection Service
- Notification Service
- Admin and Analytics Service

**Tech Stack:**

| Layer | Technology |
|---|---|
| Frontend | HTML / CSS / JavaScript |
| Backend | Python / Django |
| Database | PostgreSQL |
| Cache | Redis |
| Blockchain | Ethereum / Ganache |
| Containers | Docker |
| Orchestration | Kubernetes (k3s) |
| CI/CD | Jenkins + GitHub |
| Monitoring | Prometheus + Grafana |
| IaC | Ansible |
| Reverse Proxy | Nginx |
| API Docs | Swagger |

---

## Getting Started

> Full setup instructions will be added as development progresses.

### Prerequisites
- Python 3.11+
- Docker and Docker Compose
- Node.js (for frontend tooling)
- Git

### Clone the repository
```bash
git clone https://github.com/YOUR_USERNAME/qentis.git
cd qentis
```

### Run locally with Docker Compose
```bash
docker-compose up
```

---

## Project Structure
qentis/
├── services/           — All microservices
├── frontend/           — HTML/CSS/JS frontend
├── infrastructure/     — Kubernetes, Ansible, Nginx configs
├── monitoring/         — Prometheus and Grafana configs
├── jenkins/            — Jenkinsfile and pipeline configs
├── docs/               — Architecture docs and diagrams
├── tests/              — Test suites
└── docker-compose.yml  — Local development setup

---

## API Documentation

> Swagger documentation will be available at `/api/docs` once the 
> server is running. Link will be added here upon deployment.

---

## Team

| Name | Matricule | Role |
|---|---|---|
| MBETGA YOMBA DANIEL LEO | ICTU20233822 | Team Member |
| NEBA MISHAEL AMABO | ICTU20241112 | Team Member |

**Course:** SEN3244 — Software Architecture  
**Institution:** ICT University, Cameroon  
**Instructor:** Engr. TEKOH PALMA  
**Academic Year:** Spring 2026

---

## License

This project is licensed under the MIT License.
