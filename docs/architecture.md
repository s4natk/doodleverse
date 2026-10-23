# Architecture

Doodleverse is two processes. The split is the whole design.

```text
pointer events in the browser
        |
        v
one sketch, as a list of strokes
        |
        v
Python inference process
        |
        v
class, score, top three, and an uncertainty flag
        |
        v
the person confirms
        |
        v
the browser places an entity and runs the world
```

Python will classify a single drawing. The browser will own positions, growth, rain, and collisions. Creature behavior will be ordinary game code. The network will not output "walk" or "make rain."

TensorFlow and a 60 Hz animation loop do not belong in one process. A model load is slow and heavy. The world changes every frame and has to stay on the machine where the pointer is. Keeping them apart also means the game can run when the recognizer is down: the sketch stays put, and nothing is invented in its place.

## What crosses the boundary

The browser will send strokes: lists of points, plus the canvas size. It will not send a screenshot, and it will not rasterize the model input itself. Python will own framing, resizing, and normalization, because that code has to match training. Quick, Draw! bitmaps are already 28×28 images Google centered and scaled. A live stroke is not that file. Later days have to document that difference instead of pretending one function produced both.

The reply will be a class name from a fixed list, not a sprite and not a behavior.

Quick, Draw! bitmaps used for training are already 28×28 and centered. `normalize_quickdraw_bitmap` only rescales those rows into `[0, 1]`. `strokes_to_model_input` frames a live stroke into that same numeric picture. The two paths share size, polarity, and scale. They do not share a rasterizer. The difference is written in `docs/experiments.md`.

## Label order

`ml/doodleverse/classes.py` lists sun, cloud, tree, flower, car, cat. That order is part of the model, the same way a weight is. Index 0 is the first output unit. The API, the training script, and this file have to agree, or a correct weight vector will be given the wrong name.

## What is still ahead

No network has been trained. The API does not serve a sketch yet. Docker Compose starts the two empty shells.
