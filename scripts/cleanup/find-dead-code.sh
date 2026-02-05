#!/bin/bash
# Find unused code in the codebase
# Usage: ./scripts/cleanup/find-dead-code.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
REPORTS_DIR="$PROJECT_ROOT/reports/cleanup"

# Create reports directory
mkdir -p "$REPORTS_DIR"

echo "Finding unused code..."
echo "Project root: $PROJECT_ROOT"
echo "Reports directory: $REPORTS_DIR"
echo ""

# Check if vulture is installed
if ! command -v vulture &> /dev/null; then
    echo "⚠ vulture not found. Installing..."
    pip install vulture
fi

# Run vulture to find dead code
vulture "$PROJECT_ROOT/custom_components" \
  --min-confidence 80 \
  --sort-by-size \
  --exclude "*/tests/*,*/.venv/*,*/.devenv/*,*/node_modules/*" \
  > "$REPORTS_DIR/dead-code.txt" 2>&1 || true

# Count issues
ISSUE_COUNT=$(wc -l < "$REPORTS_DIR/dead-code.txt" | tr -d ' ')

echo "✓ Analysis complete"
echo "Found $ISSUE_COUNT potential unused code items"
echo "Report saved to: $REPORTS_DIR/dead-code.txt"
echo ""

# Show summary
if [ "$ISSUE_COUNT" -gt 0 ]; then
    echo "Top 10 issues:"
    head -10 "$REPORTS_DIR/dead-code.txt"
    echo ""
    echo "Review the full report for details."
else
    echo "✓ No unused code found!"
fi
