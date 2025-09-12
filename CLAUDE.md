# MCP KnowledgeExplorer - Project Context for Claude

## Project Overview
**Name:** MCP KnowledgeExplorer  
**Type:** Full-stack web application with MCP (Model Context Protocol) server  
**Purpose:** A sophisticated, local-first Model Context Protocol server that enables AI agents to assist with research, providing a web-based UI for configuration, real-time monitoring, and granular permission management over the local file system.

## 🎉 MAJOR MILESTONE: MCP Protocol Implementation Complete
**Status:** ✅ **FULLY OPERATIONAL MCP SERVER ("wisdom")**  
The core MCP server is now successfully implemented with complete JSON-RPC 2.0 support, file system tools, and security controls. AI agents can connect and perform file operations safely. The server is registered in Claude Code as "wisdom" for easy reference.

**Key Achievements:**
- ✅ Complete MCP JSON-RPC 2.0 protocol implementation
- ✅ File system tools: `read_file`, `list_files`, `write_file`
- ✅ Permission-based security system with allowlist controls
- ✅ Real-time activity logging via WebSocket to UI
- ✅ Comprehensive error handling with JSON-RPC compliance
- ✅ Both WebSocket and HTTP MCP endpoints for client flexibility

## Architecture: The "Unified Hub" Model
The system follows a **"Unified Hub"** architecture pattern - a single, persistent backend server acts as the central point of control for all clients (both browser UI and AI agents). Think of it as a permanent restaurant where all customers come through the same front door and are handled by the same staff.

## Technology Stack

### Backend (Python/FastAPI) - ✅ FULLY IMPLEMENTED
- **Framework:** FastAPI with async/await support
- **MCP Protocol:** Complete JSON-RPC 2.0 implementation (MCP 2024-11-05)
- **Database:** SQLite for persistent state storage
- **Real-time:** WebSockets for live communication
- **Security:** Allowlist-based permission system with path validation
- **Dependencies:** 
  - fastapi, uvicorn[standard], sqlalchemy, websockets, python-dotenv
- **Port:** 8000 (configurable via BACKEND_PORT env var)
- **Entry Point:** `backend/app/main.py`

### Frontend (React/TypeScript) - 🚧 BASIC IMPLEMENTATION
- **Framework:** React 18 with TypeScript
- **Build Tool:** Vite for fast development
- **State Management:** Zustand for global state
- **Styling:** Tailwind CSS for utility-first styling
- **Port:** 5173 (configurable via FRONTEND_PORT env var)
- **Entry Point:** `frontend/src/main.tsx`

### Infrastructure - ✅ PRODUCTION READY
- **Containerization:** Docker & Docker Compose
- **Development:** Hot-reload enabled in both frontend and backend
- **Volumes:** 
  - Database: `./data` mounted to `/data`
  - Shared Files: `./shared-fs` mounted to `/shared-fs`

## Directory Structure

```
MCPFileServer/
├── backend/                    # Python FastAPI backend
│   ├── app/                   # Main application code
│   │   ├── main.py           # ✅ FastAPI app with complete MCP implementation
│   │   ├── api/               # API endpoints and WebSocket handlers
│   │   │   ├── endpoints.py  # REST API routes
│   │   │   └── websockets.py # WebSocket connection manager
│   │   ├── services/          # ✅ Business logic services
│   │   │   ├── file_service.py      # ✅ File system operations with security
│   │   │   ├── mcp_service.py       # ✅ MCP tool definitions and discovery
│   │   │   └── permission_service.py # ✅ Security and permission checking
│   │   ├── schemas/           # ✅ Pydantic schemas
│   │   │   ├── mcp.py        # ✅ JSON-RPC 2.0 and MCP schema definitions
│   │   │   └── setting.py    # Settings schemas
│   │   ├── models/            # SQLAlchemy models
│   │   ├── crud/              # Database CRUD operations
│   │   └── database.py       # Database configuration
│   ├── Dockerfile            # Backend container definition
│   └── requirements.txt      # Python dependencies
├── frontend/                  # React TypeScript frontend
│   ├── src/                   # Source code
│   │   ├── App.tsx           # 🚧 Main React component with basic UI
│   │   ├── main.tsx          # React entry point
│   │   ├── index.css         # Global styles
│   │   └── CLAUDE.md         # Frontend context documentation
│   ├── package.json          # Node dependencies
│   ├── vite.config.ts        # Vite configuration
│   ├── tsconfig.json         # TypeScript configuration
│   └── tailwind.config.js    # Tailwind CSS configuration
├── data/                      # SQLite database storage (gitignored)
├── shared-fs/                 # Shared file system for MCP operations
├── docker-compose.yml         # Multi-container orchestration
├── .env                       # Environment variables
├── CLAUDE.md                  # This file - project context
├── README.md                  # Comprehensive user documentation
├── changelog.md               # ✅ Complete version history
├── plan.md                    # Development roadmap
└── context-strategy.md        # Documentation strategy
```

## Key Components and Endpoints

### Backend API Structure - ✅ FULLY OPERATIONAL
- **HTTP Endpoints:**
  - `GET /` - Health check endpoint
  - `/api/*` - REST API routes (via `api_router`)
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

### Connection Managers
The backend maintains two separate `ConnectionManager` instances:
- `ui_manager` - Manages browser UI WebSocket connections
- `mcp_manager` - Manages AI client WebSocket connections

This separation allows for targeted messaging and different protocol handling.

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

### ✅ Fully Implemented Features
1. **Backend Hub Server:** Fully functional FastAPI server with WebSocket support
2. **MCP Protocol Handler:** Complete JSON-RPC 2.0 implementation with MCP 2024-11-05 spec
3. **File System Tools:** Production-ready tools with integrated security
4. **Permission Management:** Allowlist-based file access control system
5. **Real-time Activity Logging:** WebSocket broadcasting of MCP operations to UI
6. **Comprehensive Error Handling:** JSON-RPC compliant error responses
7. **Dual WebSocket Management:** Separate handlers for UI and MCP clients
8. **Database Integration:** SQLite setup with SQLAlchemy ORM
9. **Docker Environment:** Complete containerization with development optimizations
10. **Security Layer:** Path validation and directory traversal prevention

### 🚧 In Progress
1. **Frontend UI Components:** 
   - Basic React shell implemented
   - File Explorer with breadcrumb navigation (planned)
   - Permission assignment panel (Context/Working/Output) (planned)
   - Enhanced Activity Log with filtering (planned)
   - Configuration dashboard (planned)

### 📋 Future Enhancements
1. **Search Features:** Keyword and semantic search capabilities
2. **Multi-client Management:** Enhanced support for multiple AI clients
3. **Advanced Security:** API keys, rate limiting, audit trails
4. **UI/UX Polish:** Shadcn/ui integration, responsive design

## Data Flow Scenarios

### Scenario 1: UI Configuration
1. Browser loads React app from frontend container
2. UI makes HTTP API call to backend for initial config
3. UI establishes WebSocket connection for real-time updates

### Scenario 2: AI Agent Tool Execution ✅ FULLY IMPLEMENTED
1. AI client connects to `/ws/mcp` WebSocket endpoint or sends HTTP request to `/mcp`
2. Sends MCP `initialize` request, server responds with capabilities
3. Client sends `tools/list` to discover available tools
4. Client sends MCP `tools/call` request with parameters
5. Backend validates permissions via `permission_service`
6. Backend executes file system logic via `file_service`
7. Returns structured result to AI client
8. Broadcasts activity log to UI clients via WebSocket

## Security Model - ✅ FULLY IMPLEMENTED

### Allowlist Approach
- **Principle:** Only explicitly permitted files/folders are accessible
- **Implementation:** `permission_service.py` with hardcoded permissions
- **Validation:** Every file operation validated against allowlist

### Current Permission Configuration
```python
PERMISSIONS = {
    "context": ["docs", "projects"],    # Read-only access
    "working": ["projects", "output"],  # Read-write access  
}
```

### Security Features
- **Docker Bind Mounts:** Controlled interface to host file system
- **Path Validation:** Prevents directory traversal attacks
- **Mount Point Isolation:** All operations restricted to `/shared-fs`
- **Permission Levels:**
  - Context: Read-only access to specified directories
  - Working: Read-write access to specified directories
  - Output: Agent-controlled directory (future feature)

## Environment Variables
Key configuration options in `.env`:
- `BACKEND_PORT`: Backend server port (default: 8000)
- `FRONTEND_PORT`: Frontend dev server port (default: 5173)
- `DATABASE_PATH`: SQLite database location (default: ./data)
- `SHARED_FS_PATH`: Shared file system mount (default: ./shared-fs)

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

# Test file operation (note: uses "name" not "toolName")
curl -X POST http://localhost:8000/mcp -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "read_file", "arguments": {"path": "docs/test.txt"}}, "id": 3}'
```

**Note:** The server is registered as "wisdom" in Claude Code and provides the following MCP tools:
- `mcp__wisdom__read_file` - Read file contents with permission checking
- `mcp__wisdom__list_files` - List directory contents  
- `mcp__wisdom__write_file` - Write file contents (subject to permissions)

### Backend Development
```bash
# Install new Python package
docker-compose exec backend pip install <package>
# Update requirements.txt
docker-compose exec backend pip freeze > requirements.txt
```

### Frontend Development
```bash
# Install new npm package
docker-compose exec frontend npm install <package>
# Run linting
docker-compose exec frontend npm run lint
# Build for production
docker-compose exec frontend npm run build
```

### Database Operations
```bash
# Access SQLite database
sqlite3 data/database.db
```

### Viewing Logs
```bash
# View all logs
docker-compose logs

# View backend logs only
docker-compose logs backend

# Follow logs in real-time
docker-compose logs -f
```

## Testing Strategy
- **Backend:** Use pytest for API and WebSocket testing
- **Frontend:** Use Vitest for React component testing
- **Integration:** Test WebSocket communication between services
- **MCP Protocol:** ✅ Validate protocol compliance with test clients

## Future Extensibility Points
1. **Search Services:** Modular service architecture ready for KeywordSearchService and SemanticSearchService
2. **Vector Database:** Qdrant container can be added for semantic search when needed
3. **WebSocket Scaling:** Current hub can be split for independent scaling of UI/MCP traffic
4. **Component Library:** Ready for Shadcn/ui integration for professional UI components

## Current Issues and Next Steps

### ✅ Resolved Issues
- ~~MCP protocol implementation was stubbed~~ **FIXED: Complete implementation**
- ~~File system tools not implemented~~ **FIXED: All core tools implemented**
- ~~Permission management system pending~~ **FIXED: Allowlist system implemented**
- ~~Activity logging needs formatting~~ **FIXED: Real-time WebSocket broadcasting**

### 🚧 Current Focus: Frontend Development
- **Priority 1:** File Explorer component with tree view
- **Priority 2:** Permission Management UI interface
- **Priority 3:** Enhanced Activity Log with filtering and export
- **Priority 4:** Configuration Dashboard

### 📋 Future Work
- Database-driven permissions (move from hardcoded to UI-managed)
- Multi-client session management
- Enhanced error reporting and debugging tools
- Performance optimization and monitoring

## Development Philosophy
1. **Simplicity First:** Single `docker-compose up` to start everything
2. **Clear Separation:** Backend handles all logic, frontend is purely presentational
3. **Real-time by Default:** WebSockets for instant feedback
4. **Security through Simplicity:** Explicit allowlist model, no complex permission chains
5. **Developer Experience:** Hot-reload, clear logs, accessible documentation

## Success Metrics ✅
- **Claude Code Integration:** Successfully connected as "wisdom" MCP server via HTTP transport
- **Tool Discovery:** All 3 tools (`read_file`, `list_files`, `write_file`) properly discovered by Claude Code
- **Protocol Compliance:** Full JSON-RPC 2.0 and MCP 2024-11-05 specification adherence with correct schema format
- **Tool Execution:** Successfully tested file operations through Claude Code MCP interface
- **Security Validation:** Path traversal prevention and permission checking working (write operations properly blocked)
- **Real-time Updates:** UI receives live activity feed from MCP operations
- **Error Handling:** Comprehensive error responses with proper JSON-RPC codes (-32001 Permission Denied, -32002 File Not Found)
- **Development Workflow:** Hot-reload development environment fully operational

## Getting Help
- **Architecture Details:** See comprehensive `README.md`
- **API Documentation:** http://localhost:8000/docs when running
- **Version History:** Complete `changelog.md` with implementation details
- **Development Plan:** Current roadmap in `plan.md`
- **Docker Logs:** `docker-compose logs -f` for debugging
- **Database Inspection:** SQLite browser or CLI tools

---

**🎉 The MCP KnowledgeExplorer has successfully achieved its core milestone!**

*The MCP server is now fully operational and ready for AI agent integration. The next development phase focuses on enhancing the frontend UI to provide comprehensive file management and monitoring capabilities.*

---
*This CLAUDE.md file serves as your primary context for understanding and working with the MCP KnowledgeExplorer project. Last updated: 2025-01-12 - MCP Protocol Implementation Complete*