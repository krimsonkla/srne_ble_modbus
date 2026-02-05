# SRNE Inverter Translations

This directory contains translation files for the SRNE Inverter Home Assistant integration.

## Available Translations

- **English (en.json)** - Complete ✓

## Translation Coverage

The integration provides translations for:

- **Config Flow**: Setup and configuration dialogs
- **32 Sensors**: Battery, power, energy, temperature, and diagnostic sensors
- **1 Switch**: AC power control
- **1 Select**: Energy priority configuration
- **1 Binary Sensor**: Fault detection
- **Services**: Integration service descriptions

## Contributing Translations

To add a new language translation:

1. Copy `en.json` to `{language_code}.json` (e.g., `de.json` for German, `fr.json` for French)
2. Translate all **values** (keep all **keys** in English)
3. Test your translation by loading it in Home Assistant
4. Submit a pull request to the repository

### Translation Guidelines

- Keep keys in English (e.g., `"battery_soc"`)
- Translate only the values (e.g., `"name": "Battery SOC"` → `"name": "Batterie-Ladezustand"`)
- Maintain the JSON structure exactly as in the English version
- Preserve special formatting like `{name}` placeholders in descriptions
- Use proper technical terms for your language
- Keep translations concise and clear

### Example Translation

```json
{
  "entity": {
    "sensor": {
      "battery_soc": {
        "name": "Batterie-Ladezustand"
      },
      "pv_power": {
        "name": "PV-Leistung"
      }
    }
  }
}
```

## Translation File Structure

```
custom_components/srne_inverter/
├── strings.json          # Base translation template
└── translations/
    ├── README.md         # This file
    ├── en.json          # English (default)
    ├── de.json          # German (example)
    └── fr.json          # French (example)
```

## Entity Translation Keys

### Sensors (32 total)

#### Power Monitoring
- `battery_soc` - Battery state of charge percentage
- `pv_power` - Solar panel power output
- `grid_power` - Grid power (import/export)
- `load_power` - Load power consumption
- `battery_power` - Battery charge/discharge power

#### Electrical Measurements
- `battery_voltage` - Battery voltage
- `battery_current` - Battery current
- `grid_voltage` - AC grid voltage
- `grid_frequency` - AC grid frequency
- `inverter_voltage` - Inverter output voltage
- `inverter_frequency` - Inverter output frequency
- `ac_charge_current` - AC charging current
- `pv_charge_current` - Solar charging current

#### Temperature
- `inverter_temperature` - Inverter internal temperature
- `battery_temperature` - Battery temperature

#### Energy Statistics
- `pv_energy_today` - Solar energy generated today
- `pv_energy_total` - Total solar energy generated
- `load_energy_today` - Load energy consumed today
- `load_energy_total` - Total load energy consumed
- `battery_charge_ah_today` - Battery charge amp-hours today
- `battery_discharge_ah_today` - Battery discharge amp-hours today
- `work_days_total` - Total operational days

#### System Status
- `charge_state` - Battery charging state
- `load_ratio` - Load percentage ratio
- `self_sufficiency` - Solar self-sufficiency rate
- `grid_dependency` - Grid dependency rate
- `system_efficiency` - Overall system efficiency

#### Diagnostics
- `ble_connection_quality` - Bluetooth signal strength (RSSI)
- `last_update` - Last successful data update timestamp
- `update_duration` - Data update cycle duration
- `failed_reads_count` - Failed communication attempts
- `success_rate` - Communication success rate percentage

### Switch
- `ac_power` - AC power on/off control

### Select
- `energy_priority` - Energy source priority selection
  - States: `solar_first`, `utility_first`, `battery_first`

### Binary Sensor
- `fault_detected` - System fault detection status

## Language Codes

Common language codes for Home Assistant:

- `en` - English
- `de` - German
- `fr` - French
- `es` - Spanish
- `it` - Italian
- `nl` - Dutch
- `pl` - Polish
- `pt` - Portuguese
- `ru` - Russian
- `zh-Hans` - Chinese (Simplified)
- `ja` - Japanese
- `ko` - Korean

## Testing Translations

1. Place your translation file in this directory
2. Restart Home Assistant
3. Change your Home Assistant language in User Profile
4. Verify all entity names appear correctly
5. Test the config flow setup dialog

## Support

If you have questions about translations:

1. Check the [Home Assistant Translation Guidelines](https://developers.home-assistant.io/docs/internationalization/)
2. Review existing translations in this directory
3. Open an issue on the GitHub repository

## License

Translations are part of the SRNE Inverter integration and follow the same license.
