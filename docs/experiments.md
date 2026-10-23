# Experiments

Numbers in this file come from `python -m doodleverse.data.explore` on the local bitmap files.

## What a Quick, Draw! bitmap already is

Each category file stores drawings as `uint8` rows of length 784. Reshaped, a row is a 28×28 image. Google already scaled the sketch into that square and centered the ink. The file is not a record of where the pen moved on a canvas, and it is not the same object as a stroke list typed into the app.

The probe below is evidence from these files, not a second copy of Google's write-up. Ink is denser in the middle 14×14 pixels than in the outer two-pixel border, which is what a centered drawing looks like after it has been fit into the frame.

## Polarity

Mean stored pixel across 2048 drawings per class: 42.90 on a 0–255 scale. Seed 1729.

That mean is below mid-gray, so the decision is `ink_high`.

`ink_high` means the background is stored as 0 and the stroke is stored brighter. The training normalizer divides by 255 and does not invert. `ink_low` would divide by 255 and invert once. The rule is the mean compared with 127. A softmax model trained on one direction will misread a drawing stored the other way.

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

Those sparse rows are still labeled. A later model will treat a nearly blank cat and a finished cat as the same class. That is a property of the dataset, visible here before training.

## Normalizer

Training will call `normalize_quickdraw_bitmap`. A row is reshaped to 28×28, divided by 255 when values still sit on the 0–255 scale, and left uninverted because the measured polarity is `ink_high`. The result is float32 in [0, 1]. The same stored bitmap always produces the same tensor.

This function does not redraw a stroke. A person drawing in the app produces points on a canvas of some width and height. Those points have not been centered in a 28×28 frame and have not been given Google's stroke thickness. If that live drawing is not mapped into this same numeric picture, the network is asked to recognize a kind of image it did not train on. That gap is train/serve skew, and it starts with the difference between these files and a raw canvas.
