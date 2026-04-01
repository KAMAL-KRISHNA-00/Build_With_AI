'use client';
/**
 * components/MapView.tsx — Full-featured map with:
 *  1. Google Maps dark base layer
 *  2. Directions API: real road paths for every edge (cached, fallback to straight)
 *  3. Canvas overlay: vehicles moving along REAL road geometry at 60fps
 *  4. Interactive edge selection: click a road segment to select it for disruption
 *  5. Smooth lerp interpolation between 100ms state updates
 */

import { useEffect, useRef, useCallback } from 'react';
import { Loader } from '@googlemaps/js-api-loader';
import { SimState, VehicleData, GraphSnapshot } from '@/types';

const API_KEY = process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY!;
const MAP_CENTER = { lat: 10.06, lng: 76.38 };
const MAP_ZOOM = 9;

const DARK_STYLE: google.maps.MapTypeStyle[] = [
    { elementType: 'geometry', stylers: [{ color: '#060c1a' }] },
    { elementType: 'labels.text.fill', stylers: [{ color: '#1e3050' }] },
    { elementType: 'labels.text.stroke', stylers: [{ color: '#060c1a' }] },
    { featureType: 'administrative', elementType: 'geometry', stylers: [{ visibility: 'off' }] },
    { featureType: 'administrative.locality', elementType: 'labels.text.fill', stylers: [{ color: '#2a4060' }] },
    { featureType: 'poi', stylers: [{ visibility: 'off' }] },
    { featureType: 'road', elementType: 'geometry', stylers: [{ color: '#0a1526' }] },
    { featureType: 'road', elementType: 'geometry.stroke', stylers: [{ color: '#060f1c' }] },
    { featureType: 'road.highway', elementType: 'geometry', stylers: [{ color: '#0d1e34' }] },
    { featureType: 'transit', stylers: [{ visibility: 'off' }] },
    { featureType: 'water', elementType: 'geometry', stylers: [{ color: '#020810' }] },
];

export interface MapViewProps {
    simState: SimState | null;
    pendingDisruption: string | null;           // set when a disruption button was clicked
    onEdgeSelected: (edgeKey: string, from: string, to: string) => void;  // callback with selected edge
    onCancelSelect: () => void;
}

// ── Module-level mutable state (accessed by rAF loop) ─────────────────────────
let _simState: SimState | null = null;
let _pendingDisruption: string | null = null;

// Smooth canvas positions: vehicleId → {x,y}
const _smooth: Record<string, { x: number; y: number }> = {};

// Real road paths cache: "FROM-TO" → array of {lat,lng} points
const _roadCache: Record<string, { lat: number; lng: number }[]> = {};
const _fetchInProgress = new Set<string>();

// Currently hovered/selected edge key
let _hoveredEdge: string | null = null;

export default function MapView({ simState, pendingDisruption, onEdgeSelected, onCancelSelect }: MapViewProps) {
    _simState = simState;
    _pendingDisruption = pendingDisruption;

    const mapDivRef = useRef<HTMLDivElement>(null);
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const mapRef = useRef<google.maps.Map | null>(null);
    const dirSvcRef = useRef<google.maps.DirectionsService | null>(null);
    const rafRef = useRef<number | null>(null);
    const loadedRef = useRef(false);
    // Store callbacks in refs so the map click listener always sees the latest version
    const onEdgeSelectedRef = useRef(onEdgeSelected);
    const onCancelSelectRef = useRef(onCancelSelect);
    useEffect(() => { onEdgeSelectedRef.current = onEdgeSelected; }, [onEdgeSelected]);
    useEffect(() => { onCancelSelectRef.current = onCancelSelect; }, [onCancelSelect]);

    // ── Fetch real road path for an edge via Directions API ──────────────────
    const fetchRoadPath = useCallback(async (
        from: string, to: string,
        fromLat: number, fromLng: number,
        toLat: number, toLng: number,
    ) => {
        const key = `${from}-${to}`;
        const rkey = `${to}-${from}`;
        if (_roadCache[key] || _roadCache[rkey] || _fetchInProgress.has(key)) return;
        _fetchInProgress.add(key);

        // Stagger requests to avoid rate limiting
        await new Promise(r => setTimeout(r, Object.keys(_roadCache).length * 150));

        if (!dirSvcRef.current) {
            _roadCache[key] = [{ lat: fromLat, lng: fromLng }, { lat: toLat, lng: toLng }];
            _fetchInProgress.delete(key);
            return;
        }
        try {
            const result = await dirSvcRef.current.route({
                origin: { lat: fromLat, lng: fromLng },
                destination: { lat: toLat, lng: toLng },
                travelMode: google.maps.TravelMode.DRIVING,
            });
            const path = result.routes[0]?.overview_path ?? [];
            _roadCache[key] = path.map(p => ({ lat: p.lat(), lng: p.lng() }));
        } catch {
            // Directions API failed — use straight line
            _roadCache[key] = [{ lat: fromLat, lng: fromLng }, { lat: toLat, lng: toLng }];
        }
        _fetchInProgress.delete(key);
    }, []);

    // ── Pre-fetch all edge road paths when graph arrives ─────────────────────
    useEffect(() => {
        if (!simState?.graph || !dirSvcRef.current) return;
        const { nodes, edges } = simState.graph;
        edges.forEach(edge => {
            const fn = nodes[edge.from], tn = nodes[edge.to];
            if (!fn || !tn) return;
            fetchRoadPath(edge.from, edge.to, fn.lat, fn.lng, tn.lat, tn.lng);
        });
    }, [simState?.graph, fetchRoadPath]);

    // ── Map init ──────────────────────────────────────────────────────────────
    useEffect(() => {
        if (loadedRef.current) return;
        loadedRef.current = true;

        new Loader({ apiKey: API_KEY, version: 'weekly', libraries: ['geometry'] }).load().then(() => {
            if (!mapDivRef.current || !canvasRef.current) return;
            const map = new google.maps.Map(mapDivRef.current, {
                center: MAP_CENTER, zoom: MAP_ZOOM, styles: DARK_STYLE,
                disableDefaultUI: true, zoomControl: true, gestureHandling: 'greedy',
            });
            mapRef.current = map;
            dirSvcRef.current = new google.maps.DirectionsService();

            // Map click handler for edge selection
            // NOTE: uses refs so this listener always calls the *latest* callbacks
            // even though the useEffect only runs once.
            map.addListener('click', (e: google.maps.MapMouseEvent) => {
                if (!_pendingDisruption || !_simState?.graph || !e.latLng) return;
                const clickLat = e.latLng.lat();
                const clickLng = e.latLng.lng();
                // Find closest road edge to click point
                let closest: { key: string; from: string; to: string; dist: number } | null = null;
                _simState.graph.edges.forEach(edge => {
                    const fn = _simState!.graph.nodes[edge.from];
                    const tn = _simState!.graph.nodes[edge.to];
                    if (!fn || !tn) return;
                    // Distance from click to edge midpoint
                    const midLat = (fn.lat + tn.lat) / 2;
                    const midLng = (fn.lng + tn.lng) / 2;
                    const dist = Math.hypot(clickLat - midLat, clickLng - midLng);
                    if (!closest || dist < closest.dist) {
                        closest = { key: `${edge.from}-${edge.to}`, from: edge.from, to: edge.to, dist };
                    }
                });
                if (closest && (closest as any).dist < 0.2) {
                    onEdgeSelectedRef.current((closest as any).key, (closest as any).from, (closest as any).to);
                } else {
                    onCancelSelectRef.current();
                }
            });

            // Start render loop after tiles load
            google.maps.event.addListenerOnce(map, 'tilesloaded', () => {
                const canvas = canvasRef.current!;
                let prev = performance.now();
                const tick = (now: number) => {
                    const dt = Math.min((now - prev) / 1000, 0.1);
                    prev = now;
                    renderFrame(canvas, map, dt);
                    rafRef.current = requestAnimationFrame(tick);
                };
                rafRef.current = requestAnimationFrame(tick);
            });
        });

        return () => { if (rafRef.current) cancelAnimationFrame(rafRef.current); };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []); // intentionally empty — callbacks are accessed via refs above

    const cursor = pendingDisruption ? 'crosshair' : 'grab';

    return (
        <div style={{ position: 'relative', width: '100%', height: '100%' }}>
            <div ref={mapDivRef} style={{ width: '100%', height: '100%', cursor }} />
            <canvas
                ref={canvasRef}
                style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', pointerEvents: 'none' }}
            />
            {/* Selection mode banner */}
            {pendingDisruption && (
                <div style={{
                    position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%,-50%)',
                    background: 'rgba(6,11,21,0.9)', border: '1px solid #ef4444',
                    borderRadius: 8, padding: '12px 24px', color: '#ef4444',
                    fontFamily: 'Share Tech Mono, monospace', fontSize: '0.8rem',
                    letterSpacing: '0.1em', textAlign: 'center', pointerEvents: 'none',
                    animation: 'pulse 1.5s ease-in-out infinite',
                    boxShadow: '0 0 20px rgba(239,68,68,0.3)',
                }}>
                    ⚠ CLICK A ROAD SEGMENT TO INJECT {pendingDisruption}<br />
                    <span style={{ fontSize: '0.6rem', color: '#ef444499' }}>Click anywhere else to cancel</span>
                </div>
            )}
        </div>
    );
}

// ── Render frame ───────────────────────────────────────────────────────────────
function renderFrame(canvas: HTMLCanvasElement, map: google.maps.Map, dt: number) {
    const bounds = map.getBounds();
    if (!bounds) return;
    const w = canvas.offsetWidth, h = canvas.offsetHeight;
    if (!w || !h) return;
    if (canvas.width !== w) canvas.width = w;
    if (canvas.height !== h) canvas.height = h;

    const ctx = canvas.getContext('2d')!;
    ctx.clearRect(0, 0, w, h);
    const state = _simState;
    if (!state?.graph) return;

    const ne = bounds.getNorthEast(), sw = bounds.getSouthWest();
    const lngSpan = ne.lng() - sw.lng(), latSpan = ne.lat() - sw.lat();
    if (!lngSpan || !latSpan) return;

    const toXY = (lat: number, lng: number) => ({
        x: ((lng - sw.lng()) / lngSpan) * w,
        y: ((ne.lat() - lat) / latSpan) * h,
    });

    // Node pixel positions
    const px: Record<string, { x: number; y: number }> = {};
    Object.entries(state.graph.nodes).forEach(([id, n]) => { px[id] = toXY(n.lat, n.lng); });

    // ── Draw real-road edge paths ─────────────────────────────────────────────
    const isPending = !!_pendingDisruption;
    state.graph.edges.forEach(edge => {
        const fn = state.graph.nodes[edge.from], tn = state.graph.nodes[edge.to];
        if (!fn || !tn) return;

        const key = `${edge.from}-${edge.to}`;
        const rkey = `${edge.to}-${edge.from}`;
        const cached = _roadCache[key] || _roadCache[rkey];
        const path = cached
            ? cached.map(p => toXY(p.lat, p.lng))
            : [px[edge.from], px[edge.to]].filter(Boolean) as { x: number; y: number }[];
        if (path.length < 2) return;

        const isHovered = _hoveredEdge === key || _hoveredEdge === rkey;
        ctx.save();
        if (edge.disruption) {
            const col = edge.disruption === 'ACCIDENT' ? '#ef4444'
                : edge.disruption === 'WEATHER' ? '#818cf8' : edge.disruption === 'WHAT_IF' ? '#3b82f6' : '#f59e0b';
            ctx.strokeStyle = col; ctx.lineWidth = 4;
            ctx.setLineDash([7, 4]); ctx.shadowColor = col; ctx.shadowBlur = 12;
        } else if (isPending && isHovered) {
            ctx.strokeStyle = '#ef4444'; ctx.lineWidth = 4; ctx.shadowColor = '#ef4444'; ctx.shadowBlur = 10;
        } else if (isPending) {
            ctx.strokeStyle = 'rgba(239,68,68,0.4)'; ctx.lineWidth = 2;
        } else {
            const t = Math.min(1, Math.max(0, (edge.traffic - 1) / 3));
            const r = Math.round(26 + t * 220), g = Math.round(64 + t * 20), bv = Math.round(128 - t * 110);
            ctx.strokeStyle = `rgba(${r},${g},${bv},0.65)`; ctx.lineWidth = 2;
        }
        ctx.beginPath(); ctx.moveTo(path[0].x, path[0].y);
        path.slice(1).forEach(p => ctx.lineTo(p.x, p.y));
        ctx.stroke(); ctx.restore();

        // Disruption emoji
        if (edge.disruption) {
            const mid = path[Math.floor(path.length / 2)];
            ctx.font = '14px serif'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
            ctx.fillText(
                edge.disruption === 'ACCIDENT' ? '⚠' : edge.disruption === 'WEATHER' ? '☁' : edge.disruption === 'WHAT_IF' ? '◈' : '⟳',
                mid.x, mid.y
            );
        }
    });

    // ── Draw city nodes ───────────────────────────────────────────────────────
    Object.entries(state.graph.nodes).forEach(([id, n]) => {
        const p = px[id]; if (!p) return;
        ctx.save();
        ctx.beginPath(); ctx.arc(p.x, p.y, 5, 0, Math.PI * 2);
        ctx.fillStyle = '#0d1a2e'; ctx.fill();
        ctx.strokeStyle = '#2a4a80'; ctx.lineWidth = 1.5; ctx.stroke();
        ctx.font = '9px "Courier New",monospace';
        ctx.fillStyle = '#3a5a90'; ctx.textAlign = 'center'; ctx.textBaseline = 'bottom';
        ctx.fillText(n.name, p.x, p.y - 8);
        ctx.restore();
    });

    // ── Draw vehicles along real road paths ───────────────────────────────────
    state.vehicles.forEach(v => drawVehicle(ctx, v, state.graph, toXY, dt));
}

// ── Position vehicle along real road path ─────────────────────────────────────
function getPositionOnPath(
    path: { x: number; y: number }[],
    progress: number
): { x: number; y: number } | null {
    if (!path.length) return null;
    if (path.length === 1) return path[0];
    // Compute total path length
    let totalLen = 0;
    const segLens: number[] = [];
    for (let i = 1; i < path.length; i++) {
        const dx = path[i].x - path[i - 1].x, dy = path[i].y - path[i - 1].y;
        const l = Math.hypot(dx, dy);
        segLens.push(l);
        totalLen += l;
    }
    if (!totalLen) return path[0];
    const target = Math.max(0, Math.min(1, progress)) * totalLen;
    let acc = 0;
    for (let i = 0; i < segLens.length; i++) {
        if (acc + segLens[i] >= target) {
            const t = segLens[i] > 0 ? (target - acc) / segLens[i] : 0;
            return {
                x: path[i].x + (path[i + 1].x - path[i].x) * t,
                y: path[i].y + (path[i + 1].y - path[i].y) * t,
            };
        }
        acc += segLens[i];
    }
    return path[path.length - 1];
}

// Client-side lerp with seg_index tracking to reset on segment change
const _prevSegIndex: Record<string, number> = {};

function drawVehicle(
    ctx: CanvasRenderingContext2D,
    v: VehicleData,
    graph: GraphSnapshot,
    toXY: (lat: number, lng: number) => { x: number; y: number },
    dt: number,
) {
    if (!v.route || v.route.length < 2) return;
    const segIdx = Math.min(v.seg_index, v.route.length - 2);
    const fromId = v.route[segIdx], toId = v.route[segIdx + 1];
    const fn = graph.nodes[fromId], tn = graph.nodes[toId];
    if (!fn || !tn) return;

    // Get real road path for this segment (or straight line fallback)
    const key = `${fromId}-${toId}`, rkey = `${toId}-${fromId}`;
    const rawPath = _roadCache[key] || _roadCache[rkey];
    const path: { x: number; y: number }[] = rawPath
        ? rawPath.map(p => toXY(p.lat, p.lng))
        : [toXY(fn.lat, fn.lng), toXY(tn.lat, tn.lng)];

    const t = Math.max(0, Math.min(1, v.seg_progress));
    const target = getPositionOnPath(path, t);
    if (!target) return;

    // Heading: look slightly ahead on the path for smooth angle
    const t2 = Math.min(1, t + 0.03);
    const next = getPositionOnPath(path, t2);
    const ang = next && (Math.abs(next.x - target.x) > 0.5 || Math.abs(next.y - target.y) > 0.5)
        ? Math.atan2(next.y - target.y, next.x - target.x)
        : 0;

    // Reset smooth position when vehicle moves to a new segment (prevents glitching across map)
    if (!_smooth[v.id] || _prevSegIndex[v.id] !== segIdx) {
        _smooth[v.id] = { x: target.x, y: target.y };
        _prevSegIndex[v.id] = segIdx;
    }
    const sp = _smooth[v.id];
    const lerpK = Math.min(1, dt * 8);
    sp.x += (target.x - sp.x) * lerpK;
    sp.y += (target.y - sp.y) * lerpK;
    const { x, y } = sp;

    // Route trail (upcoming path segments)
    ctx.save();
    ctx.strokeStyle = v.color + '35'; ctx.lineWidth = 1.5; ctx.setLineDash([3, 6]);
    ctx.beginPath();
    let first = true;
    for (let i = segIdx; i < v.route.length - 1; i++) {
        const k = `${v.route[i]}-${v.route[i + 1]}`, rk = `${v.route[i + 1]}-${v.route[i]}`;
        const segRaw = _roadCache[k] || _roadCache[rk] || [];
        const segPath = segRaw.length
            ? segRaw.map(p => toXY(p.lat, p.lng))
            : (() => { const a = graph.nodes[v.route[i]], b = graph.nodes[v.route[i + 1]]; return a && b ? [toXY(a.lat, a.lng), toXY(b.lat, b.lng)] : []; })();
        segPath.forEach(p => { if (first) { ctx.moveTo(p.x, p.y); first = false; } else ctx.lineTo(p.x, p.y); });
    }
    ctx.stroke(); ctx.restore();

    // Arrow
    ctx.save();
    ctx.translate(x, y);
    if (v.status === 'REROUTING') { ctx.shadowColor = v.color; ctx.shadowBlur = 16; }
    ctx.rotate(ang);
    ctx.fillStyle = v.color;
    ctx.strokeStyle = v.status === 'REROUTING' ? '#ffffff' : v.color;
    ctx.lineWidth = v.status === 'REROUTING' ? 1.5 : 0;
    ctx.beginPath(); ctx.moveTo(12, 0); ctx.lineTo(-7, -5); ctx.lineTo(-7, 5); ctx.closePath();
    ctx.fill(); if (v.status === 'REROUTING') ctx.stroke();
    ctx.restore();

    // Label + status dot
    ctx.save();
    ctx.font = '8px "Courier New",monospace';
    ctx.fillStyle = v.color; ctx.textAlign = 'center'; ctx.textBaseline = 'top';
    ctx.fillText(v.id, x, y + 14);
    if (v.status !== 'ACTIVE') {
        ctx.beginPath(); ctx.arc(x + 11, y - 11, 3, 0, Math.PI * 2);
        ctx.fillStyle = v.status === 'DELAYED' ? '#f59e0b' : '#ffffff'; ctx.fill();
    }
    ctx.restore();
}
