"""Tests for ADAM Audio platform components (switch, number, select)."""

from __future__ import annotations

import asyncio
from dataclasses import replace
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.adam_audio.const import DOMAIN
from custom_components.adam_audio.data import AdamAudioIntegrationData
from custom_components.adam_audio.entity import AdamAudioEntity, AdamAudioGroupEntity
from custom_components.adam_audio.number import (
    _NUMBER_DESCRIPTORS,
    AdamAudioGroupNumber,
    AdamAudioNumber,
)
from custom_components.adam_audio.select import (
    AdamAudioGroupInputSelect,
    AdamAudioGroupVoicingSelect,
)
from custom_components.adam_audio.switch import (
    AdamAudioGroupMuteSwitch,
    AdamAudioGroupSleepSwitch,
)
from homeassistant.components.button import DOMAIN as BUTTON_DOMAIN, SERVICE_PRESS
from homeassistant.components.number import ATTR_VALUE, SERVICE_SET_VALUE
from homeassistant.components.select import ATTR_OPTION, SERVICE_SELECT_OPTION
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.const import (
    ATTR_ENTITY_ID,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_UNKNOWN,
    EntityCategory,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import DATA_ENTITY_PLATFORM


async def test_switch_entities(
    hass: HomeAssistant,
    mock_config_entry,
    mock_client: MagicMock,
) -> None:
    """Test switch entities."""
    mock_config_entry.add_to_hass(hass)

    with patch(
        "custom_components.adam_audio.coordinator.AdamAudioClient",
        return_value=mock_client,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    # Mute switch
    mute_entity = "switch.left_speaker_mute"
    await hass.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: mute_entity},
        blocking=True,
    )
    mock_client.async_set_mute.assert_called_once_with(True)

    await hass.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: mute_entity},
        blocking=True,
    )
    mock_client.async_set_mute.assert_called_with(False)

    # Standby switch
    standby_entity = "switch.left_speaker_sleep"
    await hass.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: standby_entity},
        blocking=True,
    )
    mock_client.async_set_sleep.assert_called_once_with(True)

    await hass.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: standby_entity},
        blocking=True,
    )
    mock_client.async_set_sleep.assert_called_with(False)


async def test_number_entities(
    hass: HomeAssistant,
    mock_config_entry,
    mock_client: MagicMock,
) -> None:
    """Test number entities."""
    mock_config_entry.add_to_hass(hass)

    with patch(
        "custom_components.adam_audio.coordinator.AdamAudioClient",
        return_value=mock_client,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    bass_entity = "number.left_speaker_bass"
    await hass.services.async_call(
        "number",
        SERVICE_SET_VALUE,
        {ATTR_ENTITY_ID: bass_entity, ATTR_VALUE: 1.0},
        blocking=True,
    )
    mock_client.async_set_bass.assert_called_once_with(1)

    desk_entity = "number.left_speaker_desk"
    await hass.services.async_call(
        "number",
        SERVICE_SET_VALUE,
        {ATTR_ENTITY_ID: desk_entity, ATTR_VALUE: -1.0},
        blocking=True,
    )
    mock_client.async_set_desk.assert_called_once_with(-1)

    presence_entity = "number.left_speaker_presence"
    await hass.services.async_call(
        "number",
        SERVICE_SET_VALUE,
        {ATTR_ENTITY_ID: presence_entity, ATTR_VALUE: 1.0},
        blocking=True,
    )
    mock_client.async_set_presence.assert_called_once_with(1)

    treble_entity = "number.left_speaker_treble"
    await hass.services.async_call(
        "number",
        SERVICE_SET_VALUE,
        {ATTR_ENTITY_ID: treble_entity, ATTR_VALUE: 0.0},
        blocking=True,
    )
    mock_client.async_set_treble.assert_called_once_with(0)


async def test_select_entities(
    hass: HomeAssistant,
    mock_config_entry,
    mock_client: MagicMock,
) -> None:
    """Test select entities."""
    mock_config_entry.add_to_hass(hass)

    with patch(
        "custom_components.adam_audio.coordinator.AdamAudioClient",
        return_value=mock_client,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    voicing_entity = "select.left_speaker_voicing"
    await hass.services.async_call(
        "select",
        SERVICE_SELECT_OPTION,
        {ATTR_ENTITY_ID: voicing_entity, ATTR_OPTION: "Pure"},
        blocking=True,
    )
    mock_client.async_set_voicing.assert_called_once_with(0)

    input_entity = "select.left_speaker_input_source"
    await hass.services.async_call(
        "select",
        SERVICE_SELECT_OPTION,
        {ATTR_ENTITY_ID: input_entity, ATTR_OPTION: "RCA"},
        blocking=True,
    )
    mock_client.async_set_input.assert_called_once_with(0)


@pytest.mark.usefixtures("mock_config_entry", "mock_client")
async def test_group_switch_entities(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_client: MagicMock
) -> None:
    """Test group switch entities control all speakers."""
    mock_config_entry.add_to_hass(hass)
    with patch(
        "custom_components.adam_audio.coordinator.AdamAudioClient",
        return_value=mock_client,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    mute_entity = "switch.all_speakers_mute"
    await hass.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: mute_entity},
        blocking=True,
    )
    mock_client.async_set_mute.assert_called_with(True)

    sleep_entity = "switch.all_speakers_sleep"
    await hass.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: sleep_entity},
        blocking=True,
    )
    mock_client.async_set_sleep.assert_called_with(True)


@pytest.mark.usefixtures("mock_config_entry", "mock_client")
async def test_group_number_entities(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_client: MagicMock
) -> None:
    """Test group number entities."""
    mock_config_entry.add_to_hass(hass)
    with patch(
        "custom_components.adam_audio.coordinator.AdamAudioClient",
        return_value=mock_client,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    bass_entity = "number.all_speakers_bass"
    await hass.services.async_call(
        "number",
        SERVICE_SET_VALUE,
        {ATTR_ENTITY_ID: bass_entity, ATTR_VALUE: 1.0},
        blocking=True,
    )
    mock_client.async_set_bass.assert_called_with(1)


@pytest.mark.usefixtures("mock_config_entry", "mock_client")
async def test_group_select_entities(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_client: MagicMock
) -> None:
    """Test group select entities."""
    mock_config_entry.add_to_hass(hass)
    with patch(
        "custom_components.adam_audio.coordinator.AdamAudioClient",
        return_value=mock_client,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    voicing_entity = "select.all_speakers_voicing"
    await hass.services.async_call(
        "select",
        SERVICE_SELECT_OPTION,
        {ATTR_ENTITY_ID: voicing_entity, ATTR_OPTION: "Pure"},
        blocking=True,
    )
    mock_client.async_set_voicing.assert_called_with(0)


@pytest.mark.usefixtures("mock_config_entry", "mock_client")
async def test_group_switch_turn_off(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_client: MagicMock
) -> None:
    """Test group switch turn_off controls all speakers."""
    mock_config_entry.add_to_hass(hass)
    with patch(
        "custom_components.adam_audio.coordinator.AdamAudioClient",
        return_value=mock_client,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    await hass.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: "switch.all_speakers_mute"},
        blocking=True,
    )
    mock_client.async_set_mute.assert_called_with(False)

    await hass.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: "switch.all_speakers_sleep"},
        blocking=True,
    )
    mock_client.async_set_sleep.assert_called_with(False)


@pytest.mark.usefixtures("mock_config_entry", "mock_client")
async def test_group_select_input(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_client: MagicMock
) -> None:
    """Test group input select controls all speakers."""
    mock_config_entry.add_to_hass(hass)
    with patch(
        "custom_components.adam_audio.coordinator.AdamAudioClient",
        return_value=mock_client,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    await hass.services.async_call(
        "select",
        SERVICE_SELECT_OPTION,
        {ATTR_ENTITY_ID: "select.all_speakers_input_source", ATTR_OPTION: "RCA"},
        blocking=True,
    )
    mock_client.async_set_input.assert_called_with(0)


async def test_group_switch_no_coordinators(hass: HomeAssistant) -> None:
    """Test group switch returns False when no coordinators are loaded."""
    assert AdamAudioGroupMuteSwitch(hass).is_on is False
    assert AdamAudioGroupSleepSwitch(hass).is_on is False


async def test_group_select_no_coordinators(hass: HomeAssistant) -> None:
    """Test group selects report no option when no coordinators are loaded."""
    assert AdamAudioGroupInputSelect(hass).current_option is None
    assert AdamAudioGroupVoicingSelect(hass).current_option is None


async def test_group_number_no_coordinators(hass: HomeAssistant) -> None:
    """Test group number reports no value when no coordinators are loaded."""
    num = AdamAudioGroupNumber(hass, _NUMBER_DESCRIPTORS[0])
    assert num.native_value is None


def test_number_unavailable_parent() -> None:
    """Test per-device number returns unavailable when parent is unavailable."""
    entity = object.__new__(AdamAudioNumber)
    entity._desc = _NUMBER_DESCRIPTORS[0]

    with patch.object(
        AdamAudioEntity, "available", new_callable=PropertyMock, return_value=False
    ):
        assert entity.available is False


def test_number_available_null_voicings() -> None:
    """Test per-device number available when valid_voicings is None."""
    entity = object.__new__(AdamAudioNumber)
    entity._desc = replace(_NUMBER_DESCRIPTORS[0], valid_voicings=None)

    with patch.object(
        AdamAudioEntity, "available", new_callable=PropertyMock, return_value=True
    ):
        assert entity.available is True


def test_group_number_unavailable_without_active_speaker() -> None:
    """Test group number is unavailable when no online speaker allows the control."""
    entity = object.__new__(AdamAudioGroupNumber)
    entity._desc = _NUMBER_DESCRIPTORS[0]

    with patch.object(AdamAudioGroupEntity, "_coordinators", return_value=[]):
        assert entity.available is False


def test_group_number_available_null_voicings() -> None:
    """Test group number ignores the voicing when valid_voicings is None."""
    entity = object.__new__(AdamAudioGroupNumber)
    entity._desc = replace(_NUMBER_DESCRIPTORS[0], valid_voicings=None)
    coordinator = MagicMock()
    coordinator.client.state.voicing = 2

    with patch.object(
        AdamAudioGroupEntity, "_coordinators", return_value=[coordinator]
    ):
        assert entity.available is True


async def test_unknown_device_values_are_reported_as_unknown(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_client: MagicMock
) -> None:
    """A value the integration can't name must not be shown as a real option."""
    mock_client.state.input_source = 99
    mock_client.state.voicing = 99
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    for entity_id in (
        "select.left_speaker_input_source",
        "select.left_speaker_voicing",
        "select.all_speakers_input_source",
        "select.all_speakers_voicing",
    ):
        assert hass.states.get(entity_id).state == STATE_UNKNOWN


async def test_identify_button(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_client: MagicMock
) -> None:
    """Test the identify button blinks the speaker, and only exists per speaker."""
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entity_id = "button.left_speaker_identify"
    assert hass.states.get("button.all_speakers_identify") is None
    assert (
        er.async_get(hass).async_get(entity_id).entity_category == EntityCategory.CONFIG
    )

    await hass.services.async_call(
        BUTTON_DOMAIN, SERVICE_PRESS, {ATTR_ENTITY_ID: entity_id}, blocking=True
    )
    mock_client.async_identify.assert_awaited_once()


@pytest.mark.usefixtures("mock_config_entry", "mock_client")
async def test_group_resubscribes_new_coordinator(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_client: MagicMock
) -> None:
    """Test group commands reach a coordinator that appeared after setup."""
    mock_config_entry.add_to_hass(hass)
    with patch(
        "custom_components.adam_audio.coordinator.AdamAudioClient",
        return_value=mock_client,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    # Inject a second coordinator
    mock_coord2 = MagicMock()
    mock_coord2.client.state = mock_client.state
    mock_coord2.client.available = True
    mock_coord2.client.async_set_mute = AsyncMock()
    mock_coord2.async_add_listener = MagicMock(return_value=lambda: None)
    integration_data: AdamAudioIntegrationData = hass.data[DOMAIN]
    integration_data.coordinators["fake_entry_2"] = mock_coord2

    await hass.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: "switch.all_speakers_mute"},
        blocking=True,
    )
    mock_client.async_set_mute.assert_called_with(True)
    mock_coord2.client.async_set_mute.assert_called_with(True)

    del integration_data.coordinators["fake_entry_2"]


# ── Regression tests: KeyError on double-unsub after entity removal ──────────
#
# Bug: async_will_remove_from_hass() used to unsub() every coordinator
# listener without clearing _unsub_listeners. A later re-subscription then
# tried to unsub() the very same listeners a second time, and
# DataUpdateCoordinator.__async_remove_listener_internal() raises KeyError on a
# listener id that's already been popped, crashing the service call.


async def test_group_entity_removal_clears_subscription_state(
    hass: HomeAssistant,
) -> None:
    """async_will_remove_from_hass must unsub and reset all tracking state."""
    entity = AdamAudioGroupEntity(hass)
    unsub1 = MagicMock()
    unsub2 = MagicMock()
    entity._unsub_listeners = [unsub1, unsub2]

    await entity.async_will_remove_from_hass()

    unsub1.assert_called_once()
    unsub2.assert_called_once()
    assert entity._unsub_listeners == []
    assert entity._removed is True


async def test_group_entity_no_resubscribe_after_removal(hass: HomeAssistant) -> None:
    """A coordinator change must be ignored once the entity is removed."""
    entity = AdamAudioGroupEntity(hass)
    await entity.async_will_remove_from_hass()

    mock_coord = MagicMock()
    mock_coord.async_add_listener = MagicMock(return_value=lambda: None)
    with (
        patch.object(entity, "_all_coordinators", return_value=[mock_coord]),
        patch.object(entity, "async_write_ha_state") as mock_write,
    ):
        entity._on_coordinators_changed()

    assert entity._unsub_listeners == []
    mock_coord.async_add_listener.assert_not_called()
    mock_write.assert_not_called()


async def test_group_entity_command_no_state_write_after_removal(
    hass: HomeAssistant,
) -> None:
    """A command resuming after removal must not write state.

    The entity is no longer attached to a platform at that point, so writing
    state would raise.
    """
    entity = AdamAudioGroupEntity(hass)
    coordinator = MagicMock()
    coordinator.client.available = True

    async def remove_mid_command(_value: bool) -> None:
        await entity.async_will_remove_from_hass()

    coordinator.client.async_set_mute = AsyncMock(side_effect=remove_mid_command)

    with (
        patch.object(entity, "_all_coordinators", return_value=[coordinator]),
        patch.object(entity, "async_write_ha_state") as mock_write,
    ):
        await entity._async_call_all("async_set_mute", True)

    coordinator.async_notify_state.assert_called_once()
    mock_write.assert_not_called()


async def test_group_entity_survives_double_unsub_after_removal(
    hass: HomeAssistant,
) -> None:
    """Directly reproduces the KeyError.

    An unsub() that raises if invoked a second time (mirroring
    DataUpdateCoordinator's real behavior) must only ever be called once,
    even when a coordinator change arrives after removal.
    """
    entity = AdamAudioGroupEntity(hass)

    calls = 0

    def unsub_like_coordinator() -> None:
        nonlocal calls
        calls += 1
        if calls > 1:
            raise KeyError(23)

    entity._unsub_listeners = [unsub_like_coordinator]

    # Entity torn down mid-command, e.g. by a config entry reload.
    await entity.async_will_remove_from_hass()
    assert calls == 1

    entity._on_coordinators_changed()

    assert calls == 1


@pytest.mark.usefixtures("mock_config_entry", "mock_client")
async def test_group_switch_removed_mid_command_no_keyerror(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_client: MagicMock
) -> None:
    """End-to-end repro.

    Removing the group switch while a command is still in flight (simulating
    a config entry reload racing a service call) must not raise, and the
    service call must complete cleanly.
    """
    mock_config_entry.add_to_hass(hass)
    with patch(
        "custom_components.adam_audio.coordinator.AdamAudioClient",
        return_value=mock_client,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    release = asyncio.Event()

    async def slow_set_sleep(_value: bool) -> None:
        await release.wait()

    mock_client.async_set_sleep = AsyncMock(side_effect=slow_set_sleep)

    platforms = hass.data[DATA_ENTITY_PLATFORM][DOMAIN]
    switch_platform = next(p for p in platforms if p.domain == SWITCH_DOMAIN)
    entity = switch_platform.entities["switch.all_speakers_sleep"]

    task = hass.async_create_task(
        hass.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: "switch.all_speakers_sleep"},
            blocking=True,
        )
    )
    await asyncio.sleep(0)  # let _async_call_all start and suspend on gather()

    # Simulate the entity being torn down mid-command (e.g. a reload of the
    # config entry that owns the group platform removes its entities).
    await entity.async_will_remove_from_hass()

    release.set()
    await task  # must not raise KeyError
    await hass.async_block_till_done()
