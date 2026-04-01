'use client';
// components/Sidebar.tsx — Right sidebar with risk gauge, metrics, vehicle list, AI panel, and alert feed

import { SimState } from '@/types';
import RiskGauge from './RiskGauge';
import VehicleCard from './VehicleCard';
import AlertFeed from './AlertFeed';
import AIInsights from './AIInsights';

interface SidebarProps {
    simState: SimState | null;
}

export default function Sidebar({ simState }: SidebarProps) {
    const metrics = simState?.metrics;
    const vehicles = simState?.vehicles ?? [];
    const alerts = simState?.alerts ?? [];
    const insights = simState?.ai_insights ?? [];

    return (
        <div className="sidebar">

            {/* ── Risk Gauge ─────────────────────────────────────────────── */}
            <div className="sidebar-section" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', paddingBottom: '0.5rem' }}>
                <RiskGauge score={metrics?.network_risk ?? 0} />
            </div>

            {/* ── Live Metrics Grid ──────────────────────────────────────── */}
            <div className="sidebar-section">
                <div className="sidebar-section-title">Live Metrics</div>
                <div className="metrics-grid">
                    <div className="metric-card">
                        <div className="metric-card-val">{metrics?.delivered ?? 0}</div>
                        <div className="metric-card-label">Delivered</div>
                    </div>
                    <div className="metric-card">
                        <div className="metric-card-val" style={{ color: metrics && metrics.delayed > 0 ? '#ef4444' : '#00ffcc' }}>
                            {metrics?.delayed ?? 0}
                        </div>
                        <div className="metric-card-label">Delayed</div>
                    </div>
                    <div className="metric-card">
                        <div className="metric-card-val" style={{ color: metrics && metrics.avg_delay > 0 ? '#f59e0b' : '#00ffcc' }}>
                            +{metrics?.avg_delay ?? 0}m
                        </div>
                        <div className="metric-card-label">Avg Delay</div>
                    </div>
                    <div className="metric-card">
                        <div className="metric-card-val" style={{ color: metrics && metrics.efficiency >= 90 ? '#10b981' : '#f59e0b' }}>
                            {metrics ? `${metrics.efficiency.toFixed(0)}%` : '—'}
                        </div>
                        <div className="metric-card-label">Efficiency</div>
                    </div>
                </div>
            </div>

            {/* ── AI Insights ───────────────────────────────────────────── */}
            <AIInsights insights={insights} />

            {/* ── Truck Agents (scrollable) ──────────────────────────────── */}
            <div className="sidebar-section" style={{ paddingBottom: '0.25rem' }}>
                <div className="sidebar-section-title">Truck Agents</div>
            </div>
            <div className="vehicle-list">
                {vehicles.map(v => (
                    <VehicleCard key={v.id} vehicle={v} />
                ))}
                {vehicles.length === 0 && (
                    <div style={{ color: '#475569', fontSize: '0.7rem', textAlign: 'center', paddingTop: '1rem' }}>
                        Connecting to simulation...
                    </div>
                )}
            </div>

            {/* ── Alert Feed ────────────────────────────────────────────── */}
            <AlertFeed alerts={alerts} />

        </div>
    );
}
