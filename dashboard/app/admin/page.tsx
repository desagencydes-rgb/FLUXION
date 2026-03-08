'use client';
import { useState, useEffect, useRef, useCallback } from 'react';
import { api } from '@/lib/api';
import { useSimulation } from '@/hooks/useSimulation';
import Link from 'next/link';
import ThemeToggle from '@/components/ThemeToggle';

interface Zone { id: number; x: number; y: number; volume: number; city?: string; }
interface Truck { id: number; capacite: number; cout_fixe: number; city?: string; }
interface Config { level: number; zones: Zone[]; camions: Truck[]; depot: Zone; }

const LEVELS = [
    { id: 1, label: 'L1 — Dijkstra (Road Network)', color: 'text-blue-400' },
    { id: 2, label: 'L2 — Bipartite (Fleet Assignment)', color: 'text-teal-400' },
    { id: 3, label: 'L3 — Tripartite (Temporal Planning)', color: 'text-emerald-400' },
    { id: 4, label: 'L4 — VRP (2-opt + Tabu Search)', color: 'text-amber-400' },
    { id: 5, label: 'L5 — NSGA-II (Dynamic Brain)', color: 'text-violet-400' },
];

export default function AdminPage() {
    useSimulation(5000); // Maintain background activity
    const [config, setConfig] = useState<Config | null>(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [msg, setMsg] = useState<{ text: string; ok: boolean } | null>(null);
    const [isAuthenticated, setIsAuthenticated] = useState(false);
    const [pin, setPin] = useState('');

    const [selectedCities, setSelectedCities] = useState<string[]>(['All']);
    const [citySelectorOpen, setCitySelectorOpen] = useState(false);

    // New zone form
    const [newZone, setNewZone] = useState({ id: '', x: '', y: '', volume: '', city: 'Casablanca' });
    // New truck form
    const [newTruck, setNewTruck] = useState({ id: '', capacite: '', cout_fixe: '', city: 'Casablanca' });

    const load = async () => {
        try {
            const data = await api.getConfig();
            setConfig(data as unknown as Config);
        } catch (e) {
            setMsg({ text: `Failed to load config: ${e instanceof Error ? e.message : e}`, ok: false });
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => { load(); }, []);

    const flash = (text: string, ok: boolean) => {
        setMsg({ text, ok });
        setTimeout(() => setMsg(null), 3500);
    };

    const addZone = async () => {
        if (!config) return;
        if (!newZone.id || !newZone.x || !newZone.y) return flash('Fill all zone fields', false);
        const z: Zone = {
            id: Number(newZone.id), x: Number(newZone.x),
            y: Number(newZone.y), volume: Number(newZone.volume) || 0,
            city: newZone.city
        };
        const zones = [...config.zones, z];
        await applyConfig({ ...config, zones });
        setNewZone({ id: '', x: '', y: '', volume: '', city: newZone.city });
    };

    const addTruck = async () => {
        if (!config) return;
        if (!newTruck.id || !newTruck.capacite) return flash('Fill all truck fields', false);
        const t: Truck = {
            id: Number(newTruck.id), capacite: Number(newTruck.capacite),
            cout_fixe: Number(newTruck.cout_fixe) || 0,
            city: newTruck.city
        };
        const camions = [...config.camions, t];
        await applyConfig({ ...config, camions });
        setNewTruck({ id: '', capacite: '', cout_fixe: '', city: newTruck.city });
    };

    const removeZone = async (id: number) => {
        if (!config) return;
        await applyConfig({ ...config, zones: config.zones.filter(z => z.id !== id) });
    };

    const removeTruck = async (id: number) => {
        if (!config) return;
        await applyConfig({ ...config, camions: config.camions.filter(c => c.id !== id) });
    };

    const setLevel = async (level: number) => {
        if (!config) return;
        await applyConfig({ ...config, level });
    };

    const applyConfig = async (cfg: Config) => {
        setSaving(true);
        try {
            await api.setConfig(cfg);
            setConfig(cfg);
            flash('Configuration saved ✓', true);
        } catch (e) {
            flash(`Error: ${e instanceof Error ? e.message : e}`, false);
        } finally {
            setSaving(false);
        }
    };

    const cities = Array.from(new Set([
        ...(config?.zones.map(z => z.city || 'Casablanca') || []),
        ...(config?.camions.map(c => c.city || 'Casablanca') || [])
    ]));

    const filteredZones = config?.zones.filter(z => selectedCities.includes('All') || selectedCities.includes(z.city || 'Casablanca')) || [];
    const filteredTrucks = config?.camions.filter(c => selectedCities.includes('All') || selectedCities.includes(c.city || 'Casablanca')) || [];

    if (!isAuthenticated) {
        return (
            <div className="min-h-screen bg-gray-950 flex flex-col items-center justify-center text-white">
                <div className="bg-gray-900 border border-white/10 rounded-2xl p-8 w-[340px] shadow-2xl flex flex-col items-center">
                    <div className="w-12 h-12 bg-violet-500/20 text-violet-400 rounded-full flex items-center justify-center text-2xl mb-4">🔐</div>
                    <h2 className="text-xl font-bold mb-1 text-white">Admin Access</h2>
                    <p className="text-xs text-gray-500 mb-6 text-center">Enter your verification PIN</p>
                    <input
                        type="password"
                        value={pin}
                        onChange={e => setPin(e.target.value)}
                        placeholder="••••"
                        className="w-full bg-gray-800/60 border border-white/10 rounded-xl px-4 py-3 text-center text-2xl tracking-[0.5em] mb-4 focus:outline-none focus:border-violet-500/50 transition text-white placeholder-gray-700"
                        onKeyDown={e => {
                            if (e.key === 'Enter') {
                                if (pin === '1234') setIsAuthenticated(true);
                                else setPin('');
                            }
                        }}
                    />
                    <button
                        onClick={() => {
                            if (pin === '1234') setIsAuthenticated(true);
                            else setPin('');
                        }}
                        className="w-full bg-violet-600 hover:bg-violet-500 py-3 rounded-xl font-bold transition text-sm text-white"
                    >
                        Unlock Dashboard
                    </button>
                    <Link href="/" className="text-xs text-gray-500 hover:text-white transition mt-6">← Return to Fleet</Link>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gray-950 text-white">
            {/* Header */}
            <header className="sticky top-0 z-50 border-b border-white/10 px-6 py-3 bg-gray-900/80 backdrop-blur flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <span className="text-xl font-black tracking-tight bg-gradient-to-r from-blue-400 to-emerald-400 bg-clip-text text-transparent">
                        FLUXION
                    </span>
                    <span className="text-xs bg-violet-500/20 text-violet-400 px-2 py-0.5 rounded-full border border-violet-500/30">
                        Admin Config
                    </span>

                    {/* City selector */}
                    {cities.length > 0 && (
                        <div className="relative ml-4">
                            <button
                                onClick={() => setCitySelectorOpen(o => !o)}
                                className="flex items-center gap-1.5 bg-gray-800/60 border border-white/10 rounded-xl px-3 py-1.5 text-xs hover:border-emerald-500/40 transition"
                            >
                                <span className="text-gray-400">City</span>
                                <span className="text-emerald-400 font-bold">
                                    {selectedCities.includes('All') ? 'All' : selectedCities.length === 1 ? selectedCities[0] : `${selectedCities.length} selected`}
                                </span>
                                <span className="text-gray-600">▾</span>
                            </button>

                            {citySelectorOpen && (
                                <div className="absolute left-0 top-full mt-1 bg-gray-900 border border-white/10 rounded-xl shadow-2xl overflow-hidden z-50 min-w-[200px] max-h-64 overflow-y-auto">
                                    <button
                                        onClick={() => { setSelectedCities(['All']); setCitySelectorOpen(false); }}
                                        className={`w-full text-left px-4 py-2.5 text-xs transition flex items-center justify-between ${selectedCities.includes('All') ? 'bg-emerald-500/20 text-emerald-300 font-bold' : 'text-gray-300 hover:bg-gray-800'}`}
                                    >
                                        All {selectedCities.includes('All') && '✓'}
                                    </button>
                                    {cities.map(c => (
                                        <button
                                            key={c}
                                            onClick={() => {
                                                if (selectedCities.includes('All')) {
                                                    setSelectedCities([c]);
                                                } else if (selectedCities.includes(c)) {
                                                    const next = selectedCities.filter(x => x !== c);
                                                    setSelectedCities(next.length ? next : ['All']);
                                                } else {
                                                    setSelectedCities([...selectedCities, c]);
                                                }
                                            }}
                                            className={`w-full text-left px-4 py-2.5 text-xs transition flex flex-row items-center justify-between ${!selectedCities.includes('All') && selectedCities.includes(c) ? 'bg-emerald-500/20 text-emerald-300 font-bold' : 'text-gray-300 hover:bg-gray-800'}`}
                                        >
                                            {c} {!selectedCities.includes('All') && selectedCities.includes(c) && '✓'}
                                        </button>
                                    ))}
                                </div>
                            )}
                        </div>
                    )}
                </div>
                <div className="flex items-center gap-4 text-sm">
                    <ThemeToggle />
                    <Link href="/" className="text-xs text-gray-400 hover:text-white transition">← Dashboard</Link>
                    <Link href="/driver" className="text-xs text-gray-400 hover:text-white transition">Driver view →</Link>
                </div>
            </header>

            {/* Flash message */}
            {msg && (
                <div className={`mx-6 mt-4 px-4 py-2 rounded-lg text-sm font-medium border ${msg.ok
                    ? 'bg-emerald-500/20 border-emerald-500/30 text-emerald-300'
                    : 'bg-red-500/20 border-red-500/30 text-red-300'}`}>
                    {msg.text}
                </div>
            )}

            <main className="p-6 space-y-6 max-w-5xl mx-auto">

                {/* Algorithm Level Selector */}
                <section className="bg-gray-900/60 border border-white/10 rounded-2xl p-5">
                    <h2 className="text-sm font-bold text-gray-300 uppercase tracking-wider mb-3">Algorithm Level</h2>
                    <div className="grid grid-cols-1 sm:grid-cols-5 gap-2">
                        {LEVELS.map(l => (
                            <button
                                key={l.id}
                                onClick={() => setLevel(l.id)}
                                disabled={saving}
                                className={`text-left p-3 rounded-xl border text-xs font-medium transition
                                    ${config?.level === l.id
                                        ? 'border-blue-500/60 bg-blue-500/15 text-blue-300'
                                        : 'border-white/10 bg-gray-800/40 text-gray-400 hover:border-white/20 hover:text-white'
                                    }`}
                            >
                                <span className={`block text-lg mb-1 ${l.color}`}>L{l.id}</span>
                                {l.label.split(' — ')[1]}
                            </button>
                        ))}
                    </div>
                </section>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

                    {/* Collection Zones */}
                    <section className="bg-gray-900/60 border border-white/10 rounded-2xl p-5">
                        <h2 className="text-sm font-bold text-gray-300 uppercase tracking-wider mb-3">
                            Collection Zones
                            <span className="ml-2 text-gray-500 font-normal normal-case">({filteredZones.length})</span>
                        </h2>

                        {loading ? (
                            <div className="h-24 flex items-center justify-center">
                                <div className="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
                            </div>
                        ) : (
                            <div className="space-y-1.5 max-h-48 overflow-y-auto mb-4">
                                {filteredZones.map(z => (
                                    <div key={z.id} className="flex items-center justify-between text-xs bg-gray-800/50 rounded-lg px-3 py-2">
                                        <span className="text-blue-400 font-mono w-8">#{z.id}</span>
                                        <span className="text-gray-400 flex-1">x:{z.x.toFixed(1)} y:{z.y.toFixed(1)}</span>
                                        <span className="text-gray-500">{z.volume}vol</span>
                                        <button
                                            onClick={() => removeZone(z.id)}
                                            className="ml-3 text-red-400/70 hover:text-red-400 transition text-xs"
                                        >✕</button>
                                    </div>
                                ))}
                                {!filteredZones.length && (
                                    <p className="text-gray-600 text-xs text-center py-4">No zones configured for selected filters</p>
                                )}
                            </div>
                        )}

                        {/* Add zone form */}
                        <div className="border-t border-white/5 pt-3 space-y-2">
                            <p className="text-xs text-gray-500 font-medium">Add Zone</p>
                            <div className="grid grid-cols-2 gap-2">
                                {(['id', 'x', 'y', 'volume'] as const).map(field => (
                                    <input
                                        key={field}
                                        type="number"
                                        placeholder={field === 'x' ? 'Longitude (x)' : field === 'y' ? 'Latitude (y)' : field}
                                        value={newZone[field as keyof typeof newZone]}
                                        onChange={e => setNewZone(p => ({ ...p, [field]: e.target.value }))}
                                        className="bg-gray-800/60 border border-white/10 rounded-lg px-3 py-1.5 text-xs text-white placeholder-gray-600 focus:outline-none focus:border-blue-500/60"
                                    />
                                ))}
                            </div>
                            <button
                                onClick={addZone}
                                disabled={saving}
                                className="w-full py-1.5 text-xs rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-50 transition font-medium"
                            >
                                + Add Zone
                            </button>
                        </div>
                    </section>

                    {/* Fleet / Trucks */}
                    <section className="bg-gray-900/60 border border-white/10 rounded-2xl p-5">
                        <h2 className="text-sm font-bold text-gray-300 uppercase tracking-wider mb-3">
                            Fleet
                            <span className="ml-2 text-gray-500 font-normal normal-case">({filteredTrucks.length} trucks)</span>
                        </h2>

                        {loading ? (
                            <div className="h-24 flex items-center justify-center">
                                <div className="w-5 h-5 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" />
                            </div>
                        ) : (
                            <div className="space-y-1.5 max-h-48 overflow-y-auto mb-4">
                                {filteredTrucks.map(c => (
                                    <div key={c.id} className="flex items-center justify-between text-xs bg-gray-800/50 rounded-lg px-3 py-2">
                                        <span className="text-emerald-400 font-mono w-8">#{c.id}</span>
                                        <span className="text-gray-400 flex-1">{c.capacite} kg cap</span>
                                        <span className="text-gray-500">€{c.cout_fixe}/day</span>
                                        <button
                                            onClick={() => removeTruck(c.id)}
                                            className="ml-3 text-red-400/70 hover:text-red-400 transition text-xs"
                                        >✕</button>
                                    </div>
                                ))}
                                {!filteredTrucks.length && (
                                    <p className="text-gray-600 text-xs text-center py-4">No trucks configured for selected filters</p>
                                )}
                            </div>
                        )}

                        {/* Add truck form */}
                        <div className="border-t border-white/5 pt-3 space-y-2">
                            <p className="text-xs text-gray-500 font-medium">Add Truck</p>
                            <div className="grid grid-cols-3 gap-2">
                                {(['id', 'capacite', 'cout_fixe'] as const).map(field => (
                                    <input
                                        key={field}
                                        type="number"
                                        placeholder={field}
                                        value={newTruck[field]}
                                        onChange={e => setNewTruck(p => ({ ...p, [field]: e.target.value }))}
                                        className="bg-gray-800/60 border border-white/10 rounded-lg px-3 py-1.5 text-xs text-white placeholder-gray-600 focus:outline-none focus:border-emerald-500/60"
                                    />
                                ))}
                            </div>
                            <button
                                onClick={addTruck}
                                disabled={saving}
                                className="w-full py-1.5 text-xs rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 transition font-medium"
                            >
                                + Add Truck
                            </button>
                        </div>
                    </section>
                </div>

                {/* ── CSV/Excel Import ───────────────────── */}
                <section className="bg-gray-900/60 border border-white/10 rounded-2xl p-5">
                    <h2 className="text-sm font-bold text-gray-300 uppercase tracking-wider mb-1">Import from CSV / Excel</h2>
                    <p className="text-xs text-gray-500 mb-4">Upload collection points or truck fleet data. Replaces current simulation data.</p>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <ImportDropzone
                            label="Collection Points"
                            icon="📍"
                            color="blue"
                            description="Columns: id, lat, lon, name, type, volume_l"
                            sampleRows={[
                                'id,lat,lon,name,type,volume_l',
                                '1,33.5731,-7.5898,Hotel Atlas,hotel,800',
                                '2,33.5850,-7.6100,CHU Ibn Rochd,hospital,200',
                            ]}
                            onUpload={async (file) => {
                                const result = await api.importPoints(file);
                                return `Imported ${result.imported_points} points${result.errors?.length ? ` (${result.errors.length} errors)` : ''}`;
                            }}
                            onSuccess={() => { load(); flash('Points imported — simulation reloaded ✓', true); }}
                            onError={(e) => flash(`Import failed: ${e}`, false)}
                        />
                        <ImportDropzone
                            label="Truck Fleet"
                            icon="🚛"
                            color="emerald"
                            description="Columns: id, capacity_l, name, type, speed_kmh"
                            sampleRows={[
                                'id,capacity_l,name,type,speed_kmh',
                                '1,5000,Truck Alpha,standard,60',
                                '2,15000,Heavy Loader,heavy,45',
                            ]}
                            onUpload={async (file) => {
                                const result = await api.importTrucks(file);
                                return `Imported ${result.imported_trucks} trucks${result.errors?.length ? ` (${result.errors.length} errors)` : ''}`;
                            }}
                            onSuccess={() => { load(); flash('Fleet imported — simulation reloaded ✓', true); }}
                            onError={(e) => flash(`Import failed: ${e}`, false)}
                        />
                    </div>
                </section>
            </main>
        </div>
    );
}

// ── Import Dropzone Component ─────────────────────────────────────────────────

interface ImportDropzoneProps {
    label: string;
    icon: string;
    color: 'blue' | 'emerald';
    description: string;
    sampleRows: string[];
    onUpload: (file: File) => Promise<string>;
    onSuccess: () => void;
    onError: (msg: string) => void;
}

function ImportDropzone({ label, icon, color, description, sampleRows, onUpload, onSuccess, onError }: ImportDropzoneProps) {
    const inputRef = useRef<HTMLInputElement>(null);
    const [drag, setDrag] = useState(false);
    const [busy, setBusy] = useState(false);
    const [result, setResult] = useState<string | null>(null);

    const colorMap = {
        blue: { border: 'border-blue-500/50', bg: 'bg-blue-500/10', text: 'text-blue-400', btn: 'bg-blue-600 hover:bg-blue-500' },
        emerald: { border: 'border-emerald-500/50', bg: 'bg-emerald-500/10', text: 'text-emerald-400', btn: 'bg-emerald-600 hover:bg-emerald-500' },
    }[color];

    const handleFile = useCallback(async (file: File) => {
        if (!file.name.match(/\.(csv|xlsx|xls)$/i)) {
            onError('File must be .csv or .xlsx'); return;
        }
        setBusy(true); setResult(null);
        try {
            const msg = await onUpload(file);
            setResult(msg);
            onSuccess();
        } catch (e) {
            onError(e instanceof Error ? e.message : String(e));
        } finally {
            setBusy(false);
        }
    }, [onUpload, onSuccess, onError]);

    const downloadSample = useCallback(() => {
        const csv = sampleRows.join('\n');
        const blob = new Blob([csv], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a'); a.href = url; a.download = `sample_${label.toLowerCase().replace(' ', '_')}.csv`;
        a.click(); URL.revokeObjectURL(url);
    }, [sampleRows, label]);

    return (
        <div className="space-y-3">
            <div className="flex items-center justify-between">
                <p className="text-xs font-semibold text-gray-300">{icon} {label}</p>
                <button onClick={downloadSample} className="text-xs text-gray-500 hover:text-gray-300 transition underline">⬇ Sample CSV</button>
            </div>
            <p className="text-xs text-gray-500 font-mono">{description}</p>

            {/* Drop area */}
            <div
                onClick={() => inputRef.current?.click()}
                onDragOver={e => { e.preventDefault(); setDrag(true); }}
                onDragLeave={() => setDrag(false)}
                onDrop={e => { e.preventDefault(); setDrag(false); const f = e.dataTransfer.files[0]; if (f) handleFile(f); }}
                className={`relative flex flex-col items-center justify-center gap-2 p-6 rounded-xl border-2 border-dashed cursor-pointer transition
                    ${drag ? `${colorMap.border} ${colorMap.bg}` : 'border-white/10 hover:border-white/20 bg-gray-800/30'}`}
            >
                <input ref={inputRef} type="file" accept=".csv,.xlsx,.xls" className="sr-only"
                    onChange={e => { const f = e.target.files?.[0]; if (f) { handleFile(f); e.target.value = ''; } }} />

                {busy ? (
                    <div className="w-6 h-6 border-2 border-current border-t-transparent rounded-full animate-spin text-gray-400" />
                ) : (
                    <>
                        <span className="text-3xl">{drag ? '📂' : '📁'}</span>
                        <p className="text-xs text-gray-400 text-center">
                            <span className={`font-semibold ${colorMap.text}`}>Click to upload</span> or drag &amp; drop<br />
                            <span className="text-gray-600">.csv, .xlsx supported</span>
                        </p>
                    </>
                )}
            </div>

            {result && (
                <div className={`text-xs px-3 py-2 rounded-lg border ${colorMap.border} ${colorMap.bg} ${colorMap.text}`}>
                    ✓ {result}
                </div>
            )}
        </div>
    );
}
