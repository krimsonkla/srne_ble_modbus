# Quick Start Guide - SRNE BLE Modbus

Get your SRNE inverter connected to Home Assistant in under 10 minutes.

## ⚠️ DISCLAIMER

**USE AT YOUR OWN RISK**

This software interfaces directly with your SRNE inverter via BLE.
Improper configuration or use may:
- Damage your BLE device
- Damage your inverter
- Void your warranty
- Cause data loss
- Result in equipment malfunction

**ALWAYS:**
- Test in safe conditions first
- Keep battery manufacturer specifications handy
- Monitor system closely during initial setup
- Have manual override procedures ready
- Back up your configuration

The authors assume NO LIABILITY for any damage or loss.

---

## Prerequisites

Before starting, ensure you have:

- [ ] Home Assistant 2024.11 or later installed
- [ ] Bluetooth adapter with BLE support
- [ ] SRNE HF Series inverter with BLE enabled
- [ ] Inverter powered on and within 10 meters of HA server
- [ ] HACS installed (recommended) or manual installation capability

---

## Step 1: Install the Integration

### Option A: HACS (Recommended)

1. Open HACS in Home Assistant
2. Click the three dots (⋮) in the top right corner
3. Select "Custom repositories"
4. Add this repository:
   - **URL**: `https://github.com/krimsonkla/srne_ble_modbus`
   - **Category**: Integration
5. Click "Add"
6. Search for "SRNE BLE Modbus" in HACS
7. Click "Download"
8. Restart Home Assistant

### Option B: Manual Installation

1. Download the latest release from GitHub
2. Extract `custom_components/srne_inverter` to your HA config directory:
   ```
   /config/custom_components/srne_inverter/
   ```
3. Restart Home Assistant

---

## Step 2: Add the Integration

1. Go to **Settings** → **Devices & Services**
2. Click **+ Add Integration** (bottom right)
3. Search for "SRNE"
4. Select "SRNE BLE Modbus" from results

### Device Discovery

The integration will automatically scan for BLE devices:

- Look for devices starting with **E6** (e.g., E60000231107692658)
- Select your inverter from the list
- Click **Submit**

If no devices appear:
- Verify inverter is powered on
- Check Bluetooth is enabled in Home Assistant
- Move HA server closer to inverter
- Power cycle the inverter data logger

---

## Step 3: Initial Configuration

### Basic Setup (Recommended)

The integration will use default settings:
- **Update Interval**: 30 seconds
- **Register Scanning**: Automatic
- **Password**: None (configure if needed)

Click **Submit** to complete setup.

### Advanced Setup (Optional)

Configure password authentication if needed:

1. After initial setup, go to **Devices & Services**
2. Find "SRNE BLE Modbus" integration
3. Click **Configure**
4. Enter password (try these defaults):
   - **4321** - Menu/Setting Password (most common)
   - **0000** - Grid Parameter Password
   - **111111** - Software/App Password

---

## Step 4: Verify Installation

### Check Device

1. Go to **Settings** → **Devices & Services** → **SRNE BLE Modbus**
2. Click on your inverter device
3. Verify entities are populated:
   - Battery State of Charge (SOC)
   - Battery Voltage
   - Battery Current
   - Battery Temperature
   - PV Power
   - Grid Status

### Monitor Data Updates

1. Go to **Developer Tools** → **States**
2. Search for `srne_inverter`
3. Watch entities update every 30 seconds
4. Verify values match inverter LCD display

---

## Step 5: Essential Safety Setup

**CRITICAL: Install at least one safety automation before using writable controls.**

### Recommended First Automation

1. Go to **Settings** → **Automations & Scenes** → **Blueprints**
2. Click **Import Blueprint**
3. Enter URL:
   ```
   https://raw.githubusercontent.com/krimsonkla/srne_ble_modbus/main/blueprints/automation/srne_inverter/1_safety/progressive_battery_protection.yaml
   ```
4. Click **Preview** → **Import**
5. Create automation from blueprint:
   - **Name**: "Battery Protection"
   - **Critical SOC**: 20%
   - **Emergency SOC**: 10%
   - **Notification Service**: Select your notification service
6. Click **Save**

### Test Safety Automation

1. Monitor automation traces in **Settings** → **Automations & Scenes**
2. Verify automation triggers at configured thresholds
3. Adjust thresholds based on battery specifications

---

## Step 6: Explore Features

### Available Entities

**Sensors (Read-Only)**:
- Battery State of Charge (%)
- Battery Voltage (V)
- Battery Current (A)
- Battery Temperature (°C)
- PV Voltage (V)
- PV Current (A)
- PV Power (W)
- Grid Voltage (V)
- Grid Frequency (Hz)
- AC Output Load (W)

**Controls (Writable)**:
- Output Priority Mode (select)
- Charge Current Limit (number)
- Battery Type (select)
- Charging Enable/Disable (switch)

**Services**:
- `srne_inverter.force_refresh` - Force immediate update
- `srne_inverter.reset_statistics` - Reset diagnostic counters
- `srne_inverter.restart_inverter` - Restart inverter (requires confirmation)

### Energy Dashboard Integration

1. Go to **Settings** → **Dashboards** → **Energy**
2. Click **Add Consumption**
3. Select `sensor.srne_inverter_ac_output_load`
4. Configure solar production if available
5. View energy flow in dashboard

---

## Common Issues & Solutions

### BLE Connection Failed

**Symptoms**: Integration setup fails to discover devices

**Solutions**:
1. Verify inverter is powered on and within range
2. Check Home Assistant Bluetooth is enabled:
   - **Settings** → **System** → **Hardware**
   - Verify Bluetooth adapter is detected
3. Restart Bluetooth service:
   ```bash
   sudo systemctl restart bluetooth
   ```
4. Power cycle inverter data logger (BLE module)

### Permission Denied (0x0B)

**Symptoms**: Cannot write to registers, error "Permission denied"

**Solutions**:
1. Configure password in integration settings
2. Try common defaults in order:
   - 4321 (most common)
   - 0000
   - 111111
   - 1111
3. Check inverter manual for password
4. Contact SRNE support if unknown

### Slow or Missing Updates

**Symptoms**: Entities show "unavailable" or update slowly

**Solutions**:
1. Check BLE connection strength (move HA closer)
2. Verify no interference from other Bluetooth devices
3. Check Home Assistant system resources
4. Review logs for connection errors:
   - **Settings** → **System** → **Logs**
   - Search for "srne_inverter"

### Entity Not Available

**Symptoms**: Some entities missing or showing "unavailable"

**Solutions**:
1. Verify register is supported by your model
2. Check integration logs for read errors
3. Enable debug logging:
   ```yaml
   logger:
     logs:
       custom_components.srne_inverter: debug
   ```
4. Wait for automatic register rescanning (occurs periodically)

---

## Next Steps

### Recommended Actions

1. **Install Additional Safety Blueprints**:
   - Temperature Protection
   - Grid Failure Detection
   - Fault Response

2. **Set Up Optimization Automations**:
   - Peak Shaving (if on TOU rates)
   - Solar Optimization (if PV installed)
   - Smart Night Charging

3. **Configure Notifications**:
   - Battery low alerts
   - Fault notifications
   - Daily performance reports

4. **Customize Dashboard**:
   - Create inverter control panel
   - Add energy flow card
   - Set up trend graphs

### Learning Resources

- [Full Documentation Index](INDEX.md)
- [Automation Blueprints](../blueprints/automation/srne_inverter/README.md)
- [Troubleshooting Guide](TROUBLESHOOTING.md)
- [Services Reference](services.md)

---

## Safety Checklist

Before relying on automations for critical functions:

- [ ] Safety automations installed and tested
- [ ] Notification services configured and verified
- [ ] Battery specifications reviewed and applied
- [ ] Automation thresholds match battery manufacturer specs
- [ ] Manual override procedures documented
- [ ] System monitored for 24+ hours in safe conditions
- [ ] Backup power plan in place
- [ ] Emergency contact information accessible

---

## Getting Help

If you encounter issues:

1. Review this guide completely
2. Check [Troubleshooting Guide](TROUBLESHOOTING.md)
3. Search [GitHub Issues](https://github.com/krimsonkla/srne_ble_modbus/issues)
4. Create new issue with:
   - Home Assistant version
   - Integration version
   - Inverter model
   - Full error logs
   - Steps to reproduce

**Support is provided on a best-effort basis. No guarantees or warranties.**

---

**Last Updated**: 2026-02-05
