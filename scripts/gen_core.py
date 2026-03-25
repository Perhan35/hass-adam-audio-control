#!/usr/bin/env python3
"""Generate HA Core-ready integration files from this monorepo.

Usage:
    python scripts/gen_core.py --lib-version 1.0.0
    python scripts/gen_core.py --lib-version 1.0.0 --output /path/to/output

Output structure:
    build/core/
    ├── homeassistant/components/adam_audio/   (integration files or symlink)
    └── tests/components/adam_audio/           (test files or symlink)

If the output directories are not yet symlinked into a local ha-core checkout,
the script will ask interactively whether to create the symlinks.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent.parent
INTEGRATION_SRC = ROOT / "custom_components" / "adam_audio"
TESTS_SRC = ROOT / "tests"

# Files to copy as-is to the Core integration directory
INTEGRATION_FILES = [
    "client.py",
    "coordinator.py",
    "config_flow.py",
    "entity.py",
    "const.py",
    "data.py",
    "switch.py",
    "select.py",
    "number.py",
    "strings.json",
]

# Directories to copy
INTEGRATION_DIRS = [
    "translations",
]

# Test files to copy
TEST_FILES = [
    "conftest.py",
    "test_init.py",
    "test_client.py",
    "test_config_flow.py",
    "test_components.py",
]


def generate_core_manifest(lib_version: str) -> dict:
    """Generate the HA Core variant of manifest.json."""
    with (INTEGRATION_SRC / "manifest.json").open() as f:
        manifest = json.load(f)

    # Remove HACS-only fields
    manifest.pop("version", None)
    manifest.pop("issue_tracker", None)
    manifest.pop("dependencies", None)

    # Update fields for Core
    manifest["documentation"] = "https://www.home-assistant.io/integrations/adam_audio"
    manifest["requirements"] = [f"pyadamaudiocontroller=={lib_version}"]
    manifest["loggers"] = ["pyadamaudiocontroller"]
    manifest["quality_scale"] = "bronze"

    # HA Core requires: domain first, name second, then alphabetical order
    rest = {k: v for k, v in sorted(manifest.items()) if k not in ("domain", "name")}
    return {"domain": manifest["domain"], "name": manifest["name"], **rest}


def generate_core_init() -> str:
    """Generate __init__.py with card registration stripped."""
    result = (INTEGRATION_SRC / "__init__.py").read_text()

    # Remove _WWW_DIR line and its unused pathlib import
    result = re.sub(r"^_WWW_DIR = .*\n", "", result, flags=re.MULTILINE)
    result = re.sub(r"^from pathlib import Path\n", "", result, flags=re.MULTILINE)

    # Replace async_setup with a Core-compatible version that still initializes hass.data
    return re.sub(
        r"async def async_setup\(hass: HomeAssistant, _config: ConfigType\) -> bool:"
        r"(?:\n(?:    .*\n|\n)*)",
        "async def async_setup(hass: HomeAssistant, _config: ConfigType) -> bool:\n"
        '    """Set up the ADAM Audio integration."""\n'
        "    if DOMAIN not in hass.data:\n"
        "        hass.data[DOMAIN] = AdamAudioIntegrationData(coordinators={})\n"
        "    return True\n\n\n",
        result,
    )


def _transform_test_content(filename: str, content: str) -> str:
    """Apply ha-core transformations to a test file's content."""
    # 1. Replace custom_components module references with homeassistant.components
    content = re.sub(
        r"\bcustom_components\.adam_audio\b",
        "homeassistant.components.adam_audio",
        content,
    )


    # 3. Replace pytest_homeassistant_custom_component MockConfigEntry with tests.common
    content = content.replace(
        "from pytest_homeassistant_custom_component.common import MockConfigEntry",
        "from tests.common import MockConfigEntry",
    )

    # 3. Fix the conftest import path used in test_config_flow.py
    content = content.replace(
        "from tests.conftest import",
        "from tests.components.adam_audio.conftest import",
    )

    # 4. Remove the auto_enable_custom_integrations fixture from conftest.py
    #    (not needed / not available in ha-core)
    if filename == "conftest.py":
        content = re.sub(
            r"\n\n@pytest\.fixture\(autouse=True\)\ndef auto_enable_custom_integrations\([^)]*\) -> None:\n"
            r'    """Enable custom integrations for all tests\."""\n',
            "\n\n",
            content,
        )

    # 5. Remove the card-registration test from test_init.py (not applicable in core)
    if filename == "test_init.py":
        content = re.sub(
            r"\n\nasync def test_async_setup_registers_cards\(.*?\n(?=\n\nasync def |\Z)",
            "\n\n",
            content,
            flags=re.DOTALL,
        )
        # Remove async_setup from the import (now unused after test removal)
        content = re.sub(
            r",\s*async_setup\b",
            "",
            content,
        )
        content = re.sub(
            r"\basync_setup,\s*",
            "",
            content,
        )

    return content


def generate_core_tests(output_dir: Path) -> None:
    """Copy and adapt test files for Core's test structure."""
    written: list[Path] = []
    for filename in TEST_FILES:
        src = TESTS_SRC / filename
        if not src.exists():
            print(f"  Warning: {src} not found, skipping")
            continue

        content = src.read_text()
        content = _transform_test_content(filename, content)
        dest = output_dir / filename
        dest.write_text(content)
        written.append(dest)
        print(f"  Copied+transformed: tests/components/adam_audio/{filename}")

    # Create __init__.py
    init = output_dir / "__init__.py"
    init.write_text('"""Tests for the ADAM Audio integration."""\n')

    # Fix import ordering in every generated test file using ruff (I001).
    # Prefer running from the ha-core root (detected via symlink) so ruff picks up
    # the correct pyproject.toml with isort.known_first_party = ["homeassistant", "tests"].
    all_files = [*written, init]

    # Determine the working directory: if the output_dir is a symlink, resolve
    # to find the ha-core root (two levels up from tests/components/adam_audio).
    cwd: Path | None = None
    if output_dir.is_symlink():
        resolved = output_dir.resolve()
        # resolved = <ha-core>/tests/components/adam_audio → go up 3 levels
        cwd = resolved.parent.parent.parent
    elif (output_dir.parent.parent.parent / "pyproject.toml").exists():
        cwd = output_dir.parent.parent.parent

    ruff_cmd_base = [
        "python",
        "-m",
        "ruff",
    ]

    try:
        # 1. Check and fix imports (isort)
        # Use paths relative to ha-core root so ruff applies isort settings correctly
        rel_files = []
        for p in all_files:
            resolved = p.resolve()
            if cwd and resolved.is_relative_to(cwd):
                rel_files.append(str(resolved.relative_to(cwd)))
            else:
                rel_files.append(str(p))

        subprocess.run(  # noqa: S603
            [*ruff_cmd_base, "check", "--select", "I001", "--fix", "--quiet", *rel_files],
            cwd=cwd,
            check=False,
            capture_output=True,
        )
        # 2. Format code
        subprocess.run(  # noqa: S603
            [*ruff_cmd_base, "format", "--quiet", *rel_files],
            cwd=cwd,
            check=False,
            capture_output=True,
        )
        print("  Sorted imports and formatted code (ruff)")
    except subprocess.CalledProcessError:
        print("  Warning: ruff execution failed.")
    except FileNotFoundError:
        print(
            "  Warning: ruff not found — formatting may need manual fixing.\n"
            f"  Run: python -m ruff check --select I001 --fix {output_dir}\n"
            f"  Run: python -m ruff format {output_dir}"
        )


def create_symlinks(output: Path, ha_core: Path) -> None:
    """Create symlinks in the output dir pointing into a local ha-core checkout."""
    integration_out = output / "homeassistant" / "components" / "adam_audio"
    tests_out = output / "tests" / "components" / "adam_audio"

    integration_target = ha_core / "homeassistant" / "components" / "adam_audio"
    tests_target = ha_core / "tests" / "components" / "adam_audio"

    for src_path, target in [
        (integration_out, integration_target),
        (tests_out, tests_target),
    ]:
        # Already a symlink → leave it alone
        if src_path.is_symlink():
            print(f"  Already symlinked, skipping: {src_path}")
            continue

        if not target.exists():
            print(
                f"  Warning: target directory does not exist: {target}\n"
                "  Make sure the ha-core path is correct and the integration"
                " folder already exists there."
            )

        # Remove existing plain directory
        if src_path.exists():
            shutil.rmtree(src_path)
            print(f"  Removed existing directory: {src_path}")

        # Ensure parent directory exists
        src_path.parent.mkdir(parents=True, exist_ok=True)

        src_path.symlink_to(target)
        print(f"  Symlinked: {src_path}")
        print(f"          -> {target}")

    print(f"""
{"=" * 60}
Symlinks are in place!

  {integration_out}
    -> {integration_target}

  {tests_out}
    -> {tests_target}

You can now edit files directly in this repo and changes will be
reflected immediately in your ha-core checkout.
{"=" * 60}
""")


def main() -> None:
    """Generate Core-ready integration files."""
    parser = argparse.ArgumentParser(
        description="Generate HA Core-ready integration files"
    )
    parser.add_argument(
        "--lib-version",
        required=True,
        help="Version of pyadamaudiocontroller to pin in manifest",
    )
    parser.add_argument(
        "--output",
        default=str(ROOT / "build" / "core"),
        help="Output directory (default: build/core/)",
    )
    args = parser.parse_args()

    output = Path(args.output)

    # --- Symlink auto-detection ---
    integration_out = output / "homeassistant" / "components" / "adam_audio"
    tests_out = output / "tests" / "components" / "adam_audio"

    both_symlinked = integration_out.is_symlink() and tests_out.is_symlink()

    if not both_symlinked:
        default_ha_core = ROOT.parent / "ha-core"
        print(
            "\nNo symlinks detected for the output directories.\n"
            "You can link them directly into a local ha-core checkout so that\n"
            "edits in this repo are reflected there immediately.\n"
        )
        answer = input(
            f"Create symlinks into ha-core? [y/N] (ha-core path, default: {default_ha_core}): "
        ).strip()

        if answer.lower().startswith("y"):
            # Allow user to provide a custom path after 'y <path>'
            parts = answer.split(None, 1)
            ha_core_path = (
                Path(parts[1]).resolve()
                if len(parts) > 1
                else default_ha_core.resolve()
            )
            create_symlinks(output, ha_core_path)
            return
        print("  Skipping symlink setup.\n")

    integration_out = output / "homeassistant" / "components" / "adam_audio"
    tests_out = output / "tests" / "components" / "adam_audio"

    # Clean and create output dirs
    for path in [integration_out, tests_out]:
        if path.is_symlink():
            print(f"  Emptying symlinked directory: {path.name}")
            # Empty the contents of the target directory through the symlink
            for item in path.iterdir():
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()
        elif path.exists():
            shutil.rmtree(path)

        path.mkdir(parents=True, exist_ok=True)

    print(f"Generating Core files in: {output}\n")

    # 1. Generate manifest.json
    manifest = generate_core_manifest(args.lib_version)
    (integration_out / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n"
    )
    print("  Generated: manifest.json")

    # 2. Generate __init__.py (stripped of card logic)
    init_content = generate_core_init()
    (integration_out / "__init__.py").write_text(init_content)
    print("  Generated: __init__.py (card registration removed)")

    # 3. Copy integration files
    for filename in INTEGRATION_FILES:
        src = INTEGRATION_SRC / filename
        if src.exists():
            shutil.copy2(src, integration_out / filename)
            print(f"  Copied: {filename}")

    # 4. Copy directories
    for dirname in INTEGRATION_DIRS:
        src = INTEGRATION_SRC / dirname
        if src.exists():
            shutil.copytree(src, integration_out / dirname, dirs_exist_ok=True)
            print(f"  Copied: {dirname}/")

    # 5. Copy quality_scale.yaml if it exists
    quality_scale = ROOT / "quality_scale.yaml"
    if quality_scale.exists():
        shutil.copy2(quality_scale, integration_out / "quality_scale.yaml")
        print("  Copied: quality_scale.yaml")

    # 6. Generate tests
    print("\nGenerating tests:")
    generate_core_tests(tests_out)

    # Summary
    summary = f"""
{"=" * 60}
Core files generated successfully!

Integration: {integration_out}
Tests:       {tests_out}
"""
    if not both_symlinked:
        summary += f"""
Next steps:
  1. Copy into your home-assistant/core fork:
     cp -r {integration_out} <core>/homeassistant/components/
     cp -r {tests_out} <core>/tests/components/

  2. Run hassfest to register the integration:
     cd <core> && python -m script.hassfest

  3. Run tests:
     cd <core> && pytest tests/components/adam_audio/ -v

  4. Commit and submit PR
"""
    summary += "=" * 60
    print(summary)


if __name__ == "__main__":
    main()
