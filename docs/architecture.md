# Architecture

The browser sends one sketch. Python classifies it. The browser runs the world.

```text
strokes -> inference -> class, score, top 3 -> confirm -> entity
```

Python does not step the simulation. Positions, growth, rain, and collisions stay in the browser. The model returns a class, not a behavior.

The request is strokes plus the canvas size, not a screenshot. `strokes_to_model_input` frames those points into a 28×28 float image. Training rows are already 28×28 and only pass through `normalize_quickdraw_bitmap`. Both end as ink-high values in [0, 1]. Google rendered the training bitmaps. This rasterizer did not. Details are in `docs/experiments.md`.

Labels, in order: sun, cloud, tree, flower, car, cat. That tuple is the softmax index order in `ml/doodleverse/classes.py`.
