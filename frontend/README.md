# SafeNet AI — Command Console (Frontend)

A React + Vite frontend for the [`safenet-AI`](https://github.com/gee-46/safenet-AI) FastAPI backend.
Built directly against the real routes in `backend/api/routes/*.py` — every screen maps to an
endpoint that actually exists; nothing here is a mock or a placeholder feature.

## Routes

- `/` — public marketing landing page (animated hero, module showcase, how-it-works, trust section)
- `/console` — Command Overview dashboard (sidebar app shell)
- `/console/scam-shield`, `/console/counterfeit-lens`, `/console/fraud-graph`,
  `/console/geo-intel`, `/console/citizen-shield`, `/console/evidence` — the six modules

## What's included

| Page | Backend module | Endpoints used |
|---|---|---|
| Landing (`/`) | — | marketing page, links into the console |
| Command Overview | Analytics | `GET /analytics/dashboard`, `/trends`, `/model-performance` |
| ScamShield | Scam Detection | `POST /calls/analyze`, `GET /calls/reports`, `/calls/reports/{id}`, `PATCH .../status`, `GET /calls/stats` |
| CounterfeitLens | Counterfeit Detection | `POST /currency/verify`, `GET /currency/reports`, `/currency/stats` |
| FraudGraph | Fraud Graph Intelligence | `POST /fraud/graph/query`, `POST /fraud/register`, `POST /fraud/link`, `GET/POST /fraud/cases` |
| GeoIntel | Geospatial Intelligence | `GET /heatmap/crimes`, `/patrol-priorities`, `/state-summary`, `/city-hotspots` |
| CitizenShield | Citizen Shield | `POST /citizen/assess`, `GET /citizen/scam-types`, `/citizen/helplines` |
| Evidence Vault | Evidence Packages | `POST /reports/generate`, `GET /reports/download/{id}`, `/reports/audit-trail` |

Not built: `/auth/*` (the backend route file is an unimplemented stub — see
`backend/api/routes/auth_routes.py`) and the WhatsApp Twilio webhook (server-to-server only,
nothing for a person to click).

## Design

Dark "command console" aesthetic: Space Grotesk display type, Inter body, IBM Plex Mono for all
data/coordinates/hashes. Signature elements: a radar-sweep hero (used on both the landing page and
the console dashboard), a radial confidence gauge used consistently for every AI verdict (scam
confidence, counterfeit confidence, per-check security scores, fraud network risk), and a
force-directed graph (`d3-force`) for the fraud network view. The landing page uses custom animated
SVG line-art for each module instead of stock photography, so there's nothing to hotlink or license.

## Setup

```bash
npm install
cp .env.example .env   # set VITE_API_BASE_URL to your backend, e.g. http://localhost:8000
npm run dev
```

Build for production:

```bash
npm run build
npm run preview
```

## Connecting to the backend

The backend's default CORS allowlist (`backend/core/config.py`) only includes
`http://localhost:3000` and `http://localhost:8080`. Vite's dev server runs on `5173` by default,
so either:

- run `npm run dev -- --port 3000`, or
- add `http://localhost:5173` to `cors_origins` in the backend config / `CORS_ORIGINS` env var.

`VITE_API_BASE_URL` should point at the FastAPI root (no `/api/v1` suffix — the client adds that).

## Stack

React 18 · Vite · Tailwind CSS · Framer Motion · Recharts · react-leaflet (CARTO dark tiles) ·
d3-force · react-router-dom · axios · lucide-react
