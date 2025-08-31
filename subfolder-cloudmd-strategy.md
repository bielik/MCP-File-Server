# Subfolder CloudMD Strategy & Implementation Guide

## Overview
This document outlines the strategy for creating granular, contextual documentation files throughout the project structure. Each significant subfolder will contain its own `cloudmd` file that provides deep context about its specific functionality, reducing cognitive load during AI-assisted development.

## Core Principles

### 1. Contextual Hierarchy
- **Root `cloudmd`:** High-level project context, architecture, and setup
- **Module `cloudmd` files:** Specific functionality, APIs, and implementation details
- **Feature `cloudmd` files:** Detailed function-by-function documentation

### 2. Cognitive Load Reduction
Each `cloudmd` file should:
- Eliminate the need to read multiple files to understand a module
- Provide instant context about purpose, dependencies, and usage patterns
- Include examples of typical use cases and edge cases
- Document design decisions and rationale

### 3. Maintenance Automation
- Update `cloudmd` files as part of the development workflow
- Include automated reminders in the main `cloudmd` to review subfolder files
- Version control integration to track context evolution

## Subfolder CloudMD Structure

### Template Format
Each subfolder `cloudmd` should follow this structure:

```markdown
# [Module Name] - Context & Documentation

## Purpose & Scope
- Primary responsibility of this module
- Key functionalities provided
- Integration points with other modules

## Architecture & Design
- Internal structure and organization
- Design patterns used
- Key algorithms or approaches

## File-by-File Breakdown
### filename.ts
**Purpose:** Brief description
**Key Functions:**
- `functionName()`: What it does, params, return value, edge cases
- `anotherFunction()`: Purpose and usage

**Dependencies:** List of imports and why
**Usage Examples:** Common patterns

## API Reference
- Public interfaces and types
- Method signatures with examples
- Error handling patterns

## Testing Strategy
- Test coverage approach
- Mock strategies
- Key test cases

## Common Issues & Solutions
- Frequent problems encountered
- Debugging approaches
- Performance considerations

## Development Notes
- Future improvements planned
- Technical debt items
- Optimization opportunities
```

## Planned Subfolder Structure

### `/src/server/cloudmd`
**Focus:** MCP server implementation details
- Connection handling logic
- Message routing and protocol compliance
- Server lifecycle management
- WebSocket handling specifics

### `/src/files/cloudmd`
**Focus:** File operation implementations
- File system abstraction details
- CRUD operation specifics
- Path handling and validation
- Stream processing for large files
- Error handling patterns

### `/src/security/cloudmd`
**Focus:** Security implementation details
- Authentication flow documentation
- Authorization logic and role handling
- Security middleware implementation
- Vulnerability mitigation strategies
- Audit logging specifics

### `/src/config/cloudmd`
**Focus:** Configuration management
- Environment variable handling
- Configuration validation
- Default value strategies
- Runtime configuration updates

### `/src/utils/cloudmd`
**Focus:** Utility function documentation
- Helper function purposes and usage
- Common patterns and reusable code
- Error handling utilities
- Logging and debugging tools

### `/tests/cloudmd`
**Focus:** Testing approach and organization
- Test structure and patterns
- Mock strategies and setup
- Coverage requirements
- Integration test approaches

## Implementation Timeline

### Phase 1: Foundation (Immediate)
- Create cloudmd template files for planned directories
- Establish documentation standards
- Set up automated reminders

### Phase 2: Development Integration (During Coding)
- Update cloudmd files as functions are implemented
- Document design decisions in real-time
- Maintain examples and use cases

### Phase 3: Continuous Maintenance (Ongoing)
- Regular review cycles
- Context validation and updates
- Performance optimization documentation

## Best Practices

### Writing Guidelines
1. **Be Specific:** Include exact function signatures, not just descriptions
2. **Include Examples:** Show actual code usage, not just explanations
3. **Document Edge Cases:** Especially important for file operations
4. **Explain 'Why' Not Just 'What':** Design decisions and rationale
5. **Keep Current:** Update immediately when code changes

### Structure Standards
1. **Consistent Format:** All cloudmd files follow the same template
2. **Cross-References:** Link to related modules and files
3. **Dependency Mapping:** Clear documentation of module relationships
4. **Error Scenarios:** Document failure modes and handling

### Maintenance Workflow
1. **Pre-Development:** Review existing cloudmd for context
2. **During Development:** Update cloudmd with new functions/decisions
3. **Post-Development:** Validate cloudmd accuracy and completeness
4. **Regular Reviews:** Monthly validation of all cloudmd files

## Automation & Tooling

### Automated Reminders
Add to main `cloudmd` file:
```markdown
## Maintenance Reminders
- [ ] Review /src/server/cloudmd - Last updated: [DATE]
- [ ] Review /src/files/cloudmd - Last updated: [DATE]
- [ ] Review /src/security/cloudmd - Last updated: [DATE]
```

### IDE Integration
- Add cloudmd files to workspace favorites
- Create snippets for common documentation patterns
- Set up lint rules to enforce documentation standards

### Git Integration
- Include cloudmd updates in commit templates
- Add pre-commit hooks to validate documentation currency
- Track cloudmd changes in changelog

## Context Building Strategy

### For New Modules
1. Create cloudmd stub before writing code
2. Document intended architecture and approach
3. Update with actual implementation details
4. Include lessons learned and optimizations

### For Existing Modules
1. Analyze current code structure
2. Document existing patterns and decisions
3. Identify gaps and improvement opportunities
4. Plan refactoring with context documentation

## Quality Metrics

### Documentation Completeness
- All public functions documented with examples
- All error conditions documented
- All dependencies explained
- All design decisions recorded

### Usability Validation
- Can a new developer understand the module from cloudmd alone?
- Are common use cases clearly documented?
- Are troubleshooting guides helpful?
- Is the context current and accurate?

## Example Implementation

### `/src/files/cloudmd` (Preview)
```markdown
# File Operations Module - Context & Documentation

## Purpose & Scope
Handles all file system operations for the MCP File Server, providing secure and validated access to the underlying file system while maintaining protocol compliance.

## Key Responsibilities
- File CRUD operations (Create, Read, Update, Delete)
- Directory listing and traversal
- Path validation and sanitization
- Stream handling for large files
- File metadata extraction

## Architecture & Design
Uses a layered approach:
1. **Validation Layer:** Path sanitization and security checks
2. **Operation Layer:** Core file system interactions
3. **Streaming Layer:** Efficient handling of large files
4. **Error Layer:** Consistent error handling and reporting

## File-by-File Breakdown
### fileOperations.ts
**Purpose:** Core file system operations implementation
**Key Functions:**
- `readFile(path: string, options?: ReadOptions): Promise<FileContent>`
  - Validates path, reads file with streaming support
  - Handles encoding detection and conversion
  - Throws `FileNotFoundError` or `PermissionDeniedError`
- `writeFile(path: string, content: Buffer | string): Promise<WriteResult>`
  - Validates write permissions and path safety
  - Creates directories if needed (with option)
  - Atomic write with temp file and rename

### pathValidator.ts
**Purpose:** Security-focused path validation and sanitization
**Key Functions:**
- `validatePath(path: string): ValidationResult`
  - Checks for directory traversal attacks
  - Validates against allowed directories
  - Normalizes path separators
- `sanitizePath(path: string): string`
  - Removes dangerous characters
  - Resolves relative path components
  - Ensures within allowed boundaries
```

This comprehensive strategy ensures that as the project grows, each module maintains rich contextual documentation that significantly reduces cognitive load and improves development efficiency.

---

**Implementation Status:** Template Created  
**Next Steps:** Create initial cloudmd stubs for planned directories  
**Review Date:** After first module implementation