# BFA Gateway (IRC-A Protocol Gateway Server)

> Standalone semantic registry, capability broker, and PASETO token minter for autonomous agents and FastMCP tool servers.

## 1. Overview

The **BFA Gateway** is a domain-agnostic capability directory and token broker. It maintains a FAISS vector index of registered agent and tool metadata (descriptions, tags, examples) to resolve natural-language queries to the appropriate capability and mint short-lived cryptographically signed **Delegated Execution Tokens (DET)**.

### Features
- **Semantic Discovery**: FAISS vector search with L2 distance to confidence score mapping.
- **Asymmetric Handshake**: Ed25519 challenge-response dynamic registration (`POST /register/init`, `POST /register/verify`).
- **Token Minting**: PASETO v4.public token minting (`POST /discover`, `POST /mint`).
- **Persistence**: Supports local JSON persistence (`bfa_registry_db.json`) and AWS DynamoDB with optimistic locking.
- **Deployment**: Single container (`Dockerfile`), `docker-compose.yml`, Terraform GCP Cloud Run, and Serverless AWS Lambda (Mangum adapter).

## 2. Quickstart

### Run with Python

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
bfa-gateway
```

### Run with Docker

```bash
docker build -t sandrog77/bfa-gateway:latest .
docker run -p 8000:8000 sandrog77/bfa-gateway:latest
```

## 3. License

AGPLv3 / Dual Commercial License. Copyright (c) 2026 Sandro G.
