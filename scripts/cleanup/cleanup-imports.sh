#!/bin/bash
# Safely clean up unused imports
# Usage: ./scripts/cleanup/cleanup-imports.sh [--dry-run]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DRY_RUN=false

# Parse arguments
if [ "$1" = "--dry-run" ]; then
    DRY_RUN=true
    echo "🔍 DRY RUN MODE - No changes will be made"
    echo ""
fi

cd "$PROJECT_ROOT"

echo "Cleaning up imports..."
echo "Project root: $PROJECT_ROOT"
echo ""

# Check if tools are installed
if ! command -v autoflake &> /dev/null; then
    echo "⚠ autoflake not found. Installing..."
    pip install autoflake
fi

if ! command -v isort &> /dev/null; then
    echo "⚠ isort not found. Installing..."
    pip install isort
fi

# Backup before making changes
if [ "$DRY_RUN" = false ]; then
    echo "Creating backup commit..."
    git add .
    git commit -m "backup: Before import cleanup" --allow-empty
    BACKUP_COMMIT=$(git rev-parse HEAD)
    echo "✓ Backup commit: $BACKUP_COMMIT"
    echo ""
fi

# Step 1: Remove unused imports
echo "Step 1: Removing unused imports..."
if [ "$DRY_RUN" = true ]; then
    autoflake \
      --remove-all-unused-imports \
      --recursive \
      --exclude="__init__.py,test_*.py,conftest.py" \
      custom_components/srne_inverter/
else
    autoflake \
      --remove-all-unused-imports \
      --in-place \
      --recursive \
      --exclude="__init__.py,test_*.py,conftest.py" \
      custom_components/srne_inverter/
fi

# Step 2: Sort imports
echo "Step 2: Sorting imports with isort..."
if [ "$DRY_RUN" = true ]; then
    isort custom_components/srne_inverter/ --check-only --diff
else
    isort custom_components/srne_inverter/
fi

if [ "$DRY_RUN" = true ]; then
    echo ""
    echo "✓ Dry run complete. Review the changes above."
    echo "Run without --dry-run to apply changes."
    exit 0
fi

# Step 3: Verify no breakage
echo ""
echo "Step 3: Verifying changes..."
echo "Running tests..."

if pytest tests/ -v --tb=short; then
    echo ""
    echo "✓ All tests passed!"
    echo ""
    echo "Step 4: Committing changes..."
    git add .
    git commit -m "refactor: Clean up unused imports

- Removed unused imports across codebase
- Sorted imports with isort
- All tests passing

Co-Authored-By: claude-flow <ruv@ruv.net>"

    echo "✓ Import cleanup complete!"
    echo ""
    echo "Summary:"
    git show --stat
else
    echo ""
    echo "✗ Tests failed! Rolling back..."
    git reset --hard "$BACKUP_COMMIT"

    echo ""
    echo "⚠ Import cleanup failed. Changes have been rolled back."
    echo "Please review test failures and try again."
    exit 1
fi
