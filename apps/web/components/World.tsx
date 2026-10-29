"use client";

import { useEffect, useImperativeHandle, useRef, useState, type Ref } from "react";

import type { Placement } from "../lib/studio";
import type { Scene } from "../lib/world/scene";

export type WorldHandle = { clear(): void; reset(): void };

type Props = {
  ref?: Ref<WorldHandle>;
  placements: Placement[];
  paused: boolean;
  speed: number;
  onSpawned: (id: number) => void;
  onCountChange: (count: number) => void;
};

export function World({ ref, placements, paused, speed, onSpawned, onCountChange }: Props) {
  const hostRef = useRef<HTMLDivElement>(null);
  const sceneRef = useRef<Scene | null>(null);
  const spawnedRef = useRef(0);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let cancelled = false;
    let scene: Scene | null = null;
    // Pixi only loads in the browser, after the page has rendered.
    import("../lib/world/scene")
      .then(({ createScene }) => createScene(hostRef.current!))
      .then((created) => {
        if (cancelled) {
          created.destroy();
          return;
        }
        scene = created;
        sceneRef.current = created;
        setReady(true);
      });
    return () => {
      cancelled = true;
      scene?.destroy();
      sceneRef.current = null;
    };
  }, []);

  useImperativeHandle(
    ref,
    () => ({
      clear() {
        sceneRef.current?.clear();
        onCountChange(0);
      },
      reset() {
        sceneRef.current?.reset();
        onCountChange(0);
      },
    }),
    [onCountChange],
  );

  useEffect(() => {
    sceneRef.current?.setPaused(paused);
  }, [paused, ready]);

  useEffect(() => {
    sceneRef.current?.setSpeed(speed);
  }, [speed, ready]);

  useEffect(() => {
    const scene = sceneRef.current;
    if (!ready || !scene) {
      return;
    }
    for (const placement of placements) {
      if (placement.id > spawnedRef.current) {
        scene.spawn(placement);
        spawnedRef.current = placement.id;
      }
    }
    if (placements.length > 0) {
      onSpawned(spawnedRef.current);
      onCountChange(scene.count());
    }
  }, [placements, ready, onSpawned, onCountChange]);

  return <div ref={hostRef} className="h-full w-full overflow-hidden rounded-2xl bg-[#5d6a86]" aria-label="World" role="img" />;
}
