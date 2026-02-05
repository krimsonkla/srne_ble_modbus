"""Tests for DI Container."""

import pytest
from unittest.mock import Mock
from custom_components.srne_inverter.presentation.container import (
    DIContainer,
    create_container,
    validate_container,
)


@pytest.fixture
def mock_hass():
    """Create mock Home Assistant instance."""
    hass = Mock()
    hass.data = {}
    return hass


@pytest.fixture
def mock_entry():
    """Create mock config entry."""
    entry = Mock()
    entry.entry_id = "test_entry_id"
    entry.data = {"address": "AA:BB:CC:DD:EE:FF"}
    return entry


@pytest.fixture
def test_config():
    """Create test configuration."""
    return {
        "address": "AA:BB:CC:DD:EE:FF",
        "name": "Test Inverter",
        "model": "HF2420",
    }


class TestDIContainerCreation:
    """Test DIContainer creation."""

    def test_create_empty_container(self, mock_hass, mock_entry, test_config):
        """Test creating empty container with core dependencies."""
        container = DIContainer(
            hass=mock_hass,
            entry=mock_entry,
            config=test_config,
        )
        assert container.hass == mock_hass
        assert container.entry == mock_entry
        assert container.config == test_config

    def test_create_container_with_factory(self, mock_hass, mock_entry, test_config):
        """Test creating container via factory function."""
        container = create_container(mock_hass, mock_entry, test_config)
        assert container is not None
        assert container.hass == mock_hass
        assert container.entry == mock_entry
        assert container.config == test_config

    def test_container_has_coordinator(self, mock_hass, mock_entry, test_config):
        """Test that container creates coordinator."""
        container = create_container(mock_hass, mock_entry, test_config)
        # Coordinator should be created (even if placeholder in Phase 1)
        assert container.coordinator is not None


class TestDIContainerDependencies:
    """Test container dependency wiring."""

    def test_infrastructure_layer_dependencies(
        self, mock_hass, mock_entry, test_config
    ):
        """Test that infrastructure layer dependencies are set."""
        container = create_container(mock_hass, mock_entry, test_config)

        # Phase 1: These will be None (placeholders), but fields exist
        assert hasattr(container, "protocol")
        assert hasattr(container, "transport")
        assert hasattr(container, "connection_manager")
        assert hasattr(container, "failed_register_repo")
        assert hasattr(container, "crc")

    def test_application_layer_dependencies(self, mock_hass, mock_entry, test_config):
        """Test that application layer dependencies are set."""
        container = create_container(mock_hass, mock_entry, test_config)

        # Phase 1: These will be None (placeholders), but fields exist
        assert hasattr(container, "refresh_data_use_case")
        assert hasattr(container, "write_register_use_case")
        assert hasattr(container, "batch_builder_service")
        assert hasattr(container, "register_mapper_service")
        assert hasattr(container, "transaction_manager_service")

    def test_presentation_layer_dependencies(self, mock_hass, mock_entry, test_config):
        """Test that presentation layer dependencies are set."""
        container = create_container(mock_hass, mock_entry, test_config)

        assert hasattr(container, "coordinator")
        assert container.coordinator is not None  # Must have coordinator


class TestContainerValidation:
    """Test container validation."""

    def test_validate_complete_container(self, mock_hass, mock_entry, test_config):
        """Test validating complete container."""
        container = create_container(mock_hass, mock_entry, test_config)
        assert validate_container(container) is True

    def test_validate_missing_hass_raises_error(self, mock_entry, test_config):
        """Test that missing hass raises error."""
        container = DIContainer(
            hass=None,  # Missing!
            entry=mock_entry,
            config=test_config,
        )
        with pytest.raises(ValueError, match="Missing critical dependencies"):
            validate_container(container)

    def test_validate_missing_coordinator_raises_error(
        self, mock_hass, mock_entry, test_config
    ):
        """Test that missing coordinator raises error."""
        container = DIContainer(
            hass=mock_hass,
            entry=mock_entry,
            config=test_config,
            coordinator=None,  # Missing!
        )
        with pytest.raises(ValueError, match="Missing critical dependencies"):
            validate_container(container)


class TestContainerIntegration:
    """Test container integration with existing code."""

    def test_container_creates_existing_coordinator(
        self, mock_hass, mock_entry, test_config
    ):
        """Test that container can create existing coordinator type."""
        container = create_container(mock_hass, mock_entry, test_config)

        # Should create SRNEDataUpdateCoordinator for backward compatibility
        assert container.coordinator is not None
        # Check it's the right type
        from custom_components.srne_inverter.coordinator import (
            SRNEDataUpdateCoordinator,
        )

        assert isinstance(container.coordinator, SRNEDataUpdateCoordinator)

    def test_container_can_be_used_in_existing_setup(
        self, mock_hass, mock_entry, test_config
    ):
        """Test that container can replace existing setup pattern."""
        # This simulates how __init__.py currently sets up the coordinator
        container = create_container(mock_hass, mock_entry, test_config)

        # Should be able to get coordinator like before
        coordinator = container.coordinator
        assert coordinator is not None

        # Should be able to store in hass.data like before
        if "srne_inverter" not in mock_hass.data:
            mock_hass.data["srne_inverter"] = {}
        mock_hass.data["srne_inverter"][mock_entry.entry_id] = {
            "coordinator": coordinator,
            "config": test_config,
        }

        # Verify it was stored correctly
        assert (
            mock_hass.data["srne_inverter"][mock_entry.entry_id]["coordinator"]
            == coordinator
        )


class TestContainerLifecycle:
    """Test container lifecycle management."""

    def test_container_is_created_once_per_entry(
        self, mock_hass, mock_entry, test_config
    ):
        """Test that each entry gets its own container."""
        container1 = create_container(mock_hass, mock_entry, test_config)
        container2 = create_container(mock_hass, mock_entry, test_config)

        # Different container instances
        assert container1 is not container2
        # But same entry
        assert container1.entry == container2.entry

    def test_container_dependencies_are_isolated(self, mock_hass, test_config):
        """Test that multiple containers have isolated dependencies."""
        entry1 = Mock()
        entry1.entry_id = "entry1"
        entry2 = Mock()
        entry2.entry_id = "entry2"

        container1 = create_container(mock_hass, entry1, test_config)
        container2 = create_container(mock_hass, entry2, test_config)

        # Different coordinators
        assert container1.coordinator is not container2.coordinator
        # Different entries
        assert container1.entry != container2.entry


class TestContainerTypeHints:
    """Test that container maintains type hints."""

    def test_container_fields_have_types(self):
        """Test that DIContainer fields have proper type hints."""
        from typing import get_type_hints

        hints = get_type_hints(DIContainer)

        # Core fields should have types
        assert "hass" in hints
        assert "entry" in hints
        assert "config" in hints

        # Infrastructure fields should have types
        assert "protocol" in hints
        assert "transport" in hints
        assert "coordinator" in hints


class TestContainerDocumentation:
    """Test that container is well-documented."""

    def test_container_has_docstring(self):
        """Test that DIContainer has docstring."""
        assert DIContainer.__doc__ is not None
        assert len(DIContainer.__doc__) > 100

    def test_create_container_has_docstring(self):
        """Test that create_container has docstring."""
        assert create_container.__doc__ is not None
        assert "factory" in create_container.__doc__.lower()

    def test_validate_container_has_docstring(self):
        """Test that validate_container has docstring."""
        assert validate_container.__doc__ is not None
        assert "validate" in validate_container.__doc__.lower()
