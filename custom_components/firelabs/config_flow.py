"""Config flow for FireLabs."""
from __future__ import annotations

import asyncio
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo

from .const import DOMAIN, HTTP_TIMEOUT


class FirelabsConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for FireLabs."""

    VERSION = 1

    def __init__(self) -> None:
        self._host: str | None = None
        self._title: str | None = None

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
                if not status.get("mac"):
                    errors["base"] = "cannot_connect"
                else:
                    await self.async_set_unique_id(_uid(status["mac"]))
                    self._abort_if_unique_id_configured(updates={CONF_HOST: host})
                    return self.async_create_entry(
                        title=_title(status), data={CONF_HOST: host}
                    )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_HOST): str}),
            errors=errors,
        )

    async def async_step_zeroconf(
        self, discovery_info: ZeroconfServiceInfo
    ) -> ConfigFlowResult:
        """Handle a plug found via mDNS."""
        host = discovery_info.host
        try:
            status = await self._probe(host)
        except (aiohttp.ClientError, asyncio.TimeoutError):
            return self.async_abort(reason="cannot_connect")
        if not status.get("mac"):
            return self.async_abort(reason="cannot_connect")

        await self.async_set_unique_id(_uid(status["mac"]))
        self._abort_if_unique_id_configured(updates={CONF_HOST: host})

        self._host = host
        self._title = _title(status)
        self.context["title_placeholders"] = {"name": self._title}
        return await self.async_step_zeroconf_confirm()

    async def async_step_zeroconf_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(
                title=self._title, data={CONF_HOST: self._host}
            )
        return self.async_show_form(
            step_id="zeroconf_confirm",
            description_placeholders={"name": self._title},
        )

    async def _probe(self, host: str) -> dict:
        session = async_get_clientsession(self.hass)
        async with asyncio.timeout(HTTP_TIMEOUT):
            resp = await session.get(f"http://{host}/api/status")
            resp.raise_for_status()
            return await resp.json()


def _uid(mac: str) -> str:
    return mac.replace(":", "").lower()


def _title(status: dict) -> str:
    return status.get("name") or f"FireLabs {status.get('model', '')}".strip()
