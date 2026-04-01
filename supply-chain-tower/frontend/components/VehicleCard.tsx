'use client';
// components/VehicleCard.tsx — Per-vehicle status card

import { VehicleData } from '@/types';
import { nodeLabel } from '@/lib/mapHelpers';

interface VehicleCardProps {
    vehicle: VehicleData;
}

export default function VehicleCard({ vehicle }: VehicleCardProps) {
    // Progress = current segment index / total segments
    const totalSegments = Math.max(1, vehicle.route.length - 1);
    const progress = Math.min(100,
        ((vehicle.seg_index + vehicle.seg_progress) / totalSegments) * 100
    );

    const statusClass = vehicle.status === 'REROUTING'
        ? 'rerouting'
        : vehicle.status === 'DELAYED' ? 'delayed' : '';

    return (
        <div className={`vehicle-card ${statusClass}`}>
            <div className="vehicle-card-header">
                <span className="vehicle-id" style={{ color: vehicle.color }}>
                    {vehicle.id}
                </span>
                <span className={`status-badge ${statusClass}`}>
                    {vehicle.status}
                </span>
            </div>

            <div className="vehicle-dest" style={{ color: '#64748b' }}>
                → {nodeLabel(vehicle.destination)}
                &nbsp;
                <span style={{ color: vehicle.eta_ok ? '#10b981' : '#f59e0b', fontSize: '0.6rem' }}>
                    {vehicle.eta_ok ? 'ETA ok' : 'DELAYED'}
                </span>
            </div>

            {/* Progress bar */}
            <div className="vehicle-progress-bar">
                <div
                    className="vehicle-progress-fill"
                    style={{
                        width: `${progress}%`,
                        background: statusClass === 'rerouting'
                            ? 'linear-gradient(90deg, #f59e0b, #ef4444)'
                            : `linear-gradient(90deg, ${vehicle.color}80, ${vehicle.color})`,
                    }}
                />
            </div>

            <div className="vehicle-meta">
                <span>Risk: <span style={{ color: vehicle.risk_score >= 70 ? '#ef4444' : vehicle.risk_score >= 40 ? '#f59e0b' : '#10b981' }}>
                    {vehicle.risk_score.toFixed(0)}
                </span></span>
                <span>Reroutes: {vehicle.reroutes}</span>
                <span>Del: {vehicle.delivered}</span>
            </div>
        </div>
    );
}
