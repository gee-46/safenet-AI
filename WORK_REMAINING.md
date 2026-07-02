# SafeNet AI — Pending Work & Role Assignments

**Last updated:** July 2026  
**Status:** Backend + ML complete. Frontend and data pipelines pending.

---

## ROLE 1: ML ENGINEER

### Status: Code complete. Training data + weights missing.

---

### Task 1.1 — Collect real scam transcript data
**File to produce:** `data/scam_corpus.csv`  
**Format:**
```csv
text,label
"This is CBI officer. You are arrested for money laundering.",digital_arrest
"Your KYC has expired. Share OTP to update.",kyc_update
```

**Labels must be one of:**
`digital_arrest` | `loan_fraud` | `lottery` | `kyc_update` | `impersonation` | `investment` | `romance` | `tech_support` | `unknown`

**Minimum:** 500 samples per label (4,500 total minimum, 10,000 ideal)

**Sources to collect from:**
- MHA cybercrime helpline transcripts (public reports)
- NCRB complaint summaries
- News articles quoting scam scripts (The Wire, IndiaSpend)
- Manually write variations based on known scam patterns in `ml_training/scam/train.py` under `generate_synthetic_data()`

**How to run training after data is ready:**
```bash
python ml_training/scam/train.py \
  --data_path ./data/scam_corpus.csv \
  --output_dir ./ml_training/scam/checkpoints \
  --epochs 10 \
  --model_name distilbert-base-multilingual-cased
```

**Output expected:**
```
ml_training/scam/checkpoints/best_model/
├── config.json
├── pytorch_model.bin
├── tokenizer.json
├── tokenizer_config.json
└── label_map.json
```

**After training, set in `.env`:**
```
SCAM_MODEL_PATH=./ml_training/scam/checkpoints/best_model
```

---

### Task 1.2 — Collect real currency note images and train YOLOv8
**File to produce:** `data/counterfeit/images/` + `data/counterfeit/labels/`

**Dataset structure needed:**
```
data/counterfeit/
├── images/
│   ├── train/   (min 500 genuine + 500 counterfeit photos)
│   └── val/     (min 100 genuine + 100 counterfeit photos)
└── labels/
    ├── train/   (YOLO format .txt files)
    └── val/
```

**YOLO label format** (one line per detected object):
```
class_id x_center y_center width height
```

**Class IDs:**
```
0 = note_genuine
1 = note_counterfeit
2 = watermark_region
3 = security_thread_region
4 = microprint_region
5 = serial_number_region
```

**How to generate synthetic data first (for testing pipeline):**
```bash
python ml_training/counterfeit/train_yolo.py --synthetic --epochs 10
```

**How to train with real data:**
```bash
python ml_training/counterfeit/train_yolo.py \
  --data_yaml ./data/counterfeit/dataset.yaml \
  --model yolov8s \
  --epochs 100 \
  --imgsz 640
```

**Output expected:**
```
ml_training/counterfeit/checkpoints/best_yolo.pt
```

**After training, set in `.env`:**
```
COUNTERFEIT_MODEL_PATH=./ml_training/counterfeit/checkpoints/best_yolo.pt
```

---

### Task 1.3 — Train the Fraud GNN
**No external data needed — synthetic graph generator built in**

**How to run:**
```bash
python ml_training/fraud_graph/gnn_model.py \
  --synthetic \
  --num_nodes 1000 \
  --epochs 100 \
  --output_dir ./ml_training/fraud_graph/checkpoints
```

**Output expected:**
```
ml_training/fraud_graph/checkpoints/best_gnn.pt
ml_training/fraud_graph/checkpoints/gnn_config.json
```

**After training, set in `.env`:**
```
FRAUD_GNN_MODEL_PATH=./ml_training/fraud_graph/checkpoints/best_gnn.pt
```

---

### Task 1.4 — Run and verify all 51 tests pass after models are loaded
```bash
pytest tests/unit/test_backend.py -v
```
All 51 should still pass. If new model paths cause import errors, fix the path in `.env` and rerun.

---

---

## ROLE 2: BACKEND ENGINEER

### Status: 90% complete. Two things missing.

---

### Task 2.1 — Build JWT authentication routes
**File to create:** `backend/api/routes/auth_routes.py`

**What it needs to do:**
1. `POST /api/v1/auth/register` — create new user (citizen / officer / analyst)
2. `POST /api/v1/auth/login` — verify password, return JWT access token
3. `POST /api/v1/auth/refresh` — refresh expired token
4. `GET /api/v1/auth/me` — return current user profile

**The User model already exists in** `backend/db/models.py`  
**The UserCreate and UserLogin schemas already exist in** `backend/schemas/schemas.py`

**How to implement:**

Step 1 — Add these imports to `auth_routes.py`:
```python
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from backend.core.config import get_settings
from backend.db.models import User, get_db
from backend.schemas.schemas import UserCreate, UserLogin, TokenResponse, UserOut
```

Step 2 — Password hashing:
```python
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)
```

Step 3 — Token creation:
```python
def create_token(user_id: str, role: str) -> str:
    settings = get_settings()
    payload = {
        "sub": user_id,
        "role": role,
        "exp": datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    }
    return jwt.encode(payload, settings.app_secret_key, algorithm=settings.jwt_algorithm)
```

Step 4 — Add the router to `backend/main.py`:
```python
from backend.api.routes.auth_routes import router as auth_router
app.include_router(auth_router, prefix="/api/v1")
```

Step 5 — Add role guard dependency for officer-only routes:
```python
async def require_officer(token: str = Depends(oauth2_scheme)) -> dict:
    # decode token, check role == "officer" or "admin"
    # raise 403 if not
```

---

### Task 2.2 — Replace create_all() with Alembic migrations
**Why:** `create_all()` in `backend/db/models.py` wipes schema context on every restart in production. Alembic tracks schema versions safely.

**Steps:**

```bash
# Install alembic (already in requirements.txt)
pip install alembic

# Initialise in project root
alembic init alembic

# Edit alembic/env.py — add these two lines after imports:
from backend.db.models import Base
from backend.core.config import get_settings
target_metadata = Base.metadata
# Also set: config.set_main_option("sqlalchemy.url", get_settings().database_url.replace("+asyncpg", ""))

# Generate first migration
alembic revision --autogenerate -m "initial schema"

# Apply migration
alembic upgrade head
```

**After this is done, remove** `await create_tables()` from `backend/main.py` lifespan.

---

### Task 2.3 — Add Prometheus metrics endpoint
**File to create:** `infrastructure/prometheus.yml`

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'safenet-api'
    static_configs:
      - targets: ['api:8000']
    metrics_path: '/metrics'
```

**Also add to** `backend/main.py`:
```python
from prometheus_client import make_asgi_app, Counter, Histogram

# Add metrics
scam_detections = Counter('safenet_scam_detections_total', 'Total scam calls analyzed', ['scam_type'])
api_latency = Histogram('safenet_api_latency_seconds', 'API latency', ['endpoint'])

# Mount metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)
```

---

---

## ROLE 3: FRONTEND ENGINEER

### Status: 0% — nothing built yet. APIs are all ready.

**Base URL for all API calls:** `http://localhost:8000/api/v1`  
**Full API docs:** `http://localhost:8000/docs`

---

### Task 3.1 — Law Enforcement Dashboard (Next.js)
**Directory to create:** `frontend/`

**Tech stack:**
- Next.js 14 (App Router)
- Tailwind CSS
- Mapbox GL JS (map)
- Recharts (charts)
- TanStack Query (data fetching)
- shadcn/ui (components)

**Setup:**
```bash
npx create-next-app@14 frontend --typescript --tailwind --app
cd frontend
npm install @mapbox/mapbox-gl mapbox-gl recharts @tanstack/react-query
```

**5 pages to build:**

#### Page 1: Dashboard (`/`)
Shows summary stats. Call this API:
```
GET /api/v1/analytics/dashboard?days_back=30
```
Response has: `total_scam_detections_30d`, `active_fraud_cases`, `alerts_sent_30d`, `top_scam_types`, `top_states`

Display as: 4 metric cards at top, bar chart for scam types, table for top states

#### Page 2: Crime Heatmap (`/heatmap`)
Full-screen Mapbox map. Call this API:
```
GET /api/v1/heatmap/crimes?h3_resolution=7&days_back=30
```
Response has: `clusters[]` with `h3_index`, `center.lat`, `center.lng`, `risk_score`, `scam_count`

Draw H3 hexagons coloured by `risk_score` (green → yellow → red). Clicking a hex shows a popup with counts.

Also call:
```
GET /api/v1/heatmap/patrol-priorities?top_n=5
```
Show top 5 patrol zones as a sidebar list.

#### Page 3: Fraud Graph (`/graph`)
Graph visualisation using `react-force-graph` or `cytoscape.js`. 

Search input for a phone number. On submit, call:
```
POST /api/v1/fraud/graph/query
Body: { "entity_id": "+91...", "entity_type": "phone_number", "depth": 2, "max_nodes": 50 }
```
Response has `nodes[]` and `edges[]`. Render as a force-directed graph. Colour nodes by `type` (phone = red, bank_account = orange, device = blue). Node size = `risk_score`.

#### Page 4: Scam Reports (`/reports`)
Table of all scam reports. Call:
```
GET /api/v1/calls/reports?page=1&page_size=20&days_back=30
```
Columns: Date | Caller Number | Scam Type | Confidence | City | Status

Filter dropdowns for: scam type, state, status, date range.

Each row has a button "Generate Evidence PDF" which calls:
```
POST /api/v1/reports/generate
Body: { "scam_report_ids": ["<id>"] }
```
Then redirect to the download URL from response.

#### Page 5: Cases (`/cases`)
```
GET /api/v1/fraud/cases?status=open
```
Card grid of open fraud cases. Each card shows: case number, fraud type, estimated victims, estimated loss, severity badge, states involved.

---

### Task 3.2 — React Native Mobile App (CounterfeitLens)
**Directory to create:** `mobile/`

**Tech stack:**
- React Native (Expo)
- Expo Camera
- React Native Paper (UI)

**Setup:**
```bash
npx create-expo-app mobile --template blank-typescript
cd mobile
npx expo install expo-camera expo-image-picker
npm install react-native-paper axios
```

**2 screens to build:**

#### Screen 1: Camera Capture
- Full screen camera view using `expo-camera`
- Button to capture photo
- On capture: show loading spinner, then call API

```javascript
const formData = new FormData()
formData.append('image', {
  uri: photo.uri,
  type: 'image/jpeg',
  name: 'note.jpg',
})
formData.append('denomination', '500')

const response = await axios.post(
  'http://YOUR_SERVER_IP:8000/api/v1/currency/verify',
  formData,
  { headers: { 'Content-Type': 'multipart/form-data' } }
)
```

#### Screen 2: Result Display
Show the response:
- Large verdict badge: GENUINE (green) / COUNTERFEIT (red) / UNCERTAIN (yellow)
- Confidence percentage
- Security checks table (watermark score, thread score, microprint score)
- List of defects detected
- Recommendation text
- Share button (to send report to police)

---

### Task 3.3 — WhatsApp Bot (configuration only — code is done)
The webhook code is already built in `backend/api/routes/citizen_routes.py`.

What needs to be done:
1. Create a Twilio account at twilio.com
2. Activate WhatsApp Sandbox: Twilio Console → Messaging → Try it Out → WhatsApp
3. Set the webhook URL in Twilio console:
   - When a message comes in: `https://your-server.com/api/v1/citizen/whatsapp-webhook`
4. Add to `.env`:
   ```
   TWILIO_ACCOUNT_SID=ACxxxxxxxxxx
   TWILIO_AUTH_TOKEN=your_token
   TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
   ```
5. Test by sending any message to the Twilio sandbox number
6. For demo: use ngrok to expose localhost:
   ```bash
   ngrok http 8000
   # Copy the https URL → paste into Twilio webhook field
   ```

---

---

## ROLE 4: DATA ENGINEER

### Status: Geospatial engine done. NCRB + RBI ingestion scripts missing.

---

### Task 4.1 — NCRB Data Ingestion Script
**File to create:** `scripts/ingest_ncrb.py`

**What it does:** Downloads and parses publicly available NCRB cybercrime data, loads state-wise complaint counts into the database as historical baseline.

**Data source:** https://ncrb.gov.in/crime-in-india-year-wise.html  
Download: "Crime in India 2022" → Chapter 18 (Cybercrime) → Table 18.1

**Steps to build this script:**

```python
# scripts/ingest_ncrb.py

import asyncio
import csv
from backend.db.models import AsyncSessionLocal, ScamReport

# The NCRB data format after manual extraction from PDF:
# state, year, cybercrime_count, fraud_count, digital_fraud_count
NCRB_2022_DATA = [
    ("Uttar Pradesh", 2022, 10117, 8231, 6544),
    ("Maharashtra", 2022, 8976, 7123, 5891),
    ("Karnataka", 2022, 7234, 5891, 4012),
    # ... add all 36 states/UTs from NCRB table 18.1
]

async def ingest():
    async with AsyncSessionLocal() as session:
        for state, year, total, fraud, digital in NCRB_2022_DATA:
            # Create GeoCluster entries with state-level risk scores
            # This gives the heatmap a baseline even before real reports come in
            pass
```

**Expected output:** GeoCluster records for all 36 states seeded with historical baseline risk scores.

---

### Task 4.2 — RBI Currency Data Ingestion Script
**File to create:** `scripts/ingest_rbi_currency.py`

**Data source:** RBI Annual Report 2024-25, Table on FICN (Fake Indian Currency Notes) Detected  
URL: https://www.rbi.org.in/Scripts/AnnualReportPublications.aspx

**Steps:**
1. Download RBI Annual Report PDF
2. Extract Table: "Denomination-wise details of Fake Indian Currency Notes detected"
3. Parse: denomination, pieces detected, state (where available)
4. Load into `counterfeit_reports` table as historical records

**Why this matters:** Without real counterfeit reports in the DB, the heatmap shows no counterfeit hotspots. This seeds historical RBI data to make the demo map realistic.

---

### Task 4.3 — Fix Prometheus config file
**File to create:** `infrastructure/prometheus.yml`

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'safenet-api'
    static_configs:
      - targets: ['api:8000']
    metrics_path: '/metrics'

  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']

  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']
```

This file is referenced in `docker-compose.yml` but does not exist yet. Docker Compose will fail to start Prometheus without it.

---

---

## DEMO PREPARATION (all roles together)

### Before the demo, run in this exact order:

```bash
# 1. Start all infrastructure
docker-compose up -d postgres redis neo4j qdrant

# 2. Wait 30 seconds for Neo4j to start fully
sleep 30

# 3. Install dependencies
pip install -r requirements.txt

# 4. Seed realistic demo data
python scripts/seed_demo_data.py

# 5. (Optional) Run NCRB ingestion for richer heatmap
python scripts/ingest_ncrb.py

# 6. Start API server
uvicorn backend.main:app --reload --port 8000

# 7. Verify health
curl http://localhost:8000/health/deep

# 8. Start frontend (once built)
cd frontend && npm run dev

# 9. For WhatsApp demo: start ngrok in separate terminal
ngrok http 8000
```

### Demo script (3 minutes):

1. **(0:00-0:30)** Open heatmap at `/heatmap` — show real crime clusters across India
2. **(0:30-1:00)** Run live scam call analysis via `/docs` — paste the "CBI arrest" transcript — show red alert + WhatsApp message
3. **(1:00-1:30)** Hold phone to camera — scan a 500 rupee note — show GENUINE verdict with security checks
4. **(1:30-2:00)** Show fraud graph for the scammer number — visualise the network
5. **(2:00-2:30)** Click "Generate Evidence PDF" — download and show the court-ready document
6. **(2:30-3:00)** Close with dashboard stats: X scams prevented, ₹Y loss avoided

---

## File Checklist

### Must be done before submission:

- [ ] `frontend/` — Next.js dashboard (Frontend Engineer)
- [ ] `mobile/` — React Native app (Frontend Engineer)  
- [ ] `backend/api/routes/auth_routes.py` — JWT auth (Backend Engineer)
- [ ] `infrastructure/prometheus.yml` — metrics config (Data Engineer)
- [ ] `scripts/ingest_ncrb.py` — NCRB baseline data (Data Engineer)
- [ ] `.env` — filled with real credentials (all)
- [ ] ML model weights trained and paths set in `.env` (ML Engineer)
- [ ] Twilio WhatsApp sandbox configured (Frontend Engineer)

### Already done — do not rebuild:

- [x] `backend/models/scam/classifier.py`
- [x] `backend/models/counterfeit/detector.py`
- [x] `backend/models/fraud_graph/graph_intelligence.py`
- [x] `backend/main.py`
- [x] `backend/db/models.py`
- [x] `backend/schemas/schemas.py`
- [x] `backend/api/routes/scam_routes.py`
- [x] `backend/api/routes/currency_routes.py`
- [x] `backend/api/routes/fraud_routes.py`
- [x] `backend/api/routes/heatmap_routes.py`
- [x] `backend/api/routes/citizen_routes.py`
- [x] `backend/api/routes/analytics_routes.py`
- [x] `backend/services/citizen_shield.py`
- [x] `backend/services/alert_service.py`
- [x] `backend/services/evidence_generator.py`
- [x] `backend/geo/geo_intelligence.py`
- [x] `backend/tasks/celery_tasks.py`
- [x] `backend/core/config.py`
- [x] `ml_training/scam/train.py`
- [x] `ml_training/counterfeit/train_yolo.py`
- [x] `ml_training/fraud_graph/gnn_model.py`
- [x] `scripts/seed_demo_data.py`
- [x] `tests/unit/test_backend.py` (51 passing)
- [x] `docker-compose.yml`
- [x] `Dockerfile`
- [x] `requirements.txt`
- [x] `.env.example`
- [x] `README.md`
