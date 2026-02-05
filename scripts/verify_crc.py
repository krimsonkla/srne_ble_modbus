#!/usr/bin/env python3
"""Verify CRC calculations."""
import struct


def calculate_crc16(data: bytes) -> int:
    """Coordinator CRC algorithm."""
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc


# Test cases
test_cases = [
    bytes([0x01, 0x03, 0x01, 0x00, 0x00, 0x01]),
    bytes([0x01, 0x03, 0x01, 0x00, 0x00, 0x02]),
    bytes([0x01, 0x06, 0x01, 0x00, 0x01, 0x2C]),
]

print("CRC Verification:")
print("=" * 70)
for data in test_cases:
    crc = calculate_crc16(data)
    # Pack as little-endian (as coordinator does)
    crc_bytes = struct.pack("<H", crc)
    # Read back as big-endian (wrong interpretation)
    crc_swapped = struct.unpack(">H", crc_bytes)[0]

    print(f"\nData: {data.hex()}")
    print(f"  CRC (correct):     0x{crc:04X} ({crc})")
    print(f"  CRC bytes (LE):    {crc_bytes.hex()}")
    print(f"  CRC (swapped/BE):  0x{crc_swapped:04X} ({crc_swapped})")
