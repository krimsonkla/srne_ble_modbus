"""Characterization tests for existing behavior.

Characterization tests capture the current behavior of the system as executable
specifications. These tests:

1. Document how the system currently works
2. Protect against unintended changes during refactoring
3. Must pass 100% before and after each refactoring phase
4. Are NOT unit tests - they test actual integration behavior

If a characterization test fails during refactoring:
- STOP immediately
- Investigate why behavior changed
- Either:
  a) Fix the regression (behavior should not have changed)
  b) Update the test if behavior change was intentional (with documentation)

These tests are the safety net for our refactoring work.
"""
