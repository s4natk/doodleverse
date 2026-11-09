import type { Metadata, Viewport } from "next";
import { Bricolage_Grotesque, Caveat, Geist } from "next/font/google";

import "./globals.css";

const bricolage = Bricolage_Grotesque({ subsets: ["latin"], variable: "--font-bricolage", display: "swap" });
const caveat = Caveat({ subsets: ["latin"], variable: "--font-caveat", display: "swap" });
const geist = Geist({ subsets: ["latin"], variable: "--font-geist", display: "swap" });

const DESCRIPTION =
  "Sketch a sun, a cloud, a tree, a flower, a car, or a cat. A neural network names it, and it comes alive in a small animated world.";

// Runs before paint, so a visitor who asked for reduced motion never sees anything start hidden.
const MOTION = "if(!matchMedia('(prefers-reduced-motion: reduce)').matches)document.documentElement.classList.add('motion-ok')";

export const metadata: Metadata = {
  title: "Doodleverse · Draw it. Bring it to life.",
  description: DESCRIPTION,
  openGraph: { title: "Doodleverse", description: DESCRIPTION, type: "website" },
};

export const viewport: Viewport = { themeColor: "#f4f4ee" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${bricolage.variable} ${caveat.variable} ${geist.variable}`} suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: MOTION }} />
      </head>
      <body className="graph-paper min-h-dvh overflow-x-hidden font-sans text-ink antialiased">{children}</body>
    </html>
  );
}
