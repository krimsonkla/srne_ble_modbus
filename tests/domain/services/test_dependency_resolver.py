"""Tests for dependency resolver."""

import pytest

from custom_components.srne_inverter.domain.services.dependency_resolver import (
    DependencyResolver,
)


class TestDependencyResolver:
    """Test dependency resolver service."""

    def test_build_from_config_simple(self):
        """Test building from simple configuration."""
        config = {
            "sensors": [
                {
                    "entity_id": "power",
                    "source_type": "calculated",
                    "depends_on": ["voltage", "current"],
                }
            ]
        }

        resolver = DependencyResolver()
        resolver.build_from_config(config)

        assert resolver.get_dependents("voltage") == ["power"]
        assert resolver.get_dependents("current") == ["power"]
        assert resolver.get_dependencies("power") == {"voltage", "current"}

    def test_build_from_config_multiple_entities(self):
        """Test with multiple calculated entities."""
        config = {
            "sensors": [
                {
                    "entity_id": "power",
                    "source_type": "calculated",
                    "depends_on": ["voltage", "current"],
                },
                {
                    "entity_id": "energy",
                    "source_type": "calculated",
                    "depends_on": ["power"],
                },
            ]
        }

        resolver = DependencyResolver()
        resolver.build_from_config(config)

        assert resolver.get_dependents("voltage") == ["power"]
        assert resolver.get_dependents("power") == ["energy"]
        assert resolver.get_dependencies("energy") == {"power"}

    def test_ignores_non_calculated_sensors(self):
        """Test that non-calculated sensors are ignored."""
        config = {
            "sensors": [
                {
                    "entity_id": "voltage",
                    "source_type": "register",
                },
                {
                    "entity_id": "power",
                    "source_type": "calculated",
                    "depends_on": ["voltage"],
                },
            ]
        }

        resolver = DependencyResolver()
        resolver.build_from_config(config)

        # voltage is not in reverse map (it's a register sensor)
        assert not resolver.has_dependencies("voltage")
        # power is in reverse map
        assert resolver.has_dependencies("power")

    def test_get_unavailable_entities(self):
        """Test getting unavailable entities."""
        config = {
            "sensors": [
                {
                    "entity_id": "power",
                    "source_type": "calculated",
                    "depends_on": ["voltage", "current"],
                }
            ]
        }

        resolver = DependencyResolver()
        resolver.build_from_config(config)

        # Only voltage available
        available = {"voltage"}
        unavailable = resolver.get_unavailable_entities(available)
        assert "power" in unavailable

        # Both available
        available = {"voltage", "current"}
        unavailable = resolver.get_unavailable_entities(available)
        assert "power" not in unavailable

    def test_clear(self):
        """Test clearing dependency data."""
        config = {
            "sensors": [
                {
                    "entity_id": "power",
                    "source_type": "calculated",
                    "depends_on": ["voltage"],
                }
            ]
        }

        resolver = DependencyResolver()
        resolver.build_from_config(config)

        assert resolver.get_dependency_count() == 1

        resolver.clear()
        assert resolver.get_dependency_count() == 0

    def test_get_dependency_count(self):
        """Test getting dependency count."""
        config = {
            "sensors": [
                {
                    "entity_id": "power",
                    "source_type": "calculated",
                    "depends_on": ["voltage", "current"],
                },
                {
                    "entity_id": "energy",
                    "source_type": "calculated",
                    "depends_on": ["power"],
                },
            ]
        }

        resolver = DependencyResolver()
        resolver.build_from_config(config)

        assert resolver.get_dependency_count() == 2  # power and energy

    def test_empty_config(self):
        """Test with empty configuration."""
        config = {"sensors": []}

        resolver = DependencyResolver()
        resolver.build_from_config(config)

        assert resolver.get_dependency_count() == 0

    def test_missing_depends_on(self):
        """Test sensor with missing depends_on field."""
        config = {
            "sensors": [
                {
                    "entity_id": "power",
                    "source_type": "calculated",
                    # Missing depends_on
                }
            ]
        }

        resolver = DependencyResolver()
        resolver.build_from_config(config)

        # Should be ignored
        assert resolver.get_dependency_count() == 0

    def test_empty_depends_on(self):
        """Test sensor with empty depends_on list."""
        config = {
            "sensors": [
                {
                    "entity_id": "power",
                    "source_type": "calculated",
                    "depends_on": [],
                }
            ]
        }

        resolver = DependencyResolver()
        resolver.build_from_config(config)

        # Should be ignored
        assert resolver.get_dependency_count() == 0

    def test_missing_entity_id(self):
        """Test sensor with missing entity_id."""
        config = {
            "sensors": [
                {
                    "source_type": "calculated",
                    "depends_on": ["voltage"],
                }
            ]
        }

        resolver = DependencyResolver()
        resolver.build_from_config(config)

        # Should be ignored
        assert resolver.get_dependency_count() == 0

    def test_get_dependencies_nonexistent(self):
        """Test getting dependencies for non-existent entity."""
        resolver = DependencyResolver()
        deps = resolver.get_dependencies("nonexistent")
        assert deps == set()

    def test_get_dependents_nonexistent(self):
        """Test getting dependents for non-existent key."""
        resolver = DependencyResolver()
        dependents = resolver.get_dependents("nonexistent")
        assert dependents == []

    def test_multiple_dependents_same_key(self):
        """Test multiple entities depending on same key."""
        config = {
            "sensors": [
                {
                    "entity_id": "power1",
                    "source_type": "calculated",
                    "depends_on": ["voltage"],
                },
                {
                    "entity_id": "power2",
                    "source_type": "calculated",
                    "depends_on": ["voltage"],
                },
            ]
        }

        resolver = DependencyResolver()
        resolver.build_from_config(config)

        dependents = resolver.get_dependents("voltage")
        assert len(dependents) == 2
        assert "power1" in dependents
        assert "power2" in dependents

    def test_rebuild_clears_previous_data(self):
        """Test that rebuilding clears previous dependency data."""
        config1 = {
            "sensors": [
                {
                    "entity_id": "power",
                    "source_type": "calculated",
                    "depends_on": ["voltage"],
                }
            ]
        }

        config2 = {
            "sensors": [
                {
                    "entity_id": "energy",
                    "source_type": "calculated",
                    "depends_on": ["current"],
                }
            ]
        }

        resolver = DependencyResolver()
        resolver.build_from_config(config1)
        assert resolver.has_dependencies("power")

        resolver.build_from_config(config2)
        assert not resolver.has_dependencies("power")
        assert resolver.has_dependencies("energy")
