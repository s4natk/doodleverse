# Model card

Written by `python -m doodleverse.training.model_card` from `artifacts/model/sidecar.json`, `artifacts/gate.json`, `artifacts/skew/summary.json`, `artifacts/comparison.json`, `ml/splits/v1.json`. How each number was reached is in [experiments.md](experiments.md).

## Model

`gap-1ce366c1a170` names one doodle as one of six classes: sun, cloud, tree, flower, car, cat. It is a small convolutional network: three 3×3 convolution blocks (32/64/128 filters) with batch norm and ReLU, max-pooling after the first two, global average pooling, dropout 0.3, and a six-way softmax. 94,118 parameters, 424 KB as `model.keras`, SHA-256 `1ce366c1a170…`.

Trained and exported with TensorFlow 2.21.0 and Keras 3.15.1, from commit `a31d573` with uncommitted changes in the tree.

Input: one 28×28 grayscale image, float32 in [0, 1], ink bright on dark (`ink_high`). The app sends strokes, and the service draws them into that image itself: a 256-pixel canvas, stroke width 12, pad 0.08, then an area resize to 28×28.

Output: six scores that sum to 1, the top three, and `uncertain`, which is true unless the top score leads the second by at least 0.70.

## Intended use

Naming a simple drawing in a drawing toy, where the person confirms or corrects every answer before anything happens. An uncertain answer is never acted on: the person picks the class.

Not for decisions with consequences, for photos or handwriting, or for judging how well someone draws. It knows no class outside the six and always answers with one of them.

## Data

Quick, Draw! by Google Creative Lab, used under CC BY 4.0: the 28×28 bitmaps Google rendered from players' strokes. 4,000 drawings per class, split with seed 1729 into 16,800 for training, 3,600 for validation, and 3,600 for test, with the same number of every class in each split. The players drew in the online game from many countries. No breakdown by country was made.

## Results

| split | drawings | accuracy | macro-F1 | gate coverage | accepted accuracy |
| --- | --- | --- | --- | --- | --- |
| validation | 3,600 | 0.952 | 0.952 | 88.2% | 0.991 |
| test | 3,600 | 0.950 | 0.950 | 86.8% | 0.991 |

The test split was scored once, after the model, the gate, and the rasterizer were frozen. Gate coverage is the share of drawings answered without asking; accepted accuracy is how often those answers were right.

Per class on test:

| class | precision | recall | f1 | support |
| --- | --- | --- | --- | --- |
| sun | 0.969 | 0.977 | 0.973 | 600 |
| cloud | 0.953 | 0.952 | 0.952 | 600 |
| tree | 0.973 | 0.907 | 0.939 | 600 |
| flower | 0.929 | 0.960 | 0.944 | 600 |
| car | 0.951 | 0.973 | 0.962 | 600 |
| cat | 0.929 | 0.933 | 0.931 | 600 |

Weakest class: tree (recall 0.907). The most common test mistakes, true → predicted: tree → flower (29), cat → car (15), flower → cat (11).

For comparison, logistic regression on the same pixels reached 0.831 validation macro-F1 (C=0.1).

## Scores and the gate

The gate's margin of 0.70 was chosen on validation as the widest coverage whose accepted accuracy reaches 0.99. The score floor of 0.00 does not bind.

The scores are softmax outputs, not calibrated probabilities. On validation the mean top score was 0.940 against an accuracy of 0.952, and the expected calibration error over ten bins was 0.017. No calibration was fit.

## Strokes, not bitmaps

The model learned from Google's renders, but the app's drawings are rasterized by this project. To measure that gap, 6,000 drawings (1,000 per class) that are not in the split were read from Google's simplified stroke files and scored twice: as Google's bitmap, and as this rasterizer's drawing of the same strokes.

| input | accuracy on the held-back half |
| --- | --- |
| Google's bitmaps | 0.949 |
| our raster, width 18, pad 0.12 | 0.916 |
| our raster, width 12, pad 0.08 (shipped) | 0.947 |

Width and pad were chosen on the other half of those drawings, not on validation or test. They are Google's simplified strokes, already smoothed and resampled. Pointer input from a browser is denser and noisier, and its accuracy was not measured.

## Limitations

- Six classes. A drawing of anything else still gets one of the six. The gate holds back close calls, but it was never tested on drawings outside the six.
- One training run on one split with one seed. No rerun measured how far these numbers move.
- The gate was tuned on validation, so its validation coverage is optimistic. The test row is the honest one.
- Live drawings were not scored against labels; the stroke gap above is for dataset strokes.
- Latency depends on the machine. Measured numbers, with the hardware, are in [benchmark-results.md](benchmark-results.md).

## Privacy

The service keeps nothing it is sent. Each prediction logs the label, score, uncertain flag, stroke and point counts, and latency, never the points.
