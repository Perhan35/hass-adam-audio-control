"""Exceptions for the pyadamaudiocontroller library."""


class AdamAudioError(Exception):
    """Base exception for all pyadamaudiocontroller errors."""


class AdamAudioProtocolError(AdamAudioError, ValueError):
    """Malformed, unexpected, or error response from the device.

    Also subclasses ValueError so callers that catch ValueError from
    earlier library versions keep working.
    """
