"""
routing/astar.py — A* Shortest Path Algorithm
Uses haversine distance as an admissible heuristic (never overestimates).
Accounts for dynamic edge weights (traffic + disruption + risk).

Returns: (path: List[str], total_cost: float)
"""
import heapq
import math
from typing import Dict, List, Optional, Tuple

from routing.graph import RoadGraph, haversine


def astar(graph: RoadGraph,
          start: str,
          goal: str,
          occupied_edges: Optional[set] = None) -> Tuple[List[str], float]:
    """
    A* search on the dynamic road graph.

    Parameters
    ----------
    graph         : RoadGraph instance with current weights.
    start         : Source node ID.
    goal          : Destination node ID.
    occupied_edges: Set of (a, b) tuples representing edges heavily used
                   by other vehicles (multi-agent anti-congestion).

    Returns
    -------
    (path, cost) where path is list of node IDs, cost is total weight.
    Returns ([], inf) if no path found.
    """
    if start == goal:
        return [start], 0.0

    # ── Heuristic: straight-line distance scaled to time units ───────────────
    def h(node: str) -> float:
        n  = graph.nodes[node]
        g  = graph.nodes[goal]
        km = haversine(n["lat"], n["lng"], g["lat"], g["lng"])
        # Scale: ~40 km/h average → km / 40 * 3600 seconds
        # In our sim-time units (base_time in sim-seconds): km * 0.9
        return km * 0.9

    # ── Priority queue: (f_score, g_score, node) ────────────────────────────
    open_set: list = []
    heapq.heappush(open_set, (h(start), 0.0, start))

    came_from: Dict[str, Optional[str]] = {start: None}
    g_score:   Dict[str, float]         = {start: 0.0}

    while open_set:
        f, g, current = heapq.heappop(open_set)

        if current == goal:
            return _reconstruct(came_from, goal), g

        # Skip stale entries
        if g > g_score.get(current, math.inf):
            continue

        for neighbor in graph.neighbors(current):
            # Base edge weight
            edge_w = graph.weight(current, neighbor)

            # Multi-agent penalty: if another vehicle is using this edge,
            # add a congestion surcharge to encourage alternative routes
            if occupied_edges and (current, neighbor) in occupied_edges:
                edge_w *= 1.5

            tentative_g = g + edge_w

            if tentative_g < g_score.get(neighbor, math.inf):
                came_from[neighbor] = current
                g_score[neighbor]   = tentative_g
                f_new               = tentative_g + h(neighbor)
                heapq.heappush(open_set, (f_new, tentative_g, neighbor))

    return [], float("inf")   # no path found


def _reconstruct(came_from: Dict[str, Optional[str]], goal: str) -> List[str]:
    """Trace back the optimal path from came_from map."""
    path, current = [], goal
    while current is not None:
        path.append(current)
        current = came_from[current]
    path.reverse()
    return path
