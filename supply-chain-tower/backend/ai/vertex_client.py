"""
ai/vertex_client.py — Vertex AI Delay Prediction Client

Calls a Vertex AI endpoint to predict delivery delay probability for a route.
Falls back to a deterministic mock formula when:
  - VERTEX_PROJECT_ID / VERTEX_ENDPOINT_ID not set
  - Endpoint unavailable

Mock formula:
  delay_prob = sigmoid(0.4 * avg_traffic_factor + 0.3 * avg_risk - 0.5)
"""
import math
import logging
from typing import List

from config import (VERTEX_PROJECT_ID, VERTEX_LOCATION,
                    VERTEX_ENDPOINT_ID, USE_VERTEX_MOCK)

logger = logging.getLogger(__name__)


def predict_delay_probability(route: List[str], graph) -> float:
    """
    Returns probability of delay (0.0–1.0) for a given route.
    Uses Vertex AI if configured, else mock formula.
    """
    if USE_VERTEX_MOCK:
        return _mock_delay_probability(route, graph)
    try:
        return _vertex_predict(route, graph)
    except Exception as exc:
        logger.warning(f"Vertex AI call failed ({exc}), using mock.")
        return _mock_delay_probability(route, graph)


def _mock_delay_probability(route: List[str], graph) -> float:
    """
    Deterministic mock: computes delay probability from graph edge stats.
    Returns value in [0, 1].
    """
    if len(route) < 2:
        return 0.0
    total_traffic = 0.0
    total_risk    = 0.0
    n_edges       = len(route) - 1
    for i in range(n_edges):
        e = graph.edges.get(route[i], {}).get(route[i + 1], {})
        total_traffic += e.get("traffic_factor", 1.0)
        total_risk    += e.get("risk_score", 10.0)
    avg_tf   = total_traffic / n_edges
    avg_risk = total_risk    / n_edges
    # Sigmoid activation on linear combination
    z = 0.4 * (avg_tf - 1.0) * 3 + 0.3 * (avg_risk / 100.0) * 5 - 0.5
    return _sigmoid(z)


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def _vertex_predict(route: List[str], graph) -> float:
    """
    Real Vertex AI endpoint call.
    Requires google-cloud-aiplatform SDK and valid project/endpoint config.
    """
    from google.cloud import aiplatform
    aiplatform.init(project=VERTEX_PROJECT_ID, location=VERTEX_LOCATION)
    endpoint = aiplatform.Endpoint(VERTEX_ENDPOINT_ID)

    # Build feature vector: [avg_traffic, avg_risk, route_length]
    n_edges      = max(1, len(route) - 1)
    total_traffic = sum(
        graph.edges.get(route[i], {}).get(route[i + 1], {}).get("traffic_factor", 1.0)
        for i in range(n_edges)
    )
    total_risk = sum(
        graph.edges.get(route[i], {}).get(route[i + 1], {}).get("risk_score", 10.0)
        for i in range(n_edges)
    )
    instances = [[
        total_traffic / n_edges,
        total_risk    / n_edges,
        float(n_edges),
    ]]
    response  = endpoint.predict(instances=instances)
    # Expect a single probability in first prediction
    return float(response.predictions[0])
