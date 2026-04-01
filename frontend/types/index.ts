// types/index.ts — Shared TypeScript interfaces for the Supply Chain Control Tower

export interface NodePosition {
    name: string;
    lat: number;
    lng: number;
}

export interface GraphEdge {
    from: string;
    to: string;
    weight: number;
    traffic: number;
    risk: number;
    disruption: string | null;
    multiplier: number;
}

export interface GraphSnapshot {
    nodes: Record<string, NodePosition>;
    edges: GraphEdge[];
}

export type VehicleStatus = 'ACTIVE' | 'REROUTING' | 'DELAYED' | 'ARRIVED';

export interface VehicleData {
    id: string;
    source: string;
    destination: string;
    route: string[];
    lat: number;
    lng: number;
    status: VehicleStatus;
    risk_score: number;
    color: string;
    delivered: number;
    reroutes: number;
    eta_ok: boolean;
    seg_index: number;
    seg_progress: number;
}

export interface Alert {
    ts: string;
    source: string;
    msg: string;
    type: 'INFO' | 'DISRUPTION' | 'REROUTE' | 'RESOLVED' | string;
}

export interface AIInsight {
    ts: string;
    vehicle: string;
    text: string;
    algo: string;
}

export interface ActiveDisruption {
    id: string;
    type: string;
    edges: [string, string][];
    remaining: number;
}

export interface SimMetrics {
    active_trucks: number;
    delivered: number;
    delayed: number;
    reroutes: number;
    avg_delay: number;
    efficiency: number;
    network_risk: number;
}

export interface SimState {
    type: string;
    sim_time: string;
    paused: boolean;
    vehicles: VehicleData[];
    graph: GraphSnapshot;
    alerts: Alert[];
    ai_insights: AIInsight[];
    disruptions: ActiveDisruption[];
    metrics: SimMetrics;
    risk_scores: Record<string, number>;
}

export type DisruptionType = 'ACCIDENT' | 'WEATHER' | 'TRAFFIC_JAM' | 'WHAT_IF';
