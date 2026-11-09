import type { Metadata } from "next";

import { DrawHeader } from "../../components/SiteHeader";
import { Studio } from "../../components/Studio";
import { at } from "../../lib/motion";

export const metadata: Metadata = { title: "Draw · Doodleverse" };

export default function DrawPage() {
  return (
    <div id="sheet" className="sheet graph-paper">
      <DrawHeader />
      <main className="mx-auto max-w-6xl px-3 pb-14 pt-7 sm:px-6">
        <div className="mb-6 flex flex-wrap items-end justify-between gap-x-6 gap-y-1 px-1">
          <h1 className="ink-write font-display text-4xl font-extrabold tracking-tight sm:text-5xl" style={at(0.15, 0.6)}>
            Your sketchbook
          </h1>
          <p className="fade font-hand text-2xl text-graphite" style={at(0.6)}>
            draw one thing, then ask the model
          </p>
        </div>
        <Studio />
      </main>
    </div>
  );
}
