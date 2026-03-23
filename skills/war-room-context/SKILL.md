# War Room Context Management Skill

Context-aware skill loading and coordination for the War Room project. Integrates the context management system with OpenClaw's skill infrastructure and multi-agent communication.

## Purpose

This skill provides intelligent context loading for War Room development:
1. **Auto-Context Loading** - Loads relevant context based on errors, file paths, task descriptions
2. **Multi-Agent Context Sharing** - Shares context between agents via Network-AI blackboard
3. **Session-Aware Operations** - Maintains development session context across agent interactions
4. **Performance Monitoring** - Tracks context usage and quality metrics

## Integration Points

- **War Room Vector Memory** - Semantic search and storage
- **Session Management** - Development context tracking  
- **Semantic Indexing** - Live codebase understanding
- **AI Generation** - Automated pattern recognition
- **Network-AI** - Inter-agent communication

## Usage Patterns

### Error Context Loading
```bash
# Load context for debugging an error
python .context/tools/context_loader.py --error "JWT authentication failed"
```

### Code Context Search
```bash
# Search codebase semantically
python .context/tools/semantic_index.py --search "user authentication flow"
```

### Session Context Management
```bash
# Start development session
python .context/tools/session_manager.py --start "Fix authentication bug"

# Track file activity
python .context/tools/session_manager.py --file-activity "backend/auth.py:modified"
```

### AI Pattern Recognition
```bash
# Generate API documentation
python .context/tools/ai_generator.py --api-docs

# Analyze codebase patterns
python .context/tools/ai_generator.py --analyze
```

## Environment Setup

The skill expects:
- War Room project at `/home/eddy/Development/warroom/`
- Qdrant running on `localhost:6334`
- FastEmbed service at `http://10.0.0.11:11435`
- Network-AI for agent communication

## Implementation

When triggered, this skill:
1. Analyzes the user's request/error for context clues
2. Loads relevant context from multiple sources
3. Provides structured context response
4. Updates session tracking if applicable
5. Shares context with other agents if needed