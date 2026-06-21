"""Per-model entity builders.

Each FireLabs device model has its own module exposing builder functions named
after the HA platform (switches, sensors, binary_sensors, selects, buttons,
lights, numbers, texts). The integration looks up the module by the `model`
string the device reports at /api/status and calls the matching builder.

Adding a device: write models/<model>.py with the builders it needs, then add
it to MODELS below.
"""
from __future__ import annotations

from types import ModuleType

from . import s31

MODELS: dict[str, ModuleType] = {
    "S31": s31,
}


def for_model(model: str | None) -> ModuleType | None:
    """Return the module handling this device model, or None if unsupported."""
    if not model:
        return None
    return MODELS.get(model)
