"""Application layer for SRNE Inverter integration.

This layer contains use cases and application services that orchestrate
domain logic and infrastructure. It sits between the presentation layer
(coordinator) and the domain/infrastructure layers.

Architecture Pattern: Clean Architecture / Hexagonal Architecture
- Use Cases: Application-specific business rules
- Services: Reusable application logic
- DTOs: Data transfer objects for layer boundaries

Extract application services from coordinator.
"""
