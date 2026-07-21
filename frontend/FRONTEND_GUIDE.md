# SafeNet AI Frontend Developer Guide

Welcome to the SafeNet AI Public Safety Intelligence Console frontend! This guide outlines the setup, architecture, routing structure, and available tools.

## Tech Stack
- **Core Framework**: React 19 (Vite)
- **Styling**: Tailwind CSS & Vanilla CSS
- **Routing**: React Router DOM (v7)
- **Maps**: React Leaflet & Leaflet
- **Data Visualization**: Recharts, D3 (force-directed graphs)
- **Icons**: Lucide React
- **Animations**: Framer Motion

---

## Directory Structure
- `/public` - Static assets, SVG sprites, and favicon.
- `/src`
  - `/components`
    - `/graph` - Network/graph visualization components (e.g. `ForceGraph`).
    - `/landing` - Public landing components (hero sections, footer, navigation).
    - `/layout` - Dashboard UI wrapper (`Shell.jsx`).
    - `/ui` - Custom dashboard UI primitives (progress indicators, gauges).
  - `/lib` - API wrappers and integration hooks.
  - `/pages` - Console dashboards, map layers, and analytical modules.

---

## Getting Started

### 1. Installation
Install the project dependencies using npm:
```bash
npm install
```

### 2. Configure Environment Variables
Create a local `.env` file in this directory based on the `.env.example`:
```ini
VITE_API_URL=http://localhost:8000/api
```

### 3. Start Development Server
Run the local Vite server:
```bash
npm run dev
```
By default, the server starts on `http://localhost:5173/` or `http://localhost:5174/` if 5173 is occupied.

### 4. Build for Production
Create the optimized production build:
```bash
npm run build
```

---

## Dashboard Shell & Routes
The core application utilizes `src/components/layout/Shell.jsx` for dashboard navigation.
The following console modules are available under `/src/pages`:
1. **CitizenShield** (`/citizen-shield`) - Direct citizen feedback/threat report intake.
2. **CounterfeitLens** (`/counterfeit-lens`) - Image-based document/currency verification module.
3. **Dashboard** (`/dashboard`) - Unified system operational overview.
4. **Evidence** (`/evidence`) - Incident evidence logs and media timeline.
5. **FraudGraph** (`/fraud-graph`) - Relational mapping database for scam operations.
6. **GeoIntel** (`/geo-intel`) - Geographic density overlay maps.
7. **ScamShield** (`/scam-shield`) - URL/phishing scanner tool.
