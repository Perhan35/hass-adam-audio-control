"""Tests for ADAM Audio config flow."""

from __future__ import annotations

from ipaddress import IPv4Address
import logging
from unittest.mock import MagicMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.adam_audio.const import CONF_DEVICE_NAME, CONF_SERIAL, DOMAIN
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo
from tests.conftest import (
    MOCK_DESCRIPTION,
    MOCK_DEVICE_NAME,
    MOCK_HOST,
    MOCK_PORT,
    MOCK_SERIAL,
)


async def test_user_flow_success(hass: HomeAssistant, mock_client: MagicMock) -> None:
    """Test the manual user flow with a successful connection."""
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


async def test_user_flow_connection_error(
    hass: HomeAssistant, mock_client: MagicMock
) -> None:
    """Test the manual user flow when connection fails."""
    mock_client.async_setup.return_value = False

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_HOST: MOCK_HOST, CONF_PORT: MOCK_PORT},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_zeroconf_flow_empty_hostname(
    hass: HomeAssistant, mock_client: MagicMock
) -> None:
    """Test zeroconf when hostname is empty (falls back to IP-based device_id)."""
    discovery_info = ZeroconfServiceInfo(
        ip_address=IPv4Address(MOCK_HOST),
        ip_addresses=[IPv4Address(MOCK_HOST)],
        port=MOCK_PORT,
        hostname="",
        type="_oca._udp.local.",
        name="._oca._udp.local.",
        properties={},
    )

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF},
        data=discovery_info,
    )
    assert result["type"] is FlowResultType.FORM

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_HOST] == MOCK_HOST


async def test_zeroconf_flow_success(
    hass: HomeAssistant, mock_client: MagicMock
) -> None:
    """Test zeroconf discovery with a successful connection."""
    discovery_info = ZeroconfServiceInfo(
        ip_address=IPv4Address(MOCK_HOST),
        ip_addresses=[IPv4Address(MOCK_HOST)],
        port=MOCK_PORT,
        hostname="ASeries-41472b.local.",
        type="_oca._udp.local.",
        name="ASeries-41472b._oca._udp.local.",
        properties={},
    )

    # Step 1: zeroconf triggers discovery → shows confirm form
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF},
        data=discovery_info,
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "zeroconf_confirm"

    # Step 2: user confirms → entry created
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == MOCK_DESCRIPTION
    assert result["data"][CONF_HOST] == MOCK_HOST
    assert result["data"][CONF_PORT] == MOCK_PORT
    assert result["data"][CONF_DEVICE_NAME] == MOCK_DEVICE_NAME
    assert result["data"][CONF_SERIAL] == MOCK_SERIAL


async def test_zeroconf_flow_connection_failure(
    hass: HomeAssistant, mock_client: MagicMock
) -> None:
    """Test zeroconf discovery aborts when the device does not answer.

    Creating an entry for an unreachable device would never become ready and
    its hostname-based unique_id would clash with the serial-based one on a
    later successful discovery; zeroconf re-triggers the flow automatically.
    """
    discovery_info = ZeroconfServiceInfo(
        ip_address=IPv4Address(MOCK_HOST),
        ip_addresses=[IPv4Address(MOCK_HOST)],
        port=MOCK_PORT,
        hostname="ASeries-41472b.local.",
        type="_oca._udp.local.",
        name="ASeries-41472b._oca._udp.local.",
        properties={},
    )

    mock_client.async_setup.return_value = False

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF},
        data=discovery_info,
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "cannot_connect"


async def test_user_flow_exception(hass: HomeAssistant, mock_client: MagicMock) -> None:
    """Test _async_try_connect returns None when an unexpected exception occurs."""
    mock_client.async_setup.side_effect = RuntimeError("boom")

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_HOST: MOCK_HOST, CONF_PORT: MOCK_PORT},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_new_address_reloads_once_without_deprecation(
    hass: HomeAssistant,
    mock_client: MagicMock,
    mock_config_entry: MockConfigEntry,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A speaker discovered on a new address is reloaded once, quietly.

    Regression test: an update listener used to reload the entry on top of the
    reload scheduled by the flow, which Home Assistant flags for removal.
    """
    caplog.set_level(logging.WARNING)
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    real_reload = hass.config_entries.async_reload
    with patch.object(
        hass.config_entries, "async_reload", side_effect=real_reload
    ) as mock_reload:
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_ZEROCONF},
            data=ZeroconfServiceInfo(
                ip_address=IPv4Address("192.168.1.222"),
                ip_addresses=[IPv4Address("192.168.1.222")],
                hostname=f"{MOCK_DEVICE_NAME}.local.",
                name=f"{MOCK_DEVICE_NAME}._oca._udp.local.",
                port=MOCK_PORT,
                type="_oca._udp.local.",
                properties={},
            ),
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert mock_config_entry.data[CONF_HOST] == "192.168.1.222"
    mock_reload.assert_called_once_with(mock_config_entry.entry_id)
    assert "update listener" not in caplog.text


async def _start_reconfigure(
    hass: HomeAssistant, entry: MockConfigEntry
) -> config_entries.ConfigFlowResult:
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return await entry.start_reconfigure_flow(hass)


async def test_reconfigure_updates_address(
    hass: HomeAssistant, mock_client: MagicMock, mock_config_entry: MockConfigEntry
) -> None:
    """Test the address of a speaker can be corrected."""
    result = await _start_reconfigure(hass, mock_config_entry)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: " 192.168.1.50 ", CONF_PORT: 1234}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert mock_config_entry.data[CONF_HOST] == "192.168.1.50"
    assert mock_config_entry.data[CONF_PORT] == 1234
    assert mock_config_entry.unique_id == MOCK_SERIAL


async def test_reconfigure_cannot_connect_then_recovers(
    hass: HomeAssistant, mock_client: MagicMock, mock_config_entry: MockConfigEntry
) -> None:
    """Test an unreachable address shows an error and can be corrected."""
    result = await _start_reconfigure(hass, mock_config_entry)

    mock_client.async_setup.return_value = False
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: "192.168.1.50", CONF_PORT: MOCK_PORT}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}
    assert mock_config_entry.data[CONF_HOST] == MOCK_HOST

    mock_client.async_setup.return_value = True
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: "192.168.1.50", CONF_PORT: MOCK_PORT}
    )
    await hass.async_block_till_done()
    assert result["reason"] == "reconfigure_successful"


async def test_reconfigure_refuses_another_speaker(
    hass: HomeAssistant, mock_client: MagicMock, mock_config_entry: MockConfigEntry
) -> None:
    """Test an entry can't be pointed at a different speaker."""
    result = await _start_reconfigure(hass, mock_config_entry)

    mock_client.serial = "SN-OTHER"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: "192.168.1.50", CONF_PORT: MOCK_PORT}
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "wrong_device"
    assert mock_config_entry.data[CONF_HOST] == MOCK_HOST


@pytest.mark.parametrize(
    ("live_name", "reason"),
    [
        (MOCK_DEVICE_NAME, "reconfigure_successful"),
        ("ASeries-other", "wrong_device"),
    ],
)
async def test_reconfigure_entry_without_serial_compares_names(
    hass: HomeAssistant, mock_client: MagicMock, live_name: str, reason: str
) -> None:
    """Test an old entry with no stored serial falls back to the hardware name."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=MOCK_DEVICE_NAME,
        data={
            CONF_HOST: MOCK_HOST,
            CONF_PORT: MOCK_PORT,
            CONF_DEVICE_NAME: MOCK_DEVICE_NAME,
        },
    )
    entry.add_to_hass(hass)
    result = await entry.start_reconfigure_flow(hass)

    mock_client.device_name = live_name
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: "192.168.1.50", CONF_PORT: MOCK_PORT}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == reason
