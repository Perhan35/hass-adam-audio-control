"""Tests for ADAM Audio client."""

from unittest.mock import MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant

from custom_components.adam_audio.client import AdamAudioClient


@pytest.fixture
def adam_client(hass: HomeAssistant) -> AdamAudioClient:
    """Fixture for client."""
    client = AdamAudioClient(hass, "192.168.1.100", 49494)
    client._device = MagicMock()
    return client


async def test_client_fetch_state(adam_client: AdamAudioClient) -> None:
    """Test fetching all states from device."""
    # Mock the batched fetch call
    pdus = []
    for val in [5, 1, 1, 2, 1, 0, -1, 0]:
        param = MagicMock()
        param.value = val
        pdu = MagicMock()
        pdu.params = [param]
        pdus.append(pdu)

    adam_client._device.get_full_state_pdus.return_value = pdus

    # Test
    success = await adam_client.async_fetch_state()
    assert success is True

    assert adam_client.state.mute is True
    assert adam_client.state.sleep is True
    assert adam_client.state.input_source == 1
    assert adam_client.state.voicing == 2
    assert adam_client.state.bass == 1
    assert adam_client.state.desk == 0
    assert adam_client.state.presence == -1
    assert adam_client.state.treble == 0


async def test_client_fetch_state_failure(adam_client: AdamAudioClient) -> None:
    """Test fetching state failures."""
    adam_client._device.get_full_state_pdus.side_effect = TimeoutError("timeout")

    success = await adam_client.async_fetch_state()
    assert success is False
    assert adam_client.available is False


async def test_client_setters(adam_client: AdamAudioClient) -> None:
    """Test state setters."""
    # Call
    adam_client._device.get_mute.return_value = True
    await adam_client.async_set_mute(True)
    adam_client._device.set_mute.assert_called_once_with(True)
    assert adam_client.state.mute is True

    adam_client._device.get_sleep.return_value = False
    await adam_client.async_set_sleep(False)
    adam_client._device.set_sleep.assert_called_once_with(False)
    assert adam_client.state.sleep is False

    adam_client._device.get_input.return_value = 1
    await adam_client.async_set_input(1)
    adam_client._device.set_input.assert_called_once_with(1)
    assert adam_client.state.input_source == 1

    adam_client._device.get_voicing.return_value = 2
    await adam_client.async_set_voicing(2)
    adam_client._device.set_voicing.assert_called_once_with(2)
    assert adam_client.state.voicing == 2

    adam_client._device.get_bass.return_value = 1
    await adam_client.async_set_bass(1)
    adam_client._device.set_bass.assert_called_once_with(1)
    assert adam_client.state.bass == 1

    adam_client._device.get_desk.return_value = -1
    await adam_client.async_set_desk(-1)
    adam_client._device.set_desk.assert_called_once_with(-1)
    assert adam_client.state.desk == -1

    adam_client._device.get_presence.return_value = 0
    await adam_client.async_set_presence(0)
    adam_client._device.set_presence.assert_called_once_with(0)
    assert adam_client.state.presence == 0

    adam_client._device.get_treble.return_value = 1
    await adam_client.async_set_treble(1)
    adam_client._device.set_treble.assert_called_once_with(1)
    assert adam_client.state.treble == 1


async def test_client_setup_shutdown(hass: HomeAssistant) -> None:
    """Test client connection logic."""
    client = AdamAudioClient(hass, "192.168.1.100", 49494)

    with patch("custom_components.adam_audio.client.Device") as mock_device_cls:
        mock_dev = mock_device_cls.from_address.return_value
        mock_dev.get_name.return_value = "A7V"
        mock_dev.get_description.return_value = "Left"

        success = await client.async_setup()

        assert success is True
        assert client.device_name == "A7V"
        assert client.description == "Left"

        await client.async_shutdown()
        mock_dev.close.assert_called_once()


async def test_client_setup_failure(hass: HomeAssistant) -> None:
    """Test client connection logic on failure."""
    client = AdamAudioClient(hass, "192.168.1.100", 49494)

    with patch("custom_components.adam_audio.client.Device") as mock_device_cls:
        mock_device_cls.from_address.side_effect = OSError("Connection refused")
        success = await client.async_setup()
        assert success is False
        assert client.available is False


async def test_client_fetch_state_short_responses(adam_client: AdamAudioClient) -> None:
    """Test fetch state handles < 8 responses properly."""
    adam_client._device.get_full_state_pdus.return_value = [MagicMock()]
    success = await adam_client.async_fetch_state()
    assert success is False
    assert adam_client.available is False


async def test_client_setters_max_retries_fail(adam_client: AdamAudioClient) -> None:
    """Test setters raise exception after MAX_RETRIES."""
    adam_client._device.get_mute.return_value = (
        False  # won't match True -> fails verification
    )
    adam_client._device.set_mute.side_effect = OSError("Socket dead")
    adam_client._device.set_mute.__name__ = "set_mute"
    adam_client._device.get_mute.__name__ = "get_mute"

    from homeassistant.exceptions import HomeAssistantError

    with pytest.raises(HomeAssistantError):
        await adam_client.async_set_mute(True)
    assert adam_client._device.set_mute.call_count == 3
