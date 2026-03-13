"""
Number platform for ADAM Audio — EQ controls.

EQ controls (Bass, Desk, Presence, Treble) use integer dB steps.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Callable

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .client import AdamAudioClient, AdamAudioState
from .const import (
    BASS_MAX,
    BASS_MIN,
    DESK_MAX,
    DESK_MIN,
    DOMAIN,
    ENTITY_BASS,
    ENTITY_DESK,
    ENTITY_PRESENCE,
    ENTITY_TREBLE,
    EQ_STEP,
    EQ_UNIT,
    GROUP_DEVICE_ID,
    PRESENCE_MAX,
    PRESENCE_MIN,
    TREBLE_MAX,
    TREBLE_MIN,
)
from .coordinator import AdamAudioCoordinator
from .entity import AdamAudioEntity, AdamAudioGroupEntity

_LOGGER = logging.getLogger(__name__)

_GROUP_NUMBERS_KEY = f"{DOMAIN}_group_numbers_added"


# ── Entity descriptors ────────────────────────────────────────────────────────


@dataclass(frozen=True)
class _NumberDesc:
    key: str
    name: str
    icon: str
    native_min: float
    native_max: float
    native_step: float
    native_unit: str
    state_getter: Callable[[AdamAudioState], float]
    # Async setter signature: async_set_XXX(value)
    setter_name: str
    # Voicing modes where this control is active (None = always available)
    valid_voicings: tuple[int, ...] | None = None


_NUMBER_DESCRIPTORS: tuple[_NumberDesc, ...] = (
    _NumberDesc(
        key=ENTITY_BASS,
        name="Bass",
        icon="mdi:equalizer",
        native_min=BASS_MIN,
        native_max=BASS_MAX,
        native_step=EQ_STEP,
        native_unit=EQ_UNIT,
        state_getter=lambda s: float(s.bass),
        setter_name="async_set_bass",
        valid_voicings=(0, 1),  # Pure, UNR
    ),
    _NumberDesc(
        key=ENTITY_DESK,
        name="Desk",
        icon="mdi:tune-vertical",
        native_min=DESK_MIN,
        native_max=DESK_MAX,
        native_step=EQ_STEP,
        native_unit=EQ_UNIT,
        state_getter=lambda s: float(s.desk),
        setter_name="async_set_desk",
        valid_voicings=(0, 1),  # Pure, UNR
    ),
    _NumberDesc(
        key=ENTITY_PRESENCE,
        name="Presence",
        icon="mdi:tune",
        native_min=PRESENCE_MIN,
        native_max=PRESENCE_MAX,
        native_step=EQ_STEP,
        native_unit=EQ_UNIT,
        state_getter=lambda s: float(s.presence),
        setter_name="async_set_presence",
        valid_voicings=(0, 1),  # Pure, UNR
    ),
    _NumberDesc(
        key=ENTITY_TREBLE,
        name="Treble",
        icon="mdi:tune-vertical-variant",
        native_min=TREBLE_MIN,
        native_max=TREBLE_MAX,
        native_step=EQ_STEP,
        native_unit=EQ_UNIT,
        state_getter=lambda s: float(s.treble),
        setter_name="async_set_treble",
        valid_voicings=(0, 1),  # Pure, UNR
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: AdamAudioCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[NumberEntity] = [
        AdamAudioNumber(coordinator, desc) for desc in _NUMBER_DESCRIPTORS
    ]

    if not hass.data[DOMAIN].get(_GROUP_NUMBERS_KEY):
        hass.data[DOMAIN][_GROUP_NUMBERS_KEY] = True
        entities += [
            AdamAudioGroupNumber(hass, desc) for desc in _NUMBER_DESCRIPTORS
        ]

    async_add_entities(entities)


# ── Per-device number ─────────────────────────────────────────────────────────


class AdamAudioNumber(AdamAudioEntity, NumberEntity):
    """Number entity for a single speaker."""

    _attr_mode = NumberMode.SLIDER

    def __init__(self, coordinator: AdamAudioCoordinator, desc: _NumberDesc) -> None:
        super().__init__(coordinator)
        self._desc = desc
        self._attr_unique_id = f"{DOMAIN}_{coordinator.device_unique_id}_{desc.key}"
        self._attr_name = desc.name
        self._attr_icon = desc.icon
        self._attr_native_min_value = desc.native_min
        self._attr_native_max_value = desc.native_max
        self._attr_native_step = desc.native_step
        self._attr_native_unit_of_measurement = desc.native_unit

    @property
    def available(self) -> bool:
        if not super().available:
            return False
        if self._desc.valid_voicings is not None:
            return self.coordinator.client.state.voicing in self._desc.valid_voicings
        return True

    @property
    def native_value(self) -> float:
        return self._desc.state_getter(self.coordinator.client.state)

    async def async_set_native_value(self, value: float) -> None:
        setter = getattr(self.coordinator.client, self._desc.setter_name)
        # EQ controls expect int; volume expects float
        if self._desc.native_step == 1.0:
            value = int(value)
        await setter(value)
        self.async_write_ha_state()


# ── Group number ──────────────────────────────────────────────────────────────


class AdamAudioGroupNumber(AdamAudioGroupEntity, NumberEntity):
    """Number entity that controls ALL speakers simultaneously."""

    _attr_mode = NumberMode.SLIDER

    def __init__(self, hass: HomeAssistant, desc: _NumberDesc) -> None:
        super().__init__(hass)
        self._desc = desc
        self._attr_unique_id = f"{DOMAIN}_{GROUP_DEVICE_ID}_{desc.key}"
        self._attr_name = desc.name
        self._attr_icon = desc.icon
        self._attr_native_min_value = desc.native_min
        self._attr_native_max_value = desc.native_max
        self._attr_native_step = desc.native_step
        self._attr_native_unit_of_measurement = desc.native_unit

    @property
    def available(self) -> bool:
        if not super().available:
            return False
        if self._desc.valid_voicings is not None:
            return any(
                c.client.state.voicing in self._desc.valid_voicings
                for c in self._coordinators()
            )
        return True

    @property
    def native_value(self) -> float:
        """Return the average across all speakers."""
        coordinators = self._coordinators()
        if not coordinators:
            return self._desc.native_min
        values = [self._desc.state_getter(c.client.state) for c in coordinators]
        return round(sum(values) / len(values), 1)

    async def async_set_native_value(self, value: float) -> None:
        if self._desc.native_step == 1.0:
            value = int(value)
        coordinators = self._coordinators()
        await asyncio.gather(*(
            getattr(c.client, self._desc.setter_name)(value) for c in coordinators
        ))
        # Push the optimistic state to all per-speaker entities instantly
        for c in coordinators:
            c.async_set_updated_data(c.client.state)
        self.async_write_ha_state()
