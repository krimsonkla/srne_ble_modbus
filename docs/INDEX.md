# SRNE BLE Modbus Documentation Index

Complete documentation for the SRNE BLE Modbus Home Assistant integration.

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

## Quick Start

### New Users
1. [Installation Guide](../README.md#installation)
2. [Quick Start Guide](QUICK_START.md)
3. [Essential Safety Blueprints](../blueprints/automation/srne_inverter/QUICK_START.md)

### Developers
1. [Architecture Overview](ARCHITECTURE.md)
2. [BLE Protocol Specification](BLE_PROTOCOL.md)
3. [Register Mapping](REGISTER_MAPPING.md)

---

## Core Documentation

### Installation & Setup
- [**README.md**](../README.md) - Main project overview and installation
- [**QUICK_START.md**](QUICK_START.md) - Step-by-step setup guide
- [**Configuration Guide**](CONFIGURATION.md) - Detailed configuration options

### Technical Documentation
- [**Architecture Overview**](ARCHITECTURE.md) - System design and components
- [**BLE Protocol**](BLE_PROTOCOL.md) - Bluetooth Low Energy communication
- [**Register Mapping**](REGISTER_MAPPING.md) - Complete Modbus register reference
- [**Services**](services.md) - Available service calls

### User Guides
- [**Automation Blueprints**](../blueprints/automation/srne_inverter/README.md) - Pre-built automations
- [**Energy Dashboard**](energy_dashboard_integration.md) - Energy monitoring setup
- [**Troubleshooting**](TROUBLESHOOTING.md) - Common issues and solutions

---

## Advanced Topics

### Protocol & Communication
- [BLE Communication Details](ble-communication-flow.md)
- [Modbus Protocol Mapping](modbus-protocol-mapping.md)
- [Password Authentication](PASSWORD_AUTHENTICATION.md)

### Development
- [Entity Configuration Schema](ENTITY_CONFIGURATION_SCHEMA.md)
- [Extensibility Guide](EXTENSIBILITY_GUIDE.md)
- [Testing Guide](TESTING.md)

### Optimization
- [Performance Analysis](PERFORMANCE_ANALYSIS.md)
- [Model-Specific Features](MODEL_SPECIFIC_FEATURES.md)

---

## Automation Blueprints

### Safety (Essential)
Located in: `blueprints/automation/srne_inverter/1_safety/`

1. Progressive Battery Protection
2. Temperature Protection
3. Grid Failure Detection
4. Fault Response
5. And 6 more critical safety automations

[Full Safety Documentation](../blueprints/automation/srne_inverter/1_safety/README.md)

### Optimization (Recommended)
Located in: `blueprints/automation/srne_inverter/2_optimization/`

1. Peak Shaving Optimizer
2. Solar Optimization
3. Smart Night Charging
4. Dynamic Current Limiter
5. And 6 more efficiency automations

[Full Optimization Documentation](../blueprints/automation/srne_inverter/2_optimization/README.md)

### Monitoring (Optional)
Located in: `blueprints/automation/srne_inverter/3_monitoring/`

1. Daily Performance Dashboard
2. Battery Health Tracker
3. Fault Monitor
4. And 4 more monitoring automations

[Full Monitoring Documentation](../blueprints/automation/srne_inverter/3_monitoring/README.md)

---

## Reference Materials

### Register Maps
- [Inverter Manual Mapping](inverter-manual-mapping.md)
- [Configurable Settings](SRNE_CONFIGURABLE_SETTINGS.md)
- [Unsupported Features](UNSUPPORTED_FEATURES_ANALYSIS.md)

### Device Information
- Supported Models: SRNE HF Series (2000W-3000W)
- Communication: Bluetooth Low Energy (BLE)
- Protocol: Modbus RTU over BLE
- Update Interval: 30 seconds default

---

## Troubleshooting Resources

### Common Issues
- [BLE Connection Problems](TROUBLESHOOTING.md#ble-connection)
- [Register Read Errors](TROUBLESHOOTING.md#register-errors)
- [Permission Denied Errors](PASSWORD_AUTHENTICATION.md)
- [Entity Not Available](TROUBLESHOOTING.md#entity-issues)

### Debug Tools
- [Debug Raw Values](DEBUG_RAW_VALUES.md)
- [Auto-Hide Unsupported Entities](AUTO_HIDE_UNSUPPORTED.md)

---

## Version Information

- **Integration Version**: 1.0.0
- **Protocol Version**: Modbus RTU over BLE
- **Minimum HA Version**: 2024.11.0
- **Last Updated**: 2026-02-05

---

## Support & Community

- **GitHub Repository**: https://github.com/krimsonkla/srne_ble_modbus
- **Issues**: https://github.com/krimsonkla/srne_ble_modbus/issues
- **Discussions**: https://github.com/krimsonkla/srne_ble_modbus/discussions

---

## Contributing

We welcome contributions. Please review:
- [Architecture Documentation](ARCHITECTURE.md)
- [Extensibility Guide](EXTENSIBILITY_GUIDE.md)
- [Testing Guidelines](TESTING.md)

Submit pull requests with:
- Clear description of changes
- Updated documentation
- Test coverage for new features

---

## License

This project is licensed under the terms specified in the LICENSE file.

**No warranty or liability is provided. Use at your own risk.**
