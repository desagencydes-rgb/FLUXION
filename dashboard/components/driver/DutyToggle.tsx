'use client';
import { useState, useEffect } from 'react';
import { api } from '@/lib/api';

interface Props {
    camionId?: number;
    onDutyStart?: () => void;
    onDutyEnd?: () => void;
}

export default function DutyToggle({ camionId = 1, onDutyStart, onDutyEnd }: Props) {
    const [onDuty, setOnDuty] = useState(false);
    const [loading, setLoading] = useState(true);
    const [since, setSince] = useState<string | null>(null);
    const [error, setError] = useState<string | null>(null);

    // ── Load persisted duty state on mount / truck change ────────────────────
    useEffect(() => {
        let cancelled = false;
        setLoading(true);
        setError(null);
        api.getDutyStatus(camionId)
            .then(data => {
                if (cancelled) return;
                setOnDuty(data.on_duty);
                if (data.on_duty) setSince(data.since ?? new Date().toLocaleTimeString());
                else setSince(null);
            })
            .catch(() => {
                // Silently fall back to local state if endpoint unavailable
                setOnDuty(false);
            })
            .finally(() => { if (!cancelled) setLoading(false); });
        return () => { cancelled = true; };
    }, [camionId]);

    // ── Toggle duty ──────────────────────────────────────────────────────────
    async function toggle() {
        setLoading(true);
        setError(null);
        try {
            const newDuty = !onDuty;
            await api.setDuty(camionId, newDuty);
            setOnDuty(newDuty);
            if (newDuty) {
                setSince(new Date().toLocaleTimeString());
                onDutyStart?.();
            } else {
                setSince(null);
                onDutyEnd?.();
            }
        } catch (e) {
            setError(e instanceof Error ? e.message : 'Failed to update duty status');
        } finally {
            setLoading(false);
        }
    }

    return (
        <div className="flex flex-col items-center gap-4 w-full">
            {/* Big toggle button */}
            <button
                onClick={toggle}
                disabled={loading}
                aria-label={onDuty ? 'End duty shift' : 'Start duty shift'}
                className={`w-36 h-36 rounded-full flex flex-col items-center justify-center
          text-white font-bold text-lg shadow-2xl transition-all duration-300
          active:scale-95 disabled:opacity-50 select-none
          ${onDuty
                        ? 'bg-gradient-to-br from-green-500 to-emerald-600 shadow-green-500/40'
                        : 'bg-gradient-to-br from-gray-600 to-gray-700 shadow-gray-900/60 hover:from-gray-500 hover:to-gray-600'
                    }`}
            >
                {loading ? (
                    <div className="w-8 h-8 border-3 border-white border-t-transparent rounded-full animate-spin" />
                ) : (
                    <>
                        <span className="text-3xl mb-1">{onDuty ? '🟢' : '⭕'}</span>
                        <span className="text-base font-black uppercase tracking-wide leading-tight text-center">
                            {onDuty ? 'ON DUTY' : 'START\nDUTY'}
                        </span>
                    </>
                )}
            </button>

            {/* Status text */}
            {!loading && onDuty && since && (
                <p className="text-sm text-green-400 font-medium text-center">
                    On duty since <span className="font-mono text-green-300">{since}</span>
                </p>
            )}
            {!loading && !onDuty && (
                <p className="text-sm text-gray-500 text-center">Truck {camionId} — Off Duty</p>
            )}

            {/* Error */}
            {error && (
                <p className="text-xs text-red-400 bg-red-500/10 border border-red-500/30 rounded-lg px-3 py-2 text-center">
                    {error}
                </p>
            )}
        </div>
    );
}
