import type { Metadata } from "next";
import "./globals.css";
import "leaflet/dist/leaflet.css";
import ErrorBoundary from "@/components/ErrorBoundary";
import { ThemeProvider } from "@/context/ThemeContext";

export const metadata: Metadata = {
  title: {
    default: "FLUXION — Intelligent Fleet Management",
    template: "%s | FLUXION",
  },
  description:
    "Real-time waste collection optimization dashboard with live GPS tracking, route optimization, and ROI analytics.",
  keywords: ["waste management", "fleet management", "route optimization", "smart city"],
  authors: [{ name: "FLUXION" }],
  openGraph: {
    title: "FLUXION — Intelligent Fleet Management",
    description:
      "Real-time waste collection optimization dashboard with live GPS tracking, route optimization, and ROI analytics.",
    type: "website",
    locale: "en_US",
    siteName: "FLUXION",
  },
  twitter: {
    card: "summary_large_image",
    title: "FLUXION — Intelligent Fleet Management",
    description: "Real-time waste collection optimization with live GPS tracking and ROI analytics.",
  },
  icons: {
    icon: "/favicon.ico",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="antialiased">
        <ThemeProvider>
          <ErrorBoundary label="Root Layout">
            {children}
          </ErrorBoundary>
        </ThemeProvider>
      </body>
    </html>
  );
}
