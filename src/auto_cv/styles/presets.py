"""Style preset loader — resolves built-in and vault-local presets."""

from __future__ import annotations

from pathlib import Path

import yaml

from auto_cv.models.style import StyleConfig

_PRESETS_DIR = Path(__file__).parent / "presets"

BUILTIN_PRESETS = ("classic", "modern", "minimal")


def load_preset(name: str, vault_path: Path | None = None) -> StyleConfig:
    """Load a style preset by name.

    Resolution order:
    1. If name starts with "./" and vault_path is given, load from vault's presets/ dir.
    2. Otherwise look up built-in presets.
    3. Fall back to classic if not found.
    """
    if name.startswith("./") and vault_path is not None:
        local_path = vault_path / name
        if local_path.exists():
            return _load_preset_file(local_path)

    preset_file = _PRESETS_DIR / f"{name}.yml"
    if preset_file.exists():
        return _load_preset_file(preset_file)

    # Fallback
    return _load_preset_file(_PRESETS_DIR / "classic.yml")


def _load_preset_file(path: Path) -> StyleConfig:
    """Parse a YAML preset file into a StyleConfig."""
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    return StyleConfig.model_validate(raw)


def list_presets() -> list[str]:
    """Return names of all built-in presets."""
    return [p.stem for p in sorted(_PRESETS_DIR.glob("*.yml"))]
