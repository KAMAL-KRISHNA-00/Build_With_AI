'use client';
// components/MetricsBar.tsx — Top header bar with live stats

import { SimMetrics } from '@/types';

interface MetricsBarProps {
    metrics: SimMetrics | null;
    simTime: string;
    connected: boolean;
}

export default function MetricsBar({ metrics, simTime, connected }: MetricsBarProps) {
    return (
        <div className="metrics-bar">
            {/* Logo */}
            <div className="logo">
                <div className="logo-dot" />
                SUPPLY CHAIN CONTROL TOWER
            </div>

            {/* Divider */}
            <div style={{ width: 1, height: 28, background: '#1e3a5f', flexShrink: 0 }} />

            {/* Stats */}
            <div className="metric">
                <span className="metric-val">{metrics?.active_trucks ?? 0}</span>
                <span className="metric-label">Active Trucks</span>
            </div>

            <div className="metric">
                <span className="metric-val" style={{ color: metrics && metrics.efficiency >= 90 ? '#10b981' : '#f59e0b' }}>
                    {metrics ? `${metrics.efficiency.toFixed(0)}%` : '—'}
                </span>
                <span className="metric-label">On-Time</span>
            </div>

            <div className="metric">
                <span className="metric-val" style={{ color: metrics && metrics.reroutes > 0 ? '#f59e0b' : '#00ffcc' }}>
                    {metrics?.reroutes ?? 0}
                </span>
                <span className="metric-label">Reroutes</span>
            </div>

            <div className="metric">
                <span className="metric-val" style={{ color: metrics && metrics.delayed > 0 ? '#ef4444' : '#10b981' }}>
                    {metrics?.delayed ?? 0}
                </span>
                <span className="metric-label">Delayed</span>
            </div>

            <div className="metric">
                <span className="metric-val">{metrics?.delivered ?? 0}</span>
                <span className="metric-label">Delivered</span>
            </div>

            {/* Sim time + connection */}
            <div className="sim-time" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <div className={`conn-badge ${connected ? 'connected' : ''}`} title={connected ? 'Live' : 'Connecting...'} />
                SIM: {simTime || '00:00:00'}
            </div>
        </div>
    );
}
