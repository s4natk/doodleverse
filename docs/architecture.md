# Architecture

The browser sends one sketch. Python classifies it. The browser runs the world.

```text
strokes -> inference -> class, score, top 3 -> confirm -> entity
```

Python does not step the simulation. Positions, growth, rain, and collisions stay in the browser. The model returns a class, not a behavior.

The request is strokes plus the canvas size, not a screenshot. `strokes_to_model_input` frames those points into a 28×28 float image. Training rows are already 28×28 and only pass through `normalize_quickdraw_bitmap`. Both end as ink-high values in [0, 1]. Google rendered the training bitmaps. This rasterizer did not. Details are in `docs/experiments.md`.

Labels, in order: sun, cloud, tree, flower, car, cat. That tuple is the softmax index order in `ml/doodleverse/classes.py`. The web app keeps its own copy, with the sketch limits, in `apps/web/lib/contract.ts`, and a Vitest test reads the Python files to keep the two equal.

In the browser the sketch is the stroke list, nothing else. Recognize locks the canvas and sends that list with the canvas size. A confident answer is confirmed with one tap. An uncertain one is never pre-selected: the person picks from the top three or any of the six. Drawing again after an answer drops the answer and keeps the strokes.

The world is drawn on, not beside: the sketch layer sits exactly over it. A confirmed drawing becomes an entity made of its own strokes, starting where it was drawn and settling over 0.6 s into the sky (sun, cloud) or onto the ground (the rest), scaled into its class's size range.

One PixiJS ticker runs the world. Each frame hands its elapsed time to a fixed-timestep clock, 1/60 s per step, a frame counting for at most 0.25 s and at most 30 steps, and the simulation steps that many times. Rendering only reads poses. The simulation in `apps/web/lib/world` has no Pixi in it and is tested in Vitest, Matter.js included. Every number that shapes behavior is in `rules.ts`.

- Sun: pulses, glows, and brings daylight. One sun gives 0.85 of full day, two give all of it.
- Cloud: drifts and wraps. A tap on it toggles rain, which falls from the middle of the cloud and follows it.
- Tree: grows from a sapling. In the rain it grows four times faster and up to 1.25 times its usual size.
- Flower: grows from a bud and sways. Rain soaks in and dries over time. With water and daylight together it opens, swells, and turns from muted to vivid.
- Car: a Matter.js body on a shared road line. It holds its own speed, hops and turns away when it hits a wall or another car.
- Cat: sits, then wanders to a spot on the ground, bending in depth around tree trunks. A car close by makes it hop and run the other way.

A quick pencil tap that lands on a cloud goes to the world instead of drawing a dot. Removing an entity destroys its display objects and its physics body. Tearing the scene down also removes the ticker callback, the shared glow texture, the sky gradients, the reduced-motion listener, and the Matter collision callback. With reduced motion requested, nothing pulses, bobs, sways, drifts, drives, or walks. Trees still grow and flowers still open.

A frozen model is `model.keras` plus `sidecar.json`. The sidecar holds the label order, the input contract, the rasterizer settings, and the gate thresholds, so whatever serves the model reads them from there instead of repeating them. The deployed service copies the same two files from a versioned S3 prefix once at startup ([deploy.md](deploy.md)).
