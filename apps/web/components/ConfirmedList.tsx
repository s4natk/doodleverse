import type { Placement } from "../lib/studio";

export function ConfirmedList({ placed }: { placed: Placement[] }) {
  return (
    <section className="rounded-2xl bg-white/30 p-5">
      <h2 className="text-xs uppercase tracking-[0.18em] text-[#9a6b58]">Confirmed</h2>
      {placed.length === 0 ? (
        <p className="mt-2 text-sm text-black/50">Nothing yet.</p>
      ) : (
        <ul className="mt-2 flex flex-wrap gap-1.5">
          {placed.map((item) => (
            <li key={item.id} className="rounded-full bg-white/80 px-3 py-1 text-sm capitalize">
              {item.label}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
