"""Dependency Injection Container.

This module implements a simple DI container using dataclasses.
The container holds all dependencies and provides factory methods
for creating the full dependency graph.

Pattern: Service Locator + Factory
Benefits:
- Single place to wire all dependencies
- Easy to test (can inject mocks)
- Clear dependency graph
- Type-safe with dataclass fields
"""

from dataclasses import dataclass
from typing import Optional, Any, Dict
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry


@dataclass
class DIContainer:
    """Dependency Injection Container.

    This container holds all dependencies organized by layer:
    - Infrastructure: Implementations of domain interfaces
    - Application: Use cases and services
    - Presentation: Coordinators and managers

    Each dependency is lazily created on first access.

    Attributes:
        hass: Home Assistant instance
        entry: Config entry
        config: Device configuration

        # Infrastructure Layer
        protocol: Modbus protocol implementation
        transport: BLE transport implementation
        connection_manager: Connection lifecycle manager
        failed_register_repo: Repository for failed registers
        crc: CRC calculation implementation

        # Application Layer
        refresh_data_use_case: Use case for refreshing device data
        write_register_use_case: Use case for writing registers
        batch_builder_service: Service for building register batches
        register_mapper_service: Service for mapping registers
        transaction_manager_service: Service for managing write transactions
        dependency_resolver_service: Service for resolving dependencies

        # Presentation Layer
        coordinator: Data update coordinator

    Example:
        >>> container = create_container(hass, entry, config)
        >>> coordinator = container.coordinator
        >>> # All dependencies automatically wired
    """

    # Core
    hass: HomeAssistant
    entry: ConfigEntry
    config: Dict[str, Any]

    # Infrastructure Layer (implementations of domain interfaces)
    protocol: Optional[Any] = None  # IProtocol
    transport: Optional[Any] = None  # ITransport
    connection_manager: Optional[Any] = None  # IConnectionManager
    failed_register_repo: Optional[Any] = None  # IFailedRegisterRepository
    crc: Optional[Any] = None  # ICRC

    # Application Layer (use cases and services)
    refresh_data_use_case: Optional[Any] = None
    write_register_use_case: Optional[Any] = None
    batch_builder_service: Optional[Any] = None
    register_mapper_service: Optional[Any] = None
    transaction_manager_service: Optional[Any] = None
    dependency_resolver_service: Optional[Any] = None
    disabled_entity_service: Optional[Any] = None  # IDisabledEntityService

    # Presentation Layer
    coordinator: Optional[Any] = None

    # Additional services
    entity_registry_service: Optional[Any] = None
    entity_preference_service: Optional[Any] = None
    device_config_service: Optional[Any] = None

    # Phase 2: Adaptive timing infrastructure
    timing_collector: Optional[Any] = None
    # Phase 3: Timeout learning
    timeout_learner: Optional[Any] = None


def create_container(
    hass: HomeAssistant,
    entry: ConfigEntry,
    config: Dict[str, Any],
) -> DIContainer:
    """Factory function to create fully-wired DI container.

    This function creates all dependencies and wires them together.
    Dependencies are created in order:
    1. Infrastructure layer (no dependencies)
    2. Application layer (depends on infrastructure)
    3. Presentation layer (depends on application)

    Args:
        hass: Home Assistant instance
        entry: Config entry for this integration
        config: Device configuration dictionary

    Returns:
        Fully-wired DIContainer with all dependencies

    Example:
        >>> from homeassistant.core import HomeAssistant
        >>> hass = HomeAssistant()
        >>> entry = MockConfigEntry(domain="srne_inverter")
        >>> config = {"address": "AA:BB:CC:DD:EE:FF"}
        >>> container = create_container(hass, entry, config)
        >>> assert container.coordinator is not None
        >>> assert container.protocol is not None

    Notes:
        This is Phase 1 scaffolding. Actual implementations will be
        separates infrastructure concerns from domain logic.
        For now, we return placeholders to establish the pattern.
    """
    container = DIContainer(hass=hass, entry=entry, config=config)

    # Phase 2: Create timing collector for adaptive timing
    container.timing_collector = _create_timing_collector()

    # Phase 3: Create timeout learner (depends on timing collector)
    container.timeout_learner = _create_timeout_learner(container.timing_collector)

    # Infrastructure Layer
    container.crc = _create_crc()
    container.protocol = _create_protocol(container.crc)
    container.transport = _create_transport(hass, container.timing_collector)
    container.connection_manager = _create_connection_manager(container.transport)
    container.failed_register_repo = _create_failed_register_repository(hass, entry)

    # Application Layer
    container.batch_builder_service = _create_batch_builder_service()
    container.register_mapper_service = _create_register_mapper_service()
    container.transaction_manager_service = _create_transaction_manager_service(
        container.failed_register_repo
    )
    container.dependency_resolver_service = _create_dependency_resolver_service()

    container.refresh_data_use_case = _create_refresh_data_use_case(
        connection_manager=container.connection_manager,
        protocol=container.protocol,
        transport=container.transport,
        mapper=container.register_mapper_service,
        batch_builder=container.batch_builder_service,
    )

    container.write_register_use_case = _create_write_register_use_case(
        protocol=container.protocol,
        transport=container.transport,
        transaction_manager=container.transaction_manager_service,
    )

    # Disabled entity optimization service
    container.disabled_entity_service = _create_disabled_entity_service(
        hass=hass,
        entry=entry,
        device_config=config,
    )

    # Presentation Layer
    # Wire coordinator with all services
    container.coordinator = _create_coordinator(
        hass=hass,
        entry=entry,
        config=config,
        refresh_use_case=container.refresh_data_use_case,
        write_use_case=container.write_register_use_case,
        transport=container.transport,
        connection_manager=container.connection_manager,
        batch_builder=container.batch_builder_service,
        register_mapper=container.register_mapper_service,
        transaction_manager=container.transaction_manager_service,
        disabled_entity_service=container.disabled_entity_service,
        timing_collector=container.timing_collector,
        timeout_learner=container.timeout_learner,
    )

    # Additional services
    container.entity_registry_service = _create_entity_registry_service(hass)
    container.entity_preference_service = _create_entity_preference_service(hass, entry)
    container.device_config_service = _create_device_config_service(config)

    return container


# Infrastructure Layer Factory Functions


def _create_crc() -> Any:
    """Create CRC calculator.

    Returns:
        ICRC implementation (ModbusCRC16)
    """
    from ..infrastructure.protocol import ModbusCRC16

    return ModbusCRC16()


def _create_protocol(crc: Any) -> Any:
    """Create Modbus protocol implementation.

    Args:
        crc: CRC calculator

    Returns:
        IProtocol implementation (ModbusRTUProtocol)
    """
    from ..infrastructure.protocol import ModbusRTUProtocol

    return ModbusRTUProtocol(crc)


def _create_transport(hass: HomeAssistant, timing_collector: Any = None) -> Any:
    """Create BLE transport.

    Args:
        hass: Home Assistant instance
        timing_collector: Optional TimingCollector for Phase 2 measurement

    Returns:
        ITransport implementation (BLETransport)
    """
    from ..infrastructure.transport import BLETransport

    return BLETransport(hass, timing_collector=timing_collector)


def _create_connection_manager(transport: Any) -> Any:
    """Create connection manager.

    Args:
        transport: Transport implementation

    Returns:
        IConnectionManager implementation (ConnectionManager)
    """
    from ..infrastructure.transport import ConnectionManager

    return ConnectionManager(transport)


def _create_failed_register_repository(hass: HomeAssistant, entry: ConfigEntry) -> Any:
    """Create failed register repository.

    Args:
        hass: Home Assistant instance
        entry: Config entry

    Returns:
        None - Repository abstraction not needed

    Note:
        Failed registers are persisted directly via coordinator's Store.
        No separate repository layer required for this use case.
        Follows YAGNI principle - current approach is sufficient.
    """
    return None


# Application Layer Factory Functions


def _create_batch_builder_service() -> Any:
    """Create batch builder service.

    Returns:
        BatchBuilderService for building optimized register batches

    Real implementation wired
    """
    from ..application.services.batch_builder_service import BatchBuilderService

    return BatchBuilderService()


def _create_register_mapper_service() -> Any:
    """Create register mapper service.

    Returns:
        RegisterMapperService for mapping register values

    Real implementation wired
    """
    from ..application.services.register_mapper_service import RegisterMapperService

    return RegisterMapperService()


def _create_disabled_entity_service(
    hass: Any,
    entry: Any,
    device_config: dict,
) -> Any:
    """Create disabled entity service.

    Args:
        hass: Home Assistant instance
        entry: Config entry
        device_config: Full device configuration with entities and registers

    Returns:
        DisabledEntityService for tracking disabled entities

    Real implementation wired
    """
    from ..application.services.disabled_entity_service import DisabledEntityService

    # Pass full device_config so service can map entity_id → register → address
    return DisabledEntityService(
        hass=hass,
        config_entry=entry,
        device_config=device_config,
    )


def _create_transaction_manager_service(failed_register_repo: Any) -> Any:
    """Create transaction manager service.

    Args:
        failed_register_repo: Repository for tracking failed registers

    Returns:
        TransactionManagerService for managing write transactions

    Real implementation wired
    """
    from ..application.services.transaction_manager_service import (
        TransactionManagerService,
    )

    return TransactionManagerService(failed_register_repo)


def _create_dependency_resolver_service() -> Any:
    """Create dependency resolver service.

    Returns:
        None - Dependency resolution handled inline

    Note:
        Dependencies are resolved inline where needed.
        No complex dependency graph requiring dedicated service.
        Current approach is clearer and simpler.
    """
    return None


def _create_refresh_data_use_case(
    connection_manager: Any,
    protocol: Any,
    transport: Any,
    mapper: Any,
    batch_builder: Any,
) -> Any:
    """Create refresh data use case.

    Args:
        connection_manager: Connection manager implementation
        protocol: Protocol implementation
        transport: Transport implementation
        mapper: Register mapper (for future enhancement)
        batch_builder: Batch building strategy (for future enhancement)

    Returns:
        RefreshDataUseCase

    Real implementation wired
    """
    from ..application.use_cases.refresh_data_use_case import RefreshDataUseCase

    return RefreshDataUseCase(connection_manager, transport, protocol)


def _create_write_register_use_case(
    protocol: Any, transport: Any, transaction_manager: Any
) -> Any:
    """Create write register use case.

    Args:
        protocol: Protocol implementation
        transport: Transport implementation
        transaction_manager: Transaction manager (not used yet, for future enhancement)

    Returns:
        WriteRegisterUseCase

    Real implementation wired
    """
    from ..application.use_cases.write_register_use_case import WriteRegisterUseCase

    return WriteRegisterUseCase(transport, protocol)


# Presentation Layer Factory Functions


def _create_coordinator(
    hass: HomeAssistant,
    entry: ConfigEntry,
    config: Dict[str, Any],
    refresh_use_case: Any,
    write_use_case: Any,
    transport: Any,
    connection_manager: Any,
    batch_builder: Any,
    register_mapper: Any,
    transaction_manager: Any,
    disabled_entity_service: Any,
    timing_collector: Any = None,
    timeout_learner: Any = None,
) -> Any:
    """Create data update coordinator.

    Args:
        hass: Home Assistant instance
        entry: Config entry
        config: Device configuration
        refresh_use_case: Use case for data refresh
        write_use_case: Use case for register writes
        transport: Transport implementation
        connection_manager: Connection manager implementation
        batch_builder: Batch builder service
        register_mapper: Register mapper service
        transaction_manager: Transaction manager service
        disabled_entity_service: Disabled entity tracking service
        timing_collector: Optional TimingCollector for Phase 2 measurement
        timeout_learner: Optional TimeoutLearner for Phase 3 learning

    Returns:
        Coordinator instance with injected dependencies

    Coordinator now receives all application services including adaptive timing
    """
    from ..coordinator import SRNEDataUpdateCoordinator

    return SRNEDataUpdateCoordinator(
        hass,
        entry,
        config,
        transport=transport,
        connection_manager=connection_manager,
        refresh_data_use_case=refresh_use_case,
        write_register_use_case=write_use_case,
        batch_builder=batch_builder,
        register_mapper=register_mapper,
        transaction_manager=transaction_manager,
        disabled_entity_service=disabled_entity_service,
        timing_collector=timing_collector,
        timeout_learner=timeout_learner,
    )


# Additional Service Factory Functions


def _create_timing_collector() -> Any:
    """Create timing collector for Phase 2 adaptive timing.

    Returns:
        TimingCollector instance for measuring operation timings

    Note:
        Phase 2: Measurement Infrastructure
        Collects timing data for future adaptive timeout optimization.
    """
    from ..application.services.timing_collector import TimingCollector
    from ..const import TIMING_SAMPLE_SIZE

    return TimingCollector(sample_size=TIMING_SAMPLE_SIZE)


def _create_timeout_learner(timing_collector: Any) -> Any:
    """Create timeout learner for Phase 3 adaptive timing.

    Args:
        timing_collector: TimingCollector instance for accessing measurements

    Returns:
        TimeoutLearner instance for calculating optimal timeouts

    Note:
        Phase 3: Learning Algorithm
        Calculates optimal timeouts using P95 × 1.5 algorithm.
    """
    from ..application.services.timeout_learner import TimeoutLearner

    return TimeoutLearner(collector=timing_collector)


def _create_entity_registry_service(hass: HomeAssistant) -> Any:
    """Create entity registry service.

    Args:
        hass: Home Assistant instance

    Returns:
        None - Use Home Assistant's built-in entity registry

    Note:
        Home Assistant provides entity_registry directly.
        Use homeassistant.helpers.entity_registry where needed.
        No custom wrapper required.
    """
    return None


def _create_entity_preference_service(hass: HomeAssistant, entry: ConfigEntry) -> Any:
    """Create entity preference service.

    Args:
        hass: Home Assistant instance
        entry: Config entry

    Returns:
        None - Use config entry options directly

    Note:
        Entity preferences stored in entry.options.
        Access directly via config_entry.options throughout code.
        No service abstraction needed.
    """
    return None


def _create_device_config_service(config: Dict[str, Any]) -> Any:
    """Create device config service.

    Args:
        config: Device configuration

    Returns:
        None - Use config dict directly

    Note:
        Device config is read-only after load from YAML.
        Dict access is simple and clear.
        Service wrapper adds no value.
    """
    return None


# Container Validation


def validate_container(container: DIContainer) -> bool:
    """Validate that container has all required dependencies.

    Args:
        container: Container to validate

    Returns:
        True if all critical dependencies are present

    Raises:
        ValueError: If critical dependencies are missing

    Example:
        >>> container = create_container(hass, entry, config)
        >>> assert validate_container(container)
    """
    critical_dependencies = [
        "hass",
        "entry",
        "config",
        "coordinator",
    ]

    missing = []
    for dep_name in critical_dependencies:
        if getattr(container, dep_name, None) is None:
            missing.append(dep_name)

    if missing:
        raise ValueError(f"Missing critical dependencies: {', '.join(missing)}")

    return True
