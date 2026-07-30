"""Tests for ADAM Audio OCA device protocol."""

import struct
from unittest.mock import MagicMock, patch

from pyadamaudiocontroller.command import Command
from pyadamaudiocontroller.device import Device
from pyadamaudiocontroller.exceptions import AdamAudioProtocolError
from pyadamaudiocontroller.keepalive import Keepalive
from pyadamaudiocontroller.types import OcaUint16
import pytest


@pytest.fixture
def mock_socket() -> MagicMock:
    """Fixture for a mock socket."""
    with patch("pyadamaudiocontroller.device.socket.socket") as mock:
        sock = mock.return_value
        yield sock


def _response_datagram(
    handle: int, status: int = 0, params: bytes = b"", pdu_count: int = 1
) -> bytes:
    """Build a raw OCP.1 datagram containing one Response PDU."""
    pdu = struct.pack("!IIBB", 10 + len(params), handle, status, 1) + params
    header = struct.pack("!BHIBH", 0x3B, 1, 9 + len(pdu), 3, pdu_count)
    return header + pdu


def _keepalive_datagram() -> bytes:
    """Build a raw OCP.1 keepalive datagram."""
    return struct.pack("!BHIBH", 0x3B, 1, 11, 4, 1) + struct.pack("!H", 30)


def test_device_connect_disconnect(mock_socket: MagicMock) -> None:
    """Test device connection."""
    device = Device.from_address("192.168.1.100", 49494)
    mock_socket.connect.assert_called_once_with(("192.168.1.100", 49494))

    device.send_keepalive()
    assert mock_socket.send.call_count == 1

    device.close()
    mock_socket.close.assert_called_once()


def test_device_from_hostname(mock_socket: MagicMock) -> None:
    """Test from_address resolves a hostname to an IP address."""
    with patch(
        "pyadamaudiocontroller.device.socket.gethostbyname",
        return_value="192.168.1.50",
    ) as mock_resolve:
        device = Device.from_address("aseries-41472b.local", 49494)

    mock_resolve.assert_called_once_with("aseries-41472b.local")
    assert device.ip == "192.168.1.50"


def test_device_getters(mock_socket: MagicMock) -> None:
    """Test device property getters."""
    device = Device.from_address("192.168.1.100", 49494)

    # Mocking response for a GET command
    with (
        patch.object(device, "send_pdus") as mock_send,
        patch.object(device, "receive_matching_response") as mock_fetch,
    ):
        # Simulate string response for get_name, get_description, get_serial_number
        response = MagicMock()
        response.params = [MagicMock()]
        response.params[0].value = "A7V"
        mock_fetch.return_value = response

        assert device.get_name() == "A7V"
        assert device.get_description() == "A7V"
        assert device.get_serial_number() == "A7V"
        assert mock_send.call_count == 3

        # Simulate integer response for getters
        response.params[0].value = 1
        assert device.get_input() == 1
        assert device.get_voicing() == 1
        assert device.get_bass() == 1
        assert device.get_desk() == 1
        assert device.get_presence() == 1
        assert device.get_treble() == 1

        # simulate response for get_mute
        response.params[0].value = 5  # 5 = True for mute
        assert device.get_mute() is True

        # simulate response for get_sleep
        response.params[0].value = 1  # 1 = True for sleep
        assert device.get_sleep() is True


def test_device_unique_handles(mock_socket: MagicMock) -> None:
    """Test every command gets a unique, incrementing handle."""
    device = Device.from_address("192.168.1.100", 49494)

    handles = []
    with patch.object(device, "send_pdus") as mock_send:
        device.set_mute(True)
        device.set_sleep(False)
        device.set_input(1)
        handles = [call.args[0][0].handle for call in mock_send.call_args_list]

    assert handles == [1, 2, 3]


def test_device_setters(mock_socket: MagicMock) -> None:
    """Test device property setters."""
    device = Device.from_address("192.168.1.100", 49494)

    with patch.object(device, "send_pdus") as mock_send:
        device.set_mute(True)
        device.set_sleep(False)
        device.set_input(1)
        device.set_voicing(2)
        device.set_bass(-1)
        device.set_desk(-1)
        device.set_presence(1)
        device.set_treble(1)
        device.set_description("Left")
        device.blink()

        assert mock_send.call_count == 10


def test_device_setter_value_errors(mock_socket: MagicMock) -> None:
    """Test exceptions on out-of-bounds setter values."""
    device = Device.from_address("192.168.1.100", 49494)
    with pytest.raises(ValueError, match="Input value must be 0 or 1"):
        device.set_input(3)
    with pytest.raises(ValueError, match=r"Bass value .* out of range"):
        device.set_bass(5)
    with pytest.raises(ValueError, match=r"Desk value .* out of range"):
        device.set_desk(-5)
    with pytest.raises(ValueError, match=r"Presence value .* out of range"):
        device.set_presence(2)
    with pytest.raises(ValueError, match=r"Treble value .* out of range"):
        device.set_treble(2)
    with pytest.raises(ValueError, match="Voicing value must be 0, 1, or 2"):
        device.set_voicing(5)


def test_device_drain(mock_socket: MagicMock) -> None:
    mock_socket.recv.side_effect = [b"data1", b"data2", BlockingIOError()]
    device = Device.from_address("192.168.1.100", 49494)
    device.drain()
    assert mock_socket.recv.call_count == 3


def test_device_receive_matching_response(mock_socket: MagicMock) -> None:
    """Test matching receive skips stale datagrams and returns the right one."""
    device = Device.from_address("192.168.1.100", 49494)
    mock_socket.recv.side_effect = [
        _keepalive_datagram(),  # late keepalive ack — skipped
        _response_datagram(handle=1, params=b"\x00\x01"),  # stale — skipped
        b"\x00garbage",  # malformed — skipped
        _response_datagram(handle=7, params=b"\x00\x05"),  # ours
    ]

    response = device.receive_matching_response(7, [OcaUint16])
    assert response.handle == 7
    assert response.params[0].value == 5
    assert mock_socket.recv.call_count == 4


def test_device_receive_matching_response_status_error(
    mock_socket: MagicMock,
) -> None:
    """Test a non-OK device status raises AdamAudioProtocolError."""
    device = Device.from_address("192.168.1.100", 49494)
    mock_socket.recv.return_value = _response_datagram(handle=3, status=2)

    with pytest.raises(AdamAudioProtocolError, match="status 2"):
        device.receive_matching_response(3, [OcaUint16])


def test_device_receive_matching_response_exhausted(mock_socket: MagicMock) -> None:
    """Test giving up after RESPONSE_MATCH_ATTEMPTS non-matching datagrams."""
    device = Device.from_address("192.168.1.100", 49494)
    mock_socket.recv.return_value = _keepalive_datagram()

    with pytest.raises(AdamAudioProtocolError, match="No response"):
        device.receive_matching_response(1)
    assert mock_socket.recv.call_count == Device.RESPONSE_MATCH_ATTEMPTS


@patch("pyadamaudiocontroller.device.Message.decode")
@patch("pyadamaudiocontroller.device.Response.decode")
def test_device_receive_response(
    mock_resp_decode, mock_msg_decode, mock_socket: MagicMock
) -> None:
    device = Device.from_address("192.168.1.100", 49494)
    # mock raw socket
    mock_socket.recv.return_value = b"some bytes"

    # mock decoded message
    msg = MagicMock()
    msg.pdu_type = 3  # Response PDU_TYPE
    msg.pdu_count = 1
    mock_msg_decode.return_value = msg

    # mock decoded response
    resp = MagicMock()
    mock_resp_decode.return_value = resp

    out = device.receive_response()
    assert out == resp

    out_multi = device.receive_responses([[int]])
    assert out_multi == [resp]


def test_device_get_full_state_pdus(mock_socket: MagicMock) -> None:
    device = Device.from_address("192.168.1.100", 49494)
    with (
        patch.object(device, "send_pdus") as mock_send,
        patch.object(device, "receive_matching_response") as mock_recv,
    ):
        mock_recv.return_value = MagicMock()

        responses = device.get_full_state_pdus()
        assert len(responses) == 8
        assert mock_send.call_count == 8


def test_device_get_full_state_pdus_retries_transient_failure(
    mock_socket: MagicMock,
) -> None:
    """A single dropped datagram for one parameter is retried, not fatal.

    Devices commonly drop one UDP request while powering back on; the batch
    poll should retry that single request rather than failing all 8.
    """
    device = Device.from_address("192.168.1.100", 49494)
    good_response = MagicMock()
    with (
        patch.object(device, "send_pdus") as mock_send,
        patch.object(device, "receive_matching_response") as mock_recv,
    ):
        mock_recv.side_effect = [
            TimeoutError("no response"),  # 1st param: 1st attempt drops
            good_response,  # 1st param: retry succeeds
            *([good_response] * 7),  # remaining 7 params succeed first try
        ]

        responses = device.get_full_state_pdus()

        assert len(responses) == 8
        assert all(response is good_response for response in responses)
        assert mock_recv.call_count == 9
        assert mock_send.call_count == 9


def test_device_get_full_state_pdus_retries_protocol_error(
    mock_socket: MagicMock,
) -> None:
    """A transient protocol error (e.g. stale handle mismatch) is also retried."""
    device = Device.from_address("192.168.1.100", 49494)
    good_response = MagicMock()
    with (
        patch.object(device, "send_pdus"),
        patch.object(device, "receive_matching_response") as mock_recv,
    ):
        mock_recv.side_effect = [
            AdamAudioProtocolError("No response for command handle 1"),
            good_response,
            *([good_response] * 7),
        ]

        responses = device.get_full_state_pdus()

        assert len(responses) == 8
        assert mock_recv.call_count == 9


def test_device_get_full_state_pdus_gives_up_after_retry_exhausted(
    mock_socket: MagicMock,
) -> None:
    """Once retries for a single parameter are exhausted, the error propagates."""
    device = Device.from_address("192.168.1.100", 49494)
    with (
        patch.object(device, "send_pdus"),
        patch.object(device, "receive_matching_response") as mock_recv,
    ):
        mock_recv.side_effect = TimeoutError("no response")

        with pytest.raises(TimeoutError):
            device.get_full_state_pdus()

        # 1 initial attempt + POLL_RETRY_ATTEMPTS retries for the first
        # parameter, then it gives up without trying the remaining 7.
        assert mock_recv.call_count == Device.POLL_RETRY_ATTEMPTS + 1


@patch("pyadamaudiocontroller.device.Message.decode")
def test_device_receive_response_errors(
    mock_msg_decode, mock_socket: MagicMock
) -> None:
    device = Device.from_address("192.168.1.100", 49494)
    mock_socket.recv.return_value = b"junk"

    msg = MagicMock()
    msg.pdu_type = 2  # Not Response PDU TYPE
    mock_msg_decode.return_value = msg

    with pytest.raises(ValueError, match="Expected response PDU type"):
        device.receive_response()

    with pytest.raises(ValueError, match="Expected response PDU type"):
        device.receive_responses([[int]])

    msg.pdu_type = 3  # Response PDU TYPE
    msg.pdu_count = 0
    with pytest.raises(ValueError, match="Expected at least 1 PDU"):
        device.receive_response()


def test_device_close_oserror(mock_socket: MagicMock) -> None:
    """Test close() silently handles OSError."""
    mock_socket.close.side_effect = OSError("already closed")
    device = Device.from_address("192.168.1.100", 49494)
    device.close()  # Should not raise


def test_device_drain_finally_oserror(mock_socket: MagicMock) -> None:
    """Test drain() handles OSError in finally block when restoring timeout."""
    mock_socket.gettimeout.return_value = 10.0
    mock_socket.recv.side_effect = BlockingIOError()
    mock_socket.settimeout.side_effect = [None, OSError("bad fd")]
    device = Device.from_address("192.168.1.100", 49494)
    device.drain()  # Should not raise


def test_device_send_pdus_empty(mock_socket: MagicMock) -> None:
    """Test send_pdus raises ValueError for empty list."""
    device = Device.from_address("192.168.1.100", 49494)
    with pytest.raises(ValueError, match="must not be empty"):
        device.send_pdus([])


def test_device_send_pdus_mixed_types(mock_socket: MagicMock) -> None:
    """Test send_pdus raises ValueError for mixed PDU types."""
    device = Device.from_address("192.168.1.100", 49494)
    cmd = Command(handle=1, target=1, method_level=1, method_index=1)
    ka = Keepalive(timeout=30)
    with pytest.raises(ValueError, match="same type"):
        device.send_pdus([cmd, ka])


def test_device_set_timeout(mock_socket: MagicMock) -> None:
    """Test set_timeout sets socket receive timeout."""
    device = Device.from_address("192.168.1.100", 49494)
    device.set_timeout(5.0)
    mock_socket.settimeout.assert_called_with(5.0)
