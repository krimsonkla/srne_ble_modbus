"""Tests for availability checker service."""

import pytest
from unittest.mock import Mock

from custom_components.srne_inverter.application.services.availability_checker import (
    AvailabilityChecker,
)


class TestAvailabilityChecker:
    """Test availability checker service."""

    def test_available_when_connected_and_data_present(self):
        """Test entity is available when connected with data."""
        coordinator = Mock()
        coordinator.data = {"connected": True, "voltage": 12.5}
        coordinator.is_entity_unavailable = Mock(return_value=False)
        coordinator.is_register_failed = Mock(return_value=False)

        checker = AvailabilityChecker(coordinator)

        assert checker.is_available(
            entity_id="sensor.voltage",
            register_name="battery_voltage",
            source_type="register",
        )

    def test_unavailable_when_not_connected(self):
        """Test entity unavailable when not connected."""
        coordinator = Mock()
        coordinator.data = {"connected": False}

        checker = AvailabilityChecker(coordinator)

        assert not checker.is_available(entity_id="sensor.voltage")

    def test_unavailable_when_no_data(self):
        """Test entity unavailable when no data."""
        coordinator = Mock()
        coordinator.data = None

        checker = AvailabilityChecker(coordinator)

        assert not checker.is_available(entity_id="sensor.voltage")

    def test_unavailable_when_register_failed(self):
        """Test entity unavailable when register failed."""
        coordinator = Mock()
        coordinator.data = {"connected": True}
        coordinator.is_entity_unavailable = Mock(return_value=False)
        coordinator.is_register_failed = Mock(return_value=True)

        checker = AvailabilityChecker(coordinator)

        assert not checker.is_available(
            entity_id="sensor.voltage",
            register_name="battery_voltage",
        )

    def test_calculated_sensor_dependencies(self):
        """Test calculated sensor with dependencies."""
        coordinator = Mock()
        coordinator.data = {
            "connected": True,
            "voltage": 12.5,
            "current": 5.0,
        }
        coordinator.is_entity_unavailable = Mock(return_value=False)

        checker = AvailabilityChecker(coordinator)

        # All dependencies present
        assert checker.is_available(
            entity_id="sensor.power",
            source_type="calculated",
            depends_on=["voltage", "current"],
        )

    def test_calculated_sensor_missing_dependency(self):
        """Test calculated sensor with missing dependency."""
        coordinator = Mock()
        coordinator.data = {
            "connected": True,
            "voltage": 12.5,
            # Missing 'current'
        }
        coordinator.is_entity_unavailable = Mock(return_value=False)

        checker = AvailabilityChecker(coordinator)

        assert not checker.is_available(
            entity_id="sensor.power",
            source_type="calculated",
            depends_on=["voltage", "current"],
        )

    def test_check_dependencies_all_present(self):
        """Test dependency checking when all present."""
        coordinator = Mock()
        coordinator.data = {"voltage": 12.5, "current": 5.0}

        checker = AvailabilityChecker(coordinator)

        assert checker.check_dependencies(["voltage", "current"])

    def test_check_dependencies_missing(self):
        """Test dependency checking when some missing."""
        coordinator = Mock()
        coordinator.data = {"voltage": 12.5}

        checker = AvailabilityChecker(coordinator)

        assert not checker.check_dependencies(["voltage", "current"])

    def test_check_dependencies_empty_list(self):
        """Test dependency checking with empty list."""
        coordinator = Mock()
        coordinator.data = {}

        checker = AvailabilityChecker(coordinator)

        # Empty dependency list should return True
        assert checker.check_dependencies([])

    def test_check_dependencies_no_data(self):
        """Test dependency checking when no data available."""
        coordinator = Mock()
        coordinator.data = None

        checker = AvailabilityChecker(coordinator)

        assert not checker.check_dependencies(["voltage"])

    def test_entity_unavailable_method_not_available(self):
        """Test when coordinator doesn't have is_entity_unavailable method."""
        coordinator = Mock()
        coordinator.data = {"connected": True}
        # Don't set is_entity_unavailable method
        delattr(coordinator, "is_entity_unavailable")

        checker = AvailabilityChecker(coordinator)

        # Should still work without the method
        assert checker.is_available(entity_id="sensor.voltage")

    def test_register_failed_method_not_available(self):
        """Test when coordinator doesn't have is_register_failed method."""
        coordinator = Mock()
        coordinator.data = {"connected": True}
        coordinator.is_entity_unavailable = Mock(return_value=False)
        # Don't set is_register_failed method
        delattr(coordinator, "is_register_failed")

        checker = AvailabilityChecker(coordinator)

        # Should still work without the method
        assert checker.is_available(
            entity_id="sensor.voltage",
            register_name="battery_voltage",
        )

    def test_entity_marked_unavailable(self):
        """Test entity specifically marked as unavailable."""
        coordinator = Mock()
        coordinator.data = {"connected": True}
        coordinator.is_entity_unavailable = Mock(return_value=True)

        checker = AvailabilityChecker(coordinator)

        assert not checker.is_available(entity_id="sensor.voltage")
        coordinator.is_entity_unavailable.assert_called_once_with("sensor.voltage")

    def test_calculated_with_no_dependencies(self):
        """Test calculated sensor with no dependencies specified."""
        coordinator = Mock()
        coordinator.data = {"connected": True}
        coordinator.is_entity_unavailable = Mock(return_value=False)

        checker = AvailabilityChecker(coordinator)

        # Should be available if no dependencies specified
        assert checker.is_available(
            entity_id="sensor.calculated",
            source_type="calculated",
            depends_on=None,
        )
