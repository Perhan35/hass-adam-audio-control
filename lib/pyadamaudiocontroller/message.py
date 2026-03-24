"""AES70/OCA message envelope.

Originally from the pacontrol library by dmach (https://github.com/dmach/pacontrol).
"""

import struct
from typing import BinaryIO

from .util import unpack_from_stream


class Message:
    SYNC = 0x3B
    FORMAT = "!BHIBH"

    def __init__(
        self,
        protocol_version: int,
        message_size: int,
        pdu_type: int,
        pdu_count: int,
    ) -> None:
        self.protocol_version = protocol_version
        self.message_size = message_size
        self.pdu_type = pdu_type
        self.pdu_count = pdu_count

    @classmethod
    def decode(cls, stream: BinaryIO) -> Message:
        (
            sync,
            protocol_version,
            message_size,
            pdu_type,
            pdu_count,
        ) = unpack_from_stream(cls.FORMAT, stream)
        if sync != cls.SYNC:
            raise RuntimeError(
                f"Bad sync byte: expected 0x{cls.SYNC:02X}, got 0x{sync:02X}"
            )
        return cls(protocol_version, message_size, pdu_type, pdu_count)

    def encode(self) -> bytes:
        return struct.pack(
            self.FORMAT,
            self.SYNC,
            self.protocol_version,
            self.message_size,
            self.pdu_type,
            self.pdu_count,
        )
