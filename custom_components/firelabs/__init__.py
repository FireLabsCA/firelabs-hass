"""The FireLabs integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import CONF_WEBHOOK_ID, DOMAIN, MODEL_WX
from .coordinator import FirelabsCoordinator
from .webhook import async_register_webhook, async_unregister_webhook

PLATFORMS: list[Platform] = [
    Platform.SWITCH,
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.SELECT,
    Platform.BUTTON,
    Platform.LIGHT,
    Platform.NUMBER,
    Platform.TEXT,
    Platform.UPDATE,
]

# Identity fields seeded into the coordinator for a sleepy device, so setup does
# not depend on the device being awake and reachable.
_SEED_KEYS = ("host", "mac", "model", "name", "fw")


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up FireLabs from a config entry."""
    if entry.data.get("model") == MODEL_WX:
        return await _async_setup_wx(hass, entry)

    coordinator = FirelabsCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload))
    return True


async def _async_setup_wx(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a Weather Display: no polling, webhook-driven, options-mapped."""
    coordinator = FirelabsCoordinator(hass, entry, poll=False)
    coordinator.webhook_id = entry.data.get(CONF_WEBHOOK_ID)
    seed = {k: entry.data[k] for k in _SEED_KEYS if entry.data.get(k) is not None}
    coordinator.async_set_updated_data(seed)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await async_register_webhook(hass, entry, coordinator)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    # Re-pointing entity mappings (options) takes effect on reload.
    entry.async_on_unload(entry.add_update_listener(_async_reload))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if entry.data.get("model") == MODEL_WX:
        async_unregister_webhook(hass, entry)
    if await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    return True


async def _async_reload(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
