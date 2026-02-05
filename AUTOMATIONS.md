# SRNE Inverter Automations

Complete automation system for SRNE HF Series inverters with Home Assistant.

## Directory Structure

```
srne_ble_modbus/
├── blueprints/automation/srne_inverter/    # Advanced blueprints (27 files)
│   ├── 1_safety/                           # Battery, temperature, grid protection
│   ├── 2_optimization/                     # Peak shaving, TOU, solar optimization
│   └── 3_monitoring/                       # Performance tracking, health monitoring
│
└── examples/automations/quick_start/       # Simple examples (12 files)
    └── *.yaml                              # Copy-paste ready automations
```

## Getting Started

### For Beginners
**Start here:** `examples/automations/quick_start/`
- Simple copy-paste automations
- No blueprint knowledge needed
- Basic monitoring and alerts
- See: `examples/automations/quick_start/README.md`

### For Intermediate Users
**Next step:** `blueprints/automation/srne_inverter/1_safety/`
- Essential battery and grid protection
- Use Home Assistant blueprint system
- Configurable via UI
- See: `blueprints/automation/srne_inverter/ESSENTIAL_BLUEPRINTS.md`

### For Advanced Users
**Full system:** All three blueprint categories
- Complete safety + optimization + monitoring
- 27 advanced blueprints
- Fully coordinated automation system
- See: `blueprints/automation/srne_inverter/README.md`

## Quick Reference

| Level | Location | Count | Complexity |
|-------|----------|-------|------------|
| **Beginner** | `examples/automations/quick_start/` | 12 files | Low - Direct automations |
| **Intermediate** | `blueprints/.../1_safety/` | 10 files | Medium - Essential blueprints |
| **Advanced** | `blueprints/.../2_optimization/` | 10 files | High - Optimization strategies |
| **Expert** | `blueprints/.../3_monitoring/` | 7 files | Very High - Advanced analytics |

## Blueprint Categories

### 1. Safety (10 blueprints)
Critical protection automations:
- Progressive battery protection
- Temperature monitoring
- Grid disconnection handling
- Thermal stress protection
- Generator auto-start
- Under-frequency load shedding
- Soft-start recovery

**Priority:** Install these FIRST

### 2. Optimization (10 blueprints)
Cost reduction and efficiency:
- Peak shaving
- Solar optimization
- Smart night charging
- EV charging
- Time-of-use scheduling
- Dynamic current limiting
- Export optimization

**Priority:** Install after safety is tested

### 3. Monitoring (7 blueprints)
Performance tracking and alerts:
- Daily performance dashboard
- Battery health tracking
- Fault monitoring
- Seasonal adjustments
- Weather-based priority

**Priority:** Optional but recommended

## Installation

### Quick Start Examples
```bash
# Copy desired automation to your config/automations directory
cp examples/automations/quick_start/simple_low_battery_alert.yaml ~/config/automations/

# Restart Home Assistant or reload automations
```

### Blueprints
1. Go to Home Assistant → Settings → Automations & Scenes → Blueprints
2. Click "Import Blueprint"
3. Use raw GitHub URL for desired blueprint
4. Configure and create automation

## Documentation

- **Quick Start Guide**: `blueprints/automation/srne_inverter/QUICK_START.md`
- **Essential Blueprints**: `blueprints/automation/srne_inverter/ESSENTIAL_BLUEPRINTS.md`
- **All Blueprints Reference**: `blueprints/automation/srne_inverter/QUICK_REFERENCE.md`
- **Implementation Guide**: `blueprints/automation/srne_inverter/IMPLEMENTATION_SUMMARY.md`
- **Quality Review**: `docs/QUALITY_REVIEW.md`

## Safety Notice

⚠️ **Battery Protection is Critical**
- Always start with safety automations
- Test in safe conditions first
- Monitor for 24 hours before relying on automations
- Keep battery manufacturer specifications handy
- Don't disable all safety automations simultaneously

## Support

- Integration Issues: See main README.md
- Automation Questions: See blueprint documentation
- Entity Mappings: Check `entities_pilot.yaml` for your specific inverter

## Status

✅ Production Ready - All automations reviewed and approved
- 0 Critical Issues
- Quality Review: `docs/QUALITY_REVIEW.md`
- 39 Total automations (27 blueprints + 12 examples)
