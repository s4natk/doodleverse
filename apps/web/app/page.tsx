import { Studio } from "../components/Studio";

export default function HomePage() {
  return (
    <main className="mx-auto flex min-h-dvh max-w-5xl flex-col gap-6 px-6 py-10">
      <header>
        <p className="text-xs uppercase tracking-[0.18em] text-[#9a6b58]">Doodleverse</p>
        <h1 className="mt-2 text-4xl font-semibold">Draw it. Bring it to life.</h1>
        <p className="mt-3 text-lg">Draw one thing: a sun, a cloud, a tree, a flower, a car, or a cat.</p>
      </header>
      <Studio />
    </main>
  );
}
