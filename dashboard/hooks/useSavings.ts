'use client';
import { useState, useEffect, useCallback } from 'react';
import { api } from '@/lib/api';
import type { SavingsMetrics } from '@/types/fluxion';

const ZERO: SavingsMetrics = { money_saved: 0, fuel_saved_l: 0, co2_reduced_kg: 0, distance_saved_km: 0 };

export function useSavings(pollMs = 5000) {
    const [savings, setSavings] = useState<SavingsMetrics>(ZERO);
    const [history, setHistory] = useState<SavingsMetrics[]>([ZERO]);
    const [loading, setLoading] = useState(true);

    const fetch = useCallback(async () => {
        const data = await api.getSavings();
        setSavings(data);
        setHistory(prev => [...prev.slice(-59), data]); // rolling 60-point window
        setLoading(false);
    }, []);

    useEffect(() => {
        fetch();
        const id = setInterval(fetch, pollMs);
        return () => clearInterval(id);
    }, [fetch, pollMs]);

    return { savings, history, loading };
}
