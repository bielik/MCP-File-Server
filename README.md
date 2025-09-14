# MCP KnowledgeExplorer

> **🎉 Status: Phase 2 Complete - Dynamic Config-Based Permission System!**
> The MCP server now features a comprehensive config-file driven permission system with advanced caching, formal precedence logic, and a professional permission editor UI! Configure granular file access permissions through an intuitive interface or JSON editing. All Phase 2 features are fully implemented, tested, and operational.

## Quick Start

```bash
# Start the entire system with one command
docker-compose up

# Access the services
# Frontend UI: http://localhost:5173
# Backend API: http://localhost:8000
# MCP HTTP: http://localhost:8000/mcp (for AI clients like Claude)
# MCP WebSocket: ws://localhost:8000/ws/mcp (internal/debug use only)

# Connect to MCP from Claude Code
claude mcp add --transport http wisdom http://localhost:8000/mcp

# Test the connection (examples with actual directories)
# List course materials directory
curl -X POST http://localhost:8000/mcp -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "list_files", "arguments": {"path": "materials"}}, "id": 1}'

# Read a file from the materials directory
curl -X POST http://localhost:8000/mcp -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "read_file", "arguments": {"path": "materials/Hallo.txt"}}, "id": 2}'

# Try to access blocked directory (should return Permission Denied)
curl -X POST http://localhost:8000/mcp -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "list_files", "arguments": {"path": "materials/01_Introduction to Software Engineering"}}, "id": 3}'
```

---

## 1. Introduction

### 1.1. Purpose

This project is a **production-ready Model Context Protocol (MCP) server** that enables AI agents to safely interact with your local file system. It provides HTTP endpoints for AI client connections and WebSocket for internal communication, along with a web-based management interface for real-time monitoring and granular permission control.

### 1.2. Current Status - ✅ Phase 2 Complete: Dynamic Config-Based Permission System

**✅ Fully Implemented and Tested:**
- **MCP Protocol**: Complete JSON-RPC 2.0 implementation with MCP 2024-11-05 specification
- **File System Tools**: `read_file`, `list_files`, `write_file` with integrated security
- **🆕 Config Permission System**: JSON-based permission rules with formal precedence logic
- **🆕 Trie-Based Caching**: High-performance in-memory permission resolution
- **🆕 Permission Editor UI**: Visual and JSON editor with rule ID display and atomic updates
- **🆕 File Watcher Integration**: Automatic config reload when permissions.json changes
- **🆕 Feature Flags**: Safe deployment with Phase 2/3 toggles (`ENABLE_CONFIG_FILE_PERMISSIONS=true`)
- **🆕 Bug Fixes Complete**: Permission persistence, frontend integration, rule ID display all working
- **🆕 Verified Working State**: Full MCP protocol testing with real filesystem confirmed
- **Real-time Monitoring**: Live activity feed via WebSocket to UI
- **Error Handling**: Comprehensive JSON-RPC compliant error responses
- **Dual Endpoints**: Both WebSocket (`/ws/mcp`) and HTTP (`/mcp`) for client flexibility
- **Advanced File Explorer**: Tree navigation with breadcrumbs and pagination
- **Visual Permissions**: Color-coded indicators (Read-Only/Read-Write/No Access)
- **Secure Browse API**: `/api/browse` with directory traversal prevention
- **Enhanced UI**: Tabbed interface with permission legend and activity sidebar

**🚧 Next Phase (Phase 3):**
- **Database Permissions**: Move permissions from JSON to SQLite with versioning
- **User Management**: Multi-user contexts with role-based access
- **API Authentication**: Secure MCP server access with client keys
- **Audit Logging**: Track permission changes and access attempts

### 1.3. Scope

The MCP KnowledgeExplorer is a sophisticated, local-first Model Context Protocol server designed for:

- **AI Agent Integration**: Seamless connection for AI clients like Claude Code
- **File System Management**: Secure, config-driven permission-controlled file operations
- **Real-time Monitoring**: Web UI for monitoring AI agent activity
- **Development Workflow**: Hot-reload development environment with Docker
- **Security First**: Config-file based permissions with formal precedence rules
- **Future Extensibility**: Architecture ready for search and indexing features

---

## 2. Architectural Vision: The "Unified Hub" Model

The architecture follows a **"Unified Hub"** pattern - a single, persistent FastAPI server acts as the central coordination point for all clients (browser UI and AI agents).

**Key Benefits:**
- **Simplicity**: One server handles all protocols (HTTP, WebSocket, MCP)
- **Real-time**: Instant activity broadcasting to UI clients
- **Security**: Centralized permission checking for all operations
- **Maintainability**: Single point of control and configuration
- **Scalability**: Ready for future multi-client scenarios

This is like a **permanent restaurant** where all customers (browser users and AI agents) come through the same front door and are served by the same staff, ensuring consistent service and monitoring.

---

## 3. System Architecture

### 3.1. High-Level Diagram

```ascii
   User's Local Machine
+--------------------------------------------------------------------+
|                                                                    |
|  ┌──────────┐   Browser    ┌──────────┐                ┌───────────┐ |
|  │   You    ├─────────────>│ Frontend │                │ AI Client │ |
|  └──────────┘              │   UI     │                │ (Claude)  │ |
|                             └─────┬────┘                └─────┬─────┘ |
|                                   │(HTTP)                     │       |
|                                   │                           │(HTTP) |
|                                   │                     MCP   │       |
|  +--------------------------------▼-----------------------▼-------+ |
|  | Docker Environment (docker-compose up)                       | |
|  |                                                              | |
|  |  ┌────────────────────────────────────────────────────────┐  | |
|  |  │       Backend Hub (FastAPI) - Port 8000               │  | |
|  |  │                                                        │  | |
|  |  │  ✅ HTTP REST API        (/api/*)                     │  | |
|  |  │  ✅ WebSocket UI         (/ws/ui)                     │  | |
|  |  │  ✅ WebSocket MCP        (/ws/mcp) - internal only    │  | |
|  |  │  ✅ HTTP MCP Endpoint    (/mcp)                       │  | |
|  |  │  ✅ File System Tools    (read, write, list)          │  | |
|  |  │  ✅ Config Permissions   (JSON rules + Trie cache)    │  | |
|  |  │  ✅ Activity Logging     (real-time broadcast)        │  | |
|  |  │                                                        │  | |
|  |  └───────────────────┬────────────────────────────────────┘  | |
|  |                       │(SQLite)                              | |
|  |  ┌────────────────────▼───────────────────────────────────┐  | |
|  |  │  ┌────────────┐ ┌─────────────┐ ┌──────────────────┐ │  | |
|  |  │  │ SQLite DB  │ │Config Files │ │ Local Files      │ │  | |
|  |  │  │ (Volume)   │ │permissions  │ │ C:\...\MCP Test\ │ │  | |
|  |  │  └────────────┘ └─────────────┘ └──────────────────┘ │  | |
|  |  └──────────────────────────────────────────────────────┘  | |
|  |                                                              | |
|  +--------------------------------------------------------------+ |
|                                                                    |
+--------------------------------------------------------------------+
```

### 3.2. Component Status

#### ✅ Backend Hub (FastAPI) - **FULLY OPERATIONAL**
The core server handling all business logic and client communication.

**Implemented Features:**
- **MCP Protocol Handler**: Complete JSON-RPC 2.0 implementation
  - `initialize` - Server capability negotiation
  - `initialized` - Client confirmation
  - `tools/list` - Dynamic tool discovery
  - `tools/call` - Secure tool execution
- **File System Services**: Production-ready file operations
  - `read_file` - Read file contents with encoding support
  - `list_files` - Directory listing with metadata
  - `write_file` - Safe file writing with directory creation
- **🆕 Config Permission System**: Advanced permission management
  - JSON-based permission rules with precedence logic
  - Trie-based caching for sub-millisecond resolution
  - File watcher for automatic config reload
  - Atomic updates with optimistic locking
- **Security Layer**: Comprehensive protection
  - Path validation preventing directory traversal
  - Config-file based access control with formal precedence
  - Mount point isolation (`/shared-fs` container boundary)
- **Real-time Communication**: WebSocket broadcasting
  - UI activity feed for live monitoring
  - Error and success notifications
  - Client connection management

#### ✅ Frontend UI (React) - **PHASE 2 COMPLETE**
Web interface for server management and monitoring.

**Current State:**
- **✅ Advanced File Explorer**: Tree navigation with permission indicators
- **✅ Permission Editor**: Visual and JSON editor with rule management
- **✅ Real-time Activity Log**: Live MCP operation monitoring
- **✅ Server Configuration**: Dashboard with system status
- **✅ Permission Management**: Full CRUD operations for permission rules
- **✅ Tabbed Interface**: Professional UI with multiple views
- **✅ Tailwind CSS**: Modern styling with responsive design

#### ✅ Containerization (Docker) - **FULLY CONFIGURED**
Production-ready Docker environment with development optimization.

**Features:**
- Hot-reload enabled for both frontend and backend
- Volume mounts for database persistence, config files, and file access
- Environment variable configuration with feature flags
- CORS pre-configured for local development

---

## 4. MCP Protocol Implementation

### 4.1. Protocol Compliance

**✅ Specification**: MCP 2024-11-05
**✅ Transport**: HTTP (for AI clients), WebSocket (internal)
**✅ Format**: JSON-RPC 2.0 compliant

### 4.2. Supported Methods

| Method | Status | Description |
|--------|--------|-------------|
| `initialize` | ✅ | Server capability negotiation and handshake |
| `initialized` | ✅ | Client initialization confirmation |
| `tools/list` | ✅ | Returns available file system tools |
| `tools/call` | ✅ | Executes tools with parameter validation |

### 4.3. Available Tools

| Tool | Parameters | Description |
|------|------------|-------------|
| `read_file` | `path: string` | Read complete file contents |
| `list_files` | `path: string` | List directory contents with metadata |
| `write_file` | `path: string, content: string` | Write content to file |

### 4.4. Error Handling

Complete JSON-RPC 2.0 error responses with custom MCP error codes:

```json
{
  "jsonrpc": "2.0",
  "id": "request-id",
  "error": {
    "code": -32001,
    "message": "Permission Denied",
    "data": "Operation 'read' is not permitted for path: private stuff/secret.txt"
  }
}
```

**Error Codes:**
- `-32700` Parse error (malformed JSON)
- `-32600` Invalid Request (missing required fields)
- `-32601` Method not found (unsupported MCP method)
- `-32602` Invalid params (parameter validation failed)
- `-32603` Internal error (server-side exceptions)
- `-32001` Permission Denied (custom - security violation)
- `-32002` File Not Found (custom - file system error)

---

## 5. Security Model

### 5.1. Config-File Based Permissions ✅

**Principle**: Permission rules defined in formal JSON configuration files with advanced precedence logic.

**Current Working Configuration:**
```json
{
  "$schema": {
    "title": "Permission Configuration Schema",
    "description": "Schema for MCP KnowledgeExplorer permission rules",
    "version": "1.0.0"
  },
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
    "description": "Formal precedence rules for permission resolution",
    "rules": [
      "1. Specificity: A rule on a child path is more specific than a rule on a parent path",
      "2. Tie-Breaker: For rules of equal specificity, deny wins over allow",
      "3. Implied Permissions: A write permission implicitly grants read",
      "4. Default: If no rule matches, access is denied"
    ]
  }
}
```

### 5.2. Path Security ✅

**Protections Implemented:**
- **Directory Traversal Prevention**: `../` sequences blocked
- **Absolute Path Blocking**: Absolute paths rejected
- **Mount Point Isolation**: All operations restricted to `/shared-fs`
- **Path Normalization**: Cross-platform path handling

### 5.3. Performance & Caching ✅

**Advanced Features:**
- **Trie-Based Caching**: In-memory permission resolution with sub-millisecond performance
- **File Watcher**: Automatic config reload when permissions.json changes
- **Atomic Updates**: Safe multi-user editing with optimistic locking using ETags
- **Cache Statistics**: Real-time performance monitoring via `/api/stats`

### 5.4. Docker Security ✅

**Container Isolation:**
- Controlled bind mounts for file system access
- Network isolation with explicit port mapping
- Volume mounts for data persistence outside container lifecycle

---

## 6. Development Workflow

### 6.1. Getting Started

```bash
# Clone and start the project
git clone <repository-url>
cd MCPFileServer
docker-compose up

# The system will be available at:
# Frontend: http://localhost:5173
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### 6.2. Development Features ✅

- **Hot Reload**: Code changes instantly reflected (no rebuild needed)
- **Live Logs**: `docker-compose logs -f` for real-time debugging
- **API Documentation**: Auto-generated FastAPI docs at `/docs`
- **Database Access**: SQLite browser or CLI tools for data inspection

### 6.3. File System Access

The server provides controlled access to your local file system through Docker volume mounts:

```yaml
volumes:
  - ${DATABASE_PATH:-./data}:/data          # SQLite database
  - ${SHARED_FS_PATH:-C:/Users/MartinBielik/MCP Test}:/shared-fs  # File operations
  - ./config:/config                       # Permission configuration
```

**Current Shared Directory Structure:**
```
C:/Users/MartinBielik/MCP Test/
├── materials/          # Read access - course materials and documentation
│   ├── 01_Introduction to Software Engineering/  # BLOCKED by deny rule
│   └── [other course materials]/
├── projects/           # Write access - development projects and code
│   ├── [various project folders]/
│   └── README.md
└── private stuff/      # No access - blocked by default deny
    └── [private files]/
```

**Setup additional directories:**
```bash
# Create test files in the shared directory
echo "Course material example" > "C:/Users/MartinBielik/MCP Test/materials/example.txt"
mkdir -p "C:/Users/MartinBielik/MCP Test/projects/new-project"
echo "Project readme" > "C:/Users/MartinBielik/MCP Test/projects/README.md"
```

---

## 7. Testing MCP Connection

### 7.1. WebSocket Connection Test

```bash
# Test WebSocket MCP endpoint (for debugging/internal use only)
wscat -c ws://localhost:8000/ws/mcp

# Send initialization request
{"jsonrpc": "2.0", "method": "initialize", "params": {"version": "2024-11-05"}, "id": 1}

# List available tools
{"jsonrpc": "2.0", "method": "tools/list", "id": 2}

# Test file read with actual directory structure
{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "read_file", "arguments": {"path": "materials/example.txt"}}, "id": 3}
```

### 7.2. HTTP MCP Endpoint Test (⚠️ USE THIS FOR AI CLIENTS)

> **IMPORTANT**: AI clients like Claude Code must use the HTTP endpoint, NOT WebSocket!

```bash
# Test HTTP MCP endpoint (the one AI clients should use)
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}'

# Test with actual directories
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "list_files", "arguments": {"path": "materials"}}, "id": 2}'

# Test write access to projects directory
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "write_file", "arguments": {"path": "projects/test.txt", "content": "Hello from MCP"}}, "id": 3}'

# Test blocked directory (should be denied)
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "read_file", "arguments": {"path": "materials/01_Introduction to Software Engineering/README.md"}}, "id": 4}'
```

### 7.3. Expected Successful Response

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": [
    {
      "name": "read_file",
      "description": "Reads the entire content of a specified file.",
      "inputSchema": {
        "type": "object",
        "properties": {
          "path": {
            "type": "string",
            "description": "The relative path to the file from the shared directory root."
          }
        },
        "required": ["path"]
      }
    }
  ]
}
```

---

## 8. AI Client Setup Guide

### 8.1. ⚠️ CRITICAL: HTTP vs WebSocket Endpoints

**IMPORTANT:** AI clients (like Claude Code) should connect to the **HTTP endpoint**, not the WebSocket endpoint.

```
✅ CORRECT for AI clients:   http://127.0.0.1:8000/mcp
❌ WRONG for AI clients:     ws://127.0.0.1:8000/ws/mcp
```

**Why this matters:**
- The WebSocket endpoint (`/ws/mcp`) is for direct protocol testing and development
- AI clients like Claude Code expect HTTP-based MCP servers by default
- Using the wrong endpoint will result in connection failures

### 8.2. Claude Code Configuration

#### Setting up Claude Code MCP Connection

**Step 1: Locate your Claude Code configuration**
- Global config: `%USERPROFILE%\.claude\settings.json`
- Local config: `.claude\settings.json` (in your project)

**Step 2: Add MCP server configuration**

Add this configuration to your `.claude\settings.json`:

```json
{
  "mcpServers": {
    "my-local-server": {
      "type": "http",
      "url": "http://127.0.0.1:8000/mcp",
      "description": "Local MCP KnowledgeExplorer server for file operations"
    }
  }
}
```

**Step 3: Restart Claude Code**
After adding the configuration, restart Claude Code for the changes to take effect.

#### PowerShell Commands for MCP Management

```powershell
# Add MCP server to Claude Code (Global scope)
claude mcp add my-local-server http://127.0.0.1:8000/mcp --global

# Add MCP server to current project (Local scope)
claude mcp add my-local-server http://127.0.0.1:8000/mcp --local

# List configured MCP servers
claude mcp list

# Remove MCP server
claude mcp remove my-local-server

# Test MCP server connection
claude mcp test my-local-server
```

### 8.3. Configuration Verification

#### Check if your MCP server is recognized:

1. **In Claude Code interface:**
   - Look for the MCP server indicator in the status bar
   - Check the "Available Tools" section for file system tools

2. **Test connection manually:**
   ```powershell
   # Test HTTP endpoint directly
   curl -X POST http://127.0.0.1:8000/mcp -H "Content-Type: application/json" -d '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}'
   ```

3. **Check server logs:**
   ```bash
   docker-compose logs -f backend
   ```

### 8.4. Troubleshooting Common Issues

#### Problem: "Connection Failed" or "Server Not Found"

**Solutions:**
1. **Verify server is running:**
   ```bash
   docker-compose ps
   # Should show both backend and frontend containers running
   ```

2. **Check correct endpoint:**
   - ✅ Use: `http://127.0.0.1:8000/mcp`
   - ❌ Not: `ws://127.0.0.1:8000/ws/mcp`
   - ❌ Not: `http://localhost:8000/mcp` (some AI clients prefer 127.0.0.1)

3. **Test basic connectivity:**
   ```bash
   curl http://127.0.0.1:8000/
   # Should return: {"message": "MCP KnowledgeExplorer Server"}
   ```

#### Problem: "Tools Not Available" or Empty Tool List

**Solutions:**
1. **Check server logs for errors:**
   ```bash
   docker-compose logs backend | grep ERROR
   ```

2. **Verify shared filesystem exists:**
   ```bash
   # Check if the actual shared directory exists
   ls -la "C:/Users/MartinBielik/MCP Test/"
   # Should show: materials, projects, private stuff directories
   ```

3. **Test tool list manually:**
   ```bash
   curl -X POST http://127.0.0.1:8000/mcp \
     -H "Content-Type: application/json" \
     -d '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}'
   ```

#### Problem: "Permission Denied" Errors

**Solutions:**
1. **Check file path format:**
   - ✅ Use relative paths: `materials/example.txt`, `projects/folder/file.txt`
   - ❌ Not absolute paths: `/home/user/materials/example.txt`

2. **Verify permission configuration:**
   Check current config via web UI at `http://localhost:5173` or API:
   ```bash
   curl http://127.0.0.1:8000/api/config/permissions
   ```

3. **Test with allowed directories:**
   ```bash
   # These should work based on current config
   # Read access to materials
   curl -X POST http://127.0.0.1:8000/mcp \
     -H "Content-Type: application/json" \
     -d '{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "list_files", "arguments": {"path": "materials"}}, "id": 1}'

   # Write access to projects
   curl -X POST http://127.0.0.1:8000/mcp \
     -H "Content-Type: application/json" \
     -d '{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "write_file", "arguments": {"path": "projects/test.txt", "content": "test"}}, "id": 2}'

   # This should be denied (private stuff directory)
   curl -X POST http://127.0.0.1:8000/mcp \
     -H "Content-Type: application/json" \
     -d '{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "read_file", "arguments": {"path": "private stuff/secret.txt"}}, "id": 3}'

   # This should be denied (blocked by specific deny rule)
   curl -X POST http://127.0.0.1:8000/mcp \
     -H "Content-Type: application/json" \
     -d '{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "read_file", "arguments": {"path": "materials/01_Introduction to Software Engineering/README.md"}}, "id": 4}'
   ```

### 8.5. Permission Management via Web UI

#### Access the Permission Editor

1. **Open Web UI:** Navigate to `http://localhost:5173`
2. **Permission Editor Tab:** Click on the "Permission Editor" tab
3. **View Current Rules:** See all permission rules with IDs and descriptions
4. **Edit Permissions:**
   - Use Visual Editor for point-and-click rule management
   - Use JSON Editor for advanced configuration
   - Changes are saved atomically with optimistic locking

#### Understanding Permission Rules

The system uses formal precedence logic:

1. **Specificity**: Child paths override parent paths
   - Rule for `materials/private/` overrides rule for `materials/`
2. **Deny Wins**: For equal specificity, deny overrides allow
3. **Write Implies Read**: Write permission automatically grants read access
4. **Default Deny**: If no rules match, access is denied

### 8.6. Local vs Global Configuration

#### Global Configuration
- **Location:** `%USERPROFILE%\.claude\settings.json`
- **Scope:** Available to all Claude Code projects
- **Use case:** Personal development setup

#### Local Configuration
- **Location:** `.claude\settings.json` (in project root)
- **Scope:** Only for current project
- **Use case:** Project-specific MCP servers, team sharing

**Best Practice:** Start with local configuration for testing, then move to global for regular use.

---

## 9. Technology Stack

| Category | Technology | Purpose | Status |
|----------|------------|---------|---------|
| **Containerization** | Docker Compose | Reproducible development environment | ✅ |
| **Backend** | Python 3.11, FastAPI | Async API server and MCP protocol | ✅ |
| **Database** | SQLite, SQLAlchemy | Local data persistence | ✅ |
| **Frontend** | React 18, TypeScript, Vite | Web UI for management | ✅ |
| **Styling** | Tailwind CSS | Utility-first styling | ✅ |
| **State Management** | React Context | Frontend global state | ✅ |
| **Real-time** | WebSockets | Live activity monitoring | ✅ |
| **Protocol** | JSON-RPC 2.0, MCP | AI agent communication | ✅ |
| **Permissions** | JSON Config + Trie Cache | High-performance security | ✅ |
| **File Watching** | Watchdog | Automatic config reload | ✅ |

---

## 10. Project Structure

```
MCPFileServer/
├── 📁 backend/                  # Python FastAPI backend
│   ├── 📁 app/
│   │   ├── 📄 main.py          # ✅ FastAPI app with MCP endpoints
│   │   ├── 📄 config.py        # ✅ Feature flags and configuration
│   │   ├── 📁 services/         # ✅ Business logic services
│   │   │   ├── file_service.py  # ✅ File system operations
│   │   │   ├── mcp_service.py   # ✅ MCP tool definitions
│   │   │   ├── permission_service.py # ✅ Legacy permission service
│   │   │   └── config_permission_service.py # ✅ Config-file permissions
│   │   ├── 📁 utils/           # ✅ Utility modules
│   │   │   └── trie.py         # ✅ Trie-based permission caching
│   │   ├── 📁 schemas/          # ✅ Pydantic data models
│   │   │   └── mcp.py          # ✅ JSON-RPC and MCP schemas
│   │   └── 📁 api/             # ✅ REST API endpoints
│   ├── 📁 tests/               # ✅ Test suite
│   └── 📄 requirements.txt      # Python dependencies
├── 📁 frontend/                 # React TypeScript frontend
│   ├── 📁 src/
│   │   ├── 📄 App.tsx          # ✅ Enhanced main component
│   │   ├── 📁 components/      # ✅ React components
│   │   │   ├── FileExplorer.tsx # ✅ File browser with permissions
│   │   │   ├── PermissionIndicator.tsx # ✅ Permission status display
│   │   │   └── PermissionEditor.tsx # ✅ Visual/JSON rule editor
│   │   └── 📄 main.tsx         # React entry point
│   └── 📄 package.json         # Node.js dependencies
├── 📁 config/                  # ✅ Global configuration
│   └── 📄 permissions.json     # ✅ Formal permission rules
├── 📁 data/                     # SQLite database (gitignored)
├── 📄 docker-compose.yml       # ✅ Multi-container setup
├── 📄 .env                     # Environment with feature flags
├── 📄 README.md                # This file
├── 📄 CLAUDE.md                # AI context documentation
├── 📄 changelog.md             # ✅ Version history
└── 📄 plan.md                  # Development roadmap
```

**Legend**: ✅ Complete | 🚧 In Progress | 📋 Planned

---

## 11. Configuration

### 11.1. Environment Variables

```bash
# .env file configuration
BACKEND_PORT=8000                        # FastAPI server port
FRONTEND_PORT=5173                       # Vite development server
DATABASE_PATH=./data                     # SQLite database directory
SHARED_FS_PATH=C:/Users/MartinBielik/MCP Test  # Actual shared filesystem

# Phase 2 Feature Flags
ENABLE_CONFIG_FILE_PERMISSIONS=true     # Enable config-file permissions
ENABLE_DATABASE_PERMISSIONS=false       # Future Phase 3 feature

# Performance Settings
PERMISSION_CACHE_TTL=300                 # Cache TTL in seconds
PERMISSION_CACHE_MAX_SIZE=10000          # Max cache entries
DEBUG_PERMISSION_CACHE=false             # Debug cache performance
ENABLE_PERFORMANCE_METRICS=true          # Performance monitoring
```

### 11.2. Permission Configuration

Now managed through `config/permissions.json` with formal schema:

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
  ]
}
```

**Management Options:**
- **Web UI**: Visual editor at `http://localhost:5173`
- **JSON Editor**: Direct JSON editing with validation
- **API**: RESTful endpoints for programmatic management

---

## 12. Monitoring and Debugging

### 12.1. Real-time Activity Monitoring ✅

The web UI at `http://localhost:5173` displays live MCP activity:
- Tool calls and results with timestamps
- Permission checks and violations with rule details
- Error messages and stack traces
- Client connections and disconnections
- Performance metrics and cache statistics

### 12.2. Log Access

```bash
# View all container logs
docker-compose logs

# Follow backend logs in real-time
docker-compose logs -f backend

# View specific service logs
docker-compose logs frontend

# Filter for permission-related logs
docker-compose logs backend | grep -i permission
```

### 12.3. Database Inspection

```bash
# Access SQLite database directly
sqlite3 data/database.db

# List tables
.tables

# View settings
SELECT * FROM settings;
```

### 12.4. Permission System Debugging

```bash
# Check current permission config
curl http://localhost:8000/api/config/permissions

# Get permission statistics
curl http://localhost:8000/api/stats

# Test specific path permission
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "read_file", "arguments": {"path": "test/path.txt"}}, "id": 1}'
```

---

## 13. Roadmap

### ✅ Phase 2: Config-File Permission System (COMPLETE)
- [x] JSON-based permission configuration
- [x] Formal precedence logic implementation
- [x] Trie-based caching for performance
- [x] Permission Editor UI (visual + JSON)
- [x] File watcher for automatic reload
- [x] Atomic config updates with optimistic locking
- [x] Feature flag system for safe deployment
- [x] Bug fixes: Permission persistence, frontend integration, rule ID display
- [x] Full integration testing with real filesystem

### 🚧 Phase 3: Database-Driven Permissions (IN PREPARATION)
- [ ] SQLite schema for permission storage
- [ ] User management and role-based access
- [ ] API key authentication for MCP clients
- [ ] Audit logging for compliance
- [ ] Permission versioning and rollback

### 📋 Phase 4: Advanced Features (PLANNED)
- [ ] File system search capabilities (keyword + semantic)
- [ ] Multi-client support and session management
- [ ] Rate limiting and abuse prevention
- [ ] Export/import configuration
- [ ] Performance monitoring dashboard

### 📋 Phase 5: Production Readiness (FUTURE)
- [ ] Authentication and authorization system
- [ ] Backup and disaster recovery
- [ ] Deployment guides and production Docker images
- [ ] Comprehensive test suite with CI/CD
- [ ] Security audit and penetration testing

---

## 14. Contributing

### 14.1. Development Setup

```bash
# Install development dependencies
docker-compose exec backend pip install -r requirements-dev.txt
docker-compose exec frontend npm install

# Run tests
docker-compose exec backend python -m pytest backend/tests/ -v
docker-compose exec frontend npm test

# Code formatting
docker-compose exec backend black app/
docker-compose exec frontend npm run format
```

### 14.2. Code Quality Standards

- **Python**: PEP 8, type hints, comprehensive docstrings
- **TypeScript**: Strict mode, explicit types, JSDoc comments
- **Testing**: Minimum 80% code coverage for new features
- **Documentation**: Update README.md, CLAUDE.md and changelog.md with changes

---

## 15. Support and Documentation

### 15.1. Additional Documentation

- **[CLAUDE.md](./CLAUDE.md)** - Comprehensive project context for AI development
- **[changelog.md](./changelog.md)** - Detailed version history and changes
- **[plan.md](./plan.md)** - Development roadmap and task breakdown
- **[context-strategy.md](./context-strategy.md)** - Documentation strategy

### 15.2. API Documentation

- **Interactive API Docs**: http://localhost:8000/docs (when running)
- **OpenAPI Schema**: http://localhost:8000/openapi.json
- **WebSocket Test Interface**: Built-in FastAPI WebSocket testing

### 15.3. Troubleshooting

#### Common Issues and Solutions

**"File Not Found" Errors:**
- Check that your `SHARED_FS_PATH` in `.env` points to the correct directory
- Verify the directory structure matches what's configured in `config/permissions.json`
- Use `docker-compose logs backend` to see detailed error messages

**Permission Denied Errors:**
- Check `config/permissions.json` for the specific path rules
- Remember: deny rules override allow rules (specificity matters)
- Use the Settings UI at http://localhost:5173 to view and edit permissions

**MCP Connection Issues:**
- Ensure backend is running: `docker-compose ps`
- Test HTTP endpoint: `curl http://localhost:8000/api/config`
- Check MCP connection: `claude mcp list` (should show wisdom server)

**Directory Structure Verification:**
```bash
# Check what's actually mounted in the container
docker-compose exec backend ls -la /shared-fs/

# Verify your local directory
ls -la "C:/Users/MartinBielik/MCP Test/"  # or your SHARED_FS_PATH

# Check permission configuration
docker-compose exec backend cat /config/permissions.json
```

### 15.4. Getting Help

- **Issues**: Check existing issues and create new ones for bugs/features
- **Discussions**: Use GitHub Discussions for questions and ideas
- **Documentation**: All architectural details in CLAUDE.md
- **Logs**: Use `docker-compose logs -f` for debugging
- **Permission Issues**: Check web UI at http://localhost:5173

---

**🚀 The MCP KnowledgeExplorer Phase 2 is complete and ready for AI agent integration!**

Connect your AI clients to `http://127.0.0.1:8000/mcp` and start exploring your file system safely with sophisticated permission management. Use the web UI at `http://localhost:5173` to configure permissions and monitor activity in real-time.

**Current Working Setup:**
- **Shared Filesystem**: `C:/Users/MartinBielik/MCP Test/`
- **Available Directories**: `materials/` (read), `projects/` (write), `private stuff/` (blocked)
- **Permission Configuration**: Config-file driven with rule IDs and atomic updates
- **Real-time Monitoring**: Live MCP activity feed with performance metrics
- **Tested and Verified**: All Phase 2 functionality working with real filesystem access