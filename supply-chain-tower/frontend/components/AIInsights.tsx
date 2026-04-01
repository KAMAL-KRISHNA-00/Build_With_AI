'use client';
// components/AIInsights.tsx — Gemini AI explanation panel

import { AIInsight } from '@/types';

interface AIInsightsProps {
    insights: AIInsight[];
}

export default function AIInsights({ insights }: AIInsightsProps) {
    const latest = insights[0];

    return (
        <div className="ai-panel">
            <div className="ai-panel-header">
                <div className="ai-dot" />
                <span className="ai-panel-title">AI Decision Engine</span>
                {latest && (
                    <span style={{ marginLeft: 'auto', fontSize: '0.58rem', color: '#475569', fontFamily: 'monospace' }}>
                        {latest.algo}
                    </span>
                )}
            </div>
            {latest ? (
                <p className="ai-text">
                    {latest.text}
                </p>
            ) : (
                <p className="ai-text" style={{ color: '#475569', fontStyle: 'italic' }}>
                    Monitoring network. Awaiting events...
                </p>
            )}
        </div>
    );
}
