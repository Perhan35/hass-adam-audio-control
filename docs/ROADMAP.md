# Roadmap

The integration is distributed through **HACS**, which is the current priority.

## Decisions to make

### License of the protocol library

The repository and the `pyadamaudiocontroller` package are published under **MIT**. The headers of
the library's files (`device.py`, `command.py`, `keepalive.py`, `message.py`, `response.py`,
`types.py` and `util.py`) say the code comes from [pacontrol](https://github.com/dmach/pacontrol) by
dmach, which is licensed **GPL-3.0**.

These two licenses don't normally combine without the author's agreement. To settle, ideally with
legal advice, before any new Core submission. The options are:

- ask dmach for permission or for a different license
- publish the library under GPL-3.0, after checking what that means for Core
- rewrite the affected code from the AES70 standard

## Home Assistant Core

[core#166511](https://github.com/home-assistant/core/pull/166511) and
[home-assistant.io#44305](https://github.com/home-assistant/home-assistant.io/pull/44305) were closed
on 2026-09-15. A new PR is welcome once the review's concerns are addressed, and should link to the
old one. The review asked for:

- a much smaller PR, limited to a single platform (e.g. `switch` or `select`)
- no noisy AI comments and methods
- no `hass.data` suppressed with pylint, which the 'All Speakers' group relies on
- no unique_id migrations, since a new Core integration has nothing to migrate

The group would therefore probably stay HACS-only at first. `scripts/gen_core.py` still generates the
full integration, so it would need to be cut down too.

## To check on real speakers

These could not be tested without hardware:

- the **Identify** button actually blinks the LED (`Device.blink` was never used until now)
- 5 seconds is enough for a speaker to answer, including when waking from sleep
  (`AdamAudioClient.SOCKET_TIMEOUT`, which was 10 seconds)

## Cards

- Keyboard and screen reader support: the three cards have none.
- Share the code the three cards duplicate (state helpers, service calls, card suggestions).
- A visual editor: the cards are configured in YAML.

## Gold

Diagnostics, the reconfigure flow and the serial mismatch repair issue are done. What remains:

### Exception translations (`exception-translations` rule)

The `HomeAssistantError` raises in [`client.py`](../custom_components/adam_audio/client.py) build
their messages with f-strings, so they are English-only. Convert them to
`translation_domain=DOMAIN, translation_key=...` with placeholders, and add an `exceptions` block to
[`strings.json`](../custom_components/adam_audio/strings.json), which has none today.

### Documentation (`docs-troubleshooting`, `docs-use-cases` rules)

Add a **Troubleshooting** section to the Core documentation page, and frame the introduction around
concrete use cases. These are the last two `docs-*` rules still open.

Once the above are done, bump `quality_scale` to `gold` in `scripts/gen_core.py` and
`quality_scale.yaml`.

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

`client.py` then drops every `async_add_executor_job` call along with the `_run_set` executor target.
The `asyncio.Lock` can stay to serialize commands against polls.

### Strict typing (`strict-typing` rule)

After releasing the library as 2.0.0 and bumping the manifest requirement, add
`homeassistant.components.adam_audio.*` to Core's `.strict-typing` and make strict mypy pass.

Then bump `quality_scale` to `platinum`.
