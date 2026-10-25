from doodleverse.report import split_sections, upsert_section


def test_upsert_replaces_one_section_and_keeps_the_rest(tmp_path):
    path = tmp_path / "experiments.md"
    path.write_text("# Experiments\n\nintro\n\n## Data\n\nold data\n\n## Models\n\n### CNN\n\nold\n", encoding="utf-8")
    upsert_section(path, "Models", "## Models\n\n### CNN\n\nnew\n")
    upsert_section(path, "Ablation", "## Ablation\n\nrows\n")
    text = path.read_text(encoding="utf-8")
    preamble, blocks = split_sections(text)
    assert "intro" in preamble
    assert [name for name, _ in blocks] == ["Data", "Models", "Ablation"]
    assert "old data" in text
    assert "new" in text and "\nold\n" not in text
