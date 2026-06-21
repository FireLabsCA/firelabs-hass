"""FireLabs firmware update platform.

Unlike the other platforms this isn't dispatched per model: every FireLabs device
reports its running firmware the same way (`fw` in /api/status) and flashes the
same way (multipart POST to /update). The only per-model bit is which GitHub repo
holds the releases, looked up in FIRMWARE_REPOS.
"""
from __future__ import annotations

from typing import Any

from homeassistant.components.update import (
    UpdateDeviceClass,
    UpdateEntity,
    UpdateEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval

from .const import DOMAIN, FIRMWARE_REPOS, LATEST_POLL_INTERVAL, RELEASES_KEY
from .coordinator import FirelabsCoordinator
from .entity import FirelabsEntity
from .release import ReleaseCache


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: FirelabsCoordinator = hass.data[DOMAIN][entry.entry_id]
    model = coordinator.data.get("model")
    repo = FIRMWARE_REPOS.get(model) if model else None
    if not repo:
        return  # no known firmware repo for this model; nothing to update against

    cache: ReleaseCache = hass.data.setdefault(
        RELEASES_KEY, ReleaseCache(async_get_clientsession(hass))
    )
    async_add_entities([FirelabsUpdate(coordinator, cache, repo, model)])


class FirelabsUpdate(FirelabsEntity, UpdateEntity):
    """Compares the device's running firmware against the latest GitHub release."""

    _attr_name = "Firmware"
    _attr_device_class = UpdateDeviceClass.FIRMWARE
    _attr_entity_category = EntityCategory.CONFIG
    _attr_supported_features = (
        UpdateEntityFeature.INSTALL | UpdateEntityFeature.RELEASE_NOTES
    )

    def __init__(
        self,
        coordinator: FirelabsCoordinator,
        cache: ReleaseCache,
        repo: str,
        model: str,
    ) -> None:
        super().__init__(coordinator, "firmware")
        self._cache = cache
        self._repo = repo
        self._model = model

    @property
    def installed_version(self) -> str | None:
        return self.coordinator.data.get("fw")

    @property
    def latest_version(self) -> str | None:
        rel = self._cache.cached(self._repo)
        # Before the first GitHub fetch lands, report installed so HA shows
        # "up to date" rather than "unknown".
        if rel and rel.version:
            return rel.version
        return self.installed_version

    @property
    def release_url(self) -> str | None:
        rel = self._cache.cached(self._repo)
        return rel.url or None if rel else None

    async def async_release_notes(self) -> str | None:
        rel = self._cache.cached(self._repo)
        return rel.notes if rel else None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        await self._cache.async_refresh(self._repo, self._model)
        self.async_on_remove(
            async_track_time_interval(
                self.hass, self._async_poll_latest, LATEST_POLL_INTERVAL
            )
        )

    async def _async_poll_latest(self, _now: Any) -> None:
        await self._cache.async_refresh(self._repo, self._model)
        self.async_write_ha_state()

    async def async_install(
        self, version: str | None, backup: bool, **kwargs: Any
    ) -> None:
        rel = self._cache.cached(self._repo)
        if not rel or not rel.bin_url:
            raise HomeAssistantError(
                "No firmware .bin found in the latest release for this device"
            )
        self._attr_in_progress = True
        self.async_write_ha_state()
        try:
            await self.coordinator.async_ota_from_url(rel.bin_url)
        finally:
            self._attr_in_progress = False
            self.async_write_ha_state()
        await self.coordinator.async_request_refresh()
