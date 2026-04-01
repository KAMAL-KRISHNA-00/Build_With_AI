'use client';
// components/RiskGauge.tsx — Circular SVG risk meter

import { riskColor } from '@/lib/mapHelpers';

interface RiskGaugeProps {
    score: number;   // 0–100
}

export default function RiskGauge({ score }: RiskGaugeProps) {
    const radius = 50;
    const stroke = 8;
    const cx = 70;
    const cy = 70;
    const circumference = 2 * Math.PI * radius;
    // 270° arc (3/4 circle): starts from bottom-left, goes clockwise
    const arcLength = circumference * 0.75;
    const dashOffset = arcLength - (arcLength * Math.min(score, 100)) / 100;
    const color = riskColor(score);

    return (
        <div className="risk-gauge-container">
            <div className="risk-gauge-label">Network Risk Score</div>
            <svg width="140" height="140" className="risk-gauge-svg">
                {/* Background arc */}
                <circle
                    cx={cx} cy={cy} r={radius}
                    fill="none"
                    stroke="#1e3a5f"
                    strokeWidth={stroke}
                    strokeDasharray={`${arcLength} ${circumference}`}
                    strokeLinecap="round"
                    transform={`rotate(135 ${cx} ${cy})`}
                />
                {/* Value arc */}
                <circle
                    cx={cx} cy={cy} r={radius}
                    fill="none"
                    stroke={color}
                    strokeWidth={stroke}
                    strokeDasharray={`${arcLength - dashOffset} ${circumference}`}
                    strokeLinecap="round"
                    transform={`rotate(135 ${cx} ${cy})`}
                    style={{
                        filter: `drop-shadow(0 0 6px ${color}80)`,
                        transition: 'stroke-dasharray 0.8s ease, stroke 0.5s ease',
                    }}
                />
                {/* Score text */}
                <text
                    x={cx} y={cy - 6}
                    textAnchor="middle"
                    className="risk-score-text"
                    style={{ fill: color, fontFamily: 'Share Tech Mono, monospace', fontSize: '2rem', fontWeight: 700 }}
                >
                    {Math.round(score)}
                </text>
                <text
                    x={cx} y={cy + 16}
                    textAnchor="middle"
                    className="risk-sub-text"
                    style={{ fill: '#475569', fontFamily: 'Share Tech Mono, monospace', fontSize: '0.6rem', letterSpacing: '0.12em' }}
                >
                    RISK
                </text>
            </svg>
        </div>
    );
}
