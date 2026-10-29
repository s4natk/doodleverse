"use client";

import { useEffect, useRef, useState, type PointerEvent as ReactPointerEvent } from "react";

import type { Point } from "../lib/geometry";
import type { SketchAction, Stroke } from "../lib/sketch";

export type Tool = "pencil" | "eraser";
export type CanvasSize = { width: number; height: number };

const INK = "#2c2733";
const ERASER_RADIUS = 10;

type Props = {
  strokes: Stroke[];
  active: Stroke | null;
  tool: Tool;
  width: number;
  disabled?: boolean;
  onAction: (action: SketchAction) => void;
  onResize?: (size: CanvasSize) => void;
};

function paint(canvas: HTMLCanvasElement, size: CanvasSize, strokes: Stroke[]): void {
  const context = canvas.getContext("2d");
  if (!context) {
    return;
  }
  const scale = canvas.width / size.width;
  context.setTransform(scale, 0, 0, scale, 0, 0);
  context.clearRect(0, 0, size.width, size.height);
  context.strokeStyle = INK;
  context.fillStyle = INK;
  context.lineCap = "round";
  context.lineJoin = "round";
  for (const stroke of strokes) {
    const [first, ...rest] = stroke.points;
    context.beginPath();
    if (rest.length === 0) {
      context.arc(first[0], first[1], stroke.width / 2, 0, Math.PI * 2);
      context.fill();
      continue;
    }
    context.lineWidth = stroke.width;
    context.moveTo(first[0], first[1]);
    for (const [x, y] of rest) {
      context.lineTo(x, y);
    }
    context.stroke();
  }
}

export function SketchPad({ strokes, active, tool, width, disabled = false, onAction, onResize }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const gestureRef = useRef<{ pointerId: number; tool: Tool } | null>(null);
  const resizeRef = useRef(onResize);
  const [size, setSize] = useState<CanvasSize | null>(null);

  useEffect(() => {
    resizeRef.current = onResize;
  }, [onResize]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) {
      return;
    }
    const observer = new ResizeObserver(([entry]) => {
      const next = { width: entry.contentRect.width, height: entry.contentRect.height };
      const ratio = window.devicePixelRatio || 1;
      canvas.width = Math.max(1, Math.round(next.width * ratio));
      canvas.height = Math.max(1, Math.round(next.height * ratio));
      setSize(next);
      resizeRef.current?.(next);
    });
    observer.observe(canvas);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (canvasRef.current && size) {
      paint(canvasRef.current, size, active ? [...strokes, active] : strokes);
    }
  }, [strokes, active, size]);

  function toPoint(event: { clientX: number; clientY: number }): Point {
    const rect = canvasRef.current!.getBoundingClientRect();
    return [Math.round((event.clientX - rect.left) * 10) / 10, Math.round((event.clientY - rect.top) * 10) / 10];
  }

  function handleDown(event: ReactPointerEvent<HTMLCanvasElement>) {
    if (disabled || gestureRef.current || (event.pointerType === "mouse" && event.button !== 0)) {
      return;
    }
    event.preventDefault();
    gestureRef.current = { pointerId: event.pointerId, tool };
    try {
      event.currentTarget.setPointerCapture(event.pointerId);
    } catch {
      // Capture fails for a pointer the browser no longer tracks. The gesture still works without it.
    }
    const point = toPoint(event);
    if (tool === "eraser") {
      onAction({ type: "eraseBegin" });
      onAction({ type: "erase", point, radius: ERASER_RADIUS });
    } else {
      onAction({ type: "begin", point, width });
    }
  }

  function handleMove(event: ReactPointerEvent<HTMLCanvasElement>) {
    const gesture = gestureRef.current;
    if (!gesture || gesture.pointerId !== event.pointerId) {
      return;
    }
    const coalesced = event.nativeEvent.getCoalescedEvents?.() ?? [];
    const points = (coalesced.length > 0 ? coalesced : [event.nativeEvent]).map(toPoint);
    if (gesture.tool === "eraser") {
      for (const point of points) {
        onAction({ type: "erase", point, radius: ERASER_RADIUS });
      }
    } else {
      onAction({ type: "extend", points });
    }
  }

  function handleEnd(event: ReactPointerEvent<HTMLCanvasElement>, cancelled: boolean) {
    const gesture = gestureRef.current;
    if (!gesture || gesture.pointerId !== event.pointerId) {
      return;
    }
    gestureRef.current = null;
    if (gesture.tool === "eraser") {
      onAction({ type: "eraseEnd" });
    } else {
      onAction({ type: cancelled ? "cancel" : "end" });
    }
  }

  return (
    <canvas
      ref={canvasRef}
      aria-label="Drawing area"
      className={`block h-full w-full touch-none select-none rounded-2xl ${
        disabled ? "cursor-wait" : tool === "eraser" ? "cursor-cell" : "cursor-crosshair"
      }`}
      onPointerDown={handleDown}
      onPointerMove={handleMove}
      onPointerUp={(event) => handleEnd(event, false)}
      onPointerCancel={(event) => handleEnd(event, true)}
    />
  );
}
