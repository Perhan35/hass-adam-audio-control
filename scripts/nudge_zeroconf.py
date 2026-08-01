#!/usr/bin/env python3
"""Nudge ADAM Audio speakers into responding to mDNS discovery.

Home Assistant's zeroconf component browses for every service type any
integration can be discovered by in one go — well over a hundred types,
batched into a handful of compressed multicast packets. The ADAM Audio
speakers' embedded mDNS responder does not reliably answer that compound
query, but answers a clean, single-type query within about a second.

This script sends exactly that clean query, repeatedly, for a short window.
Home Assistant's own zeroconf listener is already passively receiving all
multicast traffic on the same socket, so it picks up the resulting response
immediately — it doesn't care who asked the question that triggered it.

Run this alongside `hass`, not instead of it.

Usage:
    python scripts/nudge_zeroconf.py [duration_seconds]
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
import time

from zeroconf import ServiceBrowser, Zeroconf

MANIFEST = (
    Path(__file__).resolve().parent.parent
    / "custom_components/adam_audio/manifest.json"
)


def zeroconf_types() -> list[str]:
    """Read the service types the integration is discovered by."""
    manifest = json.loads(MANIFEST.read_text())
    return sorted({entry["type"] for entry in manifest.get("zeroconf", [])})


def _ignore(
    zeroconf: Zeroconf, service_type: str, name: str, state_change: object
) -> None:
    """Discard the event — we only care about the query traffic this generates."""


def main() -> None:
    """Browse for each ADAM Audio service type on its own for a while."""
    duration = float(sys.argv[1]) if len(sys.argv) > 1 else 45.0
    types = zeroconf_types()
    if not types:
        return

    zc = Zeroconf()
    browsers = [
        ServiceBrowser(zc, service_type, handlers=[_ignore]) for service_type in types
    ]
    time.sleep(duration)
    for browser in browsers:
        browser.cancel()
    zc.close()


if __name__ == "__main__":
    main()
