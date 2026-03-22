"""Tests for ADAM Audio integration __init__.py."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant

from custom_components.adam_audio import _async_reload_entry, async_setup


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


async def test_async_setup_registers_cards(hass: HomeAssistant) -> None:
    """Test async_setup registers static paths and js urls."""
    hass.http = MagicMock()

    result = await async_setup(hass, {})
    assert result is True
    assert hass.http.register_static_path.call_count == 3

    assert "frontend_extra_module_url" in hass.data
    urls = hass.data["frontend_extra_module_url"]
    assert any("adam-audio-card.js" in url for url in urls)
    assert any("adam-audio-backplate-card.js" in url for url in urls)
    assert any("adam-audio-backplate-card-alt.js" in url for url in urls)


async def test_async_reload_entry(hass: HomeAssistant, mock_config_entry) -> None:
    """Test _async_reload_entry triggers config entry reload."""
    mock_config_entry.add_to_hass(hass)

    with patch.object(
        hass.config_entries, "async_reload", new_callable=AsyncMock
    ) as mock_reload:
        await _async_reload_entry(hass, mock_config_entry)
        mock_reload.assert_called_once_with(mock_config_entry.entry_id)


async def test_coordinator_update_failure(
    hass: HomeAssistant, mock_config_entry, mock_client: MagicMock
) -> None:
    """Test coordinator raises UpdateFailed when fetch fails."""
    mock_config_entry.add_to_hass(hass)

    with patch(
        "custom_components.adam_audio.coordinator.AdamAudioClient",
        return_value=mock_client,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    mock_client.async_fetch_state = AsyncMock(return_value=False)

    coordinator = mock_config_entry.runtime_data.coordinator
    await coordinator.async_refresh()
    await hass.async_block_till_done()

    assert coordinator.last_update_success is False
