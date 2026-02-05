# SRNE Inverter Automation Examples

This directory contains example automations for the SRNE HF Series Inverter Home
Assistant integration.

## Available Automations

### Round 1 & 2 Automations

#### 1. Sunrise/Sunset Control

**Files**: `sunrise_inverter.yaml`, `sunset_inverter.yaml`

Automatically turn the AC inverter on at sunrise and off at sunset, following
the sun's schedule.

**Use Case**: Maximize solar usage during daylight hours, preserve battery at
night.

#### 2. Battery Protection

**Files**: `low_battery_protection.yaml`, `high_battery_restore.yaml`

Protect your battery from deep discharge by automatically turning off the
inverter at 20% and restoring power at 80%.

**Use Case**: Extend battery lifespan by preventing deep discharge damage.

#### 3. Scheduled Power

**File**: `schedule_power.yaml`

Turn the inverter on/off at specific times each day (6 AM on, 10 PM off).

**Use Case**: Consistent daily schedule, predictable power availability.

---

### Round 3 Automations (Power Monitoring & Priority Control)

#### 4. High Load Alert

**File**: `high_load_alert.yaml`

Sends notifications when load power consumption exceeds a threshold (default
5kW).

**Use Case**: Monitor excessive power usage, prevent overload conditions, track
high-consumption events.

#### 5. Solar Export Optimization

**File**: `solar_export_optimization.yaml`

Automatically turns on high-power devices (water heater, etc.) when excess solar
power is being exported to the grid.

**Use Case**: Maximize self-consumption, reduce grid export, use excess solar
for heating/charging.

#### 6. Grid Import Monitor

**File**: `grid_import_monitor.yaml`

Alerts when importing from grid during solar hours when solar production should
be sufficient.

**Use Case**: Detect unexpected grid usage, identify system issues, optimize
solar utilization.

#### 7. Time of Use Priority Control

**File**: `time_of_use_priority.yaml`

Automatically switches energy priority based on electricity tariff schedule
(peak/off-peak/solar hours).

**Use Case**: Minimize electricity costs with TOU rates, maximize battery usage
during peak hours, charge from grid during off-peak.

#### 8. Weather-Based Priority

**File**: `weather_based_priority.yaml`

Adjusts energy priority based on weather forecast (solar first on sunny days,
utility first on cloudy days).

**Use Case**: Optimize energy strategy based on expected solar production,
preserve battery on cloudy days.

#### 9. Battery Preservation

**File**: `battery_preservation.yaml`

Automatically switches to utility power when battery SOC is low to prevent deep
discharge.

**Use Case**: Extend battery lifespan, prevent deep discharge damage, automatic
battery protection.

#### 10. Battery Health Monitor

**File**: `battery_health_monitor.yaml`

Monitors battery voltage for health issues and alerts if outside safe operating
range.

**Use Case**: Early detection of battery problems, prevent over-voltage/under-
voltage damage.

#### 11. Charging Efficiency Logger

**File**: `charging_efficiency_log.yaml`

Logs battery charging current during solar hours to track charging efficiency
and performance.

**Use Case**: Monitor system performance over time, detect charging issues,
optimize solar panel placement.

#### 12. Discharge Rate Alert

**File**: `discharge_rate_alert.yaml`

Monitors battery discharge rate and alerts if exceeding safe limits.

**Use Case**: Prevent damage from excessive discharge current, identify high-
load conditions.

#### 13. Overheat Protection

**File**: `overheat_protection.yaml`

Automatically shuts down inverter if temperature exceeds safe limits (default
60°C).

**Use Case**: Critical safety feature, prevent equipment damage, protect
investment.

#### 14. Battery Temperature Alert

**File**: `battery_temp_alert.yaml`

Monitors battery temperature and alerts if outside safe operating range (10-
45°C).

**Use Case**: Ensure optimal battery performance, extend battery lifespan,
detect cooling issues.

#### 15. Temperature Trend Monitor

**File**: `temperature_trend_monitor.yaml`

Monitors rapid temperature changes to detect potential problems like cooling
failures.

**Use Case**: Early warning system, detect equipment issues before failure,
monitor cooling effectiveness.

---

### Round 4 Automations (Energy Statistics & System Health)

#### 16. Daily Energy Report

**File**: `daily_energy_report.yaml`

Sends a comprehensive daily summary at 11:55 PM with solar production, load
consumption, battery cycles, and self-sufficiency percentage.

**Use Case**: Track daily performance, monitor system efficiency, maintain
energy logs for analysis or tax purposes.

#### 17. System Fault Alert

**File**: `fault_alert.yaml`

Immediately alerts when a system fault is detected with detailed fault bit
information for troubleshooting.

**Use Case**: Critical system monitoring, prevent damage from undetected faults,
quick response to equipment failures.

#### 18. Grid Stability Monitor

**File**: `grid_stability_monitor.yaml`

Monitors grid voltage and frequency to detect power quality issues. Alerts when
values fall outside normal ranges (230V ±10%, 50Hz ±2%).

**Use Case**: Detect grid problems before they damage equipment, monitor power
quality, early warning for potential outages.

#### 19. Solar Production Tracking

**File**: `solar_production_tracking.yaml`

Tracks daily and total solar production with milestone notifications and weekly
summaries. Celebrates when daily goals are reached.

**Use Case**: Monitor system performance over time, track ROI, celebrate
achievements, identify performance trends.

#### 20. Battery Cycle Tracking

**File**: `battery_cycle_tracking.yaml`

Monitors daily charge/discharge cycles, warns about excessive cycling, and
reports on battery health metrics including cycle depth.

**Use Case**: Extend battery lifespan, optimize battery usage, early detection
of battery degradation.

#### 21. System Efficiency Calculation

**File**: `efficiency_calculation.yaml`

Calculates daily efficiency metrics including self-sufficiency percentage,
solar utilization, and battery round-trip efficiency.

**Use Case**: Optimize system configuration, track performance improvements,
identify inefficiencies.

#### 22. Low Production Alert

**File**: `low_production_alert.yaml`

Alerts when solar production is unexpectedly low during daylight hours,
indicating possible panel issues, shading, or equipment problems.

**Use Case**: Early detection of system issues, maintain optimal performance,
prevent revenue loss.

#### 23. Grid Outage Detection

**File**: `grid_outage_detection.yaml`

Detects grid outages by monitoring grid voltage, automatically switches to
battery backup, and restores when grid returns.

**Use Case**: Automatic failover to backup power, maintain critical loads during
outages, seamless grid restoration.

## Installation

### Method 1: Copy to Configuration

1. Copy the desired automation file to your Home Assistant configuration
   directory:
   ```bash
   cp sunrise_inverter.yaml /config/automations/
   ```

2. Add to your `configuration.yaml`:
   ```yaml
   automation: !include_dir_merge_list automations/
   ```

3. Restart Home Assistant or reload automations

### Method 2: Add via UI

1. Go to **Settings → Automations & Scenes**
2. Click **+ Create Automation**
3. Choose **Start with an empty automation**
4. Click **⋮** → **Edit in YAML**
5. Copy and paste the content from the example file
6. Save

## Customization

All automations can be customized to fit your needs:

### Adjust Times

Change trigger times to match your schedule:

```yaml
trigger:
  - platform: time
    at: "07:00:00" # Change from 6 AM to 7 AM
```

### Adjust Battery Thresholds

Change battery protection levels:

```yaml
trigger:
  - platform: numeric_state
    entity_id: sensor.battery_soc
    below: 30 # Change from 20% to 30%
```

### Add Conditions

Add conditions to prevent automations in certain situations:

```yaml
condition:
  - condition: state
    entity_id: input_boolean.vacation_mode
    state: "off" # Don't run when on vacation
```

### Add Multiple Actions

Perform multiple actions:

```yaml
action:
  - service: switch.turn_on
    target:
      entity_id: switch.ac_power
  - service: light.turn_on
    target:
      entity_id: light.indicator
  - service: notify.mobile_app
    data:
      message: "Inverter powered on"
```

## Entity IDs

These automations reference the following entities from the SRNE integration:

### Round 1 & 2 Entities

- `switch.srne_inverter_ac_power` - AC inverter power switch
- `sensor.srne_inverter_battery_soc` - Battery state of charge (0-100%)

### Round 3 Entities (New)

- `sensor.srne_inverter_pv_power` - PV (solar) power output (W)
- `sensor.srne_inverter_grid_power` - Grid power (W, positive=import,
  negative=export)
- `sensor.srne_inverter_load_power` - Load power consumption (W)
- `sensor.srne_inverter_battery_voltage` - Battery voltage (V)
- `sensor.srne_inverter_battery_current` - Battery current (A,
  positive=charging, negative=discharging)
- `sensor.srne_inverter_inverter_temperature` - Inverter temperature (°C)
- `sensor.srne_inverter_battery_temperature` - Battery temperature (°C)
- `select.srne_inverter_energy_priority` - Energy priority selection (Solar
  First/Utility First/Battery First)

### Round 4 Entities (Energy Statistics & System Health)

**Energy Statistics:**

- `sensor.srne_inverter_pv_energy_today` - Solar production today (kWh)
- `sensor.srne_inverter_load_energy_today` - Load consumption today (kWh)
- `sensor.srne_inverter_pv_energy_total` - Cumulative solar production (kWh)
- `sensor.srne_inverter_load_energy_total` - Cumulative load consumption (kWh)
- `sensor.srne_inverter_battery_charge_ah_today` - Battery charged today (AH)
- `sensor.srne_inverter_battery_discharge_ah_today` - Battery discharged today
  (AH)
- `sensor.srne_inverter_work_days_total` - Total system uptime (days)

**System Health:**

- `sensor.srne_inverter_charge_state` - Battery charging state
- `sensor.srne_inverter_grid_voltage` - Grid voltage (V)
- `sensor.srne_inverter_grid_frequency` - Grid frequency (Hz)
- `sensor.srne_inverter_inverter_voltage` - Inverter output voltage (V)
- `sensor.srne_inverter_inverter_frequency` - Inverter output frequency (Hz)
- `binary_sensor.srne_inverter_fault_detected` - System fault indicator

**Advanced Monitoring:**

- `sensor.srne_inverter_ac_charge_current` - AC charging current (A)
- `sensor.srne_inverter_pv_charge_current` - PV charging current (A)
- `sensor.srne_inverter_load_ratio` - Load percentage (%)

Make sure these entity IDs match your actual entity IDs. You can check in:
**Developer Tools → States**

## Safety Notes

### Battery Protection

The low battery protection automation (20% threshold) is **recommended** to
prevent battery damage. Deep discharge can permanently reduce battery capacity.

### Command Spacing

The integration enforces a 10-second delay between BLE commands. Rapid on/off
cycles will be queued automatically - no special handling needed in automations.

### Grid Backup

If your inverter has grid backup, ensure you understand how power switching
affects your setup. Some configurations may require grid connection for inverter
startup.

## Troubleshooting

### Automation Not Triggering

1. Check automation is enabled (should show blue "Enabled" badge)
2. Verify entity IDs are correct
3. Check conditions are met
4. Review automation trace: Click **⋮** → **Traces**

### Inverter Not Responding

1. Check BLE connection in integration
2. Verify inverter is powered on
3. Check inverter isn't in fault state
4. Review logs: **Settings → System → Logs**

### Timing Issues

If sunrise/sunset times seem wrong:

1. Verify Home Assistant location is set correctly
2. Check timezone configuration
3. Add/remove offset as needed

## Advanced Examples

### Weekend-Only Schedule

Run automation only on weekends:

```yaml
condition:
  - condition: time
    weekday:
      - sat
      - sun
```

### Season-Based Control

Different behavior in summer vs winter:

```yaml
condition:
  - condition: template
    value_template: "{{ now().month in [6,7,8] }}" # Summer months
```

### Multi-Condition Safety

Combine multiple conditions:

```yaml
condition:
  - condition: numeric_state
    entity_id: sensor.battery_soc
    above: 30
  - condition: state
    entity_id: binary_sensor.grid_available
    state: "off"
  - condition: sun
    after: sunrise
```

## Contributing

Have a useful automation? Submit a pull request or open an issue with your
example!

## Support

For issues with these automations:

1. Check Home Assistant logs
2. Review integration documentation
3. Open an issue:
   https://github.com/krimsonkla/srne_ble_modbus/issues

## License

These automation examples are provided as-is for use with the SRNE HF Series
Inverter integration.
