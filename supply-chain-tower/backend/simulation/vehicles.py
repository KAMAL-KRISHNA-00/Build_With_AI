"""
simulation/vehicles.py — Vehicle Agent Class

Each VehicleAgent is an autonomous agent that:
  - Follows a route (list of graph node IDs)
  - Moves continuously between nodes using linear interpolation
  - Tracks its own risk score, status, and delivery stats
  - Can be rerouted mid-journey without teleporting
"""
import time
import math
from typing import List, Optional
from dataclasses import dataclass, field

from routing.graph import NODES


# Vehicle status codes
STATUS_ACTIVE    = "ACTIVE"
STATUS_REROUTING = "REROUTING"
STATUS_DELAYED   = "DELAYED"
STATUS_ARRIVED   = "ARRIVED"

# Color codes for frontend (matching the dark-theme design)
VEHICLE_COLORS = [
    "#00ffcc",   # TRK-001 cyan
    "#3b82f6",   # TRK-002 blue
    "#f59e0b",   # TRK-003 amber
    "#ef4444",   # TRK-004 red
    "#a855f7",   # TRK-005 purple
    "#10b981",   # TRK-006 emerald
]


@dataclass
class VehicleAgent:
    """
    Autonomous delivery vehicle agent.

    Position interpolation:
      - route is a list of node IDs: [A, B, C, D]
      - seg_index: index of the current segment (0 = A→B)
      - seg_progress: [0.0, 1.0] progress along the current segment
        0.0 = at node A, 1.0 = arrived at node B
    """
    id:           str
    source:       str
    destination:  str
    route:        List[str]         = field(default_factory=list)
    speed:        float             = 0.0008    # progress units / second
    seg_index:    int               = 0
    seg_progress: float             = 0.0
    status:       str               = STATUS_ACTIVE
    risk_score:   float             = 0.0
    color:        str               = "#00ffcc"
    delivered:    int               = 0
    total_delay:  float             = 0.0       # cumulative delay seconds
    reroute_count: int              = 0
    last_reroute_ts: float          = 0.0
    eta_ok:       bool              = True

    def current_position(self) -> dict:
        """
        Compute interpolated lat/lng from seg_index + seg_progress.
        Returns {"lat": float, "lng": float}.
        """
        if not self.route or len(self.route) < 2:
            # Parked at source
            node = NODES.get(self.source, {})
            return {"lat": node.get("lat", 10.1627), "lng": node.get("lng", 76.4358)}

        # Clamp to valid range
        idx = min(self.seg_index, len(self.route) - 2)
        a_id = self.route[idx]
        b_id = self.route[idx + 1]
        a    = NODES[a_id]
        b    = NODES[b_id]

        # Linear interpolation
        t    = max(0.0, min(1.0, self.seg_progress))
        lat  = a["lat"] + (b["lat"] - a["lat"]) * t
        lng  = a["lng"] + (b["lng"] - a["lng"]) * t
        return {"lat": round(lat, 6), "lng": round(lng, 6)}

    def tick(self, dt: float, graph) -> bool:
        """
        Advance vehicle position by dt seconds.
        Returns True if vehicle reached destination this tick.
        """
        if self.status == STATUS_ARRIVED or not self.route:
            return False
        if len(self.route) < 2:
            self.status = STATUS_ARRIVED
            return True

        # Advance progress along current segment
        # Speed is scaled by inverse of edge weight (heavier = slower)
        idx = min(self.seg_index, len(self.route) - 2)
        a, b = self.route[idx], self.route[idx + 1]
        edge_w = max(1.0, graph.weight(a, b))
        # Normalize: base_time=30 → nominal speed
        speed_factor    = 30.0 / edge_w
        self.seg_progress += self.speed * dt * speed_factor * 60

        # Moved to next segment
        while self.seg_progress >= 1.0 and self.seg_index < len(self.route) - 2:
            self.seg_progress -= 1.0
            self.seg_index    += 1

        # Reached destination
        if self.seg_progress >= 1.0 and self.seg_index >= len(self.route) - 2:
            self.status       = STATUS_ARRIVED
            self.seg_progress = 1.0
            self.delivered   += 1
            return True

        return False

    def reroute(self, new_route: List[str]):
        """
        Non-teleporting reroute: find the closest node in new_route to
        the vehicle's current position and continue from there.
        """
        if not new_route or len(new_route) < 2:
            return
        # Find current node (where the vehicle just passed through)
        current_node = self.route[self.seg_index] if self.route else self.source

        # Find if current_node exists in new_route, else start from beginning
        if current_node in new_route:
            new_idx = new_route.index(current_node)
            self.route        = new_route[new_idx:]
        else:
            self.route        = new_route

        self.seg_index    = 0
        self.seg_progress = 0.0
        self.status       = STATUS_ACTIVE
        self.reroute_count += 1
        self.last_reroute_ts = time.time()

    def reset_to_new_trip(self, new_source: str, new_dest: str, new_route: List[str]):
        """Start a fresh delivery after arriving."""
        self.source       = new_source
        self.destination  = new_dest
        self.route        = new_route
        self.seg_index    = 0
        self.seg_progress = 0.0
        self.status       = STATUS_ACTIVE

    def to_dict(self) -> dict:
        pos = self.current_position()
        return {
            "id":           self.id,
            "source":       self.source,
            "destination":  self.destination,
            "route":        self.route,
            "lat":          pos["lat"],
            "lng":          pos["lng"],
            "status":       self.status,
            "risk_score":   round(self.risk_score, 1),
            "color":        self.color,
            "delivered":    self.delivered,
            "reroutes":     self.reroute_count,
            "eta_ok":       self.eta_ok,
            "seg_index":    self.seg_index,
            "seg_progress": round(self.seg_progress, 4),
        }
