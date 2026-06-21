"""Switch entities for FireLabs."""
from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import FirelabsCoordinator
from .entity import FirelabsEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: FirelabsCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SwitchEntity] = [
        RelaySwitch(coordinator),
        IdentifySwitch(coordinator),
    ]
    if coordinator.data.get("meter"):
        entities.append(NoLoadSwitch(coordinator))
    async_add_entities(entities)


class RelaySwitch(FirelabsEntity, SwitchEntity):
    """The mains relay."""

    _attr_name = None  # primary feature: use the device name
    _attr_icon = "mdi:power-socket-us"

    def __init__(self, coordinator: FirelabsCoordinator) -> None:
        super().__init__(coordinator, "relay")

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.data.get("relay"))

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_command("/api/relay", {"on": True})

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_command("/api/relay", {"on": False})


class NoLoadSwitch(FirelabsEntity, SwitchEntity):
    """Toggle the blue-LED no-load indicator."""

    _attr_name = "No-load indicator"
    _attr_icon = "mdi:led-on"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: FirelabsCoordinator) -> None:
        super().__init__(coordinator, "noload")

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.data.get("noload"))

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_command("/api/config", {"noload": True})

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_command("/api/config", {"noload": False})


class IdentifySwitch(FirelabsEntity, SwitchEntity):
    """Blink the LED to locate the plug."""

    _attr_name = "Identify"
    _attr_icon = "mdi:map-marker-radius"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: FirelabsCoordinator) -> None:
        super().__init__(coordinator, "identify")

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.data.get("identify"))

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_command("/api/identify", {"on": True})

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_command("/api/identify", {"on": False})
