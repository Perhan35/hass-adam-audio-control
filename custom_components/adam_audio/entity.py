"""Base entity classes for ADAM Audio.

Two flavours:
  AdamAudioEntity      - CoordinatorEntity bound to a single physical device.
  AdamAudioGroupEntity - Plain Entity that fans commands out to ALL devices
                         registered at call-time.  It self-subscribes to every
                         coordinator's update bus so the group state stays fresh.
"""

import asyncio
from typing import Any, override

from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import get_coordinators
from .const import (
    DOMAIN,
    GROUP_DEVICE_ID,
    GROUP_DEVICE_NAME,
    MANUFACTURER,
    SIGNAL_COORDINATORS_CHANGED,
)
from .coordinator import AdamAudioCoordinator


class AdamAudioEntity(CoordinatorEntity[AdamAudioCoordinator]):
    """Base entity for a single physical speaker."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: AdamAudioCoordinator) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._attr_device_info = coordinator.device_info

    @property
    @override
    def available(self) -> bool:
        """Mark unavailable if the coordinator fails or the client drops."""
        return super().available and self.coordinator.client.available


class AdamAudioGroupEntity(Entity):
    """Base entity for the virtual 'All Speakers' device.

    Commands are dispatched concurrently to every real device coordinator.
    State is derived from the collective state of all coordinators.
    """

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the group entity."""
        self._hass = hass
        self._unsub_listeners: list = []
        self._removed = False

    # ── Device info ──────────────────────────────────────────────────────────

    @property
    @override
    def device_info(self) -> DeviceInfo:
        """Return device info for the 'All Speakers' group device."""
        return DeviceInfo(
            identifiers={(DOMAIN, GROUP_DEVICE_ID)},
            name=GROUP_DEVICE_NAME,
            manufacturer=MANUFACTURER,
            model="Group",
        )

    # ── Coordinator helpers ──────────────────────────────────────────────────

    def _all_coordinators(self) -> list[AdamAudioCoordinator]:
        """Return all currently loaded device coordinators."""
        return get_coordinators(self._hass)

    def _coordinators(self) -> list[AdamAudioCoordinator]:
        """Return the speakers that are online: state and commands use only these."""
        return [c for c in self._all_coordinators() if c.client.available]

    async def _async_call_all(self, method_name: str, *args: Any) -> None:
        """Run a client command on every online speaker, then refresh all entities.

        Speakers are commanded concurrently.  The speakers that did apply
        the change are refreshed so the UI reflects them; a HomeAssistantError
        is then raised to surface the failure(s) to the user.

        Speakers whose command failed are deliberately *not* notified:
        async_set_updated_data() would mark their coordinator as having
        updated successfully (clearing UpdateFailed) and push their next poll
        a full interval into the future, hiding the failure.
        """
        coordinators = self._coordinators()
        results = await asyncio.gather(
            *(getattr(c.client, method_name)(*args) for c in coordinators),
            return_exceptions=True,
        )
        for coordinator, result in zip(coordinators, results, strict=True):
            if not isinstance(result, Exception):
                coordinator.async_notify_state()
        if not self._removed:
            self.async_write_ha_state()

        failures = [result for result in results if isinstance(result, Exception)]
        if failures:
            raise HomeAssistantError(
                f"Command failed on {len(failures)} of {len(coordinators)} "
                f"speakers: {failures[0]}"
            )

    # ── HA lifecycle hooks ───────────────────────────────────────────────────

    @override
    async def async_added_to_hass(self) -> None:
        """Follow every coordinator, including ones loaded or reloaded later."""
        self._removed = False
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, SIGNAL_COORDINATORS_CHANGED, self._on_coordinators_changed
            )
        )
        self._subscribe_coordinators()

    def _subscribe_coordinators(self) -> None:
        """Listen to the coordinators that are loaded right now."""
        for unsub in self._unsub_listeners:
            unsub()
        self._unsub_listeners.clear()

        @callback
        def _on_coordinator_update() -> None:
            self.async_write_ha_state()

        for coordinator in self._all_coordinators():
            self._unsub_listeners.append(
                coordinator.async_add_listener(_on_coordinator_update)
            )

    @callback
    def _on_coordinators_changed(self) -> None:
        """A speaker was loaded or unloaded."""
        if self._removed:
            return
        self._subscribe_coordinators()
        self.async_write_ha_state()

    @callback
    @override
    def async_entity_id_changed(self, old_entity_id: str) -> None:
        """Nothing here is keyed on entity_id: opt in to the in-place rename."""
        super().async_entity_id_changed(old_entity_id)

    @override
    async def async_will_remove_from_hass(self) -> None:
        """Clean up coordinator listeners."""
        self._removed = True
        for unsub in self._unsub_listeners:
            unsub()
        self._unsub_listeners.clear()

    @property
    @override
    def available(self) -> bool:
        """Group is available if at least one device is online."""
        return bool(self._coordinators())
