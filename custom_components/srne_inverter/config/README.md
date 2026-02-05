# Dynamic Config Flow System

This directory contains the YAML-driven dynamic config flow system for the SRNE Inverter integration.

## Overview

The dynamic config flow system replaces hardcoded Home Assistant config flow schemas with YAML-driven generation. This enables:

- **Single source of truth**: Register definitions in `entities_pilot.yaml` drive both entity creation and config UI
- **Automatic UI generation**: Selectors (Number, Select, Boolean) created from register metadata
- **Cross-field validation**: Validation rules defined in YAML enforce relationships between settings
- **Scaling/unscaling**: Values automatically scaled for display and unscaled for writing to registers
- **Danger level classification**: Settings marked as safe/warning/dangerous/critical with appropriate warnings

## Architecture

```
config/
├── entities_pilot.yaml      # Main configuration file (registers + config_flow metadata)
├── schema_builder.py         # Main orchestrator (ConfigFlowSchemaBuilder)
├── page_manager.py           # Page organization and visibility (ConfigPageManager)
├── selector_factory.py       # UI selector creation (SelectorFactory)
├── validation_engine.py      # Cross-field validation (ValidationEngine)
└── __init__.py               # Package exports
```

## Key Classes

### ConfigFlowSchemaBuilder
Main orchestrator that coordinates all components:
- `load_config()`: Loads YAML configuration
- `build_schema(page_id)`: Builds voluptuous schema for a page
- `validate_user_input()`: Validates form submissions
- `parse_user_input()`: Parses scaled values to raw register values

### SelectorFactory
Creates Home Assistant selectors from register metadata:
- `create_selector(register)`: Returns appropriate selector (Number/Select/Boolean)
- `get_default_value(register)`: Gets default value with proper scaling
- `parse_user_input(register, value)`: Removes scaling for register write

### ConfigPageManager
Manages pages and register organization:
- `get_page_order()`: Returns ordered list of pages
- `get_page_registers(page_id)`: Returns registers for a page
- `requires_warning(page_id)`: Checks if page needs danger warning

### ValidationEngine
Handles validation logic:
- `validate_field()`: Validates single field with cross-field constraints
- `validate_all_fields()`: Validates all fields including global rules
- `get_typical_range()`: Returns recommended value ranges

## Usage in config_flow.py

### 1. Enable Dynamic Schemas

Set the feature flag in `config_flow.py`:

```python
USE_DYNAMIC_SCHEMAS = True  # Enable YAML-driven schemas
```

### 2. Initialization

The schema builder is automatically initialized in `SRNEOptionsFlowHandler.__init__()`:

```python
self._schema_builder = ConfigFlowSchemaBuilder()
if not self._schema_builder.load_config():
    _LOGGER.error("Failed to load dynamic schema configuration")
```

### 3. Build Schema

Use helper method to build schema with automatic fallback:

```python
dynamic_schema = self._build_dynamic_schema("battery_config")
if dynamic_schema is not None:
    # Use dynamic schema
    return self.async_show_form(
        step_id="battery_config",
        data_schema=dynamic_schema,
        errors=errors,
    )
# Fall back to legacy hardcoded schema
```

### 4. Handle Form Submission

Use helper method for validation and saving:

```python
if USE_DYNAMIC_SCHEMAS and self._schema_builder:
    success, error_dict = await self._handle_form_submission_dynamic(
        "battery_config", user_input
    )
    if success:
        return await self.async_step_init()
    errors.update(error_dict)
```

## YAML Configuration Structure

### config_pages Section

Defines config flow pages:

```yaml
config_pages:
  battery_config:
    order: 1
    icon: "mdi:battery-settings"
    danger_level: "critical"  # safe, warning, dangerous, critical
    translations:
      en:
        title: "Battery Configuration"
        description: "Basic battery system voltage and type settings"
        warning: "CRITICAL: Settings must match your battery system"
```

### registers Section with config_flow

Each register includes config_flow metadata:

```yaml
battery_voltage:
  address: 0xE003
  type: read_write
  data_type: uint16
  unit: "V"
  min: 12
  max: 48
  default: 48
  config_flow:
    page: "battery_config"           # Which page to display on
    display_order: 5                 # Order on page
    danger_level: "critical"         # Danger classification
    translations:
      en:
        title: "Battery System Voltage"
        description: "Nominal voltage of your battery system"
        hint: "CRITICAL: Must exactly match your battery configuration"
    options:                          # For select fields
      12: {label: "12V", description: "12V battery system"}
      24: {label: "24V", description: "24V battery system"}
      48: {label: "48V", description: "48V battery system"}
    validation:                       # Cross-field validation
      must_be_less_than: "other_field"
      warning_if_above: 55.0
```

### config_validation Section

Defines cross-field validation rules:

```yaml
config_validation:
  rules:
    - name: "bulk_float_voltage_relationship"
      fields: ["bulk_charge_voltage", "float_charge_voltage"]
      condition: "bulk_charge_voltage > float_charge_voltage"
      translations:
        en:
          error: "Bulk charge voltage must be greater than float charge voltage"
```

## Migration Strategy

### Phase 1: Parallel Operation (Current)
- Feature flag OFF by default
- Both dynamic and legacy code paths exist
- Test dynamic schemas on development/staging

### Phase 2: Gradual Rollout
- Enable feature flag for specific pages
- Monitor for issues
- Collect user feedback

### Phase 3: Full Migration
- Enable feature flag globally
- Remove legacy schema code
- Add new pages purely through YAML

## Adding New Config Pages

With dynamic schemas enabled, adding a new page only requires YAML:

1. Add page definition to `config_pages` section
2. Set `config_flow.page` on relevant registers
3. Add translations
4. Optional: Add validation rules

No Python code changes needed!

## Benefits

### Before (Hardcoded)
- 300+ lines of schema code per page
- Duplicate definitions (entities + config flow)
- Hard to maintain consistency
- Adding registers requires Python changes

### After (YAML-Driven)
- Single register definition
- Automatic UI generation
- Consistent scaling/validation
- Adding registers only requires YAML

## Testing

Test each page by:

1. Set `USE_DYNAMIC_SCHEMAS = True`
2. Go to integration configuration
3. Navigate to each page
4. Verify fields display correctly
5. Test validation rules
6. Test value scaling
7. Verify writes to inverter

## Troubleshooting

### Schema not loading
- Check `entities_pilot.yaml` syntax
- Look for errors in Home Assistant logs
- Verify `config_flow` section exists

### Fields not showing
- Check `config_flow.page` matches page ID
- Verify register in coordinator data
- Check visibility conditions

### Validation not working
- Verify validation rules syntax
- Check field names match register keys
- Review validation engine logs

## Future Enhancements

- [ ] Conditional field visibility based on other field values
- [ ] Voltage-dependent validation (12V vs 48V systems)
- [ ] Dynamic typical ranges based on battery type
- [ ] Multi-language translation support
- [ ] Export/import preset configurations
- [ ] Backup/restore settings to file
