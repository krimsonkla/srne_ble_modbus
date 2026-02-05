#!/bin/bash
# Find duplicate code in the codebase
# Usage: ./scripts/cleanup/find-duplicates.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
REPORTS_DIR="$PROJECT_ROOT/reports/cleanup"

# Create reports directory
mkdir -p "$REPORTS_DIR"

echo "Finding duplicate code..."
echo "Project root: $PROJECT_ROOT"
echo "Reports directory: $REPORTS_DIR"
echo ""

# Method 1: pylint duplicate-code checker
echo "Running pylint duplicate-code checker..."
pylint "$PROJECT_ROOT/custom_components/srne_inverter" \
  --disable=all \
  --enable=duplicate-code \
  --min-similarity-lines=5 \
  > "$REPORTS_DIR/duplicates-pylint.txt" 2>&1 || true

# Count duplicates from pylint
DUPE_COUNT=$(grep -c "Similar lines" "$REPORTS_DIR/duplicates-pylint.txt" || echo "0")

echo "✓ Pylint analysis complete"
echo "Found $DUPE_COUNT duplicate code blocks (5+ lines)"
echo ""

# Method 2: Simple AST-based duplicate function detection
echo "Finding duplicate function signatures..."
python3 << 'EOF' > "$REPORTS_DIR/duplicates-functions.json"
import ast
import json
from pathlib import Path
from collections import defaultdict
from typing import List, Dict, Tuple

def get_function_signature(node: ast.FunctionDef) -> str:
    """Get normalized function signature."""
    args = [arg.arg for arg in node.args.args]
    return f"{node.name}({', '.join(args)})"

def find_duplicate_functions(directory: Path) -> List[Dict]:
    """Find functions with identical signatures."""
    functions = defaultdict(list)

    for file in directory.rglob("*.py"):
        if any(skip in str(file) for skip in ["test_", "__pycache__", ".venv", ".devenv"]):
            continue

        try:
            tree = ast.parse(file.read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    sig = get_function_signature(node)
                    functions[sig].append({
                        "file": str(file.relative_to(directory.parent)),
                        "line": node.lineno,
                        "signature": sig
                    })
        except Exception as e:
            continue

    # Filter to only duplicates
    duplicates = {
        sig: locations
        for sig, locations in functions.items()
        if len(locations) > 1
    }

    return [
        {
            "signature": sig,
            "count": len(locations),
            "locations": locations
        }
        for sig, locations in duplicates.items()
    ]

if __name__ == "__main__":
    base = Path("custom_components/srne_inverter")
    dupes = find_duplicate_functions(base)
    print(json.dumps(dupes, indent=2))
EOF

FUNC_COUNT=$(python3 -c "import json; data=json.load(open('$REPORTS_DIR/duplicates-functions.json')); print(len(data))")

echo "✓ Function analysis complete"
echo "Found $FUNC_COUNT duplicate function signatures"
echo ""

# Generate summary report
cat > "$REPORTS_DIR/duplicates-summary.txt" << EOF
Duplicate Code Analysis Report
Generated: $(date)
=====================================

Pylint Duplicate Blocks: $DUPE_COUNT
Duplicate Function Signatures: $FUNC_COUNT

See detailed reports:
- duplicates-pylint.txt (similar code blocks)
- duplicates-functions.json (duplicate function signatures)

Review these files and create cleanup tasks for consolidation.
EOF

echo "✓ Summary saved to: $REPORTS_DIR/duplicates-summary.txt"
cat "$REPORTS_DIR/duplicates-summary.txt"
