# War Room Context System - Usage Guide

## Quick Start

### Installation
The system is ready to use - no additional installation required.

### Access Methods
1. **From project root**: `./warroom-context <command>`
2. **From .context dir**: `python3 warroom_context.py <command>`

## Daily Workflow

### 1. Start Working Session
```bash
# Start with specific task
./warroom-context start "fix JWT authentication bug"

# Start without specific task
./warroom-context start
```

### 2. Get Context When Errors Occur
```bash
# For authentication errors
./warroom-context error "JWT token has expired" backend/app/auth/jwt.py

# For database errors
./warroom-context error "relation 'users' does not exist"

# For frontend errors
./warroom-context error "Hydration failed" frontend/src/components/Auth.tsx
```

### 3. Get Context When Modifying Files
```bash
# When editing auth files
./warroom-context file backend/app/auth/middleware.py

# When editing frontend components
./warroom-context file frontend/src/components/crm/ContactForm.tsx

# When editing API routes
./warroom-context file backend/app/api/crm/contacts.py
```

### 4. Get Session-Based Context
```bash
# See what context is relevant to your current work
./warroom-context session
```

## Maintenance Commands

### Check System Health
```bash
./warroom-context status
```

### Run Maintenance Tasks
```bash
# Scan for drift and clean up cache
./warroom-context maintenance

# Run performance optimization
./warroom-context optimize
```

### Manage Patterns
```bash
# List all context patterns
./warroom-context patterns list

# Add new pattern interactively
./warroom-context patterns add
```

### Drift Detection
```bash
# Scan codebase for changes
./warroom-context drift scan

# Show recent drift alerts
./warroom-context drift alerts

# Get drift summary
./warroom-context drift summary
```

### Cache Management
```bash
# Show cache statistics
./warroom-context cache stats

# Warm cache with common files
./warroom-context cache warm

# Clear all caches
./warroom-context cache clear
```

## Understanding Output

### Context Loading Output
```bash
🔍 Error Context Analysis
📄 Loaded 2 contexts in 8.5ms
⚡ Cache hit rate: 66.7% (2/3)

📋 Relevant Context:

  📄 authentication.md (score: 1.00)
     Reason: Error pattern match: Authentication and JWT-related errors
     Preview: # Authentication & JWT Implementation...

💡 Recommendations:
  • 💡 Check authentication.md for auth-related errors
```

**Key Elements**:
- **Load time**: How long it took to find and load context (should be <20ms)
- **Cache hit rate**: How often context was served from cache vs loaded from disk
- **Relevance score**: How well the context matches your trigger (0.0-1.0)
- **Preview**: First 300 characters of the context file
- **Recommendations**: Suggested actions based on the context

### Status Output
```bash
🤖 War Room Context Engine Status
========================================
Performance Score: 85/100
Cache Hit Rate: 67.5% (27/40 requests)
Context Health: 92/100
Tracked Patterns: 1,247
Recent Alerts: 3

Current Session: a1b2c3d4 (2.3h)
Task: fix JWT authentication bug
Files Modified: 7
Unresolved Errors: 1

Active Subsystems: 4/4
  ✅ Session Tracking
  ✅ Auto Loading
  ✅ Drift Detection  
  ✅ Caching
```

**Key Metrics**:
- **Performance Score**: Overall system performance (0-100)
- **Cache Hit Rate**: How efficiently the cache is working
- **Context Health**: How accurate the context is vs current code (0-100)
- **Session Info**: Current development session details

## Adding New Context

### 1. Create Context Files
Add new `.md` files to `.context/` directory:

```bash
# Example: Create CRM context
cat > .context/crm-architecture.md << 'EOF'
# CRM Architecture

## Contact Management
...

## Deal Pipeline
...
EOF
```

### 2. Add Pattern Matching
```bash
# Interactive pattern addition
./warroom-context patterns add

# Example pattern:
Pattern type: keyword
Pattern: (contact|deal|lead|pipeline|crm)
Description: CRM-related functionality  
Priority: 7
Context files: crm-architecture.md,sales-pipeline.md
```

### 3. Test Pattern
```bash
./warroom-context error "Contact not found in database"
./warroom-context task "add new contact form validation"
```

## Performance Tuning

### Configuration
Edit `.context/engine_config.json`:

```json
{
  "auto_load_enabled": true,
  "drift_detection_enabled": true,
  "cache_enabled": true,
  "session_tracking_enabled": true,
  "max_contexts_per_load": 5,
  "cache_ttl_seconds": 3600,
  "drift_scan_interval_hours": 6,
  "performance_mode": "balanced"
}
```

**Performance Modes**:
- `"fast"`: Minimal drift checking, aggressive caching
- `"balanced"`: Default mode, good performance and accuracy
- `"thorough"`: Full drift checking, more accurate but slower

### Cache Optimization
```bash
# Check cache performance
./warroom-context cache stats

# If hit rate is low (<50%), warm cache
./warroom-context cache warm

# If cache is stale, clear it
./warroom-context cache clear
```

### Drift Management
```bash
# If context health is low (<70%), scan for drift
./warroom-context drift scan

# Fix high-priority alerts
./warroom-context drift alerts
```

## Integration Tips

### Git Hooks
Add to `.git/hooks/post-checkout`:
```bash
#!/bin/bash
# Refresh context after branch changes
cd "$(git rev-parse --show-toplevel)"
./warroom-context maintenance > /dev/null 2>&1 &
```

### Editor Integration
For VS Code, add to `tasks.json`:
```json
{
  "label": "Load Context for Current File",
  "type": "shell",
  "command": "./warroom-context",
  "args": ["file", "${relativeFile}"],
  "group": "build"
}
```

### Development Workflow
```bash
# Start work
./warroom-context start "implement social media sync"

# While coding, get context for errors
./warroom-context error "Instagram API rate limit exceeded"

# When switching files
./warroom-context file backend/app/social/instagram.py

# Before committing, check drift
./warroom-context drift summary

# End of day
./warroom-context status
```

## Troubleshooting

### System Won't Start
```bash
# Check Python installation
python3 --version

# Check file permissions
ls -la warroom-context

# Run with verbose output
python3 .context/warroom_context.py status
```

### Poor Performance
```bash
# Check performance metrics
./warroom-context status

# If cache hit rate is low:
./warroom-context cache warm

# If load times are high (>50ms):
./warroom-context optimize
```

### Context Not Loading
```bash
# Check if patterns exist
./warroom-context patterns list

# Test specific pattern
./warroom-context error "your error message here"

# Check drift alerts
./warroom-context drift alerts
```

### High Drift Alerts
```bash
# Scan for current patterns
./warroom-context drift scan

# Review alerts
./warroom-context drift alerts

# Update context files to match current code
```

## Best Practices

### 1. Context File Organization
- Keep context files focused and specific
- Use clear, descriptive filenames
- Update context when code changes significantly

### 2. Pattern Management
- Add patterns for common error types
- Use appropriate priority levels (1-10)
- Test patterns after adding them

### 3. Session Management
- Always start sessions with descriptive tasks
- Let the system track your work naturally
- Review session summaries periodically

### 4. Maintenance Schedule
- Run `./warroom-context maintenance` weekly
- Check `./warroom-context status` daily
- Update context files when adding new features

### 5. Performance Monitoring
- Keep performance score above 70
- Maintain cache hit rate above 50%
- Keep context health above 80%