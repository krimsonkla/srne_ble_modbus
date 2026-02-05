"""Infrastructure layer for SRNE Inverter integration.

The infrastructure layer contains implementations of domain interfaces:
- Protocol implementations (Modbus RTU)
- Transport implementations (BLE, Serial, TCP)
- Repository implementations (Home Assistant Store)
- External service adapters

This layer depends on:
- Domain layer (interfaces and entities)
- External libraries (bleak, homeassistant, etc.)

But domain layer does NOT depend on infrastructure.
"""
