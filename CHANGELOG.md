# Changelog

All notable changes to this integration are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Why this file matters for HACS

HACS does **not** read this file. It builds the changelog it shows from the
**body of each GitHub Release**, newest first, stopping at the version the user
already has installed (`custom_components/hacs/update.py`,
`async_release_notes`). It also decides whether to display a version number at
all by whether any releases exist — with none, it falls back to showing a
commit SHA.

So the release body is the thing users actually see. `release.yml` copies the
matching section of this file into the release body on tag push, which keeps
the two from drifting: edit this file, tag, and the release text follows.

## [Unreleased]

## [0.6.0] - 2026-09-22

First tagged release. Earlier work is in the commit history but was never
tagged, so HACS displayed commit SHAs instead of versions; `0.5.0` in
`manifest.json` was never published as a release.

### Fixed

- **Inverter output voltage read 10x high.** Registers 534/556/557
  (`InvVoltA`/`B`/`C`) carried `scaling: 1` while the device reports decivolts,
  so a 117.6 V bus displayed as 1176 V. The other 32 voltage registers in the
  table already used `scaling: 0.1`. Confirmed against `grid_voltage` (register
  531) reading 117.0 V on the same AC bus at the same moment.
- **Notify subscription leak.** A peer-initiated drop left the old
  `BleakClient` alive, so `stop_notify()` never ran and BlueZ kept the notify
  acquisition open. Each reconnect added another duplicate delivery of every
  notification — 9 rising to 18 across one window — and past the queue bound the
  transport logged "Notification queue full" about 20 times a minute.
  Connection loss now releases the transport, `connect()` is idempotent, and
  `disconnect()` has a re-entrancy guard.
- **A single dropped cycle took the whole inverter offline.** Every entity
  resolves `available` through `coordinator.last_update_success`. A cut-short
  cycle now merges its partial result over the previous values, and a cycle
  that collects nothing holds previous values for a bounded run
  (`MAX_CONSECUTIVE_EMPTY_CYCLES = 3`, roughly four minutes) before reporting
  unavailable. An empty first refresh still fails, as it should.
- **Concurrent reads and writes collided on the characteristic.** The device
  will concatenate two replies into one notification; a read consumed a write's
  reply and the write timed out. `send()` now holds an `asyncio.Lock`, so a
  write waits about one batch (~0.85 s) instead of colliding.
- **Register writes failed instead of reconnecting when the link was down.**
  `async_write_register()` hit a fail-fast `is_connected` check and returned
  failure in about a millisecond, leaving the link down until the next
  scheduled refresh happened to restore it. Measured over 39 drops, that wait
  was 48.4 s median while the reconnect itself took 1.1 s — the delay was an
  artifact of nothing asking to reconnect, not a cost of the radio. Writes now
  call `ensure_connected()` first. Reads keep the old behaviour deliberately:
  reconnecting them eagerly would triple the connect rate, and connects are
  where the remaining failures live.
- **Abort paths disagreed.** Only the `is_connected` pre-check set
  `connection_lost`; the two that actually fire on an ATT `0x0e` did not, and
  the batch-splitting path returned `data={}`, discarding every batch that had
  already landed.

### Changed

- Routine link drops log at INFO rather than WARNING. The SRNE BT-2 module
  closes the link roughly every 266 s on its own — device behaviour, not a
  fault — and logging it at WARNING put about 24 lines an hour in the log
  describing expected behaviour, burying the drops that are not expected. A
  repeat drop while failures are accumulating still warns.
- `UpdateFailed`'s `retry_after` hint is applied only where supported. It
  landed in Home Assistant 2025.11; on older versions the keyword raises
  `TypeError` and turns a handled error into a crash.

### Removed

- The unused write queue in `TransactionManagerService` (`queue_write`,
  `next_transaction`, `has_pending_writes`, `get_queue_size`) and the
  `WriteTransaction` DTO that fed only it. Nothing outside its own unit tests
  ever called it — `async_write_register()` always went straight to the use
  case. It read like coordination that existed, which is worse than none.

### Known limitations

- The ~266 s drop itself is device-side. The vendor's own app carries no BLE
  keepalive either; it recovers rather than prevents.
- ATT `0x0e` on writes is not retried. `TransportConnectionLostError` covers
  both "the module rejected the write" and "the link is dead", and retrying the
  second is useless. Separating them needs distinct exception types at the
  transport layer.

[Unreleased]: https://github.com/krimsonkla/srne_ble_modbus/compare/v0.6.0...HEAD
[0.6.0]: https://github.com/krimsonkla/srne_ble_modbus/releases/tag/v0.6.0
