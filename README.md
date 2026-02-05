# SRNE BLE Modbus Integration for Home Assistant

> [!WARNING]
> **Work in Progress:** This integration is currently under active development and has undergone very little testing. Features may be incomplete, unstable, or change significantly without notice. **Use at your own risk.**

[![GitHub Release](https://img.shields.io/github/v/release/krimsonkla/srne_ble_modbus?style=flat-square)](https://github.com/krimsonkla/srne_ble_modbus/releases)
[![License](https://img.shields.io/github/license/krimsonkla/srne_ble_modbus?style=flat-square)](LICENSE)
[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg?style=flat-square)](https://github.com/hacs/integration)

Local Bluetooth Low Energy (BLE) integration enabling comprehensive monitoring and control of SRNE HF Series hybrid inverters with Home Assistant. No cloud connection required.

## Critical Disclaimer

**USE AT YOUR OWN RISK**

This software interfaces directly with electrical equipment via Bluetooth Low Energy (BLE). Improper configuration or use may result in:
- Equipment damage or destruction
- Voided warranty
- Battery damage or thermal runaway
- Personal injury or property damage
- Fire or electrical hazards

**See [DISCLAIMER.md](DISCLAIMER.md) for complete safety warnings and terms.**

Professional installation is strongly recommended for users unfamiliar with electrical systems or battery management.

---

## Features

### Real-Time Monitoring
- **Battery Management**: State of charge (SOC), voltage, current, temperature
- **Solar Production**: PV voltage, current, and power tracking
- **Grid Monitoring**: Voltage, frequency, and power consumption
- **Load Tracking**: AC output voltage, frequency, current, and power
- **System Health**: Comprehensive fault detection and status monitoring
- **Performance Metrics**: Efficiency tracking and energy statistics

### Control Capabilities
- **Energy Priority Modes**: Solar First, Battery First, Utility First
- **Current Limits**: Configurable battery charge and discharge limits
- **Output Configuration**: Voltage and frequency adjustment
- **Charging Control**: Enable/disable charging on demand
- **Load Management**: AC output control and scheduling

### Automation Support
27 production-ready automation blueprints:
- **10 Safety Automations**: Battery protection, thermal management, grid failure handling
- **10 Optimization Automations**: Peak shaving, solar optimization, time-of-use scheduling
- **7 Monitoring Automations**: Performance tracking, health monitoring, reporting

## Supported Hardware

### SRNE HF Series Inverters
Models being tested:
- ** [Eco Worthy (Rebranded SRNE) 3000W 24V All In One Inverter](https://cdn.shopifycdn.net/s/files/1/0253/9752/6580/files/24V_3000W_solar_inverter_charger.pdf?v=1673075862) HF4830U60-145
  - With accompanied BLE/Wifi Dongle - WFBLE.DTU.PlugPro

Other HF series models may be compatible. Verify your model supports BLE before installation.

### Requirements
- **Home Assistant**: Version 2024.12.0 or newer
- **Bluetooth**: BLE adapter (Bluetooth 4.0+)
- **Inverter**: SRNE HF series with BLE enabled
- **Python**: 3.11+ (automatically handled by Home Assistant)

## Installation

### Method 1: HACS (Recommended)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=krimsonkla&repository=srne_ble_modbus&category=Integration)

1. **Add Custom Repository**
   - Open HACS in Home Assistant.
   - Click the three dots (⋮) in the top right corner.
   - Select **Custom repositories**.
   - Paste the repository URL: `https://github.com/krimsonkla/srne_ble_modbus`
   - Select **Integration** from the category dropdown.
   - Click **Add**.

2. **Install Integration**
   - Click on the newly added **SRNE BLE Modbus** repository.
   - Click **Download** in the bottom right corner.
   - Select the latest version and click **Download** again.
   - **Restart Home Assistant** when prompted or manually.

3. **Configure**
   - After restart, navigate to **Settings** → **Devices & Services**.
   - Click **+ Add Integration**.
   - Search for **SRNE BLE Modbus**.
   - Follow the configuration prompts (see [Initial Setup](#initial-setup)).

### Method 2: Manual Installation

```bash
cd /config
git clone https://github.com/krimsonkla/srne_ble_modbus.git custom_components/srne_inverter
```

Or download the latest release and extract to `custom_components/srne_inverter/`.

Restart Home Assistant after installation.

## Configuration

### Initial Setup

1. **Settings → Devices & Services → Add Integration**
2. Search for "SRNE BLE Modbus" or "SRNE"
3. Enter configuration details:
   - **Device Name**: Friendly name for your inverter
   - **BLE MAC Address**: Find using Home Assistant BLE scanner or `hcitool lescan`
   - **Password**: Default is `0000` (check your inverter manual)

4. **Advanced Options** (optional):
   - Update interval (default: 30 seconds)
   - Connection timeout settings
   - Enable/disable specific entity groups

### Finding Your BLE MAC Address

**Using Home Assistant:**
- Settings → Devices & Services → Bluetooth
- Look for devices starting with "E60"

**Using Command Line:**
```bash
hcitool lescan
# Look for device name starting with E60
```

### Entity Configuration

The integration automatically discovers and configures entities from `entities_pilot.yaml`. Entities are dynamically created based on:
- Inverter model capabilities
- Available Modbus registers
- Register read/write permissions

Unsupported or unavailable entities are automatically hidden to prevent errors.

## Automation Blueprints

### Quick Start Examples
Located in `examples/automations/quick_start/`:

- **Battery Protection**: Low battery alerts and protection
- **Grid Monitoring**: Grid failure detection and notification
- **Temperature Alerts**: Battery and inverter temperature monitoring
- **Production Tracking**: Solar production logging
- **Load Management**: High load alerts and management

### Advanced Blueprints
Located in `blueprints/automation/srne_inverter/`:

#### 1. Safety Automations (`1_safety/`)
Critical protection features:
- Battery voltage and SOC protection
- Progressive battery protection with multi-level alerts
- Temperature protection and thermal stress monitoring
- Grid failure detection and automatic response
- Fault monitoring and emergency shutdown
- Generator auto-start on grid failure
- Under-frequency load shedding
- Soft start recovery procedures

#### 2. Optimization Automations (`2_optimization/`)
Cost reduction and efficiency:
- Peak shaving to reduce demand charges
- Solar production optimization
- Time-of-use scheduling for grid charging
- Smart night charging with rate optimization
- Dynamic current limiting based on conditions
- EV charging coordination
- Solar export optimization
- Equalizing charge scheduling
- Solar midday boost during high production

#### 3. Monitoring Automations (`3_monitoring/`)
Performance and health tracking:
- Daily energy reports with statistics
- Performance dashboards and visualizations
- Battery health tracking and trending
- Fault monitoring with detailed alerts
- Seasonal parameter adjustment
- Weather-based priority optimization

See [blueprints/automation/srne_inverter/README.md](blueprints/automation/srne_inverter/README.md) for detailed documentation.

## Safety Guidelines

### Mandatory Precautions

1. **Read Your Inverter Manual**
   - Understand all specifications and limits
   - Know your battery chemistry requirements
   - Verify compatible voltage and current ranges

2. **Test in Safe Conditions**
   - Monitor system closely for first 24-48 hours
   - Start with conservative settings
   - Gradually adjust parameters as needed

3. **Implement Safety Automations First**
   - Configure battery protection before optimization
   - Set up temperature monitoring immediately
   - Enable fault detection and alerts

4. **Know Your Battery Chemistry**
   - Use manufacturer specifications for voltage limits
   - Set appropriate charge/discharge currents
   - Configure temperature thresholds correctly

5. **Manual Override Capability**
   - Maintain ability to disconnect power manually
   - Have emergency shutdown procedure documented
   - Keep fire extinguisher (Class C/ABC) accessible

6. **Professional Consultation**
   - Consult licensed electrician for installation
   - Verify compliance with local electrical codes
   - Have system inspected by qualified professional

### Dangerous Operations

**Never perform these operations without complete understanding:**
- Writing to registers without knowing consequences
- Setting voltage/current beyond manufacturer specifications
- Disabling all safety automations simultaneously
- Operating system without monitoring
- Modifying battery parameters during charging/discharging
- Bypassing inverter safety features

## Documentation

### Legal and Safety (READ FIRST)
- [**DISCLAIMER.md**](DISCLAIMER.md) - **MANDATORY READ** - Complete safety warnings and legal terms
- [LICENSE](LICENSE) - MIT License terms and conditions
- [CONTRIBUTING.md](CONTRIBUTING.md) - Contribution guidelines and safety requirements
- [SECURITY.md](SECURITY.md) - Security policy and responsible disclosure

### User Guides
- [Installation Guide](docs/QUICK_START_BLE.md)
- [Configuration Guide](docs/SRNE_CONFIGURABLE_SETTINGS.md)
- [Password Authentication](docs/PASSWORD_AUTHENTICATION.md)
- [Automation Guide](blueprints/automation/srne_inverter/README.md)

### Technical Documentation
- [Architecture Overview](docs/ARCHITECTURE_SUMMARY.md)
- [BLE Protocol](docs/ble-protocol.md)
- [Modbus Mapping](docs/modbus-protocol-mapping.md)
- [Entity Configuration Schema](docs/ENTITY_CONFIGURATION_SCHEMA.md)
- [Services Reference](docs/services.md)

### Troubleshooting
- [Troubleshooting Guide](docs/QUICK-FIX-GUIDE.md)
- [BLE Connection Issues](docs/BLE_FIX_QUICK_REFERENCE.md)
- [Unsupported Features](docs/UNSUPPORTED_FEATURES_ANALYSIS.md)
- [Auto-Hide Unsupported Entities](docs/AUTO_HIDE_UNSUPPORTED.md)

## Troubleshooting

### BLE Connection Issues

**Problem**: Integration cannot find or connect to inverter

**Solutions**:
1. Verify inverter BLE is enabled in inverter settings
2. Check BLE adapter is working:
   ```bash
   hcitool lescan
   ```
3. Ensure inverter is within BLE range (typically 10-30 feet)
4. Verify MAC address is correct (case-sensitive)
5. Restart Home Assistant Bluetooth integration
6. Check inverter is not connected to another device (Android app)

### Entities Show as Unavailable

**Problem**: Some entities appear unavailable after setup

**Causes**:
- Register not supported by your inverter model
- Permission denied (requires password authentication)
- Modbus communication error
- Entity automatically hidden due to read failures

**Solutions**:
1. Check integration logs for specific register errors
2. Verify password is correctly configured
3. Confirm register is supported on your model
4. Review `entities_pilot.yaml` for entity requirements
5. Check [Unsupported Features Guide](docs/UNSUPPORTED_FEATURES_ANALYSIS.md)

### Write Operations Failing

**Problem**: Cannot change inverter settings

**Solutions**:
1. Verify password authentication is configured correctly
2. Common passwords: `0000`, `4321`, `1111`, `111111`
3. Check register is writable on your model
4. Review logs for Modbus exception codes
5. Ensure inverter is in correct mode for configuration
6. Some settings require specific operational states

### Slow Updates or Timeouts

**Problem**: Entity updates are slow or time out

**Solutions**:
1. Increase update interval in integration options
2. Reduce number of enabled entities
3. Check BLE signal strength
4. Verify no BLE interference from other devices
5. Review [Performance Analysis](docs/PERFORMANCE_ANALYSIS.md)

### Incorrect Values Displayed

**Problem**: Sensor values appear incorrect

**Solutions**:
1. Enable debug logging to check raw register values
2. Verify scaling factors in entity configuration
3. Check [Scaling Simplification Guide](docs/SCALING_SIMPLIFICATION.md)
4. Compare with inverter display or Android app
5. Review [Debug Raw Values Guide](docs/DEBUG_RAW_VALUES.md)

## Contributing

Contributions are welcome! **Please read [CONTRIBUTING.md](CONTRIBUTING.md) and [DISCLAIMER.md](DISCLAIMER.md) before submitting pull requests.**

All contributors must understand the safety implications and follow our safety-first development practices.

### Development Setup

```bash
# Clone repository
git clone https://github.com/krimsonkla/srne_ble_modbus.git
cd srne_ble_modbus

# Install development dependencies
pip install -r requirements_dev.txt

# Run tests
pytest tests/

# Run linting
pylint custom_components/srne_inverter/
```

### Reporting Issues

When reporting issues, please include:
- Home Assistant version
- Integration version
- Inverter model and firmware version
- BLE adapter details
- Relevant logs with debug logging enabled
- Steps to reproduce the issue

### Feature Requests

We welcome feature requests! Please:
- Check existing issues first
- Provide clear use case description
- Include example configuration if applicable
- Consider submitting a pull request

## Support

### Community Support
- **GitHub Issues**: [Report bugs and issues](https://github.com/krimsonkla/srne_ble_modbus/issues)
- **GitHub Discussions**: [Ask questions and share ideas](https://github.com/krimsonkla/srne_ble_modbus/discussions)
- **Documentation**: [Complete documentation](docs/)

### Professional Support
For commercial installations or professional support:
- Review [Professional Installation Guide](docs/QUICK_START_BLE.md)
- Consult with licensed electrician
- Contact qualified Home Assistant integrator

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Disclaimer

**This project is not affiliated with, endorsed by, or supported by SRNE.**

THE SOFTWARE IS PROVIDED "AS IS" WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, OR NONINFRINGEMENT.

**YOU ASSUME ALL RISKS AND LIABILITY FOR USING THIS SOFTWARE.**

See [DISCLAIMER.md](DISCLAIMER.md) for complete legal terms and safety warnings.

## Acknowledgments

- **SRNE** for publishing Modbus protocol documentation
- **Home Assistant Community** for integration framework and support
- **Contributors** for testing, bug reports, and feature development
- **Bleak Library** for BLE communication support

## Project Status

**Current Version**: 0.4.0

### Recent Updates
- Added 27 production-ready automation blueprints
- Implemented automatic entity hiding for unsupported registers
- Enhanced BLE connection stability and error handling
- Added comprehensive password authentication support
- Improved entity configuration with dynamic discovery
- Expanded monitoring and control capabilities

### Roadmap
- Expanded inverter model support
- Enhanced automation templates
- Advanced diagnostics and troubleshooting tools
- Performance optimization
- Multi-inverter support
- Cloud-free backup and restore

---

**Remember: This software controls electrical equipment. Always prioritize safety over convenience.**

For questions about safe operation, electrical safety, battery safety, or system design, consult with qualified professionals before proceeding.
