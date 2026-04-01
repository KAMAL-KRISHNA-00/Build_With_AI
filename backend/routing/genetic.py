"""
routing/genetic.py — Genetic Algorithm Route Optimizer
Evolves a population of candidate routes between two nodes.

Fitness = total_weight(route) + congestion_penalty
Lower fitness is better.

Steps:
  1. Generate initial population of k random valid paths (DFS with randomness)
  2. Evaluate fitness for each individual
  3. Tournament selection → crossover → mutation
  4. Repeat for N generations
  5. Return fittest path
"""
import random
from typing import List, Optional, Tuple

from routing.graph import RoadGraph
from routing.astar import astar
from config import GA_POPULATION, GA_GENERATIONS, GA_MUTATION_RATE


def genetic_route(graph: RoadGraph,
                  start: str,
                  goal: str,
                  occupied_edges: Optional[set] = None) -> Tuple[List[str], float]:
    """
    Find a near-optimal route using a Genetic Algorithm.

    Returns (best_path, best_cost).
    Falls back to A* if population generation fails.
    """
    population = _generate_population(graph, start, goal, GA_POPULATION)
    if not population:
        return astar(graph, start, goal, occupied_edges)

    for generation in range(GA_GENERATIONS):
        # Evaluate fitness for all individuals
        scored = [(fitness(graph, ind, occupied_edges), ind) for ind in population]
        scored.sort(key=lambda x: x[0])

        # Elitism: keep top 2 unchanged
        next_gen = [scored[0][1], scored[1][1]] if len(scored) >= 2 else [scored[0][1]]

        # Fill rest of population via selection + crossover + mutation
        while len(next_gen) < GA_POPULATION:
            parent_a = _tournament_select(scored)
            parent_b = _tournament_select(scored)
            child    = _crossover(parent_a, parent_b, graph, start, goal)
            child    = _mutate(child, graph, start, goal)
            if _is_valid(child, graph):
                next_gen.append(child)
            else:
                # If crossover/mutation failed, inherit elite
                next_gen.append(scored[0][1])

        population = next_gen

    # Return best after all generations
    final_scored = [(fitness(graph, p, occupied_edges), p) for p in population]
    final_scored.sort(key=lambda x: x[0])
    best_cost, best_path = final_scored[0]
    return best_path, best_cost


# ── Fitness Function ──────────────────────────────────────────────────────────
def fitness(graph: RoadGraph,
            path: List[str],
            occupied_edges: Optional[set] = None) -> float:
    """
    Compute route fitness (lower = better).
    total_weight + congestion penalty for shared edges.
    """
    if len(path) < 2:
        return float("inf")
    total = 0.0
    for i in range(len(path) - 1):
        a, b  = path[i], path[i + 1]
        w     = graph.weight(a, b)
        # Penalize edges occupied by other vehicles
        if occupied_edges and (a, b) in occupied_edges:
            w *= 1.8
        total += w
    return total


# ── Population Generation (Random DFS) ───────────────────────────────────────
def _generate_population(graph: RoadGraph, start: str,
                          goal: str, n: int) -> List[List[str]]:
    """Generate n distinct random valid paths from start to goal using DFS."""
    paths = []
    attempts = 0
    while len(paths) < n and attempts < n * 10:
        attempts += 1
        path = _random_dfs(graph, start, goal, max_depth=15)
        if path and path not in paths:
            paths.append(path)
    return paths


def _random_dfs(graph: RoadGraph, start: str,
                goal: str, max_depth: int) -> Optional[List[str]]:
    """Randomized DFS to find a valid path — introduces diversity."""
    stack = [(start, [start])]
    while stack:
        node, path = stack.pop()
        if node == goal:
            return path
        if len(path) >= max_depth:
            continue
        neighbors = graph.neighbors(node)
        random.shuffle(neighbors)   # randomize order for diversity
        for nb in neighbors:
            if nb not in path:      # avoid cycles
                stack.append((nb, path + [nb]))
    return None


# ── Crossover ────────────────────────────────────────────────────────────────
def _crossover(a: List[str], b: List[str],
               graph: RoadGraph, start: str, goal: str) -> List[str]:
    """
    Order crossover: find a common node between parents a and b,
    splice the prefix of a with the suffix of b at that node.
    """
    common = [n for n in a if n in b and n not in (start, goal)]
    if not common:
        return a   # no crossover point, return parent
    pivot = random.choice(common)
    ai = a.index(pivot)
    bi = b.index(pivot)
    child = a[:ai] + b[bi:]
    # Remove cycles in child
    return _remove_cycles(child)


def _remove_cycles(path: List[str]) -> List[str]:
    """Remove any loops in a path, keeping first occurrence of each node."""
    seen, result = set(), []
    for n in path:
        if n not in seen:
            result.append(n)
            seen.add(n)
    return result


# ── Mutation ──────────────────────────────────────────────────────────────────
def _mutate(path: List[str], graph: RoadGraph,
            start: str, goal: str) -> List[str]:
    """
    Randomly replace an intermediate node with an adjacent alternative,
    then reconnect the path segments.
    """
    if len(path) < 4 or random.random() > GA_MUTATION_RATE:
        return path

    # Pick a random intermediate node (not start/goal)
    idx = random.randint(1, len(path) - 2)
    alternatives = graph.neighbors(path[idx - 1])
    alternatives = [n for n in alternatives if n not in path or n == path[idx]]
    if not alternatives:
        return path

    new_node = random.choice(alternatives)
    # Rebuild: prefix → new_node → reconnect to suffix via DFS
    prefix = path[:idx] + [new_node]
    suffix_start = path[idx + 1] if idx + 1 < len(path) else goal
    reconnect = _random_dfs(graph, new_node, suffix_start, max_depth=8)
    if reconnect:
        return _remove_cycles(prefix[:-1] + reconnect + path[idx + 1:])
    return path


# ── Tournament Selection ──────────────────────────────────────────────────────
def _tournament_select(scored: List[Tuple[float, List[str]]],
                       k: int = 3) -> List[str]:
    """Select the fittest from k random candidates (tournament selection)."""
    candidates = random.sample(scored, min(k, len(scored)))
    candidates.sort(key=lambda x: x[0])
    return candidates[0][1]


# ── Validity Check ────────────────────────────────────────────────────────────
def _is_valid(path: List[str], graph: RoadGraph) -> bool:
    """Ensure path is connected (all consecutive nodes share an edge)."""
    if len(path) < 2:
        return False
    for i in range(len(path) - 1):
        if path[i + 1] not in graph.neighbors(path[i]):
            return False
    return True
