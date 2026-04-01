"""
simulation/engine.py — Core Simulation Engine

Orchestrates:
  1. All vehicle agents
  2. Graph weight updates
  3. Risk evaluation per vehicle
  4. Autonomous rerouting decisions (no user input needed)
  5. Disruption lifecycle management
  6. WebSocket broadcast pipeline

Tick loop runs at SIMULATION_TICK_MS milliseconds.
Traffic weights update every ~5 seconds.
Risk scores update every tick.
Rerouting triggered when risk ≥ MAX_RISK_THRESHOLD or disruption detected.
"""
import asyncio
import time
import random
import logging
from typing import List, Dict, Optional, Set, Callable, Awaitable

from routing.graph import RoadGraph, NODES
from routing.astar import astar
from routing.dijkstra import dijkstra
from routing.genetic import genetic_route
from simulation.vehicles import (
    VehicleAgent, VEHICLE_COLORS,
    STATUS_ACTIVE, STATUS_ARRIVED, STATUS_REROUTING
)
from ai.risk_engine import RiskEngine
from ai.gemini_client import explain_reroute, explain_disruption
from disruptions.events import DisruptionEvent, EVENT_FACTORIES
from config import (
    SIMULATION_TICK_MS, NUM_VEHICLES,
    MAX_RISK_THRESHOLD, BASE_SPEED
)

logger = logging.getLogger(__name__)

# ── Predefined Routes to cycle vehicles through ──────────────────────────────
# Each element: (source, destination)
ROUTE_PAIRS = [
    ("KALADY",        "ERNAKULAM"),
    ("ALUVA",         "MUVATTUPUZHA"),
    ("ANGAMALY",      "KOTHAMANGALAM"),
    ("PERUMBAVOOR",   "THRISSUR"),
    ("ERNAKULAM",     "KALADY"),
    ("KAKKANAD",      "ANGAMALY"),
]


class SimulationEngine:
    """
    Central simulation orchestrator.
    run_loop() is the main async loop driven by asyncio.
    """

    def __init__(self):
        self.graph        = RoadGraph()
        self.risk_engine  = RiskEngine(self.graph)
        self.vehicles:    List[VehicleAgent]    = []
        self.disruptions: List[DisruptionEvent] = []
        self.alerts:      List[dict]            = []     # event log
        self.ai_insights: List[dict]            = []     # Gemini messages
        self.paused       = False
        self.sim_time     = 0.0                          # total sim seconds
        self.total_delivered  = 0
        self.total_delayed    = 0
        self.total_reroutes   = 0
        self._last_traffic_update = 0.0
        self._last_risk_update    = 0.0
        self._broadcast_cb: Optional[Callable[[dict], Awaitable[None]]] = None
        self._initialized  = False

    def register_broadcast(self, callback: Callable[[dict], Awaitable[None]]):
        """Register the WebSocket broadcast function."""
        self._broadcast_cb = callback

    # ── Initialization ────────────────────────────────────────────────────────
    def initialize(self):
        """Create all vehicle agents with initial routes."""
        self.vehicles = []
        for i in range(NUM_VEHICLES):
            vid   = f"TRK-{i+1:03d}"
            src, dst = ROUTE_PAIRS[i % len(ROUTE_PAIRS)]
            route, cost  = astar(self.graph, src, dst)
            if not route:
                route = [src, dst]   # fallback
            agent = VehicleAgent(
                id          = vid,
                source      = src,
                destination = dst,
                route       = route,
                speed       = BASE_SPEED * random.uniform(0.85, 1.15),
                color       = VEHICLE_COLORS[i % len(VEHICLE_COLORS)],
            )
            self.vehicles.append(agent)
        self._initialized = True
        self._add_alert("SIM", "Supply Chain Control Tower initialized. All agents active.", "INFO")

    # ── Main Simulation Loop ──────────────────────────────────────────────────
    async def run_loop(self):
        """Async tick loop — runs indefinitely until cancelled."""
        if not self._initialized:
            self.initialize()

        tick_s = SIMULATION_TICK_MS / 1000.0   # seconds per tick

        while True:
            if not self.paused:
                await self._tick(tick_s)
            else:
                # Still broadcast when paused so clients see the paused=true flag
                if self._broadcast_cb:
                    await self._broadcast_cb(self.get_state())
            await asyncio.sleep(tick_s)

    async def _tick(self, dt: float):
        """Single simulation tick."""
        self.sim_time += dt

        # ── 1. Update traffic weights every 5 seconds ─────────────────────
        if self.sim_time - self._last_traffic_update > 5.0:
            self.graph.update_traffic()
            self._last_traffic_update = self.sim_time

        # ── 2. Expire disruptions ─────────────────────────────────────────
        for d in list(self.disruptions):
            if d.is_expired:
                for (a, b) in d.edges:
                    self.graph.clear_disruption(a, b)
                self.disruptions.remove(d)
                self._add_alert(d.dtype, f"Road cleared: {d.description}", "RESOLVED")

        # ── 3. Compute occupied edges (multi-agent anti-collision) ─────────
        occupied = self._compute_occupied_edges()

        # ── 4. Advance each vehicle ────────────────────────────────────────
        for vehicle in self.vehicles:
            arrived = vehicle.tick(dt, self.graph)
            if arrived:
                self.total_delivered += 1
                # Cycle to a new route
                await self._assign_new_route(vehicle, occupied)
                continue

            # ── 5. Risk evaluation and autonomous rerouting ────────────────
            risk = self.risk_engine.score_route(vehicle.route)
            vehicle.risk_score = risk
            vehicle.eta_ok     = risk < 50.0

            if risk >= MAX_RISK_THRESHOLD and vehicle.status != STATUS_REROUTING:
                if time.time() - vehicle.last_reroute_ts > 15.0:   # cooldown
                    await self._autonomous_reroute(vehicle, occupied, risk)

        # ── 6. Broadcast state to all WebSocket clients ───────────────────
        if self._broadcast_cb:
            state = self.get_state()
            await self._broadcast_cb(state)

    # ── Autonomous Rerouting ──────────────────────────────────────────────────
    async def _autonomous_reroute(self, vehicle: VehicleAgent,
                                   occupied: set, risk: float):
        """
        Autonomously reroute a high-risk vehicle without user input.
        Tries: Genetic Algorithm → A* → Dijkstra (fallback chain).
        """
        old_route    = vehicle.route.copy()
        vehicle.status = STATUS_REROUTING
        current_node = vehicle.route[vehicle.seg_index] if vehicle.route else vehicle.source

        # ── Try Genetic Algorithm first ──────────────────────────────────────
        new_route, cost = genetic_route(self.graph, current_node,
                                        vehicle.destination, occupied)
        algo_used   = "Genetic Algorithm"

        # ── Fall back to A* if GA didn't improve ────────────────────────────
        if not new_route or new_route == old_route[vehicle.seg_index:]:
            new_route, cost = astar(self.graph, current_node,
                                    vehicle.destination, occupied)
            algo_used = "A*"

        # ── Fall back to Dijkstra if A* failed ──────────────────────────────
        if not new_route:
            new_route, cost = dijkstra(self.graph, current_node, vehicle.destination)
            algo_used = "Dijkstra"

        if new_route and len(new_route) >= 2:
            # Find triggering disruption
            disruption = self._active_disruption_on_route(old_route)
            reason     = f"risk score {risk:.0f}/100" + (f" + {disruption}" if disruption else "")

            vehicle.reroute(new_route)
            self.total_reroutes += 1
            self._add_alert(
                vehicle.id,
                f"{vehicle.id} rerouted via {algo_used}. Risk: {risk:.0f}. {reason}",
                "REROUTE"
            )

            # Ask Gemini for explanation (non-blocking)
            try:
                explanation = await explain_reroute(
                    vehicle_id  = vehicle.id,
                    old_route   = old_route,
                    new_route   = new_route,
                    reason      = reason,
                    risk_score  = risk,
                    algo_used   = algo_used,
                    disruption  = disruption,
                )
                self._add_ai_insight(vehicle.id, explanation, algo_used)
            except Exception as e:
                logger.warning(f"Gemini explanation failed: {e}")
        else:
            vehicle.status = STATUS_ACTIVE   # no better route, stay

    async def _assign_new_route(self, vehicle: VehicleAgent, occupied: set):
        """Cycle vehicle to a new trip after arrival."""
        # Pick a new random source/destination pair
        pairs = [p for p in ROUTE_PAIRS if p[0] != vehicle.destination]
        new_src, new_dst = random.choice(pairs) if pairs else (vehicle.destination, vehicle.source)
        new_route, _ = astar(self.graph, new_src, new_dst, occupied)
        if not new_route:
            new_route, _ = dijkstra(self.graph, new_src, new_dst)
        if not new_route:
            new_route = [new_src, new_dst]
        vehicle.reset_to_new_trip(new_src, new_dst, new_route)

    # ── Multi-Agent Collision Avoidance ───────────────────────────────────────
    def _compute_occupied_edges(self) -> Set[tuple]:
        """
        Returns set of (a, b) edges currently occupied by vehicles.
        Edges used by 2+ vehicles get a penalty in routing algorithms.
        """
        edge_count: Dict[tuple, int] = {}
        for v in self.vehicles:
            if v.route and len(v.route) >= 2:
                idx = min(v.seg_index, len(v.route) - 2)
                edge = (v.route[idx], v.route[idx + 1])
                edge_count[edge] = edge_count.get(edge, 0) + 1
        return {e for e, cnt in edge_count.items() if cnt >= 2}

    # ── Disruption Injection (called by API) ─────────────────────────────────
    async def inject_disruption(self, dtype: str,
                                 edge: Optional[tuple] = None) -> dict:
        """
        Inject a disruption event. If no edge given, picks a random network edge.
        Returns created event info.
        """
        if edge is None:
            # Pick a random heavily-trafficked edge
            all_edges = [(a, b) for a in self.graph.edges
                         for b in self.graph.edges[a] if a < b]
            edge = random.choice(all_edges)

        factory = EVENT_FACTORIES.get(dtype, EVENT_FACTORIES["TRAFFIC_JAM"])

        if dtype in ("WEATHER", "WHAT_IF"):
            # These affect multiple adjacent edges
            neighbors = self.graph.neighbors(edge[0])
            extra = [(edge[0], nb) for nb in neighbors[:2]]
            event = factory([edge] + extra)
        else:
            event = factory(edge)

        self.disruptions.append(event)

        # Apply to graph
        for (a, b) in event.edges:
            self.graph.apply_disruption(a, b, event.multiplier, dtype)

        # Identify impacted vehicles
        impacted = self._vehicles_on_edges(event.edges)

        # Log alert
        self._add_alert(dtype, event.description, "DISRUPTION")

        # Gemini network-level explanation
        try:
            explanation = await explain_disruption(dtype, event.edges,
                                                    [v.id for v in impacted])
            self._add_ai_insight("NETWORK", explanation, "AI Analysis")
        except Exception as e:
            logger.warning(f"Gemini disruption explain error: {e}")

        # Immediately trigger rerouting for impacted vehicles
        occupied = self._compute_occupied_edges()
        for v in impacted:
            if time.time() - v.last_reroute_ts > 5.0:
                await self._autonomous_reroute(v, occupied, v.risk_score)

        return {
            "event_id":    event.id,
            "type":        event.dtype,
            "edges":       event.edges,
            "multiplier":  event.multiplier,
            "duration":    event.duration,
            "description": event.description,
            "impacted":    [v.id for v in impacted],
        }

    def _vehicles_on_edges(self, edges: List[tuple]) -> List[VehicleAgent]:
        """Find vehicles whose current or upcoming route passes through given edges."""
        impacted = []
        edge_set = set(tuple(e) for e in edges) | set((b, a) for a, b in edges)
        for v in self.vehicles:
            route_edges = set(
                (v.route[i], v.route[i + 1])
                for i in range(len(v.route) - 1)
            )
            if route_edges & edge_set:
                impacted.append(v)
        return impacted

    def _active_disruption_on_route(self, route: List[str]) -> Optional[str]:
        """Return type of first active disruption on given route."""
        for d in self.disruptions:
            for (a, b) in d.edges:
                for i in range(len(route) - 1):
                    if (route[i] == a and route[i+1] == b) or \
                       (route[i] == b and route[i+1] == a):
                        return d.dtype
        return None

    # ── Alert and Insight Log ─────────────────────────────────────────────────
    def _add_alert(self, source: str, message: str, atype: str):
        entry = {
            "ts":     self._sim_timestamp(),
            "source": source,
            "msg":    message,
            "type":   atype,
        }
        self.alerts = [entry] + self.alerts[:49]   # keep last 50

    def _add_ai_insight(self, vehicle_id: str, text: str, algo: str):
        entry = {
            "ts":         self._sim_timestamp(),
            "vehicle":    vehicle_id,
            "text":       text,
            "algo":       algo,
        }
        self.ai_insights = [entry] + self.ai_insights[:9]   # keep last 10

    def _sim_timestamp(self) -> str:
        h = int(self.sim_time // 3600)
        m = int((self.sim_time % 3600) // 60)
        s = int(self.sim_time % 60)
        return f"{h:02d}:{m:02d}:{s:02d}"

    # ── State Snapshot for WebSocket ─────────────────────────────────────────
    def get_state(self) -> dict:
        """Return full simulation state for broadcast."""
        risks    = {v.id: v.risk_score for v in self.vehicles}
        n_risk   = self.risk_engine.network_risk({v.id: v.route for v in self.vehicles})
        delayed  = sum(1 for v in self.vehicles if not v.eta_ok)
        avg_delay = (sum(v.total_delay for v in self.vehicles) / max(1, len(self.vehicles)))
        efficiency = max(0.0, 100.0 - min(100.0, n_risk))

        return {
            "type":       "STATE",
            "sim_time":   self._sim_timestamp(),
            "paused":     self.paused,
            "vehicles":   [v.to_dict() for v in self.vehicles],
            "graph":      self.graph.get_snapshot(),
            "alerts":     self.alerts[:20],
            "ai_insights": self.ai_insights[:5],
            "disruptions": [
                {
                    "id":        d.id,
                    "type":      d.dtype,
                    "edges":     d.edges,
                    "remaining": round(d.remaining, 0),
                }
                for d in self.disruptions
            ],
            "metrics": {
                "active_trucks": len([v for v in self.vehicles if v.status != STATUS_ARRIVED]),
                "delivered":     self.total_delivered,
                "delayed":       delayed,
                "reroutes":      self.total_reroutes,
                "avg_delay":     round(avg_delay, 1),
                "efficiency":    round(efficiency, 1),
                "network_risk":  n_risk,
            },
            "risk_scores": risks,
        }
