"""Tests for ADAM Audio OCA device protocol."""

from unittest.mock import MagicMock, patch

import pytest
from pyadamaudiocontroller.command import Command
from pyadamaudiocontroller.device import Device
from pyadamaudiocontroller.keepalive import Keepalive


@pytest.fixture
def mock_socket() -> MagicMock:
    """Fixture for a mock socket."""
    with patch("pyadamaudiocontroller.device.socket.socket") as mock:
        sock = mock.return_value
        yield sock


def test_device_connect_disconnect(mock_socket: MagicMock) -> None:
    """Test device connection."""
    device = Device.from_address("192.168.1.100", 49494)

    device.send_keepalive()
    assert mock_socket.sendto.call_count == 1

    device.close()
    mock_socket.close.assert_called_once()


def test_device_getters(mock_socket: MagicMock) -> None:
    """Test device property getters."""
    device = Device.from_address("192.168.1.100", 49494)

    # Mocking response for a GET command
    with (
        patch.object(device, "send_pdus") as mock_send,
        patch.object(device, "receive_response") as mock_fetch,
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
    mock_socket.recvfrom.side_effect = [b"data1", b"data2", BlockingIOError()]
    device = Device.from_address("192.168.1.100", 49494)
    device.drain()
    assert mock_socket.recvfrom.call_count == 3


@patch("pyadamaudiocontroller.device.Message.decode")
@patch("pyadamaudiocontroller.device.Response.decode")
def test_device_receive_response(
    mock_resp_decode, mock_msg_decode, mock_socket: MagicMock
) -> None:
    device = Device.from_address("192.168.1.100", 49494)
    # mock raw socket
    mock_socket.recvfrom.return_value = (b"some bytes", None)

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
        patch.object(device, "receive_response") as mock_recv,
    ):
        mock_recv.return_value = MagicMock()

        responses = device.get_full_state_pdus()
        assert len(responses) == 8
        assert mock_send.call_count == 8


@patch("pyadamaudiocontroller.device.Message.decode")
def test_device_receive_response_errors(
    mock_msg_decode, mock_socket: MagicMock
) -> None:
    device = Device.from_address("192.168.1.100", 49494)
    mock_socket.recvfrom.return_value = (b"junk", None)

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
    mock_socket.recvfrom.side_effect = BlockingIOError()
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
