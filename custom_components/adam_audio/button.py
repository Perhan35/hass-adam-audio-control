"""Button platform for ADAM Audio — Identify.

Each physical speaker exposes one button.  There is no group button: the point
is to tell the speakers apart.
"""

from typing import override

from homeassistant.components.button import ButtonDeviceClass, ButtonEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN, ENTITY_IDENTIFY
from .coordinator import AdamAudioCoordinator
from .data import AdamAudioConfigEntry
from .entity import AdamAudioEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: AdamAudioConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the button platform."""
    async_add_entities([AdamAudioIdentifyButton(entry.runtime_data.coordinator)])


class AdamAudioIdentifyButton(AdamAudioEntity, ButtonEntity):
    """Blink a speaker's LED so it can be recognised."""

    _attr_device_class = ButtonDeviceClass.IDENTIFY
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: AdamAudioCoordinator) -> None:
        """Initialize the identify button."""
        super().__init__(coordinator)
        self._attr_unique_id = (
            # pylint: disable-next=home-assistant-entity-unique-id-redundant-domain
            f"{DOMAIN}_{coordinator.entity_unique_id_base}_{ENTITY_IDENTIFY}"
        )

    @override
    async def async_press(self) -> None:
        """Blink the speaker's LED."""
        await self.coordinator.client.async_identify()
