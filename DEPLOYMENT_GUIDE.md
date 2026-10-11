# JanSetu AI — Production Deployment Guide

This guide provides a comprehensive, step-by-step procedure for deploying **JanSetu AI** across modern hosting platforms.

---

## 1. Target Architecture & Component Map

JanSetu AI employs a unified, microservices-ready decoupled architecture:

```
+-----------------------------------------------------------------------------------+
|                                  PUBLIC CLIENTS                                   |
|                                                                                   |
|   +----------------------------------+    +-----------------------------------+   |
|   |          Vercel Hosting          |    |     Streamlit Community Cloud     |   |
|   |       React 19 + Vite SPA        |    |       Companion Operations        |   |
|   |   (VITE_API_BASE_URL -> Render)  |    |     (FASTAPI_BASE_URL -> Render)  |   |
|   +-----------------+----------------+    +-----------------+-----------------+   |
|                     |                                       |                     |
+---------------------|---------------------------------------|---------------------+
                      | HTTPS REST Calls                      | HTTPS REST Calls
                      v                                       v
+-----------------------------------------------------------------------------------+
|                                  RENDER HOSTING                                   |
|                                                                                   |
|   +---------------------------------------------------------------------------+   |
|   |                     FastAPI + LangGraph Web Service                       |   |
|   |                                                                           |   |
|   |  - 6-Agent LangGraph Orchestration Mesh                                   |   |
|   |  - Incident Intelligence & EXIF Sanitizer                                  |   |
|   |  - Bounded Request Limits & Production Exception Masking                 |   |
|   |  - Server-Side Groq Vision Calls (groq/qwen3.8-27b)                       |   |
|   |  - Short-Lived Signed URL Generator (15-min TTL)                          |   |
|   +---------------------+-------------------------------+---------------------+   |
|                         |                               |                         |
+-------------------------|-------------------------------|-------------------------+
                          | PostgreSQL Connection Pool    | HTTPS REST Storage API
                          v (Port 6543 Supavisor Pooler)  v (Backend Service-Role)
+-----------------------------------------------------------------------------------+
|                              SUPABASE MANAGED CLOUD                               |
|                                                                                   |
|   +------------------------------------+   +----------------------------------+   |
|   |        Supabase PostgreSQL         |   |         Supabase Storage         |   |
|   |                                    |   |                                  |   |
|   | - Persistent `incidents` table     |   | - Private `jansetu-evidence`     |   |
|   | - Alembic schema migrations        |   | - Sanitized JPEG artifacts       |   |
|   | - Idempotent, non-destructive      |   | - Unguessable UUID paths         |   |
|   | - Zero unmanaged table drops       |   | - Strictly Non-Public Bucket     |   |
|   +------------------------------------+   +----------------------------------+   |
+-----------------------------------------------------------------------------------+
```

---

## 2. Supabase Setup (Database & Private Storage)

### Step 2.1: Create Project
1. Log in to [Supabase Console](https://supabase.com/dashboard).
2. Click **New Project**, select an organization, name your project (e.g. `jansetu-ai-prod`), and generate a strong database password.
3. Choose the region closest to your Render service (e.g., `East US / aws-0-us-east-1`).
4. Note your **Project Reference ID** (e.g., `abcdefghijklmnop`).

### Step 2.2: Configure PostgreSQL Connection String
Supabase provides two database connection modes:
- **Direct Connection (Session Mode, Port 5432):** Best for migrations and tools with fixed IP addresses.
- **Transaction Pooler (Supavisor, Port 6543):** **Recommended for Render Web Services.** Render dynos/containers frequently restart or sleep on lower tiers, and the Transaction Pooler prevents connection exhaustion.

In **Project Settings -> Database -> Connection string**:
1. Select the **URI** tab.
2. Choose **Transaction Pooler (Port 6543)**.
3. The connection string format is:
   ```text
   postgresql://postgres.[PROJECT-REF]:[YOUR-PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres
   ```
4. *Driver compatibility:* The JanSetu AI backend automatically normalizes both `postgres://` and `postgresql://` to `postgresql+psycopg2://` with connection pooling enabled (`pool_pre_ping=True`, `pool_size=5`, `max_overflow=10`, `pool_recycle=300`).

### Step 2.3: Database Migrations
Choose one of the two migration approaches:
- **Option A (Automatic):** When the Render backend starts, `app/main.py` invokes `init_db()`. This performs non-destructive `Base.metadata.create_all()` which creates the `incidents` table and indexes if they do not exist. It **never** drops or truncates existing data.
- **Option B (Alembic CLI):** Run the migration manually from a local shell pointing to the Supabase connection string:
  ```bash
  DATABASE_URL="postgresql://postgres.[REF]:[PASS]@aws-0-[REGION].pooler.supabase.com:6543/postgres" alembic upgrade head
  ```

### Step 2.4: Create Private Storage Bucket
1. In Supabase Dashboard, navigate to **Storage -> New Bucket**.
2. **Bucket name:** `jansetu-evidence`
3. **Public bucket:** **Ensure this is toggle OFF / UNCHECKED.** (The bucket MUST be private).
4. Save the bucket.

### Step 2.5: Retrieve API Credentials
1. Navigate to **Project Settings -> API**.
2. Copy **Project URL** (`https://<project-ref>.supabase.co`).
3. Copy **service_role (secret)** key (`eyJh...`).
   > **CRITICAL SECURITY RULE:** The `service_role` key bypasses Row Level Security (RLS) to manage private evidence photos. **Keep this key ONLY in Render environment variables.** Never place it in Vercel or Streamlit configuration.

---

## 3. Render Deployment (FastAPI Backend)

Deploy the backend using the Render Dashboard or the included `render.yaml` Blueprint.

### Step 3.1: Dashboard Setup
1. Log in to [Render Dashboard](https://dashboard.render.com).
2. Click **New + -> Web Service** and connect your GitHub repository.
3. Configure the following settings:
   - **Name:** `jansetu-ai-api`
   - **Region:** Match your Supabase region (e.g. `Oregon (US West)` or `Ohio (US East)`).
   - **Branch:** `main` (or your deployment branch).
   - **Root Directory:** `backend`
   - **Runtime:** `Python`
   - **Build Command:** `pip install --upgrade pip && pip install -r requirements.txt`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Health Check Path:** `/health`
   - **Instance Type:** `Starter` (or `Free`)

### Step 3.2: Configure Environment Variables
In the Render Web Service **Environment** tab, add:

| Variable Name | Example / Expected Value | Purpose |
| :--- | :--- | :--- |
| `PYTHON_VERSION` | `3.11.9` | Enforces compatible runtime version |
| `ENVIRONMENT` | `production` | Switches logging and security guards to production |
| `HOST` | `0.0.0.0` | Binds to platform network interface |
| `DATABASE_URL` | `postgresql://postgres.[REF]:[PASS]@[HOST]:6543/postgres` | Supabase PostgreSQL Transaction Pooler connection |
| `DB_POOL_SIZE` | `5` | SQLAlchemy pool size |
| `DB_MAX_OVERFLOW` | `10` | SQLAlchemy max overflow connections |
| `DB_POOL_TIMEOUT` | `30` | Connection checkout timeout |
| `DB_POOL_RECYCLE` | `300` | Recycles idle connections every 5 minutes |
| `STORAGE_PROVIDER` | `supabase` | Directs photo persistence to private Supabase bucket |
| `SUPABASE_URL` | `https://[PROJECT-REF].supabase.co` | Supabase project API base URL |
| `SUPABASE_SERVICE_ROLE_KEY` | `eyJh...[SECRET]...` | Backend-only credential for storage operations |
| `SUPABASE_STORAGE_BUCKET` | `jansetu-evidence` | Target private storage bucket |
| `SUPABASE_SIGNED_URL_EXPIRY_SECONDS` | `900` | 15-minute expiration for signed evidence access URLs |
| `GROQ_API_KEY` | `gsk_[YOUR_ACTIVE_GROQ_KEY]` | Server-side key for vision multimodal inference |
| `GROQ_MODEL` | `qwen/qwen3.8-27b` | Groq vision multimodal model |
| `CORS_ALLOWED_ORIGINS` | `https://jansetu-ai.vercel.app,https://jansetu-companion.streamlit.app` | Comma-separated permitted frontend origins |
| `DEMO_MODE` | `true` | Allows synthetic simulation scenarios and demo seeding |
| `MAX_UPLOAD_SIZE_MB` | `10` | Enforces 10MB upload ceiling (HTTP 413) |

### Step 3.3: Verify Backend Deployment
Once deployed, verify the service in your browser or with curl:
- Root probe: `GET https://jansetu-ai-api.onrender.com/` (returns `{"status":"ok","service":"JanSetu AI API"}`)
- Health probe: `GET https://jansetu-ai-api.onrender.com/health` (returns `{"status":"healthy","database":"connected"}`)

---

## 4. Vercel Deployment (React + Vite Frontend)

### Step 4.1: Dashboard Setup
1. Log in to [Vercel Dashboard](https://vercel.com).
2. Click **Add New... -> Project** and import your GitHub repository.
3. Configure project settings:
   - **Project Name:** `jansetu-ai`
   - **Framework Preset:** `Vite`
   - **Root Directory:** Click Edit and select `frontend`
   - **Build Command:** `npm run build` (or leave default Vite build)
   - **Output Directory:** `dist`
   - **Install Command:** `npm install`

### Step 4.2: Configure Environment Variables
In the Vercel **Environment Variables** section:

| Variable Name | Value | Purpose |
| :--- | :--- | :--- |
| `VITE_API_BASE_URL` | `https://jansetu-ai-api.onrender.com` | Base URL of hosted FastAPI backend |

> **IMPORTANT:** Do NOT include trailing slashes. Do NOT add `GROQ_API_KEY`, database credentials, or Supabase service keys to Vercel.

### Step 4.3: SPA Routing Verification
The included `frontend/vercel.json` provides rewrite rules ensuring client-side routes (e.g. `/`, `/incidents/:id`) correctly serve `index.html` without 404 errors.

---

## 5. Streamlit Community Cloud (Companion Operations)

### Step 5.1: Dashboard Setup
1. Log in to [Streamlit Community Cloud](https://share.streamlit.io).
2. Click **Create app**.
3. Choose **Repository:** `YourUsername/JanSetu-AI`, **Branch:** `main`.
4. **Main file path:** `streamlit_app/app.py`
5. **App URL:** (Optional custom subdomain, e.g. `jansetu-companion.streamlit.app`).

### Step 5.2: Configure Secrets
1. In the app settings screen or dropdown, select **Advanced settings -> Secrets**.
2. Paste the following TOML configuration:
   ```toml
   FASTAPI_BASE_URL = "https://jansetu-ai-api.onrender.com"
   API_TIMEOUT_SECONDS = 30.0
   ```
3. Click **Save** and deploy.
4. Streamlit Cloud automatically uses `streamlit_app/requirements.txt` (`streamlit`, `httpx`, `pillow`, `pydantic`).

---

## 6. Groq Security & Push Protection Policy

During earlier development, a test Groq API key was caught by GitHub push protection.

Before pushing repository commits to GitHub:
1. **Revoke the old key:** Open [Groq Cloud API Keys](https://console.groq.com/keys) and delete the previously exposed key.
2. **Generate a new key:** Create a fresh key exclusively for use in Render Dashboard environment variables.
3. **Verify Git tracking:** Run `git status` to ensure `.env` and `secrets.toml` remain untracked.

---

## 7. Storage Retention & Deletion Process

To comply with data privacy policies and storage quotas:
- **Intake Sanitization:** Images uploaded to JanSetu AI are stripped of all EXIF metadata (camera serials, GPS tags, device timestamps) and re-encoded as JPEG under 4096x4096px before storage.
- **Unguessable Paths:** Files in Supabase Storage are assigned identifiers in the format `evidence/{incident_id}/{uuid}.jpg` with zero citizen PII.
- **Backend-Mediated Retrieval:** Image access is granted through 15-minute signed URLs via `GET /api/v1/incidents/{incident_id}/photo`.
- **Scheduled Retention:** Municipal guidelines recommend retaining photographic evidence for **90 days** post-resolution. Archived incidents can purge associated storage objects via `delete_stored_image(incident.photo_storage_path)`.

---

## 8. Verification & Troubleshooting Checklist

| Test Case | Expected Behavior | Troubleshooting If Failed |
| :--- | :--- | :--- |
| **Health Check** | `GET /health` returns 200 with status `healthy` | Check Render logs for database connection timeouts or missing `DATABASE_URL`. |
| **CORS Access** | React UI loads data without browser console CORS errors | Ensure `CORS_ALLOWED_ORIGINS` in Render includes the exact Vercel URL without trailing slash. |
| **Photo Upload** | Uploading photo stores JPEG in Supabase and returns 201 | Verify `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, and that bucket name `jansetu-evidence` exists and is private. |
| **Photo Viewing** | Clicking photo in React/Streamlit loads image | Verify `GET /api/v1/incidents/{id}/photo` returns a valid 307 redirect to the Supabase signed URL. |
| **Simulations** | Triggering simulation runs multi-agent workflow | If HTTP 403 is returned, verify `DEMO_MODE=true` is set in Render environment variables. |
| **Database Pool** | Concurrent requests execute cleanly | Ensure port `6543` (Supavisor Transaction Pooler) is used instead of direct port `5432`. |
