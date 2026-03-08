'use client';
import { useState } from 'react';
import { api } from '@/lib/api';

interface IncidentPreset {
    id: string;
    label: string;
    icon: string;
    type: string;
    details: Record<string, unknown>;
    color: string;
}

const PRESETS: IncidentPreset[] = [
    {
        id: 'breakdown',
        label: 'Truck Breakdown',
        icon: '🔧',
        type: 'panne_camion',
        details: { camion_id: 1, duree_minutes: 60 },
        color: 'border-red-500/50 hover:bg-red-500/10',
    },
    {
        id: 'traffic',
        label: 'Traffic Surge',
        icon: '🚦',
        type: 'trafic_intense',
        details: { zones: [1, 3, 5], vitesse_reduite: 0.5 },
        color: 'border-amber-500/50 hover:bg-amber-500/10',
    },
    {
        id: 'special',
        label: 'Special Collection',
        icon: '📦',
        type: 'demande_speciale',
        details: { type: 'encombrants', quantite_kg: 500 },
        color: 'border-blue-500/50 hover:bg-blue-500/10',
    },
    {
        id: 'urgent_replan',
        label: 'Emergency Replan',
        icon: '🚨',
        type: 'replanification_urgence',
        details: { points_urgents: [7, 12, 25] },
        color: 'border-violet-500/50 hover:bg-violet-600/10',
    },
];

interface EventLog {
    time: string;
    label: string;
    icon: string;
}

export default function IncidentSimulator() {
    const [firing, setFiring] = useState<string | null>(null);
    const [log, setLog] = useState<EventLog[]>([]);

    async function fire(preset: IncidentPreset) {
        setFiring(preset.id);
        try {
            await api.triggerIncident(preset.type, preset.details);
            setLog(prev => [{
                time: new Date().toLocaleTimeString(),
                label: preset.label,
                icon: preset.icon,
            }, ...prev.slice(0, 9)]);
        } catch {
            // API may not have this endpoint yet — still log client-side
            setLog(prev => [{
                time: new Date().toLocaleTimeString(),
                label: `${preset.label} (simulated)`,
                icon: preset.icon,
            }, ...prev.slice(0, 9)]);
        } finally {
            setTimeout(() => setFiring(null), 1200);
        }
    }

    return (
        <div className="bg-gray-800/60 backdrop-blur border border-white/10 rounded-xl p-4 space-y-4">
            <div className="flex items-center justify-between">
                <h3 className="text-sm font-bold text-white">Incident Simulator</h3>
                <span className="text-xs text-gray-400">Fleet Manager only</span>
            </div>

            <div className="grid grid-cols-2 gap-2">
                {PRESETS.map(preset => (
                    <button
                        key={preset.id}
                        onClick={() => fire(preset)}
                        disabled={firing !== null}
                        className={`flex flex-col items-center gap-1 p-3 rounded-lg border text-xs
                        font-semibold text-white transition disabled:opacity-40 cursor-pointer
                        ${preset.color}`}
                    >
                        <span className="text-xl">{preset.icon}</span>
                        <span>{preset.label}</span>
                        {firing === preset.id && (
                            <span className="text-[10px] text-gray-400 animate-pulse">Triggering…</span>
                        )}
                    </button>
                ))}
            </div>

            {/* Event log */}
            {log.length > 0 && (
                <div className="space-y-1">
                    <p className="text-xs text-gray-500 uppercase tracking-wide">Recent Events</p>
                    {log.map((e, i) => (
                        <div key={i} className="flex items-center gap-2 text-xs text-gray-300">
                            <span className="text-gray-500 font-mono w-16 shrink-0">{e.time}</span>
                            <span>{e.icon}</span>
                            <span>{e.label}</span>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
