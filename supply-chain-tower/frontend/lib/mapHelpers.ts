// lib/mapHelpers.ts — Map utility functions

/**
 * Linear interpolation between two values.
 * t=0 → a, t=1 → b
 */
export function lerp(a: number, b: number, t: number): number {
    return a + (b - a) * Math.clamp(t, 0, 1);
}

declare global {
    interface Math {
        clamp(val: number, min: number, max: number): number;
    }
}
Math.clamp = (val: number, min: number, max: number) =>
    Math.max(min, Math.min(max, val));

/**
 * Haversine distance in km between two lat/lng points.
 */
export function haversineKm(
    lat1: number, lng1: number,
    lat2: number, lng2: number
): number {
    const R = 6371;
    const dLat = ((lat2 - lat1) * Math.PI) / 180;
    const dLng = ((lng2 - lng1) * Math.PI) / 180;
    const a =
        Math.sin(dLat / 2) ** 2 +
        Math.cos((lat1 * Math.PI) / 180) *
        Math.cos((lat2 * Math.PI) / 180) *
        Math.sin(dLng / 2) ** 2;
    return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

/**
 * Risk color: green → yellow → red based on score 0–100.
 */
export function riskColor(score: number): string {
    if (score < 35) return '#10b981';   // emerald
    if (score < 60) return '#f59e0b';   // amber
    if (score < 80) return '#ef4444';   // red
    return '#dc2626';                    // dark red
}

/**
 * Status badge color for vehicle cards.
 */
export function statusColor(status: string): string {
    switch (status) {
        case 'ACTIVE': return '#10b981';
        case 'REROUTING': return '#f59e0b';
        case 'DELAYED': return '#ef4444';
        case 'ARRIVED': return '#3b82f6';
        default: return '#6b7280';
    }
}

/**
 * Alert type to color mapping.
 */
export function alertColor(type: string): string {
    switch (type) {
        case 'DISRUPTION': return '#ef4444';
        case 'REROUTE': return '#f59e0b';
        case 'RESOLVED': return '#10b981';
        case 'INFO': return '#3b82f6';
        default: return '#6b7280';
    }
}

/**
 * Create SVG marker icon for a vehicle (colored triangle).
 */
export function createVehicleIcon(color: string, status: string): google.maps.Symbol {
    // Triangle pointing right (→) as a custom path
    const scale = status === 'REROUTING' ? 9 : 8;
    return {
        path: 'M 0,-1 L 0.866,0.5 L -0.866,0.5 Z',  // equilateral triangle
        fillColor: color,
        fillOpacity: 1.0,
        strokeColor: status === 'REROUTING' ? '#ffffff' : color,
        strokeWeight: status === 'REROUTING' ? 2 : 0,
        scale,
        rotation: 90,
    };
}

/**
 * Disruption type icon mapping.
 */
export const DISRUPTION_ICONS: Record<string, string> = {
    ACCIDENT: '⚠',
    WEATHER: '☁',
    TRAFFIC_JAM: '↺',
    WHAT_IF: '◈',
};

export const DISRUPTION_LABELS: Record<string, string> = {
    ACCIDENT: 'ACCIDENT',
    WEATHER: 'WEATHER',
    TRAFFIC_JAM: 'TRAFFIC JAM',
    WHAT_IF: 'WHAT-IF',
};

/**
 * Node IDs to human-readable labels.
 */
export function nodeLabel(id: string): string {
    return id.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}
