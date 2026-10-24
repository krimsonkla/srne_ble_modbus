"""Tests for RefreshDataUseCase.

Phase 2 Week 6: Application Layer Testing
"""

import pytest
from unittest.mock import AsyncMock, Mock
from datetime import datetime

from custom_components.srne_inverter.application.use_cases.refresh_data_use_case import (
    RefreshDataUseCase,
    RegisterBatch,
    RefreshDataResult,
)
from custom_components.srne_inverter.domain.entities.register import Register
from custom_components.srne_inverter.domain.value_objects import RegisterAddress


def _make_batch(start_address, count, register_map):
    """Build a RegisterBatch from the (start:int, count, {offset: name}) shape.

    RegisterBatch was refactored to take a list of Register entities and a
    RegisterAddress. This shim preserves the concise call shape used by these
    tests.
    """
    return RegisterBatch(
        start_address=RegisterAddress(start_address),
        count=count,
        registers=[
            Register(RegisterAddress(start_address + offset), name)
            for offset, name in sorted(register_map.items())
        ],
    )


class TestRefreshDataUseCase:
    """Test suite for RefreshDataUseCase."""

    @pytest.fixture
    def mock_connection_manager(self):
        """Create mock connection manager."""
        mock = AsyncMock()
        mock.ensure_connected = AsyncMock(return_value=True)
        return mock

    @pytest.fixture
    def mock_transport(self):
        """Create mock transport."""
        mock = Mock()
        mock.is_connected = True
        mock.send = AsyncMock()
        return mock

    @pytest.fixture
    def mock_protocol(self):
        """Create mock protocol."""
        mock = Mock()
        mock.build_read_command = Mock(return_value=b"\x01\x03\x01\x00\x00\x01")
        mock.decode_response = Mock()
        return mock

    @pytest.fixture
    def use_case(self, mock_connection_manager, mock_transport, mock_protocol):
        """Create use case with mocked dependencies."""
        return RefreshDataUseCase(
            mock_connection_manager,
            mock_transport,
            mock_protocol,
        )

    @pytest.mark.asyncio
    async def test_execute_successful_single_batch(
        self, use_case, mock_connection_manager, mock_transport, mock_protocol
    ):
        """Test successful data refresh with single batch."""
        # Arrange
        batches = [
            _make_batch(
                start_address=0x0100,
                count=2,
                register_map={0: "voltage", 1: "current"},
            )
        ]

        register_defs = {
            "voltage": {"scaling": 0.1, "offset": 0, "data_type": "uint16"},
            "current": {"scaling": 0.01, "offset": 0, "data_type": "uint16"},
        }

        # Mock successful response
        mock_transport.send.return_value = b"\x01\x03\x04\x01\x00\x02\x00"
        mock_protocol.decode_response.return_value = {
            "values": [2500, 150],  # 250.0V, 1.50A after scaling
        }

        # Act
        result = await use_case.execute(
            device_address="AA:BB:CC:DD:EE:FF",
            register_batches=batches,
            register_definitions=register_defs,
        )

        # Assert
        assert result.success is True
        assert result.error == ""
        assert "voltage" in result.data
        assert "current" in result.data
        assert result.data["voltage"] == 250.0  # 2500 * 0.1
        assert result.data["current"] == 1.5  # 150 * 0.01
        assert result.data["connected"] is True
        assert result.duration > 0

        # Verify connection was established
        mock_connection_manager.ensure_connected.assert_called_once_with(
            "AA:BB:CC:DD:EE:FF"
        )

    @pytest.mark.asyncio
    async def test_execute_connection_failure(self, use_case, mock_connection_manager):
        """Test handling of connection failure."""
        # Arrange
        mock_connection_manager.ensure_connected.return_value = False

        batches = [
            _make_batch(
                start_address=0x0100,
                count=1,
                register_map={0: "voltage"},
            )
        ]

        # Act
        result = await use_case.execute(
            device_address="AA:BB:CC:DD:EE:FF",
            register_batches=batches,
            register_definitions={},
        )

        # Assert
        assert result.success is False
        # Decorator changes error message format
        assert "Failed to connect" in result.error
        assert result.data == {}

    @pytest.mark.asyncio
    async def test_execute_batch_read_failure_with_split(
        self, use_case, mock_transport, mock_protocol
    ):
        """Test batch failure triggers split and retry."""
        # Arrange
        batches = [
            _make_batch(
                start_address=0x0100,
                count=2,
                register_map={0: "reg1", 1: "reg2"},
            )
        ]

        register_defs = {
            "reg1": {"scaling": 1.0, "offset": 0, "data_type": "uint16"},
            "reg2": {"scaling": 1.0, "offset": 0, "data_type": "uint16"},
        }

        # First call (batch) fails, subsequent calls (individual) succeed.
        # Split-retry consumes the {offset: value} protocol format directly
        # (unlike the initial batch path, which also accepts {"values": [...]}).
        mock_protocol.decode_response.side_effect = [
            None,  # Batch fails
            {0: 100},  # First register succeeds
            {0: 200},  # Second register succeeds
        ]

        # Act
        result = await use_case.execute(
            device_address="AA:BB:CC:DD:EE:FF",
            register_batches=batches,
            register_definitions=register_defs,
        )

        # Assert
        assert result.success is True
        assert "reg1" in result.data
        assert "reg2" in result.data
        assert result.data["reg1"] == 100
        assert result.data["reg2"] == 200
        assert result.failed_reads >= 1  # Batch failure counted

    @pytest.mark.asyncio
    async def test_execute_multiple_batches(
        self, use_case, mock_transport, mock_protocol
    ):
        """Test reading multiple batches."""
        # Arrange
        batches = [
            _make_batch(
                start_address=0x0100,
                count=1,
                register_map={0: "voltage"},
            ),
            _make_batch(
                start_address=0x0200,
                count=1,
                register_map={0: "current"},
            ),
        ]

        register_defs = {
            "voltage": {"scaling": 0.1, "offset": 0, "data_type": "uint16"},
            "current": {"scaling": 0.01, "offset": 0, "data_type": "uint16"},
        }

        mock_protocol.decode_response.side_effect = [
            {"values": [2500]},  # First batch
            {"values": [150]},  # Second batch
        ]

        # Act
        result = await use_case.execute(
            device_address="AA:BB:CC:DD:EE:FF",
            register_batches=batches,
            register_definitions=register_defs,
        )

        # Assert
        assert result.success is True
        assert len(result.data) >= 2
        assert result.data["voltage"] == 250.0
        assert result.data["current"] == 1.5

    @pytest.mark.asyncio
    async def test_execute_int16_data_type(
        self, use_case, mock_transport, mock_protocol
    ):
        """Test signed int16 data type conversion."""
        # Arrange
        batches = [
            _make_batch(
                start_address=0x0100,
                count=1,
                register_map={0: "temperature"},
            )
        ]

        register_defs = {
            "temperature": {"scaling": 0.1, "offset": 0, "data_type": "int16"},
        }

        # Mock negative value (two's complement)
        mock_protocol.decode_response.return_value = {
            "values": [0xFFEC],  # -20 in int16
        }

        # Act
        result = await use_case.execute(
            device_address="AA:BB:CC:DD:EE:FF",
            register_batches=batches,
            register_definitions=register_defs,
        )

        # Assert
        assert result.success is True
        assert result.data["temperature"] == -2.0  # -20 * 0.1

    @pytest.mark.asyncio
    async def test_execute_with_offset(self, use_case, mock_transport, mock_protocol):
        """Test register value with offset."""
        # Arrange
        batches = [
            _make_batch(
                start_address=0x0100,
                count=1,
                register_map={0: "adjusted_voltage"},
            )
        ]

        register_defs = {
            "adjusted_voltage": {"scaling": 0.1, "offset": 100, "data_type": "uint16"},
        }

        mock_protocol.decode_response.return_value = {"values": [2400]}  # Raw value

        # Act
        result = await use_case.execute(
            device_address="AA:BB:CC:DD:EE:FF",
            register_batches=batches,
            register_definitions=register_defs,
        )

        # Assert
        assert result.success is True
        # (2400 + 100) * 0.1 = 250.0
        assert result.data["adjusted_voltage"] == 250.0

    @pytest.mark.asyncio
    async def test_execute_enriches_with_metadata(
        self, use_case, mock_transport, mock_protocol
    ):
        """Test that result is enriched with metadata."""
        # Arrange
        batches = [
            _make_batch(
                start_address=0x0100,
                count=1,
                register_map={0: "voltage"},
            )
        ]

        mock_protocol.decode_response.return_value = {"values": [2500]}

        # Act
        result = await use_case.execute(
            device_address="AA:BB:CC:DD:EE:FF",
            register_batches=batches,
            register_definitions={
                "voltage": {"scaling": 1.0, "offset": 0, "data_type": "uint16"}
            },
        )

        # Assert
        assert result.success is True
        assert result.data["connected"] is True
        assert "update_duration" in result.data
        assert "total_updates" in result.data
        assert "failed_reads" in result.data
        assert "last_update_time" in result.data
        assert isinstance(result.data["last_update_time"], datetime)

    @pytest.mark.asyncio
    async def test_execute_fault_detection(
        self, use_case, mock_transport, mock_protocol
    ):
        """Test fault code detection."""
        # Arrange
        batches = [
            _make_batch(
                start_address=0x0100,
                count=4,
                register_map={
                    0: "fault_code_0",
                    1: "fault_code_1",
                    2: "fault_code_2",
                    3: "fault_code_3",
                },
            )
        ]

        register_defs = {
            "fault_code_0": {"scaling": 1.0, "offset": 0, "data_type": "uint16"},
            "fault_code_1": {"scaling": 1.0, "offset": 0, "data_type": "uint16"},
            "fault_code_2": {"scaling": 1.0, "offset": 0, "data_type": "uint16"},
            "fault_code_3": {"scaling": 1.0, "offset": 0, "data_type": "uint16"},
        }

        # Mock fault codes (one non-zero)
        mock_protocol.decode_response.return_value = {
            "values": [0, 5, 0, 0],  # fault_code_1 = 5
        }

        # Act
        result = await use_case.execute(
            device_address="AA:BB:CC:DD:EE:FF",
            register_batches=batches,
            register_definitions=register_defs,
        )

        # Assert
        assert result.success is True
        assert result.data["fault_detected"] is True
        assert result.data["fault_bits"] == [0, 5, 0, 0]

    @pytest.mark.asyncio
    async def test_split_and_retry_max_depth(
        self, use_case, mock_transport, mock_protocol
    ):
        """Test that split stops at max depth."""
        # Arrange
        batches = [
            _make_batch(
                start_address=0x0100,
                count=8,  # Will require multiple splits
                register_map={i: f"reg{i}" for i in range(8)},
            )
        ]

        # All reads fail
        mock_protocol.decode_response.return_value = None

        # Act
        result = await use_case.execute(
            device_address="AA:BB:CC:DD:EE:FF",
            register_batches=batches,
            register_definitions={
                f"reg{i}": {"scaling": 1.0, "offset": 0, "data_type": "uint16"}
                for i in range(8)
            },
        )

        # Assert
        assert result.success is True  # Still returns success (empty data is valid)
        assert result.failed_reads > 0
        # Should have minimal data (split depth limited)

    @pytest.mark.asyncio
    async def test_transport_disconnected(
        self, use_case, mock_connection_manager, mock_transport, mock_protocol
    ):
        """Test handling when transport disconnects mid-read."""
        # Arrange
        batches = [
            _make_batch(
                start_address=0x0100,
                count=1,
                register_map={0: "voltage"},
            )
        ]

        # Transport disconnects after connection
        mock_transport.is_connected = False

        # Act
        result = await use_case.execute(
            device_address="AA:BB:CC:DD:EE:FF",
            register_batches=batches,
            register_definitions={},
        )

        # Assert
        # Mid-batch disconnect is now surfaced as a failed result
        # (previously returned success with empty data).
        assert result.success is False
        assert "connection lost" in result.error.lower()
        # Flagged so the coordinator can raise TransportConnectionLostError and
        # route this to the warning + retry-in-60s branch. Without the flag it
        # fell through to the generic handler and logged an ERROR for what is
        # an expected drop (the peer resets the link every ~5 min).
        assert result.connection_lost is True

    async def test_partial_refresh_reports_success(
        self, use_case, mock_connection_manager, mock_transport, mock_protocol
    ):
        """A cycle cut short mid-way keeps the values it already collected.

        Regression: the abort used to return success=False even when batches
        had already landed. The coordinator turned that into UpdateFailed,
        which clears last_update_success -- and every entity resolves
        `available` through it, so one dropped link took the whole device
        offline in the UI for something that recovers in ~50s.
        """
        batches = [
            _make_batch(start_address=0x0100, count=1, register_map={0: "voltage"}),
            _make_batch(start_address=0x0200, count=1, register_map={0: "current"}),
        ]
        register_defs = {
            "voltage": {"scaling": 0.1, "offset": 0, "data_type": "uint16"},
            "current": {"scaling": 0.1, "offset": 0, "data_type": "uint16"},
        }

        # Connected for the first batch, gone before the second.
        states = iter([True, True, False, False, False, False])

        class _Flaky:
            def __init__(self, inner):
                self._inner = inner

            @property
            def is_connected(self):
                return next(states, False)

            def __getattr__(self, name):
                return getattr(self._inner, name)

        use_case._transport = _Flaky(mock_transport)
        mock_transport.send.return_value = b"\x01\x03\x02\x09\xc4"
        mock_protocol.decode_response.return_value = {"values": [2500]}

        result = await use_case.execute(
            device_address="AA:BB:CC:DD:EE:FF",
            register_batches=batches,
            register_definitions=register_defs,
        )

        # Partial, but usable -- and flagged so the coordinator merges it.
        assert result.success is True
        assert result.connection_lost is True
        assert result.data, "expected the completed batch to be retained"

    @pytest.mark.asyncio
    async def test_connection_error_mid_read_is_flagged(
        self, use_case, mock_connection_manager, mock_transport, mock_protocol
    ):
        """A RuntimeError during a batch read must flag connection_lost.

        Regression: three abort paths existed and only the is_connected
        pre-check set connection_lost. The other two fire on a RuntimeError
        mid-read -- which is what an ATT 0x0e produces -- so the coordinator
        saw an unflagged failure and took every entity unavailable. Observed
        live at 21:41:48 on 2026-09-21.
        """
        batches = [
            _make_batch(start_address=0x0100, count=1, register_map={0: "voltage"}),
            _make_batch(start_address=0x0200, count=1, register_map={0: "current"}),
        ]
        register_defs = {
            "voltage": {"scaling": 0.1, "offset": 0, "data_type": "uint16"},
            "current": {"scaling": 0.1, "offset": 0, "data_type": "uint16"},
        }
        mock_transport.send = AsyncMock(
            side_effect=[
                b"\x01\x03\x02\x09\xc4",
                RuntimeError("BLE connection lost during send"),
            ]
        )
        mock_protocol.decode_response.return_value = {"values": [2500]}

        result = await use_case.execute(
            device_address="AA:BB:CC:DD:EE:FF",
            register_batches=batches,
            register_definitions=register_defs,
        )

        assert result.connection_lost is True
        assert result.data, "the batch that already landed must be retained"
        assert result.success is True, "partial data is a partial success"

    @pytest.mark.asyncio
    async def test_unexpected_exception(self, use_case, mock_connection_manager):
        """Test handling of unexpected exceptions."""
        # Arrange
        mock_connection_manager.ensure_connected.side_effect = RuntimeError("Boom!")

        batches = [
            _make_batch(
                start_address=0x0100,
                count=1,
                register_map={0: "voltage"},
            )
        ]

        # Act & Assert
        # Decorator will catch and log the exception, then raise RuntimeError
        with pytest.raises(RuntimeError, match="Boom"):
            await use_case.execute(
                device_address="AA:BB:CC:DD:EE:FF",
                register_batches=batches,
                register_definitions={},
            )


class TestConnectionDropRecovery:
    """Test connection drop detection and recovery in RefreshDataUseCase.

    These tests verify Phase 1 and Phase 2 connection recovery implementation.
    """

    @pytest.fixture
    def mock_connection_manager(self):
        """Create mock connection manager."""
        mock = AsyncMock()
        mock.ensure_connected = AsyncMock(return_value=True)
        return mock

    @pytest.fixture
    def mock_transport(self):
        """Create mock transport."""
        mock = Mock()
        mock.is_connected = True
        mock.send = AsyncMock()
        return mock

    @pytest.fixture
    def mock_protocol(self):
        """Create mock protocol."""
        mock = Mock()
        mock.build_read_command = Mock(return_value=b"\x01\x03\x01\x00\x00\x01")
        mock.decode_response = Mock()
        return mock

    @pytest.fixture
    def use_case(self, mock_connection_manager, mock_transport, mock_protocol):
        """Create use case with mocked dependencies."""
        return RefreshDataUseCase(
            mock_connection_manager,
            mock_transport,
            mock_protocol,
        )

    @pytest.mark.asyncio
    async def test_transport_send_raises_connection_error(
        self, use_case, mock_transport, mock_protocol
    ):
        """Test use case handles RuntimeError from transport.send().

        When transport.send() detects connection loss and raises RuntimeError,
        it should propagate through the use case for the coordinator to handle.
        """
        # Arrange
        batches = [
            _make_batch(
                start_address=0x0100,
                count=1,
                register_map={0: "voltage"},
            )
        ]

        # Simulate connection loss during send
        mock_transport.send.side_effect = RuntimeError(
            "BLE connection lost - reconnection needed"
        )

        # Connection errors are now caught and returned as a failed result
        # rather than propagating as exceptions.
        result = await use_case.execute(
            device_address="AA:BB:CC:DD:EE:FF",
            register_batches=batches,
            register_definitions={
                "voltage": {"scaling": 1.0, "offset": 0, "data_type": "uint16"}
            },
        )
        assert result.success is False
        assert "connection" in result.error.lower()

    @pytest.mark.asyncio
    async def test_circuit_breaker_error_propagates(
        self, use_case, mock_transport, mock_protocol
    ):
        """Test circuit breaker error propagates from transport."""
        # Arrange
        batches = [
            _make_batch(
                start_address=0x0100,
                count=1,
                register_map={0: "voltage"},
            )
        ]

        # Simulate circuit breaker opening
        mock_transport.send.side_effect = RuntimeError(
            "Connection circuit breaker opened after 3 timeouts"
        )

        result = await use_case.execute(
            device_address="AA:BB:CC:DD:EE:FF",
            register_batches=batches,
            register_definitions={},
        )
        assert result.success is False
        assert "circuit breaker" in result.error.lower()

    @pytest.mark.asyncio
    async def test_connection_manager_failure_propagates(
        self, use_case, mock_connection_manager
    ):
        """Test connection manager failure propagates correctly."""
        # Arrange
        batches = [
            _make_batch(
                start_address=0x0100,
                count=1,
                register_map={0: "voltage"},
            )
        ]

        # Connection manager fails to connect
        mock_connection_manager.ensure_connected.return_value = False

        # Act
        result = await use_case.execute(
            device_address="AA:BB:CC:DD:EE:FF",
            register_batches=batches,
            register_definitions={},
        )

        # Assert
        assert result.success is False
        assert "Failed to connect" in result.error

    @pytest.mark.asyncio
    async def test_successful_recovery_on_retry(
        self, use_case, mock_transport, mock_protocol
    ):
        """Test successful data retrieval after connection recovery.

        Simulates the scenario where:
        1. First update fails due to connection loss
        2. Connection is recovered
        3. Second update succeeds
        """
        # Arrange
        batches = [
            _make_batch(
                start_address=0x0100,
                count=1,
                register_map={0: "voltage"},
            )
        ]

        register_defs = {
            "voltage": {"scaling": 0.1, "offset": 0, "data_type": "uint16"},
        }

        # First call fails, second succeeds
        call_count = 0

        def send_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("BLE connection lost - reconnection needed")
            return b"\x01\x03\x02\x09\xc4"  # Mock response

        mock_transport.send.side_effect = send_side_effect
        mock_protocol.decode_response.return_value = {"values": [2500]}

        # Act - First attempt (should fail with connection error result)
        first_result = await use_case.execute(
            device_address="AA:BB:CC:DD:EE:FF",
            register_batches=batches,
            register_definitions=register_defs,
        )
        assert first_result.success is False

        # Reset mock behavior for second attempt
        mock_transport.send.side_effect = None
        mock_transport.send.return_value = b"\x01\x03\x02\x09\xc4"

        # Act - Second attempt (should succeed)
        result = await use_case.execute(
            device_address="AA:BB:CC:DD:EE:FF",
            register_batches=batches,
            register_definitions=register_defs,
        )

        # Assert
        assert result.success is True
        assert result.data["voltage"] == 250.0

    @pytest.mark.asyncio
    async def test_no_partial_data_on_connection_failure(
        self, use_case, mock_transport, mock_protocol
    ):
        """Half-read values from the FAILING batch must not leak.

        Note the scope: batches that already completed before the drop ARE
        retained (see test_connection_error_mid_read_is_flagged) so the
        coordinator can merge them. What must not leak is a partially decoded
        value from the batch that failed. This test has a single batch, so
        there is no prior data and result.data carries no register values.
        """
        # Arrange
        batches = [
            _make_batch(
                start_address=0x0100,
                count=2,
                register_map={0: "voltage", 1: "current"},
            )
        ]

        register_defs = {
            "voltage": {"scaling": 0.1, "offset": 0, "data_type": "uint16"},
            "current": {"scaling": 0.01, "offset": 0, "data_type": "uint16"},
        }

        # First register succeeds, second fails with connection error
        call_count = 0

        def send_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return b"\x01\x03\x02\x09\xc4"  # First register success
            raise RuntimeError("BLE connection lost - reconnection needed")

        mock_transport.send.side_effect = send_side_effect

        # First decode succeeds
        mock_protocol.decode_response.side_effect = [
            None,  # Batch read fails
            {"values": [2500]},  # Individual voltage succeeds
            # Current read will fail with connection error
        ]

        # Connection error mid-batch: use case now returns success=True with
        # only diagnostic data (no register values). The key invariant this
        # test verifies is that partial register data does NOT leak through.
        result = await use_case.execute(
            device_address="AA:BB:CC:DD:EE:FF",
            register_batches=batches,
            register_definitions=register_defs,
        )
        # No named register data should have leaked through
        assert "voltage" not in result.data
        assert "current" not in result.data
        # Failed reads should be recorded
        assert result.failed_reads > 0


class TestRegisterBatch:
    """Test RegisterBatch dataclass."""

    def test_create_register_batch(self):
        """Test creating RegisterBatch."""
        batch = RegisterBatch(
            start_address=RegisterAddress(0x0100),
            count=5,
            registers=[
                Register(RegisterAddress(0x0100 + i), f"reg{i}") for i in range(5)
            ],
        )

        assert int(batch.start_address) == 0x0100
        assert batch.count == 5
        assert len(batch.register_map) == 5
        assert batch.register_map[0] == "reg0"


class TestRefreshDataResult:
    """Test RefreshDataResult dataclass."""

    def test_create_successful_result(self):
        """Test creating successful result."""
        result = RefreshDataResult(
            data={"voltage": 250.0},
            success=True,
            duration=1.5,
            failed_reads=0,
        )

        assert result.success is True
        assert result.error == ""
        assert result.data["voltage"] == 250.0
        assert result.duration == 1.5
        assert result.failed_reads == 0

    def test_create_failed_result(self):
        """Test creating failed result."""
        result = RefreshDataResult(
            data={},
            success=False,
            error="Connection failed",
            duration=0.5,
            failed_reads=3,
        )

        assert result.success is False
        assert result.error == "Connection failed"
        assert result.data == {}
        assert result.failed_reads == 3
