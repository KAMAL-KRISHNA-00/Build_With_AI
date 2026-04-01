# Autonomous Supply Chain Control Tower

> AI-powered real-time logistics simulation with autonomous rerouting, disruption management, and Gemini-generated insights.

---

## Problem Statement

Supply chain operations teams have no real-time visibility into fleet movement across a road network, and no fast mechanism to model how disruptions (accidents, weather, traffic jams) cascade into delivery delays. Manual rerouting is slow, reactive, and error-prone — costing time and money.

---

## Project Description

The **Autonomous Supply Chain Control Tower** is a full-stack real-time logistics platform that simulates a fleet of 6 autonomous freight vehicles navigating the Kerala, India road network. The system:

- **Continuously monitors** all vehicles on a live animated Google Maps dashboard
- **Autonomously reroutes** vehicles when route risk exceeds a configurable threshold — using a GA → A* → Dijkstra fallback chain
- **Injects disruptions** (accidents, weather, traffic jams, stress tests) via a point-and-click map interface
- **Explains every decision** in plain English using the Google Gemini AI API
- **Broadcasts live state** to all connected clients over WebSocket at 200ms intervals

The result is an AI-powered command center where operators can observe, simulate, and understand complex logistics scenarios in real time.

---

## Google AI Usage

### Tools / Models Used
- **Google Gemini API** — `gemini-2.0-flash-lite`
- **Google Maps JavaScript API** — live map rendering
- **Google Directions API** — real road geometry for vehicle paths

### How Google AI Was Used

Gemini is integrated directly into the simulation engine's **autonomous decision loop**:

1. **Reroute Explanations** — Every time a vehicle is autonomously rerouted due to high risk, Gemini generates a 2-sentence technical explanation referencing the specific vehicle ID, risk score, algorithm used, and road names. This appears in the live AI Insights panel.

2. **Disruption Analysis** — When an operator injects a disruption (e.g. ACCIDENT on KALADY↔ALUVA), Gemini provides a situational awareness update describing which roads are affected, which vehicles are impacted, and what rerouting action is being taken.

3. **Rate-Limited & Resilient** — A custom rate limiter enforces a 45-second cooldown between calls and a 5-minute deduplication window per event. On quota errors (429), the system parses the retry delay and falls back to rich pre-written explanations — the simulation never crashes or stalls.

---

## Proof of Google AI Usage

<!--  Add screenshots of the AI Insights panel and Gemini responses in the /proof folder -->

![AI Proof 1](./proof/screenshot1.png)
![AI Proof 2](./proof/screenshot2.png)

---

## Screenshots

<!--  Add project screenshots in the /assets folder -->

![Dashboard Overview](./assets/screenshot1.png)
![Disruption Injection](./assets/screenshot2.png)
![AI Insights Panel](./assets/screenshot3.png)

---

## Demo Video

<!--  Upload to Google Drive (max 3 minutes) and paste link below -->

[▶ Watch Demo](#)

---

## Installation Steps

### Prerequisites
- Python 3.11+
- Node.js 18+
- Google Gemini API key
- Google Maps API key (with Maps JS + Directions enabled)

### Backend (FastAPI)

```bash
# Clone the repository
git clone <your-repo-link>

# Go to backend folder
cd supply-chain-tower/backend

# Install Python dependencies
pip install -r requirements.txt

# Add your API keys to .env
# GEMINI_API_KEY=...
# GOOGLE_MAPS_API_KEY=...

# Start the backend server
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend (Next.js)

```bash
# Go to frontend folder
cd supply-chain-tower/frontend

# Install dependencies
npm install

# Add your keys to .env.local
# NEXT_PUBLIC_GOOGLE_MAPS_API_KEY=...
# NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
# NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws

# Run the dev server
npm run dev
```

Open **http://localhost:3000** in your browser.

---

## Live Demo

- 🌐 **Frontend:** [Vercel](#)
- ⚙️ **Backend API Docs:** [https://buildwithai-production.up.railway.app/docs](https://buildwithai-production.up.railway.app/docs)

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14, React 18, TypeScript |
| Backend | FastAPI, Uvicorn, Python 3.11 |
| AI | Google Gemini API (`gemini-2.0-flash-lite`) |
| Maps | Google Maps JS API + Directions API |
| Real-time | WebSockets |
| Pathfinding | A*, Genetic Algorithm, Dijkstra |
| Deployment | Vercel (frontend) + Railway (backend) |
