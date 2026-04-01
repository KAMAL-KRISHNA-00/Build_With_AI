"""
config.py — Central configuration for Supply Chain Control Tower Backend
All environment variables and constants are loaded here.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ── API Keys ────────────────────────────────────────────────────────────────
GEMINI_API_KEY      = os.getenv("GEMINI_API_KEY", "")
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")

# ── Vertex AI ────────────────────────────────────────────────────────────────
VERTEX_PROJECT_ID  = os.getenv("VERTEX_PROJECT_ID", "")
VERTEX_LOCATION    = os.getenv("VERTEX_LOCATION", "us-central1")
VERTEX_ENDPOINT_ID = os.getenv("VERTEX_ENDPOINT_ID", "")
USE_VERTEX_MOCK    = not bool(VERTEX_PROJECT_ID and VERTEX_ENDPOINT_ID)

# ── Simulation Constants ─────────────────────────────────────────────────────
SIMULATION_TICK_MS   = int(os.getenv("SIMULATION_TICK_MS", "100"))   # ms between ticks
NUM_VEHICLES         = int(os.getenv("NUM_VEHICLES", "6"))
MAX_RISK_THRESHOLD   = float(os.getenv("MAX_RISK_THRESHOLD", "70"))   # auto-reroute above this

# ── Risk Weights (α, β, γ) ──────────────────────────────────────────────────
ALPHA = 0.45   # weight for predicted delay
BETA  = 0.35   # weight for congestion level
GAMMA = 0.20   # weight for historical instability

# ── Algorithm Params ────────────────────────────────────────────────────────
GA_POPULATION   = 20    # genetic algorithm population size
GA_GENERATIONS  = 30    # generations to evolve
GA_MUTATION_RATE = 0.15 # mutation probability per gene

# ── Disruption Duration (seconds) ───────────────────────────────────────────
DISRUPTION_DURATIONS = {
    "ACCIDENT":    120,
    "WEATHER":     180,
    "TRAFFIC_JAM":  90,
    "WHAT_IF":     300,
}

# ── Vehicle Speed (progress units/second along route segment) ───────────────
BASE_SPEED = 0.012   # segment crosses in ~10-15 sim-seconds at normal traffic
