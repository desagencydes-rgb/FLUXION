'use client';
import { useState, useEffect, useRef, useCallback } from 'react';
import { api } from '@/lib/api';
import type { SimulationState, Zone, Camion } from '@/types/fluxion';

const DEFAULT_STATE: SimulationState = {
    status: 'paused',
    zones: [],
    camions: [],
    recent_events: [],
    routes: [],
    depot: undefined,
    refuel_points: [],
};

const WS_URL = process.env.NEXT_PUBLIC_WS_URL ?? 'ws://localhost:8000/ws/events';

export function useSimulation(pollMs = 5000) {
    const [state, setState] = useState<SimulationState>(DEFAULT_STATE);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const wsRef = useRef<WebSocket | null>(null);
    const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
    const reconnectRef = useRef<ReturnType<typeof setTimeout> | null>(null);

    // ── HTTP fallback ─────────────────────────────────────────────────────────
    const fetchState = useCallback(async () => {
        try {
            const data = await api.getState();
            setState(data);
            setError(null);
        } catch (e) {
            setError(e instanceof Error ? e.message : 'Unknown error');
        } finally {
            setLoading(false);
        }
    }, []);

    const startPolling = useCallback(() => {
        if (pollRef.current) return;
        fetchState();
        pollRef.current = setInterval(fetchState, pollMs);
    }, [fetchState, pollMs]);

    const stopPolling = useCallback(() => {
        if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
    }, []);

    // ── WebSocket ─────────────────────────────────────────────────────────────
    const connectWS = useCallback(() => {
        if (wsRef.current?.readyState === WebSocket.OPEN) return;

        try {
            const ws = new WebSocket(WS_URL);
            wsRef.current = ws;

            ws.onopen = () => {
                setError(null);
                stopPolling();
                // Server sends INIT message with full state on connect
            };

            ws.onmessage = (evt) => {
                try {
                    const msg = JSON.parse(evt.data as string);

                    if (msg.type === 'INIT') {
                        // Full state from server on first connect
                        const { type: _t, ...stateData } = msg;
                        setState(stateData as SimulationState);
                        setLoading(false);
                        return;
                    }

                    if (msg.type === 'SIMULATION_UPDATE') {
                        setState(prev => {
                            // Merge changed zones (delta)
                            let updatedZones = prev.zones;
                            if (msg.zones?.length) {
                                const changeMap = new Map(msg.zones.map((z: Partial<Zone>) => [z.id, z]));
                                updatedZones = prev.zones.map(z => {
                                    const change = changeMap.get(z.id);
                                    return change ? { ...z, ...change } : z;
                                });
                            }

                            // Update truck positions
                            let updatedCamions = prev.camions;
                            if (msg.truck_positions?.length) {
                                const posMap = new Map(msg.truck_positions.map((t: { id: number; lat: number; lon: number; on_duty: boolean }) => [t.id, t]));
                                updatedCamions = prev.camions.map(c => {
                                    const pos = posMap.get(c.id) as { lat: number; lon: number; on_duty: boolean } | undefined;
                                    return pos ? { ...c, lat: pos.lat, lon: pos.lon, on_duty: pos.on_duty } : c;
                                });
                            }

                            return {
                                ...prev,
                                zones: updatedZones,
                                camions: updatedCamions,
                                routes: msg.routes || prev.routes,
                                recent_events: msg.events?.length
                                    ? [...prev.recent_events.slice(-40), ...msg.events]
                                    : prev.recent_events,
                            };
                        });
                        setLoading(false);
                    }
                } catch {
                    // Non-JSON — ignore
                }
            };

            ws.onerror = () => setError('WebSocket error — switching to polling');

            ws.onclose = () => {
                wsRef.current = null;
                startPolling();
                reconnectRef.current = setTimeout(() => {
                    stopPolling();
                    connectWS();
                }, 4000);
            };
        } catch {
            startPolling();
        }
    }, [fetchState, startPolling, stopPolling]);

    useEffect(() => {
        connectWS();
        return () => {
            if (reconnectRef.current) clearTimeout(reconnectRef.current);
            stopPolling();
            if (wsRef.current) { wsRef.current.onclose = null; wsRef.current.close(); }
        };
    }, [connectWS, stopPolling]);

    // ── Actions ───────────────────────────────────────────────────────────────
    const play = async () => { await api.play(); setState(s => ({ ...s, status: 'running' })); };
    const pause = async () => { await api.pause(); setState(s => ({ ...s, status: 'paused' })); };
    const step = async () => { await api.step(); await fetchState(); };

    return { state, loading, error, play, pause, step, refresh: fetchState };
}
