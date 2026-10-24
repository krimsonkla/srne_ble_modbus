"""Coordinator handling of a refresh cut short by a link drop.

The SRNE BT-2 module closes the link roughly every 266 seconds. Most drops land
while the integration is idle, but one that lands mid-refresh used to fail the
whole cycle. Every entity resolves `available` through
CoordinatorEntity -> coordinator.last_update_success, so that took the entire
inverter offline in the UI for something that recovers on the next poll.
"""

import pytest
from unittest.mock import AsyncMock, Mock

from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.srne_inverter.coordinator import SRNEDataUpdateCoordinator
from custom_components.srne_inverter.application.use_cases.refresh_data_result import (
    RefreshDataResult,
)
from custom_components.srne_inverter.const import MAX_CONSECUTIVE_EMPTY_CYCLES


@pytest.fixture
def mock_entry():
    entry = Mock()
    entry.entry_id = "test_entry_id"
    entry.data = {"address": "AA:BB:CC:DD:EE:FF"}
    entry.options = {}
    return entry


def _coordinator(hass, entry, result):
    """Coordinator whose refresh use case returns a prepared result."""
    use_case = Mock()
    use_case.execute = AsyncMock(return_value=result)
    coord = SRNEDataUpdateCoordinator(
        hass,
        entry,
        {"registers": {}},
        transport=Mock(),
        connection_manager=Mock(),
        refresh_data_use_case=use_case,
    )
    coord._register_batches = []
    return coord


@pytest.mark.asyncio
async def test_partial_refresh_merges_over_previous_values(hass, mock_entry):
    """Registers whose batches never ran keep their last good reading."""
    result = RefreshDataResult(
        data={"battery_voltage": 26.5},
        success=True,
        connection_lost=True,
        error="Connection lost before completing all batches",
    )
    coord = _coordinator(hass, mock_entry, result)
    coord.data = {"battery_voltage": 25.0, "inverter_temperature": 78.4}

    merged = await coord._async_update_data()

    assert merged["battery_voltage"] == 26.5, "fresh value must win"
    assert merged["inverter_temperature"] == 78.4, "stale value must survive"


@pytest.mark.asyncio
async def test_partial_refresh_keeps_entities_available(hass, mock_entry):
    """A partial cycle must not raise -- raising clears last_update_success."""
    result = RefreshDataResult(
        data={"battery_voltage": 26.5}, success=True, connection_lost=True
    )
    coord = _coordinator(hass, mock_entry, result)
    coord.data = {"battery_voltage": 25.0}

    await coord._async_update_data()  # must not raise


@pytest.mark.asyncio
async def test_empty_cycle_still_fails(hass, mock_entry):
    """A cycle that collected nothing is a real failure.

    There is nothing to merge, and pretending otherwise would leave a genuinely
    dead inverter showing stale values forever.
    """
    result = RefreshDataResult(
        data={},
        success=False,
        connection_lost=True,
        error="Connection lost before completing all batches",
    )
    coord = _coordinator(hass, mock_entry, result)

    with pytest.raises(UpdateFailed):
        await coord._async_update_data()


class TestEmptyCycleTolerance:
    """A drop landing on batch 1 leaves nothing to merge.

    The partial-merge path needs at least one collected value. When the link
    closes before batch 1 returns, the cycle has none -- and failing it clears
    last_update_success, taking every entity unavailable for one interval over
    a condition the next poll fixes. Observed live at 19:29:38 on 2026-09-21.
    """

    def _empty(self):
        return RefreshDataResult(
            data={},
            success=False,
            connection_lost=True,
            error="Connection lost before completing all batches",
        )

    def _good(self):
        return RefreshDataResult(data={"battery_voltage": 26.5}, success=True)

    @pytest.mark.asyncio
    async def test_empty_cycle_holds_previous_values(self, hass, mock_entry):
        """Under the limit, keep the last good data instead of failing."""
        coord = _coordinator(hass, mock_entry, self._empty())
        coord.data = {"battery_voltage": 26.5, "inverter_temperature": 78.4}

        held = await coord._async_update_data()

        assert held == {"battery_voltage": 26.5, "inverter_temperature": 78.4}
        assert coord._consecutive_empty_cycles == 1

    @pytest.mark.asyncio
    async def test_empty_cycles_fail_once_the_run_is_too_long(self, hass, mock_entry):
        """The tolerance is bounded -- a dead inverter still surfaces."""
        coord = _coordinator(hass, mock_entry, self._empty())
        coord.data = {"battery_voltage": 26.5}

        for _ in range(MAX_CONSECUTIVE_EMPTY_CYCLES):
            await coord._async_update_data()

        with pytest.raises(UpdateFailed):
            await coord._async_update_data()

    @pytest.mark.asyncio
    async def test_a_good_cycle_clears_the_run(self, hass, mock_entry):
        """The counter must not creep across unrelated drops."""
        coord = _coordinator(hass, mock_entry, self._empty())
        coord.data = {"battery_voltage": 26.5}
        await coord._async_update_data()
        assert coord._consecutive_empty_cycles == 1

        coord._refresh_data_use_case.execute = AsyncMock(return_value=self._good())
        await coord._async_update_data()

        assert coord._consecutive_empty_cycles == 0

    @pytest.mark.asyncio
    async def test_first_ever_refresh_still_fails(self, hass, mock_entry):
        """With no previous data there is nothing to hold.

        Reporting success on an empty first refresh would hide a device that
        never answered at all.
        """
        coord = _coordinator(hass, mock_entry, self._empty())
        coord.data = None

        with pytest.raises(UpdateFailed):
            await coord._async_update_data()


class TestWriteReconnectsOnDemand:
    """A user write must not fail just because the link is between sessions.

    The module drops every ~266s and nothing reconnects until the next
    scheduled refresh, so a button press landing in that window used to fail
    in about a millisecond on the transport's fail-fast is_connected check.
    Reconnecting takes ~1.1s; the ~50s gap was only ever "nobody asked".
    """

    def _coord(self, hass, entry, connected, reconnect_ok=True):
        use_case = Mock()
        use_case.execute = AsyncMock(
            return_value=Mock(success=True, error=None, register=0xDF00, value=1)
        )
        transport = Mock()
        transport.is_connected = connected
        cm = Mock()
        cm.ensure_connected = AsyncMock(return_value=reconnect_ok)
        coord = SRNEDataUpdateCoordinator(
            hass, entry, {"registers": {}},
            transport=transport, connection_manager=cm,
            refresh_data_use_case=Mock(),
            write_register_use_case=use_case,
        )
        return coord, use_case, cm

    @pytest.mark.asyncio
    async def test_write_reconnects_when_link_is_down(self, hass, mock_entry):
        coord, use_case, cm = self._coord(hass, mock_entry, connected=False)

        ok = await coord.async_write_register(0xDF00, 1)

        cm.ensure_connected.assert_awaited_once()
        use_case.execute.assert_awaited_once()
        assert ok is True

    @pytest.mark.asyncio
    async def test_write_does_not_reconnect_when_already_up(self, hass, mock_entry):
        """The common path must not pay a connect it does not need."""
        coord, use_case, cm = self._coord(hass, mock_entry, connected=True)

        ok = await coord.async_write_register(0xDF00, 1)

        cm.ensure_connected.assert_not_awaited()
        use_case.execute.assert_awaited_once()
        assert ok is True

    @pytest.mark.asyncio
    async def test_write_fails_cleanly_if_reconnect_fails(self, hass, mock_entry):
        """A genuinely unreachable device still reports failure, not a hang."""
        coord, use_case, cm = self._coord(
            hass, mock_entry, connected=False, reconnect_ok=False
        )

        ok = await coord.async_write_register(0xDF00, 1)

        assert ok is False
        use_case.execute.assert_not_awaited()
