# SRNE BLE Modbus - Quick Start Guide

Local development setup for macOS with Home Assistant Core and BLE support.

## 🚀 One-Command Setup

```bash
./setup-local-dev.sh
```

This script will:

- ✅ Create Python virtual environment
- ✅ Install Home Assistant Core
- ✅ Install all dependencies
- ✅ Create config directory
- ✅ Symlink integration for live editing
- ✅ Create basic configuration

**Time**: ~5 minutes

---

## 📋 Prerequisites

```bash
# Install Python 3.12+ (if not already installed)
brew install python@3.12

# Verify installation
python3 --version  # Should show 3.12+
```

---

## 🔧 Manual Setup (Alternative)

If you prefer manual setup:

```bash
# 1. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 2. Install requirements
pip install -r requirements.txt

# 3. Create HA config directory
mkdir -p ~/.homeassistant/custom_components

# 4. Symlink integration
ln -s $(pwd)/custom_components/srne_inverter \
      ~/.homeassistant/custom_components/srne_inverter

# 5. Start Home Assistant
hass
```

---

## 🔍 Test BLE Access

Before starting Home Assistant, verify Bluetooth works:

```bash
# Activate virtual environment
source venv/bin/activate

# Scan for SRNE devices
python3 test_ble_scan.py

# Test specific device (optional)
python3 test_ble_scan.py AA:BB:CC:DD:EE:FF
```

Expected output:

```
✅ Found X BLE device(s)
🎯 SRNE DEVICE FOUND!
   Name: E60X
   Address: AA:BB:CC:DD:EE:FF
   Signal: -XX dBm
```

---

## 🏠 Start Home Assistant

```bash
# Activate virtual environment (if not already active)
source venv/bin/activate

# Start Home Assistant
hass
```

**First time setup**:

1. Open: http://localhost:8123
2. Complete onboarding (create account)
3. Go to: Configuration → Integrations
4. Click: "+ Add Integration"
5. Search: "SRNE BLE Modbus"
6. Follow configuration wizard

---

## ⚙️ Configuration

### Option 1: UI Configuration (Recommended)

Use the Home Assistant web interface to configure via Integrations page.

### Option 2: YAML Configuration

Edit `~/.homeassistant/configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.srne_inverter: debug
    bleak: debug

srne_inverter:
  - name: "SRNE Test"
    address: "AA:BB:CC:DD:EE:FF" # Your device address
    scan_interval: 30
    # password: "your_password"  # Optional
```

**Restart after changes**:

```bash
# Ctrl+C to stop, then:
hass
```

---

## 🔄 Development Workflow

### Live Editing

The integration is **symlinked**, so changes take effect immediately after
restart:

```bash
# 1. Edit code in: custom_components/srne_inverter/
# 2. Restart Home Assistant: Ctrl+C, then 'hass'
# 3. Test changes
```

### View Logs

```bash
# Real-time logs
tail -f ~/.homeassistant/home-assistant.log

# Search for SRNE logs
grep -i srne ~/.homeassistant/home-assistant.log

# Search for BLE errors
grep -i "ble\|bleak" ~/.homeassistant/home-assistant.log
```

### Run Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=custom_components.srne_inverter --cov-report=term-missing

# Run specific test file
pytest tests/test_coordinator.py -v

# Run tests matching pattern
pytest -k "test_connection"
```

---

## 🐛 Troubleshooting

### BLE device not found

```bash
# 1. Check Bluetooth is enabled
# System Settings → Bluetooth → On

# 2. Grant permissions
# System Settings → Privacy & Security → Bluetooth
# Enable for Terminal/Python

# 3. Scan again
python3 test_ble_scan.py

# 4. Check device is powered on and nearby
```

### Integration not loading

```bash
# 1. Check logs for errors
tail -f ~/.homeassistant/home-assistant.log | grep -i error

# 2. Verify symlink exists
ls -la ~/.homeassistant/custom_components/srne_inverter

# 3. Check manifest.json is valid
cat custom_components/srne_inverter/manifest.json

# 4. Restart in safe mode (loads without custom components)
hass --safe-mode
```

### Connection timeouts

```yaml
# Increase timeout in configuration.yaml
srne_inverter:
  - name: "SRNE Test"
    address: "AA:BB:CC:DD:EE:FF"
    scan_interval: 60 # Longer interval
    timeout: 30 # Longer timeout
```

### Dependency warnings during setup

You may see pip dependency conflict warnings during installation:

```
homeassistant 2024.12.5 requires aiodns==3.2.0, but you have aiodns 3.1.1
homeassistant 2024.12.5 requires attrs==24.2.0, but you have attrs 25.4.0
```

**These warnings are safe to ignore** for local development. They occur because:

- The development environment includes tools (pytest, black, etc.) with
  different requirements
- The `aiodns 3.1.1` downgrade fixes a known compatibility issue in HA 2024.12.5
- These version differences don't affect the SRNE integration functionality

The SRNE integration uses BLE (Bluetooth) for communication, not HTTP, so it's
unaffected by the `aiodns` version. If you see errors in the Home Assistant logs
about `homeassistant_alerts`, that's a core HA component issue, not the SRNE
integration.

---

## 📚 Additional Resources

- **Detailed Setup Guide**: `docs/LOCAL-TESTING-GUIDE.md` (1,359 lines)
- **Test Requirements**: `tests/requirements.txt`
- **Integration Manifest**: `custom_components/srne_inverter/manifest.json`
- **Refactoring Docs**: `docs/` directory

---

## ✅ Verify Everything Works

Checklist:

- [ ] Python 3.12+ installed
- [ ] Virtual environment created
- [ ] Requirements installed (`pip list | grep homeassistant`)
- [ ] BLE scan finds SRNE device (`test_ble_scan.py`)
- [ ] Home Assistant starts without errors (`hass`)
- [ ] Integration shows in UI (http://localhost:8123/config/integrations)
- [ ] Can add integration through UI
- [ ] Entities appear and update

---

## 🎯 Quick Commands Reference

```bash
# Setup
./setup-local-dev.sh                    # One-command setup
source venv/bin/activate                # Activate venv

# Testing
python3 test_ble_scan.py                # Scan for devices
pytest                                  # Run tests
pytest --cov --cov-report=html          # Coverage report

# Development
hass                                    # Start HA
hass --version                          # Check version
hass --config ~/.homeassistant          # Specify config dir
tail -f ~/.homeassistant/home-assistant.log  # View logs

# Cleanup
rm -rf ~/.homeassistant                 # Remove HA config (careful!)
deactivate                              # Exit virtual environment
rm -rf venv                             # Remove virtual environment
```

---

## 🚨 Common Mistakes

❌ **Not activating virtual environment**

```bash
# Wrong:
hass  # Uses system Python

# Right:
source venv/bin/activate
hass  # Uses venv Python
```

❌ **Wrong device address format**

```yaml
# Wrong:
address: "E60X" # Device name, not address
address: "AA-BB-CC-DD-EE-FF" # Wrong separator

# Right:
address: "AA:BB:CC:DD:EE:FF" # MAC address with colons
```

❌ **Forgetting to restart after code changes**

```bash
# Changes won't appear until you restart:
# Ctrl+C, then: hass
```

---

## 💡 Pro Tips

- Use `hass --skip-pip` to start faster (skips pip check)
- Add `--log-no-color` for cleaner log files
- Use `pytest -x` to stop at first failure
- Install `ipython` for better Python REPL: `pip install ipython`
- Use VS Code with Python extension for debugging

---

**Ready to develop!** 🎉

For detailed information, see: `docs/LOCAL-TESTING-GUIDE.md`
