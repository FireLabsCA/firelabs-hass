"""Config flow for FireLabs."""
from __future__ import annotations

import asyncio
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant.components import webhook
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_HOST
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo

from .const import (
    CONF_LOCATION,
    CONF_QUIET_END,
    CONF_QUIET_START,
    CONF_SLEEP_MIN,
    CONF_WEATHER_ENTITY,
    CONF_WEBHOOK_ID,
    DEFAULT_QUIET_END,
    DEFAULT_QUIET_START,
    DEFAULT_SLEEP_MIN,
    DOMAIN,
    HTTP_TIMEOUT,
    MODEL_WX,
    WX_CURRENT_FIELDS,
)


class FirelabsConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for FireLabs."""

    VERSION = 1

    def __init__(self) -> None:
        self._host: str | None = None
        self._title: str | None = None
        self._status: dict | None = None

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return FirelabsOptionsFlow(config_entry)

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
                        title=_title(status), data=_entry_data(status, host)
                    )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_HOST): str}),
            errors=errors,
        )

    async def async_step_zeroconf(
        self, discovery_info: ZeroconfServiceInfo
    ) -> ConfigFlowResult:
        """Handle a device found via mDNS."""
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
        self._status = status
        self.context["title_placeholders"] = {"name": self._title}
        return await self.async_step_zeroconf_confirm()

    async def async_step_zeroconf_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(
                title=self._title, data=_entry_data(self._status, self._host)
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


class FirelabsOptionsFlow(OptionsFlow):
    """Map HA entities to the weather bundle and set the device's settings."""

    def __init__(self, entry: ConfigEntry) -> None:
        self._entry = entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if self._entry.data.get("model") != MODEL_WX:
            return self.async_abort(reason="no_options")
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        webhook_id = self._entry.data.get(CONF_WEBHOOK_ID)
        url = (
            webhook.async_generate_url(self.hass, webhook_id, allow_external=False)
            if webhook_id
            else ""
        )
        return self.async_show_form(
            step_id="init",
            data_schema=_wx_options_schema(self._entry.options),
            description_placeholders={"webhook_url": url},
        )


def _wx_options_schema(opts: dict) -> vol.Schema:
    def entity(domains: list[str]) -> selector.EntitySelector:
        return selector.EntitySelector(
            selector.EntitySelectorConfig(domain=domains)
        )

    def hour() -> selector.NumberSelector:
        return selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0, max=23, step=1, mode=selector.NumberSelectorMode.BOX
            )
        )

    fields: dict[Any, Any] = {}
    fields[
        vol.Optional(CONF_LOCATION, description={"suggested_value": opts.get(CONF_LOCATION)})
    ] = selector.TextSelector()
    for field, key in WX_CURRENT_FIELDS.items():
        domains = ["sensor", "weather"] if field == "condition" else ["sensor"]
        fields[vol.Optional(key, description={"suggested_value": opts.get(key)})] = entity(domains)

    fields[
        vol.Optional(
            CONF_WEATHER_ENTITY,
            description={"suggested_value": opts.get(CONF_WEATHER_ENTITY)},
        )
    ] = entity(["weather"])

    fields[
        vol.Optional(CONF_SLEEP_MIN, default=opts.get(CONF_SLEEP_MIN, DEFAULT_SLEEP_MIN))
    ] = selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=5, max=240, step=5, mode=selector.NumberSelectorMode.BOX,
            unit_of_measurement="min",
        )
    )
    fields[
        vol.Optional(CONF_QUIET_START, default=opts.get(CONF_QUIET_START, DEFAULT_QUIET_START))
    ] = hour()
    fields[
        vol.Optional(CONF_QUIET_END, default=opts.get(CONF_QUIET_END, DEFAULT_QUIET_END))
    ] = hour()

    return vol.Schema(fields)


def _uid(mac: str) -> str:
    return mac.replace(":", "").lower()


def _title(status: dict) -> str:
    return status.get("name") or f"FireLabs {status.get('model', '')}".strip()


def _entry_data(status: dict, host: str) -> dict:
    data = {
        CONF_HOST: host,
        "mac": status.get("mac"),
        "model": status.get("model"),
        "name": status.get("name"),
        "fw": status.get("fw"),
    }
    if status.get("model") == MODEL_WX:
        data[CONF_WEBHOOK_ID] = webhook.async_generate_id()
    return {k: v for k, v in data.items() if v is not None}
