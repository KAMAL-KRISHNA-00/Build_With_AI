"""
ai/risk_engine.py — Route Risk Scoring Engine

Risk Formula:
  Risk = α * predicted_delay + β * congestion_level + γ * instability
  (all components normalized to 0–100 range, output is 0–100)

Where:
  α (ALPHA) = 0.45  — delay probability weight
  β (BETA)  = 0.35  — congestion weight
  γ (GAMMA) = 0.20  — historical instability weight
"""
from typing import List
from config import ALPHA, BETA, GAMMA, MAX_RISK_THRESHOLD
from ai.vertex_client import predict_delay_probability


class RiskEngine:
    """Computes risk scores for vehicle routes using multi-factor analysis."""

    def __init__(self, graph):
        self.graph = graph

    def score_route(self, route: List[str]) -> float:
        """
        Compute composite risk score for a route.

        Returns: float in [0, 100].  ≥ MAX_RISK_THRESHOLD = reroute needed.
        """
        if len(route) < 2:
            return 0.0

        n_edges = len(route) - 1

        # ── Component 1: Predicted Delay (Vertex AI or mock) ─────────────────
        delay_prob   = predict_delay_probability(route, self.graph)   # [0, 1]
        delay_score  = delay_prob * 100.0                              # [0, 100]

        # ── Component 2: Average Congestion Level ─────────────────────────────
        congestion_sum = sum(
            self.graph.congestion_level(route[i], route[i + 1])
            for i in range(n_edges)
        )
        congestion_score = (congestion_sum / n_edges) * 100.0          # [0, 100]

        # ── Component 3: Historical Instability ──────────────────────────────
        instability_sum = sum(
            self.graph.instability(route[i], route[i + 1])
            for i in range(n_edges)
        )
        instability_score = (instability_sum / n_edges) * 100.0        # [0, 100]

        # ── Composite Risk ────────────────────────────────────────────────────
        risk = (ALPHA * delay_score
                + BETA  * congestion_score
                + GAMMA * instability_score)

        return round(min(100.0, max(0.0, risk)), 1)

    def is_high_risk(self, route: List[str]) -> bool:
        return self.score_route(route) >= MAX_RISK_THRESHOLD

    def network_risk(self, vehicle_routes: dict) -> float:
        """Average risk across all active vehicle routes."""
        scores = [self.score_route(r) for r in vehicle_routes.values() if len(r) >= 2]
        return round(sum(scores) / len(scores), 1) if scores else 0.0

    def per_vehicle_risks(self, vehicles: list) -> dict:
        """Returns {vehicle_id: risk_score} for all vehicles."""
        return {
            v.id: self.score_route(v.route)
            for v in vehicles
        }
