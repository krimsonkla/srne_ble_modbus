"""Test script to verify exact command bytes being sent.

This script verifies that we're generating EXACTLY the same bytes
as the user's working command: 01030100000445f5
"""

import sys
import struct

# Add parent directory to path
sys.path.insert(0, "/Users/jrisch/git/krimsonkla/srne_ble_modbus")

from custom_components.srne_inverter.infrastructure.protocol.modbus_crc16 import (
    ModbusCRC16,
)
from custom_components.srne_inverter.infrastructure.protocol.modbus_rtu_protocol import (
    ModbusRTUProtocol,
)
from custom_components.srne_inverter.const import DEFAULT_SLAVE_ID


def test_protocol_layer():
    """Test ModbusRTUProtocol command generation."""
    print("\n=== PROTOCOL LAYER TEST ===")

    crc = ModbusCRC16()
    protocol = ModbusRTUProtocol(crc, slave_id=DEFAULT_SLAVE_ID)

    # Build command for register 0x0100, count=4
    command = protocol.build_read_command(0x0100, 4)

    print(f"Register: 0x0100")
    print(f"Count: 4")
    print(f"Slave ID: {DEFAULT_SLAVE_ID}")
    print(f"\nGenerated command: {command.hex()}")
    print(f"Expected command:  01030100000445f5")
    print(f"\nMatch: {command.hex() == '01030100000445f5'}")

    # Break down the command
    print("\n=== BYTE BREAKDOWN ===")
    print(f"Byte 0 (Slave ID):    0x{command[0]:02x} (expected: 0x01)")
    print(f"Byte 1 (Function):    0x{command[1]:02x} (expected: 0x03)")
    print(f"Byte 2 (Addr High):   0x{command[2]:02x} (expected: 0x01)")
    print(f"Byte 3 (Addr Low):    0x{command[3]:02x} (expected: 0x00)")
    print(f"Byte 4 (Count High):  0x{command[4]:02x} (expected: 0x00)")
    print(f"Byte 5 (Count Low):   0x{command[5]:02x} (expected: 0x04)")
    print(f"Byte 6 (CRC Low):     0x{command[6]:02x} (expected: 0x45)")
    print(f"Byte 7 (CRC High):    0x{command[7]:02x} (expected: 0xf5)")

    return command


def test_protocol_with_different_params():
    """Test protocol with different register addresses."""
    print("\n\n=== PROTOCOL PARAMETER VARIATION TEST ===")

    crc = ModbusCRC16()
    protocol = ModbusRTUProtocol(crc, slave_id=DEFAULT_SLAVE_ID)

    # Test with register 0x0100, count=4
    command = protocol.build_read_command(0x0100, 4)

    print(f"Register: 0x0100")
    print(f"Count: 4")
    print(f"Slave ID: {DEFAULT_SLAVE_ID}")
    print(f"\nGenerated command: {command.hex()}")
    print(f"Expected command:  01030100000445f5")
    print(f"\nMatch: {command.hex() == '01030100000445f5'}")

    return command


def test_manual_construction():
    """Manually construct the command to verify CRC calculation."""
    print("\n\n=== MANUAL CONSTRUCTION TEST ===")

    # Build frame manually
    slave_id = 0x01
    function_code = 0x03
    register = 0x0100
    count = 0x0004

    # Pack using big-endian for address and count
    frame = struct.pack(">BBHH", slave_id, function_code, register, count)
    print(f"Frame without CRC: {frame.hex()}")

    # Calculate CRC using proper implementation
    crc_calculator = ModbusCRC16()
    crc_value = crc_calculator.calculate(frame)
    print(f"Calculated CRC: 0x{crc_value:04x}")

    # Append CRC in little-endian
    full_frame = frame + struct.pack("<H", crc_value)
    print(f"\nFull frame: {full_frame.hex()}")
    print(f"Expected:   01030100000445f5")
    print(f"\nMatch: {full_frame.hex() == '01030100000445f5'}")

    return full_frame


def verify_crc():
    """Verify CRC calculation against known good value."""
    print("\n\n=== CRC VERIFICATION ===")

    # Use proper CRC implementation
    crc_calculator = ModbusCRC16()

    # Data without CRC: 01 03 01 00 00 04
    data = bytes([0x01, 0x03, 0x01, 0x00, 0x00, 0x04])
    crc = crc_calculator.calculate(data)

    # Expected CRC: 0xf545 (little-endian) = bytes [0x45, 0xf5]
    print(f"Data: {data.hex()}")
    print(f"Calculated CRC: 0x{crc:04x}")
    print(f"Expected CRC:   0xf545")
    print(f"CRC bytes (LE): {struct.pack('<H', crc).hex()}")
    print(f"Expected bytes: 45f5")
    print(f"\nMatch: {crc == 0xf545}")


if __name__ == "__main__":
    print("=" * 60)
    print("COMMAND BYTE VERIFICATION TEST")
    print("=" * 60)
    print("\nUser's working command: 01030100000445f5")
    print("Testing if our code generates the same bytes...")

    # Run all tests
    cmd1 = test_protocol_layer()
    cmd2 = test_protocol_with_different_params()
    cmd3 = test_manual_construction()
    verify_crc()

    # Final verification
    print("\n" + "=" * 60)
    print("FINAL VERIFICATION")
    print("=" * 60)

    expected = "01030100000445f5"
    all_match = (
        cmd1.hex() == expected and cmd2.hex() == expected and cmd3.hex() == expected
    )

    if all_match:
        print("\n✓ SUCCESS: All methods generate correct bytes!")
        print(f"✓ Command: {expected}")
    else:
        print("\n✗ FAILURE: Byte mismatch detected!")
        print(f"Expected: {expected}")
        print(f"Protocol: {cmd1.hex()}")
        print(f"Protocol2: {cmd2.hex()}")
        print(f"Manual:   {cmd3.hex()}")

        # Find where they differ
        for i, (e, p, c, m) in enumerate(
            zip(expected, cmd1.hex(), cmd2.hex(), cmd3.hex())
        ):
            if e != p or e != c or e != m:
                print(f"\nDifference at position {i}:")
                print(f"  Expected: {e}")
                print(f"  Protocol: {p}")
                print(f"  Const:    {c}")
                print(f"  Manual:   {m}")
