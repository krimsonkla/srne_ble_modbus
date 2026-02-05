#!/usr/bin/env python3
"""Quick verification script for Modbus protocol implementation.

This script verifies that the ModbusRTUProtocol generates the exact same
command bytes as the working BLE debug tool command: 01030100000445f5
"""

import sys
import struct


# Simulate ModbusCRC16 calculate method
def calculate_crc(data):
    """Standard Modbus CRC-16 calculation."""
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc


def build_read_command_struct(slave_id, start_address, count):
    """Build command using struct.pack (like ModbusRTUProtocol)."""
    # Build frame: Slave ID + Function + Address (BE) + Count (BE)
    data = struct.pack(">BBHH", slave_id, 0x03, start_address, count)

    # Calculate and append CRC (little-endian)
    crc_value = calculate_crc(data)
    frame = data + struct.pack("<H", crc_value)

    return frame


def build_read_command_bytes(slave_id, register, count):
    """Build command using bytes manipulation (like const.py)."""
    frame = bytes(
        [
            slave_id,
            0x03,  # FUNC_READ_HOLDING
            (register >> 8) & 0xFF,
            register & 0xFF,
            (count >> 8) & 0xFF,
            count & 0xFF,
        ]
    )

    crc = calculate_crc(frame)
    frame += bytes([crc & 0xFF, (crc >> 8) & 0xFF])

    return frame


def main():
    print("=" * 80)
    print("MODBUS RTU PROTOCOL VERIFICATION")
    print("=" * 80)
    print()

    # Test parameters from user's working command
    slave_id = 0x01
    register = 0x0100
    count = 0x0004
    expected_command = "01030100000445f5"

    print(f"Test Parameters:")
    print(f"  Slave ID: 0x{slave_id:02X}")
    print(f"  Register: 0x{register:04X}")
    print(f"  Count: {count}")
    print(f"  Expected: {expected_command}")
    print()

    # Test struct.pack method (ModbusRTUProtocol)
    print("Method 1: struct.pack (ModbusRTUProtocol)")
    cmd1 = build_read_command_struct(slave_id, register, count)
    print(f"  Generated: {cmd1.hex()}")
    print(f"  Match: {cmd1.hex() == expected_command}")
    print()

    # Test bytes method (const.py)
    print("Method 2: bytes manipulation (const.py)")
    cmd2 = build_read_command_bytes(slave_id, register, count)
    print(f"  Generated: {cmd2.hex()}")
    print(f"  Match: {cmd2.hex() == expected_command}")
    print()

    # Detailed breakdown
    print("Breakdown of expected command:")
    expected_bytes = bytes.fromhex(expected_command)
    print(f"  [0] Slave ID: 0x{expected_bytes[0]:02X}")
    print(f"  [1] Function: 0x{expected_bytes[1]:02X}")
    print(f"  [2-3] Address: 0x{(expected_bytes[2] << 8) | expected_bytes[3]:04X}")
    print(f"  [4-5] Count: 0x{(expected_bytes[4] << 8) | expected_bytes[5]:04X}")
    print(f"  [6-7] CRC: 0x{(expected_bytes[7] << 8) | expected_bytes[6]:04X}")
    print()

    # Detailed breakdown of generated command
    print("Breakdown of generated command (Method 1):")
    print(f"  [0] Slave ID: 0x{cmd1[0]:02X}")
    print(f"  [1] Function: 0x{cmd1[1]:02X}")
    print(f"  [2-3] Address: 0x{(cmd1[2] << 8) | cmd1[3]:04X}")
    print(f"  [4-5] Count: 0x{(cmd1[4] << 8) | cmd1[5]:04X}")
    print(f"  [6-7] CRC: 0x{(cmd1[7] << 8) | cmd1[6]:04X}")
    print()

    # Test with count=1
    print("=" * 80)
    print("Test with count=1 (typical single register read)")
    print("=" * 80)
    print()

    count_single = 1
    cmd_single = build_read_command_struct(slave_id, register, count_single)
    print(
        f"Parameters: slave=0x{slave_id:02X}, register=0x{register:04X}, count={count_single}"
    )
    print(f"Generated: {cmd_single.hex()}")
    print()

    # Manual CRC verification
    print("=" * 80)
    print("CRC Verification")
    print("=" * 80)
    print()

    data_portion = expected_bytes[:-2]
    calculated_crc = calculate_crc(data_portion)
    received_crc = (expected_bytes[7] << 8) | expected_bytes[6]

    print(f"Data portion: {data_portion.hex()}")
    print(f"Calculated CRC: 0x{calculated_crc:04X}")
    print(f"Expected CRC: 0x{received_crc:04X}")
    print(f"CRC Match: {calculated_crc == received_crc}")
    print()

    # Return status
    if cmd1.hex() == expected_command and cmd2.hex() == expected_command:
        print("✓ SUCCESS: Both methods generate correct Modbus RTU command")
        return 0
    else:
        print("✗ FAILURE: Command generation does not match expected")
        return 1


if __name__ == "__main__":
    sys.exit(main())
