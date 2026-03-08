'use client';
import { useState, FormEvent } from 'react';
import { api, saveToken } from '@/lib/api';
import { useRouter } from 'next/navigation';

export default function LoginPage() {
    const router = useRouter();
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleSubmit = async (e: FormEvent) => {
        e.preventDefault();
        if (!email || !password) return setError('Please fill in all fields');
        setLoading(true);
        setError(null);

        try {
            const res = await api.login(email, password);
            saveToken(res.access_token);
            // Redirect based on role
            if (res.role === 'driver') {
                router.push('/driver');
            } else {
                router.push('/');
            }
        } catch (e) {
            setError(e instanceof Error && e.message.includes('401')
                ? 'Incorrect email or password'
                : `Login failed: ${e instanceof Error ? e.message : 'Unknown error'}`
            );
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen bg-gray-950 flex items-center justify-center p-4">
            {/* Background glow */}
            <div className="absolute inset-0 overflow-hidden pointer-events-none">
                <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-blue-500/10 rounded-full blur-3xl" />
                <div className="absolute bottom-1/3 left-1/2 -translate-x-1/2 w-64 h-64 bg-emerald-500/8 rounded-full blur-3xl" />
            </div>

            <div className="relative w-full max-w-sm">
                {/* Logo */}
                <div className="text-center mb-8">
                    <h1 className="text-4xl font-black tracking-tight bg-gradient-to-r from-blue-400 to-emerald-400 bg-clip-text text-transparent">
                        FLUXION
                    </h1>
                    <p className="text-sm text-gray-500 mt-1">Fleet Management Console</p>
                </div>

                {/* Card */}
                <div className="bg-gray-900/80 border border-white/10 rounded-2xl p-8 backdrop-blur shadow-2xl">
                    <h2 className="text-base font-bold text-white mb-6">Sign in to your account</h2>

                    {error && (
                        <div className="mb-4 px-4 py-3 bg-red-500/15 border border-red-500/30 rounded-xl text-xs text-red-300">
                            {error}
                        </div>
                    )}

                    <form onSubmit={handleSubmit} className="space-y-4">
                        <div>
                            <label className="block text-xs text-gray-400 mb-1.5 font-medium">
                                Email address
                            </label>
                            <input
                                id="email"
                                type="email"
                                autoComplete="email"
                                required
                                value={email}
                                onChange={e => setEmail(e.target.value)}
                                placeholder="manager@ville.ma"
                                className="w-full bg-gray-800/60 border border-white/10 rounded-xl px-4 py-2.5 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-blue-500/60 focus:ring-1 focus:ring-blue-500/30 transition"
                            />
                        </div>

                        <div>
                            <label className="block text-xs text-gray-400 mb-1.5 font-medium">
                                Password
                            </label>
                            <input
                                id="password"
                                type="password"
                                autoComplete="current-password"
                                required
                                value={password}
                                onChange={e => setPassword(e.target.value)}
                                placeholder="••••••••"
                                className="w-full bg-gray-800/60 border border-white/10 rounded-xl px-4 py-2.5 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-blue-500/60 focus:ring-1 focus:ring-blue-500/30 transition"
                            />
                        </div>

                        <button
                            id="login-submit"
                            type="submit"
                            disabled={loading}
                            className="w-full py-3 mt-2 rounded-xl bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-500 hover:to-blue-400 disabled:opacity-50 disabled:cursor-not-allowed text-sm font-bold text-white transition shadow-lg shadow-blue-500/20"
                        >
                            {loading ? (
                                <span className="flex items-center justify-center gap-2">
                                    <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                                    Signing in…
                                </span>
                            ) : (
                                'Sign in'
                            )}
                        </button>
                    </form>

                    {/* Dev hint */}
                    <p className="mt-6 text-center text-xs text-gray-600">
                        Dev mode: set{' '}
                        <code className="text-gray-500">JWT_SECRET=dev</code>{' '}
                        to bypass auth
                    </p>
                </div>
            </div>
        </div>
    );
}
