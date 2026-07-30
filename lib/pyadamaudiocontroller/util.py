"""Utility helpers for the AES70/OCA protocol layer.

Originally from the pacontrol library by dmach (https://github.com/dmach/pacontrol).
"""

import struct
from typing import BinaryIO

from .exceptions import AdamAudioProtocolError


def unpack_from_stream(fmt: str, stream: BinaryIO):
    """Unpack data from a binary stream (usually io.BytesIO)."""
    size = struct.calcsize(fmt)
    data = stream.read(size)
    try:
        return struct.unpack(fmt, data)
    except struct.error as err:
        raise AdamAudioProtocolError(
            f"Truncated or malformed PDU data ({err})"
        ) from err
