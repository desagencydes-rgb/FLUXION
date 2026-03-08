'use client';
import { useState, useEffect } from 'react';
import { useSimulation } from '@/hooks/useSimulation';
import DutyToggle from '@/components/driver/DutyToggle';
import TourneeChecklist from '@/components/driver/TourneeChecklist';
import ThemeToggle from '@/components/ThemeToggle';

const STORAGE_KEY = 'fluxion_driver_truck_id';

export default function DriverPage() {
    const { state, loading } = useSimulation(3000);

    // Persist truck selection across reloads
    const [selectedId, setSelectedId] = useState<number | null>(null);
    const [selectorOpen, setSelectorOpen] = useState(false);
    const [selectedCity, setSelectedCity] = useState<string>('Casablanca');
    const [citySelectorOpen, setCitySelectorOpen] = useState(false);

    // Load saved truck on mount — only once we have camion data
    useEffect(() => {
        if (state.camions.length === 0) return;
        const saved = localStorage.getItem(STORAGE_KEY);
        if (saved) {
            const id = Number(saved);
            const exists = state.camions.find(c => c.id === id);
            setSelectedId(exists ? id : state.camions[0].id);
            if (exists && exists.city) {
                setSelectedCity(exists.city);
            }
        } else {
            setSelectedId(state.camions[0].id);
            const firstCity = state.camions[0].city || 'Casablanca';
            setSelectedCity(firstCity);
        }
    }, [state.camions]); // eslint-disable-line react-hooks/exhaustive-deps

    const filteredCamions = state.camions.filter(c => (c.city || 'Casablanca') === selectedCity);
    const myTruck = state.camions.find(c => c.id === selectedId) ?? state.camions[0];

    const selectTruck = (id: number) => {
        setSelectedId(id);
        localStorage.setItem(STORAGE_KEY, String(id));
        setSelectorOpen(false);
    };

    const cities = Array.from(new Set(state.camions.map(c => c.city || 'Casablanca')));

    const filteredZones = state.zones.filter(z => (z.city || 'Casablanca') === selectedCity);

    return (
        <div className="min-h-screen bg-gray-950 text-white flex flex-col max-w-md mx-auto">
            {/* Header */}
            <header className="sticky top-0 z-50 bg-gray-900/90 backdrop-blur border-b border-white/10 px-4 py-3 flex items-center justify-between">
                <div>
                    <h1 className="text-lg font-black bg-gradient-to-r from-blue-400 to-emerald-400 bg-clip-text text-transparent">
                        FLUXION
                    </h1>
                    <p className="text-xs text-gray-400">Driver Console</p>
                </div>
                <div className="flex items-center gap-3">
                    {/* City selector */}
                    {cities.length > 0 && (
                        <div className="relative">
                            <button
                                onClick={() => { setCitySelectorOpen(o => !o); setSelectorOpen(false); }}
                                className="flex items-center gap-1.5 bg-gray-800/60 border border-white/10 rounded-xl px-3 py-1.5 text-xs hover:border-emerald-500/40 transition"
                            >
                                <span className="text-gray-400">City</span>
                                <span className="text-emerald-400 font-bold">{selectedCity}</span>
                                <span className="text-gray-600">▾</span>
                            </button>

                            {citySelectorOpen && (
                                <div className="absolute right-0 top-full mt-1 bg-gray-900 border border-white/10 rounded-xl shadow-2xl overflow-hidden z-50 min-w-[120px]">
                                    {cities.map(c => (
                                        <button
                                            key={c}
                                            onClick={() => {
                                                setSelectedCity(c);
                                                setCitySelectorOpen(false);
                                                // Default to a valid truck in the new city
                                                const newCityTrucks = state.camions.filter(t => (t.city || 'Casablanca') === c);
                                                if (newCityTrucks.length > 0) {
                                                    setSelectedId(newCityTrucks[0].id);
                                                    localStorage.setItem(STORAGE_KEY, String(newCityTrucks[0].id));
                                                }
                                            }}
                                            className={`w-full text-left px-4 py-2.5 text-xs transition
                                                ${c === selectedCity
                                                    ? 'bg-emerald-500/20 text-emerald-300 font-bold'
                                                    : 'text-gray-300 hover:bg-gray-800'
                                                }`}
                                        >
                                            {c}
                                        </button>
                                    ))}
                                </div>
                            )}
                        </div>
                    )}

                    {/* Truck selector */}
                    {filteredCamions.length > 0 && (
                        <div className="relative">
                            <button
                                onClick={() => { setSelectorOpen(o => !o); setCitySelectorOpen(false); }}
                                className="flex items-center gap-1.5 bg-gray-800/60 border border-white/10 rounded-xl px-3 py-1.5 text-xs hover:border-blue-500/40 transition"
                            >
                                <span className="text-gray-400">Truck</span>
                                <span className="text-blue-400 font-bold">#{myTruck?.id ?? '—'}</span>
                                <span className="text-gray-600">▾</span>
                            </button>

                            {selectorOpen && (
                                <div className="absolute right-0 top-full mt-1 bg-gray-900 border border-white/10 rounded-xl shadow-2xl overflow-hidden z-50 min-w-[120px]">
                                    {filteredCamions.map(c => (
                                        <button
                                            key={c.id}
                                            onClick={() => selectTruck(c.id)}
                                            className={`w-full text-left px-4 py-2.5 text-xs transition
                                                ${c.id === selectedId
                                                    ? 'bg-blue-500/20 text-blue-300 font-bold'
                                                    : 'text-gray-300 hover:bg-gray-800'
                                                }`}
                                        >
                                            Truck #{c.id}
                                            <span className="ml-2 text-gray-500">{c.capacite} kg</span>
                                        </button>
                                    ))}
                                </div>
                            )}
                        </div>
                    )}
                    <ThemeToggle />
                    <a href="/" className="text-xs text-gray-500 hover:text-white transition">Fleet →</a>
                </div>
            </header>

            <main className="flex-1 flex flex-col gap-4 p-4 pb-8">
                {/* Duty toggle */}
                <section className="bg-gray-900/60 border border-white/10 rounded-2xl p-6 flex flex-col items-center gap-2">
                    <DutyToggle camionId={myTruck?.id ?? 1} />

                    {/* Truck load mini-bar */}
                    {myTruck && (
                        <div className="w-full mt-2 space-y-1">
                            <div className="flex justify-between text-xs text-gray-400">
                                <span>Load</span>
                                <span>{myTruck.charge_actuelle.toFixed(0)} / {myTruck.capacite} kg</span>
                            </div>
                            <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
                                <div
                                    className="h-full rounded-full bg-gradient-to-r from-blue-500 to-violet-500 transition-all duration-500"
                                    style={{ width: `${Math.min(100, (myTruck.charge_actuelle / myTruck.capacite) * 100)}%` }}
                                />
                            </div>
                        </div>
                    )}
                </section>

                {/* Today's route status strip */}
                <div className="grid grid-cols-2 gap-3">
                    <div className="bg-gray-800/60 border border-white/10 rounded-xl p-3 text-center">
                        <p className="text-2xl font-bold text-white">{filteredZones.length}</p>
                        <p className="text-xs text-gray-400">Total Stops</p>
                    </div>
                    <div className="bg-gray-800/60 border border-white/10 rounded-xl p-3 text-center">
                        <p className="text-2xl font-bold text-red-400">
                            {filteredZones.filter(z => z.fill_level >= 90).length}
                        </p>
                        <p className="text-xs text-gray-400">Urgent Bins</p>
                    </div>
                </div>

                {/* Tournée checklist */}
                <section className="bg-gray-900/60 border border-white/10 rounded-2xl p-4 flex-1 flex flex-col">
                    <div className="flex justify-between items-center mb-3">
                        <h2 className="text-sm font-bold text-gray-300">Today&apos;s Route</h2>
                        <span className="text-xs bg-emerald-500/20 text-emerald-400 px-2 py-0.5 rounded-full border border-emerald-500/30">
                            {selectedCity}
                        </span>
                    </div>

                    {loading ? (
                        <div className="flex items-center justify-center py-8">
                            <div className="w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
                        </div>
                    ) : !myTruck ? (
                        <div className="flex-1 flex flex-col items-center justify-center text-center py-8 px-4 text-gray-500">
                            <p className="text-3xl mb-2">🚫</p>
                            <p className="text-sm">No trucks assigned to {selectedCity}</p>
                            <p className="text-xs mt-1">Select a different city above</p>
                        </div>
                    ) : (
                        <TourneeChecklist
                            zones={filteredZones}
                            routes={state.routes}
                            camionId={myTruck.id}
                        />
                    )}
                </section>

                {/* Recent events (driver-visible) */}
                {state.recent_events.length > 0 && (
                    <section className="bg-gray-900/60 border border-white/10 rounded-2xl p-4">
                        <h2 className="text-sm font-bold text-gray-300 mb-2">Alerts</h2>
                        <div className="space-y-1.5">
                            {state.recent_events.slice(0, 5).map((e, i) => (
                                <div key={i} className="flex gap-2 text-xs text-gray-300">
                                    <span className="text-amber-400 shrink-0">⚠</span>
                                    <span>{typeof e === 'string' ? e : JSON.stringify(e)}</span>
                                </div>
                            ))}
                        </div>
                    </section>
                )}
            </main>
        </div>
    );
}
