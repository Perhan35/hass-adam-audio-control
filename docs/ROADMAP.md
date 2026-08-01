# Roadmap

Planned work after the integration lands in Home Assistant Core
([core#166511](https://github.com/home-assistant/core/pull/166511),
[home-assistant.io#44305](https://github.com/home-assistant/home-assistant.io/pull/44305)).

The integration ships at **bronze** on the
[Integration Quality Scale](https://developers.home-assistant.io/docs/core/integration-quality-scale/).
Silver is already fully met. The two sections below are what Gold and Platinum still require, as
tracked in [`quality_scale.yaml`](../quality_scale.yaml).

These are deliberately kept out of the initial Core submission: reviewers prefer a new integration
to land at bronze and iterate, and Platinum in particular changes the `pyadamaudiocontroller` public
API.

## Gold

### Diagnostics (`diagnostics` rule)

Add `diagnostics.py` with `async_get_config_entry_diagnostics`, returning the config entry data, the
`AdamAudioState` snapshot, `client.available`, the consecutive-failure counters and the poll
interval. Redact `CONF_HOST` and `CONF_SERIAL` with `async_redact_data`. Cover it with a syrupy
snapshot test.

### Reconfigure flow (`reconfiguration-flow` rule)

Add `async_step_reconfigure` to [`config_flow.py`](../custom_components/adam_audio/config_flow.py)
so a speaker's host and port can be corrected without deleting and re-adding the entry. Reuse the
existing `_async_try_connect` helper, then call
`self._abort_if_unique_id_mismatch(reason="wrong_device")` so pointing an entry at a *different*
speaker is rejected rather than silently swapping the entry's identity. Needs matching
`reconfigure` strings and tests.

### Repair issue for a serial mismatch (`repair-issues` rule)

`AdamAudioCoordinator.async_setup` raises `ConfigEntryNotReady` when the speaker answering at the
configured address reports a different serial than the entry expects — typically after DHCP hands
the old IP to another speaker. Today that retries forever with nothing shown to the user.

Raise a non-fixable repair issue (`ir.async_create_issue`, severity `ERROR`) explaining the mismatch
and pointing at the reconfigure flow above, and delete it once setup succeeds.

### Exception translations (`exception-translations` rule)

The `HomeAssistantError` raises in [`client.py`](../custom_components/adam_audio/client.py) build
their messages with f-strings, so they are English-only. Convert them to
`translation_domain=DOMAIN, translation_key=...` with placeholders, and add an `exceptions` block to
[`strings.json`](../custom_components/adam_audio/strings.json), which has none today.

### Documentation (`docs-troubleshooting`, `docs-use-cases` rules)

Add a **Troubleshooting** section to the documentation page, and frame the introduction around
concrete use cases. These are the last two `docs-*` rules still open.

Once the above are done, bump `quality_scale` to `gold` in the manifest and `quality_scale.yaml`.

## Platinum

Requires a `pyadamaudiocontroller` major release.

### Native async I/O (`async-dependency` rule)

`Device` in [`lib/pyadamaudiocontroller/device.py`](../lib/pyadamaudiocontroller/device.py) wraps a
blocking `socket.socket(AF_INET, SOCK_DGRAM)`. That is why every call in `client.py` goes through
`hass.async_add_executor_job` — the one blocker for this rule.

Add an `AsyncDevice` built on `loop.create_datagram_endpoint` with an `asyncio.DatagramProtocol`:

- The encode/decode layers (`message.py`, `response.py`, `command.py`, `types.py`) are already
  transport-agnostic and need no changes.
- `receive_matching_response` becomes a handle→`Future` map resolved in `datagram_received` and
  awaited under `asyncio.timeout`, replacing the blocking recv loop.
- `send_keepalive` becomes a `loop.call_later` task.
- Keep the synchronous `Device` for non-Home Assistant users.

`client.py` then drops every `async_add_executor_job` call along with the `_run_set` / `_run_get`
executor targets. The `asyncio.Lock` can stay to serialize commands against polls.

### Strict typing (`strict-typing` rule)

After releasing the library as 2.0.0 and bumping the manifest requirement, add
`homeassistant.components.adam_audio.*` to Core's `.strict-typing` and make strict mypy pass.

Then bump `quality_scale` to `platinum`.
