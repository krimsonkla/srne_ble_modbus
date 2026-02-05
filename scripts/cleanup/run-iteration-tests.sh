#!/bin/bash
# Run comprehensive tests for a cleanup iteration
# Usage: ./scripts/cleanup/run-iteration-tests.sh <iteration-number>

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
ITERATION=$1

if [ -z "$ITERATION" ]; then
    echo "Usage: $0 <iteration-number>"
    echo "Example: $0 5"
    exit 1
fi

REPORTS_DIR="$PROJECT_ROOT/reports/iterations/iteration-$ITERATION"
mkdir -p "$REPORTS_DIR"

cd "$PROJECT_ROOT"

echo "Running tests for iteration $ITERATION..."
echo "Project root: $PROJECT_ROOT"
echo "Reports directory: $REPORTS_DIR"
echo ""

# Check if pytest is available
if ! command -v pytest &> /dev/null; then
    echo "⚠ pytest not found. Installing..."
    pip install pytest pytest-cov pytest-html pytest-benchmark
fi

# Run comprehensive test suite
echo "Running test suite..."
pytest tests/ \
  -v \
  --cov=custom_components \
  --cov-report=html:"$REPORTS_DIR/coverage" \
  --cov-report=json:"$REPORTS_DIR/coverage.json" \
  --cov-report=term \
  --html="$REPORTS_DIR/report.html" \
  --self-contained-html \
  --tb=short

TEST_EXIT_CODE=$?

# Generate test summary
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo ""
    echo "✓ All tests passed!"

    # Extract coverage percentage
    COVERAGE_PCT=$(python3 -c "import json; data=json.load(open('$REPORTS_DIR/coverage.json')); print(f\"{data['totals']['percent_covered']:.2f}\")")

    echo ""
    echo "Test Coverage: $COVERAGE_PCT%"

    # Compare with baseline if it exists
    if [ -f "reports/baseline/coverage.json" ]; then
        echo ""
        echo "Comparing with baseline..."
        python3 << EOF
import json
import sys

with open("reports/baseline/coverage.json") as f:
    baseline = json.load(f)

with open("$REPORTS_DIR/coverage.json") as f:
    current = json.load(f)

baseline_pct = baseline["totals"]["percent_covered"]
current_pct = current["totals"]["percent_covered"]
diff = current_pct - baseline_pct

print(f"Baseline coverage: {baseline_pct:.2f}%")
print(f"Current coverage:  {current_pct:.2f}%")
print(f"Difference:        {diff:+.2f}%")

if diff < -1.0:
    print("\n⚠ WARNING: Coverage decreased significantly!")
    sys.exit(1)
elif diff > 0:
    print("\n✓ Coverage improved!")
else:
    print("\n✓ Coverage maintained")
EOF
    fi

    # Create iteration summary
    cat > "$REPORTS_DIR/summary.txt" << EOF
Iteration $ITERATION Test Summary
Generated: $(date)
=====================================

Status: PASSED ✓
Test Exit Code: $TEST_EXIT_CODE
Coverage: $COVERAGE_PCT%

All tests passed successfully.

Reports:
- HTML Test Report: file://$REPORTS_DIR/report.html
- Coverage Report: file://$REPORTS_DIR/coverage/index.html
- JSON Coverage: $REPORTS_DIR/coverage.json

Next steps:
1. Review coverage report
2. Submit for code review
3. Merge changes
EOF

    echo ""
    cat "$REPORTS_DIR/summary.txt"

    exit 0
else
    echo ""
    echo "✗ Tests failed!"

    # Create failure summary
    cat > "$REPORTS_DIR/summary.txt" << EOF
Iteration $ITERATION Test Summary
Generated: $(date)
=====================================

Status: FAILED ✗
Test Exit Code: $TEST_EXIT_CODE

Tests failed. Review the test report for details.

Reports:
- HTML Test Report: file://$REPORTS_DIR/report.html
- Coverage Report: file://$REPORTS_DIR/coverage/index.html

Next steps:
1. Review test failures in report.html
2. Fix issues
3. Re-run tests
4. Consider rolling back changes
EOF

    cat "$REPORTS_DIR/summary.txt"

    exit 1
fi
