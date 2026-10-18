# JanSetu AI — Production Deployment Guide (Docker Compose & AWS EC2)

> **Document Type:** Production Deployment Specification & Operations Runbook  
> **Target Platform:** Docker Engine 24+ & Docker Compose v2.20+ on Linux (Ubuntu 22.04 LTS / Amazon Linux 2023) or Windows Docker Desktop  
> **Architecture:** Single-Origin Nginx Reverse Proxy + FastAPI Asynchronous Multi-Agent Backend + React 19 / Vite SPA  
> **Classification:** Academic Proof of Concept (Field operations strictly simulated)

---

## 1. Production Architecture Overview

The production deployment of JanSetu AI uses a dual-container architecture connected via an isolated internal bridge network:

```
                          Internet / Public Client
                                     │
                             Port 80 (HTTP)
                                     ▼
                   ┌───────────────────────────────────┐
                   │        jansetu-frontend-prod      │
                   │           (Nginx Alpine)          │
                   │                                   │
                   │  /               -> Static SPA    │
                   │  /api/v1/...     -> Proxy Pass ──┐│
                   │  /health         -> Proxy Pass ──┼┤
                   │  /docs           -> Proxy Pass ──┼┤
                   └───────────────────────────────────┼┘
                                                       │  jansetu_internal
                                                       │  (Port 8000 internal)
                                                       ▼
                                   ┌───────────────────────────────────┐
                                   │        jansetu-backend-prod       │
                                   │      (FastAPI + Python 3.11)      │
                                   │                                   │
                                   │  - 6 Specialist Agents + Critic   │
                                   │  - Deterministic Simulator Lab    │
                                   │  - Multimodal TF-IDF / Vision     │
                                   │  - Civic Incident Twin (SQLite)   │
                                   └─────────────────┬─────────────────┘
                                                     │
                                                     ▼
                                        Docker Persistent Volumes:
                                        - jansetu_production_data
                                        - jansetu_production_eval
```

### Key Architectural Invariants Enforced

1. **Port Isolation:** Port `8000` (FastAPI) is **never** exposed publicly. Only Nginx on port `80` is open to ingress.
2. **Same-Origin API Routing:** Nginx handles `/api/` and `/health` requests directly, eliminating Cross-Origin Resource Sharing (CORS) blockers and avoiding hardcoded `localhost:8000` references in the browser.
3. **Data Immutability & Persistence:** All SQLite state (`jansetu.db`) and uploaded citizen evidence (`/app/data/uploads`) reside in named Docker volumes (`jansetu_production_data`) that survive container destruction, recreation, and updates.
4. **Academic Simulation Guard:** Field interventions remain explicitly labeled `simulated=True` and reach `SIMULATED_RESOLVED`. Database seeding (`/api/v1/incidents/seed`) is strictly disabled in production (`DEMO_MODE=false`).

---

## 2. Docker Compose Configurations

JanSetu AI maintains two distinct configurations:

| Configuration File | Environment | Frontend Port | Backend Port | Seeding Allowed | Use Case |
|---|---|---|---|---|---|
| `docker-compose.yml` | `development` | `5173` | `8000` (published) | Yes (`DEMO_MODE=true`) | Local testing, inspection |
| `docker-compose.prod.yml` | `production` | `80` | Internal only | No (`DEMO_MODE=false`) | Server / EC2 deployment |

---

## 3. Operational Runbook

### Starting the Production Application

```bash
# Clone the repository
git clone https://github.com/Harshad2321/JanSetu-AI.git
cd JanSetu-AI

# Configure production environment variables
cat << 'EOF' > .env
ENVIRONMENT=production
DEMO_MODE=false
DATABASE_URL=sqlite:///./data/jansetu.db
STORAGE_DIR=./data/uploads
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile
GROQ_VISION_MODEL=qwen/qwen3.8-27b
EOF

# Build and launch production containers
docker compose -f docker-compose.prod.yml up -d --build
```

### Stopping the Application

```bash
docker compose -f docker-compose.prod.yml down
```

### Inspecting Health and Logs

```bash
# Check container status and health
docker compose -f docker-compose.prod.yml ps

# Follow logs in real-time
docker compose -f docker-compose.prod.yml logs -f

# Inspect backend logs only
docker compose -f docker-compose.prod.yml logs --tail=100 backend
```

---

## 4. Database Backup & Disaster Recovery

Because JanSetu AI utilizes SQLite with persistent named volumes, backups can be performed atomically without stopping the container:

### Creating an Atomic Database Backup

```bash
# Snapshot the SQLite database to the host machine
docker compose -f docker-compose.prod.yml exec -T backend \
  sqlite3 /app/data/jansetu.db ".backup '/app/data/jansetu_backup_$(date +%Y%m%d_%H%M%S).db'"

# Copy the backup out to host storage
docker cp jansetu-backend-prod:/app/data/jansetu_backup_*.db ./backups/
```

### Restoring from Backup

```bash
# Stop backend container
docker compose -f docker-compose.prod.yml stop backend

# Copy restored database into the volume
docker cp ./backups/jansetu_backup_20261018.db jansetu-backend-prod:/app/data/jansetu.db

# Restart backend
docker compose -f docker-compose.prod.yml start backend
```

---

## 5. AWS EC2 Provisioning Guide

### Recommended Instance Specifications
- **Instance Type:** `t3.medium` (2 vCPU, 4 GiB RAM) or `t4g.medium` (Graviton2, cost-effective).
  *Rationale:* FastAPI + LangGraph + scikit-learn model loading requires ~1.2 GB RSS. Node/Nginx requires ~200 MB. 4 GiB provides ample headroom without OOM kills.
- **Storage:** 25 GB gp3 EBS volume (root + Docker images + uploads).
- **Estimated Ongoing Cost:** ~$0.0416/hr (~$30/month) for `t3.medium` in `ap-south-1` (Mumbai).

### Network Security Group Configuration
| Type | Port | Source | Description |
|---|---|---|---|
| HTTP | 80 | `0.0.0.0/0` | Public web application |
| HTTPS | 443 | `0.0.0.0/0` | Secure web application (when TLS configured) |
| SSH | 22 | `<your-specific-ip>/32` | Administrative shell (never 0.0.0.0/0) |

*Port 8000 and internal database ports MUST NEVER be opened in the security group.*

---

## 6. Known Deployment Limitations & Notes

1. **HTTP-only Preview Restrictions:** If deployed without a TLS/SSL certificate, modern mobile browsers will restrict access to device sensors (e.g., GPS Geolocation API and Camera MediaDevices). Users should select landmark locations or upload existing photos until HTTPS is terminated via Let's Encrypt / AWS ACM.
2. **Simulation Boundary:** JanSetu AI is an educational proof of concept. The terminal status `VERIFIED_CLOSED` reflects a validated simulation outcome (`simulated=True`) rather than physical municipal road repair.
