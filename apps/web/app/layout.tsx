import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Doodleverse",
  description: "Draw it. Bring it to life.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
