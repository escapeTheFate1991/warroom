# War Room Context System Test Cases

## Phase 1 Test Cases - CCS Foundation + Context7 Setup

### Test Case 1: Context Structure Validation

**Objective:** Verify complete CCS directory structure and metadata format

**Test Commands:**
```bash
friday-ctx validate
```

**Expected Output:**
- ✓ All required directories exist (`.context/`, `backend/.context/`, `frontend/.context/`)
- ✓ All required index.md files exist with YAML front matter
- ✓ All architecture diagrams exist (auth-flow.mmd, architecture.mmd, docker-containers.mmd)
- ✓ No validation errors

**Pass Criteria:**
- All validations pass without errors
- YAML metadata structure is valid in all index.md files

### Test Case 2: Context Discovery and Search

**Objective:** Verify local context search functionality works

**Test Commands:**
```bash
# Search for authentication patterns
friday-ctx find "JWT"

# Search for Docker patterns  
friday-ctx find "docker"

# Search for CSRF protection
friday-ctx find "CSRF"
```

**Expected Output:**
- Search finds relevant content in context files
- Results show file locations and matched content
- Context is displayed with proper formatting

**Pass Criteria:**
- Each search returns relevant matches from appropriate context files
- Output is readable and helpful for development

### Test Case 3: Pattern-Specific Context Access

**Objective:** Verify quick access to specific development patterns

**Test Commands:**
```bash
friday-ctx auth      # Show JWT authentication patterns
friday-ctx csrf      # Show CSRF protection patterns  
friday-ctx docker    # Show Docker rebuild patterns
friday-ctx api       # Show API development patterns
```

**Expected Output:**
- Each command shows relevant patterns and implementation details
- Output includes code examples and usage instructions
- Information is current and accurate for War Room codebase

**Pass Criteria:**
- Commands return specific, actionable information
- Patterns match actual implementation in codebase
- Output helps solve real development questions

### Test Case 4: Context Exploration

**Objective:** Verify context hierarchy exploration works

**Test Commands:**
```bash
friday-ctx explore .          # Root level context
friday-ctx explore backend    # Backend-specific context
friday-ctx explore frontend   # Frontend-specific context
```

**Expected Output:**
- Hierarchical view of context structure
- Module names and descriptions extracted from YAML metadata
- Clear organization by feature area

**Pass Criteria:**
- All context directories are discovered and displayed
- Module information is extracted correctly from YAML
- Navigation is intuitive and helpful

### Test Case 5: Context7 Library Documentation Integration

**Objective:** Verify library documentation retrieval (when API is available)

**Test Commands:**
```bash
friday-ctx library fastapi "JWT middleware"
friday-ctx library nextjs "app router"
friday-ctx library docker "compose environment"
```

**Expected Output:**
- Integration with Context7 API when available
- Fallback to local context when API is unavailable
- Relevant documentation for current library versions

**Pass Criteria:**
- Commands attempt Context7 API integration
- Graceful fallback to local patterns when API unavailable
- Useful output regardless of Context7 availability

### Test Case 6: Error Message → Context Loading

**Objective:** Verify context system helps with real development errors

**Scenario 1: JWT Validation Error**
```
Error: 401 Unauthorized - Invalid token
```

**Test:** `friday-ctx find "JWT validation"`

**Expected:** 
- Shows JWT authentication flow patterns
- Displays common JWT issues and solutions
- Points to relevant implementation files

**Scenario 2: CORS/CSRF Error**
```
Error: 403 Forbidden - CSRF validation failed
```

**Test:** `friday-ctx csrf`

**Expected:**
- Shows CSRF protection configuration
- Displays allowed origins list
- Explains Origin header requirements

**Scenario 3: Docker Build Failure**
```
Error: Cannot find module 'package-name'
```

**Test:** `friday-ctx docker`

**Expected:**
- Shows Docker rebuild commands
- Explains when to use --no-cache
- Lists common container issues and solutions

**Pass Criteria:**
- Context system provides relevant, actionable information for common errors
- Developers can resolve issues without guessing at patterns
- Information leads to faster problem resolution

### Test Case 7: YAML Metadata Structure Validation

**Objective:** Verify YAML metadata follows CCS specification

**Test Files:**
- `/home/eddy/Development/warroom/.context/index.md`
- `/home/eddy/Development/warroom/backend/.context/index.md`
- `/home/eddy/Development/warroom/frontend/.context/index.md`

**Validation Checks:**
```yaml
# Required YAML structure
---
module-name: "string"
description: "string"
architecture:
  style: "string"
  components:
    - name: "string"
      description: "string"
patterns:
  - name: "string"
    usage: "string"
    files: ["array", "of", "strings"]
---
```

**Pass Criteria:**
- All context files have valid YAML front matter
- Required fields are present and properly formatted
- Structure follows CCS specification

### Test Case 8: Context Initialization

**Objective:** Verify new context directories can be created

**Test Commands:**
```bash
# Initialize context in a test directory
mkdir -p /tmp/test-module
friday-ctx init /tmp/test-module

# Verify structure was created
ls -la /tmp/test-module/.context/
```

**Expected Output:**
- Creates `.context/` directory with template `index.md`
- Template includes valid YAML front matter structure
- Instructions for customizing the context

**Pass Criteria:**
- Context directory is created successfully
- Template follows CCS specification
- Ready for customization with module-specific information

## Integration Test Scenarios

### Scenario 1: New Developer Onboarding

**Context:** New developer joins the team, needs to understand War Room architecture

**Test Workflow:**
1. `friday-ctx explore .` - Get overview of project structure
2. `friday-ctx auth` - Understand authentication patterns  
3. `friday-ctx docker` - Learn development setup
4. `friday-ctx find "API patterns"` - Learn API conventions

**Success Criteria:**
- Developer can understand War Room architecture without code diving
- Key patterns are clearly explained and actionable
- Development setup is straightforward to follow

### Scenario 2: Debugging Authentication Issues

**Context:** Frontend can't authenticate with backend API

**Test Workflow:**
1. Encounter error: "401 Unauthorized - Invalid token"
2. `friday-ctx auth` - Review JWT implementation
3. `friday-ctx find "JWT validation"` - Get specific troubleshooting info
4. Compare implementation with documented patterns

**Success Criteria:**
- Context provides specific debugging steps
- Common JWT issues are documented with solutions
- Developer can identify and fix authentication problems quickly

### Scenario 3: Adding New API Endpoints

**Context:** Need to add new CRM features to API

**Test Workflow:**
1. `friday-ctx api` - Review API development patterns
2. `friday-ctx explore backend` - Understand backend structure
3. `friday-ctx find "multi-tenant"` - Review data isolation patterns
4. Implement following documented patterns

**Success Criteria:**
- API patterns guide implementation decisions
- Multi-tenant isolation is correctly implemented
- New endpoints follow established conventions

### Scenario 4: Docker Development Issues

**Context:** Container won't start after dependency changes

**Test Workflow:**
1. Encounter build error: "Cannot find module 'new-package'"
2. `friday-ctx docker` - Review rebuild patterns
3. Try suggested `--no-cache` rebuild command
4. Verify issue is resolved

**Success Criteria:**
- Context provides specific Docker troubleshooting steps
- Rebuild commands resolve common container issues
- Development workflow continues smoothly

## Performance Test Cases

### Test Case P1: Context Search Speed

**Objective:** Verify context search performs within acceptable limits

**Test:** `time friday-ctx find "authentication"`

**Success Criteria:**
- Search completes in < 2 seconds
- Results are comprehensive and relevant
- Performance scales with codebase size

### Test Case P2: Context Loading Time

**Objective:** Verify context files load quickly for development use

**Test:** `time friday-ctx explore .`

**Success Criteria:**
- Complete exploration in < 1 second
- All context directories are processed
- Performance is suitable for interactive use

## Regression Test Cases

### Test Case R1: Context Accuracy After Code Changes

**Objective:** Verify context remains accurate as codebase evolves

**Test Steps:**
1. Make changes to authentication middleware
2. Run `friday-ctx validate` to check for drift
3. Update context if patterns have changed
4. Verify `friday-ctx auth` shows current implementation

**Success Criteria:**
- Context validation detects when patterns drift
- Update process is clear and straightforward
- Context remains helpful and accurate over time

### Test Case R2: Context Structure Backwards Compatibility

**Objective:** Ensure context structure changes don't break existing workflows

**Test Steps:**
1. Validate current context structure
2. Make structure improvements
3. Verify existing commands still work
4. Check that search functionality remains intact

**Success Criteria:**
- Existing context files continue to work
- Search functionality is preserved
- Migration path is clear for any breaking changes

## Acceptance Criteria Summary

Phase 1 is considered complete when:

1. ✅ **Complete CCS Structure**: All required context directories and files exist with valid YAML metadata
2. ✅ **Context Discovery Works**: Search and exploration commands return relevant, helpful information
3. ✅ **Pattern Access**: Quick access to JWT, CSRF, Docker, and API patterns
4. ✅ **Error Resolution**: Context system helps resolve common development errors
5. ✅ **Context7 Integration**: Library documentation retrieval is configured (with fallbacks)
6. ✅ **Validation System**: Context structure can be validated and maintained
7. ✅ **Performance**: All operations complete within interactive timeframes
8. ✅ **Documentation**: All patterns are accurately documented and current

## Success Metrics

- **Zero guessing at War Room patterns**: Developers can find implementation patterns through context system
- **Faster error resolution**: Common issues have documented solutions in context
- **Consistent development practices**: New features follow documented patterns
- **Reduced onboarding time**: New developers understand architecture through context exploration

## Next Phase Preparation

Phase 1 success enables Phase 2 (Semantic Navigation + Discovery) by providing:
- Solid foundation of structured context
- Proven CLI tools for context access
- Validated YAML metadata structure
- Integration patterns for external documentation sources

The foundation built in Phase 1 will support semantic indexing, relationship mapping, and AI-powered context generation in subsequent phases.