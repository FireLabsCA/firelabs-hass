"""Sensor entities for FireLabs."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.const import SIGNAL_STRENGTH_DECIBELS_MILLIWATT

from .const import DOMAIN
from .coordinator import FirelabsCoordinator
from .entity import FirelabsEntity


@dataclass(frozen=True, kw_only=True)
class FirelabsSensorDescription(SensorEntityDescription):
    """A sensor description plus how to read its value and whether it needs the meter."""

    value_fn: Callable[[dict], float | int | None]
    needs_meter: bool = False


SENSORS: tuple[FirelabsSensorDescription, ...] = (
    FirelabsSensorDescription(
        key="power",
        name="Power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        suggested_display_precision=1,
        value_fn=lambda d: d.get("power"),
        needs_meter=True,
    ),
    FirelabsSensorDescription(
        key="voltage",
        name="Voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        suggested_display_precision=1,
        value_fn=lambda d: d.get("voltage"),
        needs_meter=True,
    ),
    FirelabsSensorDescription(
        key="current",
        name="Current",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        suggested_display_precision=2,
        value_fn=lambda d: d.get("current"),
        needs_meter=True,
    ),
    FirelabsSensorDescription(
        key="energy",
        name="Energy today",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=3,
        value_fn=lambda d: d.get("energy"),
        needs_meter=True,
    ),
    FirelabsSensorDescription(
        key="rssi",
        name="WiFi signal",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.get("rssi"),
    ),
    FirelabsSensorDescription(
        key="uptime",
        name="Uptime",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.get("uptime"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: FirelabsCoordinator = hass.data[DOMAIN][entry.entry_id]
    data = coordinator.data
    has_meter = bool(data.get("meter"))
    # Only add a sensor if it applies and the device actually reports its field.
    async_add_entities(
        FirelabsSensor(coordinator, desc)
        for desc in SENSORS
        if (has_meter or not desc.needs_meter) and desc.value_fn(data) is not None
    )


class FirelabsSensor(FirelabsEntity, SensorEntity):
    entity_description: FirelabsSensorDescription

    def __init__(
        self, coordinator: FirelabsCoordinator, description: FirelabsSensorDescription
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> float | int | None:
        return self.entity_description.value_fn(self.coordinator.data)
