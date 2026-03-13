"""
Select platform for ADAM Audio — Input Source and Voicing.

Each physical speaker exposes two selects; one 'All Speakers' group select
for each is created once.
"""
from __future__ import annotations

import asyncio
import logging

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    ENTITY_INPUT,
    ENTITY_VOICING,
    GROUP_DEVICE_ID,
    INPUT_FROM_INT,
    INPUT_OPTIONS,
    INPUT_TO_INT,
    VOICING_FROM_INT,
    VOICING_OPTIONS,
    VOICING_TO_INT,
)
from .coordinator import AdamAudioCoordinator
from .entity import AdamAudioEntity, AdamAudioGroupEntity

_LOGGER = logging.getLogger(__name__)

_GROUP_SELECTS_KEY = f"{DOMAIN}_group_selects_added"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: AdamAudioCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[SelectEntity] = [
        AdamAudioInputSelect(coordinator),
        AdamAudioVoicingSelect(coordinator),
    ]

    if not hass.data[DOMAIN].get(_GROUP_SELECTS_KEY):
        hass.data[DOMAIN][_GROUP_SELECTS_KEY] = True
        entities += [
            AdamAudioGroupInputSelect(hass),
            AdamAudioGroupVoicingSelect(hass),
        ]

    async_add_entities(entities)


# ── Per-device selects ────────────────────────────────────────────────────────


class AdamAudioInputSelect(AdamAudioEntity, SelectEntity):
    """Input source selector for a single speaker (RCA / XLR)."""

    _attr_name = "Input Source"
    _attr_icon = "mdi:import"
    _attr_options = INPUT_OPTIONS

    def __init__(self, coordinator: AdamAudioCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_{coordinator.device_unique_id}_{ENTITY_INPUT}"

    @property
    def current_option(self) -> str:
        return INPUT_FROM_INT.get(self.coordinator.client.state.input_source, "XLR")

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.client.async_set_input(INPUT_TO_INT[option])
        self.async_write_ha_state()


class AdamAudioVoicingSelect(AdamAudioEntity, SelectEntity):
    """Voicing selector for a single speaker (Pure / UNR / Ext)."""

    _attr_name = "Voicing"
    _attr_icon = "mdi:equalizer-outline"
    _attr_options = VOICING_OPTIONS

    def __init__(self, coordinator: AdamAudioCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_{coordinator.device_unique_id}_{ENTITY_VOICING}"

    @property
    def current_option(self) -> str:
        return VOICING_FROM_INT.get(self.coordinator.client.state.voicing, "Pure")

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.client.async_set_voicing(VOICING_TO_INT[option])
        self.async_write_ha_state()


# ── Group selects ─────────────────────────────────────────────────────────────


class AdamAudioGroupInputSelect(AdamAudioGroupEntity, SelectEntity):
    """Input source selector that controls ALL speakers."""

    _attr_name = "Input Source"
    _attr_icon = "mdi:import"
    _attr_options = INPUT_OPTIONS
    _attr_unique_id = f"{DOMAIN}_{GROUP_DEVICE_ID}_{ENTITY_INPUT}"

    @property
    def current_option(self) -> str:
        coordinators = self._coordinators()
        if not coordinators:
            return INPUT_OPTIONS[0]
        # Show common value if all speakers agree, otherwise the first one.
        values = {c.client.state.input_source for c in coordinators}
        raw = next(iter(values)) if len(values) == 1 else coordinators[0].client.state.input_source
        return INPUT_FROM_INT.get(raw, "XLR")

    async def async_select_option(self, option: str) -> None:
        value = INPUT_TO_INT[option]
        coordinators = self._coordinators()
        await asyncio.gather(*(
            c.client.async_set_input(value) for c in coordinators
        ))
        for c in coordinators:
            c.async_set_updated_data(c.client.state)
        self.async_write_ha_state()


class AdamAudioGroupVoicingSelect(AdamAudioGroupEntity, SelectEntity):
    """Voicing selector that controls ALL speakers."""

    _attr_name = "Voicing"
    _attr_icon = "mdi:equalizer-outline"
    _attr_options = VOICING_OPTIONS
    _attr_unique_id = f"{DOMAIN}_{GROUP_DEVICE_ID}_{ENTITY_VOICING}"

    @property
    def current_option(self) -> str:
        coordinators = self._coordinators()
        if not coordinators:
            return VOICING_OPTIONS[0]
        values = {c.client.state.voicing for c in coordinators}
        raw = next(iter(values)) if len(values) == 1 else coordinators[0].client.state.voicing
        return VOICING_FROM_INT.get(raw, "Pure")

    async def async_select_option(self, option: str) -> None:
        value = VOICING_TO_INT[option]
        coordinators = self._coordinators()
        await asyncio.gather(*(
            c.client.async_set_voicing(value) for c in coordinators
        ))
        for c in coordinators:
            c.async_set_updated_data(c.client.state)
        self.async_write_ha_state()
