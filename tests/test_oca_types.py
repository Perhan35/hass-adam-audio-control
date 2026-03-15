import io

from custom_components.adam_audio.oca_command import Command
from custom_components.adam_audio.oca_keepalive import Keepalive
from custom_components.adam_audio.oca_message import Message
from custom_components.adam_audio.oca_response import Response
from custom_components.adam_audio.oca_types import OcaInt8, OcaString, OcaUint16


def test_oca_types():
    assert OcaInt8(5).encode() == b"\x05"
    assert OcaInt8(-2).encode() == b"\xfe"

    assert OcaUint16(256).encode() == b"\x01\x00"

    assert OcaString("test").encode() == b"\x00\x04test"


def test_message_decode_encode():
    msg = Message(protocol_version=1, message_size=16, pdu_type=1, pdu_count=1)
    encoded = msg.encode()
    decoded = Message.decode(io.BytesIO(encoded))
    assert decoded.protocol_version == 1
    assert decoded.message_size == 16
    assert decoded.pdu_type == 1
    assert decoded.pdu_count == 1


def test_command_encode():
    cmd = Command(
        handle=1, target=123, method_level=4, method_index=1, method_params=[OcaInt8(5)]
    )
    encoded = cmd.encode()
    assert encoded is not None


def test_keepalive_encode():
    ka = Keepalive(timeout=30)
    encoded = ka.encode()
    assert encoded is not None


def test_response_decode():
    # Construct a valid response PDU binary
    binary = b"\x00\x00\x00\x10" + b"\x00\x00\x00\x01" + b"\x00" + b"\x01" + b"\x05"
    stream = io.BytesIO(binary)
    resp = Response.decode(stream, param_types=[OcaInt8])
    assert resp.handle == 1
    assert resp.status_code == 0
    assert resp.params[0].value == 5


def test_command_encode_decode():
    cmd = Command(
        handle=1, target=123, method_level=4, method_index=1, method_params=[OcaInt8(5)]
    )
    encoded = cmd.encode()
    assert encoded is not None
    decoded = Command.decode(io.BytesIO(encoded), method_params_types=[OcaInt8])
    assert decoded.handle == 1
    assert decoded.target == 123
    assert decoded.method_params[0].value == 5


def test_keepalive_encode_decode():
    ka = Keepalive(timeout=30)
    encoded = ka.encode()
    assert encoded is not None
    # Wait, encode packs "!H" (2 bytes). decode defaults to 4.
    # Actually, decode length is variable. If we pass 2 it decodes H.
    decoded = Keepalive.decode(io.BytesIO(encoded), size=2)
    assert decoded.timeout == 30000  # Wait, size=2 multiplies by 1000

    # Let's just test size 4 decode
    ka4 = Keepalive.decode(io.BytesIO(b"\x00\x00\x00\x1e"))
    assert ka4.timeout == 30
