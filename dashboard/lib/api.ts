// FLUXION API Client v2
// Relative URLs work through Nginx proxy when deployed.
// Explicit localhost fallback for local dev.

import type { NSGAWeights, SimulationState, SavingsMetrics } from '@/types/fluxion';

const SIM_API = process.env.NEXT_PUBLIC_SIM_API_URL ?? 'http://localhost:8000';
const BRIDGE_API = process.env.NEXT_PUBLIC_BRIDGE_API_URL ?? 'http://localhost:8001';

// ── Auth helpers ──────────────────────────────────────────────────────────────

function getToken(): string | null {
    if (typeof window === 'undefined') return null;
    return localStorage.getItem('fluxion_token');
}

function clearToken() {
    if (typeof window !== 'undefined') localStorage.removeItem('fluxion_token');
}

export function saveToken(token: string) {
    if (typeof window !== 'undefined') localStorage.setItem('fluxion_token', token);
}

function jsonHeaders(): HeadersInit {
    const token = getToken();
    return token
        ? { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` }
        : { 'Content-Type': 'application/json' };
}

// ── Core HTTP helpers ─────────────────────────────────────────────────────────

async function xfetch(url: string, opts: RequestInit = {}): Promise<Response> {
    const res = await fetch(url, { cache: 'no-store', ...opts });
    if (res.status === 401) {
        clearToken();
        if (typeof window !== 'undefined') window.location.href = '/login';
        throw new Error('Unauthorized — redirecting to login');
    }
    if (!res.ok) {
        let detail = `HTTP ${res.status}`;
        try { detail = (await res.json()).detail ?? detail; } catch { /* ignore */ }
        throw new Error(detail);
    }
    return res;
}

async function get<T>(base: string, path: string): Promise<T> {
    const res = await xfetch(`${base}${path}`, { headers: jsonHeaders() });
    return res.json();
}

async function post<T>(base: string, path: string, body?: unknown): Promise<T> {
    const res = await xfetch(`${base}${path}`, {
        method: 'POST',
        headers: jsonHeaders(),
        body: body != null ? JSON.stringify(body) : undefined,
    });
    return res.json();
}

// ── Simulation API ────────────────────────────────────────────────────────────

export const api = {
    // Core state
    getState: () => get<SimulationState>(SIM_API, '/api/state'),
    getSavings: () => get<SavingsMetrics>(SIM_API, '/api/savings').catch(() => ({
        money_saved: 0, fuel_saved_l: 0, co2_reduced_kg: 0, distance_saved_km: 0,
        fuel_consumed_l: 0, money_consumed: 0, time_elapsed_min: 0,
    } as SavingsMetrics)),

    // Playback
    play: () => post<{ status: string }>(SIM_API, '/api/simulation/play'),
    pause: () => post<{ status: string }>(SIM_API, '/api/simulation/pause'),
    step: () => post<unknown>(SIM_API, '/api/simulation/step'),
    reset: () => post<unknown>(SIM_API, '/api/simulation/reset'),

    // Config & weights
    setWeights: (w: Partial<NSGAWeights>) => post<unknown>(SIM_API, '/api/simulation/weights', w),
    getConfig: () => get<unknown>(SIM_API, '/api/config'),
    setConfig: (payload: unknown) => post<unknown>(SIM_API, '/api/config', payload),

    // Driver — duty management (persists across refresh)
    getDutyStatus: (camionId: number) =>
        get<{ camion_id: number; on_duty: boolean; since?: string }>(
            SIM_API, `/api/driver/duty?camion_id=${camionId}`
        ),
    setDuty: (camionId: number, onDuty: boolean) =>
        post<{ camion_id: number; on_duty: boolean }>(SIM_API, '/api/driver/duty', {
            camion_id: camionId,
            on_duty: onDuty,
        }),

    // Driver — zone collection (with capacity enforcement)
    collectZone: (camionId: number, zoneId: number) =>
        post<{
            success: boolean;
            volume_collected: number;
            truck_load: number;
            truck_capacity: number;
        }>(SIM_API, '/api/driver/collect', { camion_id: camionId, zone_id: zoneId }),

    unloadTruck: (camionId: number) =>
        post<{ success: boolean; unloaded_l: number }>(
            SIM_API, `/api/driver/unload?camion_id=${camionId}`
        ),

    // Events / incidents
    triggerIncident: (type: string, details: Record<string, unknown>) =>
        post<unknown>(SIM_API, '/api/events/trigger', { type, details }),

    // CSV / Excel import
    importPoints: (file: File) => {
        const form = new FormData();
        form.append('file', file);
        return xfetch(`${SIM_API}/api/import/points`, {
            method: 'POST',
            body: form,
            headers: getToken() ? { Authorization: `Bearer ${getToken()}` } : {},
        }).then(r => r.json()) as Promise<{
            success: boolean;
            imported_points: number;
            errors: string[];
        }>;
    },

    importTrucks: (file: File) => {
        const form = new FormData();
        form.append('file', file);
        return xfetch(`${SIM_API}/api/import/trucks`, {
            method: 'POST',
            body: form,
            headers: getToken() ? { Authorization: `Bearer ${getToken()}` } : {},
        }).then(r => r.json()) as Promise<{
            success: boolean;
            imported_trucks: number;
            errors: string[];
        }>;
    },

    // Auth
    login: (email: string, password: string) =>
        post<{ access_token: string; token_type: string; role: string }>(
            SIM_API, '/auth/login', { email, password }
        ),
};

// ── Live Bridge API ───────────────────────────────────────────────────────────

export const bridgeApi = {
    health: () => get<{ status: string; live_graph_vertices: number }>(BRIDGE_API, '/live/health'),
    snapGPS: (coords: { lat: number; lon: number }[]) =>
        post<unknown>(BRIDGE_API, '/live/gps-snap', { coordinates: coords }),
    ingestNetwork: (lat: number, lon: number, radius = 1500) =>
        post<{ num_vertices: number; num_edges: number }>(
            BRIDGE_API,
            `/live/ingest-network?lat=${lat}&lon=${lon}&radius=${radius}`,
        ),
};
