"""
Switch platform for ADAM Audio — Mute and Sleep.

Each physical speaker exposes two switches.  A single 'All Speakers' group
switch is also created the first time the platform is loaded; subsequent
config-entry loads skip it because the unique_id is already registered.
"""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, ENTITY_MUTE, ENTITY_SLEEP, GROUP_DEVICE_ID
from .coordinator import AdamAudioCoordinator
from .entity import AdamAudioEntity, AdamAudioGroupEntity

_LOGGER = logging.getLogger(__name__)

_GROUP_SWITCHES_KEY = f"{DOMAIN}_group_switches_added"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: AdamAudioCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[SwitchEntity] = [
        AdamAudioMuteSwitch(coordinator),
        AdamAudioSleepSwitch(coordinator),
    ]

    # Create group entities exactly once per HA lifecycle.
    if not hass.data[DOMAIN].get(_GROUP_SWITCHES_KEY):
        hass.data[DOMAIN][_GROUP_SWITCHES_KEY] = True
        entities += [
            AdamAudioGroupMuteSwitch(hass),
            AdamAudioGroupSleepSwitch(hass),
        ]

    async_add_entities(entities)


# ── Per-device switches ───────────────────────────────────────────────────────


class AdamAudioMuteSwitch(AdamAudioEntity, SwitchEntity):
    """Mute switch for a single speaker."""

    _attr_name = "Mute"
    _attr_icon = "mdi:volume-off"

    def __init__(self, coordinator: AdamAudioCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_{coordinator.device_unique_id}_{ENTITY_MUTE}"

    @property
    def is_on(self) -> bool:
        return self.coordinator.client.state.mute

    @property
    def icon(self) -> str:
        return "mdi:volume-off" if self.is_on else "mdi:volume-high"

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.client.async_set_mute(True)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.client.async_set_mute(False)
        self.async_write_ha_state()


class AdamAudioSleepSwitch(AdamAudioEntity, SwitchEntity):
    """Standby (sleep) switch for a single speaker."""

    _attr_name = "Sleep"
    _attr_icon = "mdi:power-sleep"

    def __init__(self, coordinator: AdamAudioCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_{coordinator.device_unique_id}_{ENTITY_SLEEP}"

    @property
    def is_on(self) -> bool:
        return self.coordinator.client.state.sleep

    @property
    def icon(self) -> str:
        return "mdi:power-sleep" if self.is_on else "mdi:power"

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.client.async_set_sleep(True)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.client.async_set_sleep(False)
        self.async_write_ha_state()


# ── Group switches ────────────────────────────────────────────────────────────


class AdamAudioGroupMuteSwitch(AdamAudioGroupEntity, SwitchEntity):
    """Mute switch that controls ALL speakers simultaneously."""

    _attr_name = "Mute"
    _attr_unique_id = f"{DOMAIN}_{GROUP_DEVICE_ID}_{ENTITY_MUTE}"

    @property
    def icon(self) -> str:
        return "mdi:volume-off" if self.is_on else "mdi:volume-high"

    @property
    def is_on(self) -> bool:
        coordinators = self._coordinators()
        if not coordinators:
            return False
        # Muted if ANY speaker is muted.
        return any(c.client.state.mute for c in coordinators)

    async def async_turn_on(self, **kwargs: Any) -> None:
        for coordinator in self._coordinators():
            await coordinator.client.async_set_mute(True)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        for coordinator in self._coordinators():
            await coordinator.client.async_set_mute(False)
        self.async_write_ha_state()


class AdamAudioGroupSleepSwitch(AdamAudioGroupEntity, SwitchEntity):
    """Sleep switch that controls ALL speakers simultaneously."""

    _attr_name = "Sleep"
    _attr_unique_id = f"{DOMAIN}_{GROUP_DEVICE_ID}_{ENTITY_SLEEP}"

    @property
    def icon(self) -> str:
        return "mdi:power-sleep" if self.is_on else "mdi:power"

    @property
    def is_on(self) -> bool:
        coordinators = self._coordinators()
        if not coordinators:
            return False
        return any(c.client.state.sleep for c in coordinators)

    async def async_turn_on(self, **kwargs: Any) -> None:
        for coordinator in self._coordinators():
            await coordinator.client.async_set_sleep(True)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        for coordinator in self._coordinators():
            await coordinator.client.async_set_sleep(False)
        self.async_write_ha_state()
