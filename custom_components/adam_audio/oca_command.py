"""AES70/OCA command PDU.

Originally from the pacontrol library by dmach (https://github.com/dmach/pacontrol).
"""

import io
import struct
from typing import BinaryIO

from .oca_types import PDU, OcaType
from .oca_util import unpack_from_stream


class Command(PDU):
    PDU_TYPE = 1
    FORMAT = "!IIIHHB"

    def __init__(
        self,
        handle: int,
        target: int,
        method_level: int,
        method_index: int,
        method_params: list[OcaType] | None = None,
    ) -> None:
        self.handle = handle
        self.target = target
        self.method_level = method_level
        self.method_index = method_index
        self.method_params = method_params or []

    @classmethod
    def decode(
        cls, stream: BinaryIO, method_params_types: list[type] | None = None
    ) -> Command:
        method_params_types = method_params_types or []
        (
            _encoded_length,
            handle,
            target,
            method_level,
            method_index,
            param_count,
        ) = unpack_from_stream(cls.FORMAT, stream)
        assert param_count == len(method_params_types), (
            f"Expected {param_count} parameters, have {len(method_params_types)}"
        )
        params_stream = io.BytesIO(stream.read())
        method_params = [ptype.decode(params_stream) for ptype in method_params_types]
        return cls(handle, target, method_level, method_index, method_params)

    def encode(self) -> bytes:
        encoded_params = b"".join(p.encode() for p in self.method_params)
        size = struct.calcsize(self.FORMAT) + len(encoded_params)
        header = struct.pack(
            self.FORMAT,
            size,
            self.handle,
            self.target,
            self.method_level,
            self.method_index,
            len(self.method_params),
        )
        return header + encoded_params
