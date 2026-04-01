'use client';
// hooks/useWebSocket.ts — WebSocket connection manager
// Handles connection, reconnection, and message dispatching.

import { useEffect, useRef, useCallback, useState } from 'react';
import { SimState } from '@/types';

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws';
const RECONNECT_DELAY_MS = 2000;

interface UseWebSocketReturn {
    state: SimState | null;
    connected: boolean;
    send: (msg: object) => void;
}

export function useWebSocket(): UseWebSocketReturn {
    const wsRef = useRef<WebSocket | null>(null);
    const [state, setState] = useState<SimState | null>(null);
    const [connected, setConnected] = useState(false);
    const reconnectTimer = useRef<NodeJS.Timeout | null>(null);

    const connect = useCallback(() => {
        if (wsRef.current?.readyState === WebSocket.OPEN) return;

        const ws = new WebSocket(WS_URL);
        wsRef.current = ws;

        ws.onopen = () => {
            setConnected(true);
            if (reconnectTimer.current) {
                clearTimeout(reconnectTimer.current);
                reconnectTimer.current = null;
            }
        };

        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data) as SimState;
                if (data.type === 'STATE') {
                    setState(data);
                }
            } catch {
                // malformed message — ignore
            }
        };

        ws.onclose = () => {
            setConnected(false);
            // Auto-reconnect after delay
            reconnectTimer.current = setTimeout(connect, RECONNECT_DELAY_MS);
        };

        ws.onerror = () => {
            ws.close();
        };
    }, []);

    useEffect(() => {
        connect();
        return () => {
            reconnectTimer.current && clearTimeout(reconnectTimer.current);
            wsRef.current?.close();
        };
    }, [connect]);

    const send = useCallback((msg: object) => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify(msg));
        }
    }, []);

    return { state, connected, send };
}
