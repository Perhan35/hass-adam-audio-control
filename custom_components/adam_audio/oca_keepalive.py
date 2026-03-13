"""AES70/OCA keepalive PDU.

Originally from the pacontrol library by dmach (https://github.com/dmach/pacontrol).
"""
import struct
from typing import BinaryIO

from .oca_types import PDU
from .oca_util import unpack_from_stream


class Keepalive(PDU):
    PDU_TYPE = 4

    def __init__(self, timeout: int = 30) -> None:
        super().__init__()
        self.timeout = timeout

    @classmethod
    def decode(cls, stream: BinaryIO, size: int = 4) -> "Keepalive":
        if size == 4:
            (value,) = unpack_from_stream("!I", stream)
        elif size == 2:
            (value,) = unpack_from_stream("!H", stream)
            value *= 1000
        else:
            raise ValueError(f"Invalid keepalive timeout length: {size}")
        return cls(value)

    def encode(self) -> bytes:
        return struct.pack("!H", self.timeout)
