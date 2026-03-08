'use client';
import { useEffect, useRef, useState, useCallback } from 'react';
import type { SimulationState, Zone } from '@/types/fluxion';
import { FILL_COLORS, getFillStatus, POINT_TYPE_ICONS } from '@/types/fluxion';

interface FluxionMapProps {
    state: SimulationState;
    currentCity?: string;
}

type L = typeof import('leaflet');
type LeafletMap = import('leaflet').Map;
type CircleMarker = import('leaflet').CircleMarker;
type Marker = import('leaflet').Marker;
type Polyline = import('leaflet').Polyline;
type TileLayer = import('leaflet').TileLayer;

const TRUCK_COLORS = ['#3b82f6', '#8b5cf6', '#ec4899', '#f59e0b', '#10b981', '#ef4444'];
const OSM_TILE = 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';
const SAT_TILE = 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}';

export default function FluxionMap({ state, currentCity }: FluxionMapProps) {
    const containerRef = useRef<HTMLDivElement>(null);
    const mapRef = useRef<LeafletMap | null>(null);
    const tileRef = useRef<TileLayer | null>(null);
    const zoneMarkersRef = useRef<CircleMarker[]>([]);
    const truckMarkersRef = useRef<Map<number, Marker>>(new Map());
    const specialMarkersRef = useRef<Marker[]>([]);
    const routeLinesRef = useRef<Polyline[]>([]);
    const leafletRef = useRef<L | null>(null);
    const hasInitFitRef = useRef(false);
    const prevCityRef = useRef<string | undefined>(undefined);

    const [satellite, setSatellite] = useState(false);
    const [showRoutes, setShowRoutes] = useState(true);
    const [showCollected, setShowCollected] = useState(false);

    // ── Init map ──────────────────────────────────────────────────────────────
    useEffect(() => {
        if (mapRef.current || !containerRef.current) return;

        const init = async () => {
            const L = (await import('leaflet')).default;
            leafletRef.current = L;

            // Fix broken default icons (webpack issue)
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            delete (L.Icon.Default.prototype as any)._getIconUrl;
            L.Icon.Default.mergeOptions({
                iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
                iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
                shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
            });

            const map = L.map(containerRef.current!, { center: [33.57, -7.59], zoom: 13, zoomControl: true });
            tileRef.current = L.tileLayer(OSM_TILE, { attribution: '© OSM', maxZoom: 19 }).addTo(map);
            mapRef.current = map;
        };

        init();
        return () => {
            mapRef.current?.remove();
            mapRef.current = null;
            truckMarkersRef.current.clear();
            hasInitFitRef.current = false;
        };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    // ── Tile toggle ───────────────────────────────────────────────────────────
    useEffect(() => {
        if (!mapRef.current || !tileRef.current || !leafletRef.current) return;
        const L = leafletRef.current;
        tileRef.current.remove();
        tileRef.current = L.tileLayer(satellite ? SAT_TILE : OSM_TILE, {
            attribution: satellite ? 'Imagery © Esri' : '© OSM',
            maxZoom: satellite ? 17 : 19,
        }).addTo(mapRef.current!);
    }, [satellite]);

    // ── Make custom div icon ──────────────────────────────────────────────────
    const makeDivIcon = useCallback((emoji: string, bg: string, size = 32) => {
        if (!leafletRef.current) return undefined;
        return leafletRef.current.divIcon({
            html: `<div style="
        background:${bg};border:2px solid rgba(255,255,255,0.8);
        border-radius:50%;width:${size}px;height:${size}px;
        display:flex;align-items:center;justify-content:center;
        font-size:${size * 0.5}px;box-shadow:0 2px 8px rgba(0,0,0,0.5);">
        ${emoji}
      </div>`,
            className: '',
            iconSize: [size, size],
            iconAnchor: [size / 2, size / 2],
        });
    }, []);

    // ── Draw depot + refuel markers ───────────────────────────────────────────
    useEffect(() => {
        if (!mapRef.current || !leafletRef.current) return;
        const L = leafletRef.current;

        specialMarkersRef.current.forEach(m => m.remove());
        specialMarkersRef.current = [];

        // Depot
        const depot = state.depot ?? { lat: 33.5731, lon: -7.5898, name: 'Main Depot', id: 0, type: 'depot' };
        const depotIcon = makeDivIcon('📦', '#f97316', 40);
        if (depotIcon) {
            const dm = L.marker([depot.lat, depot.lon], { icon: depotIcon, zIndexOffset: 1000 })
                .bindPopup(`<b>📦 ${depot.name}</b><br>Departure & Unloading Point`)
                .addTo(mapRef.current!);
            specialMarkersRef.current.push(dm);
        }

        // Refuel points
        for (const rp of state.refuel_points ?? []) {
            const icon = makeDivIcon('⛽', '#eab308', 34);
            if (icon) {
                const rm = L.marker([rp.lat, rp.lon], { icon, zIndexOffset: 900 })
                    .bindPopup(`<b>⛽ ${rp.name}</b><br>Refueling Station`)
                    .addTo(mapRef.current!);
                specialMarkersRef.current.push(rm);
            }
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [state.depot, state.refuel_points, makeDivIcon]);

    // ── Draw zone / bin markers ───────────────────────────────────────────────
    useEffect(() => {
        if (!mapRef.current || !leafletRef.current || !state.zones.length) return;
        const L = leafletRef.current;
        const map = mapRef.current;

        zoneMarkersRef.current.forEach(m => m.remove());
        zoneMarkersRef.current = [];

        const visible = showCollected ? state.zones : state.zones.filter(z => !z.collected);

        visible.forEach(zone => {
            const status = getFillStatus(zone.fill_level, zone.collected);
            const color = FILL_COLORS[status];
            const icon = POINT_TYPE_ICONS[zone.type] ?? '📍';
            const lat = zone.lat ?? (33.5731 + zone.y * 0.001);
            const lon = zone.lon ?? (-7.5898 + zone.x * 0.001);
            const radius = status === 'critical' ? 16 : status === 'urgent' ? 13 : 10;

            const m = L.circleMarker([lat, lon], {
                radius,
                fillColor: color,
                color: '#fff',
                weight: 2,
                opacity: 1,
                fillOpacity: zone.collected ? 0.4 : 0.9,
            })
                .bindPopup(
                    `<b>${icon} ${zone.name ?? `Zone ${zone.id}`}</b><br>` +
                    `Type: ${zone.type}<br>` +
                    `Fill: ${zone.fill_level.toFixed(0)}%<br>` +
                    `Volume: ${zone.volume_estime} L<br>` +
                    (zone.collected ? `<span style="color:#10b981">✓ Collected by Truck ${zone.collected_by}</span>` : '')
                )
                .addTo(map);

            zoneMarkersRef.current.push(m);
        });

        // Auto-fit bounds on new data payload
        if (!hasInitFitRef.current || prevCityRef.current !== currentCity) {
            const group = L.featureGroup([...zoneMarkersRef.current, ...specialMarkersRef.current, ...Array.from(truckMarkersRef.current.values())]);
            if (group.getBounds().isValid()) {
                map.fitBounds(group.getBounds().pad(0.1), { maxZoom: 13, animate: true });
                hasInitFitRef.current = true;
                prevCityRef.current = currentCity;
            }
        }
    }, [state.zones, showCollected, currentCity]);

    // ── Draw truck markers ────────────────────────────────────────────────────
    useEffect(() => {
        if (!mapRef.current || !leafletRef.current || !state.camions.length) return;
        const L = leafletRef.current;
        const map = mapRef.current;

        state.camions.forEach((camion, i) => {
            const lat = camion.lat ?? 33.5731 + i * 0.003;
            const lon = camion.lon ?? -7.5898 + i * 0.003;
            const color = TRUCK_COLORS[i % TRUCK_COLORS.length];
            const onDuty = camion.on_duty;
            const loadPct = camion.capacite > 0 ? (camion.charge_actuelle / camion.capacite) * 100 : 0;
            const emoji = onDuty ? '🚛' : '🚚';

            const icon = L.divIcon({
                html: `<div style="
          background:${color};border:3px solid ${onDuty ? '#ffffff' : 'rgba(255,255,255,0.4)'};
          border-radius:50%;width:36px;height:36px;
          display:flex;align-items:center;justify-content:center;
          font-size:18px;box-shadow:0 2px 10px rgba(0,0,0,0.6);
          opacity:${onDuty ? 1 : 0.6};transition:all 0.5s ease;">
          ${emoji}
        </div>`,
                className: '',
                iconSize: [36, 36],
                iconAnchor: [18, 18],
            });

            const popup = `<b>${emoji} Truck ${camion.id}</b><br>
        Status: ${onDuty ? '<span style="color:#22c55e">ON DUTY</span>' : '<span style="color:#6b7280">Off Duty</span>'}<br>
        Load: ${camion.charge_actuelle.toFixed(0)} / ${camion.capacite} L<br>
        Load: ${loadPct.toFixed(0)}%`;

            const existing = truckMarkersRef.current.get(camion.id);
            if (existing) {
                existing.setLatLng([lat, lon]);
                existing.setIcon(icon);
                existing.setPopupContent(popup);
            } else {
                const m = L.marker([lat, lon], { icon, zIndexOffset: 800 })
                    .bindPopup(popup)
                    .addTo(map);
                truckMarkersRef.current.set(camion.id, m);
            }
        });
    }, [state.camions]);

    // ── Draw route polylines ──────────────────────────────────────────────────
    useEffect(() => {
        if (!mapRef.current || !leafletRef.current) return;
        const L = leafletRef.current;

        routeLinesRef.current.forEach(r => r.remove());
        routeLinesRef.current = [];

        if (!showRoutes) return;

        (state.routes ?? []).forEach((route, i) => {
            if (!route.points?.length) return;

            const latlngs = route.points.map(p => {
                // Use lat/lon directly if available (preferred), else convert from x/y
                const lat = p.lat ?? (p.y / 100);
                const lon = p.lon ?? (p.x / 100);
                return [lat, lon] as [number, number];
            });

            if (latlngs.length < 2) return;

            const color = TRUCK_COLORS[i % TRUCK_COLORS.length];
            const line = L.polyline(latlngs, {
                color,
                weight: 4,
                opacity: 0.85,
                dashArray: '8 5',
            }).addTo(mapRef.current!);

            // Arrow decorations for direction (endpoints)
            const lastPt = latlngs[latlngs.length - 1];
            L.marker(lastPt, {
                icon: L.divIcon({
                    html: `<div style="color:${color};font-size:16px;transform:rotate(-45deg);">➤</div>`,
                    className: '',
                    iconSize: [20, 20],
                    iconAnchor: [10, 10],
                }),
                zIndexOffset: 500,
            }).bindTooltip(`Truck ${route.camion_id} — ${route.distance_km?.toFixed(1) ?? '?'} km`)
                .addTo(mapRef.current!);

            routeLinesRef.current.push(line);
        });
    }, [state.routes, showRoutes]);

    return (
        <div className="relative w-full h-full rounded-xl overflow-hidden shadow-2xl">
            <div ref={containerRef} className="w-full h-full" />

            {/* Controls overlay */}
            <div className="absolute top-3 right-3 z-[1000] flex flex-col gap-1.5">
                <button
                    onClick={() => setSatellite(s => !s)}
                    className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-white rounded-lg
            bg-gray-900/90 backdrop-blur border border-white/20 hover:bg-gray-800 transition"
                >
                    {satellite ? '🗺️ Street' : '🛰 Satellite'}
                </button>
                <button
                    onClick={() => setShowRoutes(r => !r)}
                    className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg
            backdrop-blur border transition
            ${showRoutes ? 'bg-blue-600/80 border-blue-400/40 text-white' : 'bg-gray-900/90 border-white/20 text-gray-400'}`}
                >
                    🛣️ Routes
                </button>
                <button
                    onClick={() => setShowCollected(c => !c)}
                    className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg
            backdrop-blur border transition
            ${showCollected ? 'bg-emerald-600/80 border-emerald-400/40 text-white' : 'bg-gray-900/90 border-white/20 text-gray-400'}`}
                >
                    ✓ Collected
                </button>
            </div>

            {/* Legend */}
            <div className="absolute bottom-6 left-3 z-[1000] bg-gray-900/90 backdrop-blur rounded-lg p-3 text-xs text-white space-y-1 border border-white/10">
                <p className="font-bold mb-1 text-gray-300">Bin Fill Level</p>
                {([
                    ['ok', '#22c55e', '< 70%'],
                    ['warning', '#f59e0b', '70–89%'],
                    ['urgent', '#ef4444', '90–94%'],
                    ['critical', '#7c3aed', '≥ 95%'],
                    ['collected', '#6b7280', 'Collected'],
                ] as const).map(([label, color, pct]) => (
                    <div key={label} className="flex items-center gap-2">
                        <span className="w-3 h-3 rounded-full inline-block" style={{ background: color }} />
                        <span className="capitalize">{label}</span>
                        <span className="text-gray-400">{pct}</span>
                    </div>
                ))}
                <hr className="border-white/10 my-1" />
                <div className="flex items-center gap-2"><span>📦</span><span>Depot</span></div>
                <div className="flex items-center gap-2"><span>⛽</span><span>Refuel</span></div>
                <div className="flex items-center gap-2"><span>🚛</span><span>On-Duty Truck</span></div>
            </div>
        </div>
    );
}
