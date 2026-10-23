from __future__ import annotations

import argparse
from pathlib import Path

from doodleverse.classes import LABELS
from doodleverse.data.download import bitmap_row_count, download_bitmaps
from doodleverse.data.splits import (
    SAMPLES_PER_CLASS,
    SEED,
    assert_manifest_integrity,
    make_manifest,
    write_manifest,
)


def prepare(
    raw_dir: Path,
    manifest_path: Path,
    seed: int = SEED,
    samples_per_class: int = SAMPLES_PER_CLASS,
    skip_download: bool = False,
) -> dict:
    if not skip_download:
        download_bitmaps(raw_dir, LABELS)
    counts = {label: bitmap_row_count(raw_dir / f"{label}.npy") for label in LABELS}
    manifest = make_manifest(counts, seed=seed, samples_per_class=samples_per_class)
    assert_manifest_integrity(manifest)
    write_manifest(manifest, manifest_path)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Download Quick, Draw! bitmaps and write splits.")
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--manifest", type=Path, default=Path("ml/splits/v1.json"))
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--samples", type=int, default=SAMPLES_PER_CLASS)
    parser.add_argument("--skip-download", action="store_true")
    args = parser.parse_args()
    manifest = prepare(
        raw_dir=args.raw_dir,
        manifest_path=args.manifest,
        seed=args.seed,
        samples_per_class=args.samples,
        skip_download=args.skip_download,
    )
    print(
        f"Wrote {args.manifest} with {manifest['samples_per_class']} drawings per class, "
        f"seed {manifest['seed']}."
    )


if __name__ == "__main__":
    main()
