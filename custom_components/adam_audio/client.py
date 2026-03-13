"""
Async-safe client wrapper around the pacontrol Device.

All blocking socket I/O runs in HA's executor thread pool so the event loop
is never blocked.  A single asyncio.Lock serialises all access so commands
and polls never interleave on the UDP socket.

State management
────────────────
• SET commands update ``self.state`` optimistically so the UI responds
  instantly without waiting for the next poll cycle.
• ``async_fetch_state()`` polls all 9 GET commands from the device and
  overwrites ``self.state`` with the real values.  This is called by the
  coordinator on every update interval.
• The polling is now batched into a single UDP request for 0.1s response time.
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Callable

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .pacontrol.device import Device

_LOGGER = logging.getLogger(__name__)


@dataclass
class AdamAudioState:
    """Current device state."""
    mute: bool = False
    sleep: bool = False
    input_source: int = 1
    voicing: int = 0
    volume: float = 0.0
    bass: int = 0
    desk: int = 0
    presence: int = 0
    treble: int = 0


class AdamAudioClient:
    """Manages one UDP connection to a single ADAM Audio A-Series device."""

    SOCKET_TIMEOUT: float = 10.0
    KEEPALIVE_TIMEOUT: int = 30

    def __init__(self, hass: HomeAssistant, host: str, port: int) -> None:
        self._hass = hass
        self.host = host
        self.port = port
        self._device: Device | None = None
        self._lock = asyncio.Lock()
        self._last_keepalive: float = 0.0
        self.available: bool = False
        self.device_name: str = ""
        self.description: str = ""
        self.serial: str = ""
        self.state = AdamAudioState()

    async def async_setup(self) -> bool:
        """Connect to the device and fetch metadata."""
        return await self._hass.async_add_executor_job(self._setup)

    def _setup(self) -> bool:
        try:
            self._device = Device.from_address(self.host, self.port)
            self._device.set_timeout(self.SOCKET_TIMEOUT)
            self._device.send_keepalive()
            self._last_keepalive = time.monotonic()
            self.device_name = self._device.get_name()
            self.description = self._device.get_description()
            self.serial = self._device.get_serial_number()
            self.available = True
            _LOGGER.info("Connected to ADAM Audio '%s' at %s", self.description, self.host)
            return True
        except OSError as err:
            _LOGGER.warning("Cannot reach ADAM Audio device at %s — %s", self.host, err)
            self.available = False
            return False

    async def async_shutdown(self) -> None:
        """Release the UDP socket."""
        if self._device is not None:
            await self._hass.async_add_executor_job(self._device.close)

    async def async_fetch_state(self) -> bool:
        """Autoritative full state poll via a single batched UDP request."""
        async with self._lock:
            try:
                success = await self._hass.async_add_executor_job(self._fetch_state_blocking)
                self.available = success
                return success
            except Exception as err:
                _LOGGER.debug("State fetch critical failure for %s: %s", self.host, err)
                self.available = False
                return False

    def _fetch_state_blocking(self) -> bool:
        """Executor target for batched state polling."""
        if not self._device:
            return False
            
        self._device.drain()

        # Opportunistic keepalive - don't let a keepalive timeout kill the whole poll
        try:
            now = time.monotonic()
            if self._last_keepalive == 0.0 or (now - self._last_keepalive > self.KEEPALIVE_TIMEOUT / 2):
                self._device.send_keepalive(timeout_secs=5.0)
                self._last_keepalive = now
        except OSError:
            # Drain any late-arriving keepalive response so it doesn't
            # get read by the batch poll below.
            self._device.drain()

        try:
            responses = self._device.get_full_state_pdus()
            if not responses or len(responses) < 9:
                return False

            # Maps response indices to state attributes
            self.state.mute = (responses[0].params[0].value == 5)
            self.state.sleep = bool(responses[1].params[0].value)
            self.state.input_source = int(responses[2].params[0].value)
            self.state.voicing = int(responses[3].params[0].value)
            self.state.volume = responses[4].params[0].value / 2.0
            self.state.bass = int(responses[5].params[0].value)
            self.state.desk = int(responses[6].params[0].value)
            self.state.presence = int(responses[7].params[0].value)
            self.state.treble = int(responses[8].params[0].value)

            return True
        except Exception as err:
            _LOGGER.warning("Batched poll failed for %s: %s", self.host, err)
            return False

    async def _async_send(self, fn: Callable, *args) -> None:
        """Send a single SET command and handle the session locking."""
        async with self._lock:
            try:
                await self._hass.async_add_executor_job(self._run, fn, *args)
                self.available = True
            except OSError as err:
                self.available = False
                _LOGGER.error("Command to %s failed: %s", self.host, err)
                raise HomeAssistantError(f"Command to {self.host} failed: {err}") from err

    def _run(self, fn: Callable, *args) -> None:
        """Executor target for SET commands."""
        # Simple ensuring of session before sending
        if time.monotonic() - self._last_keepalive > self.KEEPALIVE_TIMEOUT / 2:
            try:
                self._device.send_keepalive(timeout_secs=2.0)
                self._last_keepalive = time.monotonic()
            except OSError:
                pass
        fn(*args)

    # ── Public SET API ───────────────────────────────────────────────────────

    async def async_set_mute(self, value: bool) -> None:
        await self._async_send(self._device.set_mute, value)
        self.state.mute = value

    async def async_set_sleep(self, value: bool) -> None:
        await self._async_send(self._device.set_sleep, value)
        self.state.sleep = value

    async def async_set_input(self, value: int) -> None:
        await self._async_send(self._device.set_input, value)
        self.state.input_source = value

    async def async_set_voicing(self, value: int) -> None:
        await self._async_send(self._device.set_voicing, value)
        self.state.voicing = value

    async def async_set_volume(self, db_value: float) -> None:
        raw = int(round(db_value * 2))
        await self._async_send(self._device.set_level, raw)
        self.state.volume = db_value

    async def async_set_bass(self, value: int) -> None:
        await self._async_send(self._device.set_bass, value)
        self.state.bass = value

    async def async_set_desk(self, value: int) -> None:
        await self._async_send(self._device.set_desk, value)
        self.state.desk = value

    async def async_set_presence(self, value: int) -> None:
        await self._async_send(self._device.set_presence, value)
        self.state.presence = value

    async def async_set_treble(self, value: int) -> None:
        await self._async_send(self._device.set_treble, value)
        self.state.treble = value
