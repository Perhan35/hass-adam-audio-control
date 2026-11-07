"""Tests for ADAM Audio diagnostics."""

from unittest.mock import MagicMock

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.adam_audio.diagnostics import async_get_config_entry_diagnostics
from homeassistant.const import CONF_DESCRIPTION, CONF_HOST
from homeassistant.core import HomeAssistant
from tests.conftest import MOCK_DESCRIPTION, MOCK_DEVICE_NAME, MOCK_HOST, MOCK_SERIAL


async def test_diagnostics(
    hass: HomeAssistant, mock_client: MagicMock, mock_config_entry: MockConfigEntry
) -> None:
    """Test diagnostics report the state and hide what identifies the speaker."""
    mock_client.state.bass = -1
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    result = await async_get_config_entry_diagnostics(hass, mock_config_entry)

    assert result["state"]["bass"] == -1
    assert result["available"] is True
    assert result["consecutive_poll_failures"] == 0
    assert result["last_update_success"] is True
    assert result["poll_interval_seconds"] == 15
    assert result["entry"][CONF_HOST] == "**REDACTED**"
    assert result["entry"][CONF_DESCRIPTION] == MOCK_DESCRIPTION
    dumped = str(result)
    assert MOCK_HOST not in dumped
    assert MOCK_SERIAL not in dumped
    assert MOCK_DEVICE_NAME not in dumped
