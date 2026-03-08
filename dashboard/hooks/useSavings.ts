'use client';
import { useState, useEffect } from 'react';
import { api } from '@/lib/api';
import type { SavingsMetrics } from '@/types/fluxion';

const ZERO: SavingsMetrics = { money_saved: 0, fuel_saved_l: 0, co2_reduced_kg: 0, distance_saved_km: 0 };

export function useSavings(pollMs = 5000) {
    const [savings, setSavings] = useState<SavingsMetrics>(ZERO);
    const [history, setHistory] = useState<SavingsMetrics[]>([ZERO]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        let isMounted = true;
        const doFetch = async () => {
            const data = await api.getSavings();
            if (isMounted) {
                setSavings(data);
                setHistory(prev => [...prev.slice(-59), data]);
                setLoading(false);
            }
        };

        doFetch();
        const id = setInterval(doFetch, pollMs);
        return () => {
            isMounted = false;
            clearInterval(id);
        };
    }, [pollMs]);

    return { savings, history, loading };
}
