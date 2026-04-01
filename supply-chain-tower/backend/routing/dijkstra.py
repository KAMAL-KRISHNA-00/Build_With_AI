"""
routing/dijkstra.py — Dijkstra Shortest Path Algorithm
Baseline routing algorithm. Used to compare against A* and genetic routes.
Ignores heuristic info — explores all nodes uniformly by weight.

Returns: (path: List[str], total_cost: float)
"""
import heapq
import math
from typing import Dict, List, Optional, Tuple

from routing.graph import RoadGraph


def dijkstra(graph: RoadGraph,
             start: str,
             goal: str) -> Tuple[List[str], float]:
    """
    Dijkstra's algorithm on the dynamic road graph.

    Returns (path, cost). ([], inf) if unreachable.
    """
    if start == goal:
        return [start], 0.0

    dist: Dict[str, float]          = {start: 0.0}
    prev: Dict[str, Optional[str]]  = {start: None}
    pq:   list                      = [(0.0, start)]

    while pq:
        d, u = heapq.heappop(pq)

        if u == goal:
            return _reconstruct(prev, goal), d

        if d > dist.get(u, math.inf):
            continue

        for v in graph.neighbors(u):
            alt = d + graph.weight(u, v)
            if alt < dist.get(v, math.inf):
                dist[v] = alt
                prev[v] = u
                heapq.heappush(pq, (alt, v))

    return [], float("inf")


def _reconstruct(prev: Dict[str, Optional[str]], goal: str) -> List[str]:
    path, cur = [], goal
    while cur is not None:
        path.append(cur)
        cur = prev[cur]
    path.reverse()
    return path
