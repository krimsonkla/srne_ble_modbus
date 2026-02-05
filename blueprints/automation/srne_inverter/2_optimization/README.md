# Optimization Blueprints

This directory contains automation blueprints focused on maximizing energy efficiency, reducing costs, and optimizing system performance.

## Purpose

Optimization blueprints intelligently manage energy flows to minimize electricity costs, maximize solar utilization, and improve overall system efficiency. These automations enhance your system's economic performance while respecting safety constraints.

## Available Blueprints

### 1. Peak Shaving (`peak_shaving.yaml`)

**Purpose:** Reduce grid power consumption during expensive peak rate periods

**What it does:**
- Monitors time-of-use periods
- Tracks grid power import levels
- Automatically switches to battery power during peak hours
- Protects battery by respecting minimum SOC thresholds

**When to use:**
- **Essential** if your utility has time-of-use (TOU) pricing
- Highly valuable for reducing electricity bills in areas with demand charges
- Useful for load balancing during high-usage periods

**Economic impact:**
- Can reduce electricity costs by 30-50% with TOU rates
- Typically pays for battery system faster through peak avoidance
- Reduces strain on grid during peak demand

**Key features:**
- Configurable peak hours (start/end times)
- Grid import threshold triggering
- Battery protection (won't discharge below minimum SOC)
- Hysteresis to prevent rapid mode switching
- Automatic restoration to normal mode after peak hours
- Optional notifications for mode changes

**Typical configuration:**
```yaml
Peak hours: 16:00 - 21:00 (adjust to your utility's schedule)
Grid import threshold: 1000W
Minimum battery SOC: 30%
Peak priority: "Battery First"
Off-peak priority: "Solar First"
```

**Best practices:**
- Align peak hours exactly with your utility's TOU schedule
- Set import threshold based on your typical usage patterns
- Reserve enough battery capacity for the full peak period
- Monitor battery SOC trends to optimize minimum threshold

---

### 2. Solar Optimization (`solar_optimization.yaml`)

**Purpose:** Maximize solar self-consumption and minimize grid export/import

**What it does:**
- Monitors solar production levels
- Tracks battery state of charge
- Intelligently routes solar power to maximize self-consumption
- Adjusts priority modes based on production and battery status

**When to use:**
- **Recommended** for all solar+storage installations
- Essential when grid export rates are low or zero
- Critical for maximizing solar ROI in areas with net metering caps
- Valuable for reducing grid dependency

**Economic impact:**
- Increases solar self-consumption from ~30% to 70-90%
- Maximizes value when export rates < import rates
- Reduces battery cycles by smarter charging strategies

**Key features:**
- Multi-level solar production tracking (low/medium/high)
- Intelligent battery charging during excess solar
- Dynamic priority switching based on conditions
- Morning startup optimization
- Evening transition to battery mode
- Load-aware solar routing

**Typical configuration:**
```yaml
High production threshold: 3000W (adjust to your array size)
Medium production threshold: 1500W
Minimum battery for export: 80% (protects battery first)
Solar priority: "Solar First" (use solar directly)
Low solar priority: "Battery First" (supplement from battery)
```

**Best practices:**
- Scale thresholds to your solar array size (typically 20-40% of peak)
- Consider seasonal variations in solar production
- Coordinate with peak shaving (solar optimization during day, peak shaving at night)
- Adjust battery charge thresholds based on usage patterns

---

## Optimization Strategy Guide

### Combining Optimization Blueprints

Both blueprints work together to create a comprehensive optimization strategy:

**Daily cycle example:**
```
06:00-10:00: Solar Optimization (morning production builds up)
10:00-16:00: Solar Optimization (peak production, charge battery)
16:00-21:00: Peak Shaving (use battery, avoid peak rates)
21:00-06:00: Normal mode (utility backup if needed)
```

### Energy Flow Priority

Understanding priority modes used by optimization:

1. **Solar First**: Use solar → then battery → then grid
   - Best for daytime with solar production
   - Maximizes self-consumption
   - Reduces battery wear

2. **Battery First**: Use battery → then solar → then grid
   - Best for peak shaving periods
   - Reduces grid import during expensive hours
   - Coordinates with solar when available

3. **Utility First**: Use grid → supplement with solar/battery
   - Safety fallback mode
   - Used when battery is low
   - Preserves backup power

### Performance Monitoring

Track these metrics to optimize your automations:

1. **Self-sufficiency rate**: (Solar + Battery) / Total Consumption
   - Target: 70-90% with good solar/battery sizing
   - Lower? Increase solar or battery capacity
   - Higher? System may be oversized

2. **Peak avoidance**: Grid import during peak hours
   - Target: < 10% of daily grid import during peak hours
   - Track monthly to verify peak shaving effectiveness

3. **Solar utilization**: Direct solar use + battery charging / Total solar production
   - Target: > 95% (minimize grid export)
   - Lower? Adjust battery charging thresholds

4. **Battery cycle efficiency**: Energy out / Energy in
   - Typical: 85-95% depending on battery chemistry
   - Track over time to monitor battery health

## Configuration Best Practices

### Initial Setup

1. **Start with conservative settings**
   - Higher minimum battery SOC (40-50%)
   - Wider peak hours (start earlier, end later)
   - Lower import thresholds

2. **Monitor for 1-2 weeks**
   - Track battery SOC patterns
   - Note when peak shaving triggers
   - Observe solar optimization behavior

3. **Tune progressively**
   - Adjust one parameter at a time
   - Wait several days to see impact
   - Document changes and results

### Seasonal Adjustments

**Summer (high solar):**
- Lower minimum battery SOC (30%)
- Earlier peak shaving start (more daylight to recharge)
- Higher solar production thresholds

**Winter (low solar):**
- Higher minimum battery SOC (40-50%)
- Later peak shaving start (less daylight to recharge)
- Lower solar production thresholds
- Consider shorter peak shaving window

### Advanced Optimization

For maximum efficiency, consider:

1. **Weather integration**: Adjust strategy based on forecast
2. **Load prediction**: Use historical data to predict evening consumption
3. **Battery aging**: Gradually reduce depth of discharge as battery ages
4. **Grid price API**: Dynamic optimization based on real-time pricing

## Safety Integration

Optimization blueprints always respect safety constraints:

- **Battery protection overrides optimization** - Safety comes first
- **Never discharge below minimum SOC** - Battery health is prioritized
- **Grid failure triggers safety mode** - Optimization pauses during emergencies
- **Temperature limits respected** - No optimization if battery is too hot/cold

## Economic Analysis

### Calculating ROI

Track your optimization savings:

```
Monthly savings =
  (Peak hours avoided kWh × peak rate) +
  (Increased solar self-consumption × import rate) -
  (Reduced efficiency from optimization × battery cost)

Typical results:
- Peak shaving: $20-100/month depending on rates and usage
- Solar optimization: $15-50/month from increased self-consumption
- Combined optimization: 15-30% reduction in electricity bills
```

### Payback Period Impact

Well-tuned optimization can reduce battery system payback period by:
- 20-40% in areas with significant TOU rate differences
- 30-50% in areas with high import rates and low export rates
- 10-20% in areas with flat rates (still valuable for grid independence)

## Troubleshooting

### Common Issues

**Peak shaving not activating:**
- Verify peak hours match utility schedule
- Check grid import sensor is working
- Ensure battery SOC is above minimum
- Review hysteresis duration setting

**Battery draining too fast during peak hours:**
- Increase minimum battery SOC
- Reduce peak shaving window
- Check for excessive loads during peak hours
- Verify solar optimization is charging battery during day

**Solar not being fully utilized:**
- Lower battery charge threshold
- Adjust production thresholds for your array size
- Check if grid export is unnecessarily enabled
- Verify solar priority mode is "Solar First"

**Frequent mode switching:**
- Increase hysteresis duration
- Widen production threshold bands
- Check for sensor noise or fluctuations
- Add delay to mode change triggers

## Related Documentation

- [Safety Blueprints](../1_safety/README.md) - Always prioritized over optimization
- [Monitoring Blueprints](../3_monitoring/README.md) - Track optimization performance
- [Main Blueprint Documentation](../README.md)
- [Energy Flow Diagrams](../../../../docs/energy-flows.md)

## Getting Help

For optimization questions:
1. Share your utility rate structure (TOU schedule, rates)
2. Provide system sizing (solar array, battery capacity)
3. Describe typical daily usage patterns
4. Include 1-2 weeks of energy data
5. Open a discussion on GitHub with "optimization" tag
