"""AES70/OCA response PDU.

Originally from the pacontrol library by dmach (https://github.com/dmach/pacontrol).
"""

import io
from typing import BinaryIO

from .types import PDU, OcaType
from .util import unpack_from_stream


class Response(PDU):
    PDU_TYPE = 3

    def __init__(
        self,
        handle: int,
        status_code: int,
        param_count: int,
        params: list[OcaType] | None = None,
        extra_hex: list[str] | None = None,
    ) -> None:
        self.handle = handle
        self.status_code = status_code
        self.param_count = param_count
        self.params = params or []
        self.extra_hex = extra_hex or []

    @classmethod
    def decode(
        cls, stream: BinaryIO, param_types: list[type] | None = None
    ) -> Response:
        param_types = param_types or []
        _length, handle, status_code, param_count = unpack_from_stream("!IIBB", stream)

        # PDU header is 10 bytes. The remaining bytes in this PDU are (_length - 10).
        pdu_data_size = _length - 10
        pdu_data = stream.read(pdu_data_size)
        pdu_stream = io.BytesIO(pdu_data)

        if param_count < len(param_types):
            raise ValueError(
                f"ADAM_AUDIO_PROTOCOL_ERROR: Speaker returned {param_count} params, "
                f"but we expected at least {len(param_types)}."
            )

        # Decode the requested parameters from this PDU's stream
        params = [ptype.decode(pdu_stream) for ptype in param_types]

        # Capture any remaining data in this PDU's stream as hex strings (e.g. min/max ranges)
        extra_hex = []
        remaining = pdu_stream.read()
        if remaining:
            extra_hex.append(remaining.hex())

        return cls(handle, status_code, param_count, params, extra_hex)
