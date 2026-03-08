'use client';
import { useState, useCallback } from 'react';
import type { Zone, Route } from '@/types/fluxion';
import { FILL_COLORS, getFillStatus, POINT_TYPE_ICONS } from '@/types/fluxion';
import { api } from '@/lib/api';

interface CollectionPoint {
    id: number;
    nom: string;
    type: string;
    fill_level: number;
    volume_estime: number;
    ordre: number;
    heure_estimee: string;
    collected: boolean;
}

interface Props {
    zones: Zone[];
    camionId?: number;
    routes?: Route[];
    onCollected?: (zoneId: number) => void;
}

function buildChecklist(zones: Zone[], camionId: number, routes?: Route[]): CollectionPoint[] {
    if (routes !== undefined) {
        const route = routes.find(r => r.camion_id === camionId);
        if (!route) return [];

        const zoneMap = new Map(zones.map(z => [z.id, z]));
        let orderCounter = 1;

        return route.points
            .filter(p => p.type === 'zone')
            .map((p) => {
                const z = zoneMap.get(p.id as number);
                if (!z || z.collected) return null;

                const ordre = orderCounter++;
                return {
                    id: z.id,
                    nom: z.name || `Zone ${z.id}`,
                    type: z.type || 'trash_bin',
                    fill_level: z.fill_level,
                    volume_estime: z.volume_estime,
                    ordre,
                    heure_estimee: `${String(8 + Math.floor(ordre / 2)).padStart(2, '0')}:${ordre % 2 === 0 ? '00' : '30'}`,
                    collected: false,
                };
            })
            .filter(Boolean) as CollectionPoint[];
    }

    // Fallback if no routes object provided at all
    return zones
        .filter(z => !z.collected)
        .sort((a, b) => b.fill_level - a.fill_level)
        .map((z, i) => ({
            id: z.id,
            nom: z.name || `Zone ${z.id}`,
            type: z.type || 'trash_bin',
            fill_level: z.fill_level,
            volume_estime: z.volume_estime,
            ordre: i + 1,
            heure_estimee: `${String(8 + Math.floor(i / 2)).padStart(2, '0')}:${i % 2 === 0 ? '00' : '30'}`,
            collected: false,
        }));
}

export default function TourneeChecklist({ zones, camionId = 1, routes, onCollected }: Props) {
    const [localCollected, setLocalCollected] = useState<Set<number>>(new Set());
    const [loading, setLoading] = useState<Set<number>>(new Set());
    const [errors, setErrors] = useState<Map<number, string>>(new Map());

    const points = buildChecklist(zones, camionId, routes);
    const assignedZoneIds = routes
        ? new Set(routes.find(r => r.camion_id === camionId)?.points.filter(p => p.type === 'zone').map(p => p.id) || [])
        : new Set(zones.map(z => z.id));

    const done = localCollected.size + zones.filter(z => z.collected && z.collected_by === camionId && assignedZoneIds.has(z.id)).length;
    const total = assignedZoneIds.size || zones.length;
    const pct = total > 0 ? Math.round((done / total) * 100) : 0;

    const handleCollect = useCallback(async (pt: CollectionPoint) => {
        if (localCollected.has(pt.id) || loading.has(pt.id)) return;

        setLoading(prev => new Set(prev).add(pt.id));
        setErrors(prev => { const m = new Map(prev); m.delete(pt.id); return m; });

        try {
            await api.collectZone(camionId, pt.id);
            setLocalCollected(prev => new Set(prev).add(pt.id));
            onCollected?.(pt.id);
        } catch (e) {
            const msg = e instanceof Error ? e.message : 'Collection failed';
            setErrors(prev => new Map(prev).set(pt.id, msg));
        } finally {
            setLoading(prev => { const s = new Set(prev); s.delete(pt.id); return s; });
        }
    }, [camionId, localCollected, loading, onCollected]);

    return (
        <div className="space-y-3">
            {/* Progress */}
            <div className="flex items-center justify-between text-sm mb-1">
                <span className="text-gray-300 font-semibold">Truck {camionId} — Route</span>
                <span className="text-gray-400">{done}/{total} collected</span>
            </div>
            <div className="h-2 rounded-full bg-gray-700 overflow-hidden mb-3">
                <div
                    className="h-full rounded-full bg-gradient-to-r from-blue-500 to-emerald-500 transition-all duration-500"
                    style={{ width: `${pct}%` }}
                />
            </div>

            {/* Empty state */}
            {points.length === 0 && (
                <p className="text-center text-gray-500 text-sm py-6">
                    {total > 0 ? '✅ All zones collected!' : 'No zones in your route yet'}
                </p>
            )}

            {/* Checklist */}
            <div className="space-y-2">
                {points.map(pt => {
                    const isDone = localCollected.has(pt.id) || (zones.find(z => z.id === pt.id)?.collected ?? false);
                    const isLoading = loading.has(pt.id);
                    const err = errors.get(pt.id);
                    const status = getFillStatus(pt.fill_level);
                    const color = FILL_COLORS[status];
                    const icon = POINT_TYPE_ICONS[pt.type] ?? '📍';

                    return (
                        <button
                            key={pt.id}
                            onClick={() => handleCollect(pt)}
                            disabled={isDone || isLoading}
                            className={`w-full flex items-center gap-3 p-3 rounded-xl border text-left transition
                ${isDone
                                    ? 'border-emerald-500/40 bg-emerald-500/10 cursor-default'
                                    : err
                                        ? 'border-red-500/40 bg-red-500/10 hover:bg-red-500/20'
                                        : 'border-white/10 bg-gray-800/50 hover:bg-gray-700/50 active:scale-98'
                                }`}
                        >
                            {/* Order badge */}
                            <span
                                className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold text-white shrink-0"
                                style={{ background: isDone ? '#10b981' : err ? '#ef4444' : '#374151' }}
                            >
                                {isLoading ? (
                                    <span className="w-3 h-3 border border-white border-t-transparent rounded-full animate-spin" />
                                ) : isDone ? '✓' : pt.ordre}
                            </span>

                            {/* Type icon + fill bar */}
                            <span className="text-base shrink-0">{icon}</span>
                            <span className="w-2 h-8 rounded-full shrink-0" style={{ background: isDone ? '#10b981' : color }} />

                            {/* Info */}
                            <div className="flex-1 min-w-0">
                                <p className={`text-sm font-medium truncate ${isDone ? 'line-through text-gray-500' : 'text-white'}`}>
                                    {pt.nom}
                                </p>
                                <p className="text-xs text-gray-400">
                                    {pt.heure_estimee} · {pt.fill_level.toFixed(0)}% full · {pt.volume_estime}L
                                </p>
                                {err && <p className="text-xs text-red-400 mt-0.5 truncate">{err}</p>}
                            </div>

                            {/* Urgency / action badge */}
                            {!isDone && !isLoading && (
                                <>
                                    {status !== 'ok' && (
                                        <span className={`text-xs px-2 py-0.5 rounded-full font-semibold shrink-0
                      ${status === 'critical' ? 'bg-violet-500/20 text-violet-400' :
                                                status === 'urgent' ? 'bg-red-500/20 text-red-400' :
                                                    'bg-amber-500/20 text-amber-400'}`}>
                                            {status.toUpperCase()}
                                        </span>
                                    )}
                                    <span className="text-xs text-gray-600 shrink-0">Tap ✓</span>
                                </>
                            )}
                        </button>
                    );
                })}
            </div>
        </div>
    );
}
