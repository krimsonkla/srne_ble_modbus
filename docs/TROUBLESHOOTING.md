# Troubleshooting Guide - SRNE BLE Modbus

Complete troubleshooting guide for common issues and their solutions.

## ⚠️ DISCLAIMER

**USE AT YOUR OWN RISK**

This software interfaces directly with your SRNE inverter via BLE.
Improper configuration or use may result in equipment damage.
The authors assume NO LIABILITY for any damage or loss.

---

## Quick Diagnosis

### Symptom Checklist

Use this checklist to quickly identify your issue category:

- [ ] **Cannot find integration** → [Installation Issues](#installation-issues)
- [ ] **Cannot discover device** → [BLE Connection Issues](#ble-connection-issues)
- [ ] **Setup fails** → [Configuration Issues](#configuration-issues)
- [ ] **Entities unavailable** → [Entity Issues](#entity-issues)
- [ ] **Cannot write registers** → [Permission Issues](#permission-issues)
- [ ] **Slow updates** → [Performance Issues](#performance-issues)
- [ ] **Random disconnects** → [Connection Stability](#connection-stability)

---

## Installation Issues

### Integration Not Appearing in HACS

**Symptoms**:
- Cannot find "SRNE BLE Modbus" in HACS
- Search returns no results

**Solutions**:

1. **Verify custom repository added**:
   - HACS → Three dots → Custom repositories
   - URL: `https://github.com/krimsonkla/srne_ble_modbus`
   - Category: Integration
   - Click Add

2. **Clear HACS cache**:
   ```bash
   # SSH into Home Assistant
   rm -rf /config/.storage/hacs*
   # Restart Home Assistant
   ```

3. **Check HACS version**:
   - Requires HACS 1.32.0 or later
   - Update HACS if needed

4. **Manual installation fallback**:
   - Download latest release from GitHub
   - Extract to `/config/custom_components/srne_inverter/`
   - Restart Home Assistant

### Integration Not Loading

**Symptoms**:
- Integration installed but not available in UI
- Error in logs: "Setup failed"

**Solutions**:

1. **Check Home Assistant version**:
   - Requires HA 2024.11.0 or later
   - Update Home Assistant if needed

2. **Verify installation path**:
   ```
   /config/custom_components/srne_inverter/
   ├── __init__.py
   ├── manifest.json
   ├── config_flow.py
   └── ... (other files)
   ```

3. **Check logs for errors**:
   - Settings → System → Logs
   - Search for "srne_inverter"
   - Look for import errors or missing dependencies

4. **Verify Bluetooth support**:
   - Settings → System → Hardware
   - Confirm Bluetooth adapter detected
   - Install Bluetooth integration if missing

---

## BLE Connection Issues

### Cannot Discover Devices

**Symptoms**:
- Integration setup shows "No devices found"
- Scan completes but list is empty

**Solutions**:

1. **Verify inverter powered on**:
   - Check inverter LCD is active
   - Verify battery connected and charged
   - Ensure inverter not in standby mode

2. **Check Bluetooth range**:
   - Move Home Assistant server closer (< 10 meters)
   - Remove obstacles between server and inverter
   - Avoid metal enclosures/walls

3. **Verify Bluetooth enabled**:
   ```bash
   # SSH into Home Assistant
   bluetoothctl
   power on
   scan on
   # Look for device starting with "E6"
   ```

4. **Restart Bluetooth service**:
   ```bash
   sudo systemctl restart bluetooth
   ```

5. **Power cycle data logger**:
   - Some models: Press and hold button for 10 seconds
   - Others: Disconnect/reconnect inverter power
   - Wait 30 seconds before scanning

6. **Check for interference**:
   - Disable other Bluetooth devices temporarily
   - Move away from WiFi routers (2.4GHz interference)
   - Test at different times of day

### Device Discovered But Connection Fails

**Symptoms**:
- Device appears in scan
- Setup fails with "Connection timeout"

**Solutions**:

1. **Verify device not paired elsewhere**:
   - Close SRNE mobile app
   - Disconnect other Bluetooth clients
   - Only one connection supported at a time

2. **Increase connection timeout**:
   - Default: 10 seconds
   - Some systems need 15-20 seconds
   - Edit integration configuration

3. **Check system resources**:
   ```bash
   # Monitor system during connection
   htop
   # Look for CPU/memory constraints
   ```

4. **Try manual MAC address**:
   - Note device MAC from scan
   - Enter directly in setup
   - Skip auto-discovery

5. **Bluetooth adapter issues**:
   - Test with different USB port
   - Update Bluetooth firmware
   - Try external USB Bluetooth adapter

---

## Configuration Issues

### Setup Wizard Fails

**Symptoms**:
- Setup completes but entities not created
- Error: "Failed to set up integration"

**Solutions**:

1. **Check integration logs**:
   ```yaml
   logger:
     logs:
       custom_components.srne_inverter: debug
   ```

2. **Verify inverter model supported**:
   - SRNE HF Series: Supported
   - Other models: May not work
   - Check device name starts with "E6"

3. **Register discovery timeout**:
   - Initial setup scans 100+ registers
   - Can take 2-3 minutes
   - Wait for completion, do not cancel

4. **Configuration file corrupted**:
   ```bash
   # Remove integration
   # Delete config entry
   rm /config/.storage/core.config_entries
   # Restart and re-add
   ```

### Password Configuration Not Working

**Symptoms**:
- Entered password but writes still fail
- Error: "Permission denied (0x0B)"

**Solutions**:

1. **Try common passwords in order**:
   - 4321 (Menu/Setting - most common)
   - 0000 (Grid Parameters)
   - 111111 (Software Access)
   - 1111 (Alternative)

2. **Check password for your model**:
   - Refer to inverter manual
   - Contact SRNE support
   - Try dealer/installer password

3. **Password format**:
   - Enter as numeric only (no spaces)
   - Do not include leading zeros unless required
   - Example: "4321" not "04321"

4. **Re-authenticate after disconnect**:
   - Password valid for session only
   - Automatic re-auth on reconnect
   - Check logs for auth failures

---

## Entity Issues

### Entities Show "Unavailable"

**Symptoms**:
- Some or all entities show "unavailable"
- Entity was working previously

**Solutions**:

1. **Check BLE connection**:
   - Review connection status sensor
   - Look for disconnection events in logs
   - Verify device within range

2. **Register read failures**:
   - Some registers may not be supported
   - Check logs for "Illegal data address (0x02)"
   - Normal for unsupported registers

3. **Wait for next update cycle**:
   - Default: 30 seconds
   - Entity will recover automatically
   - Force refresh if needed:
     ```yaml
     service: srne_inverter.force_refresh
     ```

4. **Entity disabled**:
   - Settings → Devices → SRNE Inverter
   - Check entity not manually disabled
   - Enable if needed

### Missing Expected Entities

**Symptoms**:
- Some documented entities not appearing
- Feature seems unsupported

**Solutions**:

1. **Model-specific features**:
   - Check `MODEL_SPECIFIC_FEATURES.md`
   - Some features require grid-tie models
   - Enable feature flags if applicable

2. **Register scanning incomplete**:
   - Wait for initial discovery (2-3 minutes)
   - Check logs for scan completion
   - Manually trigger rescan if needed

3. **Feature flags disabled**:
   - Check `entities_pilot.yaml` configuration
   - Enable required features:
     ```yaml
     device:
       features:
         grid_tie: true  # If you have grid-tie model
     ```

4. **Entity hidden intentionally**:
   - Some entities disabled by default
   - Prevents clutter for unused features
   - Enable in device settings if needed

### Entity Values Incorrect

**Symptoms**:
- Entity shows wrong value
- Value doesn't match inverter LCD

**Solutions**:

1. **Check scaling factor**:
   - Some values use 0.1 or 0.01 scale
   - Verify unit of measurement
   - Report issue if consistently wrong

2. **Verify register mapping**:
   - Check `REGISTER_MAPPING.md`
   - Some models use different registers
   - May need device-specific configuration

3. **Read timing issue**:
   - Value updating during read
   - Causes temporary inconsistency
   - Should resolve on next update

4. **Enable raw value debug**:
   ```yaml
   # configuration.yaml
   srne_inverter:
     raw_sensors: true
   ```
   - Compare raw vs scaled values
   - Identify scaling issues

---

## Permission Issues

### Cannot Write to Registers

**Symptoms**:
- Write operations fail
- Error: "Permission denied (0x0B)"

**Solutions**:

1. **Configure password**:
   - Settings → Devices → SRNE BLE Modbus → Configure
   - Enter password for protected range
   - Try defaults: 4321, 0000, 111111

2. **Verify register is writable**:
   - Check `REGISTER_MAPPING.md`
   - Some registers are read-only
   - Cannot be written even with password

3. **Password authentication timing**:
   - Password valid for current session
   - Lost on disconnect/reconnect
   - Integration auto-authenticates

4. **Protected range reference**:
   | Range | Password | Description |
   |-------|----------|-------------|
   | 0xE000-0xE0FF | 4321 | Battery settings |
   | 0xE200-0xE2FF | 0000 | Grid settings |
   | 0xE300-0xE3FF | 111111 | Software settings |

### Write Succeeds But Value Not Changed

**Symptoms**:
- No error message
- Value remains unchanged after write

**Solutions**:

1. **Value validation**:
   - Inverter may reject out-of-range values
   - Check min/max limits
   - Verify value makes sense for parameter

2. **Write verification**:
   - Enable write verification logging
   - Check actual value written
   - Compare with intended value

3. **Firmware protection**:
   - Some parameters locked by firmware
   - Requires different unlock procedure
   - Contact SRNE support

4. **Mode-dependent settings**:
   - Some settings only apply in certain modes
   - Example: Grid settings when grid connected
   - Change mode first, then setting

---

## Performance Issues

### Slow Data Updates

**Symptoms**:
- Entity updates take > 30 seconds
- Long delays between value changes

**Solutions**:

1. **BLE protocol limitation**:
   - 10-second minimum between commands
   - Normal behavior, not a bug
   - Cannot be eliminated

2. **Optimize update interval**:
   - Default: 30 seconds (optimal)
   - Faster not recommended (BLE constraints)
   - Slower acceptable if preferred

3. **Reduce registered entities**:
   - Disable unused entities
   - Fewer registers = faster updates
   - Focus on critical sensors

4. **Check system load**:
   ```bash
   top
   # Look for CPU usage
   # Ensure HA not resource-constrained
   ```

### Initial Setup Takes Too Long

**Symptoms**:
- Setup wizard runs for > 5 minutes
- Progress appears stuck

**Solutions**:

1. **Register scanning is normal**:
   - First setup scans 100+ registers
   - Takes 2-3 minutes with 10s spacing
   - Be patient, do not cancel

2. **Failed register retry**:
   - Unsupported registers retried
   - Adds time to initial scan
   - Cached after first failure

3. **Monitor progress**:
   - Enable debug logging
   - Watch register scan in logs
   - Verify progressing, not stuck

4. **Background processing**:
   - Setup can continue in background
   - Close wizard after starting
   - Entities appear when ready

---

## Connection Stability

### Frequent Disconnections

**Symptoms**:
- Connection drops every few minutes
- Constant "unavailable" → "available" cycles

**Solutions**:

1. **Improve signal strength**:
   - Move HA server closer
   - Use USB extension cable for BT adapter
   - Avoid metal obstacles

2. **Reduce interference**:
   - Change WiFi to 5GHz band
   - Disable nearby Bluetooth devices
   - Move away from microwave ovens

3. **Increase connection keepalive**:
   - Integration handles reconnection
   - Automatic retry with backoff
   - Check logs for reconnect frequency

4. **Bluetooth adapter quality**:
   - Some adapters have poor BLE support
   - Try different adapter
   - Prefer name-brand (Intel, Broadcom)

5. **Power saving issues**:
   ```bash
   # Disable Bluetooth power saving
   echo 'on' > /sys/bus/usb/devices/[device]/power/level
   ```

### Connection Loss After Inverter Restart

**Symptoms**:
- Connection fails after inverter reboot
- Manual reconnection required

**Solutions**:

1. **Normal behavior**:
   - BLE connection lost when inverter resets
   - Integration auto-reconnects
   - Wait 30-60 seconds

2. **Inverter boot time**:
   - BLE module takes 20-30s to initialize
   - Too-fast reconnect attempts fail
   - Automatic retry handles this

3. **Check reconnection logs**:
   ```
   [srne_inverter] Connection lost, reconnecting...
   [srne_inverter] Reconnection successful
   ```

4. **Manual reconnect if needed**:
   - Settings → Devices → SRNE Inverter
   - Reload integration
   - Or restart Home Assistant

---

## Error Messages

### Common Error Codes

**Modbus Exception 0x01: Illegal Function**
```
Error: Modbus exception 0x01 (Illegal Function)
```
- **Cause**: Unsupported function code
- **Solution**: Update integration, report issue

**Modbus Exception 0x02: Illegal Data Address**
```
Error: Modbus exception 0x02 (Illegal Data Address)
```
- **Cause**: Register not supported by inverter model
- **Solution**: Normal, register cached as unsupported

**Modbus Exception 0x03: Illegal Data Value**
```
Error: Modbus exception 0x03 (Illegal Data Value)
```
- **Cause**: Value out of acceptable range
- **Solution**: Check min/max limits, adjust value

**Modbus Exception 0x0B: Permission Denied**
```
Error: Modbus exception 0x0B (Permission Denied)
```
- **Cause**: Password required for protected register
- **Solution**: Configure password in settings

**BLE Error: Connection Timeout**
```
Error: Connection timeout after 10 seconds
```
- **Cause**: BLE device not responding
- **Solution**: Check device powered on, within range

**BLE Error: Device Not Found**
```
Error: Device E6XXXX not found
```
- **Cause**: Device out of range or powered off
- **Solution**: Move closer, verify device on

---

## Debug Mode

### Enable Debug Logging

```yaml
# configuration.yaml
logger:
  default: info
  logs:
    custom_components.srne_inverter: debug
    custom_components.srne_inverter.coordinator: debug
    custom_components.srne_inverter.ble_manager: debug
```

### Useful Log Filters

**Connection issues**:
```bash
grep "BLE" home-assistant.log
```

**Register read failures**:
```bash
grep "Modbus exception" home-assistant.log
```

**Write operations**:
```bash
grep "write_register" home-assistant.log
```

**Authentication**:
```bash
grep "password" home-assistant.log
```

---

## Advanced Troubleshooting

### Packet Capture

Use Wireshark or btmon for BLE traffic analysis:

```bash
# Start BLE monitoring
btmon -w ble_capture.pcap

# In another terminal, trigger operations
# Stop btmon with Ctrl+C

# Analyze with Wireshark
wireshark ble_capture.pcap
```

### Manual BLE Testing

Use BLE test suite for direct testing:

```bash
cd /config/custom_components/srne_inverter/tests
python ble_test_suite.py --device E6XXXXXXXXXXXX --test-all
```

### Database Issues

Reset integration data:

```bash
# Stop Home Assistant
# Edit /config/.storage/core.config_entries
# Find srne_inverter entry, delete it
# Restart Home Assistant
# Re-add integration
```

---

## Getting Help

### Before Requesting Support

1. **Enable debug logging**
2. **Reproduce the issue**
3. **Collect logs** (last 50 lines minimum)
4. **Note system details**:
   - Home Assistant version
   - Integration version
   - Inverter model
   - Bluetooth adapter type

### Creating an Issue

Include in GitHub issue:

```markdown
## System Information
- HA Version: 2024.x.x
- Integration Version: 1.x.x
- Inverter Model: SR-HF2430Sxx-xxx

## Problem Description
[Clear description of issue]

## Steps to Reproduce
1. [First step]
2. [Second step]
3. [Issue occurs]

## Expected Behavior
[What should happen]

## Actual Behavior
[What actually happens]

## Logs
```
[Paste relevant logs here]
```

## Attempted Solutions
[What you've already tried]
```

### Community Support

- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: General questions and help
- **Documentation**: Check all guides first

---

## Preventing Issues

### Best Practices

1. **Initial Setup**:
   - Ensure strong BLE signal
   - Allow full register scan to complete
   - Configure password before writing

2. **Regular Operation**:
   - Monitor connection status
   - Review logs periodically
   - Keep integration updated

3. **Configuration Changes**:
   - Test in safe conditions
   - Verify values before writing
   - Monitor for 24 hours after changes

4. **System Maintenance**:
   - Keep Home Assistant updated
   - Update Bluetooth firmware
   - Restart integration monthly

### Warning Signs

Watch for these indicators of problems:

- Increasing connection failures
- Growing log file size
- Slow entity updates
- Frequent "unavailable" states
- Write verification failures

Address issues early before they escalate.

---

## Known Limitations

### Protocol Limitations

1. **10-second command spacing**: Cannot be eliminated
2. **Single client**: Only one BLE connection at a time
3. **Range**: 10-30 meters typical
4. **Throughput**: ~1-2 KB/s effective

### Integration Limitations

1. **Model variations**: Some registers model-specific
2. **Firmware differences**: Older firmware lacks features
3. **Password management**: Session-based, not persistent
4. **Bulk operations**: Limited batch size

### Hardware Limitations

1. **Bluetooth interference**: Susceptible to 2.4GHz noise
2. **Adapter quality**: Varies significantly
3. **USB positioning**: Affects range
4. **Power saving**: Can cause disconnects

---

**Last Updated**: 2026-02-05

**Need more help?** Check [Documentation Index](INDEX.md) or create a [GitHub Issue](https://github.com/krimsonkla/srne_ble_modbus/issues).
