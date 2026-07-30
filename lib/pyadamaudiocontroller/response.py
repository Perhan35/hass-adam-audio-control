"""AES70/OCA response PDU.

Originally from the pacontrol library by dmach (https://github.com/dmach/pacontrol).
"""

import io
from typing import BinaryIO

from .exceptions import AdamAudioProtocolError
from .types import PDU, OcaType
from .util import unpack_from_stream

# Size of the Response PDU header (length + handle + status + param count)
_HEADER_SIZE = 10


class Response(PDU):
    PDU_TYPE = 3
    STATUS_OK = 0

    def __init__(
        self,
        handle: int,
        status_code: int,
        param_count: int,
        params: list[OcaType] | None = None,
        extra_hex: list[str] | None = None,
        *,
        raw_params: bytes = b"",
    ) -> None:
        self.handle = handle
        self.status_code = status_code
        self.param_count = param_count
        self.params = params or []
        self.extra_hex = extra_hex or []
        self.raw_params = raw_params

    @classmethod
    def decode(
        cls, stream: BinaryIO, param_types: list[type] | None = None
    ) -> Response:
        """Decode a Response PDU header and capture its raw parameter bytes.

        If ``param_types`` is given, the parameters are parsed immediately;
        otherwise call :meth:`parse_params` once the expected types are known
        (e.g. after matching the response handle to a pending command).
        """
        _length, handle, status_code, param_count = unpack_from_stream("!IIBB", stream)
        if _length < _HEADER_SIZE:
            raise AdamAudioProtocolError(
                f"Response PDU length {_length} smaller than header size"
            )
        raw_params = stream.read(_length - _HEADER_SIZE)

        response = cls(handle, status_code, param_count, raw_params=raw_params)
        if param_types:
            response.parse_params(param_types)
        return response

    def parse_params(self, param_types: list[type]) -> None:
        """Parse the raw parameter bytes into typed values."""
        if self.param_count < len(param_types):
            raise AdamAudioProtocolError(
                f"Speaker returned {self.param_count} params, "
                f"but we expected at least {len(param_types)}."
            )

        pdu_stream = io.BytesIO(self.raw_params)
        self.params = [ptype.decode(pdu_stream) for ptype in param_types]

        # Capture any remaining data as hex strings (e.g. min/max ranges)
        remaining = pdu_stream.read()
        self.extra_hex = [remaining.hex()] if remaining else []
