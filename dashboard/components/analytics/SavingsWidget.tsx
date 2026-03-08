'use client';
import {
    Chart as ChartJS,
    CategoryScale, LinearScale, BarElement,
    LineElement, PointElement,
    Title, Tooltip, Legend, Filler,
} from 'chart.js';
import { Bar, Line } from 'react-chartjs-2';
import type { SavingsMetrics } from '@/types/fluxion';

ChartJS.register(CategoryScale, LinearScale, BarElement, LineElement, PointElement, Title, Tooltip, Legend, Filler);

interface Props {
    savings: SavingsMetrics;
    history: SavingsMetrics[];
}

const lineOpts = {
    responsive: true, maintainAspectRatio: false,
    plugins: { legend: { display: false }, tooltip: { enabled: false } },
    scales: { x: { display: false }, y: { display: false } },
    animation: { duration: 300 },
};

function Sparkline({ values, color }: { values: number[]; color: string }) {
    if (!values.length) return <div className="h-10 w-full" />;
    return (
        <div className="h-10">
            <Line
                data={{
                    labels: values.map((_, i) => i),
                    datasets: [{ data: values, borderColor: color, backgroundColor: color + '20', borderWidth: 2, pointRadius: 0, fill: true, tension: 0.4 }],
                }}
                options={lineOpts}
            />
        </div>
    );
}

function KPICard({
    title, value, unit, color, icon, history, positive = true,
}: {
    title: string; value: number; unit: string; color: string;
    icon: string; history: number[]; positive?: boolean;
}) {
    const isPositive = positive ? value > 0 : false;
    return (
        <div className={`bg-gray-800/60 backdrop-blur border rounded-xl p-3 flex flex-col gap-1.5 transition
            ${isPositive ? 'border-white/10' : 'border-white/5'}`}>
            <div className="flex items-center justify-between">
                <span className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider leading-tight">{title}</span>
                <span className="text-sm">{icon}</span>
            </div>
            <div className="flex items-end gap-1">
                <span className={`text-xl font-bold ${positive && value > 0 ? 'text-white' : 'text-gray-300'}`}>
                    {value.toFixed(1)}
                </span>
                <span className="text-[10px] text-gray-400 mb-0.5">{unit}</span>
            </div>
            <Sparkline values={history} color={color} />
        </div>
    );
}

export default function SavingsWidget({ savings, history }: Props) {
    const get = (key: keyof SavingsMetrics) => history.map(h => (h[key] as number) ?? 0);

    const elapsedMin = savings.time_elapsed_min ?? 0;
    const hours = Math.floor(elapsedMin / 60);
    const mins = elapsedMin % 60;
    const timeStr = elapsedMin > 0
        ? (hours > 0 ? `${hours}h ${mins}m` : `${mins}m`)
        : '—';

    const barData = {
        labels: ['Saved (€)', 'Fuel Saved (L)', 'CO₂ (kg)', 'Distance (km)'],
        datasets: [{
            label: 'Optimization savings',
            data: [savings.money_saved, savings.fuel_saved_l, savings.co2_reduced_kg, savings.distance_saved_km],
            backgroundColor: ['#10b981cc', '#3b82f6cc', '#8b5cf6cc', '#f59e0bcc'],
            borderColor: ['#10b981', '#3b82f6', '#8b5cf6', '#f59e0b'],
            borderWidth: 1, borderRadius: 6,
        }],
    };

    const barOpts = {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false }, tooltip: { callbacks: { label: (ctx: { raw: unknown }) => ` ${ctx.raw}` } } },
        scales: {
            x: { ticks: { color: '#9ca3af', font: { size: 10 } }, grid: { display: false } },
            y: { ticks: { color: '#9ca3af', font: { size: 10 } }, grid: { color: '#374151' } },
        },
        animation: { duration: 600 },
    };

    return (
        <div className="space-y-3">
            {/* Header */}
            <div className="flex items-center justify-between">
                <p className="text-xs font-bold text-gray-400 uppercase tracking-wider">Fleet Analytics</p>
                {elapsedMin > 0 && (
                    <span className="text-xs text-gray-500 font-mono">⏱ {timeStr} elapsed</span>
                )}
            </div>

            {/* Savings KPIs */}
            <div className="grid grid-cols-3 gap-2">
                <KPICard title="Money Saved" value={savings.money_saved} unit="€" color="#10b981" icon="💰" history={get('money_saved')} />
                <KPICard title="Fuel Saved" value={savings.fuel_saved_l} unit="L" color="#3b82f6" icon="💧" history={get('fuel_saved_l')} />
                <KPICard title="CO₂ Cut" value={savings.co2_reduced_kg} unit="kg" color="#8b5cf6" icon="🌿" history={get('co2_reduced_kg')} />
            </div>

            {/* Cost KPIs */}
            <div className="grid grid-cols-2 gap-2">
                <KPICard title="Fuel Consumed" value={savings.fuel_consumed_l ?? 0} unit="L" color="#ef4444" icon="⛽" history={get('fuel_consumed_l')} positive={false} />
                <KPICard title="Fleet Cost" value={savings.money_consumed ?? 0} unit="€" color="#f97316" icon="💸" history={get('money_consumed')} positive={false} />
            </div>

            {/* Historical bar */}
            <div className="bg-gray-800/60 backdrop-blur border border-white/10 rounded-xl p-3">
                <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-2">Savings vs Naive Routing</p>
                <div className="h-32">
                    <Bar data={barData} options={barOpts} />
                </div>
            </div>

            {/* Distance comparison */}
            {savings.distance_saved_km > 0 && (
                <div className="bg-gray-800/60 border border-white/10 rounded-xl p-3 flex items-center gap-3">
                    <span className="text-2xl">🛣️</span>
                    <div>
                        <p className="text-xs text-gray-400">Distance Saved vs Naive Route</p>
                        <p className="text-lg font-bold text-emerald-400">{savings.distance_saved_km.toFixed(1)} km</p>
                    </div>
                </div>
            )}
        </div>
    );
}
