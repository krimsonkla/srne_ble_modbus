# SRNE Inverter Automation Blueprints

Advanced Home Assistant blueprints for SRNE HF Series hybrid inverters with comprehensive safety, optimization, and monitoring features.

## Overview

This directory contains **27 production-ready blueprints** organized into three categories:

```
blueprints/automation/srne_inverter/
├── 1_safety/          (10 blueprints) - Critical protection systems
├── 2_optimization/    (10 blueprints) - Cost reduction and efficiency
└── 3_monitoring/      (7 blueprints)  - Performance tracking and alerts
```

## Category Structure

### 🛡️ Safety Blueprints (`1_safety/`)

**Priority:** Essential - Install these FIRST

Critical protection automations that prevent battery damage, handle grid failures, and ensure system safety:

1. **progressive_battery_protection.yaml** - Multi-stage load shedding at 30%/20%/10% SOC
2. **temperature_protection.yaml** - Charging/discharging limits with auto-recovery
3. **battery_protection.yaml** - Basic battery voltage and SOC protection
4. **grid_disconnection_handler.yaml** - 4-stage load shedding with soft-start recovery
5. **grid_failure_detection.yaml** - Auto-switch to battery on grid loss
6. **thermal_stress_protector.yaml** - Graduated power derating at high temperatures
7. **generator_auto_start.yaml** - Automatic generator control at low SOC
8. **under_frequency_load_shed.yaml** - 4-stage protection during frequency sag
9. **soft_start_recovery.yaml** - Gentle voltage restoration after faults
10. **fault_response.yaml** - Intelligent fault handling and recovery

📖 **Full documentation:** `1_safety/README.md`

### ⚡ Optimization Blueprints (`2_optimization/`)

**Priority:** Recommended - Install after safety is tested

Cost reduction and efficiency maximization automations:

1. **peak_shaving_optimizer.yaml** - Enhanced demand management with frequency response
2. **peak_shaving.yaml** - Basic peak demand reduction
3. **solar_optimization.yaml** - Maximize solar self-consumption
4. **solar_midday_boost.yaml** - PV priority during peak production
5. **smart_night_charging.yaml** - Off-peak grid charging with weather awareness
6. **dynamic_current_limiter.yaml** - Auto-adjust charge current based on surplus
7. **ev_charging_optimizer.yaml** - Smart EV charging (off-peak + solar)
8. **time_of_use_scheduler.yaml** - Daily mode switching for TOU rates
9. **solar_export_optimizer.yaml** - Control devices to maximize self-consumption
10. **equalizing_charge_scheduler.yaml** - Weekly maintenance for lead-acid batteries

📖 **Full documentation:** `2_optimization/README.md`

### 📊 Monitoring Blueprints (`3_monitoring/`)

**Priority:** Optional - Enhanced visibility and analytics

Performance tracking, health monitoring, and advanced analytics:

1. **daily_performance_dashboard.yaml** - Comprehensive KPI tracking and reporting
2. **daily_energy_report.yaml** - Basic daily energy summary
3. **battery_health_tracker.yaml** - Weekly health checks and EOL prediction
4. **fault_monitor_alert.yaml** - Enhanced fault monitoring with auto-restart
5. **seasonal_parameter_adjuster.yaml** - Automatic winter/summer mode switching
6. **weather_based_priority.yaml** - Cloud coverage-based priority adjustment

📖 **Full documentation:** `3_monitoring/README.md`

## Quick Start

### 1. Choose Your Path

**Beginner?** Start with simple examples:
- Go to `../../examples/automations/quick_start/`
- Copy-paste ready automations without blueprints

**Ready for blueprints?** Continue below.

### 2. Essential Setup (Day 1)

Import and configure these safety automations:

```yaml
# Start with battery protection
1. progressive_battery_protection.yaml
   - Set critical_soc: 20%
   - Set emergency_soc: 10%
   - Configure notification service

2. temperature_protection.yaml
   - Set charge_max_temperature: 45°C
   - Set discharge_max_temperature: 60°C
   - Map battery temperature sensor
```

### 3. Add Optimization (Week 1)

After safety is tested, add efficiency:

```yaml
# Peak hours protection
3. peak_shaving_optimizer.yaml
   - Set peak hours (e.g., 16:00-21:00)
   - Set grid import threshold: 1000W
   - Set minimum battery SOC: 30%

# Solar maximization
4. solar_midday_boost.yaml
   - Automatic 10:00-15:00 optimization
   - PV priority during peak production
```

### 4. Monitor Performance (Week 2+)

Track and optimize:

```yaml
# Daily analytics
5. daily_performance_dashboard.yaml
   - Set report time: 23:00
   - Choose notification style: "detailed"
   - Enable cost analysis
```

## Importing Blueprints

### Method 1: Home Assistant UI

1. Go to **Settings** → **Automations & Scenes** → **Blueprints**
2. Click **Import Blueprint**
3. Enter GitHub raw URL for desired blueprint
4. Click **Preview** then **Import**

### Method 2: YAML Configuration

```yaml
# configuration.yaml
blueprint:
  auto_reload: true

# Import from local file
automation: !include_dir_merge_list automations/
```

## Blueprint Configuration

All blueprints follow this pattern:

```yaml
automation:
  - alias: "My SRNE Automation"
    use_blueprint:
      path: srne_inverter/1_safety/progressive_battery_protection.yaml
      input:
        inverter_device: <select_your_device>
        battery_soc_sensor: sensor.srne_inverter_battery_soc
        critical_soc: 20
        emergency_soc: 10
        notification_service: notify.mobile_app_phone
```

## Entity Requirements

Common entities needed (verify your actual entity IDs):

```yaml
# Core sensors
sensor.srne_inverter_battery_soc          # Battery state of charge (%)
sensor.srne_inverter_battery_voltage      # Battery voltage (V)
sensor.srne_inverter_battery_temperature  # Battery temperature (°C)
sensor.srne_inverter_pv_power             # PV input power (W)
sensor.srne_inverter_ac_output_load       # AC output load (W)
sensor.srne_inverter_grid_voltage         # Grid voltage (V)
sensor.srne_inverter_grid_frequency       # Grid frequency (Hz)

# Control entities
select.srne_inverter_output_priority      # Energy priority mode
number.srne_inverter_charge_current       # Charge current limit (A)
switch.srne_inverter_charging             # Charging enable/disable
```

Check `../../custom_components/srne_inverter/config/entities_pilot.yaml` for complete entity list.

## Coordination

Blueprints are designed to work together:

### Priority Hierarchy
```
SAFETY (highest)     → Overrides everything
  ↓
OPTIMIZATION        → Respects safety limits
  ↓
MONITORING (lowest) → Observes and reports
```

### Shared Resources
- All blueprints use the same `priority_select` entity
- Safety automations use `mode: queued` (sequential processing)
- Optimization automations use `mode: single` (prevent conflicts)
- Hysteresis prevents rapid mode switching

### Time-Based Coordination
```
00:00-07:00  Smart Night Charging (off-peak)
07:00-10:00  Normal operation (PV + battery)
10:00-15:00  Solar Midday Boost (maximize PV)
15:00-16:00  Transition period
16:00-21:00  Peak Shaving (avoid high rates)
21:00-23:00  Evening operation
23:00        Daily performance report
```

## Documentation Files

- **QUICK_START.md** - 5-minute setup guide
- **ESSENTIAL_BLUEPRINTS.md** - Detailed feature documentation
- **QUICK_REFERENCE.md** - Quick lookup tables
- **NEW_BLUEPRINTS.md** - Complete blueprint catalog
- **IMPLEMENTATION_SUMMARY.md** - Technical specifications
- **PROJECT_COMPLETE.md** - Project overview

## Safety Guidelines

⚠️ **Critical Safety Rules**

1. **Test before relying** - Monitor for 24 hours in safe conditions
2. **Safety first** - Always start with battery and temperature protection
3. **Know your battery** - Use manufacturer specifications for thresholds
4. **Monitor initially** - Check logs and notifications frequently at first
5. **Don't disable all safety** - Keep at least basic battery protection active
6. **Emergency preparedness** - Have manual override procedures ready

## Troubleshooting

### Blueprints Not Appearing
- Check blueprint import URL is correct (raw GitHub URL)
- Verify `blueprint:` is in configuration.yaml
- Restart Home Assistant after first import

### Entity Not Found
- Check entity IDs in Developer Tools → States
- Entity names may vary based on device configuration
- Use device selector instead of specific entity IDs

### Automations Conflicting
- Verify only one automation modifies priority at a time
- Check time-based triggers don't overlap
- Review automation traces in UI for condition failures

### Mode Changes Too Frequent
- Increase hysteresis values (default: 5 units)
- Add longer delays before mode switches
- Check for sensor noise or fluctuations

## Quality Assurance

✅ **All blueprints reviewed and approved**
- Comprehensive safety analysis
- Logic validation
- Entity reference standards
- Documentation quality check
- See: `../../docs/QUALITY_REVIEW.md`

**Status:** Production Ready
- 0 Critical Issues
- 3 Minor warnings (documented)
- 8 Recommendations for future improvements

## Support

- **Integration Issues:** See main repository README
- **Entity Mapping:** Check `entities_pilot.yaml`
- **Blueprint Questions:** Review category README files
- **Bug Reports:** Use GitHub issues with "automation" label

## Version History

- **v1.0** - Initial release (Feb 2026)
  - 27 production-ready blueprints
  - 3-tier category structure
  - Comprehensive documentation
  - Quality reviewed and approved
