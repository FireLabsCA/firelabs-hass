"""Binary sensor entities for FireLabs."""
from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import FirelabsCoordinator
from .entity import FirelabsEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: FirelabsCoordinator = hass.data[DOMAIN][entry.entry_id]
    if coordinator.data.get("meter"):
        async_add_entities([FaultBinarySensor(coordinator)])


class FaultBinarySensor(FirelabsEntity, BinarySensorEntity):
    """Relay on but drawing roughly no power."""

    _attr_name = "Fault"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, coordinator: FirelabsCoordinator) -> None:
        super().__init__(coordinator, "fault")

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.data.get("fault"))
