"""Base entity for FireLabs devices."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import FirelabsCoordinator


class FirelabsEntity(CoordinatorEntity[FirelabsCoordinator]):
    """Common device info + unique id for all FireLabs entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: FirelabsCoordinator, key: str) -> None:
        super().__init__(coordinator)
        self._key = key
        mac = (coordinator.data.get("mac") or coordinator.host).replace(":", "").lower()
        self._attr_unique_id = f"{mac}_{key}"

    @property
    def device_info(self) -> DeviceInfo:
        data = self.coordinator.data
        mac = (data.get("mac") or self.coordinator.host).replace(":", "").lower()
        return DeviceInfo(
            identifiers={(DOMAIN, mac)},
            name=data.get("name") or "FireLabs",
            manufacturer=MANUFACTURER,
            model=data.get("model"),
            sw_version=data.get("fw"),
            configuration_url=f"http://{self.coordinator.host}",
            connections={("mac", data["mac"])} if data.get("mac") else set(),
        )
