"""
AES70/OCA device abstraction.
Extended from the original pacontrol library by dmach
(https://github.com/dmach/pacontrol) to support direct IP/port construction
and socket lifecycle management required for long-running integrations.
"""
from __future__ import annotations

import io
import socket
import struct
from types import SimpleNamespace
from typing import List

from .command import Command
from .keepalive import Keepalive
from .message import Message
from .response import Response
from .types import OcaInt8, OcaString, OcaUint16, PDU


class Device:
    def __init__(self, info) -> None:
        self.info = info
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._last_response: "Response" | None = None

    # ── Alternative constructors ─────────────────────────────────────────────

    @classmethod
    def from_address(cls, host: str, port: int) -> "Device":
        """Create a Device directly from a host/port pair (no zeroconf needed)."""
        info = SimpleNamespace(
            addresses=[socket.inet_aton(host)],
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
        try:
            self.sock.close()
        except OSError:
            pass

    def drain(self) -> None:
        """Discard all pending packets in the UDP receive buffer to prevent stale data."""
        original_timeout = self.sock.gettimeout()
        self.sock.settimeout(0.0)
        try:
            while True:
                # Discard up to 1024 bytes at a time until buffer is empty.
                self.sock.recvfrom(1024)
        except (BlockingIOError, socket.timeout, OSError):
            pass
        finally:
            self.sock.settimeout(original_timeout)

    # ── Low-level I/O ────────────────────────────────────────────────────────

    def send_bytes(self, data: bytes) -> None:
        self.sock.sendto(data, self.addr)

    def receive_bytes(self) -> bytes:
        return self.sock.recvfrom(1024)[0]

    def send_pdus(self, pdus: List[PDU]) -> None:
        if not pdus:
            raise ValueError("List of PDUs must not be empty")
        pdu_type = pdus[0].PDU_TYPE
        encoded_pdus: bytes = b""
        for pdu in pdus:
            if pdu.PDU_TYPE != pdu_type:
                raise ValueError("All PDUs must have the same type")
            encoded_pdus += pdu.encode()
        message = Message(
            protocol_version=1,
            message_size=struct.calcsize(Message.FORMAT) - 1 + len(encoded_pdus),
            pdu_type=pdu_type,
            pdu_count=len(pdus),
        )
        self.send_bytes(message.encode() + encoded_pdus)

    def receive_response(self, param_types: List[type] | None = None) -> Response:
        """Receive a single Response PDU."""
        data = self.receive_bytes()
        stream = io.BytesIO(data)
        message = Message.decode(stream)
        if message.pdu_type != Response.PDU_TYPE:
            raise ValueError(f"Expected response PDU type {Response.PDU_TYPE}, got {message.pdu_type}")
        if message.pdu_count < 1:
            raise ValueError("Expected at least 1 PDU in response")
        self._last_response = Response.decode(stream, param_types)
        return self._last_response

    def receive_responses(self, expected_ptypes: List[List[type]]) -> List[Response]:
        """Receive a multi-PDU response message and return all PDUs."""
        data = self.receive_bytes()
        stream = io.BytesIO(data)
        message = Message.decode(stream)
        if message.pdu_type != Response.PDU_TYPE:
            raise ValueError(f"Expected response PDU type {Response.PDU_TYPE}, got {message.pdu_type}")

        responses = []
        for i in range(message.pdu_count):
            # Use the requested param types for this PDU index, or empty list if extra
            ptypes = expected_ptypes[i] if i < len(expected_ptypes) else []
            resp = Response.decode(stream, ptypes)
            responses.append(resp)
            self._last_response = resp
        return responses

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

    def get_full_state_pdus(self) -> List[Response]:
        """
        Query all 9 controllable parameters sequentially.
        Each command is sent and its response received individually, because
        the device responds with separate UDP packets per command.
        Returns a list of 9 Response objects.
        """
        commands_and_types = [
            (Command(handle=1, target=33619989, method_level=4, method_index=1), [OcaUint16]),  # mute
            (Command(handle=2, target=50528364, method_level=4, method_index=1), [OcaUint16]),  # sleep
            (Command(handle=3, target=16842763, method_level=4, method_index=1), [OcaUint16]),  # input
            (Command(handle=4, target=50397289, method_level=4, method_index=1), [OcaUint16]),  # voicing
            (Command(handle=5, target=16842754, method_level=5, method_index=1), [OcaInt8]),    # volume
            (Command(handle=6, target=50397285, method_level=5, method_index=1), [OcaInt8]),    # bass
            (Command(handle=7, target=50397286, method_level=5, method_index=1), [OcaInt8]),    # desk
            (Command(handle=8, target=50397287, method_level=5, method_index=1), [OcaInt8]),    # presence
            (Command(handle=9, target=50397288, method_level=5, method_index=1), [OcaInt8]),    # treble
        ]
        responses = []
        for cmd, ptypes in commands_and_types:
            self.send_pdus([cmd])
            resp = self.receive_response(ptypes)
            responses.append(resp)
        return responses

    # ── Device metadata ──────────────────────────────────────────────────────

    def get_serial_number(self) -> str:
        self.send_pdus([Command(handle=0, target=1, method_level=3, method_index=3)])
        return self.receive_response([OcaString]).params[0].value

    def get_name(self) -> str:
        self.send_pdus([Command(handle=0, target=1, method_level=3, method_index=4)])
        return self.receive_response([OcaString]).params[0].value

    def get_description(self) -> str:
        self.send_pdus([Command(handle=0, target=50593843, method_level=5, method_index=1)])
        return self.receive_response([OcaString]).params[0].value

    def set_description(self, value: str) -> None:
        self.send_pdus([Command(
            handle=59, target=50593843, method_level=5, method_index=2,
            method_params=[OcaString(value)],
        )])

    # ── Power / routing ──────────────────────────────────────────────────────

    def set_sleep(self, value: bool) -> None:
        """Put device into standby (True) or wake it up (False)."""
        self.send_pdus([Command(
            handle=0, target=50528364, method_level=4, method_index=2,
            method_params=[OcaUint16(int(value))],
        )])

    def set_mute(self, value: bool) -> None:
        """Mute (True) or unmute (False) the device."""
        val = 5 if value else 1
        self.send_pdus([Command(
            handle=0, target=33619989, method_level=4, method_index=2,
            method_params=[OcaUint16(val)],
        )])

    def set_input(self, value: int) -> None:
        """Select input: 0 = RCA, 1 = XLR."""
        if value not in (0, 1):
            raise ValueError(f"Input value must be 0 or 1, got {value}")
        self.send_pdus([Command(
            handle=0, target=16842763, method_level=4, method_index=2,
            method_params=[OcaUint16(value)],
        )])

    # ── Volume ───────────────────────────────────────────────────────────────

    def set_level(self, value: int) -> None:
        """
        Set volume level.  Applicable to Ext. voicing.
        Signed integer in 0.5 dB steps: -40 = -20 dB … +12 = +6 dB.
        """
        if not (-40 <= value <= 12):
            raise ValueError(f"Level {value} out of range -40..12")
        self.send_pdus([Command(
            handle=0, target=16842754, method_level=5, method_index=2,
            method_params=[OcaInt8(value)],
        )])

    # ── EQ ───────────────────────────────────────────────────────────────────

    def set_bass(self, value: int) -> None:
        """Bass correction: -2, -1, 0, +1 (Pure and UNR voicings)."""
        if not (-2 <= value <= 1):
            raise ValueError(f"Bass value {value} out of range -2..1")
        self.send_pdus([Command(
            handle=0, target=50397285, method_level=5, method_index=2,
            method_params=[OcaInt8(value)],
        )])

    def set_desk(self, value: int) -> None:
        """Desk correction: -2, -1, 0 (Pure and UNR voicings)."""
        if not (-2 <= value <= 0):
            raise ValueError(f"Desk value {value} out of range -2..0")
        self.send_pdus([Command(
            handle=0, target=50397286, method_level=5, method_index=2,
            method_params=[OcaInt8(value)],
        )])

    def set_presence(self, value: int) -> None:
        """Presence correction: -1, 0, +1 (Pure and UNR voicings)."""
        if not (-1 <= value <= 1):
            raise ValueError(f"Presence value {value} out of range -1..1")
        self.send_pdus([Command(
            handle=0, target=50397287, method_level=5, method_index=2,
            method_params=[OcaInt8(value)],
        )])

    def set_treble(self, value: int) -> None:
        """Treble correction: -1, 0, +1 (Pure and UNR voicings)."""
        if not (-1 <= value <= 1):
            raise ValueError(f"Treble value {value} out of range -1..1")
        self.send_pdus([Command(
            handle=0, target=50397288, method_level=5, method_index=2,
            method_params=[OcaInt8(value)],
        )])

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
        self.send_pdus([Command(
            handle=54, target=50397289, method_level=4, method_index=2,
            method_params=[OcaUint16(value)],
        )])

    # ── Diagnostics ──────────────────────────────────────────────────────────

    def blink(self) -> None:
        """Identify device by blinking its LED."""
        self.send_pdus([Command(
            handle=52, target=50593804, method_level=5, method_index=2,
            method_params=[OcaUint16(0x0101)],
        )])

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
        self.send_pdus([Command(
            handle=0, target=33619989, method_level=4, method_index=1,
        )])
        response = self.receive_response([OcaUint16])
        return response.params[0].value == 5

    def get_sleep(self) -> bool:
        """Read current sleep/standby state. Device returns OcaUint16: 0=awake, 1=sleep."""
        self.send_pdus([Command(
            handle=0, target=50528364, method_level=4, method_index=1,
        )])
        response = self.receive_response([OcaUint16])
        return bool(response.params[0].value)

    def get_input(self) -> int:
        """Read current input selection. Returns 0 (RCA) or 1 (XLR)."""
        self.send_pdus([Command(
            handle=0, target=16842763, method_level=4, method_index=1,
        )])
        response = self.receive_response([OcaUint16])
        return int(response.params[0].value)

    def get_voicing(self) -> int:
        """Read current voicing. Returns 0 (Pure), 1 (UNR) or 2 (Ext)."""
        self.send_pdus([Command(
            handle=54, target=50397289, method_level=4, method_index=1,
        )])
        response = self.receive_response([OcaUint16])
        return int(response.params[0].value)

    def get_level(self) -> int:
        """
        Read current volume level as raw device integer.
        Divide by 2 to get dB (range −40..+12 raw = −20..+6 dB).
        """
        self.send_pdus([Command(
            handle=0, target=16842754, method_level=5, method_index=1,
        )])
        response = self.receive_response([OcaInt8])
        return int(response.params[0].value)

    def get_bass(self) -> int:
        """Read current bass correction (−2 to +1)."""
        self.send_pdus([Command(
            handle=0, target=50397285, method_level=5, method_index=1,
        )])
        response = self.receive_response([OcaInt8])
        return int(response.params[0].value)

    def get_desk(self) -> int:
        """Read current desk correction (−2 to 0)."""
        self.send_pdus([Command(
            handle=0, target=50397286, method_level=5, method_index=1,
        )])
        response = self.receive_response([OcaInt8])
        return int(response.params[0].value)

    def get_presence(self) -> int:
        """Read current presence correction (−1 to +1)."""
        self.send_pdus([Command(
            handle=0, target=50397287, method_level=5, method_index=1,
        )])
        response = self.receive_response([OcaInt8])
        return int(response.params[0].value)

    def get_treble(self) -> int:
        """Read current treble correction (−1 to +1)."""
        self.send_pdus([Command(
            handle=0, target=50397288, method_level=5, method_index=1,
        )])
        response = self.receive_response([OcaInt8])
        return int(response.params[0].value)
