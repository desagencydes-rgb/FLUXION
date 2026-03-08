'use client';
import { useState } from 'react';
import { api } from '@/lib/api';
import type { NSGAWeights } from '@/types/fluxion';

interface Props {
    onWeightsChange?: (w: NSGAWeights) => void;
}

const DEFAULTS: NSGAWeights = { distance: 0.3, co2: 0.3, satisfaction: 0.2, equite: 0.2 };

function normalize(w: NSGAWeights): NSGAWeights {
    const total = w.distance + w.co2 + w.satisfaction + w.equite;
    if (total === 0) return DEFAULTS;
    return {
        distance: +(w.distance / total).toFixed(3),
        co2: +(w.co2 / total).toFixed(3),
        satisfaction: +(w.satisfaction / total).toFixed(3),
        equite: +(w.equite / total).toFixed(3),
    };
}

const SLIDERS: { key: keyof NSGAWeights; label: string; icon: string; color: string }[] = [
    { key: 'distance', label: 'Distance', icon: '📍', color: '#3b82f6' },
    { key: 'co2', label: 'CO₂', icon: '🌿', color: '#10b981' },
    { key: 'satisfaction', label: 'Satisfaction', icon: '😊', color: '#f59e0b' },
    { key: 'equite', label: 'Equity', icon: '⚖️', color: '#8b5cf6' },
];

export default function WeightSliders({ onWeightsChange }: Props) {
    const [weights, setWeights] = useState<NSGAWeights>(DEFAULTS);
    const [saving, setSaving] = useState(false);
    const [saved, setSaved] = useState(false);

    function update(key: keyof NSGAWeights, val: number) {
        setWeights(prev => ({ ...prev, [key]: val }));
        setSaved(false);
    }

    async function apply() {
        setSaving(true);
        try {
            const norm = normalize(weights);
            await api.setWeights(norm);
            setWeights(norm);
            onWeightsChange?.(norm);
            setSaved(true);
            setTimeout(() => setSaved(false), 2000);
        } catch {
            // silently fail if API not ready
        } finally {
            setSaving(false);
        }
    }

    const total = Object.values(weights).reduce((a, b) => a + b, 0);
    const isValid = Math.abs(total - 1.0) < 0.05 || true; // auto-normalise on apply

    return (
        <div className="bg-gray-800/60 backdrop-blur border border-white/10 rounded-xl p-4 space-y-4">
            <div className="flex items-center justify-between">
                <h3 className="text-sm font-bold text-white">NSGA-II Weights</h3>
                <span className="text-xs text-gray-400">Pareto optimisation</span>
            </div>

            {SLIDERS.map(({ key, label, icon, color }) => (
                <div key={key} className="space-y-1">
                    <div className="flex justify-between text-xs">
                        <span className="text-gray-300">{icon} {label}</span>
                        <span className="font-mono text-white">{(weights[key] * 100).toFixed(0)}%</span>
                    </div>
                    <div className="relative">
                        <input
                            type="range"
                            min={0}
                            max={100}
                            step={5}
                            value={Math.round(weights[key] * 100)}
                            onChange={e => update(key, +e.target.value / 100)}
                            className="w-full h-2 rounded appearance-none cursor-pointer accent-blue-500"
                            style={{ accentColor: color }}
                        />
                        {/* Mini progress bar */}
                        <div
                            className="absolute top-0 left-0 h-2 rounded pointer-events-none"
                            style={{ width: `${weights[key] * 100}%`, background: color + '40' }}
                        />
                    </div>
                </div>
            ))}

            {/* Sum indicator */}
            <div className="text-xs text-gray-400 flex items-center gap-1">
                <span>Sum: {(total * 100).toFixed(0)}%</span>
                <span className="text-gray-500">(auto-normalised on apply)</span>
            </div>

            <button
                onClick={apply}
                disabled={saving || !isValid}
                className="w-full py-2 rounded-lg text-sm font-semibold transition
                   bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white"
            >
                {saving ? 'Applying…' : saved ? '✓ Applied' : 'Apply Weights'}
            </button>
        </div>
    );
}
