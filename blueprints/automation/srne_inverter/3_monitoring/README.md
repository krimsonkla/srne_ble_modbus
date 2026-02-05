# Monitoring Blueprints

This directory contains automation blueprints focused on tracking system performance, generating reports, and providing insights into energy usage patterns.

## Purpose

Monitoring blueprints collect and present data about your solar, battery, and energy system performance. They help you understand system behavior, track savings, and identify optimization opportunities - without directly controlling the system.

## Available Blueprints

### 1. Daily Energy Report (`daily_energy_report.yaml`)

**Purpose:** Comprehensive daily summary of energy production, consumption, and system performance

**What it tracks:**
- Solar energy production
- Battery charge/discharge cycles
- Grid import/export
- Total load consumption
- Self-sufficiency percentage
- Battery health metrics
- System efficiency

**When to use:**
- **Recommended** for all users wanting visibility into system performance
- Essential for tracking ROI and savings
- Valuable for identifying trends and optimization opportunities
- Useful for monthly/annual energy reporting

**Key features:**
- Flexible reporting time (default: 23:00 nightly)
- Two report formats: detailed and summary
- Optional battery health metrics
- Persistent notification in Home Assistant UI
- Customizable notification services
- Automatic calculation of self-sufficiency and grid independence

**Report formats:**

**Detailed format** (best for daily review):
```
📊 Daily Energy Report - 2026-02-05

☀️ Solar Production:
└─ PV Energy: 18.5 kWh

🔋 Battery:
└─ Charged: 12.3 kWh
└─ Discharged: 10.8 kWh
└─ Current SOC: 85%
└─ Efficiency: 87.8%
└─ Cycles: 145

⚡ Consumption:
└─ Total Load: 22.4 kWh
└─ From Grid: 3.9 kWh
└─ From Solar/Battery: 18.5 kWh

📈 Self-Sufficiency: 82.6%
💰 Grid Independence: 82.6%
```

**Summary format** (best for mobile notifications):
```
📊 Daily Report 02/05

☀️ Solar: 18.5 kWh
🔋 Battery: 85% (↑12.3 ↓10.8 kWh)
⚡ Load: 22.4 kWh
📈 Self-Sufficiency: 82.6%
```

**Typical configuration:**
```yaml
Report time: 23:00 (end of day summary)
Format: detailed (for Home Assistant UI)
Include battery health: Yes
Persistent notification: Yes (keep in UI for reference)
Notification service: notify.mobile_app
```

**Best practices:**
- Use detailed format in Home Assistant, summary on mobile
- Enable persistent notifications to review trends
- Schedule just before midnight to capture full day
- Track reports over weeks to identify patterns
- Compare weekday vs weekend consumption

---

## Understanding Your Reports

### Key Metrics Explained

**Self-Sufficiency Percentage**
```
(Solar Energy + Battery Discharge) / Total Consumption × 100
```
- Measures how much of your consumption is met by your system
- Target: 70-90% with properly sized solar+battery
- Higher is better but diminishing returns above 90%
- Seasonal variation is normal

**Grid Independence**
```
(1 - Grid Import / Total Consumption) × 100
```
- Similar to self-sufficiency but focuses on grid reliance
- Includes direct solar use and battery discharge
- 100% = fully off-grid
- 0% = fully dependent on grid

**Battery Efficiency**
```
Battery Discharge / Battery Charge × 100
```
- Measures round-trip battery efficiency
- Typical range: 85-95% depending on chemistry
- Lower values may indicate battery aging or high charge/discharge rates
- Excludes conversion losses (inverter, etc.)

**System Efficiency**
```
(Solar Used + Battery Discharge) / (Solar Production + Grid Import) × 100
```
- Overall system energy efficiency
- Accounts for all losses in the system
- Typical range: 80-90%
- Lower values suggest optimization opportunities

### Reading the Trends

**Healthy system indicators:**
- Self-sufficiency: Consistent within 10-20% day-to-day (weather-adjusted)
- Battery efficiency: Stable 85-95% range
- Grid import: Predictable patterns (higher at night, lower during day)
- Battery cycles: Gradual increase (0.5-1.5 cycles per day typical)

**Warning signs:**
- Self-sufficiency: Sudden drops (equipment issues or unusual consumption)
- Battery efficiency: Declining below 80% (battery aging or problems)
- Grid import: Unexplained increases (check for phantom loads)
- Battery cycles: Rapid increase (may indicate mode switching issues)

---

## Setting Up Monitoring

### Required Sensors

**Essential for basic reporting:**
- `sensor.pv_energy_today` - Solar production
- `sensor.battery_charge_today` - Energy into battery
- `sensor.battery_discharge_today` - Energy from battery
- `sensor.battery_soc` - Current battery level

**Optional but recommended:**
- `sensor.grid_import_today` - Grid usage tracking
- `sensor.load_consumption_today` - Total consumption
- `sensor.battery_cycles` - Battery health tracking

### Configuring Notifications

**Mobile app (recommended):**
```yaml
notification_service: notify.mobile_app_<device>
format: summary
persistent_notification: false
```

**Home Assistant UI:**
```yaml
notification_service: notify.persistent_notification
format: detailed
persistent_notification: true
```

**Multiple destinations:**
Create separate blueprint instances for different formats:
1. Instance 1: Mobile app with summary format
2. Instance 2: Persistent notification with detailed format
3. Instance 3: Email/Pushover with detailed format

### Advanced Monitoring

For deeper insights, consider adding:

1. **Weekly summaries**: Create additional blueprint instance running weekly
2. **Monthly reports**: Export to spreadsheet for long-term tracking
3. **Comparison tracking**: Save reports to a database for historical analysis
4. **Cost calculations**: Add utility rate to calculate actual savings
5. **Environmental impact**: Convert kWh to CO2 savings

---

## Integrating with Other Systems

### Data Export Options

**Home Assistant Recorder:**
- Reports automatically logged in Home Assistant database
- Query using SQL for custom analysis
- Access via Developer Tools → Statistics

**InfluxDB/Grafana:**
- Create custom dashboards with historical trends
- Set up alerting for unusual patterns
- Compare performance across time periods

**Google Sheets/Excel:**
- Manual export for monthly/annual reviews
- Create custom charts and projections
- Share with family or solar installer

**Energy Dashboard:**
- Use sensors in Home Assistant Energy Dashboard
- Visualize flows and patterns
- Track costs if utility integration available

---

## Monitoring Best Practices

### Daily Review (2 minutes)

Check your daily report for:
1. Self-sufficiency percentage (is it normal for weather?)
2. Grid import (any unexpected increases?)
3. Battery SOC (did it fully charge during day?)
4. Any anomalies or unusual patterns

### Weekly Analysis (10 minutes)

Review trends over the week:
1. Compare weekday vs weekend consumption
2. Check battery health metrics for changes
3. Identify peak consumption times
4. Calculate weekly self-sufficiency average

### Monthly Review (30 minutes)

Deep dive into the data:
1. Calculate actual electricity bill savings
2. Review optimization effectiveness
3. Check for seasonal adjustment needs
4. Identify any declining performance trends
5. Plan any system adjustments

### Annual Audit (1-2 hours)

Comprehensive system review:
1. Compare actual vs projected performance
2. Calculate ROI and payback timeline
3. Review battery degradation rate
4. Plan for system upgrades or changes
5. Update insurance and documentation

---

## Troubleshooting

### Missing Data in Reports

**Symptom:** Report shows zeros or N/A for values

**Causes:**
- Sensor not configured correctly
- Entity ID mismatch in blueprint
- Integration not providing daily totals
- Sensor reset before report time

**Solutions:**
1. Verify sensor entity IDs in blueprint configuration
2. Check sensors update correctly in Developer Tools
3. Ensure "today" sensors reset at midnight
4. Consider using utility meter helpers if sensors don't reset

### Inaccurate Calculations

**Symptom:** Self-sufficiency or other calculations seem wrong

**Causes:**
- Missing optional sensors (calculations use fallback)
- Sensor units incorrect (W vs kW)
- Time zones causing day boundary issues
- Grid import/export not properly separated

**Solutions:**
1. Configure all optional sensors for accurate calculations
2. Verify sensor units match blueprint expectations
3. Check Home Assistant time zone settings
4. Use separate sensors for grid import vs export

### Reports Not Sending

**Symptom:** Automation runs but no notification received

**Causes:**
- Notification service not configured
- Service name incorrect
- Mobile app not set up
- Persistent notification disabled

**Solutions:**
1. Test notification service in Developer Tools
2. Verify exact service name (case-sensitive)
3. Check mobile app integration is working
4. Enable persistent notifications for reliable delivery

---

## Future Monitoring Enhancements

Planned improvements for monitoring blueprints:

1. **Real-time alerts**: Notify on unusual consumption or production
2. **Predictive reports**: Estimate evening/next-day usage
3. **Cost tracking**: Direct integration with utility rates
4. **Comparison mode**: Compare to previous day/week/month
5. **Goal tracking**: Set targets and track progress
6. **Weather correlation**: Link performance to weather data

---

## Integration with Other Categories

Monitoring works alongside other blueprints:

**With Safety:**
- Track safety event frequency
- Monitor protection trigger patterns
- Identify recurring issues

**With Optimization:**
- Measure optimization effectiveness
- Calculate cost savings from peak shaving
- Track solar utilization improvements

**Standalone value:**
- Useful even without optimization/safety blueprints
- Provides system transparency
- Helps identify issues early

---

## Related Documentation

- [Safety Blueprints](../1_safety/README.md) - Monitor safety event frequency
- [Optimization Blueprints](../2_optimization/README.md) - Track optimization results
- [Main Blueprint Documentation](../README.md)
- [Home Assistant Energy Dashboard](https://www.home-assistant.io/docs/energy/)

## Getting Help

For monitoring questions:
1. Share example report output
2. Describe what seems wrong or unexpected
3. List which sensors you have configured
4. Include relevant automation YAML
5. Open issue on GitHub with "monitoring" tag
