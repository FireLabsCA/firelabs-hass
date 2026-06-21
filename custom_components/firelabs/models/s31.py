"""Entities for the FireLabs S31 / S31 Lite smart plug.

One module per device model. To add a new FireLabs device, create a sibling
module and register it in models/__init__.py; it exposes builder functions named
after the HA platform (switches, sensors, binary_sensors, selects, buttons,
lights, numbers, texts) returning that platform's entities.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.components.button import ButtonDeviceClass, ButtonEntity
from homeassistant.components.select import SelectEntity
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.components.switch import SwitchEntity
from homeassistant.const import (
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    EntityCategory,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTime,
)

from ..coordinator import FirelabsCoordinator
from ..entity import FirelabsEntity

RESTORE_OPTIONS = ["Off", "On", "Last"]  # matches Config::RestoreMode in firmware


# ---------- switches ----------

class RelaySwitch(FirelabsEntity, SwitchEntity):
    _attr_name = None  # primary feature; takes the device name
    _attr_icon = "mdi:power-socket-us"

    def __init__(self, coordinator: FirelabsCoordinator) -> None:
        super().__init__(coordinator, "relay")

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.data.get("relay"))

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_command("/api/relay", {"on": True})

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_command("/api/relay", {"on": False})


class NoLoadSwitch(FirelabsEntity, SwitchEntity):
    _attr_name = "No-load indicator"
    _attr_icon = "mdi:led-on"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: FirelabsCoordinator) -> None:
        super().__init__(coordinator, "noload")

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.data.get("noload"))

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_command("/api/config", {"noload": True})

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_command("/api/config", {"noload": False})


class IdentifySwitch(FirelabsEntity, SwitchEntity):
    _attr_name = "Identify"
    _attr_icon = "mdi:map-marker-radius"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: FirelabsCoordinator) -> None:
        super().__init__(coordinator, "identify")

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.data.get("identify"))

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_command("/api/identify", {"on": True})

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_command("/api/identify", {"on": False})


# ---------- sensors ----------

@dataclass(frozen=True, kw_only=True)
class S31SensorDescription(SensorEntityDescription):
    value_fn: Callable[[dict], float | int | None]
    needs_meter: bool = False


SENSORS: tuple[S31SensorDescription, ...] = (
    S31SensorDescription(
        key="power", name="Power",
        device_class=SensorDeviceClass.POWER, state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT, suggested_display_precision=1,
        value_fn=lambda d: d.get("power"), needs_meter=True,
    ),
    S31SensorDescription(
        key="voltage", name="Voltage",
        device_class=SensorDeviceClass.VOLTAGE, state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT, suggested_display_precision=1,
        value_fn=lambda d: d.get("voltage"), needs_meter=True,
    ),
    S31SensorDescription(
        key="current", name="Current",
        device_class=SensorDeviceClass.CURRENT, state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE, suggested_display_precision=2,
        value_fn=lambda d: d.get("current"), needs_meter=True,
    ),
    S31SensorDescription(
        key="energy", name="Energy today",
        device_class=SensorDeviceClass.ENERGY, state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR, suggested_display_precision=3,
        value_fn=lambda d: d.get("energy"), needs_meter=True,
    ),
    S31SensorDescription(
        key="rssi", name="WiFi signal",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH, state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        entity_category=EntityCategory.DIAGNOSTIC, entity_registry_enabled_default=False,
        value_fn=lambda d: d.get("rssi"),
    ),
    S31SensorDescription(
        key="uptime", name="Uptime",
        device_class=SensorDeviceClass.DURATION, native_unit_of_measurement=UnitOfTime.SECONDS,
        entity_category=EntityCategory.DIAGNOSTIC, entity_registry_enabled_default=False,
        value_fn=lambda d: d.get("uptime"),
    ),
)


class S31Sensor(FirelabsEntity, SensorEntity):
    entity_description: S31SensorDescription

    def __init__(self, coordinator: FirelabsCoordinator, description: S31SensorDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> float | int | None:
        return self.entity_description.value_fn(self.coordinator.data)


# ---------- binary sensor ----------

class FaultBinarySensor(FirelabsEntity, BinarySensorEntity):
    _attr_name = "Fault"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, coordinator: FirelabsCoordinator) -> None:
        super().__init__(coordinator, "fault")

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.data.get("fault"))


# ---------- select ----------

class RestoreModeSelect(FirelabsEntity, SelectEntity):
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


# ---------- button ----------

class RestartButton(FirelabsEntity, ButtonEntity):
    _attr_name = "Restart"
    _attr_device_class = ButtonDeviceClass.RESTART
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: FirelabsCoordinator) -> None:
        super().__init__(coordinator, "restart")

    async def async_press(self) -> None:
        await self.coordinator.async_command("/api/restart", {})


# ---------- per-platform builders ----------

def switches(coordinator: FirelabsCoordinator) -> list[SwitchEntity]:
    data = coordinator.data
    out: list[SwitchEntity] = [RelaySwitch(coordinator), IdentifySwitch(coordinator)]
    if data.get("meter"):
        out.append(NoLoadSwitch(coordinator))
    return out


def sensors(coordinator: FirelabsCoordinator) -> list[SensorEntity]:
    data = coordinator.data
    has_meter = bool(data.get("meter"))
    return [
        S31Sensor(coordinator, d)
        for d in SENSORS
        if (has_meter or not d.needs_meter) and d.value_fn(data) is not None
    ]


def binary_sensors(coordinator: FirelabsCoordinator) -> list[BinarySensorEntity]:
    return [FaultBinarySensor(coordinator)] if coordinator.data.get("meter") else []


def selects(coordinator: FirelabsCoordinator) -> list[SelectEntity]:
    return [RestoreModeSelect(coordinator)]


def buttons(coordinator: FirelabsCoordinator) -> list[ButtonEntity]:
    return [RestartButton(coordinator)]
