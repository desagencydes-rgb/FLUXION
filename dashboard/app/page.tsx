'use client';
import { useState } from 'react';
import dynamic from 'next/dynamic';
import { useSimulation } from '@/hooks/useSimulation';
import { useSavings } from '@/hooks/useSavings';
import SavingsWidget from '@/components/analytics/SavingsWidget';
import WeightSliders from '@/components/controls/WeightSliders';
import IncidentSimulator from '@/components/controls/IncidentSimulator';
import ThemeToggle from '@/components/ThemeToggle';

// Dynamic import for Leaflet (no SSR)
const FluxionMap = dynamic(() => import('@/components/map/FluxionMap'), {
  ssr: false,
  loading: () => (
    <div className="w-full h-full flex items-center justify-center bg-gray-900 rounded-xl">
      <div className="flex flex-col items-center gap-3 text-gray-400">
        <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
        <span className="text-sm">Loading map…</span>
      </div>
    </div>
  ),
});

export default function DashboardPage() {
  const { state, loading, error, play, pause, step } = useSimulation();
  const { savings, history } = useSavings();

  const [selectedCities, setSelectedCities] = useState<string[]>(['All']);
  const [citySelectorOpen, setCitySelectorOpen] = useState(false);

  const cities = Array.from(new Set([
    ...state.zones.map(z => z.city || 'Casablanca'),
    ...state.camions.map(c => c.city || 'Casablanca')
  ]));

  const filteredState = {
    ...state,
    zones: selectedCities.includes('All') ? state.zones : state.zones.filter(z => selectedCities.includes(z.city || 'Casablanca')),
    camions: selectedCities.includes('All') ? state.camions : state.camions.filter(c => selectedCities.includes(c.city || 'Casablanca')),
    routes: selectedCities.includes('All') ? state.routes : state.routes.filter(r => {
      const c = state.camions.find(tc => tc.id === r.camion_id);
      return c && selectedCities.includes(c.city || 'Casablanca');
    })
  };

  const urgentCount = filteredState.zones.filter(z => z.fill_level >= 90).length;
  const criticalCount = filteredState.zones.filter(z => z.fill_level >= 95).length;

  return (
    <div className="min-h-screen bg-gray-950 text-white flex flex-col">
      {/* ── Top Nav ───────────────────────────────────────────────────────── */}
      <header className="border-b border-white/10 px-6 py-3 flex items-center justify-between bg-gray-900/80 backdrop-blur sticky top-0 z-50">
        <div className="flex items-center gap-3">
          <span className="text-2xl font-black tracking-tight bg-gradient-to-r from-blue-400 to-emerald-400 bg-clip-text text-transparent">
            FLUXION
          </span>
          <span className="text-xs bg-blue-500/20 text-blue-400 px-2 py-0.5 rounded-full border border-blue-500/30">
            Fleet Manager
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
                      className={`w-full text-left px-4 py-2.5 text-xs transition flex items-center justify-between ${!selectedCities.includes('All') && selectedCities.includes(c) ? 'bg-emerald-500/20 text-emerald-300 font-bold' : 'text-gray-300 hover:bg-gray-800'}`}
                    >
                      {c} {!selectedCities.includes('All') && selectedCities.includes(c) && '✓'}
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* KPI badges */}
        <div className="hidden md:flex items-center gap-4 text-sm">
          {criticalCount > 0 && (
            <span className="flex items-center gap-1 bg-violet-500/20 text-violet-400 px-3 py-1 rounded-full animate-pulse">
              <span>🟣</span> {criticalCount} Critical
            </span>
          )}
          {urgentCount > 0 && (
            <span className="flex items-center gap-1 bg-red-500/20 text-red-400 px-3 py-1 rounded-full">
              <span>🔴</span> {urgentCount} Urgent
            </span>
          )}
          <span className={`flex items-center gap-1 px-3 py-1 rounded-full ${state.status === 'running'
            ? 'bg-green-500/20 text-green-400'
            : 'bg-gray-500/20 text-gray-400'
            }`}>
            <span>{state.status === 'running' ? '▶' : '⏸'}</span>
            {state.status === 'running' ? 'Live' : 'Paused'}
          </span>
          <a href="/admin" className="text-xs text-gray-400 hover:text-white transition">⚙ Admin →</a>
          <a href="/driver" className="text-xs text-gray-400 hover:text-white transition">Driver view →</a>
        </div>

        {/* Playback controls + theme toggle */}
        <div className="flex items-center gap-2">
          <ThemeToggle />
          <button onClick={step} className="px-3 py-1.5 text-xs rounded-lg bg-gray-700 hover:bg-gray-600 transition">⏭ Step</button>
          {state.status === 'paused'
            ? <button onClick={play} className="px-3 py-1.5 text-xs rounded-lg bg-green-600 hover:bg-green-500 transition">▶ Play</button>
            : <button onClick={pause} className="px-3 py-1.5 text-xs rounded-lg bg-amber-600 hover:bg-amber-500 transition">⏸ Pause</button>
          }
        </div>
      </header>

      {/* ── Main Grid ─────────────────────────────────────────────────────── */}
      <main className="flex-1 grid grid-cols-1 xl:grid-cols-[1fr_360px] gap-0 overflow-hidden" style={{ height: 'calc(100vh - 57px)' }}>

        {/* Left: Map */}
        <div className="relative h-full min-h-[400px] p-3">
          {error && (
            <div className="absolute top-4 left-1/2 -translate-x-1/2 z-50 bg-red-900/80 border border-red-500/40 text-red-300 text-xs px-4 py-2 rounded-lg">
              API Error: {error} — showing cached data
            </div>
          )}
          {loading && (
            <div className="absolute inset-0 flex items-center justify-center z-50 bg-gray-950/50">
              <div className="w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
            </div>
          )}
          <FluxionMap state={filteredState} currentCity={selectedCities.join(',')} />
        </div>

        {/* Right panel */}
        <aside className="border-l border-white/10 overflow-y-auto bg-gray-900/60 backdrop-blur">
          <div className="p-4 space-y-4">

            {/* Fleet status strip */}
            <div className="grid grid-cols-3 gap-2 text-center">
              {[
                { label: 'Trucks', value: filteredState.camions.length, color: 'text-blue-400' },
                { label: 'Zones', value: filteredState.zones.length, color: 'text-emerald-400' },
                { label: 'Events', value: state.recent_events.length, color: 'text-amber-400' },
              ].map(({ label, value, color }) => (
                <div key={label} className="bg-gray-800/60 rounded-xl py-2 px-1">
                  <div className={`text-xl font-bold ${color}`}>{value}</div>
                  <div className="text-xs text-gray-400">{label}</div>
                </div>
              ))}
            </div>

            {/* Savings / Analytics */}
            <SavingsWidget savings={savings} history={history} />

            {/* Controls */}
            <WeightSliders />
            <IncidentSimulator />

            {/* Recent events log */}
            {state.recent_events.length > 0 && (
              <div className="bg-gray-800/60 border border-white/10 rounded-xl p-4">
                <p className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">System Events</p>
                <div className="space-y-1.5 max-h-40 overflow-y-auto">
                  {state.recent_events.slice().reverse().map((e, i) => (
                    <div key={i} className="text-xs text-gray-300 flex gap-2">
                      <span className="text-gray-500 shrink-0">›</span>
                      <span>{typeof e === 'string' ? e : JSON.stringify(e)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </aside>
      </main>
    </div>
  );
}
