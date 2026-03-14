# Contributing to ADAM Audio Control

Everyone is invited to contribute to this project. Here are some tips to get you started.

## Development Environment

1. Clone the repository.
2. Open in VS Code with the Dev Container (Preferably with "Dev Containers: Clone Repository in Named Container Volume...").
3. Run `scripts/develop` to start Home Assistant with the integration loaded.

## Development Workflow

1. Create a feature branch from `main`.
2. Make your changes.
3. Run `scripts/lint` to format and lint your code.
4. Test your changes by running `scripts/develop`.
5. Create a Pull Request.

## Code Quality

This project uses [ruff](https://github.com/astral-sh/ruff) for linting and formatting. Run the linter before submitting:

```bash
scripts/lint
```
