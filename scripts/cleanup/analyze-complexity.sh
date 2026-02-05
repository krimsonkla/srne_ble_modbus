#!/bin/bash
# Analyze code complexity metrics
# Usage: ./scripts/cleanup/analyze-complexity.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
REPORTS_DIR="$PROJECT_ROOT/reports/cleanup"

# Create reports directory
mkdir -p "$REPORTS_DIR"

echo "Analyzing code complexity..."
echo "Project root: $PROJECT_ROOT"
echo "Reports directory: $REPORTS_DIR"
echo ""

# Check if radon is installed
if ! command -v radon &> /dev/null; then
    echo "⚠ radon not found. Installing..."
    pip install radon
fi

# Cyclomatic complexity
echo "Calculating cyclomatic complexity..."
radon cc "$PROJECT_ROOT/custom_components/srne_inverter" \
  -a \
  -nb \
  -s \
  --json > "$REPORTS_DIR/complexity.json"

# Also get human-readable format
radon cc "$PROJECT_ROOT/custom_components/srne_inverter" \
  -a \
  -s \
  > "$REPORTS_DIR/complexity.txt"

# Maintainability index
echo "Calculating maintainability index..."
radon mi "$PROJECT_ROOT/custom_components/srne_inverter" \
  -s \
  --json > "$REPORTS_DIR/maintainability.json"

radon mi "$PROJECT_ROOT/custom_components/srne_inverter" \
  -s \
  > "$REPORTS_DIR/maintainability.txt"

# Raw metrics (lines of code, etc.)
echo "Calculating raw metrics..."
radon raw "$PROJECT_ROOT/custom_components/srne_inverter" \
  -s \
  --json > "$REPORTS_DIR/raw-metrics.json"

# Generate summary report
python3 << 'EOF' > "$REPORTS_DIR/complexity-summary.txt"
import json
from pathlib import Path

# Load complexity data
with open("reports/cleanup/complexity.json") as f:
    complexity = json.load(f)

# Load maintainability data
with open("reports/cleanup/maintainability.json") as f:
    maintainability = json.load(f)

# Calculate statistics
all_complexities = []
for file_data in complexity.values():
    for item in file_data:
        if isinstance(item, dict) and "complexity" in item:
            all_complexities.append(item["complexity"])

if all_complexities:
    avg_complexity = sum(all_complexities) / len(all_complexities)
    max_complexity = max(all_complexities)
    high_complexity = [c for c in all_complexities if c > 10]
else:
    avg_complexity = 0
    max_complexity = 0
    high_complexity = []

# Find files with low maintainability
low_maintainability = []
for file, data in maintainability.items():
    if isinstance(data, dict) and "mi" in data:
        mi = data["mi"]
        if mi < 20:  # Low maintainability threshold
            low_maintainability.append((file, mi))

low_maintainability.sort(key=lambda x: x[1])

# Generate report
report = f"""Code Complexity Analysis Report
Generated: {Path("reports/cleanup/complexity-summary.txt").stat().st_mtime}
=====================================

Cyclomatic Complexity:
- Average: {avg_complexity:.2f}
- Maximum: {max_complexity}
- Functions with CC > 10: {len(high_complexity)}

Maintainability:
- Files with MI < 20: {len(low_maintainability)}

Top 5 files needing refactoring:
"""

for file, mi in low_maintainability[:5]:
    report += f"\n- {file}: MI = {mi:.2f}"

report += """

Recommendations:
- Target functions with CC > 10 for refactoring
- Focus on files with MI < 20 for improvement
- Consider breaking down large functions

See detailed reports:
- complexity.json (cyclomatic complexity by function)
- maintainability.json (maintainability index by file)
- raw-metrics.json (lines of code, comments, etc.)
"""

print(report)
EOF

echo "✓ Analysis complete"
echo ""
cat "$REPORTS_DIR/complexity-summary.txt"
