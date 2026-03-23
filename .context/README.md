# Friday Context Management System

**Semantic navigation and discovery for War Room development**

## Overview

The Friday Context Management System provides intelligent, searchable documentation and navigation for the War Room codebase. It implements semantic search, natural language queries, and automatic context discovery to eliminate guessing about code patterns, authentication flows, and system architecture.

## Quick Start

```bash
# Build the context index
friday-ctx index

# Search for information
friday-ctx find "JWT authentication"
friday-ctx find "database schema"

# Natural language queries
friday-ask "How does authentication work?"
friday-ask "Where are the API endpoints defined?"

# Explore context files
friday-ctx explore
friday-ctx related ".context/patterns.md"

# Check system status
friday-ctx status
```

## System Components

### 1. Context Files
Structured documentation in `.context/` directories throughout the codebase:

- **architecture.md** - System architecture and service organization
- **patterns.md** - Code patterns, auth flows, and standards  
- **apis.md** - Endpoint documentation and API patterns
- **frontend.md** - Next.js structure and component organization
- **development.md** - Development workflows and troubleshooting
- **troubleshooting.md** - Common issues and solutions

### 2. CLI Tools

#### `friday-ctx` - Core Context Management
```bash
friday-ctx find "query"           # Search context files
friday-ctx explore [path]         # Browse context hierarchy  
friday-ctx related "file.md"      # Find related files
friday-ctx status                 # Show index status
friday-ctx index                  # Build/rebuild index
```

#### `friday-ask` - Natural Language Interface  
```bash
friday-ask "How does auth work?"  # Ask questions naturally
friday-ask -i                    # Interactive mode
friday-ask "question" -v          # Verbose analysis
```

#### `friday-ctx-enhanced` - Semantic Search (requires dependencies)
```bash
friday-ctx-enhanced find "query"      # Semantic similarity search
friday-ctx-enhanced relationships     # Show file relationships
friday-ctx-enhanced index             # Build semantic index
```

### 3. Git Integration

Automatic context updates via git hooks:
- **post-commit** - Update index after commits
- **post-checkout** - Update index after branch switches  
- **post-merge** - Update index after merges

### 4. Validation & CI

```bash
# Validate context system
./scripts/validate-context.sh

# Setup semantic search (optional)
./scripts/setup-semantic-search.py
```

## Architecture

```
.context/
├── metadata.yaml           # System configuration
├── architecture.md         # System overview
├── patterns.md            # Code patterns & auth flows
├── apis.md               # API documentation  
├── frontend.md           # Next.js components & structure
├── development.md        # Development workflows
├── troubleshooting.md    # Common issues & solutions
├── index.db              # Search index (auto-generated)
└── ci-integration.md     # CI/CD setup guide

bin/
├── friday-ctx            # Core CLI (text search)
├── friday-ctx-enhanced   # Semantic search (optional)
└── friday-ask           # Natural language interface

scripts/
├── context-git-hooks.sh  # Setup git integration
├── validate-context.sh   # System validation
└── setup-semantic-search.py  # Enhanced search setup
```

## Search Capabilities

### Text Search (Default)
Fast text-based search across all context files:
```bash
friday-ctx find "JWT authentication"
friday-ctx find "Docker compose"
```

### Semantic Search (Enhanced)
Embedding-based similarity search for natural language queries:
```bash
friday-ctx-enhanced find "user login process"
friday-ctx-enhanced find "API error handling"
```

### Natural Language Queries
Ask questions in plain English:
```bash
friday-ask "How do I debug Docker issues?"
friday-ask "What is the database schema?"
friday-ask "Where are React components defined?"
```

## Discovery Features

### File Relationships
Find semantically related context files:
```bash
friday-ctx related ".context/patterns.md"
friday-ctx-enhanced relationships
```

### Cross-References
Automatic detection of related concepts and keywords across files.

### Contextual Guidance
Smart suggestions based on query type and context categories.

## Development Integration

### Auto-Loading
Context is automatically loaded and updated based on:
- Git commit activity
- File modifications
- Error patterns in logs
- Import statements in code

### Freshness Validation
- Detect stale context relative to code changes
- Alert when context needs updates
- Track context age vs. commit history

### Session Tracking
- Remember current development context
- Preserve context across editor sessions
- Track files recently viewed/modified

## Setup Instructions

### 1. Basic Setup (Text Search Only)
```bash
# Setup git hooks for auto-updating
./scripts/context-git-hooks.sh

# Build initial index
friday-ctx index

# Validate setup
./scripts/validate-context.sh
```

### 2. Enhanced Setup (Semantic Search)
```bash
# Install semantic search dependencies
./scripts/setup-semantic-search.py

# Build semantic index  
friday-ctx-enhanced index

# Test semantic search
friday-ctx-enhanced find "authentication flow"
```

### 3. CI/CD Integration
See `.context/ci-integration.md` for GitHub Actions, Docker, and package.json integration patterns.

## Usage Examples

### Finding Authentication Information
```bash
# Text search
friday-ctx find "JWT"

# Natural language
friday-ask "How does user authentication work?"

# Semantic search  
friday-ctx-enhanced find "user login process"
```

### Debugging Issues
```bash
# Find troubleshooting info
friday-ctx find "Docker issues"

# Ask for help
friday-ask "Why is my container failing to start?"

# Explore troubleshooting guide
friday-ctx explore .context/troubleshooting.md
```

### Understanding Architecture
```bash
# Browse architecture context
friday-ctx explore .context/architecture.md

# Ask architectural questions
friday-ask "What is the system architecture?"

# Find related architectural files
friday-ctx related ".context/architecture.md"
```

## Maintenance

### Updating Context
Context files should be updated when:
- System architecture changes
- New patterns are established  
- API endpoints are modified
- Development workflows change
- Common issues are discovered

### Index Management
```bash
# Rebuild index after major changes
friday-ctx index

# Check index status
friday-ctx status

# Validate context freshness
./scripts/validate-context.sh
```

## Troubleshooting

### Common Issues

**"friday-ctx not found"**
```bash
# Add to PATH
export PATH="$PWD/bin:$PATH"

# Or run setup script
./scripts/context-git-hooks.sh
```

**"No results found"**
```bash
# Rebuild index
friday-ctx index

# Check if files exist
friday-ctx explore
```

**Semantic search errors**
```bash
# Install dependencies
./scripts/setup-semantic-search.py

# Use text-only search
friday-ctx find "query" --text-only
```

## Contributing

When adding new context:

1. **Create context files** in appropriate `.context/` directories
2. **Add YAML frontmatter** with metadata:
   ```yaml
   ---
   description: "Brief description"
   module-name: "Component Name"
   ---
   ```
3. **Update index** after changes:
   ```bash
   friday-ctx index
   ```
4. **Validate** the system:
   ```bash
   ./scripts/validate-context.sh
   ```

## Future Enhancements

- **AI-powered context generation** from code analysis
- **Integration with IDE plugins** for in-editor context
- **Real-time context updates** via file watchers  
- **Multi-repository context** for microservices
- **Visual context maps** showing file relationships

---

**Built for War Room by the Friday Context Management System**  
*Eliminating guesswork in development workflows*