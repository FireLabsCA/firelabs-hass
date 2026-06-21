"""Config flow for FireLabs."""
from __future__ import annotations

import asyncio
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN, HTTP_TIMEOUT


class FirelabsConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for FireLabs."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            try:
                status = await self._probe(host)
            except (aiohttp.ClientError, asyncio.TimeoutError):
                errors["base"] = "cannot_connect"
            else:
                mac = status.get("mac")
                if not mac:
                    errors["base"] = "cannot_connect"
                else:
                    await self.async_set_unique_id(mac.replace(":", "").lower())
                    self._abort_if_unique_id_configured(updates={CONF_HOST: host})
                    title = status.get("name") or f"FireLabs {status.get('model', '')}".strip()
                    return self.async_create_entry(title=title, data={CONF_HOST: host})

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_HOST): str}),
            errors=errors,
        )

    async def _probe(self, host: str) -> dict:
        session = async_get_clientsession(self.hass)
        async with asyncio.timeout(HTTP_TIMEOUT):
            resp = await session.get(f"http://{host}/api/status")
            resp.raise_for_status()
            return await resp.json()
