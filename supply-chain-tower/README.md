# Autonomous Supply Chain Control Tower
> Real-time AI-powered logistics simulation | Kalady, Ernakulam, Kerala

## Architecture
```
Backend (FastAPI + Python)  ←──WebSocket──→  Frontend (Next.js 14)
     │                                              │
     ├── A* / Dijkstra / Genetic Algorithm          ├── Google Maps API
     ├── Kerala Road Network Graph (12 nodes)        ├── Live animated vehicles
     ├── Simulation Engine (6 autonomous agents)     ├── Risk gauge (SVG)
     ├── Risk Engine (α·delay + β·congestion)        ├── AI insights panel
     ├── Gemini API (NL explanations)                └── Disruption controls
     └── Vertex AI (delay prediction + mock)
```

## Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- Run from `d:\Projects\Build_with_AI\supply-chain-tower\`

---

### 1. Backend Setup

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Start the FastAPI server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Server runs at: **http://localhost:8000**  
API docs at: **http://localhost:8000/docs**

---

### 2. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start Next.js dev server
npm run dev
```

Dashboard at: **http://localhost:3000**

---

## Demo Flow

1. **Open** `http://localhost:3000` — 6 trucks appear moving on the Kerala map
2. **Watch** vehicles move along colored routes (Kalady ↔ Ernakulam ↔ Aluva etc.)
3. **Click ACCIDENT** → a random road gets disrupted (red edge highlight appears)
4. **Watch automatically**: affected vehicles reroute within seconds
5. **AI panel** shows Gemini's explanation of why the reroute happened
6. **Click TRAFFIC JAM** → more rerouting, risk gauge rises
7. **Click PAUSE** → simulation freezes, resume with same button
8. **Click WHAT-IF** → stress-test multiple routes simultaneously

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/init_simulation` | Reset and initialize simulation |
| GET | `/get_routes` | Current vehicle routes |
| POST | `/inject_event` | Inject disruption event |
| POST | `/reroute` | Manually reroute a vehicle |
| GET | `/risk_analysis` | Risk scores per vehicle |
| GET | `/graph_snapshot` | Current graph weights |
| POST | `/toggle_pause` | Pause/resume simulation |
| WS | `/ws` | Real-time state stream |

### Inject Event (example)
```bash
curl -X POST http://localhost:8000/inject_event \
  -H "Content-Type: application/json" \
  -d '{"type": "ACCIDENT", "edge": ["KALADY", "ALUVA"]}'
```

### Manual Reroute
```bash
curl -X POST http://localhost:8000/reroute \
  -H "Content-Type: application/json" \
  -d '{"vehicle_id": "TRK-001"}'
```

---

## Key Algorithms

### A* (Primary Routing)
- Haversine heuristic — never overestimates (admissible)
- Multi-agent anti-congestion: ×1.5 penalty on edges shared by 2+ vehicles
- File: `backend/routing/astar.py`

### Genetic Algorithm (Optimization)
- Population: 20 candidate routes
- Fitness: total_weight + congestion_penalty
- Tournament selection, path crossover, mutation
- 30 generations → near-global optimum
- File: `backend/routing/genetic.py`

### Risk Formula
```
Risk = 0.45 × predicted_delay + 0.35 × congestion_level + 0.20 × historical_instability
```
All components normalized 0–100. Rerouting triggered at Risk ≥ 70.  
File: `backend/ai/risk_engine.py`

### Reroute Decision Chain
```
Detected high risk → Genetic Algorithm → (if fails) A* → (if fails) Dijkstra
→ Reroute vehicle (non-teleporting) → Gemini explains decision
```

---

## Vertex AI

Set in `backend/.env` to enable real prediction:
```
VERTEX_PROJECT_ID=your-gcp-project
VERTEX_ENDPOINT_ID=your-endpoint-id
```
Leave blank → uses deterministic mock formula (sigmoid of traffic + risk avg).

---

## Kerala Road Network

12 nodes, ~20 edges:
`Kalady ↔ Aluva ↔ Angamaly ↔ Perumbavoor ↔ Ernakulam ↔ Kakkanad ↔ Muvattupuzha ↔ Kothamangalam ↔ Chalakudy ↔ Thrissur ↔ North Paravur ↔ Piravom`

Edge weights update every 5 seconds. Disruptions multiply weights (ACCIDENT: ×4.5, WHAT-IF: ×5.0).
