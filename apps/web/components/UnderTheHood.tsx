"use client";

import { useEffect, useState } from "react";

import { LABELS } from "../lib/contract";
import { apiBaseUrl, isMocked } from "../lib/inference";
import { fetchModelInfo, type ModelInfo } from "../lib/modelInfo";
import { at } from "../lib/motion";
import { SectionHeading } from "./HowItWorks";
import { ArrowUpRightIcon } from "./icons";
import { Reveal } from "./Reveal";
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

type Status = "loading" | "live" | "unreachable" | "mocked";

const LABEL = "font-hand text-2xl leading-none text-graphite";

function Big({ children }: { children: React.ReactNode }) {
  return <p className="mt-2 font-display text-6xl font-extrabold tracking-tight sm:text-7xl">{children}</p>;
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
    live: `Read live from ${info?.version}, the model answering this site.`,
    unreachable: "The model's API is out of reach from here, so the live numbers are blank. The model card has them.",
    mocked: "This page runs with the mock recognizer, so there is no model to ask. The model card has the numbers.",
  }[status];

  return (
    <section id="model" className="mx-auto max-w-6xl px-4 pb-28 sm:px-6">
      <Reveal>
        <SectionHeading note="under the hood" title="The numbers, straight from the model">
          {note}
        </SectionHeading>
      </Reveal>
      <Reveal className="mt-14 grid gap-6 md:grid-cols-3">
        <div className="pop ink-card p-7 md:col-span-2" style={at(0.05)}>
          <p className={LABEL}>test accuracy</p>
          <Big>
            <span className="highlight" style={at(0.6)}>
              {show(info?.testAccuracy, percent)}
            </span>
          </Big>
          <p className="mt-3 max-w-lg text-sm leading-relaxed text-graphite">
            On {show(info?.testCount, (count) => count.toLocaleString())} drawings it never saw while learning,{" "}
            {show(info?.testCount, (count) => (count / LABELS.length).toLocaleString())} of each class, scored once
            after the model, its rasterizer, and its thresholds were frozen. Macro-F1{" "}
            {show(info?.testMacroF1, (value) => value.toFixed(3))}.
          </p>
        </div>
        <div className="pop -rotate-1 rounded-[18px] border-2 border-ink bg-note p-7 shadow-ink" style={at(0.15)}>
          <p className={LABEL}>knows when to ask</p>
          <Big>{show(info?.gateCoverage, percent)}</Big>
          <p className="mt-3 text-sm leading-relaxed text-ink/75">
            of drawings answered on its own, right {show(info?.gateAcceptedAccuracy, percent)} of the time when it does.
            Close calls come back to you as a choice.
          </p>
        </div>
        <div className="pop ink-card p-7" style={at(0.25)}>
          <p className={LABEL}>tiny on purpose</p>
          <Big>{show(info?.fileBytes, (bytes) => `${Math.round(bytes / 1024)} KB`)}</Big>
          <p className="mt-3 text-sm leading-relaxed text-graphite">
            {show(info?.parameters, (count) => count.toLocaleString())} parameters. A prediction takes a few
            milliseconds on a CPU, so most of the wait is the network.
          </p>
        </div>
        <div className="pop rotate-1 rounded-[18px] border-2 border-ink bg-[#ffd0e0] p-7 shadow-ink" style={at(0.35)}>
          <p className={LABEL}>your drawing stays yours</p>
          <p className="mt-3 font-display text-3xl font-extrabold leading-tight tracking-tight">Classified, then forgotten.</p>
          <p className="mt-3 text-sm leading-relaxed text-ink/75">
            The service keeps nothing it is sent. Its logs carry the label and timing, never the strokes.
          </p>
        </div>
        <div className="pop ink-card p-7" style={at(0.45)}>
          <p className={LABEL}>read the details</p>
          <ul className="mt-3 flex flex-col gap-1.5">
            {READING.map((link) => (
              <li key={link.label}>
                <a
                  href={link.href}
                  className="group inline-flex items-center gap-1.5 font-display text-xl font-bold decoration-marker decoration-[3px] underline-offset-4 hover:underline"
                >
                  {link.label}
                  <ArrowUpRightIcon className="text-marker" width={18} height={18} />
                </a>
              </li>
            ))}
          </ul>
        </div>
        <div className="pop ink-card p-7 md:col-span-3" style={at(0.55)}>
          <p className={LABEL}>the whole stack</p>
          <ul className="mt-4 flex flex-wrap gap-2.5">
            {STACK.map((name, index) => (
              <li
                key={name}
                className={`rounded-md border-2 border-ink bg-sheet px-3 py-1 text-sm font-semibold ${index % 2 ? "rotate-1" : "-rotate-1"}`}
              >
                {name}
              </li>
            ))}
          </ul>
          <p className="mt-5 max-w-3xl text-sm leading-relaxed text-graphite">
            The browser runs the world and sends strokes, never pixels. Python owns the rasterizer, so the model sees a
            drawing the way it was trained to. The API runs in a container on AWS and reads its model from S3. This
            site is on Vercel.
          </p>
        </div>
      </Reveal>
    </section>
  );
}
