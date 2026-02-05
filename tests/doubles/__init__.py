"""Test doubles for unit testing.

Test doubles are fake implementations of interfaces used for testing.
They're faster and more reliable than mocking, and they implement the
actual interface contracts.

Types of test doubles:
- Fake: Lightweight working implementation (e.g., in-memory storage)
- Stub: Returns predetermined values
- Spy: Records calls for verification
- Mock: Verifies interactions (use unittest.mock for this)

We primarily use Fakes because they:
- Actually implement the interface
- Can be reused across many tests
- Are self-testing (can have their own tests)
- Provide realistic behavior

Example:
    >>> from tests.doubles import FakeTransport
    >>> transport = FakeTransport()
    >>> transport.add_response(command, expected_response)
    >>> response = await transport.send(command)
    >>> assert response == expected_response
"""
