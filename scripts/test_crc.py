#!/usr/bin/env python3
"""Test CRC values against coordinator implementation."""


def calculate_crc16(data: bytes) -> int:
    """Original coordinator CRC algorithm."""
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc


# Test the three cases from the tests
test_cases = [
    (bytes([0x01, 0x03, 0x01, 0x00, 0x00, 0x01]), 0xD404),
    (bytes([0x01, 0x03, 0x01, 0x00, 0x00, 0x02]), 0x2405),
    (bytes([0x01, 0x06, 0x01, 0x00, 0x01, 0x2C]), 0x4B02),
]

print("Testing CRC values:")
for data, expected_crc in test_cases:
    actual_crc = calculate_crc16(data)
    print(f"Data: {data.hex()}")
    print(f"  Expected: 0x{expected_crc:04X} ({expected_crc})")
    print(f"  Actual:   0x{actual_crc:04X} ({actual_crc})")
    print(f"  Match: {actual_crc == expected_crc}")
    print()
