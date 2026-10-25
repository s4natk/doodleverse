from doodleverse.training.ablate_cnn import _stability, ablation_section


def _row(name: str, first: float, drop: float, best: int, ran: int, accuracy: float, f1: float) -> dict:
    return {
        "name": name,
        "first": first,
        "drop": drop,
        "best_epoch": best,
        "epochs_ran": ran,
        "val_accuracy": accuracy,
        "val_macro_f1": f1,
    }


def test_stability_reports_first_epoch_and_largest_drop():
    first, drop = _stability({"val_accuracy": [0.17, 0.9, 0.72, 0.88, 0.91]})
    assert first == 0.17
    assert round(drop, 2) == 0.18
    assert _stability({"val_accuracy": [0.5, 0.6, 0.7]}) == (0.5, 0.0)


def test_section_is_written_from_the_measured_rows():
    rows = [
        _row("defaults", 0.2, 0.15, 6, 10, 0.9, 0.89),
        _row("momentum", 0.6, 0.05, 10, 14, 0.94, 0.94),
        _row("kept", 0.7, 0.02, 12, 16, 0.95, 0.95),
    ]
    section = ablation_section(rows)
    assert section.startswith("## CNN training fixes")
    assert "0.200 (chance is 0.167)" in section
    assert "| kept | 0.700 | 0.020 | 12 of 16 | 0.950 | 0.950 |" in section
    assert "+0.040" in section and "+0.010" in section
