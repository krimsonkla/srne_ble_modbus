# Quick Start Automation Examples

This directory contains simple, copy-paste automation examples for the SRNE SRNE BLE Modbus integration. These examples are designed to be easy to understand and modify without requiring blueprint knowledge.

## How to Use These Examples

1. **Choose an automation** that fits your needs
2. **Copy the entire file** to your Home Assistant `config/automations` directory
3. **Edit entity IDs** if they differ from your setup
4. **Adjust thresholds** and settings to match your requirements
5. **Reload automations** in Home Assistant (Developer Tools → YAML → Automations)

## Example Categories

### Basic Examples (Simple Operations)
- `simple_low_battery_alert.yaml` - Alert when battery SOC drops below 20%
- `simple_grid_failure.yaml` - Auto-switch to battery on grid failure
- `simple_fault_alert.yaml` - Immediate notification on fault detection
- `simple_schedule.yaml` - Time-based on/off scheduling
- `simple_high_load_alert.yaml` - Alert on high AC load

### Monitoring Examples (System Health)
- `battery_temp_monitor.yaml` - Battery temperature alerts (warning + critical)
- `pv_production_tracker.yaml` - Daily PV production summary
- `grid_stability_watch.yaml` - Grid voltage/frequency monitoring
- `efficiency_logger.yaml` - Daily efficiency and performance metrics

### Utility Examples (Convenience Features)
- `sunrise_activation.yaml` - Auto-start at sunrise
- `sunset_deactivation.yaml` - Auto-stop after sunset
- `maintenance_reminder.yaml` - Monthly maintenance checklist

## Common Entity IDs

All examples use standard entity IDs. Verify these exist in your setup:

| Entity ID | Description |
|-----------|-------------|
| `sensor.srne_inverter_battery_soc` | Battery state of charge (%) |
| `sensor.srne_inverter_battery_voltage` | Battery voltage (V) |
| `sensor.srne_inverter_battery_temperature` | Battery temperature (°C) |
| `sensor.srne_inverter_pv_power` | PV input power (W) |
| `sensor.srne_inverter_pv_energy_today` | Daily PV production (kWh) |
| `sensor.srne_inverter_ac_output_load` | AC output load (W) |
| `sensor.srne_inverter_grid_voltage` | Grid voltage (V) |
| `sensor.srne_inverter_grid_frequency` | Grid frequency (Hz) |
| `sensor.srne_inverter_fault_code` | Current fault code |
| `switch.srne_inverter_power` | Inverter on/off switch |
| `select.srne_inverter_output_priority` | Output priority mode |

## Customization Tips

### Adjusting Thresholds
```yaml
# Change from 20% to 30%
below: 30  # in numeric_state triggers
```

### Changing Notification Services
```yaml
# Use specific notification service
service: notify.mobile_app_your_phone

# Or persistent notification
service: persistent_notification.create
```

### Adding Delays/Debouncing
```yaml
# Wait 5 minutes before triggering
trigger:
  - platform: numeric_state
    entity_id: sensor.srne_inverter_battery_soc
    below: 20
    for:
      minutes: 5
```

### Multiple Actions
```yaml
action:
  - service: notify.notify
    data:
      message: "Alert!"

  - service: switch.turn_off
    target:
      entity_id: switch.some_device

  - delay:
      seconds: 10

  - service: script.some_script
```

## Notification Priority

Set priority based on urgency:

```yaml
data:
  priority: high      # Critical alerts
  priority: normal    # Standard notifications
  priority: low       # Informational only
```

## Sun Integration Setup

For sunrise/sunset automations, ensure sun integration is configured in `configuration.yaml`:

```yaml
# Configuration.yaml
sun:

homeassistant:
  latitude: YOUR_LATITUDE
  longitude: YOUR_LONGITUDE
```

## Testing Automations

1. **Manual Trigger**: Use Developer Tools → Actions → `automation.trigger`
2. **Trace**: Check automation traces in Settings → Automations → [Select automation] → Traces
3. **Logs**: Monitor Home Assistant logs for errors

## Combining Automations

You can combine multiple examples into one file:

```yaml
automation:
  - alias: "SRNE: Low Battery Alert"
    # ... first automation ...

  - alias: "SRNE: High Load Alert"
    # ... second automation ...

  - alias: "SRNE: Grid Failure"
    # ... third automation ...
```

## Troubleshooting

**Automation not triggering:**
- Check entity IDs are correct
- Verify sensors have valid values (not `unavailable` or `unknown`)
- Review automation traces for condition failures

**Entity not found:**
- Check your integration's actual entity IDs in Developer Tools → States
- Entity naming may vary based on device configuration

**Notification not received:**
- Verify notification service is configured
- Test with: Developer Tools → Actions → `notify.notify`

## Support

For more complex scenarios, see the blueprint examples in `examples/automations/blueprints/`.

For integration-specific questions, refer to the main documentation.
