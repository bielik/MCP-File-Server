# Context File Strategy - MCP KnowledgeExplorer

## Purpose and Philosophy

This document outlines the comprehensive strategy for creating and maintaining contextual documentation files throughout the MCP KnowledgeExplorer project. The goal is to create a **"Context-Rich Development Environment"** where every significant directory contains detailed documentation that dramatically reduces cognitive load during development and maintenance.

## Context File Hierarchy

### 1. Root Level Context
**File:** `CLAUDE.md` (Primary project context)
- **Scope:** Entire project overview
- **Content:** Architecture, tech stack, setup instructions, common tasks
- **Audience:** New developers, project understanding, high-level decisions
- **Maintenance:** Updated with major architectural changes

### 2. Module Level Context  
**Files:** `backend/app/CLAUDE.md`, `frontend/src/CLAUDE.md`
- **Scope:** Major application modules
- **Content:** Module architecture, patterns, file organization, development priorities
- **Audience:** Developers working within specific modules
- **Maintenance:** Updated when new major components are added

### 3. Service/Component Level Context
**Files:** Individual context files for complex subsystems
- **Scope:** Specific service areas or component groups
- **Content:** Detailed implementation notes, function documentation, usage patterns
- **Audience:** Developers implementing or debugging specific features
- **Maintenance:** Updated with implementation progress

## Recommended Context File Locations

### Backend Context Files
```
backend/
├── app/CLAUDE.md                    # ✅ Created - Main backend context
├── app/api/CLAUDE.md                # 📋 Recommended - API layer context
├── app/services/CLAUDE.md           # 📋 Recommended - Business logic context
├── app/models/CLAUDE.md             # 📋 Optional - Database schema context
└── app/schemas/CLAUDE.md            # 📋 Optional - API contract context
```

### Frontend Context Files
```
frontend/
├── src/CLAUDE.md                    # ✅ Created - Main frontend context
├── src/components/CLAUDE.md         # 📋 Recommended - Component library context
├── src/hooks/CLAUDE.md              # 📋 Optional - Custom hooks context
├── src/services/CLAUDE.md           # 📋 Optional - API client context
└── src/store/CLAUDE.md              # 📋 Optional - State management context
```

### Infrastructure Context Files
```
MCPFileServer/
├── CLAUDE.md                        # ✅ Created - Root project context
├── change.log                       # ✅ Created - Change tracking
├── plan.md                          # ✅ Created - Task management
├── .docker/CLAUDE.md                # 📋 Optional - Docker configuration context
└── docs/CLAUDE.md                   # 📋 Future - User documentation context
```

## Context File Template Structure

### Standard Template for Subfolder Context Files
```markdown
# [Module Name] Context - MCP KnowledgeExplorer

## Directory Overview
Brief description of what this directory contains and its role in the larger system.

## File Structure
Detailed breakdown of files and their purposes:
- **filename.ext** - Purpose and responsibility
- **subdirectory/** - What it contains

## Key Patterns and Conventions
Common patterns used throughout this module:
- Naming conventions
- Code organization patterns  
- Import/export strategies
- Error handling approaches

## Function/Component Documentation
For each major function or component:
- **Purpose:** What it does
- **Interface:** Parameters, return values, types
- **Usage:** Common use cases and examples
- **Dependencies:** What it relies on
- **Known Issues:** Current limitations or TODOs

## Development Guidelines
- Code quality standards for this module
- Testing approaches
- Common debugging techniques
- Performance considerations

## Integration Points
How this module connects to other parts of the system:
- API contracts
- State management
- Event handling
- Data flow

## Future Considerations
- Planned enhancements
- Refactoring opportunities
- Technical debt items

---
*Last updated: [Date] - [Brief summary of changes]*
```

## Content Strategy for Each Context File Type

### API Layer Context (`backend/app/api/CLAUDE.md`)
**Focus:** HTTP endpoints, WebSocket handlers, request/response patterns
**Key Sections:**
- Endpoint documentation with examples
- WebSocket message protocols
- Authentication and authorization patterns
- Error response formats
- Rate limiting and validation rules

### Services Context (`backend/app/services/CLAUDE.md`)
**Focus:** Business logic implementation, service patterns, integration points
**Key Sections:**
- Service architecture and dependency injection
- File system operation patterns
- Permission checking logic
- MCP protocol implementation details
- Error handling and logging strategies

### Component Library Context (`frontend/src/components/CLAUDE.md`)
**Focus:** React component patterns, shared utilities, design system
**Key Sections:**
- Component architecture and composition patterns
- Props interface standards
- Styling conventions and Tailwind usage
- Accessibility implementation patterns
- Testing approaches for components

## Implementation Priority

### High Priority (Implement During Active Development)
1. **`backend/app/api/CLAUDE.md`** - Critical for MCP protocol implementation
2. **`backend/app/services/CLAUDE.md`** - Essential for business logic development
3. **`frontend/src/components/CLAUDE.md`** - Important for UI development consistency

### Medium Priority (Implement As Modules Grow)
1. **`backend/app/models/CLAUDE.md`** - When database schema becomes complex
2. **`frontend/src/hooks/CLAUDE.md`** - When custom hooks library develops
3. **`frontend/src/store/CLAUDE.md`** - When state management becomes complex

### Low Priority (Future Enhancement)
1. **`backend/app/schemas/CLAUDE.md`** - When API contracts stabilize
2. **`frontend/src/services/CLAUDE.md`** - When API client patterns emerge
3. **`.docker/CLAUDE.md`** - When deployment becomes more complex

## Maintenance Strategy

### Update Triggers
Context files should be updated when:
- **New major components** are added to the directory
- **Architectural patterns** change significantly
- **API contracts** are modified
- **Development conventions** are established or changed
- **Performance optimizations** are implemented
- **Bug fixes** reveal important implementation details

### Review Schedule
- **Monthly Review:** Check if high-priority context files need updates
- **Sprint Review:** Update context files for areas with active development
- **Release Review:** Comprehensive review of all context files before major releases

### Quality Standards
Each context file should:
- **Be accurate** - Reflect current implementation state
- **Be complete** - Cover all major functionality in the directory
- **Be actionable** - Provide clear guidance for developers
- **Be concise** - Focus on essential information without overwhelming detail
- **Be current** - Include last-updated timestamp and change summary

## Benefits of This Strategy

### For Development
- **Reduced Onboarding Time:** New developers can understand any part of the system quickly
- **Consistent Patterns:** Clear documentation of established conventions
- **Debugging Efficiency:** Context files serve as debugging guides
- **Code Review Quality:** Reviewers have better context for changes

### For Maintenance
- **Technical Debt Tracking:** Context files highlight areas needing attention
- **Refactoring Safety:** Clear documentation of current behavior before changes
- **Knowledge Preservation:** Important implementation decisions are documented
- **Regression Prevention:** Understanding of why things work prevents accidental breakage

### For Project Management
- **Scope Understanding:** Clear breakdown of functionality in each area
- **Progress Tracking:** Context files reflect implementation progress
- **Risk Assessment:** Documented complexity helps identify risky changes
- **Resource Planning:** Understanding of component complexity aids in task estimation

## Integration with Existing Tools

### Git Integration
- Context files should be committed with related code changes
- Use conventional commit messages when updating context files
- Consider context file updates as part of feature completion

### IDE Integration
- Context files provide excellent reference material during development
- Can be opened alongside code for immediate context
- Markdown preview provides structured view of information

### Documentation Pipeline
- Context files can be aggregated into larger documentation
- Automated tools can extract API documentation from context files
- Context files serve as source material for user documentation

---

## Conclusion

This context file strategy transforms the codebase into a **"self-documenting system"** where every directory contains the information needed to understand and work with that area of the code. By implementing this strategy progressively, starting with high-priority areas, the project will become significantly more maintainable and approachable for all developers.

The key to success is treating context files as **living documentation** that evolves with the code, rather than static documentation that becomes outdated. Regular updates and reviews ensure the context files remain a valuable development resource throughout the project's lifecycle.

---

*This strategy document should be reviewed and updated as the project grows and context file patterns emerge from actual usage.*