import json

from doodleverse.training.select_cnn import choose, kept_model_dir, narrow_section, trained_report


def _row(variant: str, f1: float, p50: float) -> dict:
    return {
        "variant": variant,
        "filters": [16, 32, 64] if variant == "narrow" else [32, 64, 128],
        "parameter_count": 1000,
        "best_epoch": 10,
        "epochs_ran": 14,
        "val_accuracy": f1,
        "val_macro_f1": f1,
        "p50_ms": p50,
        "p95_ms": p50 + 1,
    }


def test_clear_macro_f1_lead_wins_even_when_slower():
    kept, reason = choose([_row("gap", 0.952, 6.2), _row("narrow", 0.940, 5.1)])
    assert kept["variant"] == "gap"
    assert "0.012 higher" in reason


def test_within_tolerance_the_faster_model_wins():
    kept, reason = choose([_row("gap", 0.952, 6.2), _row("narrow", 0.948, 5.1)])
    assert kept["variant"] == "narrow"
    assert "latency decides" in reason
    kept, _ = choose([_row("gap", 0.952, 5.0), _row("narrow", 0.950, 5.1)])
    assert kept["variant"] == "gap"


def test_saved_run_is_reused_only_with_the_current_settings(tmp_path):
    report = {"variant": "narrow", "filters": [16, 32, 64], "bn_momentum": 0.9, "interpolation": "nearest"}
    (tmp_path / "metrics.json").write_text(json.dumps(report), encoding="utf-8")
    assert trained_report(tmp_path, "narrow") == report
    assert trained_report(tmp_path, "gap") is None
    report["interpolation"] = "bilinear"
    (tmp_path / "metrics.json").write_text(json.dumps(report), encoding="utf-8")
    assert trained_report(tmp_path, "narrow") is None


def test_kept_model_falls_back_to_the_gap_run(tmp_path):
    assert kept_model_dir(tmp_path) == tmp_path / "cnn-gap"
    (tmp_path / "selection.json").write_text(json.dumps({"model_dir": "artifacts/cnn-narrow"}), encoding="utf-8")
    assert kept_model_dir(tmp_path).as_posix() == "artifacts/cnn-narrow"


def test_section_names_the_kept_variant():
    rows = [_row("gap", 0.952, 6.2), _row("narrow", 0.948, 5.1)]
    kept, reason = choose(rows)
    section = narrow_section(rows, kept, reason)
    assert section.startswith("## Narrow CNN")
    assert "| narrow | 16/32/64 | 1,000 | 10 of 14 | 0.948 | 0.948 | 5.10 ms | 6.10 ms |" in section
    assert "Kept: narrow." in section
    assert "still improving" not in section


def test_section_flags_equal_latency_and_a_run_that_used_every_epoch():
    gap, narrow = _row("gap", 0.952, 5.39), _row("narrow", 0.936, 5.37)
    gap["parameter_count"], narrow["parameter_count"] = 94118, 24022
    narrow["best_epoch"] = narrow["epochs_ran"] = 20
    kept, reason = choose([gap, narrow])
    section = narrow_section([gap, narrow], kept, reason)
    assert "Kept: gap." in section
    assert "3.9× fewer parameters but the same single-image latency" in section
    assert "best epoch was its last (20)" in section
