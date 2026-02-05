#!/bin/bash

# Test runner script for SRNE Inverter integration
# Run from repository root: ./tests/run_tests.sh

set -e

echo "=========================================="
echo "SRNE Inverter Integration Test Suite"
echo "=========================================="
echo ""

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo "Error: pytest not found. Install with: pip install pytest pytest-asyncio"
    exit 1
fi

# Run tests with verbose output
echo "Running test suite..."
echo ""

python -m pytest tests/ -v --tb=short

echo ""
echo "=========================================="
echo "Test Results Summary"
echo "=========================================="
echo ""
