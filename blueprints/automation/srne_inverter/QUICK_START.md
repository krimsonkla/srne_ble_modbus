# Quick Start Guide - Essential SRNE Blueprints

## 5-Minute Setup

### Step 1: Import Blueprints (2 minutes)

In Home Assistant:
1. Go to **Settings** → **Automations & Scenes** → **Blueprints**
2. Click **Import Blueprint**
3. Import each blueprint URL or upload the YAML files:

**Safety (Required)**:
- `1_safety/progressive_battery_protection.yaml`
- `1_safety/temperature_protection.yaml`
- `1_safety/grid_disconnection_handler.yaml`

**Optimization (Recommended)**:
- `2_optimization/smart_night_charging.yaml`
- `2_optimization/peak_shaving_optimizer.yaml`
- `2_optimization/solar_midday_boost.yaml`

### Step 2: Create Automations (3 minutes)

For each blueprint:
1. Click **Create Automation**
2. Select your SRNE Inverter device
3. Use these quick-start settings:

---

## 🛡️ Safety Automations

### Progressive Battery Protection
```yaml
Name: "Battery Protection - Progressive"
Device: [Your SRNE Inverter]
SOC Sensor: sensor.srne_battery_soc
Temp Sensor: sensor.srne_battery_temperature
Voltage Sensor: sensor.srne_battery_voltage

Quick Settings:
  Warning SOC: 30%
  Critical SOC: 20%
  Emergency SOC: 10%
  Charge Max Temp: 45°C
  Discharge Max Temp: 60°C
  Priority Select: select.srne_charge_source_priority
  Notification: notify.mobile_app_[your_phone]
```

### Temperature Protection
```yaml
Name: "Battery Temperature Guard"
Device: [Your SRNE Inverter]
Temp Sensor: sensor.srne_battery_temperature

Quick Settings:
  Charge Max: 45°C
  Discharge Max: 60°C
  Hysteresis: 5°C
  Recovery Delay: 30 seconds
  Priority Select: select.srne_charge_source_priority
  Notification: notify.mobile_app_[your_phone]
```

### Grid Disconnection Handler
```yaml
Name: "Grid Failure Protection"
Device: [Your SRNE Inverter]
Voltage Sensor: sensor.srne_grid_voltage
SOC Sensor: sensor.srne_battery_soc

Quick Settings:
  Warning Voltage: 150V
  Critical Voltage: 100V
  Restore Voltage: 200V
  Priority Select: select.srne_charge_source_priority
  Enable Progressive Shedding: Yes
  Enable Soft Start: Yes
  Notification: notify.mobile_app_[your_phone]
```

---

## ⚡ Optimization Automations

### Smart Night Charging
```yaml
Name: "Off-Peak Charging"
Device: [Your SRNE Inverter]
SOC Sensor: sensor.srne_battery_soc

Quick Settings:
  Off-Peak Start: 23:00 (11 PM)
  Off-Peak End: 07:00 (7 AM)
  Min SOC Threshold: 80%
  Target SOC: 100%
  AC Charge Current: 30A
  Charge Priority: select.srne_charge_source_priority
  Max Current: number.srne_max_ac_charge_current
```

### Peak Shaving Optimizer
```yaml
Name: "Peak Hour Management"
Device: [Your SRNE Inverter]
Grid Power: sensor.srne_grid_power
SOC Sensor: sensor.srne_battery_soc

Quick Settings:
  Peak Start: 16:00 (4 PM)
  Peak End: 21:00 (9 PM)
  Import Threshold: 1000W
  Min Battery SOC: 30%
  Priority Select: select.srne_charge_source_priority
  Notification: notify.mobile_app_[your_phone]
```

### Solar Midday Boost
```yaml
Name: "Solar Optimization"
Device: [Your SRNE Inverter]
PV Power: sensor.srne_pv_power
SOC Sensor: sensor.srne_battery_soc

Quick Settings:
  Boost Start: 10:00 (10 AM)
  Boost End: 15:00 (3 PM)
  Min PV Power: 500W
  Max SOC: 95%
  Priority Select: select.srne_charge_source_priority
  Disable AC Charging: Yes
```

---

## 🎯 Common Entity Mappings

### Required Sensors:
```yaml
Battery SOC: sensor.srne_battery_soc
Battery Temp: sensor.srne_battery_temperature
Battery Voltage: sensor.srne_battery_voltage
Grid Voltage: sensor.srne_grid_voltage
Grid Power: sensor.srne_grid_power
PV Power: sensor.srne_pv_power
```

### Control Entities:
```yaml
Priority Select: select.srne_charge_source_priority
Max AC Current: number.srne_max_ac_charge_current
Charging Switch: switch.srne_battery_charging
```

### Optional Entities:
```yaml
Grid Frequency: sensor.srne_grid_frequency
PV Balance: select.srne_pv_power_balance
Output Priority: select.srne_output_priority
Weather: weather.home
```

---

## ✅ Verification Checklist

After setup:

1. **Check Automations**:
   - [ ] All 6 automations created
   - [ ] No configuration errors
   - [ ] All entities resolved (no "unavailable")

2. **Test Notifications**:
   - [ ] Send test notification to verify service works
   - [ ] Check notification format on mobile device

3. **Monitor First 24 Hours**:
   - [ ] Check automation triggers in logbook
   - [ ] Verify no conflicts in logs
   - [ ] Confirm battery protection working

4. **Adjust Thresholds** (after 1 week):
   - [ ] Review actual SOC patterns
   - [ ] Adjust time windows for your usage
   - [ ] Fine-tune temperature limits

---

## 🚨 Safety First Checklist

Before enabling automations:

- [ ] Know your battery specifications (voltage, temperature limits)
- [ ] Understand your grid voltage range
- [ ] Test load switches manually
- [ ] Configure notification services
- [ ] Have backup plan for power failures
- [ ] Know how to disable automations in emergency

---

## 📞 Emergency Procedures

### If Something Goes Wrong:

1. **Disable All Automations**:
   ```
   Settings → Automations → Select All → Disable
   ```

2. **Manual Control**:
   - Use SRNE Inverter integration directly
   - Control priority manually: select.srne_charge_source_priority
   - Monitor battery SOC closely

3. **Check Logs**:
   ```
   Settings → System → Logs
   Filter: "srne" or "automation"
   ```

4. **Reset to Safe State**:
   - Priority: "Utility First" (grid charging)
   - AC Charge Current: 10A (safe minimum)
   - Disable load shedding switches

---

## 🔧 Troubleshooting Quick Fixes

### Issue: Automations not triggering
**Fix**: Check entity states in Developer Tools → States
```yaml
Look for: "unavailable" or "unknown"
Fix: Restart SRNE integration or check sensor mapping
```

### Issue: Too many notifications
**Fix**: Adjust notification settings in each automation
```yaml
Disable: "Notify on Activation"
Keep: "Notify on Critical Events"
```

### Issue: Load shedding too aggressive
**Fix**: Adjust SOC thresholds higher
```yaml
Change:
  Warning: 30% → 40%
  Critical: 20% → 30%
  Emergency: 10% → 20%
```

### Issue: Not charging at night
**Fix**: Check time zone and SOC threshold
```yaml
Verify:
  - Time zone: Settings → System → General
  - Min SOC Threshold: Must be below current SOC
  - AC Charge Current entity: Must be writable
```

---

## 📊 Expected First Week

### Day 1-2: Learning Phase
- Automations trigger frequently as they learn your patterns
- Multiple notifications (normal)
- Minor adjustments needed

### Day 3-5: Stabilization
- Fewer notifications
- Smoother operation
- Pattern established

### Day 6-7: Optimized
- Minimal intervention
- Predictable behavior
- Full automation achieved

---

## 🎓 Next Steps

After basic setup works:

1. **Fine-Tune Thresholds**:
   - Adjust based on actual usage patterns
   - Refine time windows for your location
   - Optimize battery SOC targets

2. **Add Optional Features**:
   - Weather integration for smart charging
   - Frequency sensor for grid support
   - Additional load switches for granular control

3. **Monitor Performance**:
   - Track electricity costs (before/after)
   - Monitor battery health metrics
   - Review automation efficiency

4. **Advanced Configuration**:
   - Configure load priority groups
   - Set up conditional notifications
   - Add seasonal adjustments

---

## 📖 Learn More

- **Detailed Guide**: See `ESSENTIAL_BLUEPRINTS.md`
- **Entity Reference**: See entity analysis documentation
- **Home Assistant**: https://www.home-assistant.io/docs/automation/

---

## 💡 Pro Tips

1. **Start with Safety**: Enable all 3 safety automations first, test for 24 hours
2. **Add Optimization Gradually**: Enable one optimization automation per day
3. **Watch Notifications**: First week will have many - this is normal
4. **Document Changes**: Keep notes on what thresholds work best
5. **Seasonal Adjust**: Review settings every 3 months
6. **Backup Config**: Export automation config regularly

---

**Ready to Start?**
1. Import the 6 blueprints
2. Create automations with quick-start settings above
3. Enable safety automations first
4. Monitor for 24 hours
5. Add optimization automations
6. Fine-tune based on your patterns

**Questions?** Review the detailed guide in `ESSENTIAL_BLUEPRINTS.md`

---

**Version**: 1.0
**Last Updated**: 2026-02-05
