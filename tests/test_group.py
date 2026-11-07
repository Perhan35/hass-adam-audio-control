"""Tests for the 'All Speakers' group across two speakers.

These run the real integration code; only AdamAudioClient is faked.
"""

from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.adam_audio.client import AdamAudioState
from custom_components.adam_audio.const import (
    CONF_DEVICE_NAME,
    CONF_SERIAL,
    DOMAIN,
    GROUP_DEVICE_ID,
)
from custom_components.adam_audio.entity import AdamAudioGroupEntity
from homeassistant.components.number import (
    ATTR_VALUE,
    DOMAIN as NUMBER_DOMAIN,
    SERVICE_SET_VALUE,
)
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import (
    ATTR_ENTITY_ID,
    CONF_DESCRIPTION,
    CONF_HOST,
    CONF_PORT,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import Event, HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.entity import Entity
from homeassistant.setup import async_setup_component

LEFT_HOST = "192.168.1.1"
RIGHT_HOST = "192.168.1.2"
GROUP_IDENTIFIER = (DOMAIN, GROUP_DEVICE_ID)
GROUP_MUTE = "switch.all_speakers_mute"
GROUP_BASS = "number.all_speakers_bass"
GROUP_INPUT = "select.all_speakers_input_source"
GROUP_VOICING = "select.all_speakers_voicing"
GROUP_ENTITY_COUNT = 8
TOTAL_ENTITY_COUNT = 26


def _fake_client(serial: str, description: str) -> MagicMock:
    """Build a fake speaker whose setters change its state, like the real one."""
    client = MagicMock()
    client.available = True
    client.description = description
    client.serial = serial
    client.state = AdamAudioState(
        mute=False,
        sleep=False,
        input_source=1,
        voicing=0,
        bass=0,
        desk=0,
        presence=0,
        treble=0,
    )
    client.async_setup = AsyncMock(return_value=True)
    client.async_shutdown = AsyncMock()
    client.async_fetch_state = AsyncMock(return_value=True)

    async def _set_mute(value: bool) -> None:
        client.state.mute = value

    async def _set_bass(value: int) -> None:
        client.state.bass = value

    client.async_set_mute = AsyncMock(side_effect=_set_mute)
    client.async_set_bass = AsyncMock(side_effect=_set_bass)
    return client


def _speaker_entry(host: str, serial: str, description: str) -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        title=description,
        unique_id=serial,
        data={
            CONF_HOST: host,
            CONF_PORT: 49494,
            CONF_DEVICE_NAME: f"ASeries-{description}",
            CONF_DESCRIPTION: description,
            CONF_SERIAL: serial,
        },
    )


@pytest.fixture
def left_client() -> MagicMock:
    """Return the fake left speaker."""
    return _fake_client("SN-LEFT", "Left")


@pytest.fixture
def right_client() -> MagicMock:
    """Return the fake right speaker."""
    return _fake_client("SN-RIGHT", "Right")


@pytest.fixture
def left_entry() -> MockConfigEntry:
    """Return the config entry of the left speaker."""
    return _speaker_entry(LEFT_HOST, "SN-LEFT", "Left")


@pytest.fixture
def right_entry() -> MockConfigEntry:
    """Return the config entry of the right speaker."""
    return _speaker_entry(RIGHT_HOST, "SN-RIGHT", "Right")


@pytest.fixture(autouse=True)
async def speakers_on_network(
    hass: HomeAssistant, left_client: MagicMock, right_client: MagicMock
) -> AsyncGenerator[None]:
    """Make the integration reach the fake speakers instead of the network."""
    clients = {LEFT_HOST: left_client, RIGHT_HOST: right_client}

    def _client(_hass: HomeAssistant, host: str, port: int) -> MagicMock:
        return clients[host]

    with patch(
        "custom_components.adam_audio.coordinator.AdamAudioClient",
        side_effect=_client,
    ):
        yield
        await _stop(hass)


async def _start(hass: HomeAssistant, *entries: MockConfigEntry) -> None:
    """Start the integration; the entry added first becomes the group owner."""
    for entry in entries:
        entry.add_to_hass(hass)
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()


async def _stop(hass: HomeAssistant) -> None:
    """Unload every speaker, like a shutdown: nothing moves to another speaker.

    The owner goes last, because unloading it first would hand the group to
    the other speaker.
    """
    data = hass.data.get(DOMAIN)
    owner_id = data.group_owner_entry_id if data else None
    for entry in sorted(
        hass.config_entries.async_entries(DOMAIN),
        key=lambda entry: entry.entry_id == owner_id,
    ):
        if entry.state is ConfigEntryState.LOADED:
            assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def _poll(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """Run one polling cycle of a speaker."""
    await entry.runtime_data.coordinator.async_refresh()
    await hass.async_block_till_done()


async def _go_offline(
    hass: HomeAssistant, client: MagicMock, entry: MockConfigEntry
) -> None:
    """Turn a speaker off while Home Assistant is running."""
    client.available = False
    await _poll(hass, entry)


async def _mute_group(hass: HomeAssistant) -> None:
    await hass.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: GROUP_MUTE},
        blocking=True,
    )


def _group_devices(hass: HomeAssistant) -> list[dr.DeviceEntry]:
    """Return every 'All Speakers' device in the registry."""
    device_registry = dr.async_get(hass)
    return [
        device
        for entry in hass.config_entries.async_entries(DOMAIN)
        if (
            device := device_registry.async_get_device_by_identifier(
                GROUP_IDENTIFIER, entry.entry_id
            )
        )
    ]


def _group_entities(hass: HomeAssistant) -> list[er.RegistryEntry]:
    """Return every group entity in the registry."""
    return [
        entity
        for entity in er.async_get(hass).entities.values()
        if entity.platform == DOMAIN and GROUP_DEVICE_ID in entity.unique_id
    ]


def _assert_group_on(
    hass: HomeAssistant, owner: MockConfigEntry, device_id: str | None = None
) -> None:
    """Assert there is one complete group, attached to the owner entry."""
    devices = _group_devices(hass)
    assert len(devices) == 1
    assert devices[0].config_entry_id == owner.entry_id
    if device_id is not None:
        assert devices[0].id == device_id
    entities = _group_entities(hass)
    assert len(entities) == GROUP_ENTITY_COUNT
    assert {entity.config_entry_id for entity in entities} == {owner.entry_id}
    assert {entity.device_id for entity in entities} == {devices[0].id}
    assert hass.data[DOMAIN].group_owner_entry_id == owner.entry_id


def _seed_group_device(hass: HomeAssistant, entry: MockConfigEntry) -> dr.DeviceEntry:
    return dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id, identifiers={GROUP_IDENTIFIER}
    )


# ── Who owns the group ───────────────────────────────────────────────────────


async def test_two_speakers_share_one_group(
    hass: HomeAssistant, left_entry: MockConfigEntry, right_entry: MockConfigEntry
) -> None:
    """Two speakers give 24 entities and a single group device."""
    await _start(hass, left_entry, right_entry)

    assert left_entry.state is ConfigEntryState.LOADED
    assert right_entry.state is ConfigEntryState.LOADED
    _assert_group_on(hass, left_entry)
    assert len(er.async_get(hass).entities) == TOTAL_ENTITY_COUNT


@pytest.mark.parametrize("right_first", [False, True])
async def test_empty_duplicate_device_is_removed(
    hass: HomeAssistant,
    left_entry: MockConfigEntry,
    right_entry: MockConfigEntry,
    right_first: bool,
) -> None:
    """The device with entities wins, whichever speaker starts first.

    This is the state found on a real install: the same group identifier on
    both entries, Left's device holding the entities and Right's empty.
    """
    await _start(hass, left_entry, right_entry)
    device_id = _group_devices(hass)[0].id
    await _stop(hass)
    empty = _seed_group_device(hass, right_entry)
    assert empty.id != device_id

    first, second = (
        (right_entry, left_entry) if right_first else (left_entry, right_entry)
    )
    assert await hass.config_entries.async_setup(first.entry_id)
    assert await hass.config_entries.async_setup(second.entry_id)
    await hass.async_block_till_done()

    _assert_group_on(hass, first, device_id)


async def test_group_entities_split_over_two_devices_are_merged(
    hass: HomeAssistant, left_entry: MockConfigEntry, right_entry: MockConfigEntry
) -> None:
    """Moving a device onto an entry that already has one must not fail setup."""
    right_entry.add_to_hass(hass)  # added first, so it becomes the owner
    left_entry.add_to_hass(hass)
    entity_registry = er.async_get(hass)
    left_device = _seed_group_device(hass, left_entry)
    right_device = _seed_group_device(hass, right_entry)
    assert left_device.id != right_device.id
    for key, entry, device in (
        ("mute", right_entry, right_device),
        ("sleep", left_entry, left_device),
        ("bass", left_entry, left_device),
    ):
        entity_registry.async_get_or_create(
            NUMBER_DOMAIN if key == "bass" else SWITCH_DOMAIN,
            DOMAIN,
            f"{DOMAIN}_{GROUP_DEVICE_ID}_{key}",
            config_entry=entry,
            device_id=device.id,
        )

    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()

    assert right_entry.state is ConfigEntryState.LOADED
    assert left_entry.state is ConfigEntryState.LOADED
    _assert_group_on(hass, right_entry, left_device.id)


# ── The device id must not change ────────────────────────────────────────────


async def test_owner_reload_keeps_device_id(
    hass: HomeAssistant, left_entry: MockConfigEntry, right_entry: MockConfigEntry
) -> None:
    """Reloading the owner leaves one device with the same id."""
    await _start(hass, left_entry, right_entry)
    device_id = _group_devices(hass)[0].id

    assert await hass.config_entries.async_reload(left_entry.entry_id)
    await hass.async_block_till_done()

    assert left_entry.state is ConfigEntryState.LOADED
    assert right_entry.state is ConfigEntryState.LOADED
    assert _group_devices(hass)[0].id == device_id
    _assert_group_on(hass, _owner(hass, left_entry, right_entry), device_id)
    assert len(er.async_get(hass).entities) == TOTAL_ENTITY_COUNT


async def test_group_moves_when_owner_is_off_at_startup(
    hass: HomeAssistant,
    left_entry: MockConfigEntry,
    right_entry: MockConfigEntry,
    left_client: MagicMock,
    right_client: MagicMock,
) -> None:
    """Left off at startup: the group drives Right, then both when Left returns."""
    await _start(hass, left_entry, right_entry)
    device_id = _group_devices(hass)[0].id
    await _stop(hass)

    left_client.async_setup.return_value = False
    await hass.config_entries.async_setup(left_entry.entry_id)
    await hass.config_entries.async_setup(right_entry.entry_id)
    await hass.async_block_till_done()

    assert left_entry.state is ConfigEntryState.SETUP_RETRY
    _assert_group_on(hass, right_entry, device_id)
    await _mute_group(hass)
    right_client.async_set_mute.assert_awaited_once_with(True)
    left_client.async_set_mute.assert_not_awaited()
    assert hass.states.get(GROUP_MUTE).state == STATE_ON

    left_client.async_setup.return_value = True
    assert await hass.config_entries.async_reload(left_entry.entry_id)
    await hass.async_block_till_done()

    _assert_group_on(hass, right_entry, device_id)
    await _mute_group(hass)
    left_client.async_set_mute.assert_awaited_once_with(True)


async def test_owner_change_keeps_user_customizations(
    hass: HomeAssistant,
    left_entry: MockConfigEntry,
    right_entry: MockConfigEntry,
    left_client: MagicMock,
) -> None:
    """Entities follow the device: they are moved, never deleted and restored."""
    await _start(hass, left_entry, right_entry)
    entity_registry = er.async_get(hass)
    before = entity_registry.async_update_entity(
        GROUP_MUTE,
        new_entity_id="switch.studio_mute",
        name="Studio mute",
        area_id="studio",
        hidden_by=er.RegistryEntryHider.USER,
    )
    await hass.async_block_till_done()
    await _stop(hass)

    removed: list[str] = []

    def _on_registry_update(event: Event[Any]) -> None:
        if event.data["action"] == "remove":
            removed.append(event.data["entity_id"])

    hass.bus.async_listen(er.EVENT_ENTITY_REGISTRY_UPDATED, _on_registry_update)

    left_client.async_setup.return_value = False
    await hass.config_entries.async_setup(left_entry.entry_id)
    await hass.config_entries.async_setup(right_entry.entry_id)
    await hass.async_block_till_done()

    assert removed == []
    after = entity_registry.async_get("switch.studio_mute")
    assert after is not None
    assert after.id == before.id
    assert after.name == "Studio mute"
    assert after.area_id == "studio"
    assert after.hidden_by is er.RegistryEntryHider.USER
    assert after.config_entry_id == right_entry.entry_id
    assert entity_registry.async_get(GROUP_MUTE) is None


async def test_removing_owner_keeps_group_on_other_speaker(
    hass: HomeAssistant,
    left_entry: MockConfigEntry,
    right_entry: MockConfigEntry,
    right_client: MagicMock,
) -> None:
    """Deleting the owner's entry keeps the group, its id and custom entity_id."""
    await _start(hass, left_entry, right_entry)
    device_id = _group_devices(hass)[0].id
    er.async_get(hass).async_update_entity(
        GROUP_MUTE, new_entity_id="switch.studio_mute"
    )
    await hass.async_block_till_done()

    await hass.config_entries.async_remove(left_entry.entry_id)
    await hass.async_block_till_done()

    _assert_group_on(hass, right_entry, device_id)
    assert hass.states.get("switch.studio_mute") is not None
    await hass.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: "switch.studio_mute"},
        blocking=True,
    )
    right_client.async_set_mute.assert_awaited_once_with(True)


async def test_group_entity_rename_keeps_following_speakers(
    hass: HomeAssistant,
    left_entry: MockConfigEntry,
    right_entry: MockConfigEntry,
    left_client: MagicMock,
    right_client: MagicMock,
) -> None:
    """A renamed group entity still follows the speakers."""
    await _start(hass, left_entry, right_entry)
    er.async_get(hass).async_update_entity(
        GROUP_MUTE, new_entity_id="switch.studio_mute"
    )
    await hass.async_block_till_done()

    left_client.state.mute = True
    right_client.state.mute = True
    await _poll(hass, left_entry)
    await _poll(hass, right_entry)

    assert hass.states.get("switch.studio_mute").state == STATE_ON
    assert hass.states.get(GROUP_MUTE) is None


@pytest.mark.skipif(
    not hasattr(Entity, "async_entity_id_changed"),
    reason="Home Assistant calls this hook from 2026.11 on",
)
async def test_group_entity_id_changed_defers_to_home_assistant(
    hass: HomeAssistant,
) -> None:
    """The hook is defined, so HA renames group entities in place."""
    entity = AdamAudioGroupEntity(hass)
    with patch.object(Entity, "async_entity_id_changed") as mock_super:
        entity.async_entity_id_changed("switch.old")
    mock_super.assert_called_once_with("switch.old")


# ── The group state must stay right ──────────────────────────────────────────


async def test_group_shows_unknown_when_speakers_differ(
    hass: HomeAssistant,
    left_entry: MockConfigEntry,
    right_entry: MockConfigEntry,
    right_client: MagicMock,
) -> None:
    """Different speakers must not be shown as if they matched."""
    await _start(hass, left_entry, right_entry)
    assert hass.states.get(GROUP_INPUT).state == "XLR"
    assert hass.states.get(GROUP_VOICING).state == "Pure"
    assert float(hass.states.get(GROUP_BASS).state) == 0.0

    right_client.state.input_source = 0
    right_client.state.voicing = 1
    right_client.state.bass = -1
    await _poll(hass, right_entry)

    assert hass.states.get(GROUP_INPUT).state == STATE_UNKNOWN
    assert hass.states.get(GROUP_VOICING).state == STATE_UNKNOWN
    assert hass.states.get(GROUP_BASS).state == STATE_UNKNOWN


async def test_group_eq_skips_speaker_in_ext_voicing(
    hass: HomeAssistant,
    left_entry: MockConfigEntry,
    right_entry: MockConfigEntry,
    left_client: MagicMock,
    right_client: MagicMock,
) -> None:
    """EQ is disabled in Ext voicing: the group follows the same rule."""
    await _start(hass, left_entry, right_entry)
    right_client.state.voicing = 2
    right_client.state.bass = -2
    await _poll(hass, right_entry)

    # The Ext speaker's value doesn't count, so the group isn't "unknown".
    assert float(hass.states.get(GROUP_BASS).state) == 0.0

    await hass.services.async_call(
        NUMBER_DOMAIN,
        SERVICE_SET_VALUE,
        {ATTR_ENTITY_ID: GROUP_BASS, ATTR_VALUE: -1},
        blocking=True,
    )

    left_client.async_set_bass.assert_awaited_once_with(-1)
    right_client.async_set_bass.assert_not_awaited()
    assert float(hass.states.get(GROUP_BASS).state) == -1.0


async def test_group_eq_unavailable_when_every_speaker_is_in_ext_voicing(
    hass: HomeAssistant,
    left_entry: MockConfigEntry,
    right_entry: MockConfigEntry,
    left_client: MagicMock,
    right_client: MagicMock,
) -> None:
    """No speaker allows the control, so the group doesn't either."""
    await _start(hass, left_entry, right_entry)
    left_client.state.voicing = 2
    right_client.state.voicing = 2
    await _poll(hass, left_entry)
    await _poll(hass, right_entry)

    assert hass.states.get(GROUP_BASS).state == STATE_UNAVAILABLE


async def test_returned_speaker_is_followed(
    hass: HomeAssistant,
    left_entry: MockConfigEntry,
    right_entry: MockConfigEntry,
    left_client: MagicMock,
    right_client: MagicMock,
) -> None:
    """A change on a returned speaker alone reaches the group.

    The common case of a speaker switched on after Home Assistant.
    """
    await _start(hass, left_entry, right_entry)
    await _stop(hass)
    left_client.async_setup.return_value = False
    await hass.config_entries.async_setup(left_entry.entry_id)
    await hass.config_entries.async_setup(right_entry.entry_id)
    await hass.async_block_till_done()

    left_client.async_setup.return_value = True
    assert await hass.config_entries.async_reload(left_entry.entry_id)
    await hass.async_block_till_done()
    await _mute_group(hass)
    assert hass.states.get(GROUP_MUTE).state == STATE_ON

    left_client.state.mute = False
    await _poll(hass, left_entry)

    assert hass.states.get(GROUP_MUTE).state == STATE_OFF
    assert right_client.state.mute is True


async def test_non_owner_reload_is_followed(
    hass: HomeAssistant,
    left_entry: MockConfigEntry,
    right_entry: MockConfigEntry,
    left_client: MagicMock,
    right_client: MagicMock,
) -> None:
    """After reloading a speaker, the group listens to its new coordinator."""
    await _start(hass, left_entry, right_entry)
    await _mute_group(hass)
    assert hass.states.get(GROUP_MUTE).state == STATE_ON

    assert await hass.config_entries.async_reload(right_entry.entry_id)
    await hass.async_block_till_done()
    _assert_group_on(hass, left_entry)

    right_client.state.mute = False
    await _poll(hass, right_entry)

    assert hass.states.get(GROUP_MUTE).state == STATE_OFF
    assert left_client.state.mute is True


# ── A speaker going away ─────────────────────────────────────────────────────


async def test_speaker_off_while_running_leaves_group_usable(
    hass: HomeAssistant,
    left_entry: MockConfigEntry,
    right_entry: MockConfigEntry,
    left_client: MagicMock,
    right_client: MagicMock,
) -> None:
    """Commands reach the online speaker, without error, and state ignores the other."""
    await _start(hass, left_entry, right_entry)
    right_client.state.bass = 2
    await _poll(hass, right_entry)
    assert hass.states.get(GROUP_BASS).state == STATE_UNKNOWN

    await _go_offline(hass, right_client, right_entry)
    assert hass.states.get(GROUP_MUTE).state == STATE_OFF
    assert float(hass.states.get(GROUP_BASS).state) == 0.0

    await _mute_group(hass)

    left_client.async_set_mute.assert_awaited_once_with(True)
    right_client.async_set_mute.assert_not_awaited()
    assert hass.states.get(GROUP_MUTE).state == STATE_ON


async def test_missed_command_is_not_replayed(
    hass: HomeAssistant,
    left_entry: MockConfigEntry,
    right_entry: MockConfigEntry,
    left_client: MagicMock,
    right_client: MagicMock,
) -> None:
    """A speaker that missed a command stays different when it returns.

    Decision: nothing is sent to it, and the group shows the difference.
    """
    await _start(hass, left_entry, right_entry)
    await _go_offline(hass, right_client, right_entry)
    await _mute_group(hass)
    assert hass.states.get(GROUP_MUTE).state == STATE_ON

    right_client.available = True
    await _poll(hass, right_entry)

    right_client.async_set_mute.assert_not_awaited()
    assert left_client.state.mute is True
    assert right_client.state.mute is False
    assert hass.states.get(GROUP_MUTE).state == STATE_OFF


async def test_group_unavailable_when_every_speaker_is_off(
    hass: HomeAssistant,
    left_entry: MockConfigEntry,
    right_entry: MockConfigEntry,
    left_client: MagicMock,
    right_client: MagicMock,
) -> None:
    """With no speaker online, the group is unavailable, and comes back."""
    await _start(hass, left_entry, right_entry)
    await _go_offline(hass, left_client, left_entry)
    assert hass.states.get(GROUP_MUTE).state != STATE_UNAVAILABLE

    await _go_offline(hass, right_client, right_entry)
    assert hass.states.get(GROUP_MUTE).state == STATE_UNAVAILABLE

    left_client.available = True
    await _poll(hass, left_entry)
    assert hass.states.get(GROUP_MUTE).state != STATE_UNAVAILABLE


async def test_command_failing_on_online_speaker_still_raises(
    hass: HomeAssistant,
    left_entry: MockConfigEntry,
    right_entry: MockConfigEntry,
    left_client: MagicMock,
    right_client: MagicMock,
) -> None:
    """A real failure is reported, and the other speaker still gets the command."""
    await _start(hass, left_entry, right_entry)
    right_client.async_set_bass.side_effect = OSError("no answer")

    with pytest.raises(HomeAssistantError, match="1 of 2"):
        await hass.services.async_call(
            NUMBER_DOMAIN,
            SERVICE_SET_VALUE,
            {ATTR_ENTITY_ID: GROUP_BASS, ATTR_VALUE: 1},
            blocking=True,
        )

    left_client.async_set_bass.assert_awaited_once_with(1)


def _owner(hass: HomeAssistant, *entries: MockConfigEntry) -> MockConfigEntry:
    """Return the entry that currently owns the group."""
    owner_id = hass.data[DOMAIN].group_owner_entry_id
    return next(entry for entry in entries if entry.entry_id == owner_id)
