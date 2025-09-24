# MCP KnowledgeExplorer - Project Context for Claude

## Project Overview
**Name:** MCP KnowledgeExplorer
**Type:** Full-stack web application with MCP (Model Context Protocol) server
**Purpose:** A sophisticated, local-first Model Context Protocol server that enables AI agents to assist with research, providing a web-based UI for configuration, real-time monitoring, and granular permission management over the local file system.

## 🎉 MAJOR MILESTONE: Phase 4A Complete - Production Ready & Fully Documented
**Status:** ✅ **PHASE 4A 100% COMPLETE - Ready for Phase 4B Semantic Search**

Phase 4A advanced search infrastructure is fully operational with comprehensive documentation for independent software engineers. All critical production issues have been resolved, and the system is ready for Phase 4B semantic search implementation.

**🎯 Phase 4A Achievement Summary:**
- ✅ **🚀 Search Infrastructure Complete**: Indexer service with file watching, job queue, and metadata extraction
- ✅ **🛠️ 7 MCP Tools Operational**: 3 core file system + 4 new search tools with cursor pagination
- ✅ **💾 Database Integration**: Shared SQLite with WAL mode, Phase 4A models, and proper bootstrap
- ✅ **📊 Performance Validated**: Sub-100ms response times, crash recovery, comprehensive testing
- ✅ **📖 Documentation Complete**: Full service documentation, implementation guide, and Phase 4B roadmap

**🔧 Critical Production Issues Resolved (v4.0.1):**
- ✅ **Issue 013 - Database URL Misconfiguration**: Backend now correctly connects to database file instead of directory
- ✅ **Issue 014 - Indexer Import Errors**: All duplicate import issues resolved, indexer fully operational
- ✅ **Issue 015 - Frontend 404 Cascade**: Graceful empty state handling prevents workspace 404 errors
- ✅ **SQLAlchemy Parameter Format**: Fixed database bootstrap query parameter handling
- ✅ **Environment Variable Handling**: Corrected Docker container path configurations
- ✅ **Cross-Container Imports**: Enhanced model import compatibility between services

**Phase 4A Infrastructure Fixes (v4.0.0 - Maintained):**
- ✅ **🔧 Database Schema Creation Fixed**: All Phase 4A models properly imported and created
- ✅ **🔧 Indexer DB Connection Hardened**: Proper DatabaseBootstrap with WAL mode and concurrency settings
- ✅ **🔧 File Rename Handling Enhanced**: Improved doc_id generation preserves identity through renames
- ✅ **🔧 Job De-duplication Fixed**: Removed created_at from job_signature for proper race condition handling
- ✅ **🔧 Configuration Drift Resolved**: Single source of truth with Phase4AConfig across all services
- ✅ **🔧 Cursor-Based Pagination Implemented**: API now meets specification with efficient pagination
- ✅ **🔧 Critical Test Suite Created**: Comprehensive tests for atomic job claiming, crash recovery, and file watching

**Phase 3B Achievements (Maintained):**
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

### Backend (Python/FastAPI) - ✅ PHASE 4A HARDENED
- **Framework:** FastAPI with async/await support
- **MCP Protocol:** Complete JSON-RPC 2.0 implementation (MCP 2024-11-05) with search tools
- **Database:** SQLite with WAL mode for concurrency, proper bootstrap, schema versioning
- **Real-time:** WebSockets for live communication
- **Security:** Database-driven permission system with workspace contexts and Trie caching
- **Search Tools:** list_all_files, search_files_by_metadata, get_file_info, get_search_statistics
- **New Features:** Cursor-based pagination, enhanced error handling, comprehensive test coverage
- **Dependencies:**
  - fastapi, uvicorn[standard], sqlalchemy, websockets, python-dotenv, watchdog
- **Port:** 8000 (configurable via BACKEND_PORT env var)
- **Entry Point:** `backend/app/main.py`

### Indexer Service (Python/FastAPI) - ✅ PHASE 4A COMPLETE
- **Framework:** FastAPI with background processing capabilities
- **Purpose:** File system monitoring, job queue management, metadata extraction
- **Database:** Shared SQLite with proper bootstrap and concurrency support
- **Job Queue:** Crash-resilient with atomic claiming, exponential backoff, dead letter queue
- **File Watcher:** Intelligent monitoring with stability checks and rename handling
- **Control:** Pause/resume functionality, throttling, real-time status reporting
- **Dependencies:**
  - fastapi, uvicorn[standard], sqlalchemy, watchdog, pillow, python-magic
- **Port:** 8002 (configurable via INDEXER_PORT env var)
- **Entry Point:** `indexer/app/main.py`

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
- `list_all_files(limit?: number, offset?: number)` - List all indexed files across the workspace
- `search_files_by_metadata(query: object)` - Search files using metadata criteria
- `get_file_info(path: string)` - Get detailed file information and metadata
- `get_search_statistics()` - Retrieve indexing and search statistics

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
- **MCP Wisdom Test Routine**: Use `./scripts/test-mcp-wisdom.sh` for comprehensive MCP functionality validation

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
- `mcp__wisdom__list_files` - List directory contents with metadata
- `mcp__wisdom__write_file` - Write file contents (subject to permissions)
- `mcp__wisdom__list_all_files` - List all indexed files across workspace
- `mcp__wisdom__search_files_by_metadata` - Search files by metadata criteria
- `mcp__wisdom__get_file_info` - Get detailed file information and metadata
- `mcp__wisdom__get_search_statistics` - Retrieve indexing and search statistics

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

### MCP Wisdom Comprehensive Test Routine ✅
**Location:** `backend/tests/test_mcp_wisdom_comprehensive.py` and `scripts/test-mcp-wisdom.sh`

A comprehensive, adaptive test suite for validating the complete MCP Wisdom functionality after every development phase. The test suite automatically validates assumptions about the current environment and adapts to changes before running tests.

**Key Features:**
- **Pre-validation:** Checks current workspace, permissions, and environment state
- **Adaptive Configuration:** Adjusts test expectations based on actual system state
- **Comprehensive Coverage:** Tests all MCP tools, permission enforcement, and security
- **Performance Validation:** Measures response times and system performance
- **JSON Reporting:** Generates detailed test reports for tracking and analysis
- **Multiple Modes:** Quick, comprehensive, and isolated test environments

**Usage:**
```bash
# Quick test with current environment
./scripts/test-mcp-wisdom.sh

# Full comprehensive test suite
./scripts/test-mcp-wisdom.sh --comprehensive

# Create isolated test environment
./scripts/test-mcp-wisdom.sh --isolated

# View last test report
./scripts/test-mcp-wisdom.sh --report-only
```

**Test Categories:**
1. **Environment Validation:** Docker containers, backend health, MCP endpoint
2. **Tool Functionality:** `list_files`, `read_file`, `write_file`, `list_all_files`
3. **Permission Enforcement:** Allow/deny rule testing, precedence validation
4. **Security Testing:** Path traversal prevention, unauthorized access blocking
5. **Performance Testing:** Response time measurement, resource usage monitoring
6. **Edge Case Testing:** Error handling, malformed requests, boundary conditions

**Adaptive Behavior:**
- Automatically discovers active workspace and permission rules
- Adapts test expectations to current environment state
- Validates test assumptions before execution (workspace exists, permissions configured)
- Creates isolated test workspace if `--isolated` flag is used
- Self-corrects when environment changes between test runs

**Reporting:**
- **JSON Report:** `mcp_wisdom_test_report.json` with detailed results and metrics
- **Detailed Log:** `mcp_wisdom_test.log` with complete test execution trace
- **Console Output:** Real-time test progress with color-coded results

This test routine should be executed after every major development phase to ensure MCP Wisdom functionality remains intact and performs correctly.

## Current Issues and Next Steps

### ✅ Resolved Issues (v4.0.2 - Critical Production Issues Fully Resolved)
- ~~Issue 013: Database URL misconfiguration causing empty workspace API~~ **FIXED: Docker volume mount configuration and database path standardization**
- ~~Issue 014: Indexer import errors preventing service startup~~ **FIXED: Removed duplicate import statements causing module conflicts**
- ~~Issue 015: Frontend workspace 404 errors and empty state handling~~ **FIXED: API client returning complete response with active_workspace_id**
- ~~SQLAlchemy parameter format errors~~ **FIXED: Added text() wrapper for raw SQL queries**
- ~~Docker environment variable issues~~ **FIXED: Container vs local path detection logic**
- ~~Database diagnostic endpoint missing~~ **FIXED: Added /api/system/db-info for troubleshooting**

### ✅ Resolved Issues (Phase 2-4A Infrastructure)
- ~~MCP protocol implementation was stubbed~~ **FIXED: Complete implementation**
- ~~File system tools not implemented~~ **FIXED: All core tools implemented**
- ~~Permission management system pending~~ **FIXED: Database-driven workspace system**
- ~~Activity logging needs formatting~~ **FIXED: Real-time WebSocket broadcasting**
- ~~Hardcoded permissions need config migration~~ **FIXED: Database workspace permissions**
- ~~Permission changes not persisting~~ **FIXED: Atomic database operations**
- ~~Frontend PermissionIndicator API integration~~ **FIXED: Batch API integration**
- ~~Rule IDs not displayed in UI~~ **FIXED: Complete permission inspector**
- ~~Integration tests failing~~ **FIXED: Comprehensive MCP Wisdom test suite**
- ~~Database schema creation issues~~ **FIXED: All Phase 4A models properly imported**
- ~~Indexer database connection problems~~ **FIXED: Proper DatabaseBootstrap with WAL mode**
- ~~Job de-duplication race conditions~~ **FIXED: Proper job signature calculation**
- ~~Configuration drift between services~~ **FIXED: Single source of truth (Phase4AConfig)**

### ✅ Completed: All Implementation Phases (PHASE 4A COMPLETE)
- ✅ **Phase 2**: Complete MCP protocol implementation with file system tools
- ✅ **Phase 3A**: Database-driven workspace and permission management
- ✅ **Phase 3B**: Advanced workspace UI with two-panel permission editor
- ✅ **Phase 4A**: ⭐ **COMPLETE** ⭐ Advanced search infrastructure with indexer service
- ✅ **Phase 4A Critical Fixes**: All production blocking issues resolved
- ✅ **Phase 4A Documentation**: Comprehensive documentation for Phase 4B development

### 🎯 Production Readiness Status - PHASE 4A COMPLETE ✅
**The MCP KnowledgeExplorer Phase 4A is 100% COMPLETE** with all objectives achieved:
- ✅ **Search Infrastructure**: Indexer service with job queue, file watching, metadata extraction
- ✅ **7 MCP Tools**: 3 core + 4 search tools (list_all_files, search_files_by_metadata, get_file_info, get_search_statistics)
- ✅ **Database Integration**: Phase 4A models (IndexedFile, IndexJob, ControlSetting) with WAL mode
- ✅ **Performance Validated**: Sub-100ms response times, cursor pagination, comprehensive testing
- ✅ **Production Stability**: All services start successfully, proper error handling, graceful recovery
- ✅ **Documentation Ready**: Complete service docs, implementation summary, Phase 4B development guide

### 📋 Next Phase: Phase 4B Semantic Search
**Ready for Independent Development** - Complete documentation provided:
- 📖 `docs/Phase4A-Implementation-Summary.md` - Complete achievement overview
- 📖 `docs/Phase4B-Development-Guide.md` - Detailed implementation roadmap
- 📖 `indexer/README.md` - Comprehensive indexer service documentation
- 🎯 **Phase 4B Objectives**: Vector embeddings, semantic search, document clustering, 4 new semantic MCP tools

## Development Philosophy
1. **Simplicity First:** Single `docker-compose up` to start everything
2. **Clear Separation:** Backend handles all logic, frontend is purely presentational
3. **Real-time by Default:** WebSockets for instant feedback
4. **Security through Clarity:** Explicit config-based permissions with formal precedence
5. **Developer Experience:** Hot-reload, clear logs, accessible documentation
6. **Safe Deployment:** Feature flags for gradual rollout of new capabilities

## Success Metrics ✅ (v4.0.1 - FULLY OPERATIONAL)
### 🎯 Critical Production Issues Resolved
- **Database Connectivity:** Backend correctly connects to SQLite database file (was connecting to directory)
- **Service Startup:** All three services (backend, indexer, frontend) start successfully without errors
- **Import Resolution:** All Python imports work correctly in containerized environments
- **Frontend Stability:** No more 404 cascade errors when workspace list is empty
- **Container Integration:** Proper environment variable handling and volume mounting

### 🏆 Complete MCP Implementation Validated
- **Claude Code Integration:** Successfully connected as "wisdom" MCP server via HTTP transport
- **Tool Discovery:** All 7 MCP tools properly discovered by Claude Code (core file system + search tools)
- **Protocol Compliance:** Full JSON-RPC 2.0 and MCP 2024-11-05 specification adherence
- **Tool Execution:** Successfully tested file operations with workspace permission validation
- **Permission Resolution:** Database-driven workspace permissions working with formal precedence logic
- **Performance:** Trie-based caching provides sub-millisecond permission checks
- **UI Integration:** Complete workspace management with two-panel permission editor
- **Real-time Updates:** UI receives live activity feed from MCP operations via WebSocket
- **Error Handling:** Comprehensive error responses with proper JSON-RPC codes

### ⚡ Production Performance Metrics
- **Service Health:** All health checks passing (backend, indexer, frontend)
- **Database Operations:** Workspace CRUD operations complete in <50ms
- **MCP Response Times:** Tool calls complete in <100ms average
- **File Watching:** Indexer monitors file system with 2-second debounce
- **WebSocket Connectivity:** Real-time UI updates with <100ms latency
- **Development Workflow:** Hot-reload development environment fully operational

### 🧪 Comprehensive Testing Coverage
- **Unit Tests:** Core functionality covered with pytest
- **Integration Tests:** MCP Wisdom comprehensive test suite with 6 categories
- **End-to-End Testing:** Full workflow from workspace creation to MCP tool execution
- **Browser Testing:** Automated UI testing with Browser MCP tools
- **Performance Testing:** Automated response time validation
- **Error Scenarios:** Graceful handling of empty states and permission denials

## Getting Help
- **Architecture Details:** See comprehensive `README.md`
- **API Documentation:** http://localhost:8000/docs when running
- **Version History:** Complete `changelog.md` with implementation details
- **Development Plan:** Current roadmap in `plan.md`
- **Docker Logs:** `docker-compose logs -f` for debugging
- **Database Inspection:** SQLite browser or CLI tools

---

**🎉 The MCP KnowledgeExplorer Phase 4A is 100% COMPLETE - Ready for Semantic Search!**

*Phase 4A advanced search infrastructure is fully operational with comprehensive indexing, metadata extraction, and 7 MCP tools. All critical production issues have been resolved, and complete documentation has been provided for independent Phase 4B semantic search development.*

**Phase 4A Achievements (v4.0.1):**
- ✅ **Search Infrastructure Complete**: Indexer service with crash-resilient job processing
- ✅ **7 MCP Tools Operational**: Extended from 3 to 7 tools with 4 new search capabilities
- ✅ **Database Integration**: Phase 4A models with shared SQLite and WAL mode
- ✅ **Performance Validated**: Sub-100ms response times, comprehensive testing
- ✅ **Production Issues Resolved**: All 3 critical bugs fixed by independent review
- ✅ **Documentation Complete**: Implementation summary and Phase 4B development guide

**Phase 4B Ready Documentation:**
- 📖 **`docs/Phase4A-Implementation-Summary.md`** - Complete Phase 4A achievement overview
- 📖 **`docs/Phase4B-Development-Guide.md`** - Detailed semantic search implementation plan
- 📖 **`indexer/README.md`** - Comprehensive indexer service documentation

---
*This CLAUDE.md file serves as your primary context for understanding and working with the MCP KnowledgeExplorer project. Last updated: 2025-01-23 - Phase 4A Complete & Fully Documented*

## Recent Implementation Notes (post-4A polish)
- Root config shim: env_config.py re-exports config.env_config for stable imports in tests/local runs.
- Indexer /status includes jobs_per_minute (rolling) to support ETA computations.
- Indexer accepts eindex_file jobs in Phase 4A (handled like index_file).
- Frontend IndexerDashboard reads VITE_API_BASE_URL and refreshes recent files/jobs periodically.
- Docker-aware SHARED_FS_PATH validation: suppresses warning if /source mount exists.
- equests added to backend and indexer images for healthchecks.
- Path model: host C:\Users\<you>\MCP Test is mounted to container /source; services always use /source inside Docker.

