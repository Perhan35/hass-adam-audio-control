"""Custom types for adam_audio."""

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry

from .client import AdamAudioClient
from .coordinator import AdamAudioCoordinator

type AdamAudioConfigEntry = ConfigEntry[AdamAudioData]


@dataclass
class AdamAudioData:
    """Data for the ADAM Audio integration."""

    client: AdamAudioClient
    coordinator: AdamAudioCoordinator


@dataclass
class AdamAudioIntegrationData:
    """Integration-wide data stored in hass.data[DOMAIN]."""

    coordinators: dict[str, AdamAudioCoordinator]
    # Entry whose platforms own the group entities.
    group_owner_entry_id: str | None = None
