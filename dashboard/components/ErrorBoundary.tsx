'use client';
import React from 'react';

interface ErrorBoundaryProps {
    children: React.ReactNode;
    fallback?: React.ReactNode;
    label?: string; // for identifying which boundary caught
}

interface ErrorBoundaryState {
    hasError: boolean;
    error: Error | null;
}

export class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
    constructor(props: ErrorBoundaryProps) {
        super(props);
        this.state = { hasError: false, error: null };
    }

    static getDerivedStateFromError(error: Error): ErrorBoundaryState {
        return { hasError: true, error };
    }

    componentDidCatch(error: Error, info: React.ErrorInfo) {
        console.error(`[ErrorBoundary:${this.props.label ?? 'root'}]`, error, info);
    }

    handleReload = () => {
        window.location.reload();
    };

    handleReset = () => {
        this.setState({ hasError: false, error: null });
    };

    render() {
        if (this.state.hasError) {
            if (this.props.fallback) return this.props.fallback;

            return (
                <div className="flex items-center justify-center w-full h-full min-h-[200px] p-6">
                    <div className="bg-gray-900/80 border border-red-500/30 rounded-2xl p-6 max-w-md w-full backdrop-blur">
                        {/* Icon */}
                        <div className="flex items-center gap-3 mb-4">
                            <div className="w-10 h-10 rounded-full bg-red-500/20 flex items-center justify-center text-red-400 text-xl">
                                ⚠
                            </div>
                            <div>
                                <h3 className="text-sm font-bold text-red-400">Component Error</h3>
                                <p className="text-xs text-gray-500">{this.props.label ?? 'An unexpected error occurred'}</p>
                            </div>
                        </div>

                        {/* Error message */}
                        {this.state.error && (
                            <div className="bg-gray-950/60 border border-white/5 rounded-lg p-3 mb-4 font-mono text-xs text-red-300 break-all">
                                {this.state.error.message}
                            </div>
                        )}

                        {/* Actions */}
                        <div className="flex gap-2">
                            <button
                                onClick={this.handleReset}
                                className="flex-1 py-2 text-xs rounded-lg bg-gray-700 hover:bg-gray-600 text-white transition font-medium"
                            >
                                Try Again
                            </button>
                            <button
                                onClick={this.handleReload}
                                className="flex-1 py-2 text-xs rounded-lg bg-red-600/80 hover:bg-red-500 text-white transition font-medium"
                            >
                                Reload Page
                            </button>
                        </div>
                    </div>
                </div>
            );
        }

        return this.props.children;
    }
}

export default ErrorBoundary;
