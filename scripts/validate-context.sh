#!/bin/bash
# Friday Context Validation Script
# Checks context freshness and consistency

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FRIDAY_CTX="$PROJECT_ROOT/bin/friday-ctx"

if [ ! -x "$FRIDAY_CTX" ]; then
    echo "❌ friday-ctx not found or not executable"
    exit 1
fi

cd "$PROJECT_ROOT"
export PATH="$PROJECT_ROOT/bin:$PATH"

echo "🔍 Validating context system..."

# Check index status
echo "📊 Context index status:"
"$FRIDAY_CTX" status

# Validate context files exist
echo -e "\n📁 Checking core context files:"

REQUIRED_FILES=(
    ".context/metadata.yaml"
    ".context/architecture.md"
    ".context/patterns.md"
    ".context/apis.md"
    ".context/frontend.md"
    ".context/development.md"
)

missing_files=0
for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ $file"
    else
        echo "❌ $file (missing)"
        missing_files=$((missing_files + 1))
    fi
done

# Check for stale context
echo -e "\n⏰ Checking context freshness:"
git_last_commit=$(git log -1 --format="%at")
index_db=".context/index.db"

if [ -f "$index_db" ]; then
    index_timestamp=$(stat -f "%m" "$index_db" 2>/dev/null || stat -c "%Y" "$index_db" 2>/dev/null)
    
    if [ "$git_last_commit" -gt "$index_timestamp" ]; then
        echo "⚠️ Context index is stale (older than latest commit)"
        echo "Run: friday-ctx index"
    else
        echo "✅ Context index is fresh"
    fi
else
    echo "❌ Context index not found"
    missing_files=$((missing_files + 1))
fi

echo -e "\n📝 Validation summary:"
if [ "$missing_files" -eq 0 ]; then
    echo "✅ All context files present and valid"
    exit 0
else
    echo "❌ $missing_files issues found"
    exit 1
fi
