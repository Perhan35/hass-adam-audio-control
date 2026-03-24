#!/usr/bin/env python3
"""Generate HA Core-ready integration files from this monorepo.

Usage:
    python scripts/gen_core.py --lib-version 1.0.0
    python scripts/gen_core.py --lib-version 1.0.0 --output /path/to/output

Output structure:
    build/core/
    ├── homeassistant/components/adam_audio/   (integration files)
    └── tests/components/adam_audio/           (test files)
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path

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

    return manifest


def generate_core_init() -> str:
    """Generate __init__.py with card registration stripped."""
    result = (INTEGRATION_SRC / "__init__.py").read_text()

    # Remove _WWW_DIR line
    result = re.sub(r"^_WWW_DIR = .*\n\n?", "", result, flags=re.MULTILINE)

    # Replace the entire async_setup function (from signature to the next
    # top-level definition or end of indented block)
    return re.sub(
        r"async def async_setup\(hass: HomeAssistant, _config: ConfigType\) -> bool:"
        r"\n(?:    .*\n|\n)*",
        "async def async_setup(hass: HomeAssistant, _config: ConfigType) -> bool:\n"
        '    """Set up the ADAM Audio integration."""\n'
        "    return True\n\n",
        result,
    )


def generate_core_tests(output_dir: Path) -> None:
    """Copy and adapt test files for Core's test structure."""
    for filename in TEST_FILES:
        src = TESTS_SRC / filename
        if not src.exists():
            print(f"  Warning: {src} not found, skipping")
            continue

        content = src.read_text()
        (output_dir / filename).write_text(content)
        print(f"  Copied: tests/components/adam_audio/{filename}")

    # Create __init__.py
    (output_dir / "__init__.py").write_text(
        '"""Tests for the ADAM Audio integration."""\n'
    )


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
    integration_out = output / "homeassistant" / "components" / "adam_audio"
    tests_out = output / "tests" / "components" / "adam_audio"

    # Clean and create output dirs
    if output.exists():
        shutil.rmtree(output)
    integration_out.mkdir(parents=True)
    tests_out.mkdir(parents=True)

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
            shutil.copytree(src, integration_out / dirname)
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
    print(f"""
{"=" * 60}
Core files generated successfully!

Integration: {integration_out}
Tests:       {tests_out}

Next steps:
  1. Copy into your home-assistant/core fork:
     cp -r {integration_out} <core>/homeassistant/components/adam_audio/
     cp -r {tests_out} <core>/tests/components/adam_audio/

  2. Run hassfest to register the integration:
     cd <core> && python -m script.hassfest

  3. Run tests:
     cd <core> && pytest tests/components/adam_audio/ -v

  4. Commit and submit PR
{"=" * 60}
""")


if __name__ == "__main__":
    main()
