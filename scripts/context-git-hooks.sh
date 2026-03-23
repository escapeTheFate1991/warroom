#!/bin/bash
# Friday Context Management Git Hooks Setup
# Automatically update context index on git events

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HOOKS_DIR="$PROJECT_ROOT/.git/hooks"

# Ensure hooks directory exists
mkdir -p "$HOOKS_DIR"

echo "Setting up Friday Context git hooks..."

# Post-commit hook - update context after commits
cat > "$HOOKS_DIR/post-commit" << 'EOF'
#!/bin/bash
# Friday Context post-commit hook
# Updates context index after commits

PROJECT_ROOT="$(git rev-parse --show-toplevel)"
FRIDAY_CTX="$PROJECT_ROOT/bin/friday-ctx"

if [ -x "$FRIDAY_CTX" ]; then
    echo "🔄 Updating context index after commit..."
    cd "$PROJECT_ROOT"
    export PATH="$PROJECT_ROOT/bin:$PATH"
    "$FRIDAY_CTX" index 2>/dev/null || echo "⚠️ Context index update failed"
fi
EOF

# Post-checkout hook - update context after branch switches
cat > "$HOOKS_DIR/post-checkout" << 'EOF'
#!/bin/bash
# Friday Context post-checkout hook  
# Updates context index after branch switches

# Only run on branch switches (not file checkouts)
if [ "$3" = "1" ]; then
    PROJECT_ROOT="$(git rev-parse --show-toplevel)"
    FRIDAY_CTX="$PROJECT_ROOT/bin/friday-ctx"
    
    if [ -x "$FRIDAY_CTX" ]; then
        echo "🔄 Updating context index after branch switch..."
        cd "$PROJECT_ROOT"
        export PATH="$PROJECT_ROOT/bin:$PATH"
        "$FRIDAY_CTX" index 2>/dev/null || echo "⚠️ Context index update failed"
    fi
fi
EOF

# Post-merge hook - update context after merges
cat > "$HOOKS_DIR/post-merge" << 'EOF'
#!/bin/bash
# Friday Context post-merge hook
# Updates context index after merges

PROJECT_ROOT="$(git rev-parse --show-toplevel)"
FRIDAY_CTX="$PROJECT_ROOT/bin/friday-ctx"

if [ -x "$FRIDAY_CTX" ]; then
    echo "🔄 Updating context index after merge..."
    cd "$PROJECT_ROOT"
    export PATH="$PROJECT_ROOT/bin:$PATH"
    "$FRIDAY_CTX" index 2>/dev/null || echo "⚠️ Context index update failed"
fi
EOF

# Make hooks executable
chmod +x "$HOOKS_DIR/post-commit"
chmod +x "$HOOKS_DIR/post-checkout" 
chmod +x "$HOOKS_DIR/post-merge"

echo "✅ Git hooks installed:"
echo "  - post-commit: Updates context after commits"
echo "  - post-checkout: Updates context after branch switches"
echo "  - post-merge: Updates context after merges"

# Create context validation script
cat > "$PROJECT_ROOT/scripts/validate-context.sh" << 'EOF'
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
EOF

chmod +x "$PROJECT_ROOT/scripts/validate-context.sh"

echo "✅ Context validation script created at scripts/validate-context.sh"

# Setup CI/CD integration hints
cat > "$PROJECT_ROOT/.context/ci-integration.md" << 'EOF'
# Friday Context CI/CD Integration

## GitHub Actions Integration

Add to `.github/workflows/context-validation.yml`:

```yaml
name: Context Validation

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  validate-context:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Validate Context System
      run: |
        chmod +x scripts/validate-context.sh
        ./scripts/validate-context.sh
    
    - name: Test Context Search
      run: |
        export PATH="$PWD/bin:$PATH"
        friday-ctx index
        friday-ctx find "authentication" | head -5
```

## Docker Integration

Add to Dockerfile for context-aware builds:

```dockerfile
# Copy context system
COPY .context/ .context/
COPY bin/friday-ctx bin/
COPY scripts/ scripts/

# Validate context during build
RUN chmod +x scripts/validate-context.sh && \
    ./scripts/validate-context.sh
```

## Local Development

Add to package.json scripts:

```json
{
  "scripts": {
    "context:validate": "./scripts/validate-context.sh",
    "context:index": "friday-ctx index",
    "context:search": "friday-ctx find"
  }
}
```
EOF

echo "✅ CI/CD integration guide created at .context/ci-integration.md"
echo ""
echo "🚀 Friday Context Management system is now fully set up!"
echo ""
echo "Next steps:"
echo "  1. Test the system: friday-ctx find 'your query'"
echo "  2. Validate setup: ./scripts/validate-context.sh"
echo "  3. Make a commit to test auto-indexing"