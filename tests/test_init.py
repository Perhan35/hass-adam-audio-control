"""Tests for ADAM Audio integration __init__.py."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant


async def test_setup_entry(
    hass: HomeAssistant,
    mock_config_entry,
    mock_client: MagicMock,
) -> None:
    """Test successful setup of a config entry."""
    mock_config_entry.add_to_hass(hass)

    with patch(
        "custom_components.adam_audio.coordinator.AdamAudioClient",
        return_value=mock_client,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.LOADED
    assert mock_config_entry.runtime_data is not None
    assert mock_config_entry.runtime_data.coordinator is not None


async def test_setup_entry_connection_failure(
    hass: HomeAssistant,
    mock_config_entry,
    mock_client: MagicMock,
) -> None:
    """Test setup failure when device is unreachable."""
    mock_client.async_setup = AsyncMock(return_value=False)
    mock_config_entry.add_to_hass(hass)

    with patch(
        "custom_components.adam_audio.coordinator.AdamAudioClient",
        return_value=mock_client,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_unload_entry(
    hass: HomeAssistant,
    mock_config_entry,
    mock_client: MagicMock,
) -> None:
    """Test successful unload of a config entry."""
    mock_config_entry.add_to_hass(hass)

    with patch(
        "custom_components.adam_audio.coordinator.AdamAudioClient",
        return_value=mock_client,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.LOADED

    await hass.config_entries.async_unload(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.NOT_LOADED
