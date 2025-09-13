# Changelog - MCP KnowledgeExplorer

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.0.0] - 2025-09-13 - Phase 1: Dynamic Workspace Foundation

### 🎉 Major Features Added
- **🗂️ Advanced File Explorer UI**
  - Tree navigation with expandable folders
  - Breadcrumb navigation with clickable path segments
  - Professional pagination system with page numbers and item counts
  - Smooth folder navigation and responsive design

- **🎨 Visual Permission System**
  - Color-coded permission indicators (Read-Only: Blue, Read-Write: Green, No Access: Gray)
  - Real-time permission status display for all files and folders
  - Interactive permission legend with explanations
  - Tooltip descriptions for each permission level

- **🔐 Secure Browse API**
  - New `/api/browse` endpoint with comprehensive security hardening
  - Directory traversal prevention and path validation
  - Pagination support (configurable page sizes)
  - File metadata with size and modification timestamps

- **📊 Enhanced User Interface**
  - Tabbed interface with File Explorer and Server Status views
  - Permission legend sidebar with recent activity feed
  - Responsive layout optimized for different screen sizes
  - Real-time connection status indicators

### 🛡️ Security Enhancements
- **Path Security**: Comprehensive directory traversal prevention in `/api/browse`
- **Input Validation**: Proper normalization and validation of all path parameters
- **Error Handling**: Secure error responses that don't expose file system details

### 🚀 Performance Improvements
- **Smart Pagination**: Efficient handling of large directories
- **Optimized File Listing**: Fast directory browsing with metadata caching
- **Responsive UI**: Smooth interactions with loading states and error handling

### 🔧 API Additions
- `GET /api/browse` - Secure file system browsing with pagination
- `GET /api/current-permissions` - Permission status for UI visualization

### 🎨 UI/UX Improvements
- Modern dark theme with cyan accent colors
- Professional file and folder icons
- Intuitive navigation with visual feedback
- Clear permission status communication

### 📚 Documentation Updates
- Updated CLAUDE.md with Phase 1 implementation details
- Enhanced plan.md with completed milestones
- Updated feature-dynamic-workspaces.md with Phase 1 completion status

### Previous Changes

### Added
- **📚 Comprehensive AI Client Setup Documentation** (`README.md` Section 8)
  - Complete Claude Code MCP configuration guide
  - Step-by-step .claude.json setup instructions
  - PowerShell commands for MCP server management
  - **⚠️ CRITICAL HTTP vs WebSocket endpoint clarification** to prevent connection failures
  - Detailed troubleshooting guide for common connection issues
  - Local vs Global configuration scope explanation
  - Configuration verification steps and debugging commands

### Changed
- **🔄 Enhanced Documentation Structure** (`README.md`)
  - Repositioned and expanded AI client setup instructions
  - Added prominent warnings about HTTP vs WebSocket endpoint confusion
  - Improved quick start section with endpoint clarity
  - Enhanced troubleshooting section with specific error scenarios

### Documentation Improvements
- **🎯 Addressed Critical Client Setup Gap**: Previously missing AI client connection instructions
- **🚨 Fixed HTTP/WebSocket Confusion**: Clear warnings preventing common connection failures
- **🛠️ Added Practical Commands**: PowerShell and curl examples for client management
- **🔍 Enhanced Debugging Support**: Comprehensive troubleshooting for connection issues

## [1.0.0] - 2025-01-12

### 🎉 MAJOR MILESTONE: Full MCP Protocol Implementation Complete

This release marks the successful completion of the core MCP (Model Context Protocol) server implementation, enabling AI agents to successfully connect and perform file operations with proper security controls.

### Added
- **🚀 Complete MCP JSON-RPC 2.0 Protocol Support** (`backend/app/main.py`)
  - Full MCP initialization handshake with protocol version 2024-11-05
  - JSON-RPC 2.0 compliant request/response handling
  - Support for both WebSocket and HTTP MCP endpoints
  - Comprehensive error handling with proper error codes
  - Real-time activity broadcasting to UI clients

- **📁 Core File System Tools** (`backend/app/services/file_service.py`)
  - `read_file` - Read file contents with permission validation
  - `list_files` - Directory listing with file/folder metadata
  - `write_file` - File writing with automatic directory creation
  - All operations integrate with permission checking system

- **🔐 Permission Management System** (`backend/app/services/permission_service.py`)
  - Allowlist-based security model preventing directory traversal
  - Permission levels: Context (read-only), Working (read-write)
  - Path normalization and validation against `/shared-fs` mount
  - Centralized security checks for all file operations

- **📋 MCP Tools Service** (`backend/app/services/mcp_service.py`)
  - Dynamic tool discovery for `tools/list` endpoint
  - Structured tool definitions with parameter schemas
  - Integration with file system tools

- **📐 MCP Schema Definitions** (`backend/app/schemas/mcp.py`)
  - Pydantic models for JSON-RPC 2.0 protocol
  - MCP-specific schemas (ToolDefinition, ToolResult, etc.)
  - Type-safe request/response handling
  - Built-in error response factories

- **📊 Enhanced Activity Logging**
  - Real-time WebSocket broadcasting of MCP operations
  - Detailed operation logging with success/failure states
  - UI integration for live monitoring

### Changed
- **🔄 Backend Architecture Overhaul** (`backend/app/main.py`)
  - Replaced echo WebSocket handlers with full MCP protocol implementation
  - Added HTTP MCP endpoint (`/mcp`) for better client compatibility
  - Implemented dual-protocol support (WebSocket + HTTP)
  - Enhanced error handling with JSON-RPC compliant error responses

- **📈 Development Status Updated** (`plan.md`)
  - Marked MCP Protocol Implementation as ✅ COMPLETE
  - Marked Core File System Tools as ✅ COMPLETE  
  - Marked Permission Management System as ✅ COMPLETE
  - Updated project status to "Frontend Component Development" phase

### Technical Details

#### MCP Protocol Compliance
- **Protocol Version**: 2024-11-05
- **Supported Methods**: 
  - `initialize` - Server capability negotiation
  - `initialized` - Client initialization confirmation
  - `tools/list` - Available tools discovery
  - `tools/call` - Tool execution with parameters
- **Error Codes**:
  - `-32700` Parse error
  - `-32600` Invalid Request  
  - `-32601` Method not found
  - `-32602` Invalid params
  - `-32603` Internal error
  - `-32001` Permission Denied (custom)
  - `-32002` File Not Found (custom)

#### Security Implementation
- **Path Validation**: Prevents `../` directory traversal attacks
- **Mount Point Security**: All operations restricted to `/shared-fs` container mount
- **Permission Checking**: Every file operation validates against allowlist
- **Error Isolation**: Security errors don't expose file system structure

#### File Operations
- **Encoding**: UTF-8 support for all text files
- **Path Normalization**: Cross-platform path handling
- **Directory Creation**: Automatic parent directory creation for write operations
- **Error Handling**: Proper FileNotFoundError and PermissionError responses

### Performance Improvements
- **Async Operations**: All file I/O operations are properly async
- **Connection Management**: Efficient WebSocket connection pooling
- **Error Response Caching**: Reusable error response objects

### Developer Experience
- **Type Safety**: Full TypeScript-style type hints in Python
- **Documentation**: Comprehensive inline documentation
- **Error Messages**: Clear, actionable error messages for debugging
- **Logging**: Detailed operation logging for troubleshooting

### 🧪 Successful Testing Confirmed
- **MCP Connection**: AI agents can successfully connect via WebSocket
- **Tool Discovery**: `tools/list` returns complete tool definitions
- **File Operations**: All core file operations working with permission checks
- **Error Handling**: Proper error responses for invalid operations
- **Real-time Updates**: UI receives live activity feed from MCP operations

### Breaking Changes
- ⚠️ **MCP WebSocket endpoint** now requires JSON-RPC 2.0 format (previously echo)
- ⚠️ **File operations** now require permission validation (security enhancement)

### Migration Guide
For existing clients:
1. Update MCP WebSocket clients to use JSON-RPC 2.0 format
2. Ensure file paths are relative to shared filesystem root
3. Handle new custom error codes (-32001, -32002)

### Next Phase: Frontend Development
The core MCP server is now fully functional. The next development phase focuses on:
- File Explorer UI component
- Permission management interface  
- Enhanced activity log with filtering
- Configuration dashboard

---

## [0.2.0] - 2025-01-11

### Added
- **Context Strategy Documentation** (`context-strategy.md`)
  - Comprehensive documentation strategy for maintainable development
  - Context file hierarchy and templates
  - Guidelines for documentation maintenance

- **Project Context Files**
  - Root level: `CLAUDE.md` - Complete project overview
  - Backend: `backend/app/CLAUDE.md` - Backend module context
  - Frontend: `frontend/src/CLAUDE.md` - Frontend module context

- **Development Planning** (`plan.md`)
  - Detailed development roadmap with priorities
  - Task breakdown with acceptance criteria
  - Definition of done for all components

### Changed
- **Enhanced Project Structure Documentation**
  - Updated README.md with comprehensive architecture details
  - Detailed component breakdown and interaction scenarios
  - Technology stack justification and rationale

---

## [0.1.0] - 2025-01-10

### Added
- **Initial Project Setup**
  - Docker Compose environment with hot-reload
  - FastAPI backend with WebSocket support
  - React frontend with Tailwind CSS
  - SQLite database configuration
  - Dual WebSocket managers (UI and MCP)

- **Basic Infrastructure**
  - CORS middleware for local development
  - Environment variable configuration
  - Volume mounts for database and shared filesystem
  - Basic health check endpoints

### Technical Foundation
- **Backend**: FastAPI with async/await support
- **Frontend**: React 18 with TypeScript and Vite
- **Database**: SQLite with SQLAlchemy ORM
- **Containerization**: Docker with development optimization

---

## Version History Legend

- 🎉 Major milestones
- 🚀 New features  
- 🔄 Changes to existing functionality
- 🔐 Security enhancements
- 📁 File system operations
- 📋 Protocol implementations
- 📐 Schema/model definitions
- 📊 Monitoring and logging
- 📈 Development progress
- ⚠️ Breaking changes
- 🧪 Testing and validation
- 🔧 Bug fixes
- 📚 Documentation updates

[Unreleased]: https://github.com/user/mcp-knowledgeexplorer/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/user/mcp-knowledgeexplorer/compare/v0.2.0...v1.0.0
[0.2.0]: https://github.com/user/mcp-knowledgeexplorer/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/user/mcp-knowledgeexplorer/releases/tag/v0.1.0