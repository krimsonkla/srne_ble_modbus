# SRNE BLE Modbus — Documentation Index

Map of the documentation for the SRNE BLE Modbus Home Assistant integration.

## ⚠️ Disclaimer

**USE AT YOUR OWN RISK.** This software interfaces directly with your SRNE
inverter over BLE. Improper configuration or use may damage your inverter or
battery, void your warranty, or cause equipment malfunction.

**Always** test in safe conditions first, keep your battery manufacturer's
specifications to hand, monitor the system closely during initial setup, and
have manual override procedures ready.

See [DISCLAIMER.md](../DISCLAIMER.md) for the complete safety warnings and legal
terms. The authors assume no liability for any damage or loss.

---

## Start Here

### Users

1. [Installation](../README.md#installation) — HACS or manual install
2. [Quick Start](QUICK_START.md) — step-by-step first-time setup
3. [Automation Blueprints](../blueprints/automation/srne_inverter/README.md) —
   27 ready-made automations
4. [Troubleshooting](TROUBLESHOOTING.md) — when something isn't working

### Developers

1. [Architecture](ARCHITECTURE.md) — layering, DI container, data flow
2. [BLE Protocol](BLE_PROTOCOL.md) — transport framing, CRC, register semantics
3. [Test Suite](../tests/README.md) — test layout and how to run it
4. [Contributing](../CONTRIBUTING.md) — workflow and safety requirements

---

## Core Documentation

| Document                                 | Contents                                      |
| ---------------------------------------- | --------------------------------------------- |
| [README](../README.md)                   | Project overview, installation, configuration |
| [QUICK_START.md](QUICK_START.md)         | First-time setup walkthrough                  |
| [ARCHITECTURE.md](ARCHITECTURE.md)       | System design, layer boundaries, DI container |
| [BLE_PROTOCOL.md](BLE_PROTOCOL.md)       | Modbus-over-BLE transport details             |
| [TROUBLESHOOTING.md](TROUBLESHOOTING.md) | Connection, register, and entity issues       |
| [AUTOMATIONS.md](../AUTOMATIONS.md)      | How the blueprint library is organized        |

## Project Documents

| Document                              | Contents                                         |
| ------------------------------------- | ------------------------------------------------ |
| [DISCLAIMER.md](../DISCLAIMER.md)     | Safety warnings and legal terms — **read first** |
| [CONTRIBUTING.md](../CONTRIBUTING.md) | Contribution guidelines and dev setup            |
| [SECURITY.md](../SECURITY.md)         | Security policy and responsible disclosure       |
| [LICENSE](../LICENSE)                 | MIT License                                      |

---

## Reference Material

Vendor documentation this integration was built against:

- [SRNE Energy Storage Inverter Protocol v1.96](../resources/SRNE_Energy_Storage_Inverter_Protocol_v1.96.md)
  — complete Modbus register reference
- [SRNE HF Series User Manual](../resources/SRNE_HF_Series_User_Manual.md) —
  hardware documentation

### Device Information

- **Supported models**: SRNE HF Series (2000W–3000W)
- **Communication**: Bluetooth Low Energy (BLE)
- **Protocol**: Modbus RTU over BLE GATT
- **Default update interval**: 30 seconds

---

## Automation Blueprints

Located under `blueprints/automation/srne_inverter/`.

| Category                   | Count | Documentation                                                                               |
| -------------------------- | ----- | ------------------------------------------------------------------------------------------- |
| Safety (essential)         | 10    | [1_safety/README.md](../blueprints/automation/srne_inverter/1_safety/README.md)             |
| Optimization (recommended) | 10    | [2_optimization/README.md](../blueprints/automation/srne_inverter/2_optimization/README.md) |
| Monitoring (optional)      | 7     | [3_monitoring/README.md](../blueprints/automation/srne_inverter/3_monitoring/README.md)     |

Safety blueprints cover progressive battery protection, temperature protection,
grid failure detection, and fault response. Optimization covers peak shaving,
solar optimization, smart night charging, and dynamic current limiting.
Monitoring covers performance dashboards, battery health tracking, and fault
alerting.

Start with
[the blueprint overview](../blueprints/automation/srne_inverter/README.md).

---

## Version Information

- **Integration version**: 0.5.0 — authoritative source is
  [`manifest.json`](../custom_components/srne_inverter/manifest.json)
- **Minimum Home Assistant version**: 2024.12.0
- **Protocol**: Modbus RTU over BLE

## Support

- **Repository**: https://github.com/krimsonkla/srne_ble_modbus
- **Issues**: https://github.com/krimsonkla/srne_ble_modbus/issues
- **Discussions**: https://github.com/krimsonkla/srne_ble_modbus/discussions
