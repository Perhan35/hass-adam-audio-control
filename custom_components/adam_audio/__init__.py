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

from pathlib import Path
from typing import TYPE_CHECKING

import homeassistant.helpers.config_validation as cv
from homeassistant.const import Platform

from .const import (
    DOMAIN,
    LOGGER,
)
from .coordinator import AdamAudioCoordinator
from .data import AdamAudioData

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.typing import ConfigType

    from .data import AdamAudioConfigEntry

_CARD_URL = "/adam_audio/adam-audio-card.js"
_CARD_JS = Path(__file__).parent / "www" / "adam-audio-card.js"

_BACKPLATE_URL = "/adam_audio/backplate-card.js"
_BACKPLATE_JS = Path(__file__).parent / "www" / "backplate-card.js"

_BACKPLATE_2_URL = "/adam_audio/adam-audio-backplate-card.js"
_BACKPLATE_2_JS = Path(__file__).parent / "www" / "adam-audio-backplate-card.js"

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

PLATFORMS: list[Platform] = [
    Platform.SWITCH,
    Platform.SELECT,
    Platform.NUMBER,
]


async def async_setup(hass: HomeAssistant, _config: ConfigType) -> bool:
    """Register the Lovelace card as a frontend resource."""
    from homeassistant.components.frontend import add_extra_js_url

    if hasattr(hass, "http") and hass.http is not None:
        try:
            hass.http.register_static_path(
                _CARD_URL, str(_CARD_JS), cache_headers=False
            )
            hass.http.register_static_path(
                _BACKPLATE_URL, str(_BACKPLATE_JS), cache_headers=False
            )
            hass.http.register_static_path(
                _BACKPLATE_2_URL, str(_BACKPLATE_2_JS), cache_headers=False
            )
        except AttributeError:
            # Fallback for newer Home Assistant versions
            from homeassistant.components.http import StaticPathConfig

            await hass.http.async_register_static_paths(
                [
                    StaticPathConfig(_CARD_URL, str(_CARD_JS), cache_headers=False),
                    StaticPathConfig(
                        _BACKPLATE_URL, str(_BACKPLATE_JS), cache_headers=False
                    ),
                    StaticPathConfig(
                        _BACKPLATE_2_URL, str(_BACKPLATE_2_JS), cache_headers=False
                    ),
                ]
            )

    if "frontend_extra_module_url" not in hass.data:
        hass.data["frontend_extra_module_url"] = set()

    add_extra_js_url(hass, _CARD_URL)
    add_extra_js_url(hass, _BACKPLATE_URL)
    add_extra_js_url(hass, _BACKPLATE_2_URL)

    return True


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
