"""Polling coordinator for a FireLabs device."""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    HTTP_TIMEOUT,
    OTA_DOWNLOAD_TIMEOUT,
    OTA_UPLOAD_TIMEOUT,
)

_LOGGER = logging.getLogger(__name__)


class FirelabsCoordinator(DataUpdateCoordinator[dict]):
    """Polls /api/status and pushes commands to a FireLabs plug over HTTP."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} {entry.data['host']}",
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.host: str = entry.data["host"]
        self._session = async_get_clientsession(hass)

    @property
    def base_url(self) -> str:
        return f"http://{self.host}"

    async def _async_update_data(self) -> dict:
        try:
            async with asyncio.timeout(HTTP_TIMEOUT):
                resp = await self._session.get(f"{self.base_url}/api/status")
                resp.raise_for_status()
                data = await resp.json()
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise UpdateFailed(f"Error talking to {self.host}: {err}") from err
        self._reconcile_sw_version(data)
        return data

    def _reconcile_sw_version(self, data: dict) -> None:
        """Push the running firmware into the device registry when it changes.

        HA reads sw_version from device_info only at registration, so an OTA would
        otherwise show the old version until a reload. Updating the registry here
        keeps it current within a poll, including updates driven by the update
        entity.
        """
        mac = data.get("mac")
        fw = data.get("fw")
        if not mac or not fw:
            return
        registry = dr.async_get(self.hass)
        device = registry.async_get_device(
            identifiers={(DOMAIN, mac.replace(":", "").lower())}
        )
        if device and device.sw_version != fw:
            registry.async_update_device(device.id, sw_version=fw)

    async def async_command(self, path: str, payload: dict) -> None:
        """POST a command, then refresh so HA reflects the new state quickly."""
        try:
            async with asyncio.timeout(HTTP_TIMEOUT):
                resp = await self._session.post(f"{self.base_url}{path}", json=payload)
                resp.raise_for_status()
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise UpdateFailed(f"Command {path} failed: {err}") from err
        await self.async_request_refresh()

    async def async_ota_from_url(self, url: str) -> None:
        """Pull a firmware image and push it to the device's /update endpoint.

        HA downloads over TLS (the device only ever speaks LAN http), then uploads
        the bytes as multipart, the same path the device's web UI uses. The device
        flashes and reboots; the next poll picks up the new version.
        """
        try:
            async with asyncio.timeout(OTA_DOWNLOAD_TIMEOUT):
                resp = await self._session.get(url)
                resp.raise_for_status()
                blob = await resp.read()
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise HomeAssistantError(f"Failed to download firmware: {err}") from err

        form = aiohttp.FormData()
        form.add_field(
            "firmware", blob, filename="firmware.bin",
            content_type="application/octet-stream",
        )
        try:
            async with asyncio.timeout(OTA_UPLOAD_TIMEOUT):
                resp = await self._session.post(f"{self.base_url}/update", data=form)
                resp.raise_for_status()
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise HomeAssistantError(f"Failed to flash {self.host}: {err}") from err
