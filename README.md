# MCP KnowledgeExplorer

> **🎉 Status: MCP Protocol Successfully Implemented!**  
> The core MCP server is fully operational with complete JSON-RPC 2.0 support, file system tools, and security controls. AI agents can now connect and perform file operations safely.

## Quick Start

```bash
# Start the entire system with one command
docker-compose up

# Access the services
# Frontend UI: http://localhost:5173
# Backend API: http://localhost:8000  
# MCP WebSocket: ws://localhost:8000/ws/mcp
# MCP HTTP: http://localhost:8000/mcp
```

---

## 1. Introduction

### 1.1. Purpose

This project is a **production-ready Model Context Protocol (MCP) server** that enables AI agents to safely interact with your local file system. It provides both WebSocket and HTTP endpoints for maximum compatibility, along with a web-based management interface for real-time monitoring and permission control.

### 1.2. Current Status - ✅ Core Implementation Complete

**✅ Fully Implemented:**
- **MCP Protocol**: Complete JSON-RPC 2.0 implementation with MCP 2024-11-05 specification
- **File System Tools**: `read_file`, `list_files`, `write_file` with integrated security
- **Permission System**: Allowlist-based security preventing unauthorized file access  
- **Real-time Monitoring**: Live activity feed via WebSocket to UI
- **Error Handling**: Comprehensive JSON-RPC compliant error responses
- **Dual Endpoints**: Both WebSocket (`/ws/mcp`) and HTTP (`/mcp`) for client flexibility

**🚧 In Development:**
- **Frontend UI**: File explorer and permission management interface
- **Enhanced Logging**: Structured activity logs with filtering and export
- **Configuration Management**: UI-based server configuration

### 1.3. Scope

The MCP KnowledgeExplorer is a sophisticated, local-first Model Context Protocol server designed for:

- **AI Agent Integration**: Seamless connection for AI clients like Claude Code
- **File System Management**: Secure, permission-controlled file operations  
- **Real-time Monitoring**: Web UI for monitoring AI agent activity
- **Development Workflow**: Hot-reload development environment with Docker
- **Security First**: Allowlist-based permissions with path validation
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
|  ┌──────────┐   Browser    ┌──────────┐      MCP      ┌───────────┐ |
|  │   You    ├─────────────>│ Frontend │   (WebSocket) │ AI Client │ |
|  └──────────┘              │   UI     │<──────────────┤ (Claude)  │ |
|                             └─────┬────┘               └─────┬─────┘ |
|                                   │(HTTP)                    │       |
|  +--------------------------------▼----------------------▼-------+ |
|  | Docker Environment (docker-compose up)                       | |
|  |                                                              | |
|  |  ┌────────────────────────────────────────────────────────┐  | |
|  |  │       Backend Hub (FastAPI) - Port 8000               │  | |
|  |  │                                                        │  | |
|  |  │  ✅ HTTP REST API        (/api/*)                     │  | |
|  |  │  ✅ WebSocket UI         (/ws/ui)                     │  | |
|  |  │  ✅ WebSocket MCP        (/ws/mcp)                    │  | |
|  |  │  ✅ HTTP MCP Endpoint    (/mcp)                       │  | |
|  |  │  ✅ File System Tools    (read, write, list)          │  | |
|  |  │  ✅ Permission System    (allowlist security)         │  | |
|  |  │  ✅ Activity Logging     (real-time broadcast)        │  | |
|  |  │                                                        │  | |
|  |  └───────────────────┬────────────────────────────────────┘  | |
|  |                       │(SQLite)                              | |
|  |  ┌────────────────────▼───────────────────────────────────┐  | |
|  |  │    ┌────────────┐               ┌────────────┐       │  | |
|  |  │    │ SQLite DB  │               │ Local Files│       │  | |
|  |  │    │ (Volume)   │               │ (Volume)   │       │  | |
|  |  │    └────────────┘               └────────────┘       │  | |
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
- **Security Layer**: Comprehensive permission system
  - Path validation preventing directory traversal
  - Allowlist-based access control
  - Mount point isolation (`/shared-fs` container boundary)
- **Real-time Communication**: WebSocket broadcasting
  - UI activity feed for live monitoring
  - Error and success notifications
  - Client connection management

#### 🚧 Frontend UI (React) - **BASIC IMPLEMENTATION**
Web interface for server management and monitoring.

**Current State:**
- Basic React app with WebSocket connection
- Real-time activity log display
- Server configuration display
- Tailwind CSS styling foundation

**Planned Features:**
- File Explorer with breadcrumb navigation
- Permission Management interface
- Enhanced Activity Log with filtering
- Configuration Dashboard

#### ✅ Containerization (Docker) - **FULLY CONFIGURED**
Production-ready Docker environment with development optimization.

**Features:**
- Hot-reload enabled for both frontend and backend
- Volume mounts for database persistence and file access
- Environment variable configuration
- CORS pre-configured for local development

---

## 4. MCP Protocol Implementation

### 4.1. Protocol Compliance

**✅ Specification**: MCP 2024-11-05  
**✅ Transport**: WebSocket + HTTP support  
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
    "data": "Operation 'read' is not permitted for path: restricted/file.txt"
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

### 5.1. Allowlist-Based Permissions ✅

**Principle**: Only explicitly permitted directories are accessible to AI agents.

**Current Configuration:**
```python
PERMISSIONS = {
    "context": ["docs", "projects"],    # Read-only access
    "working": ["projects", "output"],  # Read-write access
}
```

### 5.2. Path Security ✅

**Protections Implemented:**
- **Directory Traversal Prevention**: `../` sequences blocked
- **Absolute Path Blocking**: Absolute paths rejected  
- **Mount Point Isolation**: All operations restricted to `/shared-fs`
- **Path Normalization**: Cross-platform path handling

### 5.3. Docker Security ✅

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
  - ${SHARED_FS_PATH:-./shared-fs}:/shared-fs  # File operations
```

**Setup your shared directory:**
```bash
mkdir -p shared-fs/docs shared-fs/projects shared-fs/output
echo "Sample document" > shared-fs/docs/sample.txt
```

---

## 7. Testing MCP Connection

### 7.1. WebSocket Connection Test

```bash
# Test WebSocket MCP endpoint
wscat -c ws://localhost:8000/ws/mcp

# Send initialization request
{"jsonrpc": "2.0", "method": "initialize", "params": {"version": "2024-11-05"}, "id": 1}

# List available tools  
{"jsonrpc": "2.0", "method": "tools/list", "id": 2}

# Test file read
{"jsonrpc": "2.0", "method": "tools/call", "params": {"toolName": "read_file", "arguments": {"path": "docs/sample.txt"}}, "id": 3}
```

### 7.2. HTTP MCP Endpoint Test

```bash
# Test HTTP MCP endpoint
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}'
```

### 7.3. Expected Successful Response

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": [
    {
      "toolName": "read_file",
      "description": "Reads the entire content of a specified file.",
      "parameters": [
        {
          "name": "path",
          "type": "string", 
          "description": "The relative path to the file from the shared directory root.",
          "required": true
        }
      ]
    }
  ]
}
```

---

## 8. Technology Stack

| Category | Technology | Purpose | Status |
|----------|------------|---------|---------|
| **Containerization** | Docker Compose | Reproducible development environment | ✅ |
| **Backend** | Python 3.11, FastAPI | Async API server and MCP protocol | ✅ |
| **Database** | SQLite, SQLAlchemy | Local data persistence | ✅ |
| **Frontend** | React 18, TypeScript, Vite | Web UI for management | 🚧 |
| **Styling** | Tailwind CSS | Utility-first styling | ✅ |
| **State Management** | Zustand | Frontend global state | ✅ |
| **Real-time** | WebSockets | Live activity monitoring | ✅ |
| **Protocol** | JSON-RPC 2.0, MCP | AI agent communication | ✅ |

---

## 9. Project Structure

```
MCPFileServer/
├── 📁 backend/                  # Python FastAPI backend
│   ├── 📁 app/
│   │   ├── 📄 main.py          # ✅ FastAPI app with MCP endpoints
│   │   ├── 📁 services/         # ✅ Business logic services
│   │   │   ├── file_service.py  # ✅ File system operations
│   │   │   ├── mcp_service.py   # ✅ MCP tool definitions  
│   │   │   └── permission_service.py # ✅ Security layer
│   │   ├── 📁 schemas/          # ✅ Pydantic data models
│   │   │   └── mcp.py          # ✅ JSON-RPC and MCP schemas
│   │   └── 📁 api/             # ✅ REST API endpoints
│   └── 📄 requirements.txt      # Python dependencies
├── 📁 frontend/                 # React TypeScript frontend  
│   ├── 📁 src/
│   │   ├── 📄 App.tsx          # 🚧 Main React component
│   │   └── 📄 main.tsx         # React entry point
│   └── 📄 package.json         # Node.js dependencies
├── 📁 data/                     # SQLite database (gitignored)
├── 📁 shared-fs/               # File system for AI operations
├── 📄 docker-compose.yml       # ✅ Multi-container setup
├── 📄 .env                     # Environment configuration
├── 📄 README.md                # This file
├── 📄 CLAUDE.md                # AI context documentation
├── 📄 changelog.md             # ✅ Version history
└── 📄 plan.md                  # Development roadmap
```

**Legend**: ✅ Complete | 🚧 In Progress | 📋 Planned

---

## 10. Configuration

### 10.1. Environment Variables

```bash
# .env file configuration
BACKEND_PORT=8000           # FastAPI server port
FRONTEND_PORT=5173          # Vite development server
DATABASE_PATH=./data        # SQLite database directory
SHARED_FS_PATH=./shared-fs  # File system mount point
```

### 10.2. Permission Configuration

Currently hardcoded in `backend/app/services/permission_service.py`:

```python
PERMISSIONS = {
    "context": ["docs", "projects"],    # Read-only directories
    "working": ["projects", "output"],  # Read-write directories  
}
```

**Future**: Database-driven permissions with UI management

---

## 11. Monitoring and Debugging

### 11.1. Real-time Activity Monitoring ✅

The web UI at `http://localhost:5173` displays live MCP activity:
- Tool calls and results
- Permission checks and violations  
- Error messages and stack traces
- Client connections and disconnections

### 11.2. Log Access

```bash
# View all container logs
docker-compose logs

# Follow backend logs in real-time
docker-compose logs -f backend

# View specific service logs
docker-compose logs frontend
```

### 11.3. Database Inspection

```bash
# Access SQLite database directly
sqlite3 data/database.db

# List tables
.tables

# View settings
SELECT * FROM settings;
```

---

## 12. Roadmap

### ✅ Phase 1: Core MCP Implementation (COMPLETE)
- [x] MCP JSON-RPC 2.0 protocol
- [x] File system tools with security
- [x] Permission management system
- [x] Real-time activity logging
- [x] Comprehensive error handling

### 🚧 Phase 2: Frontend Development (IN PROGRESS)
- [ ] File Explorer component with tree view
- [ ] Permission Management UI
- [ ] Enhanced Activity Log with filtering
- [ ] Configuration Dashboard
- [ ] Responsive design and accessibility

### 📋 Phase 3: Advanced Features (PLANNED)  
- [ ] Database-driven permissions management
- [ ] Multi-client support and session management
- [ ] File system search capabilities
- [ ] Export/import configuration
- [ ] Performance monitoring and metrics

### 📋 Phase 4: Production Readiness (FUTURE)
- [ ] Authentication and API keys
- [ ] Rate limiting and abuse prevention  
- [ ] Backup and disaster recovery
- [ ] Deployment guides and Docker production images
- [ ] Comprehensive test suite

---

## 13. Contributing

### 13.1. Development Setup

```bash
# Install development dependencies
docker-compose exec backend pip install -r requirements-dev.txt
docker-compose exec frontend npm install

# Run tests
docker-compose exec backend python -m pytest
docker-compose exec frontend npm test

# Code formatting
docker-compose exec backend black app/
docker-compose exec frontend npm run format
```

### 13.2. Code Quality Standards

- **Python**: PEP 8, type hints, comprehensive docstrings
- **TypeScript**: Strict mode, explicit types, JSDoc comments  
- **Testing**: Minimum 80% code coverage for new features
- **Documentation**: Update CLAUDE.md and changelog.md with changes

---

## 14. Support and Documentation

### 14.1. Additional Documentation

- **[CLAUDE.md](./CLAUDE.md)** - Comprehensive project context for AI development
- **[changelog.md](./changelog.md)** - Detailed version history and changes
- **[plan.md](./plan.md)** - Development roadmap and task breakdown
- **[context-strategy.md](./context-strategy.md)** - Documentation strategy

### 14.2. API Documentation

- **Interactive API Docs**: http://localhost:8000/docs (when running)
- **OpenAPI Schema**: http://localhost:8000/openapi.json
- **WebSocket Test Interface**: Built-in FastAPI WebSocket testing

### 14.3. Getting Help

- **Issues**: Check existing issues and create new ones for bugs/features
- **Discussions**: Use GitHub Discussions for questions and ideas  
- **Documentation**: All architectural details in CLAUDE.md
- **Logs**: Use `docker-compose logs -f` for debugging

---

**🚀 The MCP KnowledgeExplorer is ready for AI agent integration!**

Connect your AI clients to `ws://localhost:8000/ws/mcp` or `http://localhost:8000/mcp` and start exploring your file system safely and efficiently.