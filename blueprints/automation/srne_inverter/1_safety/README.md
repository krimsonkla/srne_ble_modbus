# Safety Blueprints

This directory contains critical safety automation blueprints that protect your inverter, battery, and connected systems from damage or unsafe conditions.

## Purpose

Safety blueprints monitor critical parameters and take immediate protective actions when dangerous conditions are detected. These automations should be considered **essential** for any SRNE inverter installation.

## Available Blueprints

### 1. Battery Protection (`battery_protection.yaml`)

**Purpose:** Comprehensive battery safety monitoring and protection

**What it monitors:**
- Battery State of Charge (SOC)
- Battery temperature
- Battery voltage (both over and under voltage)

**When to use:**
- **Always recommended** - This is the most critical safety blueprint
- Essential for protecting expensive battery investments
- Required for preventing battery damage from overheating or deep discharge

**Key features:**
- Automatic switching to safe mode when thresholds exceeded
- Multi-parameter monitoring (temperature, voltage, SOC)
- Optional automatic charging cutoff on high temperature
- Emergency notification system with redundancy support
- System logging for incident tracking

**Typical configuration:**
- Critical SOC: 10% (prevents deep discharge)
- Max temperature: 45°C (protects from thermal damage)
- Safe mode: Switches to "Utility First" to stop battery drain

---

### 2. Grid Failure Detection (`grid_failure_detection.yaml`)

**Purpose:** Detect grid outages and automatically switch to backup power mode

**What it monitors:**
- Grid voltage levels
- Grid frequency
- Grid power availability

**When to use:**
- **Highly recommended** for off-grid or backup power scenarios
- Critical for areas with unreliable grid power
- Essential for automatic failover systems

**Key features:**
- Intelligent grid failure detection with configurable thresholds
- Automatic mode switching during outages
- Battery preservation during extended outages
- Automatic restoration when grid returns
- Hysteresis to prevent mode switching on transient events

**Typical configuration:**
- Min grid voltage: 200V
- Max grid voltage: 260V
- Detection time: 30 seconds (prevents false triggers)

---

### 3. Fault Response (`fault_response.yaml`)

**Purpose:** Monitor and respond to inverter fault conditions

**What it monitors:**
- Inverter fault codes
- System error states
- Component failures

**When to use:**
- **Recommended** for proactive fault management
- Important for systems requiring high reliability
- Useful for remote installations where manual intervention is difficult

**Key features:**
- Automatic fault detection and categorization
- Intelligent response based on fault severity
- Emergency shutdown capability for critical faults
- Detailed fault logging and notification
- Automatic recovery attempts for transient faults

**Typical configuration:**
- Critical faults: Immediate shutdown and notification
- Warning faults: Notification only
- Auto-recovery: Enabled for transient issues

---

## Safety Best Practices

### Priority and Loading Order

1. **Battery Protection** - Load this first, it's your primary safety net
2. **Grid Failure Detection** - Essential for backup power systems
3. **Fault Response** - Handles system-level errors

### Configuration Tips

1. **Test in safe conditions first** - Verify notifications work before relying on them
2. **Use redundant notifications** - Configure multiple notification methods for critical alerts
3. **Set conservative thresholds** - It's better to trigger protection too early than too late
4. **Monitor the monitors** - Periodically verify your safety automations are active
5. **Document your settings** - Keep a record of threshold values and why you chose them

### Important Warnings

- **Never disable all safety automations** - At minimum, keep battery protection active
- **Check battery manufacturer specifications** - Use their recommended voltage and temperature ranges
- **Test grid failure detection** - Verify it works during a controlled test scenario
- **Battery protection takes precedence** - If multiple automations conflict, battery safety wins
- **Don't ignore repeated alerts** - Frequent protection triggers indicate a system issue

## Integration with Other Categories

Safety blueprints work alongside optimization and monitoring automations:

- **Override optimization** - Safety always takes precedence over efficiency
- **Generate alerts** - Feed into monitoring systems for trend analysis
- **Emergency mode** - Optimization automations should respect safety-triggered modes

## Maintenance

- **Review thresholds quarterly** - As batteries age, you may need to adjust protection levels
- **Check logs after events** - Review what triggered protection and if settings need adjustment
- **Update firmware** - Keep inverter firmware current for best fault detection
- **Test annually** - Verify safety automations trigger correctly in controlled scenarios

## Getting Help

If safety automations are frequently triggering:
1. Check battery health and age
2. Verify sensor calibration
3. Review inverter logs for underlying issues
4. Consider if environmental factors (temperature, ventilation) need improvement
5. Consult the main documentation or open an issue on GitHub

## Related Documentation

- [Main Blueprint Documentation](../README.md)
- [Optimization Blueprints](../2_optimization/README.md)
- [Monitoring Blueprints](../3_monitoring/README.md)
- [Integration Configuration Guide](../../../../docs/integration-setup.md)
