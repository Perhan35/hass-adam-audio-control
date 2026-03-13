"""Utility helpers for the AES70/OCA protocol layer.

Originally from the pacontrol library by dmach (https://github.com/dmach/pacontrol).
"""
import struct
from typing import BinaryIO


def unpack_from_stream(fmt: str, stream: BinaryIO):
    """Unpack data from a binary stream (usually io.BytesIO)."""
    size = struct.calcsize(fmt)
    data = stream.read(size)
    return struct.unpack(fmt, data)
