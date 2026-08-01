#!/usr/bin/env python3
"""Pre-seed a Home Assistant config dir so it boots past onboarding.

Creates an owner account (username/password given on the command line) and
marks every onboarding step done, so a freshly created config dir lands on the
login screen instead of the setup wizard.

Structure mirrors homeassistant/scripts/auth.py — that is the supported way to
touch the auth store outside a running instance.

Usage:
    python scripts/seed_onboarding.py <config_dir> [username] [password]
"""

from __future__ import annotations

import asyncio
import sys
import warnings

from homeassistant import runner
from homeassistant.auth import auth_manager_from_config
from homeassistant.auth.const import GROUP_ID_ADMIN
from homeassistant.components import onboarding
from homeassistant.config_entries import ConfigEntries
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.storage import Store


async def seed(config_dir: str, username: str, password: str) -> None:
    """Create the owner account and mark onboarding complete."""
    hass = HomeAssistant(config_dir)
    hass.config_entries = ConfigEntries(hass, {})
    # The device registry migration waits for the config entries to load.
    await hass.config_entries.async_initialize()
    dr.async_setup(hass)
    await asyncio.gather(dr.async_load(hass), er.async_load(hass))

    hass.auth = await auth_manager_from_config(hass, [{"type": "homeassistant"}], [])
    provider = hass.auth.auth_providers[0]
    await provider.async_initialize()

    # Same sequence as UserOnboardingView.post, except we go through the auth
    # store directly: AuthManager.async_create_user has no is_owner parameter.
    # Passing credentials also links them, so no async_link_user call is needed.
    await provider.async_add_auth(username, password)
    credentials = await provider.async_get_or_create_credentials({"username": username})
    await hass.auth._store.async_create_user(  # noqa: SLF001
        username.capitalize(),
        is_owner=True,
        is_active=True,
        group_ids=[GROUP_ID_ADMIN],
        credentials=credentials,
    )

    # The auth store only schedules a delayed save, and the usual flush on
    # shutdown needs a running instance — write it out ourselves instead.
    auth_store = hass.auth._store  # noqa: SLF001
    await auth_store._store.async_save(auth_store._data_to_save())  # noqa: SLF001

    store: Store[onboarding.OnboardingStoreData] = Store(
        hass, onboarding.STORAGE_VERSION, onboarding.STORAGE_KEY, private=True
    )
    await store.async_save({"done": list(onboarding.STEPS)})

    await hass.async_stop()


def main() -> None:
    """Run the seeder."""
    if len(sys.argv) < 2:
        sys.exit("Usage: seed_onboarding.py <config_dir> [username] [password]")

    config_dir = sys.argv[1]
    username = sys.argv[2] if len(sys.argv) > 2 else "dev"
    password = sys.argv[3] if len(sys.argv) > 3 else "dev"

    with warnings.catch_warnings():
        # HA's own scripts still set the policy; the deprecation is not ours to fix.
        warnings.simplefilter("ignore", DeprecationWarning)
        asyncio.set_event_loop_policy(runner.HassEventLoopPolicy(False))  # type: ignore[deprecated]
    asyncio.run(seed(config_dir, username, password))


if __name__ == "__main__":
    main()
