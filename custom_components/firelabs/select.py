"""Select entities for FireLabs."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import FirelabsCoordinator
from .entity import FirelabsEntity

# index matches the firmware's Config::RestoreMode enum
RESTORE_OPTIONS = ["Off", "On", "Last"]


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: FirelabsCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([RestoreModeSelect(coordinator)])


class RestoreModeSelect(FirelabsEntity, SelectEntity):
    """Relay state to restore after a power loss."""

    _attr_name = "Restore mode"
    _attr_icon = "mdi:restart"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_options = RESTORE_OPTIONS

    def __init__(self, coordinator: FirelabsCoordinator) -> None:
        super().__init__(coordinator, "restore")

    @property
    def current_option(self) -> str | None:
        idx = self.coordinator.data.get("restore")
        if isinstance(idx, int) and 0 <= idx < len(RESTORE_OPTIONS):
            return RESTORE_OPTIONS[idx]
        return None

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.async_command(
            "/api/config", {"restore_mode": RESTORE_OPTIONS.index(option)}
        )
