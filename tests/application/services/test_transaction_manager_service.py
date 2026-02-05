"""Tests for TransactionManagerService.

Phase 2 Week 6: Application Layer Testing (Day 27)
"""

import pytest
from unittest.mock import AsyncMock, Mock

from custom_components.srne_inverter.application.services.transaction_manager_service import (
    TransactionManagerService,
    WriteTransaction,
)


class TestTransactionManagerService:
    """Test suite for TransactionManagerService."""

    @pytest.fixture
    def mock_repository(self):
        """Create mock repository."""
        mock = Mock()
        mock.save_failed_registers = AsyncMock()
        mock.load_failed_registers = AsyncMock(return_value=[])
        return mock

    @pytest.fixture
    def manager(self, mock_repository):
        """Create manager with mocked repository."""
        return TransactionManagerService(mock_repository)

    @pytest.fixture
    def manager_no_repo(self):
        """Create manager without repository."""
        return TransactionManagerService()

    @pytest.mark.asyncio
    async def test_queue_write_successful(self, manager):
        """Test successful write queuing."""
        # Act
        success = await manager.queue_write(0x0100, 5000)

        # Assert
        assert success is True
        assert manager.has_pending_writes() is True
        assert manager.get_queue_size() == 1

    @pytest.mark.asyncio
    async def test_queue_multiple_writes(self, manager):
        """Test queuing multiple writes."""
        # Act
        await manager.queue_write(0x0100, 5000)
        await manager.queue_write(0x0200, 3000)
        await manager.queue_write(0x0300, 2000)

        # Assert
        assert manager.get_queue_size() == 3

    @pytest.mark.asyncio
    async def test_next_transaction(self, manager):
        """Test getting next transaction."""
        # Arrange
        await manager.queue_write(0x0100, 5000)

        # Act
        transaction = await manager.next_transaction()

        # Assert
        assert transaction is not None
        assert transaction.register == 0x0100
        assert transaction.value == 5000
        assert manager.get_queue_size() == 0

    @pytest.mark.asyncio
    async def test_next_transaction_empty_queue(self, manager):
        """Test getting transaction from empty queue."""
        # Act
        transaction = await manager.next_transaction()

        # Assert
        assert transaction is None

    @pytest.mark.asyncio
    async def test_has_pending_writes(self, manager):
        """Test has_pending_writes check."""
        # Initially empty
        assert manager.has_pending_writes() is False

        # Add write
        await manager.queue_write(0x0100, 5000)
        assert manager.has_pending_writes() is True

        # Remove write
        await manager.next_transaction()
        assert manager.has_pending_writes() is False

    @pytest.mark.asyncio
    async def test_mark_register_failed(self, manager, mock_repository):
        """Test marking register as failed."""
        # Act
        await manager.mark_register_failed(0x0200)

        # Assert
        assert 0x0200 in manager.get_failed_registers()
        assert manager.needs_batch_rebuild() is True
        mock_repository.save_failed_registers.assert_called_once()

    @pytest.mark.asyncio
    async def test_mark_register_recovered(self, manager, mock_repository):
        """Test marking register as recovered."""
        # Arrange
        await manager.mark_register_failed(0x0200)
        mock_repository.save_failed_registers.reset_mock()

        # Act
        await manager.mark_register_recovered(0x0200)

        # Assert
        assert 0x0200 not in manager.get_failed_registers()
        assert manager.needs_batch_rebuild() is True
        mock_repository.save_failed_registers.assert_called_once()

    @pytest.mark.asyncio
    async def test_mark_same_register_failed_twice(self, manager, mock_repository):
        """Test marking same register failed twice."""
        # Act
        await manager.mark_register_failed(0x0200)
        await manager.mark_register_failed(0x0200)  # Again

        # Assert
        assert len(manager.get_failed_registers()) == 1
        # Should only save once per unique register
        assert mock_repository.save_failed_registers.call_count == 1

    @pytest.mark.asyncio
    async def test_load_failed_registers(self, manager, mock_repository):
        """Test loading failed registers from storage."""
        # Arrange
        mock_repository.load_failed_registers.return_value = [0x0100, 0x0200, 0x0300]

        # Act
        await manager.load_failed_registers()

        # Assert
        assert len(manager.get_failed_registers()) == 3
        assert 0x0100 in manager.get_failed_registers()
        assert 0x0200 in manager.get_failed_registers()
        assert 0x0300 in manager.get_failed_registers()
        assert manager.needs_batch_rebuild() is True

    @pytest.mark.asyncio
    async def test_load_failed_registers_no_repository(self, manager_no_repo):
        """Test loading when no repository configured."""
        # Act
        await manager_no_repo.load_failed_registers()

        # Assert
        assert len(manager_no_repo.get_failed_registers()) == 0

    @pytest.mark.asyncio
    async def test_needs_batch_rebuild(self, manager):
        """Test batch rebuild signaling."""
        # Initially false
        assert manager.needs_batch_rebuild() is False

        # Mark register failed
        await manager.mark_register_failed(0x0200)
        assert manager.needs_batch_rebuild() is True

        # Acknowledge rebuild
        manager.acknowledge_batch_rebuild()
        assert manager.needs_batch_rebuild() is False

    @pytest.mark.asyncio
    async def test_acknowledge_batch_rebuild(self, manager):
        """Test acknowledging batch rebuild."""
        # Arrange
        await manager.mark_register_failed(0x0200)
        assert manager.needs_batch_rebuild() is True

        # Act
        manager.acknowledge_batch_rebuild()

        # Assert
        assert manager.needs_batch_rebuild() is False

    @pytest.mark.asyncio
    async def test_clear_failed_registers(self, manager):
        """Test clearing all failed registers."""
        # Arrange
        await manager.mark_register_failed(0x0100)
        await manager.mark_register_failed(0x0200)
        await manager.mark_register_failed(0x0300)
        assert len(manager.get_failed_registers()) == 3

        # Act
        manager.clear_failed_registers()

        # Assert
        assert len(manager.get_failed_registers()) == 0
        assert manager.needs_batch_rebuild() is True

    def test_get_statistics(self, manager):
        """Test getting manager statistics."""
        # Act
        stats = manager.get_statistics()

        # Assert
        assert "pending_writes" in stats
        assert "failed_registers_count" in stats
        assert "failed_registers" in stats
        assert "needs_batch_rebuild" in stats
        assert stats["pending_writes"] == 0
        assert stats["failed_registers_count"] == 0

    @pytest.mark.asyncio
    async def test_get_statistics_with_data(self, manager):
        """Test statistics with actual data."""
        # Arrange
        await manager.queue_write(0x0100, 5000)
        await manager.mark_register_failed(0x0200)

        # Act
        stats = manager.get_statistics()

        # Assert
        assert stats["pending_writes"] == 1
        assert stats["failed_registers_count"] == 1
        assert "0x0200" in stats["failed_registers"]
        assert stats["needs_batch_rebuild"] is True

    @pytest.mark.asyncio
    async def test_write_priority(self, manager):
        """Test write transaction priority."""
        # Arrange
        await manager.queue_write(0x0100, 5000, priority=2)
        await manager.queue_write(0x0200, 3000, priority=1)

        # Act
        first = await manager.next_transaction()
        second = await manager.next_transaction()

        # Assert
        # Note: Queue is FIFO, not priority-sorted by default
        # Priority is metadata for future enhancement
        assert first.register == 0x0100
        assert first.priority == 2
        assert second.register == 0x0200
        assert second.priority == 1


class TestWriteTransaction:
    """Test WriteTransaction dataclass."""

    def test_create_transaction(self):
        """Test creating transaction."""
        transaction = WriteTransaction(
            register=0x0100,
            value=5000,
            priority=1,
        )

        assert transaction.register == 0x0100
        assert transaction.value == 5000
        assert transaction.priority == 1

    def test_create_transaction_default_priority(self):
        """Test transaction with default priority."""
        transaction = WriteTransaction(
            register=0x0100,
            value=5000,
        )

        assert transaction.priority == 0
