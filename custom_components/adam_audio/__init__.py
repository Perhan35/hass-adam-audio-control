"""ADAM Audio Home Assistant Integration.

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

from homeassistant.const import Platform
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN, LOGGER
from .coordinator import AdamAudioCoordinator
from .data import AdamAudioData, AdamAudioIntegrationData

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.typing import ConfigType

    from .data import AdamAudioConfigEntry

_WWW_DIR = Path(__file__).parent / "www"

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

PLATFORMS: list[Platform] = [
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SWITCH,
]


async def async_setup(hass: HomeAssistant, _config: ConfigType) -> bool:
    """Register Lovelace cards if present (HACS install only)."""
    # Initialize integration-wide data in hass.data[DOMAIN]
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = AdamAudioIntegrationData(coordinators={})

    if not _WWW_DIR.is_dir():
        return True

    from homeassistant.components.frontend import add_extra_js_url  # noqa: PLC0415

    card_url = "/adam_audio/adam-audio-card.js"
    card_js = str(_WWW_DIR / "adam-audio-card.js")

    backplate_url = "/adam_audio/adam-audio-backplate-card.js"
    backplate_js = str(_WWW_DIR / "adam-audio-backplate-card.js")

    backplate_alt_url = "/adam_audio/adam-audio-backplate-card-alt.js"
    backplate_alt_js = str(_WWW_DIR / "adam-audio-backplate-card-alt.js")

    if hasattr(hass, "http") and hass.http is not None:
        try:
            hass.http.register_static_path(card_url, card_js, cache_headers=False)
            hass.http.register_static_path(
                backplate_url, backplate_js, cache_headers=False
            )
            hass.http.register_static_path(
                backplate_alt_url, backplate_alt_js, cache_headers=False
            )
        except AttributeError:
            # Fallback for newer Home Assistant versions
            from homeassistant.components.http import StaticPathConfig  # noqa: PLC0415

            await hass.http.async_register_static_paths(
                [
                    StaticPathConfig(card_url, card_js, cache_headers=False),
                    StaticPathConfig(backplate_url, backplate_js, cache_headers=False),
                    StaticPathConfig(
                        backplate_alt_url, backplate_alt_js, cache_headers=False
                    ),
                ]
            )

    if "frontend_extra_module_url" not in hass.data:
        hass.data["frontend_extra_module_url"] = set()

    add_extra_js_url(hass, card_url)
    add_extra_js_url(hass, backplate_url)
    add_extra_js_url(hass, backplate_alt_url)

    return True


def get_coordinators(hass: HomeAssistant) -> list[AdamAudioCoordinator]:
    """Return all currently loaded ADAM Audio coordinators."""
    data: AdamAudioIntegrationData | None = hass.data.get(DOMAIN)
    if not data:
        return []
    return list(data.coordinators.values())


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

    # Ensure integration-wide state exists (especially for tests)
    integration_data = hass.data.setdefault(
        DOMAIN, AdamAudioIntegrationData(coordinators={})
    )
    integration_data.coordinators[entry.entry_id] = coordinator

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
        # Integration data might missing if async_setup was skipped (e.g. tests)
        integration_data: AdamAudioIntegrationData | None = hass.data.get(DOMAIN)
        if integration_data:
            coordinator = integration_data.coordinators.pop(entry.entry_id, None)
            if coordinator:
                await coordinator.async_shutdown()

            LOGGER.debug(
                "Unloaded entry %s; %d coordinators remaining",
                entry.entry_id,
                len(integration_data.coordinators),
            )
        else:
            LOGGER.debug("Skipping coordinator cleanup (domain data missing)")

    return unload_ok


async def _async_reload_entry(
    hass: HomeAssistant,
    entry: AdamAudioConfigEntry,
) -> None:
    """Reload entry after options update."""
    await hass.config_entries.async_reload(entry.entry_id)
