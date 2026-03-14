"""
ADAM Audio Home Assistant Integration.

Supports ADAM Audio A-Series studio monitors via AES70/OCA over UDP.
Auto-discovers speakers via mDNS (_oca._udp.local.) and also accepts
manually configured IP addresses as a fallback.

Each physical speaker becomes an HA Device with Switch, Select, and Number
child entities.  A virtual 'All Speakers' group device is automatically
created to control all speakers simultaneously.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.const import Platform

from .const import DOMAIN as DOMAIN
from .const import LOGGER
from .coordinator import AdamAudioCoordinator
from .data import AdamAudioData

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .data import AdamAudioConfigEntry

PLATFORMS: list[Platform] = [
    Platform.SWITCH,
    Platform.SELECT,
    Platform.NUMBER,
]


def get_coordinators() -> list[AdamAudioCoordinator]:
    """Return all currently loaded ADAM Audio coordinators."""
    return list(_coordinators.values()) if _coordinators else []


# Module-level registry of coordinators, keyed by config entry ID.
# This replaces hass.data[DOMAIN] for coordinator storage and is used
# by group entities to locate all active device coordinators.
_coordinators: dict[str, AdamAudioCoordinator] = {}


# https://developers.home-assistant.io/docs/config_entries_index/#setting-up-an-entry
async def async_setup_entry(
    hass: HomeAssistant,
    entry: AdamAudioConfigEntry,
) -> bool:
    """Set up ADAM Audio from a config entry (one entry = one physical speaker)."""
    coordinator = AdamAudioCoordinator(hass, entry)
    await coordinator.async_setup()  # raises ConfigEntryNotReady if unreachable

    entry.runtime_data = AdamAudioData(
        client=coordinator.client,
        coordinator=coordinator,
    )

    _coordinators[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Re-run setup if the entry's options are updated (e.g., host changed).
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: AdamAudioConfigEntry,
) -> bool:
    """Unload a config entry cleanly."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator = _coordinators.pop(entry.entry_id, None)
        if coordinator:
            await coordinator.async_shutdown()

        LOGGER.debug(
            "Unloaded entry %s; %d coordinators remaining",
            entry.entry_id,
            len(_coordinators),
        )

    return unload_ok


async def _async_reload_entry(
    hass: HomeAssistant,
    entry: AdamAudioConfigEntry,
) -> None:
    """Reload entry after options update."""
    await hass.config_entries.async_reload(entry.entry_id)
