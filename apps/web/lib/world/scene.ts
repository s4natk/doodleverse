import { Application, Container, FillGradient, Graphics, Sprite, Texture, type Ticker } from "pixi.js";

import { advance, createClock, MAX_SPEED } from "./clock";
import { GROUND_Y, WORLD_HEIGHT, WORLD_WIDTH, type Drawing, type Sketch } from "./layout";
import {
  BLOOM_GLOW,
  CLOUD_OUTLINE,
  DAY,
  DUSK,
  FLOWER_CLOSED,
  FLOWER_OPEN,
  INK,
  mixColor,
  RAIN,
  SHADE_AT_DUSK,
  STROKE,
  SUN_GLOW_TINT,
} from "./palette";
import { clearWorld, createWorld, pose, rainSpan, resetWorld, spawn, step, tapCloud, type Entity, type World } from "./sim";

export type Scene = {
  spawn(sketch: Sketch): void;
  /** A tap at world (x, y). True when it hit a cloud and toggled its rain. */
  tap(x: number, y: number): boolean;
  /** How many entities are in the world. */
  count(): number;
  setPaused(paused: boolean): void;
  setSpeed(speed: number): void;
  clear(): void;
  reset(): void;
  destroy(): void;
};

type View = { root: Container; glow: Sprite | null };

const GLOW_SIZE = 2.4;

function backdrop(colors: typeof DAY): { graphics: Graphics; gradient: FillGradient } {
  const gradient = new FillGradient({
    type: "linear",
    start: { x: 0, y: 0 },
    end: { x: 0, y: 1 },
    colorStops: [
      { offset: 0, color: colors.skyTop },
      { offset: 1, color: colors.skyHorizon },
    ],
    textureSpace: "local",
  });
  const graphics = new Graphics()
    .rect(0, 0, WORLD_WIDTH, GROUND_Y)
    .fill(gradient)
    .rect(0, GROUND_Y, WORLD_WIDTH, WORLD_HEIGHT - GROUND_Y)
    .fill(colors.ground)
    .rect(0, GROUND_Y, WORLD_WIDTH, 5)
    .fill(colors.groundEdge);
  return { graphics, gradient };
}

function glowTexture(): Texture {
  const size = 256;
  const canvas = document.createElement("canvas");
  canvas.width = size;
  canvas.height = size;
  const context = canvas.getContext("2d")!;
  const gradient = context.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2);
  gradient.addColorStop(0, "rgba(255, 255, 255, 0.95)");
  gradient.addColorStop(0.4, "rgba(255, 255, 255, 0.4)");
  gradient.addColorStop(1, "rgba(255, 255, 255, 0)");
  context.fillStyle = gradient;
  context.fillRect(0, 0, size, size);
  return Texture.from(canvas);
}

function trace(graphics: Graphics, drawing: Drawing, color: number, extraWidth = 0): void {
  for (const stroke of drawing.strokes) {
    const width = stroke.width + extraWidth;
    const [first, ...rest] = stroke.points;
    if (rest.length === 0) {
      graphics.circle(first[0], first[1], width / 2).fill(color);
      continue;
    }
    graphics.moveTo(first[0], first[1]);
    for (const [x, y] of rest) {
      graphics.lineTo(x, y);
    }
    graphics.stroke({ width, color, cap: "round", join: "round" });
  }
}

function halo(texture: Texture, size: number, tint: number, y = 0): Sprite {
  const sprite = new Sprite(texture);
  sprite.anchor.set(0.5);
  sprite.blendMode = "add";
  sprite.width = size;
  sprite.height = size;
  sprite.tint = tint;
  sprite.y = y;
  return sprite;
}

function buildView(entity: Entity, glow: Texture): View {
  const root = new Container();
  const { drawing } = entity;
  let sprite: Sprite | null = null;
  if (entity.label === "sun") {
    sprite = halo(glow, Math.max(drawing.width, drawing.height) * GLOW_SIZE, SUN_GLOW_TINT);
  } else if (entity.label === "flower") {
    // A flower's drawing hangs from its base, so its head is near the top.
    sprite = halo(glow, drawing.width * 1.6, BLOOM_GLOW, -drawing.height * 0.78);
  }
  if (sprite) {
    sprite.alpha = 0;
    root.addChild(sprite);
  }
  const body = new Graphics();
  if (entity.label === "cloud") {
    trace(body, drawing, CLOUD_OUTLINE, 6);
  }
  // Flowers are traced in white and tinted, so the color can open up with the bloom.
  trace(body, drawing, entity.label === "flower" ? 0xffffff : STROKE[entity.label]);
  root.addChild(body);
  return { root, glow: sprite };
}

function bodyColor(entity: Entity, bloom: number): number {
  return entity.label === "flower" ? mixColor(FLOWER_CLOSED, FLOWER_OPEN, bloom) : 0xffffff;
}

const DROP_SPACING = 9;
const DROP_LENGTH = 14;
const DROP_SPEED = 260;

function fraction(value: number): number {
  return value - Math.floor(value);
}

/** Streaks from each raining cloud down to the ground. They fall on world time, so pause stops them. */
function drawRain(graphics: Graphics, world: World, time: number): void {
  graphics.clear();
  let any = false;
  for (const cloud of world.entities) {
    const span = rainSpan(cloud);
    if (!span) {
      continue;
    }
    const now = pose(cloud, world.motion);
    const top = now.y + (cloud.drawing.height * now.scale) / 4;
    const fall = GROUND_Y + 20 - top;
    const drops = Math.max(4, Math.round((span[1] - span[0]) / DROP_SPACING));
    for (let index = 0; index < drops; index += 1) {
      const seed = index * 0.6180339887 + cloud.id * 0.1234;
      const x = span[0] + ((index + 0.5 + 0.3 * (fraction(seed * 7) - 0.5)) / drops) * (span[1] - span[0]);
      const y = top + ((time * DROP_SPEED * (0.8 + 0.4 * fraction(seed * 3)) + fraction(seed) * fall) % fall);
      graphics.moveTo(x, y).lineTo(x - 2, Math.min(y + DROP_LENGTH, GROUND_Y + 20));
      any = true;
    }
  }
  if (any) {
    graphics.stroke({ width: 2.5, color: RAIN, alpha: 0.65, cap: "round" });
  }
}

/**
 * One Pixi app and one ticker for the whole world. Removing entities destroys their display objects;
 * `destroy` also releases the shared textures, the gradients, the ticker callback, and the motion listener.
 */
export async function createScene(host: HTMLElement): Promise<Scene> {
  const app = new Application();
  await app.init({
    resizeTo: host,
    backgroundAlpha: 0,
    antialias: true,
    autoDensity: true,
    resolution: Math.min(2, window.devicePixelRatio || 1),
  });
  host.appendChild(app.canvas);

  const world = createWorld();
  const clock = createClock();
  const glow = glowTexture();
  const dusk = backdrop(DUSK);
  const day = backdrop(DAY);
  const suns = new Container();
  const shaded = new Container();
  shaded.sortableChildren = true;
  const rain = new Graphics();
  rain.zIndex = -1;
  shaded.addChild(rain);
  app.stage.addChild(dusk.graphics, day.graphics, suns, shaded);
  const views = new Map<number, View>();
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  const applyMotion = () => {
    world.motion = reducedMotion.matches ? 0 : 1;
  };
  applyMotion();
  reducedMotion.addEventListener("change", applyMotion);

  function sync(): void {
    app.stage.scale.set(app.screen.width / WORLD_WIDTH);
    day.graphics.alpha = world.sunlight;
    shaded.tint = mixColor(SHADE_AT_DUSK, 0xffffff, world.sunlight);
    drawRain(rain, world, world.motion > 0 ? clock.time : 0);
    for (const entity of world.entities) {
      const view = views.get(entity.id);
      if (!view) {
        continue;
      }
      const now = pose(entity, world.motion);
      view.root.position.set(now.x, now.y);
      view.root.scale.set(now.scale);
      view.root.rotation = now.rotation;
      view.root.tint = mixColor(INK, bodyColor(entity, now.bloom), now.settled);
      if (view.glow) {
        view.glow.alpha = entity.label === "flower" ? 0.8 * now.bloom : now.glow;
      }
    }
  }

  function tick(ticker: Ticker): void {
    const steps = advance(clock, ticker.deltaMS);
    for (let index = 0; index < steps; index += 1) {
      step(world);
    }
    sync();
  }

  function removeViews(): void {
    for (const view of views.values()) {
      view.root.destroy({ children: true });
    }
    views.clear();
  }

  app.ticker.add(tick);
  sync();

  return {
    spawn(sketch) {
      const entity = spawn(world, sketch);
      const view = buildView(entity, glow);
      if (entity.label === "sun") {
        suns.addChild(view.root);
      } else {
        view.root.zIndex = entity.label === "cloud" ? 0 : entity.rest.y;
        shaded.addChild(view.root);
      }
      views.set(entity.id, view);
      sync();
    },
    tap(x, y) {
      const hit = tapCloud(world, x, y) !== null;
      if (hit) {
        sync();
      }
      return hit;
    },
    count() {
      return world.entities.length;
    },
    setPaused(paused) {
      clock.paused = paused;
    },
    setSpeed(speed) {
      clock.speed = Math.min(MAX_SPEED, Math.max(0, speed));
    },
    clear() {
      removeViews();
      clearWorld(world);
      sync();
    },
    reset() {
      removeViews();
      resetWorld(world);
      Object.assign(clock, createClock());
      sync();
    },
    destroy() {
      app.ticker.remove(tick);
      reducedMotion.removeEventListener("change", applyMotion);
      removeViews();
      clearWorld(world);
      glow.destroy(true);
      dusk.gradient.destroy();
      day.gradient.destroy();
      app.destroy({ removeView: true }, { children: true });
    },
  };
}
