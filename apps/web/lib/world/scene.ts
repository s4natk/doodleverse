import { Application, Container, FillGradient, Graphics, Sprite, Texture, type Ticker } from "pixi.js";

import { advance, createClock, MAX_SPEED } from "./clock";
import { GROUND_Y, WORLD_HEIGHT, WORLD_WIDTH, type Drawing, type Sketch } from "./layout";
import { CLOUD_OUTLINE, DAY, DUSK, INK, mixColor, SHADE_AT_DUSK, STROKE } from "./palette";
import { clearWorld, createWorld, pose, resetWorld, spawn, step, type Entity } from "./sim";

export type Scene = {
  spawn(sketch: Sketch): void;
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
  gradient.addColorStop(0, "rgba(255, 222, 140, 0.95)");
  gradient.addColorStop(0.4, "rgba(255, 196, 96, 0.4)");
  gradient.addColorStop(1, "rgba(255, 176, 64, 0)");
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

function buildView(entity: Entity, glow: Texture): View {
  const root = new Container();
  let sprite: Sprite | null = null;
  if (entity.label === "sun") {
    sprite = new Sprite(glow);
    sprite.anchor.set(0.5);
    sprite.blendMode = "add";
    const size = Math.max(entity.drawing.width, entity.drawing.height) * GLOW_SIZE;
    sprite.width = size;
    sprite.height = size;
    root.addChild(sprite);
  }
  const body = new Graphics();
  if (entity.label === "cloud") {
    trace(body, entity.drawing, CLOUD_OUTLINE, 6);
  }
  trace(body, entity.drawing, STROKE[entity.label]);
  root.addChild(body);
  return { root, glow: sprite };
}

/** One Pixi app and one ticker for the whole world. `destroy` releases every view, texture, and listener. */
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
  app.stage.addChild(dusk.graphics, day.graphics, suns, shaded);
  const views = new Map<number, View>();

  function sync(): void {
    app.stage.scale.set(app.screen.width / WORLD_WIDTH);
    day.graphics.alpha = world.sunlight;
    shaded.tint = mixColor(SHADE_AT_DUSK, 0xffffff, world.sunlight);
    for (const entity of world.entities) {
      const view = views.get(entity.id);
      if (!view) {
        continue;
      }
      const now = pose(entity);
      view.root.position.set(now.x, now.y);
      view.root.scale.set(now.scale);
      view.root.rotation = now.rotation;
      view.root.tint = mixColor(INK, 0xffffff, now.settled);
      if (view.glow) {
        view.glow.alpha = now.glow;
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
      removeViews();
      clearWorld(world);
      glow.destroy(true);
      dusk.gradient.destroy();
      day.gradient.destroy();
      app.destroy({ removeView: true }, { children: true });
    },
  };
}
