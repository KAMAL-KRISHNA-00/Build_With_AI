"""
main.py — FastAPI Application Entry Point
Supply Chain Control Tower Backend

Endpoints:
  GET  /init_simulation  → Initialize/reset simulation, return initial state
  GET  /get_routes       → Current vehicle routes
  POST /inject_event     → Inject a disruption event
  POST /reroute          → Manually reroute a specific vehicle
  GET  /risk_analysis    → Risk scores for all routes + network risk
  GET  /graph_snapshot   → Current graph weights
  WS   /ws               → Real-time WebSocket for simulation state

WebSocket broadcast: every SIMULATION_TICK_MS milliseconds
"""
import asyncio
import logging
import json
from contextlib import asynccontextmanager
from typing import Optional, Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from simulation.engine import SimulationEngine
from routing.astar import astar
from routing.genetic import genetic_route
from routing.graph import NODES

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Global Simulation Engine ──────────────────────────────────────────────────
engine = SimulationEngine()

# ── WebSocket Connection Manager ─────────────────────────────────────────────
class ConnectionManager:
    def __init__(self):
        self.active: Set[WebSocket] = set()

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.add(ws)
        logger.info(f"WS connected. Total: {len(self.active)}")

    def disconnect(self, ws: WebSocket):
        self.active.discard(ws)
        logger.info(f"WS disconnected. Total: {len(self.active)}")

    async def broadcast(self, data: dict):
        if not self.active:
            return
        payload = json.dumps(data, default=str)
        dead = set()
        for ws in self.active:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.add(ws)
        self.active -= dead

manager = ConnectionManager()

# ── App Lifecycle ─────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Register broadcast callback so engine can push to WebSocket clients
    engine.register_broadcast(manager.broadcast)
    engine.initialize()
    # Start simulation loop as background task
    loop_task = asyncio.create_task(engine.run_loop())
    yield
    loop_task.cancel()
    try:
        await loop_task
    except asyncio.CancelledError:
        pass

app = FastAPI(
    title="Supply Chain Control Tower",
    description="Autonomous logistics simulation with real-time rerouting",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Request Models ────────────────────────────────────────────────────────────
class InjectEventRequest(BaseModel):
    type:   str                      # ACCIDENT | WEATHER | TRAFFIC_JAM | WHAT_IF
    edge:   Optional[list] = None    # [node_a, node_b] — optional, picks random if omitted

class RerouteRequest(BaseModel):
    vehicle_id:  str
    destination: Optional[str] = None   # override destination or keep current

# ── REST Endpoints ────────────────────────────────────────────────────────────

@app.get("/init_simulation")
async def init_simulation():
    """
    Initialize or reset the simulation.
    Returns the initial state snapshot including graph and vehicle list.
    """
    engine.initialize()
    state = engine.get_state()
    return {
        "status":  "initialized",
        "nodes":   NODES,
        "state":   state,
    }


@app.get("/get_routes")
async def get_routes():
    """Return current routes for all vehicle agents."""
    return {
        v.id: {
            "route":       v.route,
            "source":      v.source,
            "destination": v.destination,
            "status":      v.status,
        }
        for v in engine.vehicles
    }


@app.post("/inject_event")
async def inject_event(req: InjectEventRequest):
    """
    Inject a disruption event into the simulation.
    Immediately affects graph weights and triggers rerouting for impacted vehicles.
    """
    valid_types = {"ACCIDENT", "WEATHER", "TRAFFIC_JAM", "WHAT_IF"}
    if req.type not in valid_types:
        raise HTTPException(400, f"type must be one of: {valid_types}")

    edge = tuple(req.edge) if req.edge else None
    result = await engine.inject_disruption(req.type, edge)
    return {"status": "injected", "event": result}


@app.post("/reroute")
async def manual_reroute(req: RerouteRequest):
    """
    Manually reroute a specific vehicle.
    Uses Genetic Algorithm → A* fallback.
    """
    vehicle = next((v for v in engine.vehicles if v.id == req.vehicle_id), None)
    if not vehicle:
        raise HTTPException(404, f"Vehicle {req.vehicle_id} not found")

    dst   = req.destination or vehicle.destination
    start = vehicle.route[vehicle.seg_index] if vehicle.route else vehicle.source

    occupied  = engine._compute_occupied_edges()
    new_route, cost = genetic_route(engine.graph, start, dst, occupied)
    if not new_route:
        new_route, cost = astar(engine.graph, start, dst, occupied)
    if not new_route:
        raise HTTPException(500, "Could not compute a valid route")

    old_route = vehicle.route.copy()
    vehicle.reroute(new_route)
    engine.total_reroutes += 1

    return {
        "status":     "rerouted",
        "vehicle_id": req.vehicle_id,
        "old_route":  old_route,
        "new_route":  new_route,
        "cost":       round(cost, 2),
    }


@app.get("/risk_analysis")
async def risk_analysis():
    """Return risk scores for all vehicles + network risk."""
    risks = engine.risk_engine.per_vehicle_risks(engine.vehicles)
    routes = {v.id: v.route for v in engine.vehicles}
    network = engine.risk_engine.network_risk(routes)
    return {
        "vehicle_risks": risks,
        "network_risk":  network,
        "threshold":     70,
        "high_risk":     [vid for vid, r in risks.items() if r >= 70],
    }


@app.get("/graph_snapshot")
async def graph_snapshot():
    """Return current graph state (node positions + dynamic edge weights)."""
    return engine.graph.get_snapshot()


@app.post("/toggle_pause")
async def toggle_pause():
    """Pause or resume the simulation. Broadcasts state immediately."""
    engine.paused = not engine.paused
    # Push updated paused state to all WebSocket clients right now
    if engine._broadcast_cb:
        await engine._broadcast_cb(engine.get_state())
    return {"paused": engine.paused}


# ── WebSocket Endpoint ────────────────────────────────────────────────────────
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    """
    Real-time WebSocket connection.
    Stays alive indefinitely — simulation engine broadcasts state every tick.
    Clients can send: {"action": "inject", "type": "ACCIDENT", "edge": ["A","B"]}
                   or {"action": "pause"}
    """
    await manager.connect(ws)
    # Send full initial state immediately on connect
    try:
        await ws.send_text(json.dumps(engine.get_state(), default=str))
    except Exception:
        manager.disconnect(ws)
        return

    # Keep alive loop — listen for client commands
    try:
        while True:
            try:
                # Wait up to 1s for a client message; timeout is normal (not an error)
                data = await asyncio.wait_for(ws.receive_text(), timeout=1.0)
                msg  = json.loads(data)
                if msg.get("action") == "inject":
                    edge = tuple(msg["edge"]) if msg.get("edge") else None
                    await engine.inject_disruption(msg.get("type", "TRAFFIC_JAM"), edge)
                elif msg.get("action") == "pause":
                    engine.paused = not engine.paused
            except asyncio.TimeoutError:
                continue   # ← no client message — keep loop alive, engine broadcasts state
            except json.JSONDecodeError:
                continue   # malformed message — ignore
    except WebSocketDisconnect:
        manager.disconnect(ws)
    except Exception as e:
        logger.error(f"WS error: {e}")
        manager.disconnect(ws)
