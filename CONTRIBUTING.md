# Contributing to ADAM Audio Control

This project uses `pytest` for unit testing and `pre-commit` hooks for code formatting and linting (`ruff`).

---

## Repository Structure

This is a monorepo with three concerns (HACS, HA Core, PyPI Library):

```
hass-adam-audio-control/
├── lib/                                  PyPI library
│   ├── pyadamaudiocontroller/
│   ├── tests/                            lib tests
│   └── pyproject.toml
│
├── custom_components/adam_audio/          HA integration
│   └── www/                               Lovelace cards — HACS only
│
├── tests/                                 HA integration tests
│
├── scripts/                               Build/automation and helper scripts
│
└── .github/workflows/                     CI/CD workflows
```

---

## Getting Started

To set up a local development environment:

1. Clone the repository
2. Create a virtual environment and install dependencies:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
   This installs the protocol library in editable mode (`-e lib/`) plus all dev tools.
3. Install pre-commit hooks:
   ```bash
   pre-commit install
   ```
4. Open in VS Code with the Dev Container, or run directly:
   ```bash
   scripts/develop
   ```

---

## Workflow

1. Create a feature branch from `main`
2. Make your changes
3. Lint, test, and verify:
   ```bash
   ./scripts/checks        # runs lint + tests + coverage in one go
   ```
4. Test the UI by running `scripts/develop`
5. Run pre-commit hooks:
   ```bash
   pre-commit run --all-files
   ```
6. Open a Pull Request

---

## Scripts

| Script | Description |
|---|---|
| `scripts/develop` | Start Home Assistant with the integration loaded |
| `scripts/lint` | Format and lint with [ruff](https://github.com/astral-sh/ruff) |
| `scripts/checks` | Run all checks (lint + tests + coverage) |
| `scripts/browse_mdns` | Debug mDNS / zeroconf discovery |

---

## Testing

### Library tests (protocol only, no HA dependency)

```bash
pytest lib/tests/ -v --cov=pyadamaudiocontroller
```

Library coverage target: **100%**.

### Integration tests (HA entities, config flow, coordinator)

```bash
pytest tests/ -v --cov=custom_components.adam_audio
```

Integration coverage target: **95%** or above — CI will fail otherwise.

### All tests

```bash
pytest tests/ lib/tests/ -v
```

---

## Generating HA Core PR Files

To produce a Core-ready integration for submitting to `home-assistant/core`:

```bash
python scripts/gen_core.py --lib-version 1.0.0
```

This creates `build/core/` with the integration files (no cards, no vendored protocol code, Core manifest). See the script output for next steps.

---

## Publishing the Library to PyPI

### Verify the library builds (recommended before publish)

```bash
pip install build
python -m build lib/
# Should produce lib/dist/pyadamaudiocontroller-x.x.x.tar.gz and .whl
```

### Publish a new library version

1. Bump `version` in [`lib/pyproject.toml`](lib/pyproject.toml) (PyPI rejects re-uploads of an existing version).
2. Tag and push:
   ```bash
   git tag lib-v1.0.0
   git push origin lib-v1.0.0
   ```
3. GitHub Actions (`publish-lib.yml`) builds and uploads automatically.
4. Verify at [pypi.org/project/pyadamaudiocontroller/](https://pypi.org/project/pyadamaudiocontroller/) (~1 min).

---

## Release Strategy

| Tag | What happens |
|-----|--------------|
| `v*` (e.g., `v0.3.0`) | HACS GitHub release + PyPI library publish |
| `lib-v*` (e.g., `lib-v1.0.0`) | PyPI library publish only |

Always publish the library before or alongside the integration release.
