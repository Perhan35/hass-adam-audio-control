"""Diagnostics for ADAM Audio."""

from dataclasses import asdict
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant

from .const import CONF_DEVICE_NAME, CONF_SERIAL, POLL_INTERVAL
from .data import AdamAudioConfigEntry

# The hardware name embeds a per-unit identifier (e.g. "ASeries-41472b").
TO_REDACT = {CONF_DEVICE_NAME, CONF_HOST, CONF_SERIAL}


async def async_get_config_entry_diagnostics(
    _hass: HomeAssistant, entry: AdamAudioConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data.coordinator
    client = coordinator.client
    return {
        "entry": async_redact_data(dict(entry.data), TO_REDACT),
        "state": asdict(client.state),
        "available": client.available,
        "consecutive_poll_failures": client.consecutive_poll_failures,
        "last_update_success": coordinator.last_update_success,
        "poll_interval_seconds": POLL_INTERVAL,
    }
