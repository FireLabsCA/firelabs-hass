"""Polling coordinator for a FireLabs device."""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DEFAULT_SCAN_INTERVAL, DOMAIN, HTTP_TIMEOUT

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
                return await resp.json()
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise UpdateFailed(f"Error talking to {self.host}: {err}") from err

    async def async_command(self, path: str, payload: dict) -> None:
        """POST a command, then refresh so HA reflects the new state quickly."""
        try:
            async with asyncio.timeout(HTTP_TIMEOUT):
                resp = await self._session.post(f"{self.base_url}{path}", json=payload)
                resp.raise_for_status()
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise UpdateFailed(f"Command {path} failed: {err}") from err
        await self.async_request_refresh()
