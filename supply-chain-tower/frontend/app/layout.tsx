import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
    title: 'Supply Chain Control Tower — Kalady, Kerala',
    description: 'Autonomous real-time logistics simulation with AI-driven rerouting',
};

export default function RootLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <html lang="en">
            <body>{children}</body>
        </html>
    );
}
