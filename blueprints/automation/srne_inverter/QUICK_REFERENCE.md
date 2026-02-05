# SRNE Inverter Blueprints - Quick Reference

## All Available Blueprints

| # | Name | Category | Priority | Key Features |
|---|------|----------|----------|--------------|
| 1 | **Dynamic Current Limiter** | Optimization | ⭐⭐⭐ | Real-time charge current adjustment, solar surplus calculation |
| 2 | **EV Charging Optimizer** | Optimization | ⭐⭐⭐ | Off-peak + solar charging, grid limit protection |
| 3 | **Time of Use Scheduler** | Optimization | ⭐⭐⭐⭐⭐ | Daily mode switching, TOU rate optimization |
| 4 | **Solar Export Optimizer** | Optimization | ⭐⭐⭐⭐ | Device control during export, priority-based loads |
| 5 | **Equalizing Charge Scheduler** | Optimization | ⭐⭐ | Lead-acid equalization, battery maintenance |
| 6 | **Thermal Stress Protector** | Safety | ⭐⭐⭐⭐⭐ | Graduated derating, emergency shutdown |
| 7 | **Generator Auto-Start** | Safety | ⭐⭐⭐⭐ | Backup power, low battery protection |
| 8 | **Under-Frequency Load Shed** | Safety | ⭐⭐⭐ | 4-stage load shedding, frequency stability |
| 9 | **Soft Start Recovery** | Safety | ⭐⭐⭐⭐ | Controlled restart, voltage ramp, recovery period |
| 10 | **Fault Monitor Alert** | Monitoring | ⭐⭐⭐⭐⭐ | Enhanced fault response, auto-restart, escalation |
| 11 | **Battery Health Tracker** | Monitoring | ⭐⭐⭐⭐ | Health checks, EOL prediction, maintenance alerts |

**Priority Legend:**
- ⭐⭐⭐⭐⭐ Essential (recommended for all users)
- ⭐⭐⭐⭐ Highly Recommended (important for most setups)
- ⭐⭐⭐ Recommended (beneficial for specific use cases)
- ⭐⭐ Optional (specialized applications)

---

## Required Entities by Blueprint

### Universal Requirements (All Blueprints)
- `inverter_device` - Your SRNE inverter device
- `battery_soc_sensor` - Battery State of Charge
- `priority_select` - Energy priority mode control

### Blueprint-Specific Requirements

| Blueprint | Additional Required Entities |
|-----------|------------------------------|
| **Dynamic Current Limiter** | `pv_power_sensor`, `load_power_sensor`, `charge_current_number`, `battery_voltage_sensor` |
| **EV Charging Optimizer** | `ev_charger_switch`, `pv_power_sensor`, `load_power_sensor`, `grid_power_sensor` |
| **Time of Use Scheduler** | None (uses priority_select only) |
| **Solar Export Optimizer** | `grid_power_sensor`, `pv_power_sensor`, `priority_1_device` (switch) |
| **Equalizing Charge** | `equalization_enable_switch`, `battery_voltage_sensor`, `battery_temp_sensor` |
| **Thermal Stress** | `temperature_sensor`, `charge_current_number` |
| **Generator Auto-Start** | `grid_status_sensor` (binary), `generator_start_relay` (switch) |
| **UFLS** | `grid_frequency_sensor`, `load_power_sensor`, `priority_1_load` (switch) |
| **Soft Start Recovery** | `fault_sensor` (binary), `ac_output_switch`, `charge_current_number`, `battery_voltage_sensor` |
| **Fault Monitor** | `fault_sensor` (binary) |
| **Battery Health** | `battery_voltage_sensor`, `battery_current_sensor`, `battery_temp_sensor` |

---

## Typical Configurations

### 🏠 Basic Home Setup
Minimum recommended blueprints:
1. **Time of Use Scheduler** - Optimize for electricity rates
2. **Fault Monitor Alert** - Safety and auto-recovery
3. **Solar Export Optimizer** - Maximize solar usage

**Configuration time**: ~30 minutes

---

### 🔋 Off-Grid System
Essential blueprints:
1. **Generator Auto-Start** - Backup power management
2. **Thermal Stress Protector** - Equipment protection
3. **Under-Frequency Load Shed** - System stability
4. **Soft Start Recovery** - Safe restarts
5. **Battery Health Tracker** - Long-term monitoring

**Configuration time**: ~1 hour

---

### 🚗 EV Owner Setup
Recommended blueprints:
1. **EV Charging Optimizer** - Smart EV charging
2. **Time of Use Scheduler** - Rate optimization
3. **Solar Export Optimizer** - Use excess solar
4. **Dynamic Current Limiter** - Manage total load

**Configuration time**: ~45 minutes

---

### ⚡ Power User / Advanced
Full optimization suite:
- All 11 blueprints
- Custom thresholds tuned to your system
- Integration with energy dashboard
- Detailed logging and analytics

**Configuration time**: ~2-3 hours

---

## Quick Setup Guide

### Step 1: Choose Your Profile
Select one of the configurations above based on your needs.

### Step 2: Import Blueprints
```bash
# Option A: Git clone (if using git integration)
cd /config/blueprints/automation/
git pull

# Option B: Manual download
# Download YAML files and place in:
# /config/blueprints/automation/srne_inverter/[category]/
```

### Step 3: Create Automations
For each blueprint:
1. Configuration → Automations → Create Automation
2. "Start with a blueprint"
3. Select SRNE blueprint
4. Fill in required fields
5. Save with descriptive name

### Step 4: Test Mode
Enable notifications, disable actions for first 24 hours:
```yaml
# Set these in blueprint configuration:
notify_on_start: true
auto_restart_enabled: false  # For safety blueprints
enable_notifications: true
```

### Step 5: Gradual Activation
After 24-hour test period:
1. Review automation traces
2. Verify triggers are correct
3. Enable actions one blueprint at a time
4. Monitor for 48 hours each

---

## Common Thresholds

### Temperature Limits
- Normal: 45°C
- Level 1 derate: 50°C
- Level 2 derate: 60°C
- Level 3 derate: 70°C
- Critical shutdown: 75°C

### Battery SOC
- Critical low: 10-15%
- Reserve minimum: 20%
- Charge target: 80-90%
- Full: 95-100%

### Power Thresholds
- Solar surplus minimum: 200-500W
- Export optimization: 2000W
- Grid draw limit: 3000-5000W

### Time Delays
- Start hysteresis: 5 minutes
- Stop hysteresis: 2 minutes
- Recovery delay: 30 seconds
- Transition delay: 5 minutes

---

## Notification Setup

### Recommended Services
1. **Primary**: Mobile app (immediate)
2. **Secondary**: Persistent notification (backup)
3. **Critical**: Email (for serious faults)

### Example Configuration
```yaml
notification_service_1: notify.mobile_app_iphone
notification_service_2: notify.persistent_notification
notification_service_3: notify.email  # Critical only
```

### Notification Priority
- **High**: Safety issues, critical faults
- **Normal**: Mode changes, optimization triggers
- **Low**: Weekly reports, informational

---

## Automation Modes

### Single
- Use for: State-changing operations
- Examples: Fault response, mode switching
- Prevents: Overlapping execution

### Queued
- Use for: Sequential operations
- Examples: Load shedding, device control
- Max queue: 3-10 depending on complexity

### Parallel
- Use for: Independent monitoring
- Examples: Health checks, logging
- Caution: Resource usage

### Restart
- Use for: Time-based schedulers
- Examples: TOU scheduler
- Behavior: Cancels previous run

---

## Performance Tips

### Optimize Trigger Frequency
```yaml
# Good: Periodic + significant changes
trigger:
  - platform: time_pattern
    minutes: "/5"
  - platform: numeric_state
    entity_id: sensor.power
    above: 1000

# Avoid: High-frequency polling
trigger:
  - platform: time_pattern
    seconds: "/10"  # Too frequent!
```

### Use Hysteresis
Prevent automation flapping:
```yaml
trigger:
  - platform: numeric_state
    entity_id: sensor.temperature
    above: 50
    for:
      minutes: 5  # Wait 5 minutes before triggering
```

### Batch Notifications
Don't spam yourself:
```yaml
notification_repeat_interval: 30  # Re-notify every 30 min, not constantly
```

---

## Maintenance Schedule

### Daily
- Review automation traces for errors
- Check notification summary

### Weekly
- Review battery health report
- Check fault log (if any)
- Verify all automations running

### Monthly
- Adjust thresholds based on seasonal changes
- Review energy savings
- Update time windows for TOU

### Quarterly
- Full system health check
- Blueprint updates (check GitHub)
- Review and archive old logs

---

## Troubleshooting Checklist

### Automation Not Triggering
- [ ] Entity IDs correct?
- [ ] Entity state updating?
- [ ] Conditions being met?
- [ ] Mode set correctly?
- [ ] Check automation trace

### Actions Not Working
- [ ] Entity writable?
- [ ] Permissions correct?
- [ ] Integration responding?
- [ ] Check Home Assistant logs

### Unexpected Behavior
- [ ] Review all conditions
- [ ] Check for conflicting automations
- [ ] Verify threshold values
- [ ] Test manually first

### Poor Performance
- [ ] Reduce trigger frequency
- [ ] Optimize conditions
- [ ] Check system resources
- [ ] Review automation mode

---

## Safety Checklist

Before enabling production mode:

### Critical Safety Blueprints
- [ ] **Thermal Stress Protector**
  - Temperature thresholds verified
  - Emergency shutdown tested
  - Recovery process validated

- [ ] **Generator Auto-Start**
  - Start relay wiring verified
  - Fuel levels adequate
  - Manual override accessible

- [ ] **UFLS**
  - Load priorities correct
  - Critical loads protected
  - Frequency sensor accurate

### Optimization Blueprints
- [ ] **Dynamic Current Limiter**
  - Max current within specs
  - Voltage calculations verified
  - Battery type appropriate

- [ ] **EV Charging**
  - Grid limits safe
  - Battery reserve adequate
  - Charging window reasonable

### Monitoring Blueprints
- [ ] **Fault Monitor**
  - Critical codes identified
  - Restart attempts reasonable
  - Escalation contacts valid

- [ ] **Battery Health**
  - Capacity specs correct
  - Cycle life appropriate
  - EOL thresholds reasonable

---

## Support Resources

### Documentation
- Full blueprint documentation: `NEW_BLUEPRINTS.md`
- Integration docs: Main repository README
- Home Assistant automation docs: https://www.home-assistant.io/docs/automation/

### Community
- GitHub Issues: Report bugs and feature requests
- Home Assistant Community: General discussion
- SRNE User Forums: Hardware-specific questions

### Professional Support
For critical installations:
- Consult qualified electrician
- Contact SRNE technical support
- Professional Home Assistant installer

---

## Version Compatibility

| Blueprint Version | HA Version | Integration Version |
|-------------------|------------|---------------------|
| 1.0 | 2023.4+ | Any |
| Future | TBD | TBD |

**Note**: Always backup your configuration before updating!

---

*Last Updated: 2026-02-05*
*Blueprint Version: 1.0*
