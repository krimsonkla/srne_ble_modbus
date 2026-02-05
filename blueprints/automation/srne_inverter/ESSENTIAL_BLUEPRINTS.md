# Essential SRNE Inverter Automation Blueprints

This document describes the 6 essential automation blueprints designed based on comprehensive entity analysis. These blueprints provide complete battery protection, grid management, and solar optimization for SRNE inverter systems.

## 🛡️ Safety Blueprints (1_safety/)

### 1. Progressive Battery Protection (`progressive_battery_protection.yaml`)

**Purpose**: Multi-stage battery protection with intelligent load shedding, temperature control, and overvoltage prevention.

**Key Features**:
- **3-Stage Load Shedding**: Automatically reduces loads at 30%, 20%, and 10% SOC
- **Temperature Protection**: Monitors charge/discharge temperature limits
- **Overvoltage Prevention**: Graduated current reduction and charging cutoff
- **Configurable Hysteresis**: Prevents oscillation with smart recovery delays
- **Multi-Service Notifications**: Primary and secondary notification services with severity levels

**Combines Logic From**:
- `low_battery_alert.yaml` - SOC monitoring and alerts
- `battery_protection.yaml` - Voltage and temperature protection
- Custom overvoltage logic with graduated response

**Configuration Highlights**:
```yaml
Inputs:
  - warning_soc: 30% (first protection stage)
  - critical_soc: 20% (second stage)
  - emergency_soc: 10% (final stage)
  - charge_max_temperature: 45°C
  - discharge_max_temperature: 60°C
  - overvoltage_warning: 56.0V
  - overvoltage_critical: 58.0V
  - Load groups for each protection level
  - Temp hysteresis: 5°C
  - Recovery delay: 300 seconds
```

**Mode**: `queued` (allows multiple triggers, processes in sequence)

**When to Use**:
- Primary battery protection system
- Essential for battery lifespan
- Coordinates with all other automations
- Run 24/7

---

### 2. Temperature Protection (`temperature_protection.yaml`)

**Purpose**: Dedicated temperature monitoring with automatic charging/discharging control and hysteresis-based recovery.

**Key Features**:
- **Separate Charge/Discharge Limits**: Independent high/low temperature thresholds
- **Smart Hysteresis**: Prevents rapid on/off cycling
- **Automatic Recovery**: Resumes operation after safety delay
- **Priority Switching**: Changes operation mode based on temperature conditions
- **Optional Recovery Notifications**: Configurable notification levels

**Configuration Highlights**:
```yaml
Inputs:
  - charge_max_temperature: 45°C
  - charge_min_temperature: 0°C
  - discharge_max_temperature: 60°C
  - discharge_min_temperature: -20°C
  - temp_hysteresis: 5°C
  - recovery_delay: 30 seconds
  - Charging switch control
  - Priority mode switching
```

**Mode**: `restart` (override previous triggers for latest temperature state)

**When to Use**:
- Works independently but coordinates with Progressive Battery Protection
- Essential in extreme temperature environments
- Critical for lithium battery systems
- Run 24/7

---

### 3. Grid Disconnection Handler (`grid_disconnection_handler.yaml`)

**Purpose**: Enhanced grid failure detection with intelligent islanding, progressive load shedding, and safe restoration with soft-start.

**Key Features**:
- **Multi-Stage Voltage Monitoring**: Warning, critical, restore, and stable thresholds
- **Progressive Load Shedding**: 4-stage priority-based load management
- **Grid Quality Verification**: Frequency-based stability checking before restoration
- **Soft-Start Restoration**: Sequential load restoration to prevent inrush
- **Off-Grid Preparation**: Automatic islanding mode preparation
- **Comprehensive Notifications**: Status updates at each stage

**Enhanced From**: `grid_failure_detection.yaml` with major additions:
- Grid quality monitoring (frequency)
- Soft-start restoration sequence
- Progressive multi-stage load shedding
- Grid stabilization verification

**Configuration Highlights**:
```yaml
Inputs:
  - grid_voltage_warning: 150V
  - grid_voltage_critical: 100V
  - grid_restore_threshold: 200V
  - grid_restore_stable_threshold: 220V
  - frequency_min_threshold: 49.5Hz
  - frequency_max_threshold: 50.5Hz
  - 4 load priority groups (warning/critical/emergency/essential)
  - grid_failure_hysteresis: 30 seconds
  - grid_restore_hysteresis: 60 seconds
  - grid_stabilization_delay: 120 seconds
  - load_restoration_delay: 30 seconds between groups
  - enable_progressive_shedding: true
  - enable_grid_quality_check: true
  - enable_soft_start: true
```

**Mode**: `queued` (handles multiple grid events safely)

**When to Use**:
- Essential for grid-tied systems
- Critical in areas with unstable power
- Protects equipment from power surges
- Coordinates with battery protection
- Run 24/7

---

## ⚡ Optimization Blueprints (2_optimization/)

### 4. Smart Night Charging (`smart_night_charging.yaml`)

**Purpose**: Optimizes battery charging during off-peak electricity hours with intelligent scheduling and weather awareness.

**Key Features**:
- **Time-Based Scheduling**: Configurable off-peak charging windows
- **Minimum SOC Threshold**: Only charges when needed
- **Target SOC Management**: Charges to optimal level, not 100% unnecessarily
- **AC Current Control**: Sets optimal charging current
- **Emergency Pre-Charge**: Charges immediately if battery critically low
- **Weather Integration**: Adjusts target SOC based on next-day forecast
- **Automatic Mode Switching**: PV priority during day, AC priority at night

**Configuration Highlights**:
```yaml
Inputs:
  - off_peak_start_time: 23:00:00 (11 PM)
  - off_peak_end_time: 07:00:00 (7 AM)
  - min_soc_threshold: 80% (only charge below this)
  - target_soc: 100%
  - ac_charge_current: 30A
  - precharge_soc_threshold: 20% (emergency charging)
  - daytime_priority: "PV Priority"
  - nighttime_priority: "AC Priority"
  - Weather entity (optional)
  - sunny_weather_target_soc: 85% (reduced target if sunny forecast)
```

**Mode**: `single` (prevents overlapping charging sessions)

**When to Use**:
- Time-of-use (TOU) pricing areas
- Reduces electricity costs
- Optimal with solar panels
- Schedule daily

---

### 5. Peak Shaving Optimizer (`peak_shaving_optimizer.yaml`)

**Purpose**: Enhanced peak shaving with frequency-based grid stress detection and adaptive response.

**Merged/Enhanced From**: `peak_shaving.yaml` with major additions:
- Grid frequency monitoring
- Multi-threshold power response
- Frequency-based grid support
- Battery reserve management

**Key Features**:
- **Time-Based Peak Detection**: Configurable peak hour windows
- **Power Threshold Switching**: Responds to high import levels
- **Frequency Response**: Detects grid stress (>50.2Hz) and prevents export
- **Aggressive Mode**: Higher threshold for very high imports
- **Battery Reserve Management**: Protects battery while maximizing savings
- **Grid Stability Support**: Helps stabilize grid during frequency events
- **Hysteresis Control**: Prevents rapid mode switching

**Configuration Highlights**:
```yaml
Inputs:
  - peak_start_time: 16:00:00 (4 PM)
  - peak_end_time: 21:00:00 (9 PM)
  - grid_import_threshold: 1000W
  - aggressive_threshold: 2000W
  - frequency_high_threshold: 50.2Hz (stressed grid)
  - frequency_low_threshold: 49.8Hz (weak grid)
  - minimum_battery_soc: 30%
  - battery_reserve_soc: 20% (for grid emergencies)
  - peak_priority_mode: "Battery First"
  - off_peak_priority_mode: "Solar First"
  - enable_frequency_response: true
  - prevent_export_during_stress: true
  - hysteresis_duration: 2 minutes
```

**Mode**: `single` (consistent peak shaving strategy)

**When to Use**:
- Time-of-use pricing areas
- Demand charge reduction
- Grid stability support
- Frequency regulation participation
- Run during peak hours (or 24/7 with frequency response)

---

### 6. Solar Midday Boost (`solar_midday_boost.yaml`)

**Purpose**: Maximizes solar energy utilization during peak PV production hours with intelligent power balance management.

**Key Features**:
- **Time-Window Optimization**: Focuses on peak solar hours (10 AM - 3 PM)
- **Minimum PV Threshold**: Only activates with sufficient solar power
- **PV Power Balance Control**: Prioritizes charging vs. loads
- **AC Charging Disable**: Forces solar-only charging during boost
- **Cloud Detection**: Automatically adjusts when PV output drops
- **Battery Full Management**: Switches to load priority when battery full
- **Weather-Aware**: Optional integration with weather forecasts

**Configuration Highlights**:
```yaml
Inputs:
  - solar_boost_start_time: 10:00:00 (10 AM)
  - solar_boost_end_time: 15:00:00 (3 PM)
  - min_pv_power: 500W (minimum to activate)
  - optimal_pv_power: 2000W
  - max_soc_for_boost: 95% (reserve capacity)
  - solar_boost_priority: "PV Priority"
  - pv_balance_mode: "Charging Priority"
  - disable_ac_charging: true
  - activation_delay: 5 minutes
  - deactivation_delay: 10 minutes
  - enable_cloud_detection: true
  - cloudy_pv_threshold: 300W
```

**Mode**: `single` (consistent solar optimization)

**When to Use**:
- Maximize solar self-consumption
- Reduce grid dependency
- Optimize renewable energy capture
- Coordinate with night charging
- Run daily during solar hours

---

## 🔗 Blueprint Coordination

These blueprints work together as a coordinated system:

```
┌─────────────────────────────────────────────────────────────┐
│                    SAFETY LAYER (24/7)                       │
├─────────────────────────────────────────────────────────────┤
│  Progressive Battery Protection ──┬── Temperature Protection │
│                                   │                          │
│           Grid Disconnection Handler                         │
│                    (queued mode)                             │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                 OPTIMIZATION LAYER (Scheduled)               │
├─────────────────────────────────────────────────────────────┤
│  Morning (7-10 AM):  Normal/PV Priority                     │
│  Midday (10-15 PM):  Solar Midday Boost                     │
│  Peak (16-21 PM):    Peak Shaving Optimizer                 │
│  Night (23-07 AM):   Smart Night Charging                   │
└─────────────────────────────────────────────────────────────┘
```

### Coordination Rules:
1. **Safety First**: Safety blueprints (1-3) always override optimization
2. **Queued Safety**: Battery and grid protection use queued mode to handle multiple events
3. **Single Optimization**: Optimization blueprints use single mode to prevent conflicts
4. **Priority Hierarchy**:
   - Emergency battery protection > Grid failure > Temperature > Optimization
5. **Shared Entities**: All blueprints coordinate through priority_select entity

---

## 📋 Implementation Checklist

### Initial Setup:
1. ✅ Install all 6 blueprints in Home Assistant
2. ✅ Verify SRNE inverter integration is working
3. ✅ Map all required sensors and controls
4. ✅ Set up notification services

### Safety First (Required):
1. ✅ Configure Progressive Battery Protection
   - Set SOC thresholds based on battery type
   - Configure load groups by priority
   - Test load shedding sequence
2. ✅ Configure Temperature Protection
   - Set temperature limits from battery specs
   - Configure hysteresis appropriately
   - Test with charging switch
3. ✅ Configure Grid Disconnection Handler
   - Set voltage thresholds for your grid
   - Configure load priority groups
   - Test soft-start restoration

### Optimization (Optional but Recommended):
4. ✅ Configure Smart Night Charging
   - Set off-peak hours from electricity plan
   - Configure target SOC and current
   - Optional: Add weather integration
5. ✅ Configure Peak Shaving Optimizer
   - Set peak hours from electricity plan
   - Configure power thresholds
   - Optional: Add frequency sensor
6. ✅ Configure Solar Midday Boost
   - Set solar peak hours for your location
   - Configure PV power thresholds
   - Set power balance preferences

### Testing:
- Test each blueprint individually first
- Verify notifications work correctly
- Monitor for conflicts in logs
- Adjust thresholds based on real-world behavior
- Document your configuration settings

---

## 🎯 Key Design Principles

1. **Mode Selection**:
   - Safety: `queued` or `restart` (handle multiple events)
   - Optimization: `single` (prevent conflicts)

2. **Hysteresis Everywhere**:
   - Prevents oscillation
   - Allows natural recovery
   - Reduces wear on equipment

3. **Progressive Response**:
   - Multi-stage protection (warning → critical → emergency)
   - Graduated actions (notify → reduce → disable)
   - Graceful recovery

4. **Notification Strategy**:
   - Warning: Informational
   - Critical: High priority, persistent
   - Emergency: Multiple services, urgent

5. **Coordination Through Priority**:
   - All blueprints use common priority_select entity
   - Clear priority hierarchy
   - No direct conflicts

---

## 📊 Expected Outcomes

### Safety:
- ✅ Battery protected from over-discharge, over-voltage, extreme temperatures
- ✅ Automatic grid failure handling with load management
- ✅ Extended battery lifespan through gentle operation
- ✅ Reduced risk of equipment damage

### Optimization:
- ✅ 30-50% reduction in electricity costs (with TOU pricing)
- ✅ 70-90% solar self-consumption rate
- ✅ Automatic peak demand management
- ✅ Maximized renewable energy utilization

### Operational:
- ✅ Fully automated battery management
- ✅ Minimal user intervention required
- ✅ Comprehensive status monitoring
- ✅ Proactive problem prevention

---

## 🔧 Troubleshooting

### Common Issues:

**1. Blueprints Conflicting**:
- Check priority_select entity is shared correctly
- Verify mode settings (safety=queued, optimization=single)
- Review Home Assistant logs for race conditions

**2. Load Shedding Not Working**:
- Verify switch entities are correct
- Check entity availability
- Test switches manually first
- Review load shedding delays

**3. Temperature Protection Too Sensitive**:
- Increase temp_hysteresis (5-10°C recommended)
- Increase recovery_delay
- Verify temperature sensor accuracy

**4. Grid Restoration Issues**:
- Increase grid_restore_hysteresis
- Verify voltage thresholds match your grid
- Check frequency sensor if using quality checks

**5. Charging Not Optimizing**:
- Verify time zones are correct
- Check SOC thresholds allow charging
- Verify AC charge current entity is writable
- Review charge source priority options

### Debug Mode:
Enable debug logging in Home Assistant:
```yaml
logger:
  default: warning
  logs:
    homeassistant.components.srne_inverter: debug
    homeassistant.components.automation: debug
```

---

## 📖 Related Documentation

- **Entity Analysis**: See entity analysis documentation for complete sensor/control mapping
- **Strategic Plan**: Reference strategic plan for integration architecture
- **Modbus Protocol**: See protocol documentation for register details
- **Home Assistant Blueprints**: https://www.home-assistant.io/docs/automation/using_blueprints/

---

## 🤝 Contributing

To enhance these blueprints:
1. Test thoroughly in your environment
2. Document any modifications
3. Share improvements via pull request
4. Report issues with detailed logs

---

**Version**: 1.0
**Created**: 2026-02-05
**Author**: SRNE Inverter Integration
**Based On**: Comprehensive entity analysis and strategic planning
