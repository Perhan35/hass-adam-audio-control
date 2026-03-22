# Contributing to ADAM Audio Control

This project uses `pytest` for unit testing and `pre-commit` hooks for code formatting and linting (`ruff`).

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

```bash
pytest tests/ -v --cov=custom_components.adam_audio
```

Coverage must stay at **95%** or above — CI will fail otherwise.
