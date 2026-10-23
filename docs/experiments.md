# Experiments

Numbers in this file come from `python -m doodleverse.data.explore` on the local bitmap files.

## What a Quick, Draw! bitmap already is

Each file is `uint8` rows of length 784, one 28×28 drawing per row. The ink is already scaled into that square and centered. A stroke list from the app is not one of these rows.

In the probe, ink is denser in the middle 14×14 than on the outer two-pixel border.

## Polarity

Mean stored pixel across 2048 drawings per class: 42.90 on a 0–255 scale. Seed 1729.

That mean is below mid-gray, so the decision is `ink_high`.

Under 127, paper is stored as 0 and strokes are brighter (`ink_high`): divide by 255, do not invert. At or above 127, invert once after scaling (`ink_low`).

| class | drawings in file | mean pixel | fraction nonzero | border ink | center ink |
| --- | --- | --- | --- | --- | --- |
| sun | 133781 | 39.48 | 0.276 | 0.029 | 0.538 |
| cloud | 120265 | 35.02 | 0.241 | 0.044 | 0.394 |
| tree | 144721 | 44.36 | 0.292 | 0.044 | 0.494 |
| flower | 144818 | 44.88 | 0.286 | 0.036 | 0.588 |
| car | 182764 | 42.97 | 0.277 | 0.046 | 0.559 |
| cat | 123202 | 50.68 | 0.331 | 0.042 | 0.602 |

## Figures

- [Class counts](figures/class_counts.png)
- [Sixteen examples per class](figures/examples.png), shown in stored polarity
- [Pixel-value histogram](figures/pixel_histogram.png) of the same probe
- [Sparsest drawings](figures/odd_samples.png). The emptiest row in each class has sun 10 px, cloud 15 px, tree 18 px, flower 8 px, car 8 px, cat 8 px.

Those sparse rows are still labeled with the class.

## Normalizer

`normalize_quickdraw_bitmap` reshapes a row to 28×28 and divides by 255 when values are still on the 0–255 scale. Measured polarity is `ink_high`, so it does not invert. Output is float32 in [0, 1]. The same bitmap always gives the same tensor.

## Stroke rasterizer

`strokes_to_model_input` frames a live stroke with one scale, pads, centers, draws at a fixed thickness, area-resizes to 28×28, then calls the bitmap normalizer with `ink_high`.

Same as the bitmap path: 28×28, polarity, divide by 255, float32 in [0, 1], rank `(1, 28, 28, 1)`.

Not the same: these dataset files were rendered by Google. Stroke width and INTER_AREA are ours. Changing either moves the 28×28 pixels.
