'use client';
import { useTheme } from '@/context/ThemeContext';

export default function ThemeToggle() {
    const { theme, toggle } = useTheme();
    const isDark = theme === 'dark';

    return (
        <button
            onClick={toggle}
            title={`Switch to ${isDark ? 'light' : 'dark'} mode`}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-white/10 bg-gray-800/60 hover:bg-gray-700/60 text-gray-300 hover:text-white text-xs font-medium transition-all duration-200 select-none"
        >
            <span className="text-sm">{isDark ? '☀️' : '🌙'}</span>
            <span className="hidden sm:inline">{isDark ? 'Light' : 'Dark'}</span>
        </button>
    );
}
