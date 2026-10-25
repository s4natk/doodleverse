# Experiments

Every number here is written by a script from a local run: the data sections by `doodleverse.data.explore`, the models by `doodleverse.training.compare`, and the training fixes by `doodleverse.training.ablate_cnn`.

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

## Models

Validation split only (3,600 drawings, 600 per class). The test split was not read. Split seed 1729. Machine: Windows-11-10.0.26300-SP0, 32 CPUs, Python 3.12.3, TensorFlow 2.21.0.

Accuracy equals macro-recall here because every class has the same support.

### Logistic regression

Multinomial cross-entropy on the 784 flattened pixels, L2 penalty, lbfgs. One fit per C on the full training split. The best validation macro-F1 is kept.

| C | val accuracy | val macro-F1 | iterations | converged |
| --- | --- | --- | --- | --- |
| 0.01 | 0.828 | 0.828 | 136 | yes |
| 0.1 | 0.831 | 0.831 | 151 | yes |
| 1.0 | 0.819 | 0.818 | 297 | yes |
| 10.0 | 0.810 | 0.809 | 606 | yes |

Kept `C=0.1`. Train accuracy 0.863, validation accuracy 0.831, macro-F1 0.831. 4710 parameters. Weakest class: cat (recall 0.763).

| class | precision | recall | f1 | support |
| --- | --- | --- | --- | --- |
| sun | 0.834 | 0.853 | 0.843 | 600 |
| cloud | 0.855 | 0.852 | 0.853 | 600 |
| tree | 0.812 | 0.822 | 0.817 | 600 |
| flower | 0.814 | 0.788 | 0.801 | 600 |
| car | 0.882 | 0.910 | 0.896 | 600 |
| cat | 0.788 | 0.763 | 0.776 | 600 |

### CNN

Three 3×3 conv blocks (32, 64, 128 filters), batch norm (momentum 0.9), ReLU, max-pool after the first two, global average pooling, dropout 0.3, softmax over six classes. Adam at 1e-3, sparse categorical cross-entropy, up to 8% whole-pixel shifts during training only, learning rate halved on a validation-loss plateau, early stopping that restores the best validation-loss epoch.

Best epoch 14 of 18. Train accuracy 0.957 (inference mode), validation accuracy 0.952, macro-F1 0.952. 94118 parameters, 1167 KB on disk. Weakest class: tree (recall 0.917).

Single-image CPU forward pass: first call 19.6 ms, then p50 6.16 ms and p95 6.97 ms over 100 calls. This is the model alone, not the HTTP service.

| class | precision | recall | f1 | support |
| --- | --- | --- | --- | --- |
| sun | 0.956 | 0.968 | 0.962 | 600 |
| cloud | 0.964 | 0.970 | 0.967 | 600 |
| tree | 0.963 | 0.917 | 0.939 | 600 |
| flower | 0.937 | 0.943 | 0.940 | 600 |
| car | 0.970 | 0.967 | 0.968 | 600 |
| cat | 0.922 | 0.945 | 0.933 | 600 |

The CNN is 0.121 macro-F1 above logistic regression on validation. A convolution reuses the same local stroke detector at every position in the bitmap. Logistic regression has one weight per pixel, so a curve in the corner and the same curve in the middle need unrelated weights.

Figures: [baseline confusion](figures/baseline_confusion.png), [CNN learning curves](figures/cnn_learning_curves.png), [CNN confusion](figures/cnn_confusion.png).

## CNN training fixes

With Keras defaults, validation accuracy after the first epoch was 0.167, chance for six classes, and fell by as much as 0.196 between consecutive epochs, while training accuracy rose smoothly. Two settings were changed. Each is switched back below with the same split, seed, and schedule (up to 20 epochs, early-stopping patience 4).

Batch-norm momentum. Inference uses a moving average of each channel's mean and variance. At the default momentum of 0.99 that average spans roughly the last 100 steps, and after one 132-step epoch about a quarter of its weight still sits on the starting values. Momentum 0.9 spans roughly the last 10 steps, so validation runs on statistics from the current weights.

Shift interpolation. RandomTranslation moves each training image by a fractional number of pixels. Bilinear interpolation resamples, and so blurs, every training stroke. Validation images and live sketches are never shifted and stay sharp. Nearest interpolation shifts by whole pixels, so training and inference see strokes of the same sharpness.

| configuration | epoch-1 val accuracy | largest epoch-to-epoch drop | best epoch | val accuracy | val macro-F1 |
| --- | --- | --- | --- | --- | --- |
| Keras defaults: momentum 0.99, bilinear shifts | 0.167 | 0.196 | 6 of 10 | 0.914 | 0.913 |
| Momentum 0.9, bilinear shifts | 0.758 | 0.095 | 14 of 18 | 0.949 | 0.949 |
| Momentum 0.9, nearest shifts (kept) | 0.337 | 0.089 | 14 of 18 | 0.952 | 0.952 |

Momentum moved validation accuracy by +0.035. Nearest shifts moved it by +0.003 more. One seed on one split cannot separate a change that small from noise, so nearest is kept because it removes a train/inference mismatch, not for its score. Epoch-1 accuracy is a single noisy reading. The largest drop is the steadier measure of how much validation swings.
