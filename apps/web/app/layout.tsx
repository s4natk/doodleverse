import type { Metadata, Viewport } from "next";
import { Inter, Outfit } from "next/font/google";

import "./globals.css";

const outfit = Outfit({ subsets: ["latin"], variable: "--font-outfit", display: "swap" });
const inter = Inter({ subsets: ["latin"], variable: "--font-inter", display: "swap" });

const DESCRIPTION =
  "Sketch a sun, a cloud, a tree, a flower, a car, or a cat. A neural network names it, and it comes alive in a small animated world.";

export const metadata: Metadata = {
  title: "Doodleverse · Draw it. Bring it to life.",
  description: DESCRIPTION,
  openGraph: { title: "Doodleverse", description: DESCRIPTION, type: "website" },
};

export const viewport: Viewport = { themeColor: "#fffaf3" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${outfit.variable} ${inter.variable}`}>
      <body className="min-h-dvh font-sans text-ink antialiased">
        <div className="page-backdrop" aria-hidden />
        {children}
      </body>
    </html>
  );
}
