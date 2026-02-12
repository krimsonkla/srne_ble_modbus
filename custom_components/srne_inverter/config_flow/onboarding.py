"""Config flow onboarding for SRNE HF Series Inverter integration."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components import bluetooth
from homeassistant.const import CONF_ADDRESS
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import selector

from .helpers.schema_builder import ConfigFlowSchemaBuilder
from .base import CONFIGURATION_PRESETS, get_options_flow_handler
from ..const import DOMAIN
from ..onboarding import (
    OnboardingContext,
    OnboardingState,
    OnboardingStateMachine,
    FeatureDetector,
)

_LOGGER = logging.getLogger(__name__)


class SRNEConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SRNE Inverter."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._discovered_devices: dict[str, str] = {}
        self._selected_address: str | None = None
        self._onboarding_context: OnboardingContext | None = None
        self._state_machine = OnboardingStateMachine()
        self._detection_progress: dict[str, Any] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step - scan for BLE devices."""
        errors: dict[str, str] = {}

        if user_input is not None:
            address = user_input[CONF_ADDRESS]

            # Set unique ID based on BLE address
            await self.async_set_unique_id(address)
            self._abort_if_unique_id_configured()

            # Store selected address for onboarding flow
            self._selected_address = address

            # Transition to onboarding flow
            self._state_machine.transition(OnboardingState.DEVICE_SELECTED)
            return await self.async_step_welcome()

        # Scan for SRNE devices (E6* prefix)
        discovered = await self._async_scan_devices()

        if not discovered:
            errors["base"] = "no_devices_found"

        data_schema = vol.Schema(
            {
                vol.Required(CONF_ADDRESS): vol.In(discovered),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "device_count": str(len(discovered)),
            },
        )

    async def _async_scan_devices(self) -> dict[str, str]:
        """Scan for SRNE BLE devices.

        Returns:
            Dictionary mapping addresses to display names
        """
        _LOGGER.info("Scanning for SRNE BLE devices with E6* prefix")

        # Get current Bluetooth devices from Home Assistant's discovery
        try:
            # Get all discovered service info
            devices = bluetooth.async_discovered_service_info(self.hass)
            _LOGGER.info("Total BLE devices discovered by HA: %d", len(devices))

            srne_devices = {}
            for device in devices:
                _LOGGER.debug(
                    "Checking device: name=%s, address=%s", device.name, device.address
                )

                # SRNE devices have names starting with "E60" (at least 3 chars)
                if device.name and device.name.startswith("E60"):
                    display_name = f"{device.name} ({device.address})"
                    srne_devices[device.address] = display_name
                    self._discovered_devices[device.address] = device.name
                    _LOGGER.info(
                        "Found SRNE device: %s at %s", device.name, device.address
                    )
                elif device.name and device.name.startswith("E6"):
                    # Log devices that match E6 but not E60 for debugging
                    _LOGGER.debug(
                        "Found E6* device but not E60*: %s at %s",
                        device.name,
                        device.address,
                    )

            if not srne_devices:
                _LOGGER.debug(
                    "No SRNE devices found. Ensure: "
                    "1) Inverter is powered on, "
                    "2) BLE is enabled on inverter, "
                    "3) Within Bluetooth range (~10m), "
                    "4) Home Assistant Bluetooth is working"
                )

            return srne_devices

        except Exception as err:
            _LOGGER.exception("Error scanning for devices: %s", err)
            return {}

    async def async_step_bluetooth(
        self, discovery_info: bluetooth.BluetoothServiceInfoBleak
    ) -> FlowResult:
        """Handle bluetooth discovery."""
        _LOGGER.debug("Discovered SRNE device via bluetooth: %s", discovery_info.name)

        address = discovery_info.address
        await self.async_set_unique_id(address)
        self._abort_if_unique_id_configured()

        self.context["title_placeholders"] = {
            "name": discovery_info.name or "SRNE Inverter"
        }
        self._discovered_devices[address] = discovery_info.name or "SRNE Inverter"

        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Confirm bluetooth discovery and start full onboarding."""
        if user_input is not None:
            address = self.context["unique_id"]
            device_name = self._discovered_devices.get(address, "SRNE Inverter")

            _LOGGER.info("Bluetooth discovery confirmed for %s (%s), starting full onboarding", device_name, address)

            # Store selected device for device_selected step
            self._selected_address = address

            # Follow proper state machine flow: device_scan → device_selected → welcome
            self._state_machine.transition(OnboardingState.DEVICE_SELECTED)
            return await self.async_step_device_selected()

        return self.async_show_form(
            step_id="bluetooth_confirm",
            description_placeholders={
                "name": self.context["title_placeholders"]["name"],
            },
        )

    async def async_step_device_selected(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Device selected - initialize context and proceed to welcome."""
        # Initialize onboarding context
        address = self._selected_address
        device_name = self._discovered_devices.get(address, "SRNE Inverter")

        self._onboarding_context = OnboardingContext(
            device_address=address,
            device_name=device_name,
        )

        _LOGGER.info("Starting onboarding for device: %s (%s)", device_name, address)

        # Transition to welcome screen
        self._state_machine.transition(OnboardingState.WELCOME)
        return await self.async_step_welcome()

    async def async_step_welcome(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Welcome screen after device selection."""
        if user_input is not None:
            self._state_machine.transition(OnboardingState.USER_LEVEL)
            return await self.async_step_user_level()

        # Initialize onboarding context
        address = self._selected_address
        device_name = self._discovered_devices.get(address, "SRNE Inverter")

        self._onboarding_context = OnboardingContext(
            device_address=address,
            device_name=device_name,
        )

        _LOGGER.info("Starting onboarding for device: %s (%s)", device_name, address)

        return self.async_show_form(
            step_id="welcome",
            data_schema=vol.Schema({}),
            description_placeholders={
                "device_name": device_name,
            },
        )

    async def async_step_user_level(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """User level selection screen."""
        if user_input is not None:
            self._onboarding_context.user_level = user_input["user_level"]
            self._onboarding_context.mark_step_complete("user_level")

            _LOGGER.info("User selected level: %s", user_input["user_level"])
            _LOGGER.info("Transitioning to hardware detection step")

            self._state_machine.transition(OnboardingState.HARDWARE_DETECTION)
            return await self.async_step_hardware_detection()

        return self.async_show_form(
            step_id="user_level",
            data_schema=vol.Schema(
                {
                    vol.Required("user_level", default="basic"): vol.In(
                        {
                            "basic": "Basic User - Guided Setup",
                            "advanced": "Advanced User - Full Control",
                            "expert": "Expert Mode - Maximum Control",
                        }
                    ),
                }
            ),
        )

    async def async_step_hardware_detection(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Hardware detection screen with progress."""
        _LOGGER.info("=== HARDWARE DETECTION STEP CALLED ===")
        _LOGGER.info("Device: %s (%s)", self._onboarding_context.device_name, self._onboarding_context.device_address)
        _LOGGER.info("Existing detected_features: %s", self._onboarding_context.detected_features)

        # If we have detection results, complete progress and proceed (background task completed)
        if self._onboarding_context.detected_features:
            _LOGGER.info("Detection complete, showing progress_done")
            return self.async_show_progress_done(next_step_id="detection_review")

        # Start detection in background
        _LOGGER.info("Starting hardware feature detection in background")

        # Create and track the background task
        detection_task = self.hass.async_create_task(self._run_detection())

        return self.async_show_progress(
            step_id="hardware_detection",
            progress_action="detect_hardware",
            progress_task=detection_task,
        )

    async def _run_detection(self) -> None:
        """Run feature detection in background using actual hardware probing."""
        import time

        start_time = time.time()
        detector = FeatureDetector(None)
        device_name = self._onboarding_context.device_name
        results = None
        detection_method = "failed"

        try:
            # Create temporary test coordinator for hardware probing
            _LOGGER.info("Creating temporary connection for hardware feature detection")
            test_coordinator = await self._create_test_coordinator()

            if test_coordinator:
                try:
                    # Create detector with test coordinator
                    detector_with_hw = FeatureDetector(test_coordinator)

                    # Run actual hardware detection
                    _LOGGER.info("Starting hardware register testing for feature detection")
                    results = await detector_with_hw.detect_all_features()
                    detection_method = "hardware_probing"
                    _LOGGER.info(
                        "Hardware detection complete. Detected %d/%d features",
                        sum(results.values()) if results else 0,
                        len(results) if results else 0,
                    )
                finally:
                    # Always cleanup test coordinator connection
                    await self._cleanup_test_coordinator(test_coordinator)

        except Exception as err:
            _LOGGER.warning(
                "Hardware detection failed: %s. Falling back to model inference",
                err,
            )

        # Fallback to model inference if hardware probing failed
        if not results:
            _LOGGER.info("Using model-based inference as fallback for: %s", device_name)
            results = detector.infer_features_from_model(device_name)
            detection_method = "model_inference_fallback"

        duration = time.time() - start_time

        # Store results in context
        self._onboarding_context.detected_features = results
        self._onboarding_context.detection_method = detection_method
        self._onboarding_context.detection_timestamp = time.strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        self._onboarding_context.detection_duration_seconds = duration
        self._onboarding_context.mark_step_complete("hardware_detection")

        _LOGGER.info(
            "Feature detection complete in %.1f seconds using %s. Detected %d/%d features",
            duration,
            detection_method,
            sum(results.values()),
            len(results),
        )

        # Transition to detection review (don't call async_configure, let progress_done handle it)
        self._state_machine.transition(OnboardingState.DETECTION_REVIEW)

    async def _create_test_coordinator(self):
        """Create a temporary coordinator for hardware feature testing.

        Returns:
            A minimal coordinator-like object with async_read_register method,
            or None if creation failed.
        """
        try:
            from ..infrastructure.transport.ble_transport import BLETransport
            from ..infrastructure.transport.connection_manager import ConnectionManager
            from ..application.services.timing_collector import TimingCollector
            from ..infrastructure.protocol.modbus_rtu_protocol import ModbusRTUProtocol
            from ..infrastructure.protocol.modbus_crc16 import ModbusCRC16

            # Create minimal infrastructure for testing
            timing_collector = TimingCollector()
            crc = ModbusCRC16()
            protocol = ModbusRTUProtocol(crc)

            # Create BLE transport (only needs hass and timing_collector)
            transport = BLETransport(
                self.hass,
                timing_collector,
            )

            # Create connection manager
            connection_manager = ConnectionManager(transport)

            # Set address on transport (done separately, not in constructor)
            transport._address = self._onboarding_context.device_address

            # Create minimal test coordinator wrapper
            class TestCoordinator:
                """Minimal coordinator for feature detection."""

                def __init__(self, protocol, transport, connection_manager, address):
                    self._protocol = protocol
                    self._transport = transport
                    self._connection_manager = connection_manager
                    self._address = address

                async def async_read_register(self, register: int) -> int | None:
                    """Read a single register value using protocol."""
                    try:
                        # Ensure connected
                        if not self._transport.is_connected:
                            await self._connection_manager.ensure_connected(self._address)

                        # Build Modbus read request using protocol
                        request_frame = self._protocol.build_read_command(
                            start_address=register,
                            count=1,
                        )

                        # Send request and get response
                        response = await self._transport.send(request_frame)

                        if not response:
                            return None

                        # Decode response using protocol
                        decoded = self._protocol.decode_response(response)

                        # Check for error response (dash pattern or Modbus exception)
                        # Both indicate the register/feature is not supported
                        if "error" in decoded:
                            # Return dash pattern for any error (unsupported or Modbus exception)
                            # This tells the detector the feature is definitively not supported
                            _LOGGER.debug(
                                "Register 0x%04X error response: %s (treating as not supported)",
                                register,
                                decoded,
                            )
                            return 0x2D2D

                        # Return first register value (response uses index keys: {0: value})
                        if decoded and 0 in decoded:
                            return decoded[0]

                        return None

                    except Exception as err:
                        _LOGGER.debug("Test read register 0x%04X error: %s", register, err)
                        return None

                async def async_write_register(
                    self, register: int, value: int, password: int | None = None
                ) -> bool:
                    """Write a single register value using protocol.

                    Args:
                        register: Register address to write
                        value: Value to write
                        password: Optional password for protected registers

                    Returns:
                        True if write succeeded, False otherwise
                    """
                    try:
                        # Ensure connected
                        if not self._transport.is_connected:
                            await self._connection_manager.ensure_connected(self._address)

                        # Authenticate with password if provided
                        if password is not None and password != 0:
                            PASSWORD_REGISTER = 0xE203
                            _LOGGER.info(
                                "Authenticating with password for register 0x%04X",
                                register,
                            )

                            # Write password to password register
                            password_frame = self._protocol.build_write_command(
                                address=PASSWORD_REGISTER,
                                value=password,
                            )

                            password_response = await self._transport.send(password_frame)

                            if not password_response:
                                _LOGGER.error("Password authentication failed - no response")
                                return False

                            # Decode password response
                            password_decoded = self._protocol.decode_response(
                                password_response
                            )

                            if "error" in password_decoded:
                                _LOGGER.error(
                                    "Password authentication failed: %s",
                                    password_decoded,
                                )
                                return False

                            _LOGGER.debug("Password authentication successful")

                        # Build Modbus write request using protocol
                        request_frame = self._protocol.build_write_command(
                            address=register,
                            value=value,
                        )

                        # Send request and get response
                        response = await self._transport.send(request_frame)

                        if not response:
                            return False

                        # Decode response using protocol
                        decoded = self._protocol.decode_response(response)

                        # Check for error response
                        if "error" in decoded:
                            _LOGGER.warning(
                                "Write register 0x%04X = %d failed: %s",
                                register,
                                value,
                                decoded,
                            )
                            return False

                        # Verify the write succeeded (response contains register and value)
                        if decoded and register in decoded:
                            written_value = decoded[register]
                            if written_value == value:
                                return True
                            else:
                                _LOGGER.warning(
                                    "Write verification failed: wrote %d but read back %d",
                                    value,
                                    written_value,
                                )
                                return False

                        return True

                    except Exception as err:
                        _LOGGER.error(
                            "Test write register 0x%04X = %d error: %s",
                            register,
                            value,
                            err,
                        )
                        return False

            test_coord = TestCoordinator(
                protocol,
                transport,
                connection_manager,
                self._onboarding_context.device_address,
            )

            _LOGGER.debug("Test coordinator created successfully")
            return test_coord

        except Exception as err:
            _LOGGER.error("Failed to create test coordinator: %s", err, exc_info=True)
            return None

    async def _cleanup_test_coordinator(self, test_coordinator) -> None:
        """Cleanup test coordinator and disconnect.

        Args:
            test_coordinator: The test coordinator to cleanup
        """
        if not test_coordinator:
            return

        try:
            _LOGGER.debug("Cleaning up test coordinator connection")
            if hasattr(test_coordinator, "_connection_manager"):
                await test_coordinator._connection_manager.disconnect()
            _LOGGER.debug("Test coordinator cleanup complete")
        except Exception as err:
            _LOGGER.warning("Error during test coordinator cleanup: %s", err)

    async def _read_current_settings(self) -> dict[str, Any]:
        """Read current inverter settings.

        Returns:
            Dictionary of current settings with proper defaults if read fails
        """
        # Register map for configuration settings
        SETTING_REGISTERS = {
            "battery_capacity": 0xE002,  # Battery rated capacity (Ah)
            "battery_voltage": 0xE003,  # Battery system voltage (V)
            "output_priority": 0xE204,  # Output priority mode
            "charge_source_priority": 0xE20F,  # Charge source priority
            "discharge_stop_soc": 0xE00F,  # Discharge stop SOC (%)
            "switch_to_ac_soc": 0xE01F,  # Switch to AC SOC (%)
            "switch_to_battery_soc": 0xE020,  # Switch to battery SOC (%)
        }

        settings = {}
        test_coordinator = None

        try:
            # Create temporary coordinator for reading
            test_coordinator = await self._create_test_coordinator()
            if not test_coordinator:
                _LOGGER.warning("Could not create test coordinator, using defaults")
                return self._get_default_settings()

            # Read each register
            for setting_name, register in SETTING_REGISTERS.items():
                try:
                    value = await test_coordinator.async_read_register(register)
                    if value is not None and value != 0x2D2D:
                        settings[setting_name] = value
                        _LOGGER.debug(
                            "Read %s from register 0x%04X = %s",
                            setting_name,
                            register,
                            value,
                        )
                    else:
                        _LOGGER.debug(
                            "Could not read %s (register 0x%04X), using default",
                            setting_name,
                            register,
                        )
                except Exception as err:
                    _LOGGER.debug(
                        "Error reading %s from register 0x%04X: %s",
                        setting_name,
                        register,
                        err,
                    )

        except Exception as err:
            _LOGGER.error("Failed to read current settings: %s", err)

        finally:
            # Cleanup
            if test_coordinator:
                await self._cleanup_test_coordinator(test_coordinator)

        # Merge with defaults for any missing values
        defaults = self._get_default_settings()
        defaults.update(settings)

        return defaults

    def _get_default_settings(self) -> dict[str, Any]:
        """Get default settings as fallback.

        Returns:
            Dictionary of default settings
        """
        return {
            "battery_capacity": 100,  # 100Ah default
            "battery_voltage": 48,  # 48V default
            "output_priority": 2,  # SBU default
            "charge_source_priority": 0,  # PV Priority default
            "discharge_stop_soc": 10,  # 10% default
            "switch_to_ac_soc": 20,  # 20% default
            "switch_to_battery_soc": 80,  # 80% default
        }

    async def _write_settings_to_inverter(self) -> dict[str, Any]:
        """Write configuration settings to inverter.

        Only writes settings that have changed from current values.

        Returns:
            Dictionary with write results: success, applied, failed
        """
        from ..const import COMMAND_DELAY_WRITE

        # Register map for configuration settings
        SETTING_REGISTERS = {
            "battery_capacity": 0xE002,
            "battery_voltage": 0xE003,
            "output_priority": 0xE204,
            "charge_source_priority": 0xE20F,
            "discharge_stop_soc": 0xE00F,
            "switch_to_ac_soc": 0xE01F,
            "switch_to_battery_soc": 0xE020,
        }

        # Protected register range (requires password)
        PROTECTED_REGISTER_START = 0xE000
        PROTECTED_REGISTER_END = 0xE0FF

        applied = []
        failed = []
        test_coordinator = None

        try:
            # Create temporary coordinator for writing
            test_coordinator = await self._create_test_coordinator()
            if not test_coordinator:
                return {
                    "success": False,
                    "applied": [],
                    "failed": ["Could not create coordinator"],
                }

            # Get password from settings
            password = self._onboarding_context.custom_settings.get(
                "inverter_password", 1111
            )

            # Get current values to compare
            current = getattr(self, "_current_values", self._get_default_settings())

            # Write each changed setting
            for setting_name, new_value in self._onboarding_context.custom_settings.items():
                # Skip if not a register setting
                if setting_name not in SETTING_REGISTERS:
                    continue

                # Convert to int for comparison
                try:
                    new_value_int = int(new_value)
                    current_value = current.get(setting_name)

                    # Skip if value hasn't changed
                    if current_value == new_value_int:
                        _LOGGER.debug(
                            "Skipping %s - value unchanged (%s)",
                            setting_name,
                            new_value_int,
                        )
                        continue

                    # Write the setting
                    register = SETTING_REGISTERS[setting_name]
                    _LOGGER.info(
                        "Writing %s = %s to register 0x%04X (was %s)",
                        setting_name,
                        new_value_int,
                        register,
                        current_value,
                    )

                    # Check if register is protected and needs authentication
                    is_protected = (
                        PROTECTED_REGISTER_START <= register <= PROTECTED_REGISTER_END
                    )

                    # Write to inverter (with password if protected)
                    success = await test_coordinator.async_write_register(
                        register, new_value_int, password if is_protected else None
                    )

                    if success:
                        applied.append(setting_name)
                        _LOGGER.info(
                            "Successfully wrote %s = %d to register 0x%04X",
                            setting_name,
                            new_value_int,
                            register,
                        )
                    else:
                        failed.append((setting_name, "Write failed"))
                        _LOGGER.error(
                            "Failed to write %s = %d to register 0x%04X",
                            setting_name,
                            new_value_int,
                            register,
                        )

                    # Add delay between writes
                    await asyncio.sleep(COMMAND_DELAY_WRITE)

                except (ValueError, TypeError) as err:
                    _LOGGER.error(
                        "Failed to write %s: invalid value %s - %s",
                        setting_name,
                        new_value,
                        err,
                    )
                    failed.append((setting_name, str(err)))

        except Exception as err:
            _LOGGER.error("Failed to write settings: %s", err)
            failed.append(("general", str(err)))

        finally:
            # Cleanup
            if test_coordinator:
                await self._cleanup_test_coordinator(test_coordinator)

        return {
            "success": len(failed) == 0,
            "applied": applied,
            "failed": failed,
        }

    async def async_step_detection_review(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Review detection results."""
        if user_input is not None:
            # Store any overrides (for advanced/expert users)
            if "overrides" in user_input:
                self._onboarding_context.user_overrides = user_input["overrides"]

            self._onboarding_context.mark_step_complete("detection_review")

            _LOGGER.info(
                "Detection review complete. User level: %s, Features: %s",
                self._onboarding_context.user_level,
                self._onboarding_context.active_features,
            )

            # Route based on user level
            if self._onboarding_context.user_level == "basic":
                # Basic users: preset selection
                self._state_machine.transition(OnboardingState.PRESET_SELECTION)
                return await self.async_step_preset_selection()
            else:
                # Advanced/expert users: manual configuration
                self._state_machine.transition(OnboardingState.MANUAL_CONFIG)
                return await self.async_step_manual_config()

        # Build display based on user level
        if self._onboarding_context.user_level == "basic":
            # Simple display for basic users
            return self.async_show_form(
                step_id="detection_review",
                data_schema=vol.Schema({}),
                description_placeholders={
                    "detected_features": self._format_features_basic(),
                },
            )
        else:
            # Advanced/expert: show with override capability
            return self.async_show_form(
                step_id="detection_review",
                data_schema=self._build_override_schema(),
                description_placeholders={
                    "detected_features": self._format_features_advanced(),
                },
            )

    def _format_features_basic(self) -> str:
        """Format features for basic users."""
        if not self._onboarding_context.detected_features:
            return "⚠️ Detection did not complete. Using safe defaults."

        lines = ["Your inverter has the following capabilities:\n"]
        for feature, detected in self._onboarding_context.detected_features.items():
            status = "✓" if detected else "✗"
            name = feature.replace("_", " ").title()
            lines.append(f"{status} {name}")
        return "\n".join(lines)

    def _format_features_advanced(self) -> str:
        """Format features with technical details for advanced users."""
        if not self._onboarding_context.detected_features:
            return "⚠️ Detection did not complete. You can configure features manually."

        from ..onboarding.detection import FEATURE_TEST_REGISTERS

        lines = ["Auto-detected features (you can override below):\n"]
        for feature, detected in self._onboarding_context.detected_features.items():
            status = "✓" if detected else "✗"
            name = feature.replace("_", " ").title()
            register = FEATURE_TEST_REGISTERS.get(feature, 0)
            lines.append(f"{status} {name} (register 0x{register:04X})")
        return "\n".join(lines)

    def _build_override_schema(self) -> vol.Schema:
        """Build schema with override checkboxes for each feature."""
        if not self._onboarding_context.detected_features:
            return vol.Schema({})

        schema_dict = {}
        for feature, detected in self._onboarding_context.detected_features.items():
            # Format feature name for display
            feature_name = feature.replace("_", " ").title()

            # Use selector with proper name for display
            schema_dict[vol.Optional(f"override_{feature}", default=detected)] = (
                selector.BooleanSelector(
                    selector.BooleanSelectorConfig()
                )
            )
        return vol.Schema(schema_dict)

    async def async_step_preset_selection(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Preset selection for basic users."""
        if user_input is not None:
            preset_key = user_input["preset"]

            # Store selected preset
            self._onboarding_context.selected_preset = preset_key
            self._onboarding_context.mark_step_complete("preset_selection")

            # Check if user chose to skip preset selection
            if preset_key == "skip":
                # Don't apply any preset - user will use current/default inverter settings
                _LOGGER.info("User skipped preset selection - using current inverter settings")
            else:
                # Apply preset settings
                preset_settings = CONFIGURATION_PRESETS[preset_key]["settings"]
                self._onboarding_context.custom_settings = preset_settings.copy()
                _LOGGER.info("User selected preset: %s", preset_key)

            # Proceed to validation
            self._state_machine.transition(OnboardingState.VALIDATION)
            return await self.async_step_validation()

        # Filter presets based on detected features
        available_presets = self._filter_presets_by_features()

        # Build preset selection form - add skip option first
        preset_options = [
            selector.SelectOptionDict(
                value="skip",
                label="Skip - Use Current Inverter Settings"
            ),
        ]

        # Add available presets
        preset_options.extend([
            selector.SelectOptionDict(
                value=key, label=f"{preset['name']} - {preset['description']}"
            )
            for key, preset in available_presets.items()
        ])

        return self.async_show_form(
            step_id="preset_selection",
            data_schema=vol.Schema(
                {
                    vol.Required("preset"): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=preset_options,
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    ),
                }
            ),
            description_placeholders={
                "preset_count": str(len(available_presets)),
            },
        )

    def _filter_presets_by_features(self) -> dict[str, dict]:
        """Filter presets based on detected features."""
        available = {}
        active_features = self._onboarding_context.active_features

        for key, preset in CONFIGURATION_PRESETS.items():
            # Check if preset requirements are met
            required_features = preset.get("required_features", [])

            if all(active_features.get(f, False) for f in required_features):
                available[key] = preset

        # Always include at least one preset (off-grid solar has no requirements)
        if not available:
            available["off_grid_solar"] = CONFIGURATION_PRESETS["off_grid_solar"]

        return available

    async def async_step_manual_config(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manual configuration for advanced/expert users."""
        if user_input is not None:
            # Store settings
            self._onboarding_context.custom_settings.update(user_input)
            self._onboarding_context.mark_step_complete("manual_config")

            _LOGGER.info(
                "User completed manual config. Settings: %s",
                self._onboarding_context.custom_settings,
            )

            # Proceed to validation
            self._state_machine.transition(OnboardingState.VALIDATION)
            return await self.async_step_validation()

        # Read current values from inverter if not already loaded
        if not hasattr(self, "_current_values"):
            _LOGGER.info("Reading current settings from inverter...")
            self._current_values = await self._read_current_settings()
            _LOGGER.debug("Current settings: %s", self._current_values)

        # Build dynamic form based on user level with current values
        schema = self._build_manual_config_schema()

        return self.async_show_form(
            step_id="manual_config",
            data_schema=schema,
            description_placeholders={
                "user_level": self._onboarding_context.user_level,
            },
        )

    def _build_manual_config_schema(self) -> vol.Schema:
        """Build configuration schema based on user level and features."""
        schema_dict = {}
        user_level = self._onboarding_context.user_level

        # Get current values (or defaults if not loaded)
        current = getattr(self, "_current_values", self._get_default_settings())

        # Battery settings (always shown)
        schema_dict[
            vol.Required(
                "battery_capacity", default=current.get("battery_capacity", 100)
            )
        ] = vol.All(vol.Coerce(int), vol.Range(min=10, max=400))

        schema_dict[
            vol.Required(
                "battery_voltage", default=str(current.get("battery_voltage", 48))
            )
        ] = vol.In(["12", "24", "36", "48"])

        # Output priority
        schema_dict[
            vol.Required(
                "output_priority", default=str(current.get("output_priority", 2))
            )
        ] = selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=[
                    {"value": "0", "label": "Solar First"},
                    {"value": "1", "label": "Mains First"},
                    {"value": "2", "label": "SBU (Solar-Battery-Utility)"},
                ],
                mode=selector.SelectSelectorMode.DROPDOWN,
            )
        )

        # Charge source priority
        schema_dict[
            vol.Required(
                "charge_source_priority",
                default=str(current.get("charge_source_priority", 0)),
            )
        ] = selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=[
                    {"value": "0", "label": "PV Priority (AC Backup)"},
                    {"value": "1", "label": "AC Priority"},
                    {"value": "2", "label": "Hybrid Mode"},
                    {"value": "3", "label": "PV Only"},
                ],
                mode=selector.SelectSelectorMode.DROPDOWN,
            )
        )

        # SOC thresholds (advanced/expert)
        if user_level in ["advanced", "expert"]:
            schema_dict[
                vol.Optional(
                    "discharge_stop_soc", default=current.get("discharge_stop_soc", 20)
                )
            ] = vol.All(vol.Coerce(int), vol.Range(min=0, max=100))

            schema_dict[
                vol.Optional(
                    "switch_to_ac_soc", default=current.get("switch_to_ac_soc", 10)
                )
            ] = vol.All(vol.Coerce(int), vol.Range(min=0, max=100))

            schema_dict[
                vol.Optional(
                    "switch_to_battery_soc",
                    default=current.get("switch_to_battery_soc", 80),
                )
            ] = vol.All(vol.Coerce(int), vol.Range(min=1, max=100))

        # Password for write operations (advanced/expert)
        if user_level in ["advanced", "expert"]:
            schema_dict[
                vol.Optional("inverter_password", default=1111)
            ] = vol.All(vol.Coerce(int), vol.Range(min=0, max=9999999))

        # Expert-only settings
        if user_level == "expert":
            schema_dict[vol.Optional("enable_diagnostic_sensors", default=True)] = (
                cv.boolean
            )
            schema_dict[vol.Optional("log_modbus_traffic", default=False)] = cv.boolean

        return vol.Schema(schema_dict)

    async def async_step_validation(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Validate configuration settings."""
        # Run validation
        validation_results = self._validate_settings()

        if validation_results["has_errors"]:
            # Format error messages for display
            error_messages = "\n\n".join(
                f"• {error}" for error in validation_results["errors"]
            )

            _LOGGER.warning(
                "Validation failed with %d errors: %s",
                len(validation_results["errors"]),
                validation_results["errors"],
            )

            # Store validation errors for display
            errors_dict = {"base": "validation_failed"}

            # Return to previous step with errors displayed
            if self._onboarding_context.user_level == "basic":
                # Basic users: return to preset selection
                available_presets = self._filter_presets_by_features()
                preset_options = [
                    selector.SelectOptionDict(
                        value=key, label=f"{preset['name']} - {preset['description']}"
                    )
                    for key, preset in available_presets.items()
                ]

                return self.async_show_form(
                    step_id="preset_selection",
                    data_schema=vol.Schema(
                        {
                            vol.Required("preset"): selector.SelectSelector(
                                selector.SelectSelectorConfig(
                                    options=preset_options,
                                    mode=selector.SelectSelectorMode.DROPDOWN,
                                )
                            ),
                        }
                    ),
                    errors=errors_dict,
                    description_placeholders={
                        "preset_count": str(len(available_presets)),
                        "error_details": error_messages,
                    },
                )
            else:
                # Advanced/expert users: return to manual config
                schema = self._build_manual_config_schema()

                return self.async_show_form(
                    step_id="manual_config",
                    data_schema=schema,
                    errors=errors_dict,
                    description_placeholders={
                        "user_level": self._onboarding_context.user_level,
                        "error_details": error_messages,
                    },
                )

        # Validation passed - proceed to review
        self._onboarding_context.validation_passed = True
        self._onboarding_context.validation_warnings = validation_results.get(
            "warnings", []
        )
        self._onboarding_context.mark_step_complete("validation")

        _LOGGER.info(
            "Validation passed with %d warnings: %s",
            len(validation_results["warnings"]),
            validation_results["warnings"],
        )

        self._state_machine.transition(OnboardingState.REVIEW)
        return await self.async_step_review()

    def _validate_settings(self) -> dict[str, Any]:
        """Validate configuration settings with enhanced error messages.

        Returns:
            Dict with keys: has_errors, errors, warnings
        """
        errors = []
        warnings = []
        settings = self._onboarding_context.custom_settings

        # If user chose to skip preset (use current settings), don't show warnings
        # Only validate for errors in case settings are truly invalid
        skip_warnings = (
            self._onboarding_context.selected_preset == "skip"
        )

        # Validate SOC order if present
        discharge_stop = settings.get("discharge_stop_soc", 0)
        switch_ac = settings.get("switch_to_ac_soc", 0)
        switch_battery = settings.get("switch_to_battery_soc", 100)

        if discharge_stop and switch_ac and discharge_stop >= switch_ac:
            errors.append(
                f"Discharge stop SOC ({discharge_stop}%) must be less than "
                f"switch to AC SOC ({switch_ac}%). "
                "Recommended: discharge stop at 20%, switch to AC at 30%."
            )

        if switch_ac and switch_battery and switch_ac >= switch_battery:
            errors.append(
                f"Switch to AC SOC ({switch_ac}%) must be less than "
                f"switch to battery SOC ({switch_battery}%). "
                "Recommended: switch to AC at 30%, switch to battery at 80%."
            )

        # Validate battery voltage
        battery_voltage = settings.get("battery_voltage")
        if battery_voltage and battery_voltage not in ["12", "24", "36", "48"]:
            errors.append(
                f"Battery voltage '{battery_voltage}' is invalid. "
                "Must be one of: 12V, 24V, 36V, or 48V."
            )

        # Battery capacity vs charge current validation
        battery_capacity = settings.get("battery_capacity")
        max_charge = settings.get("max_charge_current")

        if battery_capacity and max_charge and not skip_warnings:
            # Recommend max charge current <= 0.5C (C/2)
            safe_max = battery_capacity * 0.5
            if max_charge > safe_max:
                warnings.append(
                    f"Charge current ({max_charge}A) exceeds recommended 0.5C rate "
                    f"for {battery_capacity}Ah battery. "
                    f"Maximum recommended: {safe_max:.1f}A. "
                    "Higher rates may reduce battery lifespan."
                )

        # Note: AC input (charging from grid) is a basic feature of hybrid inverters
        # and works independently of grid-tie (export) capability.
        # The grid_tie feature specifically refers to feeding power BACK to the grid,
        # not consuming power FROM the grid.
        # Therefore, we don't need to warn about AC-related settings just because
        # grid_tie is not detected.

        # Battery voltage consistency check
        if battery_voltage and not skip_warnings:
            device_name = self._onboarding_context.device_name
            # Check common voltage indicators in device name
            if "48V" in device_name.upper() and battery_voltage != "48":
                warnings.append(
                    f"Device name suggests 48V system, but {battery_voltage}V configured. "
                    "Please verify this is correct for your setup."
                )
            elif "24V" in device_name.upper() and battery_voltage != "24":
                warnings.append(
                    f"Device name suggests 24V system, but {battery_voltage}V configured. "
                    "Please verify this is correct for your setup."
                )

        # Low discharge SOC warning
        if discharge_stop and discharge_stop < 10 and not skip_warnings:
            warnings.append(
                f"Discharge stop SOC set to {discharge_stop}%, which is below 10%. "
                "This may significantly reduce battery lifespan. "
                "Consider setting to at least 20% for better battery health."
            )

        # High switch to battery SOC warning
        if switch_battery and switch_battery > 90 and not skip_warnings:
            warnings.append(
                f"Switch to battery SOC set to {switch_battery}%, which is above 90%. "
                "This may cause frequent switching between AC and battery. "
                "Consider setting to 80% for more stable operation."
            )

        return {
            "has_errors": len(errors) > 0,
            "errors": errors,
            "warnings": warnings,
        }

    async def async_step_review(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Review and confirm configuration before writing."""
        if user_input is not None:
            # Write changed settings to inverter before creating entry
            if self._onboarding_context.custom_settings:
                _LOGGER.info("Writing configuration changes to inverter...")
                write_result = await self._write_settings_to_inverter()

                if not write_result["success"]:
                    _LOGGER.warning(
                        "Some settings failed to write: %s",
                        write_result["failed"],
                    )
                    # Continue anyway - settings are stored in config entry
                    # and can be retried later via options flow
                else:
                    _LOGGER.info(
                        "Successfully wrote %d settings to inverter",
                        len(write_result["applied"]),
                    )

            # User confirmed - create entry
            self._onboarding_context.mark_completed()

            _LOGGER.info(
                "Onboarding complete. User level: %s, Duration: %.1f seconds",
                self._onboarding_context.user_level,
                self._onboarding_context.total_duration or 0,
            )

            # Log configuration summary for troubleshooting
            _LOGGER.info(
                "=== CREATING CONFIG ENTRY ==="
            )
            _LOGGER.info(
                "detected_features (%d features): %s",
                len(self._onboarding_context.detected_features),
                self._onboarding_context.detected_features,
            )
            _LOGGER.info(
                "detection_method: %s",
                self._onboarding_context.detection_method,
            )
            _LOGGER.debug(
                "Final configuration: detected_features=%s, settings=%s",
                self._onboarding_context.detected_features,
                self._onboarding_context.custom_settings,
            )

            # Extract password from settings (store in data, not options)
            password = self._onboarding_context.custom_settings.get(
                "inverter_password", 1111
            )

            # Remove password from options (will be in data instead)
            options = {
                k: v
                for k, v in self._onboarding_context.custom_settings.items()
                if k != "inverter_password"
            }

            # Create entry with complete metadata
            return self.async_create_entry(
                title=self._onboarding_context.device_name,
                data={
                    CONF_ADDRESS: self._onboarding_context.device_address,
                    "user_level": self._onboarding_context.user_level,
                    "detected_features": self._onboarding_context.detected_features,
                    "detection_method": self._onboarding_context.detection_method,
                    "detection_timestamp": self._onboarding_context.detection_timestamp,
                    "onboarding_completed": True,
                    "onboarding_duration": self._onboarding_context.total_duration,
                    "inverter_password": password,
                },
                options=options,
            )

        # Build review display
        review_text = self._format_settings_review()
        warnings_text = (
            "\n".join(
                f"⚠️ {warning}"
                for warning in self._onboarding_context.validation_warnings
            )
            if self._onboarding_context.validation_warnings
            else "✓ No warnings"
        )

        return self.async_show_form(
            step_id="review",
            data_schema=vol.Schema({}),
            description_placeholders={
                "review_text": review_text,
                "warnings": warnings_text,
            },
        )

    def _format_settings_review(self) -> str:
        """Format settings for review display."""
        lines = ["Configuration Summary:\n"]

        settings = self._onboarding_context.custom_settings

        if self._onboarding_context.selected_preset:
            if self._onboarding_context.selected_preset == "skip":
                lines.append("Preset: None (using current inverter settings)\n")
            else:
                preset = CONFIGURATION_PRESETS.get(
                    self._onboarding_context.selected_preset, {}
                )
                lines.append(f"Preset: {preset.get('name', 'Unknown')}\n")

        for key, value in settings.items():
            label = key.replace("_", " ").title()
            lines.append(f"  {label}: {value}")

        return "\n".join(lines)

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Get the options flow handler."""
        return get_options_flow_handler()
