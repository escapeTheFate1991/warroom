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
