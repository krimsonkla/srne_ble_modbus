#!/usr/bin/env python3
"""Generate translations/en.json from entities_pilot.yaml config_flow metadata."""

import json
import yaml
from pathlib import Path
from collections import defaultdict

def load_yaml_config(yaml_path: Path) -> dict:
    """Load entities_pilot.yaml configuration."""
    with open(yaml_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def extract_translations(config: dict) -> dict:
    """Extract translations from YAML config_flow metadata.

    Returns dict structure:
    {
        "battery_config": {
            "data": {"battery_capacity": "Battery Capacity", ...},
            "data_description": {"battery_capacity": "Total capacity...", ...}
        },
        ...
    }
    """
    translations_by_page = defaultdict(lambda: {"data": {}, "data_description": {}})

    registers = config.get("registers", {})

    for reg_key, reg_def in registers.items():
        config_flow = reg_def.get("config_flow")
        if not config_flow:
            continue

        page = config_flow.get("page")
        if not page:
            continue

        translations = config_flow.get("translations", {}).get("en", {})
        title = translations.get("title")
        description = translations.get("description")

        if title:
            translations_by_page[page]["data"][reg_key] = title

        if description:
            translations_by_page[page]["data_description"][reg_key] = description

    return dict(translations_by_page)

def load_existing_translations(json_path: Path) -> dict:
    """Load existing translations/en.json."""
    if json_path.exists():
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"options": {"step": {}}}

def merge_translations(existing: dict, generated: dict) -> dict:
    """Merge generated translations with existing, preserving manual entries."""
    result = existing.copy()

    # Ensure structure exists
    if "options" not in result:
        result["options"] = {}
    if "step" not in result["options"]:
        result["options"]["step"] = {}

    step = result["options"]["step"]

    # Merge each page
    for page_name, page_translations in generated.items():
        if page_name not in step:
            step[page_name] = {}

        # Merge data (field titles)
        if "data" not in step[page_name]:
            step[page_name]["data"] = {}
        step[page_name]["data"].update(page_translations["data"])

        # Merge data_description (field descriptions)
        if "data_description" not in step[page_name]:
            step[page_name]["data_description"] = {}
        step[page_name]["data_description"].update(page_translations["data_description"])

    return result

def write_translations(json_path: Path, translations: dict):
    """Write translations to en.json with pretty formatting."""
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(translations, f, indent=2, ensure_ascii=False)
        f.write('\n')  # Add newline at end

def main():
    """Generate translations from YAML."""
    # Paths
    repo_root = Path(__file__).parent.parent
    yaml_path = repo_root / "custom_components" / "srne_inverter" / "config" / "entities_pilot.yaml"
    json_path = repo_root / "custom_components" / "srne_inverter" / "translations" / "en.json"

    print(f"Reading YAML from: {yaml_path}")
    config = load_yaml_config(yaml_path)

    print("Extracting translations from config_flow metadata...")
    generated = extract_translations(config)

    print(f"Found translations for {len(generated)} pages:")
    for page, trans in generated.items():
        print(f"  - {page}: {len(trans['data'])} fields")

    print(f"\nReading existing translations from: {json_path}")
    existing = load_existing_translations(json_path)

    print("Merging translations...")
    merged = merge_translations(existing, generated)

    print(f"Writing translations to: {json_path}")
    write_translations(json_path, merged)

    print("\n✅ Translation generation complete!")
    print(f"Generated translations for {sum(len(t['data']) for t in generated.values())} fields")

if __name__ == "__main__":
    main()
