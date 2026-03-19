"""Tests for style preset loading."""

from auto_cv.styles.presets import list_presets, load_preset


def test_list_presets():
    presets = list_presets()
    assert "classic" in presets
    assert "modern" in presets
    assert "minimal" in presets


def test_load_classic():
    style = load_preset("classic")
    assert style.preset == "classic"
    assert style.colors.primary is not None


def test_load_modern():
    style = load_preset("modern")
    assert style.preset == "modern"
    assert style.html.layout == "sidebar"


def test_load_minimal():
    style = load_preset("minimal")
    assert style.preset == "minimal"


def test_fallback_to_classic():
    style = load_preset("nonexistent_preset_name")
    assert style.preset == "classic"
