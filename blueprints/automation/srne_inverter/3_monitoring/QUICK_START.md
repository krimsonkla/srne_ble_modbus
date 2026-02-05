# Quick Start Guide - Advanced Monitoring Blueprints

Get started with the three advanced monitoring blueprints in minutes.

---

## 🚀 5-Minute Setup

### Step 1: Choose Your Blueprint

**For comprehensive daily reports:**
→ Use `daily_performance_dashboard.yaml`

**For automatic seasonal adjustments:**
→ Use `seasonal_parameter_adjuster.yaml`

**For weather-responsive operation:**
→ Use `weather_based_priority.yaml`

### Step 2: Import Blueprint

1. Go to **Settings** > **Automations & Scenes** > **Blueprints**
2. Click **Import Blueprint**
3. Enter the blueprint URL or select from local files
4. Click **Preview** then **Import**

### Step 3: Create Automation

1. Click **Create Automation** from the blueprint
2. Give it a name (e.g., "SRNE Daily Dashboard")
3. Fill in required sensors (see below)
4. Click **Save**

---

## 📋 Required Sensors

### Daily Performance Dashboard

**Minimum Required:**
```yaml
- sensor.srne_pv_energy_today
- sensor.srne_battery_charge_today
- sensor.srne_battery_discharge_today
- sensor.srne_battery_soc
```

**Recommended Add:**
```yaml
- sensor.grid_import_today
- sensor.grid_export_today
- sensor.load_consumption_today
```

### Seasonal Parameter Adjuster

**Minimum Required:**
```yaml
- SRNE Inverter Device (from dropdown)
- sensor.srne_battery_temperature (optional but recommended)
```

### Weather-Based Priority

**Minimum Required:**
```yaml
- SRNE Inverter Device
- select.srne_energy_priority
- sensor.openweathermap_cloud_coverage (or equivalent)
- sensor.srne_battery_soc
```

---

## 🎯 Recommended Starting Configurations

### Configuration 1: Start with Dashboard Only

**Best for:** First-time users who want to understand their system

```yaml
Blueprint: daily_performance_dashboard.yaml
Settings:
  - notification_style: "summary"
  - calculation_method: "simple"
  - report_time: "23:00:00"
  - include_comparisons: false
  - include_cost_analysis: false
```

**Why:** Simple setup, easy to understand, no advanced features to configure.

**Next step:** After 1 week, enable comparisons and switch to "weighted" calculation.

---

### Configuration 2: Add Seasonal Adjustment

**Best for:** Users with temperature extremes (hot summers or cold winters)

```yaml
Blueprint: seasonal_parameter_adjuster.yaml
Settings:
  - Define your winter months
  - Set conservative winter voltages (54-55V)
  - Set optimal summer voltages (56-57V)
  - Enable temperature overrides
  - Check every 6 hours
```

**Why:** Protects battery from temperature damage, extends battery life.

**Monitor:** Watch for notifications on mode changes, verify voltages are being set.

---

### Configuration 3: Add Weather Automation

**Best for:** Users wanting to maximize self-sufficiency

```yaml
Blueprint: weather_based_priority.yaml
Settings:
  - Connect cloud coverage sensor
  - Use default priority mappings
  - Set confidence threshold to 70%
  - Check every 15 minutes
  - Enable sunrise/sunset checks
```

**Why:** Automatically adjusts to weather, reduces grid usage, maximizes solar.

**Monitor:** First few days, watch priority changes and adjust thresholds if needed.

---

## ⚙️ Essential Configuration Tips

### Tip 1: Start Conservative

Begin with:
- Higher confidence thresholds (75-80%)
- Longer check intervals (30-60 min)
- Simple calculation methods
- Fewer optional features

**Rationale:** Learn how your system behaves before optimizing.

### Tip 2: Enable Notifications

Always enable notifications during initial setup:
```yaml
notification_service: notify.mobile_app_YOUR_DEVICE
notify_on_mode_change: true
include_reasoning: true
```

**Rationale:** Understand what the automation is doing and why.

### Tip 3: Use Persistent Notifications

For the first week:
```yaml
create_persistent_notification: true
```

**Rationale:** Easy to review automation history without checking logs.

### Tip 4: Test in Developer Tools

Before enabling automation, test your sensors:

**Developer Tools > Template:**
```yaml
PV Today: {{ states('sensor.srne_pv_energy_today') }}
Battery SOC: {{ states('sensor.srne_battery_soc') }}
Cloud Coverage: {{ states('sensor.openweathermap_cloud_coverage') }}
```

**Rationale:** Verify sensors are working and providing sensible values.

---

## 🔍 Verification Checklist

After setup, verify:

### Dashboard Blueprint
- [ ] Report generated at scheduled time
- [ ] All values look reasonable (no 0s or errors)
- [ ] Notification received
- [ ] Self-sufficiency calculation makes sense

### Seasonal Blueprint
- [ ] Correct season detected
- [ ] Voltages set appropriately
- [ ] Temperature override working (test in extreme weather)
- [ ] Mode change notification received

### Weather Blueprint
- [ ] Priority changes based on cloud coverage
- [ ] Changes don't happen too frequently
- [ ] Battery level considered in decisions
- [ ] Night mode activates after sunset

---

## 🐛 Common Issues & Quick Fixes

### Issue: "Entity not found" error

**Quick Fix:**
1. Check entity ID in **Developer Tools > States**
2. Update blueprint configuration with correct ID
3. Restart automation

### Issue: Dashboard shows all zeros

**Quick Fix:**
1. Verify sensors update at midnight
2. Check sensor device class is "energy"
3. Try "metrics" notification style to see raw values

### Issue: Seasonal adjustment not changing parameters

**Quick Fix:**
1. Verify inverter has writable parameters
2. Check entity IDs in device entities list
3. Enable manual override temporarily to test

### Issue: Weather priority changes too often

**Quick Fix:**
```yaml
confidence_threshold: 80  # Increase from 70
minimum_change_interval: 45  # Increase from 30
hysteresis_margin: 15  # Increase from 10
```

### Issue: No notifications received

**Quick Fix:**
1. Test notification service in Developer Tools
2. Verify service name is correct (case-sensitive)
3. Check mobile app integration is working
4. Enable persistent notifications as backup

---

## 📱 Mobile App Notification Setup

### iOS (Home Assistant Companion)

1. Install Home Assistant Companion app
2. Log in to your instance
3. Go to **App Configuration > Notifications**
4. Enable notifications
5. Note your device name (e.g., "iphone")

**Use in blueprints:**
```yaml
notification_service: notify.mobile_app_iphone
```

### Android (Home Assistant Companion)

1. Install Home Assistant Companion app
2. Log in to your instance
3. Grant notification permissions
4. Note device name in app settings

**Use in blueprints:**
```yaml
notification_service: notify.mobile_app_pixel
```

### Multiple Devices

Create separate automation instances:
```yaml
# Instance 1: Primary phone (detailed)
notification_service: notify.mobile_app_iphone
notification_style: "detailed"

# Instance 2: Secondary device (summary)
secondary_notification_service: notify.mobile_app_ipad
```

---

## 🎓 Learning Path

### Week 1: Observation
- Enable Daily Dashboard only
- Review reports daily
- Understand your energy patterns
- Don't change any settings

### Week 2: Optimization
- Add Seasonal Adjuster if needed
- Enable cost analysis in Dashboard
- Start tracking savings
- Fine-tune calculation method

### Week 3: Automation
- Add Weather-Based Priority
- Monitor priority changes
- Adjust thresholds if needed
- Enable all optional features

### Week 4: Refinement
- Review 3 weeks of data
- Adjust thresholds for your patterns
- Enable advanced features
- Share learnings with community

---

## 💡 Pro Tips

### Tip: Use Notification Groups

Create a notification group for all SRNE alerts:

```yaml
# configuration.yaml
notify:
  - name: srne_alerts
    platform: group
    services:
      - service: mobile_app_iphone
      - service: mobile_app_ipad
      - service: persistent_notification
```

**Then use:**
```yaml
notification_service: notify.srne_alerts
```

### Tip: Create Helper Entities

For dynamic rate adjustment:

```yaml
# configuration.yaml
input_number:
  electricity_buy_rate:
    name: "Current Electricity Rate"
    min: 0
    max: 1
    step: 0.01
    unit_of_measurement: "$/kWh"
```

**Then reference in Dashboard:**
```yaml
electricity_buy_rate: "{{ states('input_number.electricity_buy_rate') | float }}"
```

### Tip: Schedule Different Report Times

Create multiple dashboard instances:
- Morning report (07:00) - Yesterday's summary
- Evening report (23:00) - Full detailed analysis
- Weekly report (Sunday 20:00) - 7-day summary

### Tip: Use Tags for Organization

In automation config:
```yaml
tags:
  - srne
  - monitoring
  - energy
  - automated
```

Easy to filter in automation list.

---

## 📚 Next Steps

Once comfortable with basics:

1. **Read full documentation:**
   - `ADVANCED_BLUEPRINTS.md` - Detailed feature explanations
   - `USAGE_EXAMPLES.yaml` - Copy-paste configurations
   - `README.md` - Original monitoring guide

2. **Explore advanced features:**
   - Historical comparisons
   - Multiple calculation methods
   - Cost optimization
   - Battery health tracking

3. **Join the community:**
   - Share your configuration
   - Report bugs or improvements
   - Help other users
   - Request new features

4. **Integrate with other systems:**
   - Grafana dashboards
   - Energy tracking spreadsheets
   - Home automation scenes
   - Voice assistants

---

## 🆘 Getting Help

### Before Asking for Help

1. Check automation is enabled
2. Verify sensors have valid values
3. Check Home Assistant logs
4. Review notification settings
5. Try the troubleshooting section

### When Reporting Issues

Include:
- Blueprint name and version
- Home Assistant version
- Inverter model
- Complete error message
- Relevant sensor values
- Automation YAML (sanitized)

### Where to Get Help

1. **GitHub Issues:** Bug reports and feature requests
2. **Home Assistant Community:** General discussions
3. **Discord/Reddit:** Real-time help
4. **Documentation:** This file and related docs

---

## ✅ Success Indicators

You'll know it's working when:

### Daily Dashboard
✅ Report arrives at scheduled time every day
✅ Values match your inverter display
✅ Self-sufficiency percentage is reasonable (50-90%)
✅ Cost savings calculated correctly

### Seasonal Adjuster
✅ Mode changes twice per year (or when temperature extreme)
✅ Voltages adjust appropriately
✅ Battery temperature stays in safe range
✅ No manual intervention needed

### Weather Priority
✅ Priority matches current weather conditions
✅ Changes happen smoothly (not constantly)
✅ Battery preserved during poor weather
✅ Solar maximized during good weather

---

## 🎉 You're Ready!

With these quick start steps, you should be up and running in minutes.

**Remember:**
- Start simple
- Monitor initially
- Adjust gradually
- Share your success

**Happy monitoring!** 🌞🔋⚡

---

For detailed documentation, see:
- **ADVANCED_BLUEPRINTS.md** - Complete feature reference
- **USAGE_EXAMPLES.yaml** - Configuration templates
- **README.md** - Original monitoring guide
