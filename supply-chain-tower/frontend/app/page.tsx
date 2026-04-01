'use client';
import { useCallback, useState, useEffect } from 'react';
import dynamic from 'next/dynamic';
import { useWebSocket } from '@/hooks/useWebSocket';
import MetricsBar from '@/components/MetricsBar';
import Sidebar from '@/components/Sidebar';
import DisruptionPanel from '@/components/DisruptionPanel';

const MapView = dynamic(() => import('@/components/MapView'), {
    ssr: false,
    loading: () => (
        <div style={{
            width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center',
            background: '#070d1a', color: '#3b82f6', fontFamily: 'Share Tech Mono, monospace', fontSize: '0.8rem',
        }}>
            LOADING MAP…
        </div>
    ),
});

const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

async function fetchWithTimeout(url: string, opts: RequestInit, ms = 6000) {
    const ctrl = new AbortController();
    const t = setTimeout(() => ctrl.abort(), ms);
    try { const r = await fetch(url, { ...opts, signal: ctrl.signal }); clearTimeout(t); return r; }
    catch (e) { clearTimeout(t); throw e; }
}

export default function Home() {
    const { state, connected, send } = useWebSocket();
    const [pendingDisruption, setPendingDisruption] = useState<string | null>(null);
    const [feedback, setFeedback] = useState<{ msg: string; ok: boolean } | null>(null);

    // Auto-clear feedback after 3s
    useEffect(() => {
        if (!feedback) return;
        const t = setTimeout(() => setFeedback(null), 3000);
        return () => clearTimeout(t);
    }, [feedback]);

    // Called when user clicks PAUSE button
    const handleTogglePause = useCallback(async () => {
        try {
            await fetchWithTimeout(`${BACKEND}/toggle_pause`, { method: 'POST' });
        } catch {
            send({ action: 'pause' });
        }
    }, [send]);

    // Called when user clicks a disruption type button — enter selection mode
    const handleSelectType = useCallback((type: string) => {
        setPendingDisruption(type || null);
    }, []);

    // Called when user clicks an edge on the map in selection mode
    const handleEdgeSelected = useCallback(async (edgeKey: string, from: string, to: string) => {
        if (!pendingDisruption) return;
        const type = pendingDisruption;
        setPendingDisruption(null);
        try {
            const res = await fetchWithTimeout(`${BACKEND}/inject_event`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ type, edge: [from, to] }),
            });
            if (res.ok) {
                setFeedback({ msg: `✓ ${type} on ${from}↔${to}`, ok: true });
            } else {
                setFeedback({ msg: `✗ Server error ${res.status}`, ok: false });
            }
        } catch {
            setFeedback({ msg: '✗ Backend offline', ok: false });
        }
    }, [pendingDisruption]);

    const handleCancelSelect = useCallback(() => {
        setPendingDisruption(null);
    }, []);

    return (
        <div className="dashboard-root">
            <MetricsBar
                metrics={state?.metrics ?? null}
                simTime={state?.sim_time ?? '00:00:00'}
                connected={connected}
            />
            <div className="main-area">
                <div className="map-container">
                    <MapView
                        simState={state}
                        pendingDisruption={pendingDisruption}
                        onEdgeSelected={handleEdgeSelected}
                        onCancelSelect={handleCancelSelect}
                    />
                    <DisruptionPanel
                        paused={state?.paused ?? false}
                        connected={connected}
                        pendingDisruption={pendingDisruption}
                        onSelectType={handleSelectType}
                        onTogglePause={handleTogglePause}
                        lastFeedback={feedback}
                    />
                    {/* Active disruption badges */}
                    {state && state.disruptions.length > 0 && (
                        <div style={{
                            position: 'absolute', bottom: '1rem', left: '50%', transform: 'translateX(-50%)',
                            zIndex: 100, display: 'flex', gap: '0.5rem', flexWrap: 'wrap', justifyContent: 'center',
                        }}>
                            {state.disruptions.map(d => (
                                <div key={d.id} className="disruption-active-badge">
                                    <span>{d.type}</span>
                                    <span style={{ color: '#ef444480' }}>{Math.round(d.remaining)}s</span>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
                <Sidebar simState={state} />
            </div>
        </div>
    );
}
