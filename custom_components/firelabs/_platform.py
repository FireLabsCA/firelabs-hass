"""Shared platform setup: dispatch to the device model's builder.

Each platform file (switch.py, sensor.py, ...) is a thin wrapper that calls
add_entities_for() with the builder name for that platform. The per-model
module (models/<model>.py) supplies the actual entities.
"""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import models
from .const import DOMAIN
from .coordinator import FirelabsCoordinator

_LOGGER = logging.getLogger(__name__)


def add_entities_for(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
    builder: str,
) -> None:
    coordinator: FirelabsCoordinator = hass.data[DOMAIN][entry.entry_id]
    model = coordinator.data.get("model")
    module = models.for_model(model)
    if module is None:
        _LOGGER.warning("No FireLabs model handler for '%s'; skipping %s", model, builder)
        return
    fn = getattr(module, builder, None)
    if fn is not None:
        async_add_entities(fn(coordinator))
