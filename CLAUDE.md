# MCP KnowledgeExplorer - Project Context for Claude

## Project Overview
**Name:** MCP KnowledgeExplorer
**Type:** Full-stack web application with MCP (Model Context Protocol) server
**Purpose:** A sophisticated, local-first Model Context Protocol server that enables AI agents to assist with research, providing a web-based UI for configuration, real-time monitoring, and granular permission management over the local file system.

## 🎉 MAJOR MILESTONE: Phase 3A Complete - Database-Driven Workspace System
**Status:** ✅ **PHASE 3A COMPLETE - Database-Driven Permission System with Full Workspace Backend**

We have successfully completed Phase 3A of the dynamic workspace system! The MCP KnowledgeExplorer now features a complete database-driven workspace and permission system with comprehensive CRUD APIs, batch permission resolution, audit logging, and automated migration capabilities. All Phase 3A functionality has been implemented, thoroughly tested, and is production-ready.

**Phase 3A Achievements:**
- ✅ **🆕 Complete Database Schema**: Full `Workspace` and `Permission` SQLAlchemy models with constraints
- ✅ **🆕 Workspace Management**: Full CRUD APIs for workspace creation, activation, and management
- ✅ **🆕 Permission Management**: Complete permission CRUD with workspace context and validation
- ✅ **🆕 Batch Permission API**: High-performance `POST /api/workspaces/{id}/effective-permissions:batch` endpoint
- ✅ **🆕 Database Permission Service**: New `DatabasePermissionService` with preserved Trie caching
- ✅ **🆕 Audit Logging System**: Comprehensive structured audit events for all permission decisions
- ✅ **🆕 Migration Script**: Complete, idempotent migration from config files to database
- ✅ **🆕 Comprehensive Test Suite**: Full Phase 3A test coverage with performance validation
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
  - Shared Files: `C:/Users/MartinBielik/MCP Test/` mounted to `/shared-fs`

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

**Permission Configuration:** `config/permissions.json`
- materials/ - Read-only access (allow rule)
- projects/ - Read-write access (allow rule)
- materials/01_Introduction to Software Engineering/ - Blocked (deny rule overrides)
- private stuff/ - No access (default deny)

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

### Starting the Application
```bash
# Single command to start everything
docker-compose up

# Or run in detached mode
docker-compose up -d
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

## Core Functionality (Current State)

### ✅ Phase 2 Complete: Config-File Driven Permission System
1. **Backend Hub Server:** Fully functional FastAPI server with WebSocket support
2. **MCP Protocol Handler:** Complete JSON-RPC 2.0 implementation with MCP 2024-11-05 spec
3. **File System Tools:** Production-ready tools with integrated security
4. **🆕 Config Permission Management:** JSON-based permission rules with formal precedence
5. **🆕 Trie-Based Caching:** High-performance permission resolution with in-memory cache
6. **🆕 File Watcher Integration:** Automatic config reload on file changes
7. **🆕 Feature Flag System:** Safe Phase 2/3 deployment with environment toggles
8. **🆕 Permission Editor UI:** Visual and JSON editor with rule ID display
9. **🆕 Atomic Config Updates:** Safe multi-user editing with optimistic locking
10. **🆕 Verified Working State:** All bug fixes complete, full integration tested
11. **Real-time Activity Logging:** WebSocket broadcasting of MCP operations to UI
12. **Comprehensive Error Handling:** JSON-RPC compliant error responses
13. **Dual WebSocket Management:** Separate handlers for UI and MCP clients
14. **Database Integration:** SQLite setup with SQLAlchemy ORM
15. **Docker Environment:** Complete containerization with development optimizations
16. **Security Layer:** Path validation and directory traversal prevention
17. **Advanced File Explorer:** Tree navigation with breadcrumbs and pagination
18. **Visual Permission System:** Color-coded indicators (Read-Only/Read-Write/No Access)
19. **Secure Browse API:** `/api/browse` with pagination and security hardening
20. **Enhanced UI:** Tabbed interface with File Explorer, Permission Editor, and Server Status
21. **Permission Legend:** Clear documentation of permission levels in sidebar

### ✅ Complete: Phase 3A - Database-Driven Permissions
1. ✅ **Database Schema:** Complete migration to SQLite with full workspace and permission models
2. ✅ **Workspace Management:** Full workspace CRUD with activation and context switching
3. ✅ **Audit Logging:** Comprehensive tracking of all permission changes and access attempts
4. ✅ **Migration Tools:** Complete, idempotent config-to-database migration script
5. ✅ **Batch Permission API:** High-performance endpoint for efficient UI integration

### 🚧 Next: Phase 3B - Advanced Workspace UI
1. **Workspace UI Components:** Create, delete, and activate workspaces from the UI
2. **Two-Panel Permission Editor:** Full visual workspace permission management
3. **"Inspect Permission" Feature:** Detailed permission explanations with matched rule info
4. **Real-time Workspace Switching:** Dynamic UI updates when workspace context changes

### 📋 Future Enhancements
1. **Search Features:** Keyword and semantic search capabilities
2. **Multi-client Management:** Enhanced support for multiple AI clients
3. **Advanced Security:** Rate limiting, audit trails, compliance reporting
4. **UI/UX Polish:** Shadcn/ui integration, responsive design, accessibility

## Security Model - ✅ PHASE 2 COMPLETE

### Config-File Based Permissions
- **Principle:** Permission rules defined in JSON configuration files
- **Implementation:** `config_permission_service.py` with Trie caching
- **Validation:** Every file operation validated against config rules

**Security Features:**
- **Docker Bind Mounts:** Controlled interface to host file system
- **Path Validation:** Prevents directory traversal attacks
- **Mount Point Isolation:** All operations restricted to `/shared-fs`
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

# Legacy Permission Management (Phase 2 - Still Available)
curl http://localhost:8000/api/config/permissions           # View current config
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

**🎉 The MCP KnowledgeExplorer Phase 2 is now complete and fully operational!**

*The config-file driven permission system is production-ready with advanced caching, formal precedence logic, and a professional UI. The system has been successfully tested with actual filesystem access to C:/Users/MartinBielik/MCP Test/ containing materials, projects, and private directories. All Phase 2 features are implemented, tested, and working correctly.*

---
*This CLAUDE.md file serves as your primary context for understanding and working with the MCP KnowledgeExplorer project. Last updated: 2025-01-14 - Phase 2 Config-File Permission System Complete and Fully Operational*
