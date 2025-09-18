# MCP KnowledgeExplorer - Project Context for Claude

## Project Overview
**Name:** MCP KnowledgeExplorer
**Type:** Full-stack web application with MCP (Model Context Protocol) server
**Purpose:** A sophisticated, local-first Model Context Protocol server that enables AI agents to assist with research, providing a web-based UI for configuration, real-time monitoring, and granular permission management over the local file system.

## 🎉 MAJOR MILESTONE: Phase 3B Complete - Advanced UI & Full Workspace Experience
**Status:** ✅ **PHASE 3B COMPLETE - Advanced UI & Full Workspace Experience**

We have successfully completed Phase 3B of the dynamic workspace system! The MCP KnowledgeExplorer now features a complete, production-ready workspace management system with advanced UI components, real-time updates, comprehensive permission management, and full user experience. All Phase 3B functionality has been implemented, thoroughly tested, and is production-ready.

**Phase 3B Achievements:**
- ✅ **🆕 Complete Workspace Management UI**: Create, activate, delete workspaces with real-time updates
- ✅ **🆕 Two-Panel Permission Editor**: Visual permission management with file tree navigation
- ✅ **🆕 Permission Inspector System**: Detailed rule explanations with hover tooltips and click modals
- ✅ **🆕 Real-time WebSocket Integration**: Live workspace switching and permission updates
- ✅ **🆕 Comprehensive Test Infrastructure**: Backend and frontend test suites (72.3 KB test code)
- ✅ **🆕 Performance Validation**: Sub-100ms batch API responses, optimized caching
- ✅ **🆕 Production-Ready UI**: Complete user experience with visual indicators
- ✅ **🆕 Browser MCP Test Integration**: Full automated testing infrastructure
- ✅ Complete Database Schema: Full `Workspace` and `Permission` SQLAlchemy models (Phase 3A maintained)
- ✅ Workspace Management APIs: Full CRUD operations (Phase 3A maintained)
- ✅ Batch Permission API: High-performance endpoint (Phase 3A maintained)
- ✅ Database Permission Service: Trie caching with workspace context (Phase 3A maintained)
- ✅ Audit Logging System: Comprehensive event tracking (Phase 3A maintained)
- ✅ Complete MCP JSON-RPC 2.0 protocol implementation (Phase 2 maintained)
- ✅ File system tools: `read_file`, `list_files`, `write_file` (Phase 2 maintained)
- ✅ Config-File Permission System (Phase 2 maintained for backward compatibility)
- ✅ Trie-Based Caching: High-performance permission resolution (enhanced for database)
- ✅ Formal Precedence Logic: Comprehensive permission resolution (enhanced)
- ✅ Real-time activity logging via WebSocket to UI
- ✅ Advanced file explorer with tree navigation and visual permission indicators

## Architecture: The "Unified Hub" Model
The system follows a **"Unified Hub"** architecture pattern - a single, persistent backend server acts as the central point of control for all clients (both browser UI and AI agents). Think of it as a permanent restaurant where all customers come through the same front door and are handled by the same staff.

## Technology Stack

### Backend (Python/FastAPI) - ✅ PHASE 3A COMPLETE
- **Framework:** FastAPI with async/await support
- **MCP Protocol:** Complete JSON-RPC 2.0 implementation (MCP 2024-11-05)
- **Database:** SQLite for persistent state storage with full workspace/permission schema
- **Real-time:** WebSockets for live communication
- **Security:** Database-driven permission system with workspace contexts and Trie caching
- **New Features:** Workspace CRUD, Batch permission resolution, Audit logging, Migration scripts
- **Dependencies:**
  - fastapi, uvicorn[standard], sqlalchemy, websockets, python-dotenv, watchdog
- **Port:** 8000 (configurable via BACKEND_PORT env var)
- **Entry Point:** `backend/app/main.py`

### Frontend (React/TypeScript) - ✅ PHASE 2 COMPLETE
- **Framework:** React 18 with TypeScript
- **Build Tool:** Vite for fast development
- **State Management:** React useState/useEffect with context patterns
- **Styling:** Tailwind CSS for utility-first styling
- **Components:** FileExplorer, PermissionIndicator, PermissionEditor, enhanced App with tabs
- **Port:** 5173 (configurable via FRONTEND_PORT env var)
- **Entry Point:** `frontend/src/main.tsx`

### Infrastructure - ✅ PRODUCTION READY
- **Containerization:** Docker & Docker Compose
- **Development:** Hot-reload enabled in both frontend and backend
- **Volumes:**
  - Database: `./data` mounted to `/data`
  - Configuration: `./config` mounted to `/config`
  - Shared Files: `C:/Users/MartinBielik/MCP Test/` mounted to `/source`

## Working Directory Structure

**Actual Shared Filesystem:** `C:/Users/MartinBielik/MCP Test/`
```
C:/Users/MartinBielik/MCP Test/
├── materials/                    # Read access - course materials and documentation
│   ├── 01_Introduction to Software Engineering/  # BLOCKED by deny rule
│   └── [other course materials]/
├── projects/                     # Read-Write access - development projects and code
│   ├── [various project folders]/
│   └── README.md
└── private stuff/                # No access - not covered by any allow rules
    └── [private files]/
```

**Permission Configuration:** Database-driven workspaces (Phase 3)
- materials/ - Read-only access (allow rule)
- projects/ - Read-write access (allow rule)
- materials/01_Introduction to Software Engineering/ - Blocked (deny rule overrides)
- private stuff/ - No access (default deny)

**Note:** The legacy `config/permissions.json` file has been removed to prevent confusion between config-file and database permission systems.

## Key Components and Endpoints

### Backend API Structure - ✅ FULLY OPERATIONAL
- **HTTP Endpoints:**
  - `GET /` - Health check endpoint
  - `/api/*` - REST API routes (via `api_router`)
  - `GET /api/browse` - Secure file system browsing with pagination
  - `GET /api/current-permissions` - Permission status for UI visualization
  - `GET /api/config/permissions` - Get current permission configuration
  - `PUT /api/config/permissions` - Update permission configuration
  - `POST /mcp` - HTTP MCP endpoint for JSON-RPC requests

- **WebSocket Endpoints:**
  - `/ws/ui` - UI client connections for real-time updates
  - `/ws/mcp` - MCP client connections for AI agent communication

### MCP Protocol Implementation - ✅ COMPLETE
**Supported Methods:**
- `initialize` - Server capability negotiation with MCP 2024-11-05
- `initialized` - Client initialization confirmation
- `tools/list` - Dynamic tool discovery returning available file system tools
- `tools/call` - Secure tool execution with parameter validation

**Available Tools:**
- `read_file(path: string)` - Read complete file contents with permission checking
- `list_files(path: string)` - List directory contents with file metadata
- `write_file(path: string, content: string)` - Write content to file with directory creation

### Permission System - ✅ PHASE 2 COMPLETE

#### Config-File Based Permissions
The system uses formal JSON configuration files with advanced features:

**Current Working Configuration:**
```json
{
  "rules": [
    {
      "id": "context-materials-read",
      "path": "materials",
      "permission_type": "read",
      "rule_type": "allow",
      "description": "Allow read access to materials directory"
    },
    {
      "id": "working-projects-write",
      "path": "projects",
      "permission_type": "write",
      "rule_type": "allow",
      "description": "Allow write access to projects directory"
    },
    {
      "id": "deny-intro-software-eng",
      "path": "materials/01_Introduction to Software Engineering",
      "permission_type": "read",
      "rule_type": "deny",
      "description": "Block access to Introduction to Software Engineering module"
    }
  ],
  "precedence_rules": {
    "rules": [
      "1. Specificity: Child paths override parent paths",
      "2. Deny wins: For equal specificity, deny overrides allow",
      "3. Write implies read: Write permission grants read access",
      "4. Default deny: No matching rules = access denied"
    ]
  }
}
```

**Key Features:**
- **Formal Precedence Logic**: Child paths override parent paths, deny wins ties
- **Trie-Based Caching**: High-performance in-memory permission resolution
- **File Watcher**: Automatic reload when config files change
- **Atomic Updates**: Safe multi-user editing with optimistic locking
- **Feature Flags**: Safe deployment with `ENABLE_CONFIG_FILE_PERMISSIONS=true`

## Development Workflow

### ⚠️ **IMPORTANT: Docker is the Primary Development Method**

**This application is designed to run exclusively with Docker Compose. Do NOT run backend/frontend individually outside Docker as this will cause networking and configuration issues.**

### Starting the Application (Primary Method)
```bash
# 🏁 PRIMARY METHOD: Single command to start everything
docker-compose up

# Or run in detached mode for background operation
docker-compose up -d

# Stop all services
docker-compose down
```

### Alternative Development (For Debugging Only)
Individual service startup outside Docker is generally NOT recommended but may be required for:
- **Debugging WebSocket connectivity issues**
- **Backend logging and inspection**
- **Development when Docker Desktop is unavailable**

⚠️ **Known Issues with Individual Services:**
- WebSocket connectivity issues (requires code inspection to resolve)
- CORS configuration problems
- Database mounting/access issues
- Environment variable conflicts

**For Emergency Debugging:**
```bash
# Backend only (for inspection)
cd backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Frontend only (for testing)
cd frontend && npm run dev
```

### Accessing Services
- **Frontend UI:** http://localhost:5173
- **Backend API:** http://localhost:8000
- **API Documentation:** http://localhost:8000/docs (FastAPI auto-generated)
- **MCP WebSocket:** ws://localhost:8000/ws/mcp
- **MCP HTTP:** http://localhost:8000/mcp

### Development Features
- **Hot Reload:** Both frontend and backend support hot-reload in development
- **Volume Mounts:** Code changes are immediately reflected without rebuilding containers
- **CORS Configuration:** Pre-configured for local development

## Ticket Management System

### Overview
The project uses a structured ticket system for tracking bugs, features, and issues in the `tickets/` folder. Each ticket includes comprehensive problem analysis, implementation plans, and testing strategies.

### Naming Convention
**Format:** `{NUMBER}-{TYPE}-{short-title}.md`

**Examples:**
- `001-BUG-permission-indicator-mapping.md`
- `002-BUG-file-explorer-wrong-permissions.md`
- `003-FEATURE-file-browser-navigation.md`

### Ticket Types
- **BUG**: Issues with existing functionality
- **FEATURE**: New functionality requests
- **ISSUE**: General problems or improvements
- **ENHANCEMENT**: Improvements to existing features

### Ticket Structure
Each ticket must include these sections:

#### 1. **Header & Metadata**
```markdown
# {NUMBER}-{TYPE}: {Descriptive Title}

## Status: Open/In Progress/Closed
**Created:** YYYY-MM-DD
**Priority:** High/Medium/Low
**Component:** Frontend/Backend/Full-stack
```

#### 2. **Problem Statement**
- Clear description of the issue or requested feature
- Current vs expected behavior
- Root cause analysis when applicable
- Screenshots or code references

#### 3. **Implementation Plan**
- Step-by-step technical approach
- Files to be modified
- Code examples or pseudocode
- Architecture considerations

#### 4. **Test Plan**
**Must include both manual and automated testing approaches:**

##### Manual Testing
- Step-by-step test procedures
- Expected outcomes for each step
- Browser MCP integration for UI testing
- Screenshot capture points

##### Automated Testing
- Test scripts using Browser MCP tools
- Validation functions
- Assertion criteria

##### Browser MCP Testing Template
```javascript
async function validateFeature() {
  // Navigate to app
  await browser.navigate('http://localhost:5173')
  await browser.wait(2)

  // Take initial screenshot
  await browser.screenshot()

  // Perform test actions
  await browser.click('element description', 'selector')

  // Verify results
  const snapshot = await browser.snapshot()
  const isValid = snapshot.includes('expected-content')

  console.log('Test Result:', isValid ? 'PASS' : 'FAIL')
  return isValid
}
```

#### 5. **Success Criteria**
- Checkboxes with specific, measurable outcomes
- Performance requirements
- User experience validation

#### 6. **References**
- Links to relevant code files
- Related tickets or documentation
- External resources

### Testing Integration
All tickets must include Browser MCP integration for frontend testing:

**Required Browser MCP Tools:**
- `mcp__browser__browser_navigate` - Navigate to application
- `mcp__browser__browser_screenshot` - Capture visual state
- `mcp__browser__browser_snapshot` - Get DOM structure
- `mcp__browser__browser_click` - Interact with elements
- `mcp__browser__browser_wait` - Allow for loading/animations

### Workflow
1. **Create Ticket**: Use next available number and appropriate type
2. **Analysis**: Include thorough problem analysis and root cause
3. **Planning**: Detail implementation approach with specific files
4. **Testing**: Define both manual procedures and automated validation
5. **Implementation**: Follow the planned approach
6. **Validation**: Execute test plan using Browser MCP
7. **Documentation**: Update relevant documentation
8. **Closure**: Mark ticket as closed with test results

### Current Tickets
- `001-BUG-permission-indicator-mapping.md` - Permission indicator display issues
- `001-BUG-test-report.md` - Test report for permission indicators
- `002-BUG-file-explorer-wrong-permissions.md` - File explorer permission problems
- `003-FEATURE-file-browser-navigation.md` - Dynamic file browsing functionality

### Best Practices
- **Specific Titles**: Use descriptive, searchable titles
- **Comprehensive Testing**: Always include Browser MCP automation
- **Visual Validation**: Capture screenshots for UI changes
- **Performance Metrics**: Include timing and resource requirements
- **Cross-browser Testing**: Validate on multiple browsers when applicable

## Core Functionality (Current State)

### ✅ System Architecture Complete: Simplified Single-Mount Design
1. **Backend Hub Server:** Fully functional FastAPI server with WebSocket support
2. **MCP Protocol Handler:** Complete JSON-RPC 2.0 implementation with MCP 2024-11-05 spec
3. **File System Tools:** Production-ready tools with integrated security
4. **🆕 Database Permission Management:** Full workspace-driven permission system
5. **🆕 Trie-Based Caching:** High-performance permission resolution with workspace context
6. **🆕 Real-time Updates:** WebSocket integration for live workspace switching
7. **🆕 Feature Flag System:** Production-ready database permissions (Phase 3)
8. **🆕 Workspace Management UI:** Complete workspace CRUD with visual indicators
9. **🆕 Two-Panel Permission Editor:** Visual permission management with batch API
10. **🆕 Permission Inspector:** Detailed rule explanations with matched rule info
11. **Real-time Activity Logging:** WebSocket broadcasting of MCP operations to UI
12. **Comprehensive Error Handling:** JSON-RPC compliant error responses
13. **Dual WebSocket Management:** Separate handlers for UI and MCP clients
14. **Database Integration:** SQLite with full workspace/permission schema
15. **Docker Environment:** Simplified single-mount containerization
16. **Security Layer:** Path validation and directory traversal prevention
17. **Streamlined UI:** Clean 3-tab interface (Workspaces, Permissions, Server Status)
18. **Visual Permission System:** Color-coded indicators with tooltip explanations
19. **Secure Browse API:** `/api/browse` with pagination and security hardening
20. **Batch Permission API:** High-performance endpoint for UI integration
21. **Legacy System Removed:** No more dual mount confusion or config file conflicts

### ✅ Complete: Phase 3A - Database-Driven Permissions
1. ✅ **Database Schema:** Complete migration to SQLite with full workspace and permission models
2. ✅ **Workspace Management:** Full workspace CRUD with activation and context switching
3. ✅ **Audit Logging:** Comprehensive tracking of all permission changes and access attempts
4. ✅ **Migration Tools:** Complete, idempotent config-to-database migration script
5. ✅ **Batch Permission API:** High-performance endpoint for efficient UI integration

### ✅ Complete: Phase 3B - Advanced Workspace UI (FINISHED)
1. ✅ **Workspace UI Components:** Create, delete, and activate workspaces from the UI
2. ✅ **Two-Panel Permission Editor:** Full visual workspace permission management
3. ✅ **"Inspect Permission" Feature:** Detailed permission explanations with matched rule info
4. ✅ **Real-time Workspace Switching:** Dynamic UI updates when workspace context changes
5. ✅ **Legacy System Cleanup:** Removed File Explorer and Settings tabs to eliminate confusion
6. ✅ **Single Mount Architecture:** Simplified to `/source` mount only (removed `/shared-fs`)
7. ✅ **Config File Cleanup:** Deleted `permissions.json` to prevent dual system conflicts

### 📋 Future Enhancements
1. **Search Features:** Keyword and semantic search capabilities
2. **Multi-client Management:** Enhanced support for multiple AI clients
3. **Advanced Security:** Rate limiting, audit trails, compliance reporting
4. **UI/UX Polish:** Shadcn/ui integration, responsive design, accessibility

## Security Model - ✅ PHASE 2 COMPLETE

### Database-Driven Permissions
- **Principle:** Permission rules stored in SQLite database with workspace contexts
- **Implementation:** `database_permission_service.py` with Trie caching
- **Validation:** Every file operation validated against active workspace rules
- **Legacy Support:** Config-file system maintained for backward compatibility (disabled by default)

**Security Features:**
- **Docker Bind Mounts:** Controlled interface to host file system
- **Path Validation:** Prevents directory traversal attacks
- **Mount Point Isolation:** All operations restricted to `/source`
- **Formal Precedence Logic:**
  - **Specificity:** Child paths override parent paths
  - **Tie-Breaker:** Deny wins over allow for equal specificity
  - **Implied Permissions:** Write permission implicitly grants read
  - **Default Deny:** If no rules match, access is denied
- **Atomic Updates:** Safe concurrent editing with optimistic locking
- **File Watcher:** Automatic permission reload on config changes

## Environment Variables
Key configuration options in `.env`:
- `BACKEND_PORT`: Backend server port (default: 8000)
- `FRONTEND_PORT`: Frontend dev server port (default: 5173)
- `DATABASE_PATH`: SQLite database location (default: ./data)
- `SHARED_FS_PATH`: Shared file system mount (default: C:/Users/MartinBielik/MCP Test)
- `ENABLE_CONFIG_FILE_PERMISSIONS`: Enable Phase 2 features (default: true, maintained for compatibility)
- `ENABLE_DATABASE_PERMISSIONS`: Enable Phase 3A features (default: true, production-ready)
- `PERMISSION_CACHE_TTL`: Cache TTL in seconds (default: 300)
- `PERMISSION_CACHE_MAX_SIZE`: Max cache entries (default: 10000)

## Common Tasks and Commands

### Setting Up MCP Connection with Claude Code ✅
```bash
# Add the MCP server to Claude Code (HTTP transport - recommended)
claude mcp add --transport http wisdom http://localhost:8000/mcp

# Verify connection
claude mcp list

# Remove if needed
claude mcp remove wisdom -s local
```

### Testing MCP Connection ✅
```bash
# Test HTTP MCP connection (recommended)
curl -X POST http://localhost:8000/mcp -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "initialize", "params": {"version": "2024-11-05"}, "id": 1}'

# List tools
curl -X POST http://localhost:8000/mcp -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "tools/list", "id": 2}'

# Test file operation with actual directories (materials, projects)
curl -X POST http://localhost:8000/mcp -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "read_file", "arguments": {"path": "materials/example.txt"}}, "id": 3}'

# Test projects directory (should have write access)
curl -X POST http://localhost:8000/mcp -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "list_files", "arguments": {"path": "projects"}}, "id": 4}'

# Test blocked directory (should be denied)
curl -X POST http://localhost:8000/mcp -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "read_file", "arguments": {"path": "materials/01_Introduction to Software Engineering/README.md"}}, "id": 5}'
```

**Note:** The server is registered as "wisdom" in Claude Code and provides the following MCP tools:
- `mcp__wisdom__read_file` - Read file contents with permission checking
- `mcp__wisdom__list_files` - List directory contents
- `mcp__wisdom__write_file` - Write file contents (subject to permissions)

### Workspace & Permission Management (Phase 3A)
```bash
# Workspace Management
curl http://localhost:8000/api/workspaces                    # List all workspaces
curl -X POST http://localhost:8000/api/workspaces \          # Create workspace
  -H "Content-Type: application/json" \
  -d '{"name": "My Workspace", "description": "Test workspace", "is_active": true}'

curl -X PUT http://localhost:8000/api/workspaces/1/activate  # Activate workspace

# Permission Management within Workspaces
curl http://localhost:8000/api/workspaces/1/permissions      # List workspace permissions
curl -X POST http://localhost:8000/api/workspaces/1/permissions \ # Add permission
  -H "Content-Type: application/json" \
  -d '{"path": "projects", "permission_type": "write", "rule_type": "allow"}'

# Batch Effective Permissions (Cornerstone API for UI)
curl -X POST http://localhost:8000/api/workspaces/1/effective-permissions:batch \
  -H "Content-Type: application/json" \
  -d '{"paths": ["/materials/docs", "/projects/app", "/private/secret"]}'

# Migration from Phase 2 Config
python -m app.scripts.migrate_config_to_db --workspace-name "Legacy Config" --activate --dry-run
python -m app.scripts.migrate_config_to_db --workspace-name "Legacy Config" --activate  # Actual migration

# Legacy Permission Management (Phase 2 - Deprecated)
# Note: Config file system has been removed to prevent confusion
# All permission management now uses the database workspace system above
```

## Testing Strategy
- **Backend:** Use pytest for API and WebSocket testing
- **Frontend:** Use Vitest for React component testing
- **Integration:** Test WebSocket communication between services
- **MCP Protocol:** ✅ Validate protocol compliance with test clients
- **Permission System:** ✅ Comprehensive test matrix for precedence logic

## Current Issues and Next Steps

### ✅ Resolved Issues (Phase 2)
- ~~MCP protocol implementation was stubbed~~ **FIXED: Complete implementation**
- ~~File system tools not implemented~~ **FIXED: All core tools implemented**
- ~~Permission management system pending~~ **FIXED: Config-file system implemented**
- ~~Activity logging needs formatting~~ **FIXED: Real-time WebSocket broadcasting**
- ~~Hardcoded permissions need config migration~~ **FIXED: JSON config with Trie caching**
- ~~Permission changes not persisting~~ **FIXED: Atomic file updates with optimistic locking**
- ~~Frontend PermissionIndicator API integration~~ **FIXED: Proper API endpoint usage**
- ~~Rule IDs not displayed in UI~~ **FIXED: Rule ID display in permission editor**
- ~~Integration tests failing in Phase 2 environment~~ **FIXED: All tests passing**

### 🚧 Current Focus: Phase 3B - Advanced Workspace UI
- **Priority 1:** Workspace management UI components (create, delete, activate)
- **Priority 2:** Two-panel permission editor with batch API integration
- **Priority 3:** "Inspect Permission" tooltip/modal with matched rule explanations
- **Priority 4:** Real-time workspace context switching with UI updates

### 📋 Future Work
- Multi-tenant permission contexts
- Advanced security features (rate limiting, audit trails)
- Enhanced error reporting and debugging tools
- Performance optimization and monitoring
- Production deployment documentation

## Development Philosophy
1. **Simplicity First:** Single `docker-compose up` to start everything
2. **Clear Separation:** Backend handles all logic, frontend is purely presentational
3. **Real-time by Default:** WebSockets for instant feedback
4. **Security through Clarity:** Explicit config-based permissions with formal precedence
5. **Developer Experience:** Hot-reload, clear logs, accessible documentation
6. **Safe Deployment:** Feature flags for gradual rollout of new capabilities

## Success Metrics ✅
- **Claude Code Integration:** Successfully connected as "wisdom" MCP server via HTTP transport
- **Tool Discovery:** All 3 tools (`read_file`, `list_files`, `write_file`) properly discovered by Claude Code
- **Protocol Compliance:** Full JSON-RPC 2.0 and MCP 2024-11-05 specification adherence
- **Tool Execution:** Successfully tested file operations with actual filesystem (C:/Users/MartinBielik/MCP Test/)
- **Permission Resolution:** Config-file permissions working with formal precedence logic
- **Performance:** Trie-based caching provides sub-millisecond permission checks
- **UI Integration:** Permission editor working with rule ID display and atomic updates
- **Real-time Updates:** UI receives live activity feed from MCP operations
- **Error Handling:** Comprehensive error responses with proper JSON-RPC codes
- **Development Workflow:** Hot-reload development environment fully operational
- **File Persistence:** Permission changes properly saved to config files
- **Integration Testing:** Full MCP protocol testing with actual directories (materials, projects)
- **Deny Rule Testing:** Verified deny rules properly block access (materials/01_Introduction to Software Engineering)

## Getting Help
- **Architecture Details:** See comprehensive `README.md`
- **API Documentation:** http://localhost:8000/docs when running
- **Version History:** Complete `changelog.md` with implementation details
- **Development Plan:** Current roadmap in `plan.md`
- **Docker Logs:** `docker-compose logs -f` for debugging
- **Database Inspection:** SQLite browser or CLI tools

---

**🎉 The MCP KnowledgeExplorer is now complete with Phase 3B Advanced Workspace UI!**

*The database-driven workspace permission system is production-ready with advanced caching, formal precedence logic, and a comprehensive UI. The system architecture has been simplified with single `/source` mount point and removal of legacy config file system. All Phase 3B features are implemented, tested, and working correctly with full workspace management capabilities.*

**Recent Improvements (v3.1.0):**
- ✅ **Legacy Mount Removal:** Simplified from dual `/shared-fs` + `/source` to single `/source` mount
- ✅ **UI Cleanup:** Removed File Explorer and Settings tabs to eliminate dual system confusion
- ✅ **Config File Removal:** Deleted `permissions.json` to prevent config vs database conflicts
- ✅ **Permission Bug Fixes:** Fixed permission indicator mapping bugs (BUG-001)
- ✅ **Architecture Simplification:** Single source of truth with database-only permissions

---
*This CLAUDE.md file serves as your primary context for understanding and working with the MCP KnowledgeExplorer project. Last updated: 2025-01-15 - Phase 3B Complete with Simplified Architecture*
