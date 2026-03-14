"""Tests for ADAM Audio config flow."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.adam_audio.const import (
    CONF_HOST,
    CONF_PORT,
    DOMAIN,
)
from tests.conftest import (
    MOCK_DESCRIPTION,
    MOCK_DEVICE_NAME,
    MOCK_HOST,
    MOCK_PORT,
    MOCK_SERIAL,
)


async def test_user_flow_success(hass: HomeAssistant) -> None:
    """Test the manual user flow with a successful connection."""
    with patch(
        "custom_components.adam_audio.config_flow.AdamAudioClient",
    ) as mock_client_cls:
        client = mock_client_cls.return_value
        client.async_setup = AsyncMock(return_value=True)
        client.async_shutdown = AsyncMock()
        client.device_name = MOCK_DEVICE_NAME
        client.description = MOCK_DESCRIPTION
        client.serial = MOCK_SERIAL

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "user"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_HOST: MOCK_HOST, CONF_PORT: MOCK_PORT},
        )
        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["title"] == MOCK_DESCRIPTION
        assert result["data"][CONF_HOST] == MOCK_HOST


async def test_user_flow_connection_error(hass: HomeAssistant) -> None:
    """Test the manual user flow when connection fails."""
    with patch(
        "custom_components.adam_audio.config_flow.AdamAudioClient",
    ) as mock_client_cls:
        client = mock_client_cls.return_value
        client.async_setup = AsyncMock(return_value=False)
        client.async_shutdown = AsyncMock()

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_HOST: MOCK_HOST, CONF_PORT: MOCK_PORT},
        )
        assert result["type"] is FlowResultType.FORM
        assert result["errors"] == {"base": "cannot_connect"}
