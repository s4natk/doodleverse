"use client";

import { useEffect, useState } from "react";

import { LABELS } from "../lib/contract";
import { apiBaseUrl, isMocked } from "../lib/inference";
import { fetchModelInfo, type ModelInfo } from "../lib/modelInfo";
import { SectionLabel } from "./HowItWorks";
import { ArrowUpRightIcon } from "./icons";
import { REPO } from "./SiteHeader";

const STACK = [
  "Next.js",
  "React",
  "Tailwind",
  "PixiJS",
  "Matter.js",
  "FastAPI",
  "TensorFlow",
  "Docker",
  "AWS ECS",
  "S3",
  "Vercel",
  "GitHub Actions",
];

const READING = [
  { label: "Model card", href: `${REPO}/blob/main/docs/model-card.md` },
  { label: "Benchmarks", href: `${REPO}/blob/main/docs/benchmark-results.md` },
  { label: "Experiments", href: `${REPO}/blob/main/docs/experiments.md` },
  { label: "Source", href: REPO },
];

const CARD = "rounded-3xl border border-line bg-white/80 p-6 text-left shadow-[0_1px_0_rgba(0,0,0,0.03)] sm:p-7";

type Status = "loading" | "live" | "unreachable" | "mocked";

function Big({ children }: { children: React.ReactNode }) {
  return <p className="font-display text-5xl font-bold tracking-tight text-ink sm:text-6xl">{children}</p>;
}

export function UnderTheHood() {
  const [info, setInfo] = useState<ModelInfo | null>(null);
  const [status, setStatus] = useState<Status>(() => (isMocked() ? "mocked" : "loading"));

  useEffect(() => {
    if (isMocked()) {
      return;
    }
    const controller = new AbortController();
    fetchModelInfo(apiBaseUrl(), controller.signal).then((answer) => {
      if (!controller.signal.aborted) {
        setInfo(answer);
        setStatus(answer ? "live" : "unreachable");
      }
    });
    return () => controller.abort();
  }, []);

  const blank = status === "loading" ? "…" : "—";
  const show = (value: number | null | undefined, format: (value: number) => string) =>
    value == null ? blank : format(value);
  const percent = (value: number) => `${(value * 100).toFixed(1)}%`;
  const note = {
    loading: "Asking the model about itself…",
    live: `Read live from ${info?.version}, the model answering this page.`,
    unreachable: "The model's API is out of reach from here, so the live numbers are blank. The model card has them.",
    mocked: "This page is running with the mock recognizer, so there is no model to ask. The model card has the numbers.",
  }[status];

  return (
    <section id="model" className="mx-auto max-w-6xl px-4 pb-24 text-center sm:px-6">
      <SectionLabel>Under the hood</SectionLabel>
      <h2 className="mt-4 font-display text-4xl font-bold tracking-tight sm:text-5xl">Small model, honest numbers</h2>
      <p className="mx-auto mt-4 max-w-2xl text-muted">{note}</p>
      <div className="mt-12 grid gap-4 md:grid-cols-3">
        <div className={`${CARD} md:col-span-2`}>
          <p className="text-sm font-medium text-muted">Test accuracy</p>
          <Big>{show(info?.testAccuracy, percent)}</Big>
          <p className="mt-3 max-w-lg text-sm leading-relaxed text-muted">
            On {show(info?.testCount, (count) => count.toLocaleString())} drawings it never saw while learning,{" "}
            {show(info?.testCount, (count) => (count / LABELS.length).toLocaleString())} of each class, scored once
            after the model, its rasterizer, and its thresholds were frozen. Macro-F1{" "}
            {show(info?.testMacroF1, (value) => value.toFixed(3))}.
          </p>
        </div>
        <div className={CARD}>
          <p className="text-sm font-medium text-muted">Knows when to ask</p>
          <Big>{show(info?.gateCoverage, percent)}</Big>
          <p className="mt-3 text-sm leading-relaxed text-muted">
            of drawings answered on its own, and right {show(info?.gateAcceptedAccuracy, percent)} of the time when it
            does. Close calls come back to you as a choice.
          </p>
        </div>
        <div className={CARD}>
          <p className="text-sm font-medium text-muted">Tiny on purpose</p>
          <Big>{show(info?.fileBytes, (bytes) => `${Math.round(bytes / 1024)} KB`)}</Big>
          <p className="mt-3 text-sm leading-relaxed text-muted">
            {show(info?.parameters, (count) => count.toLocaleString())} parameters. A prediction takes a few
            milliseconds on a CPU, so most of the wait is the network.
          </p>
        </div>
        <div className={CARD}>
          <p className="text-sm font-medium text-muted">Your drawing stays yours</p>
          <p className="mt-2 font-display text-2xl font-semibold leading-snug">Classified, then forgotten.</p>
          <p className="mt-3 text-sm leading-relaxed text-muted">
            The service keeps nothing it is sent. Its logs carry the label and timing, never the strokes.
          </p>
        </div>
        <div className={CARD}>
          <p className="text-sm font-medium text-muted">Read the details</p>
          <ul className="mt-3 flex flex-col gap-1">
            {READING.map((link) => (
              <li key={link.label}>
                <a
                  href={link.href}
                  className="group inline-flex items-center gap-1.5 font-display text-lg font-medium transition hover:text-coral"
                >
                  {link.label}
                  <ArrowUpRightIcon className="text-muted transition group-hover:text-coral" width={16} height={16} />
                </a>
              </li>
            ))}
          </ul>
        </div>
        <div className={`${CARD} md:col-span-3`}>
          <p className="text-sm font-medium text-muted">The whole stack</p>
          <ul className="mt-4 flex flex-wrap gap-2">
            {STACK.map((name) => (
              <li key={name} className="rounded-full border border-line bg-paper px-3 py-1.5 text-sm">
                {name}
              </li>
            ))}
          </ul>
          <p className="mt-4 max-w-3xl text-sm leading-relaxed text-muted">
            The browser runs the world and sends strokes, never pixels. Python owns the rasterizer, so the model sees
            a drawing the way it was trained to. The API runs in a container on AWS and reads its model from S3. This
            page is on Vercel.
          </p>
        </div>
      </div>
    </section>
  );
}
