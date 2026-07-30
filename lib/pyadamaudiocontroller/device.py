"""AES70/OCA device abstraction.

Extended from the original pacontrol library by dmach
(https://github.com/dmach/pacontrol) to support direct IP/port construction
and socket lifecycle management required for long-running integrations.

Reliability notes
─────────────────
• The UDP socket is ``connect()``-ed to the device address, so the kernel
  drops datagrams arriving from any other host.
• Every command carries a unique, auto-incrementing handle.  Responses are
  matched on that handle, so stale datagrams (late keepalive acks, responses
  to earlier commands) are skipped instead of being mis-attributed.
• Response status codes are checked: a non-OK status raises
  AdamAudioProtocolError instead of being silently parsed as data.
"""

from __future__ import annotations

import contextlib
import io
import socket
import struct
from types import SimpleNamespace

from .command import Command
from .exceptions import AdamAudioProtocolError
from .keepalive import Keepalive
from .message import Message
from .response import Response
from .types import PDU, OcaInt8, OcaString, OcaType, OcaUint16

# ── AES70 object numbers (targets) used by A-Series monitors ────────────────
_TARGET_DEVICE_MANAGER = 1
_TARGET_INPUT = 16842763
_TARGET_MUTE = 33619989
_TARGET_BASS = 50397285
_TARGET_DESK = 50397286
_TARGET_PRESENCE = 50397287
_TARGET_TREBLE = 50397288
_TARGET_VOICING = 50397289
_TARGET_SLEEP = 50528364
_TARGET_BLINK = 50593804
_TARGET_DESCRIPTION = 50593843

# AES70 method indices: 1 = getter, 2 = setter (on the same method level)
_METHOD_GET = 1
_METHOD_SET = 2

# (target, method_level, param type) for every pollable parameter, in the
# order expected by consumers of get_full_state_pdus().
_STATE_QUERIES: tuple[tuple[int, int, type], ...] = (
    (_TARGET_MUTE, 4, OcaUint16),
    (_TARGET_SLEEP, 4, OcaUint16),
    (_TARGET_INPUT, 4, OcaUint16),
    (_TARGET_VOICING, 4, OcaUint16),
    (_TARGET_BASS, 5, OcaInt8),
    (_TARGET_DESK, 5, OcaInt8),
    (_TARGET_PRESENCE, 5, OcaInt8),
    (_TARGET_TREBLE, 5, OcaInt8),
)


class Device:
    # How many datagrams to inspect while waiting for the response that
    # matches a command handle before giving up.  Each wait is additionally
    # bounded by the socket timeout.
    RESPONSE_MATCH_ATTEMPTS = 8

    # Extra attempts per parameter in get_full_state_pdus() if the first one
    # times out or fails.  A single dropped UDP datagram (common right after
    # a device power-cycle) would otherwise fail the entire batch poll.
    POLL_RETRY_ATTEMPTS = 1

    def __init__(self, info) -> None:
        self.info = info
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Connecting the UDP socket makes the kernel reject datagrams from
        # any address other than the device's.
        self.sock.connect(self.addr)
        self._handle = 0
        self._last_response: Response | None = None

    # ── Alternative constructors ─────────────────────────────────────────────

    @classmethod
    def from_address(cls, host: str, port: int) -> Device:
        """Create a Device from a host/port pair (no zeroconf needed).

        ``host`` may be a dotted IPv4 address or a resolvable hostname
        (e.g. ``aseries-41472b.local``).
        """
        try:
            packed = socket.inet_aton(host)
        except OSError:
            # Not a dotted IPv4 address — resolve as a hostname.
            packed = socket.inet_aton(socket.gethostbyname(host))
        info = SimpleNamespace(
            addresses=[packed],
            port=port,
        )
        return cls(info)

    # ── Socket helpers ───────────────────────────────────────────────────────

    @property
    def addr(self) -> tuple[str, int]:
        return (self.ip, self.port)

    @property
    def ip(self) -> str:
        return socket.inet_ntoa(self.info.addresses[0])

    @property
    def port(self) -> int:
        return self.info.port

    def set_timeout(self, timeout: float) -> None:
        """Set socket receive timeout in seconds.  Must be called after construction."""
        self.sock.settimeout(timeout)

    def close(self) -> None:
        """Release the UDP socket."""
        with contextlib.suppress(OSError):
            self.sock.close()

    def drain(self) -> None:
        """Discard all pending packets in the UDP receive buffer to prevent stale data."""
        original_timeout = self.sock.gettimeout()
        try:
            self.sock.settimeout(0.0)
            while True:
                # Discard up to 1024 bytes at a time until buffer is empty.
                self.sock.recv(1024)
        except OSError:
            # BlockingIOError when the buffer is empty; any other socket
            # error also just ends the drain.
            pass
        finally:
            with contextlib.suppress(OSError):
                self.sock.settimeout(original_timeout)

    # ── Low-level I/O ────────────────────────────────────────────────────────

    def send_bytes(self, data: bytes) -> None:
        self.sock.send(data)

    def receive_bytes(self) -> bytes:
        return self.sock.recv(1024)

    def send_pdus(self, pdus: list[PDU]) -> None:
        if not pdus:
            raise ValueError("List of PDUs must not be empty")
        pdu_type = pdus[0].PDU_TYPE
        encoded_pdus: bytes = b""
        for pdu in pdus:
            if pdu_type != pdu.PDU_TYPE:
                raise ValueError("All PDUs must have the same type")
            encoded_pdus += pdu.encode()
        message = Message(
            protocol_version=1,
            message_size=struct.calcsize(Message.FORMAT) - 1 + len(encoded_pdus),
            pdu_type=pdu_type,
            pdu_count=len(pdus),
        )
        self.send_bytes(message.encode() + encoded_pdus)

    def receive_response(self, param_types: list[type] | None = None) -> Response:
        """Receive a single Response PDU (no handle matching)."""
        data = self.receive_bytes()
        stream = io.BytesIO(data)
        message = Message.decode(stream)
        if message.pdu_type != Response.PDU_TYPE:
            raise AdamAudioProtocolError(
                f"Expected response PDU type {Response.PDU_TYPE}, got {message.pdu_type}"
            )
        if message.pdu_count < 1:
            raise AdamAudioProtocolError("Expected at least 1 PDU in response")
        self._last_response = Response.decode(stream, param_types)
        return self._last_response

    def receive_responses(self, expected_ptypes: list[list[type]]) -> list[Response]:
        """Receive a multi-PDU response message and return all PDUs."""
        data = self.receive_bytes()
        stream = io.BytesIO(data)
        message = Message.decode(stream)
        if message.pdu_type != Response.PDU_TYPE:
            raise AdamAudioProtocolError(
                f"Expected response PDU type {Response.PDU_TYPE}, got {message.pdu_type}"
            )

        responses = []
        for i in range(message.pdu_count):
            # Use the requested param types for this PDU index, or empty list if extra
            ptypes = expected_ptypes[i] if i < len(expected_ptypes) else []
            resp = Response.decode(stream, ptypes)
            responses.append(resp)
            self._last_response = resp
        return responses

    def receive_matching_response(
        self, handle: int, param_types: list[type] | None = None
    ) -> Response:
        """Receive the Response PDU whose handle matches ``handle``.

        Datagrams that are not responses (e.g. late keepalive acks) or whose
        handle belongs to an earlier command are skipped.  Raises
        AdamAudioProtocolError if the device reports a non-OK status or if no
        matching response arrives within RESPONSE_MATCH_ATTEMPTS datagrams.
        Raises TimeoutError (via the socket timeout) if the device goes quiet.
        """
        for _ in range(self.RESPONSE_MATCH_ATTEMPTS):
            stream = io.BytesIO(self.receive_bytes())
            try:
                message = Message.decode(stream)
            except AdamAudioProtocolError:
                continue  # garbage datagram — keep waiting
            if message.pdu_type != Response.PDU_TYPE:
                continue  # e.g. keepalive ack — not for us
            for _ in range(message.pdu_count):
                response = Response.decode(stream)
                if response.handle != handle:
                    continue  # stale response from an earlier command
                if response.status_code != Response.STATUS_OK:
                    raise AdamAudioProtocolError(
                        f"Device returned status {response.status_code} "
                        f"for command handle {handle}"
                    )
                response.parse_params(param_types or [])
                self._last_response = response
                return response
        raise AdamAudioProtocolError(
            f"No response for command handle {handle} after "
            f"{self.RESPONSE_MATCH_ATTEMPTS} datagrams"
        )

    # ── Command helpers ──────────────────────────────────────────────────────

    def _allocate_handle(self) -> int:
        """Return a unique handle for the next command (wraps at 32 bits)."""
        self._handle = self._handle % 0xFFFFFFFF + 1
        return self._handle

    def _command(
        self,
        target: int,
        method_level: int,
        method_index: int,
        method_params: list[OcaType] | None = None,
    ) -> int:
        """Send a command PDU and return its handle."""
        handle = self._allocate_handle()
        self.send_pdus(
            [
                Command(
                    handle=handle,
                    target=target,
                    method_level=method_level,
                    method_index=method_index,
                    method_params=method_params,
                )
            ]
        )
        return handle

    def _request(
        self,
        target: int,
        method_level: int,
        method_index: int,
        param_types: list[type],
        method_params: list[OcaType] | None = None,
    ) -> Response:
        """Send a command and wait for its matching response."""
        handle = self._command(target, method_level, method_index, method_params)
        return self.receive_matching_response(handle, param_types)

    def _request_with_retry(
        self,
        target: int,
        method_level: int,
        method_index: int,
        param_types: list[type],
        method_params: list[OcaType] | None = None,
    ) -> Response:
        """Like ``_request``, but retries up to POLL_RETRY_ATTEMPTS times.

        Used by get_full_state_pdus() so a single dropped or mismatched
        datagram doesn't fail the whole batch poll.
        """
        last_error: Exception | None = None
        for _ in range(self.POLL_RETRY_ATTEMPTS + 1):
            try:
                return self._request(
                    target, method_level, method_index, param_types, method_params
                )
            except (OSError, AdamAudioProtocolError) as err:
                last_error = err
        assert last_error is not None
        raise last_error

    # ── Session management ───────────────────────────────────────────────────

    def send_keepalive(self, timeout_secs: float = 2.0) -> None:
        """Send keepalive packet. Defaults to a short timeout for the response."""
        original_timeout = self.sock.gettimeout()
        self.sock.settimeout(timeout_secs)
        try:
            self.send_pdus([Keepalive(timeout=30)])
            self.receive_bytes()
        finally:
            self.sock.settimeout(original_timeout)

    # ── Batched Polling ──────────────────────────────────────────────────────

    def get_full_state_pdus(self) -> list[Response]:
        """
        Query all 8 controllable parameters sequentially.
        Each command is sent and its response received individually, because
        the device responds with separate UDP packets per command.
        Returns a list of 8 Response objects in the order of _STATE_QUERIES
        (mute, sleep, input, voicing, bass, desk, presence, treble).

        Each parameter gets up to POLL_RETRY_ATTEMPTS extra tries if its
        request times out or fails, since a single dropped datagram
        shouldn't fail the entire poll.
        """
        return [
            self._request_with_retry(target, method_level, _METHOD_GET, [ptype])
            for target, method_level, ptype in _STATE_QUERIES
        ]

    # ── Device metadata ──────────────────────────────────────────────────────

    def get_serial_number(self) -> str:
        return self._request(_TARGET_DEVICE_MANAGER, 3, 3, [OcaString]).params[0].value

    def get_name(self) -> str:
        return self._request(_TARGET_DEVICE_MANAGER, 3, 4, [OcaString]).params[0].value

    def get_description(self) -> str:
        return (
            self._request(_TARGET_DESCRIPTION, 5, _METHOD_GET, [OcaString])
            .params[0]
            .value
        )

    def set_description(self, value: str) -> None:
        self._command(_TARGET_DESCRIPTION, 5, _METHOD_SET, [OcaString(value)])

    # ── Power / routing ──────────────────────────────────────────────────────

    def set_sleep(self, value: bool) -> None:
        """Put device into standby (True) or wake it up (False)."""
        self._command(_TARGET_SLEEP, 4, _METHOD_SET, [OcaUint16(int(value))])

    def set_mute(self, value: bool) -> None:
        """Mute (True) or unmute (False) the device."""
        val = 5 if value else 1
        self._command(_TARGET_MUTE, 4, _METHOD_SET, [OcaUint16(val)])

    def set_input(self, value: int) -> None:
        """Select input: 0 = RCA, 1 = XLR."""
        if value not in (0, 1):
            raise ValueError(f"Input value must be 0 or 1, got {value}")
        self._command(_TARGET_INPUT, 4, _METHOD_SET, [OcaUint16(value)])

    # ── EQ ───────────────────────────────────────────────────────────────────

    def set_bass(self, value: int) -> None:
        """Bass correction: -2, -1, 0, +1 (Pure and UNR voicings)."""
        if not (-2 <= value <= 1):
            raise ValueError(f"Bass value {value} out of range -2..1")
        self._command(_TARGET_BASS, 5, _METHOD_SET, [OcaInt8(value)])

    def set_desk(self, value: int) -> None:
        """Desk correction: -2, -1, 0 (Pure and UNR voicings)."""
        if not (-2 <= value <= 0):
            raise ValueError(f"Desk value {value} out of range -2..0")
        self._command(_TARGET_DESK, 5, _METHOD_SET, [OcaInt8(value)])

    def set_presence(self, value: int) -> None:
        """Presence correction: -1, 0, +1 (Pure and UNR voicings)."""
        if not (-1 <= value <= 1):
            raise ValueError(f"Presence value {value} out of range -1..1")
        self._command(_TARGET_PRESENCE, 5, _METHOD_SET, [OcaInt8(value)])

    def set_treble(self, value: int) -> None:
        """Treble correction: -1, 0, +1 (Pure and UNR voicings)."""
        if not (-1 <= value <= 1):
            raise ValueError(f"Treble value {value} out of range -1..1")
        self._command(_TARGET_TREBLE, 5, _METHOD_SET, [OcaInt8(value)])

    # ── Voicing ──────────────────────────────────────────────────────────────

    def set_voicing(self, value: int) -> None:
        """
        Set voicing:
          0 = Pure  (flat, highly accurate)
          1 = UNR   (Uniform Natural Response)
          2 = Ext.  (Extended — use with Advanced / Sonarworks)
        """
        if value not in (0, 1, 2):
            raise ValueError(f"Voicing value must be 0, 1, or 2, got {value}")
        self._command(_TARGET_VOICING, 4, _METHOD_SET, [OcaUint16(value)])

    # ── Diagnostics ──────────────────────────────────────────────────────────

    def blink(self) -> None:
        """Identify device by blinking its LED."""
        self._command(_TARGET_BLINK, 5, _METHOD_SET, [OcaUint16(0x0101)])

    # ── GET methods (method_index=1 per AES70/OCA spec) ───────────────────────
    #
    # These mirror every SET method and let us read back the current device
    # state so that physical knob changes and A Control app changes are
    # reflected in Home Assistant.
    #
    # The device returns a Response PDU whose param matches the SET type.

    def get_mute(self) -> bool:
        """
        Read current mute state.
        Device returns OcaUint16: 1 = unmuted, 5 = muted.
        """
        response = self._request(_TARGET_MUTE, 4, _METHOD_GET, [OcaUint16])
        return response.params[0].value == 5

    def get_sleep(self) -> bool:
        """Read current sleep/standby state. Device returns OcaUint16: 0=awake, 1=sleep."""
        response = self._request(_TARGET_SLEEP, 4, _METHOD_GET, [OcaUint16])
        return bool(response.params[0].value)

    def get_input(self) -> int:
        """Read current input selection. Returns 0 (RCA) or 1 (XLR)."""
        response = self._request(_TARGET_INPUT, 4, _METHOD_GET, [OcaUint16])
        return int(response.params[0].value)

    def get_voicing(self) -> int:
        """Read current voicing. Returns 0 (Pure), 1 (UNR) or 2 (Ext)."""
        response = self._request(_TARGET_VOICING, 4, _METHOD_GET, [OcaUint16])
        return int(response.params[0].value)

    def get_bass(self) -> int:
        """Read current bass correction (−2 to +1)."""
        response = self._request(_TARGET_BASS, 5, _METHOD_GET, [OcaInt8])
        return int(response.params[0].value)

    def get_desk(self) -> int:
        """Read current desk correction (−2 to 0)."""
        response = self._request(_TARGET_DESK, 5, _METHOD_GET, [OcaInt8])
        return int(response.params[0].value)

    def get_presence(self) -> int:
        """Read current presence correction (−1 to +1)."""
        response = self._request(_TARGET_PRESENCE, 5, _METHOD_GET, [OcaInt8])
        return int(response.params[0].value)

    def get_treble(self) -> int:
        """Read current treble correction (−1 to +1)."""
        response = self._request(_TARGET_TREBLE, 5, _METHOD_GET, [OcaInt8])
        return int(response.params[0].value)
