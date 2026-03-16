"""Fixtures for ADAM Audio integration tests."""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.adam_audio.client import AdamAudioState
from custom_components.adam_audio.const import (
    CONF_DESCRIPTION,
    CONF_DEVICE_NAME,
    CONF_HOST,
    CONF_PORT,
    CONF_SERIAL,
    DOMAIN,
)

MOCK_HOST = "192.168.1.100"
MOCK_PORT = 49494
MOCK_DEVICE_NAME = "ASeries-test01"
MOCK_DESCRIPTION = "Left Speaker"
MOCK_SERIAL = "SN-12345"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(
    enable_custom_integrations: None,
) -> None:
    """Enable custom integrations for all tests."""


@pytest.fixture(autouse=True)
def clear_state_leakage() -> None:
    """Clear global state to prevent leakage across tests."""
    from custom_components.adam_audio import _coordinators

    _coordinators.clear()

    import custom_components.adam_audio.switch as switch_mod

    switch_mod._group_switches_added = False

    import custom_components.adam_audio.number as number_mod

    number_mod._group_numbers_added = False

    import custom_components.adam_audio.select as select_mod

    select_mod._group_selects_added = False


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Create a mock config entry."""
    return MockConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title=MOCK_DESCRIPTION,
        data={
            CONF_HOST: MOCK_HOST,
            CONF_PORT: MOCK_PORT,
            CONF_DEVICE_NAME: MOCK_DEVICE_NAME,
            CONF_DESCRIPTION: MOCK_DESCRIPTION,
            CONF_SERIAL: MOCK_SERIAL,
        },
        source="user",
        unique_id=MOCK_SERIAL,
        options={},
        discovery_keys={},
    )


@pytest.fixture
def mock_state() -> AdamAudioState:
    """Create a default mock device state."""
    return AdamAudioState(
        mute=False,
        sleep=False,
        input_source=1,
        voicing=0,
        bass=0,
        desk=0,
        presence=0,
        treble=0,
    )


@pytest.fixture
def mock_client(mock_state: AdamAudioState) -> Generator[MagicMock]:
    """Create a mock AdamAudioClient."""
    with patch(
        "custom_components.adam_audio.coordinator.AdamAudioClient",
        autospec=True,
    ) as mock:
        client = mock.return_value
        client.host = MOCK_HOST
        client.port = MOCK_PORT
        client.available = True
        client.device_name = MOCK_DEVICE_NAME
        client.description = MOCK_DESCRIPTION
        client.serial = MOCK_SERIAL
        client.state = mock_state
        client.async_setup = AsyncMock(return_value=True)
        client.async_shutdown = AsyncMock()
        client.async_fetch_state = AsyncMock(return_value=True)
        client.async_set_mute = AsyncMock()
        client.async_set_sleep = AsyncMock()
        client.async_set_input = AsyncMock()
        client.async_set_voicing = AsyncMock()
        client.async_set_bass = AsyncMock()
        client.async_set_desk = AsyncMock()
        client.async_set_presence = AsyncMock()
        client.async_set_treble = AsyncMock()
        yield client
