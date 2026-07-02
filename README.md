<p align="center">
  <h1 align="center">🔒 SafeNet AI</h1>
  <p align="center"><b>India's Unified Public Safety Intelligence Platform</b></p>
  <p align="center">
    Detect digital arrest scams · Identify counterfeit currency · Map fraud networks · Protect citizens in 12 languages
  </p>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11-blue?style=flat-square" />
  <img src="https://img.shields.io/badge/FastAPI-0.111-green?style=flat-square" />
  <img src="https://img.shields.io/badge/Neo4j-5.18-orange?style=flat-square" />
  <img src="https://img.shields.io/badge/Tests-51%20passing-brightgreen?style=flat-square" />
  <img src="https://img.shields.io/badge/ET%20AI%20Hackathon-2026-purple?style=flat-square" />
</p>

---

## What is SafeNet AI?

SafeNet AI is a multi-modal AI platform built for **ET AI Hackathon 2.0 (Problem #6 — Digital Public Safety)**. It protects Indian citizens from three converging threats:

| Threat | Scale | SafeNet Response |
|--------|-------|-----------------|
| Digital Arrest Scams | ₹1,776 Cr stolen in 9 months (MHA 2024) | Real-time call classifier + WhatsApp alerts |
| Counterfeit Currency | Record FICN seizures (RBI 2025) | Computer vision security feature analysis |
| Organised Fraud Networks | 1.14M cybercrime complaints (2023) | Graph AI mapping criminal networks across states |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      SAFENET AI PLATFORM                        │
├──────────────┬──────────────────┬──────────────┬───────────────┤
│  CitizenApp  │  WhatsApp/IVR   │ LEA Dashboard│ Bank Portal   │
│ (React Native│  (Twilio)       │ (Next.js)    │ (API Access)  │
└──────┬───────┴────────┬─────────┴──────┬───────┴───────┬───────┘
       └────────────────▼────────────────▼───────────────┘
                        │         FastAPI + WebSocket
       ┌────────────────▼─────────────────────────────────┐
       │              Intelligence Hub                     │
       │  ┌──────────┐ ┌──────────┐ ┌─────────────────┐  │
       │  │  Scam    │ │Counterfeit│ │   FraudGraph    │  │
       │  │Classifier│ │  Detector│ │  (Neo4j + GNN)  │  │
       │  └──────────┘ └──────────┘ └─────────────────┘  │
       │  ┌────────────────────────────────────────────┐  │
       │  │     Geospatial Engine (H3 + DBSCAN)       │  │
       │  └────────────────────────────────────────────┘  │
       └──────────────────────────────────────────────────┘
                             │
              ┌──────────────▼──────────────┐
              │  PostgreSQL │ Neo4j │ Redis  │
              └─────────────────────────────┘
```

---

## Repository Structure

```
safenet-ai/
│
├── backend/                          # All server-side Python code
│   ├── main.py                       # FastAPI app factory + lifespan events
│   ├── core/
│   │   └── config.py                 # Centralised settings (pydantic-settings)
│   ├── db/
│   │   └── models.py                 # 8 SQLAlchemy async models + session factory
│   ├── schemas/
│   │   └── schemas.py                # 27 Pydantic request/response schemas
│   │
│   ├── models/                       # ML inference modules
│   │   ├── scam/
│   │   │   └── classifier.py         # Pattern + DistilBERT ensemble scam detector
│   │   ├── counterfeit/
│   │   │   └── detector.py           # OpenCV + YOLOv8 counterfeit detector
│   │   └── fraud_graph/
│   │       └── graph_intelligence.py # Neo4j graph manager + GNN risk scorer
│   │
│   ├── services/                     # Business logic layer
│   │   ├── citizen_shield.py         # 12-language LLM fraud advisor
│   │   ├── alert_service.py          # Twilio WhatsApp/SMS dispatcher
│   │   └── evidence_generator.py     # ReportLab PDF evidence packages
│   │
│   ├── geo/
│   │   └── geo_intelligence.py       # H3 hexagonal clustering + DBSCAN hotspots
│   │
│   ├── api/routes/                   # FastAPI route handlers
│   │   ├── scam_routes.py            # POST /calls/analyze + 4 more
│   │   ├── currency_routes.py        # POST /currency/verify + 3 more
│   │   ├── fraud_routes.py           # POST /fraud/graph/query + 5 more
│   │   ├── heatmap_routes.py         # GET /heatmap/crimes + 3 more
│   │   ├── citizen_routes.py         # POST /citizen/assess + WhatsApp webhook
│   │   └── analytics_routes.py       # GET /analytics/dashboard + 2 more
│   │
│   └── tasks/
│       └── celery_tasks.py           # 7 background tasks + beat schedule
│
├── ml_training/                      # Model training scripts
│   ├── scam/
│   │   └── train.py                  # DistilBERT fine-tuning
│   ├── counterfeit/
│   │   └── train_yolo.py             # YOLOv8 training + synthetic data gen
│   └── fraud_graph/
│       └── gnn_model.py              # GraphSAGE architecture + training loop
│
├── tests/
│   └── unit/
│       └── test_backend.py           # 51 tests across all modules
│
├── scripts/
│   └── seed_demo_data.py             # Seeds 342 realistic records for demo
│
├── frontend/                         # [TODO] Next.js law enforcement dashboard
├── mobile/                           # [TODO] React Native CounterfeitLens app
│
├── Dockerfile                        # Multi-stage build, Tesseract OCR
├── docker-compose.yml                # Full stack: PG + Redis + Neo4j + Qdrant
├── requirements.txt                  # 35 pinned dependencies
├── .env.example                      # All environment variables documented
└── WORK_REMAINING.md                 # Detailed pending tasks per role
```

---

## Completed Work (Backend + ML)

### ML Models — all in pattern/CV fallback mode, no GPU needed for demo

| Module | File | Capabilities |
|--------|------|-------------|
| Scam Classifier | `backend/models/scam/classifier.py` | 20+ regex patterns, DistilBERT ensemble, 9 scam types, confidence calibration |
| Counterfeit Detector | `backend/models/counterfeit/detector.py` | Watermark, security thread, microprint, colour-shift ink, serial number OCR + RBI checksum |
| Fraud Graph | `backend/models/fraud_graph/graph_intelligence.py` | Neo4j Cypher traversal, heuristic + GNN risk scoring, mule network detection |

### API — 28 endpoints across 6 route groups

| Group | Endpoints | Key capability |
|-------|-----------|---------------|
| `/calls` | 5 | Real-time scam call analysis with instant WhatsApp alert |
| `/currency` | 4 | Multipart image upload → counterfeit verdict |
| `/fraud` | 6 | Graph query, entity linking, case management |
| `/heatmap` | 4 | H3 crime clusters, patrol priorities, state summary |
| `/citizen` | 4 | 12-language fraud assessment + WhatsApp webhook |
| `/analytics` | 3 | Dashboard stats, trend charts, model performance |

### Infrastructure

- PostgreSQL async (8 models with full audit trail)
- Neo4j fraud graph with 6 Cypher query templates
- Celery task queue (7 tasks, hourly beat schedule)
- Docker Compose full stack (one command)
- 51/51 unit tests passing

---

## Quick Start

### Prerequisites
- Python 3.11+
- Docker + Docker Compose
- Git

### 1. Clone and configure
```bash
git clone https://github.com/gee-46/safenet-AI.git
cd safenet-AI
cp .env.example .env
# Edit .env — minimum: DATABASE_URL is pre-filled for Docker
```

### 2. Start all infrastructure
```bash
docker-compose up -d postgres redis neo4j qdrant
```

### 3. Install Python dependencies
```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 4. Seed demo data
```bash
python scripts/seed_demo_data.py
# Seeds: 250 scam reports, 80 counterfeit reports, 12 fraud cases
```

### 5. Run the API
```bash
uvicorn backend.main:app --reload --port 8000
```

### 6. Open API docs
```
http://localhost:8000/docs
```

### Full Docker stack (all services)
```bash
docker-compose up --build
# API: http://localhost:8000
# Neo4j Browser: http://localhost:7474
# API Docs: http://localhost:8000/docs
```

---

## API Quick Reference

### Detect a scam call
```bash
curl -X POST http://localhost:8000/api/v1/calls/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "caller_number": "+911800123456",
    "victim_number": "+919876543210",
    "number_spoofing_detected": true,
    "transcript_snippet": "This is CBI officer. You are arrested for money laundering.",
    "call_duration_seconds": 300,
    "silence_ratio": 0.45
  }'
```

### Verify currency note
```bash
curl -X POST http://localhost:8000/api/v1/currency/verify \
  -F "image=@note.jpg" \
  -F "denomination=500" \
  -F "city=Mumbai" \
  -F "state=Maharashtra"
```

### Query fraud network
```bash
curl -X POST http://localhost:8000/api/v1/fraud/graph/query \
  -H "Content-Type: application/json" \
  -d '{
    "entity_id": "+911800123456",
    "entity_type": "phone_number",
    "depth": 2,
    "max_nodes": 50
  }'
```

### Citizen fraud assessment (any Indian language)
```bash
curl -X POST http://localhost:8000/api/v1/citizen/assess \
  -H "Content-Type: application/json" \
  -d '{
    "message": "CBI officer called and said I am arrested. Do not disconnect.",
    "language": "en",
    "context_type": "call"
  }'
```

### Get crime heatmap
```bash
curl "http://localhost:8000/api/v1/heatmap/crimes?h3_resolution=7&days_back=30&state=Maharashtra"
```

### Generate evidence package PDF
```bash
curl -X POST http://localhost:8000/api/v1/reports/generate \
  -H "Content-Type: application/json" \
  -d '{
    "scam_report_ids": ["<uuid>"],
    "include_regulatory_sections": true
  }'
```

---

## Training the ML Models

### Scam Classifier (DistilBERT)
```bash
# With synthetic data (demo mode — no GPU needed)
python ml_training/scam/train.py --synthetic --epochs 5

# With real data
python ml_training/scam/train.py \
  --data_path ./data/scam_corpus.csv \
  --epochs 10 \
  --output_dir ./ml_training/scam/checkpoints
```

### Counterfeit Detector (YOLOv8)
```bash
# Generate synthetic notes + train
python ml_training/counterfeit/train_yolo.py --synthetic --epochs 50

# With real annotated data
python ml_training/counterfeit/train_yolo.py \
  --data_yaml ./data/counterfeit/dataset.yaml \
  --model yolov8s --epochs 100
```

### Fraud GNN (GraphSAGE)
```bash
python ml_training/fraud_graph/gnn_model.py --synthetic --epochs 50
```

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | ✅ | postgres://... | Async PostgreSQL URL |
| `REDIS_URL` | ✅ | redis://localhost | Redis URL |
| `NEO4J_URI` | ✅ | bolt://localhost:7687 | Neo4j connection |
| `NEO4J_PASSWORD` | ✅ | neo4j_pass | Neo4j password |
| `OPENAI_API_KEY` | ⚡ | — | CitizenShield LLM (falls back to rules without it) |
| `TWILIO_ACCOUNT_SID` | ⚡ | — | WhatsApp alerts |
| `TWILIO_AUTH_TOKEN` | ⚡ | — | WhatsApp alerts |
| `SCAM_MODEL_PATH` | 💡 | — | Fine-tuned DistilBERT path |
| `COUNTERFEIT_MODEL_PATH` | 💡 | — | YOLOv8 weights path |
| `FRAUD_GNN_MODEL_PATH` | 💡 | — | GraphSAGE weights path |

✅ Required · ⚡ Enables extra feature · 💡 Falls back to rule-based

---

## Testing

```bash
# Run all tests
pytest tests/ -v

# With coverage report
pytest tests/ -v --cov=backend --cov-report=term-missing

# Specific test class
pytest tests/unit/test_backend.py::TestScamCallClassifier -v
```

**Current status: 51/51 passing**

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| API Framework | FastAPI 0.111 + Uvicorn |
| Database | PostgreSQL 16 + PostGIS (async SQLAlchemy) |
| Graph DB | Neo4j 5.18 Community |
| Cache / Queue | Redis 7 + Celery 5 |
| Vector Store | Qdrant 1.9 |
| NLP Model | DistilBERT (multilingual) via HuggingFace |
| Computer Vision | YOLOv8 + OpenCV 4.9 |
| Graph ML | PyTorch Geometric (GraphSAGE) |
| Geospatial | H3 v4 + DBSCAN (scikit-learn) |
| PDF Generation | ReportLab |
| Alerts | Twilio WhatsApp + SMS |
| LLM | OpenAI GPT-4o-mini (CitizenShield) |
| Containerisation | Docker + Docker Compose |

---

## Security & Privacy

- No raw audio ever stored — metadata + transcript snippet (max 500 chars) only
- Phone numbers partially masked in all UI-facing responses
- Full immutable audit trail in `audit_logs` table (for legal admissibility)
- PDPB-compliant: citizen data is opt-in only via WhatsApp
- All AI decisions logged with input hash + model version for court use

---

## Hackathon Context

**Event:** ET AI Hackathon 2.0 — Phase 2: Build Sprint  
**Problem:** #6 — AI for Digital Public Safety: Defeating Counterfeiting, Fraud & Digital Arrest Scams  
**Team:** Gautam N Chipkar  
**Submission deadline:** Wednesday, 22nd July 2026, 11:59 PM

---

## License

Proprietary — ET AI Hackathon 2026 submission. All rights reserved.
