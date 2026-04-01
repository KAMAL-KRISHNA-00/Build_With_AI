"""
routing/graph.py — Kerala Road Network Graph
Represents the road network around Kalady, Ernakulam, Kerala as a weighted
undirected graph. Edge weights are dynamically updated to reflect traffic,
disruptions, and risk scores.

Node positions are real GPS coordinates (lat, lng).
Edges have:
  - base_time: base travel time in simulation-seconds
  - traffic_factor: 1.0 = nominal, >1 = congested
  - risk_score: 0–100
  - disruption_multiplier: applied during active disruptions
"""
import math
import random
import time
from typing import Dict, List, Optional, Tuple

# ── Node Definitions ─────────────────────────────────────────────────────────
# Each node: { id: { name, lat, lng } }
NODES: Dict[str, dict] = {
    "KALADY":       {"name": "Kalady",        "lat": 10.1627, "lng": 76.4358},
    "ALUVA":        {"name": "Aluva",          "lat": 10.1003, "lng": 76.3564},
    "ANGAMALY":     {"name": "Angamaly",       "lat": 10.1956, "lng": 76.3867},
    "PERUMBAVOOR":  {"name": "Perumbavoor",    "lat": 10.1082, "lng": 76.4693},
    "ERNAKULAM":    {"name": "Ernakulam",      "lat":  9.9312, "lng": 76.2673},
    "KAKKANAD":     {"name": "Kakkanad",       "lat": 10.0183, "lng": 76.3289},
    "MUVATTUPUZHA": {"name": "Muvattupuzha",   "lat":  9.9893, "lng": 76.5799},
    "KOTHAMANGALAM":{"name": "Kothamangalam",  "lat": 10.0647, "lng": 76.6327},
    "CHALAKUDY":    {"name": "Chalakudy",      "lat": 10.3006, "lng": 76.3326},
    "THRISSUR":     {"name": "Thrissur",       "lat": 10.5276, "lng": 76.2144},
    "NORTH_PARAVUR":{"name": "North Paravur",  "lat": 10.1483, "lng": 76.2152},
    "PIRAVOM":      {"name": "Piravom",        "lat": 10.0467, "lng": 76.5000},
}

# ── Edge Definitions ─────────────────────────────────────────────────────────
# Each edge: (node_a, node_b, base_time_seconds)
# base_time represents nominal travel time in simulation time units
EDGE_DEFINITIONS: List[Tuple[str, str, float]] = [
    ("KALADY",        "ALUVA",         30),
    ("KALADY",        "ANGAMALY",      25),
    ("KALADY",        "PERUMBAVOOR",   20),
    ("KALADY",        "PIRAVOM",       22),
    ("ALUVA",         "ANGAMALY",      20),
    ("ALUVA",         "ERNAKULAM",     35),
    ("ALUVA",         "CHALAKUDY",     40),
    ("ALUVA",         "NORTH_PARAVUR", 30),
    ("ANGAMALY",      "CHALAKUDY",     35),
    ("PERUMBAVOOR",   "MUVATTUPUZHA",  28),
    ("PERUMBAVOOR",   "KOTHAMANGALAM", 32),
    ("PERUMBAVOOR",   "PIRAVOM",       18),
    ("ERNAKULAM",     "KAKKANAD",      20),
    ("ERNAKULAM",     "NORTH_PARAVUR", 40),
    ("KAKKANAD",      "MUVATTUPUZHA",  30),
    ("KAKKANAD",      "PIRAVOM",       25),
    ("MUVATTUPUZHA",  "KOTHAMANGALAM", 22),
    ("CHALAKUDY",     "THRISSUR",      45),
    ("CHALAKUDY",     "NORTH_PARAVUR", 38),
    ("NORTH_PARAVUR", "ANGAMALY",      28),
]


class RoadGraph:
    """
    Dynamic weighted road graph for the Kalady/Ernakulam region.
    Edge weights update every few seconds to simulate real traffic conditions.
    """

    def __init__(self):
        self.nodes = NODES.copy()
        # adjacency: {node_id: {neighbor_id: edge_data_dict}}
        self.edges: Dict[str, Dict[str, dict]] = {n: {} for n in NODES}
        # historical instability tracking (moving average of weight changes)
        self._instability: Dict[str, Dict[str, float]] = {}
        self._last_weights: Dict[str, Dict[str, float]] = {}
        self._build_edges()
        self._weight_update_ts = time.time()

    def _build_edges(self):
        """Initialize all edges with base values."""
        for (a, b, base_time) in EDGE_DEFINITIONS:
            edge = {
                "base_time":              base_time,
                "traffic_factor":         1.0,
                "risk_score":             random.uniform(5, 20),
                "disruption_multiplier":  1.0,
                "disruption_type":        None,
            }
            self.edges[a][b] = edge
            self.edges[b][a] = edge.copy()   # undirected: share same dict
            self._instability.setdefault(a, {})[b] = 0.0
            self._instability.setdefault(b, {})[a] = 0.0
            self._last_weights.setdefault(a, {})[b] = self.weight(a, b)
            self._last_weights.setdefault(b, {})[a] = self.weight(b, a)

    # ── Weight Formula ────────────────────────────────────────────────────────
    def weight(self, a: str, b: str) -> float:
        """
        Dynamic edge weight:
          weight = base_travel_time × traffic_factor × disruption_multiplier
                   + risk_penalty
        """
        if b not in self.edges.get(a, {}):
            return float("inf")
        e = self.edges[a][b]
        traffic_penalty = e["base_time"] * (e["traffic_factor"] - 1.0) * 0.5
        risk_penalty    = e["risk_score"] * 0.3
        return (e["base_time"] * e["traffic_factor"] * e["disruption_multiplier"]
                + traffic_penalty + risk_penalty)

    def congestion_level(self, a: str, b: str) -> float:
        """Returns 0–1 congestion level for an edge."""
        e = self.edges.get(a, {}).get(b)
        if not e:
            return 0.0
        return min(1.0, (e["traffic_factor"] - 1.0) / 3.0)

    def instability(self, a: str, b: str) -> float:
        """Returns historical instability 0–1 for an edge."""
        return min(1.0, self._instability.get(a, {}).get(b, 0.0) / 50.0)

    # ── Dynamic Weight Updates ─────────────────────────────────────────────────
    def update_traffic(self):
        """
        Randomly drift traffic factors every tick to simulate real-world variance.
        Called by simulation engine every ~5 seconds.
        """
        for a in self.edges:
            for b, e in self.edges[a].items():
                # Random walk: traffic factor drifts ±0.1, clamped to [0.9, 4.0]
                drift = random.uniform(-0.12, 0.12)
                e["traffic_factor"] = max(0.9, min(4.0, e["traffic_factor"] + drift))
                e["risk_score"]     = max(0, min(100, e["risk_score"] + random.uniform(-3, 3)))

                # Track instability as moving average of absolute weight change
                new_w = self.weight(a, b)
                old_w = self._last_weights.get(a, {}).get(b, new_w)
                delta = abs(new_w - old_w)
                self._instability[a][b] = 0.85 * self._instability[a].get(b, 0) + 0.15 * delta
                self._last_weights.setdefault(a, {})[b] = new_w

    def apply_disruption(self, node_a: str, node_b: str,
                          multiplier: float, dtype: str):
        """Apply a disruption multiplier to an edge (both directions)."""
        for a, b in [(node_a, node_b), (node_b, node_a)]:
            if b in self.edges.get(a, {}):
                self.edges[a][b]["disruption_multiplier"] = multiplier
                self.edges[a][b]["disruption_type"]       = dtype
                self.edges[a][b]["risk_score"]            = min(100, self.edges[a][b]["risk_score"] + 40)

    def clear_disruption(self, node_a: str, node_b: str):
        """Remove a disruption from an edge."""
        for a, b in [(node_a, node_b), (node_b, node_a)]:
            if b in self.edges.get(a, {}):
                self.edges[a][b]["disruption_multiplier"] = 1.0
                self.edges[a][b]["disruption_type"]       = None
                self.edges[a][b]["risk_score"]            = max(5, self.edges[a][b]["risk_score"] - 35)

    def neighbors(self, node: str) -> List[str]:
        return list(self.edges.get(node, {}).keys())

    def get_snapshot(self) -> dict:
        """Return serializable graph snapshot for frontend."""
        edges_out = []
        seen = set()
        for a in self.edges:
            for b, e in self.edges[a].items():
                key = tuple(sorted([a, b]))
                if key not in seen:
                    seen.add(key)
                    edges_out.append({
                        "from":        a,
                        "to":          b,
                        "weight":      round(self.weight(a, b), 2),
                        "traffic":     round(e["traffic_factor"], 2),
                        "risk":        round(e["risk_score"], 1),
                        "disruption":  e["disruption_type"],
                        "multiplier":  e["disruption_multiplier"],
                    })
        return {"nodes": self.nodes, "edges": edges_out}


# ── Haversine Distance (used as A* heuristic) ─────────────────────────────────
def haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Returns great-circle distance in km (used as admissible A* heuristic)."""
    R = 6371.0
    φ1, φ2 = math.radians(lat1), math.radians(lat2)
    Δφ = math.radians(lat2 - lat1)
    Δλ = math.radians(lng2 - lng1)
    a = math.sin(Δφ/2)**2 + math.cos(φ1) * math.cos(φ2) * math.sin(Δλ/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
