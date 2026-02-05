# SRNE Inverter - Advanced Monitoring Blueprints

This directory contains three advanced automation blueprints designed for power users who want to maximize the efficiency and performance of their SRNE inverter systems.

---

## 📊 Blueprint 1: Daily Performance Dashboard

**File:** `daily_performance_dashboard.yaml`

### Overview
An enhanced version of the basic daily energy report that provides comprehensive KPI tracking, cost analysis, battery health monitoring, and intelligent recommendations.

### Key Features

#### Comprehensive KPIs
- **Self-Sufficiency %** - How much of your load is covered by solar/battery
- **Grid Dependency %** - Percentage of energy from grid
- **System Efficiency %** - Overall energy conversion efficiency
- **Battery Efficiency** - Round-trip battery performance
- **Solar Utilization** - How much of your solar production is used vs exported

#### Multiple Calculation Methods
1. **Simple** - Basic ratio calculations (load / generation)
2. **Weighted** - Accounts for battery and inverter efficiency losses
3. **Normalized** - Adjusts for grid export and net consumption
4. **Conservative** - Uses pessimistic estimates for safety margin

#### Cost Analysis
- Grid import costs
- Export revenue (if applicable)
- Solar value (avoided costs)
- Battery value (avoided costs)
- Net daily cost/savings
- Configurable electricity rates

#### Battery Health Tracking
- Cycle counting (daily incremental + lifetime total)
- Round-trip efficiency monitoring
- Temperature impact analysis
- Health score calculation (0-100)
- Maintenance recommendations

#### Historical Comparisons
- Compare today vs yesterday
- Compare today vs 7-day average
- Trend indicators (↑↓)
- Performance anomaly detection

#### Notification Styles
1. **Detailed** - Full analysis with all metrics and recommendations
2. **Summary** - Key metrics and alerts only
3. **Compact** - One-line status update
4. **Metrics Only** - Raw numbers for logging/graphing
5. **Visual** - ASCII progress bars and gauges

### Configuration Example

```yaml
# Example automation configuration
automation:
  - alias: "Daily Performance Dashboard"
    use_blueprint:
      path: srne_inverter/3_monitoring/daily_performance_dashboard.yaml
      input:
        inverter_device: YOUR_DEVICE_ID
        pv_energy_today_sensor: sensor.srne_pv_energy_today
        battery_charge_today_sensor: sensor.srne_battery_charge_today
        battery_discharge_today_sensor: sensor.srne_battery_discharge_today
        grid_import_today_sensor: sensor.grid_import_today
        battery_soc_sensor: sensor.srne_battery_soc

        # Calculation method
        calculation_method: "weighted"
        battery_efficiency_factor: 0.90
        inverter_efficiency_factor: 0.95

        # Cost configuration
        electricity_buy_rate: 0.12
        electricity_sell_rate: 0.08
        currency_symbol: "$"

        # Notification preferences
        report_time: "23:00:00"
        notification_style: "detailed"
        notification_service: notify.mobile_app_iphone

        # Optional features
        include_comparisons: true
        include_battery_health: true
        include_cost_analysis: true
        include_recommendations: true
```

### Helper Sensors Required

To get historical comparisons, create these template sensors:

```yaml
# configuration.yaml or template.yaml
template:
  - sensor:
      - name: "PV Energy Yesterday"
        unit_of_measurement: "kWh"
        device_class: energy
        state: >
          {{ states('sensor.srne_pv_energy_today') | float(0) }}
        # Use history integration to get actual yesterday value

      - name: "PV Energy 7-Day Average"
        unit_of_measurement: "kWh"
        device_class: energy
        state: >
          {% set history = states.sensor.srne_pv_energy_today.history(days=7) %}
          {% set values = history | map(attribute='state') | map('float', 0) | list %}
          {{ (values | sum / values | length) | round(2) if values | length > 0 else 0 }}
```

### Alert Thresholds

The blueprint includes configurable alert thresholds:

- **Low Self-Sufficiency** (default 50%) - Warns when you're too grid-dependent
- **High Grid Dependency** (default 60%) - Alerts on excessive grid usage
- **Battery Cycle Warning** (default disabled) - Warns as battery approaches cycle limit

### Troubleshooting

#### Issue: Incorrect self-sufficiency calculation
**Solution:** Check your calculation method. Use "simple" to debug, then switch to "weighted" for accuracy.

```yaml
calculation_method: "simple"  # Start here to verify sensors
```

#### Issue: Cost savings showing as negative
**Solution:** Verify your electricity rates and check grid import/export sensors.

```yaml
# Enable metrics-only style to see raw values
notification_style: "metrics"
```

#### Issue: Missing historical comparisons
**Solution:** Ensure yesterday and 7-day average sensors exist and have data.

```yaml
include_comparisons: false  # Disable until sensors are ready
```

#### Issue: Battery health score always 100
**Solution:** Provide battery temperature and cycles sensors for accurate health scoring.

---

## 🌡️ Blueprint 2: Seasonal Parameter Adjuster

**File:** `seasonal_parameter_adjuster.yaml`

### Overview
Automatically adjusts inverter charging parameters based on seasonal conditions to optimize battery performance and longevity across different climate conditions.

### Key Features

#### Automatic Season Detection
- Configurable winter period (default: Nov 1 - Apr 30)
- Summer mode for remaining months
- Handles year boundary crossing (Nov-Apr)
- Optional transition periods for gradual adjustment

#### Winter Mode (Conservative)
- **Lower charge voltages** - Protects battery in cold
- **Reduced charge currents** - Prevents damage
- **Low temperature cutoff** - Stops charging below threshold
- **Limited discharge** - Preserves battery capacity
- **Conservative float voltage** - Longer battery life

#### Summer Mode (Optimal)
- **Higher charge voltages** - Faster charging
- **Increased charge currents** - Maximize solar utilization
- **High temperature protection** - Prevents overheating
- **Full discharge capability** - Use full battery capacity
- **Optimized float voltage** - Balanced performance

#### Temperature-Based Overrides
- **Extreme cold protection** - Force winter mode if too cold
- **Heat protection mode** - Reduce charging if too hot
- **Real-time monitoring** - Uses battery/ambient temperature
- **Safety thresholds** - Configurable temperature limits

#### Transition Support
- Gradual parameter changes over configurable period
- Prevents sudden system behavior changes
- Smooth voltage and current ramping
- Optional feature (default: off)

### Configuration Example

```yaml
automation:
  - alias: "Seasonal Parameter Adjustment"
    use_blueprint:
      path: srne_inverter/3_monitoring/seasonal_parameter_adjuster.yaml
      input:
        inverter_device: YOUR_DEVICE_ID
        battery_temperature_sensor: sensor.srne_battery_temperature

        # Season definition (Northern Hemisphere)
        winter_start_month: 11
        winter_start_day: 1
        winter_end_month: 4
        winter_end_day: 30

        # Winter parameters (conservative)
        winter_battery_charge_voltage: 55.0
        winter_battery_float_voltage: 54.0
        winter_max_charge_current: 40
        winter_max_discharge_current: 40
        winter_low_temp_cutoff: 0
        winter_energy_priority: "Solar First"

        # Summer parameters (optimal)
        summer_battery_charge_voltage: 56.0
        summer_battery_float_voltage: 54.5
        summer_max_charge_current: 60
        summer_max_discharge_current: 60
        summer_high_temp_cutoff: 40
        summer_energy_priority: "Solar First"

        # Temperature overrides
        enable_temp_override: true
        extreme_cold_threshold: -5
        extreme_heat_threshold: 45

        # Notification
        notification_service: notify.mobile_app_iphone
        notify_on_mode_change: true

        # Check frequency
        check_frequency_hours: 6
```

### Battery Type Considerations

#### Lithium (LiFePO4)
- **Winter:** 54-55V charge, 0°C minimum
- **Summer:** 56-57V charge, 40°C maximum
- **Most tolerant** of temperature variations

#### AGM/Flooded Lead-Acid
- **Winter:** 55-56V charge, 5°C minimum
- **Summer:** 57-58V charge, 35°C maximum
- **More sensitive** to temperature

### Southern Hemisphere Configuration

For Southern Hemisphere locations, adjust the season dates:

```yaml
# Winter: May 1 - October 31
winter_start_month: 5
winter_start_day: 1
winter_end_month: 10
winter_end_day: 31
```

### Manual Override

Create an input boolean to disable automatic adjustments:

```yaml
# configuration.yaml
input_boolean:
  srne_manual_override:
    name: "Manual Inverter Control"
    icon: mdi:lock
```

Then reference it in the blueprint:

```yaml
manual_override_switch: input_boolean.srne_manual_override
```

### Troubleshooting

#### Issue: Parameters not updating
**Solution:** Check that your inverter supports writable parameters and entities exist.

```bash
# Check available writable entities
ha core check_config
```

#### Issue: Temperature override not working
**Solution:** Verify temperature sensor is providing valid readings.

```yaml
# Test in Developer Tools > Template
{{ states('sensor.srne_battery_temperature') | float(20) }}
```

#### Issue: Wrong season detected
**Solution:** Verify date configuration matches your hemisphere and region.

```yaml
# Debug in Developer Tools > Template
Current date: {{ now().month }}-{{ now().day }}
Winter start: {{ winter_start_month }}-{{ winter_start_day }}
Winter end: {{ winter_end_month }}-{{ winter_end_day }}
```

#### Issue: Mode changes too frequently
**Solution:** Increase check frequency or add hysteresis.

```yaml
check_frequency_hours: 12  # Check less often
enable_temp_override: false  # Disable temporary overrides
```

---

## 🌤️ Blueprint 3: Weather-Based Priority Adjustment

**File:** `weather_based_priority.yaml`

### Overview
Intelligently adjusts energy priority based on weather forecasts and real-time conditions to maximize self-sufficiency and minimize costs by predicting solar production.

### Key Features

#### Multi-Source Weather Integration
- **Cloud Coverage** - Primary decision factor
- **Weather Conditions** - Rain, snow, storms, fog
- **Solar Radiation** - Real-time production potential
- **UV Index** - Additional solar indicator
- **Visibility** - Fog/haze detection
- **Precipitation** - Rain probability/amount
- **Solar Forecast** - Integration with Solcast/Forecast.Solar

#### Intelligent Priority Mapping

| Condition | Default Priority | Reasoning |
|-----------|-----------------|-----------|
| Clear Sky (<20% clouds) | Solar First | Maximize solar usage |
| Partly Cloudy (20-50%) | SBU | Balanced approach |
| Cloudy (50-80%) | Battery First | Preserve battery for peak |
| Overcast (>80%) | Utility First | Limited solar expected |
| Rainy/Stormy | Utility First | Safety + preservation |
| Night | Utility First | No solar production |

#### Time-of-Day Awareness
- **Morning (6am-10am)** - Ramp up solar priority
- **Peak Solar (10am-3pm)** - Maximize solar utilization
- **Evening (3pm-7pm)** - Transition to battery
- **Night (7pm-6am)** - Grid priority

#### Confidence-Based Switching
- Prevents rapid priority changes
- Requires minimum confidence threshold (default 70%)
- Hysteresis margin prevents bouncing
- Minimum interval between changes (default 30 min)

#### Battery-Aware Logic
- **Low battery (<20%)** - Force charging regardless of weather
- **High battery (>80%)** - Can use battery even in poor weather
- Considers SOC in all priority decisions

#### Storm Mode
- Automatic detection of severe weather
- Forces grid priority for safety
- Protects equipment from power surges
- Auto-recovery when conditions improve

### Configuration Example

```yaml
automation:
  - alias: "Weather-Based Priority"
    use_blueprint:
      path: srne_inverter/3_monitoring/weather_based_priority.yaml
      input:
        inverter_device: YOUR_DEVICE_ID
        energy_priority_entity: select.srne_energy_priority

        # Weather sensors
        cloud_coverage_sensor: sensor.openweathermap_cloud_coverage
        weather_condition_sensor: weather.home
        solar_radiation_sensor: sensor.solar_radiation
        uv_index_sensor: sensor.openweathermap_uv_index

        # Priority mappings (customize for your needs)
        clear_sky_priority: "Solar First"
        partly_cloudy_priority: "SBU (Solar-Battery-Utility)"
        cloudy_priority: "Battery First"
        overcast_priority: "Utility First"
        rainy_priority: "Utility First"
        night_priority: "Utility First"

        # Cloud coverage thresholds (adjust for your climate)
        clear_sky_threshold: 20
        partly_cloudy_threshold: 50
        cloudy_threshold: 80

        # Stability settings
        confidence_threshold: 70
        minimum_change_interval: 30
        hysteresis_margin: 10

        # Time-based logic
        enable_time_based_logic: true
        morning_start_time: "06:00:00"
        peak_solar_start_time: "10:00:00"
        peak_solar_end_time: "15:00:00"
        evening_end_time: "19:00:00"

        # Battery considerations
        battery_soc_sensor: sensor.srne_battery_soc
        low_battery_threshold: 20
        high_battery_threshold: 80

        # Storm protection
        enable_storm_mode: true

        # Notifications
        notification_service: notify.mobile_app_iphone
        notify_on_priority_change: true
        include_reasoning: true

        # Execution
        check_frequency: 15
        enable_at_sunrise: true
        enable_at_sunset: true
```

### Weather Integration Setup

#### OpenWeatherMap (Recommended)

```yaml
# configuration.yaml
weather:
  - platform: openweathermap
    api_key: YOUR_API_KEY
    mode: onecall

sensor:
  - platform: openweathermap
    api_key: YOUR_API_KEY
    monitored_conditions:
      - cloud_coverage
      - uv_index
      - weather
```

#### Met.no (Free, No API Key)

```yaml
# configuration.yaml
weather:
  - platform: met
    name: Home

# Template sensor for cloud coverage
template:
  - sensor:
      - name: "Cloud Coverage"
        unit_of_measurement: "%"
        state: >
          {% set condition = states('weather.home') %}
          {% if condition in ['clear-night', 'sunny'] %}
            0
          {% elif condition in ['partlycloudy'] %}
            50
          {% elif condition in ['cloudy'] %}
            80
          {% elif condition in ['overcast', 'fog'] %}
            100
          {% else %}
            50
          {% endif %}
```

#### Solar Forecast Integration

Using Forecast.Solar (free):

```yaml
# configuration.yaml
sensor:
  - platform: forecast_solar
    api_key: YOUR_API_KEY  # Optional for free tier
    monitored_conditions:
      - energy_production_today
      - power_production_now
```

Using Solcast (more accurate, requires account):

```yaml
# Install via HACS
# Search for "Solcast Solar"
# Configure in UI with your Solcast API key
```

### Advanced Tuning

#### For Coastal/Variable Weather

```yaml
# More conservative thresholds
clear_sky_threshold: 15  # Tighter clear definition
confidence_threshold: 80  # Higher confidence required
minimum_change_interval: 45  # Less frequent changes
hysteresis_margin: 15  # More stability
```

#### For Stable/Predictable Climate

```yaml
# More aggressive switching
clear_sky_threshold: 30  # Broader clear definition
confidence_threshold: 60  # Lower confidence required
minimum_change_interval: 15  # More frequent changes
hysteresis_margin: 5  # More responsive
```

#### For Time-of-Use (TOU) Rates

```yaml
# Adjust priorities to use grid during off-peak
night_priority: "Utility First"  # Charge battery from grid
partly_cloudy_priority: "Battery First"  # Use battery during peak
```

### Troubleshooting

#### Issue: Priority changes too frequently
**Solution:** Increase confidence threshold and minimum interval.

```yaml
confidence_threshold: 85
minimum_change_interval: 60
hysteresis_margin: 15
```

#### Issue: Priority doesn't change in cloudy weather
**Solution:** Check cloud coverage sensor and thresholds.

```yaml
# Debug in Developer Tools > Template
Cloud Coverage: {{ states('sensor.openweathermap_cloud_coverage') }}
Is Cloudy: {{ states('sensor.openweathermap_cloud_coverage') | float > 50 }}
```

#### Issue: Storm mode not activating
**Solution:** Verify weather condition sensor format.

```yaml
# Check weather condition format
Current condition: {{ states('weather.home') }}
Lowercase: {{ states('weather.home') | lower }}
```

#### Issue: Solar forecast not working
**Solution:** Enable solar forecast feature and verify sensor.

```yaml
use_solar_forecast: true
solar_forecast_sensor: sensor.solcast_forecast_today
```

#### Issue: Night priority not applying
**Solution:** Adjust time-based logic settings for your location.

```yaml
evening_end_time: "18:00:00"  # Earlier sunset in winter
morning_start_time: "07:00:00"  # Later sunrise in winter
```

---

## 🛠️ General Troubleshooting

### Blueprint Not Appearing in UI

1. **Check file location**: Blueprints must be in `config/blueprints/automation/`
2. **Restart Home Assistant**: After adding new blueprints
3. **Check YAML syntax**: Use YAML validator
4. **Check logs**: Look for blueprint loading errors

```bash
# In Home Assistant container/system
tail -f /config/home-assistant.log | grep -i blueprint
```

### Automation Not Triggering

1. **Check automation is enabled**: Settings > Automations & Scenes
2. **Verify triggers**: Look at "Last Triggered" timestamp
3. **Check conditions**: Use Developer Tools > Template to test
4. **Enable debug logging**:

```yaml
# configuration.yaml
logger:
  default: warning
  logs:
    homeassistant.components.automation: debug
```

### Entity Not Found Errors

1. **Check entity IDs**: Developer Tools > States
2. **Device vs Entity**: Some inputs need device ID, others entity ID
3. **Integration loaded**: Ensure SRNE BLE Modbus integration is working
4. **Restart required**: After sensor configuration changes

### Performance Issues

If automations are causing lag:

1. **Reduce check frequency**:
```yaml
check_frequency: 30  # Instead of 15
check_frequency_hours: 12  # Instead of 6
```

2. **Disable optional features**:
```yaml
include_comparisons: false
include_recommendations: false
use_solar_forecast: false
```

3. **Use compact notifications**:
```yaml
notification_style: "compact"
```

---

## 📋 Best Practices

### 1. Start Simple
- Begin with one blueprint
- Use default settings first
- Gradually customize based on your system

### 2. Monitor Initially
- Watch first few days of operation
- Check notifications for unexpected behavior
- Adjust thresholds based on observations

### 3. Document Your Settings
- Keep notes on what works for your system
- Track seasonal performance differences
- Share learnings with community

### 4. Use Persistent Notifications
- Enable persistent notifications during testing
- Provides detailed logs of changes
- Easy to review decision history

### 5. Backup Your Configuration
- Before major changes
- Export automation YAML
- Save working configurations

---

## 🤝 Contributing

Found a bug or have an enhancement idea?

1. **Check existing issues**: GitHub Issues
2. **Provide details**:
   - Blueprint name and version
   - Home Assistant version
   - Inverter model
   - Error messages/logs
   - Configuration (sanitized)

3. **Share improvements**:
   - Fork the repository
   - Make your changes
   - Submit pull request with description

---

## 📚 Additional Resources

### Home Assistant Documentation
- [Automations](https://www.home-assistant.io/docs/automation/)
- [Blueprints](https://www.home-assistant.io/docs/blueprint/)
- [Templates](https://www.home-assistant.io/docs/configuration/templating/)

### Community Forums
- [Home Assistant Community](https://community.home-assistant.io/)
- [SRNE Inverter Discussions](https://community.home-assistant.io/t/srne-inverter-integration/)

### Related Integrations
- [Solcast Solar](https://github.com/BJReplay/ha-solcast-solar)
- [Forecast.Solar](https://www.home-assistant.io/integrations/forecast_solar/)
- [OpenWeatherMap](https://www.home-assistant.io/integrations/openweathermap/)

---

## 📄 License

These blueprints are part of the srne_ble_modbus project.
See main repository LICENSE file for details.

---

## ✨ Credits

Developed for the SRNE Inverter Home Assistant Integration community.

Special thanks to all contributors and testers who helped refine these automations.
