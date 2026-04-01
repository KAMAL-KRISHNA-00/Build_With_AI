'use client';
/**
 * components/DisruptionPanel.tsx
 * Disruption buttons enter "pending" mode — user then clicks a road on the map.
 * Pause button shows clear visual state with immediate optimistic toggle.
 */
import { useCallback } from 'react';

interface DisruptionPanelProps {
    paused: boolean;
    connected: boolean;
    pendingDisruption: string | null;
    onSelectType: (type: string) => void;
    onTogglePause: () => void;
    lastFeedback: { msg: string; ok: boolean } | null;
}

const BTNS = [
    {
        type: 'ACCIDENT',
        label: 'ACCIDENT',
        icon: '⚠',
        cls: 'accident',
        tooltip: 'Blocks a road completely. Affected trucks reroute via A*.',
    },
    {
        type: 'WEATHER',
        label: 'WEATHER',
        icon: '☁',
        cls: 'weather',
        tooltip: 'Slows traffic over multiple nearby roads. Risk score rises.',
    },
    {
        type: 'TRAFFIC_JAM',
        label: 'TRAFFIC JAM',
        icon: '⟳',
        cls: 'traffic',
        tooltip: 'Congestion spike on one road — trucks slow down + might reroute.',
    },
    {
        type: 'WHAT_IF',
        label: 'WHAT-IF',
        icon: '◈',
        cls: 'whatif',
        tooltip: 'STRESS TEST: Injects a severe blockage (×5 weight). Genetic Algorithm\nevaluates all alternate routes. Use to test network resilience.',
    },
];

export default function DisruptionPanel({
    paused, connected, pendingDisruption, onSelectType, onTogglePause, lastFeedback,
}: DisruptionPanelProps) {
    return (
        <div className="disruption-overlay">
            {/* Backend offline warning */}
            {!connected && (
                <div style={{
                    padding: '0.35rem 0.75rem', background: 'rgba(239,68,68,0.12)',
                    border: '1px solid rgba(239,68,68,0.4)', borderRadius: 6,
                    color: '#ef4444', fontSize: '0.65rem', fontFamily: 'monospace',
                }}>
                    ⚡ Backend offline — start uvicorn
                </div>
            )}

            {/* Pause button — clearly shows current state */}
            <button
                className={`disruption-btn pause ${paused ? 'paused' : ''}`}
                onClick={onTogglePause}
                style={{
                    background: paused ? 'rgba(0,255,204,0.12)' : 'rgba(30,58,96,0.5)',
                    borderColor: paused ? '#00ffcc' : '#1e3a60',
                    color: paused ? '#00ffcc' : '#7ab0e0',
                    fontWeight: 700,
                }}
            >
                <span style={{ fontSize: '1rem' }}>{paused ? '▶' : '■'}</span>
                <span>{paused ? 'RESUME SIM' : 'PAUSE SIM'}</span>
                {paused && (
                    <span style={{ marginLeft: 'auto', fontSize: '0.6rem', animation: 'pulse 1s infinite', color: '#00ffcc' }}>
                        FROZEN
                    </span>
                )}
            </button>

            {/* Divider */}
            <div style={{ height: 1, background: '#1a2840', margin: '2px 0' }} />
            <div style={{ fontSize: '0.58rem', color: '#3a5070', fontFamily: 'monospace', letterSpacing: '0.08em', padding: '2px 4px' }}>
                CLICK TYPE → CLICK ROAD ON MAP
            </div>

            {/* Disruption buttons */}
            {BTNS.map(btn => {
                const isActive = pendingDisruption === btn.type;
                return (
                    <button
                        key={btn.type}
                        className={`disruption-btn ${btn.cls} ${isActive ? 'active-select' : ''}`}
                        onClick={() => onSelectType(isActive ? '' : btn.type)}
                        title={btn.tooltip}
                        style={{
                            borderColor: isActive ? '#ef4444' : undefined,
                            background: isActive ? 'rgba(239,68,68,0.18)' : undefined,
                            transform: isActive ? 'scale(1.02)' : 'scale(1)',
                            transition: 'all 0.15s ease',
                        }}
                    >
                        <span style={{ fontSize: '1rem' }}>{btn.icon}</span>
                        <span style={{ textAlign: 'left', flex: 1 }}>
                            {btn.label}
                            {btn.type === 'WHAT_IF' && (
                                <span style={{ display: 'block', fontSize: '0.55rem', color: '#6b7a9a', marginTop: 1 }}>
                                    Stress test: max disruption
                                </span>
                            )}
                        </span>
                        {isActive && (
                            <span style={{ fontSize: '0.58rem', color: '#ef4444', animation: 'pulse 0.8s infinite', whiteSpace: 'nowrap' }}>
                                ← SELECT ROAD
                            </span>
                        )}
                    </button>
                );
            })}

            {/* Feedback toast */}
            {lastFeedback && (
                <div style={{
                    padding: '0.4rem 0.75rem',
                    background: lastFeedback.ok ? 'rgba(0,255,204,0.08)' : 'rgba(239,68,68,0.08)',
                    border: `1px solid ${lastFeedback.ok ? 'rgba(0,255,204,0.3)' : 'rgba(239,68,68,0.4)'}`,
                    borderRadius: 6, fontSize: '0.68rem', fontFamily: 'monospace',
                    color: lastFeedback.ok ? '#00ffcc' : '#ef4444',
                    animation: 'slide-in 0.3s ease',
                }}>
                    {lastFeedback.msg}
                </div>
            )}
        </div>
    );
}
