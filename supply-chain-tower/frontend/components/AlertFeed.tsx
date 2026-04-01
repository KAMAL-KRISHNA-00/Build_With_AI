'use client';
// components/AlertFeed.tsx — Scrolling event log

import { Alert } from '@/types';
import { alertColor } from '@/lib/mapHelpers';
import { useEffect, useRef } from 'react';

interface AlertFeedProps {
    alerts: Alert[];
}

export default function AlertFeed({ alerts }: AlertFeedProps) {
    const feedRef = useRef<HTMLDivElement>(null);

    // Auto-scroll to top when new alerts arrive
    useEffect(() => {
        if (feedRef.current) feedRef.current.scrollTop = 0;
    }, [alerts.length]);

    return (
        <div className="alert-feed" ref={feedRef}>
            {alerts.length === 0 && (
                <div style={{ color: '#475569', fontSize: '0.65rem', fontFamily: 'monospace', textAlign: 'center', paddingTop: '1rem' }}>
                    No events yet...
                </div>
            )}
            {alerts.map((alert, i) => (
                <div key={i} className="alert-entry">
                    <div
                        className="alert-dot"
                        style={{ background: alertColor(alert.type) }}
                    />
                    <span className="alert-ts">[{alert.ts}]</span>
                    <span style={{ color: '#94a3b8', fontSize: '0.63rem' }}>
                        <span style={{ color: alertColor(alert.type), fontWeight: 600 }}>
                            {alert.source}
                        </span>
                        {' '}
                        {alert.msg}
                    </span>
                </div>
            ))}
        </div>
    );
}
