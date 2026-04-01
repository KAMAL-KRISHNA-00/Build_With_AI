"""
disruptions/events.py — Disruption Event System
Defines injectable disruption events that modify graph edge weights.
Supports: ACCIDENT, WEATHER, TRAFFIC_JAM, WHAT_IF

Each event targets an edge (or multiple edges), applies a multiplier,
and auto-expires after a configured duration.
"""
import time
import uuid
from typing import List, Optional
from dataclasses import dataclass, field

from config import DISRUPTION_DURATIONS


@dataclass
class DisruptionEvent:
    """
    Represents an active disruption in the network.

    Attributes
    ----------
    id          : Unique event identifier.
    dtype       : Event type string (ACCIDENT, WEATHER, etc.)
    edges       : List of (node_a, node_b) tuples affected.
    multiplier  : Edge weight multiplier applied (e.g. 3.0 for accidents).
    start_time  : Unix timestamp when event was injected.
    duration    : How long (seconds) the event lasts.
    description : Human-readable description.
    """
    id:          str   = field(default_factory=lambda: str(uuid.uuid4())[:8])
    dtype:       str   = "TRAFFIC_JAM"
    edges:       List  = field(default_factory=list)
    multiplier:  float = 2.0
    start_time:  float = field(default_factory=time.time)
    duration:    float = 90.0
    description: str   = ""

    @property
    def is_expired(self) -> bool:
        return (time.time() - self.start_time) >= self.duration

    @property
    def remaining(self) -> float:
        return max(0.0, self.duration - (time.time() - self.start_time))


# ── Event Factory ─────────────────────────────────────────────────────────────
def make_accident(edge: tuple) -> DisruptionEvent:
    """
    Accident: severe weight multiplier on one edge.
    Simulates emergency situation blocking most of the lane.
    """
    return DisruptionEvent(
        dtype="ACCIDENT",
        edges=[edge],
        multiplier=4.5,
        duration=DISRUPTION_DURATIONS["ACCIDENT"],
        description=f"Accident blocking {edge[0]} ↔ {edge[1]}",
    )


def make_weather(edges: List[tuple]) -> DisruptionEvent:
    """
    Weather: moderate multiplier across multiple edges.
    Simulates heavy rainfall reducing all-road speeds.
    """
    return DisruptionEvent(
        dtype="WEATHER",
        edges=edges,
        multiplier=2.0,
        duration=DISRUPTION_DURATIONS["WEATHER"],
        description=f"Heavy rain affecting {len(edges)} routes",
    )


def make_traffic_jam(edge: tuple) -> DisruptionEvent:
    """
    Traffic jam: medium multiplier on a single edge.
    """
    return DisruptionEvent(
        dtype="TRAFFIC_JAM",
        edges=[edge],
        multiplier=3.0,
        duration=DISRUPTION_DURATIONS["TRAFFIC_JAM"],
        description=f"Traffic jam on {edge[0]} ↔ {edge[1]}",
    )


def make_what_if(edges: List[tuple]) -> DisruptionEvent:
    """
    What-if: high multiplier for scenario planning.
    Asks: what if these roads became impassable?
    """
    return DisruptionEvent(
        dtype="WHAT_IF",
        edges=edges,
        multiplier=5.0,
        duration=DISRUPTION_DURATIONS["WHAT_IF"],
        description=f"What-if scenario: blocking {len(edges)} edges",
    )


# ── Event Type to Factory Mapping ─────────────────────────────────────────────
EVENT_FACTORIES = {
    "ACCIDENT":    make_accident,
    "WEATHER":     make_weather,
    "TRAFFIC_JAM": make_traffic_jam,
    "WHAT_IF":     make_what_if,
}
