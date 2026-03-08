'use client';
import { createContext, useContext, useEffect, useState, useCallback } from 'react';

type Theme = 'dark' | 'light';

interface ThemeContextValue {
    theme: Theme;
    toggle: () => void;
}

const ThemeContext = createContext<ThemeContextValue>({ theme: 'dark', toggle: () => { } });

export function ThemeProvider({ children }: { children: React.ReactNode }) {
    const [theme, setTheme] = useState<Theme>('dark');

    // Apply class on mount from localStorage
    useEffect(() => {
        const stored = (localStorage.getItem('fluxion-theme') as Theme) ?? 'dark';
        setTheme(stored);
        document.documentElement.setAttribute('data-theme', stored);
    }, []);

    const toggle = useCallback(() => {
        setTheme(prev => {
            const next: Theme = prev === 'dark' ? 'light' : 'dark';
            localStorage.setItem('fluxion-theme', next);
            document.documentElement.setAttribute('data-theme', next);
            return next;
        });
    }, []);

    return (
        <ThemeContext.Provider value={{ theme, toggle }}>
            {children}
        </ThemeContext.Provider>
    );
}

export const useTheme = () => useContext(ThemeContext);
