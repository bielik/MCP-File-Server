# MCP Research File Server - Project Context & Setup Guide

## Project Overview
**Project Name:** MCP Research File Server  
**Type:** Multimodal Model Context Protocol (MCP) File Server for Research Proposal Development  
**Status:** Active development - Phase 1 foundation  
**Purpose:** Create a sophisticated local MCP server that enables AI agents (Claude, ChatGPT, Gemini) to assist with research proposal and paper writing through intelligent multimodal file management, advanced search, and contextual discovery.

## Project Scope & Objectives
This specialized MCP server creates a research writing assistant that:
- **Multimodal Intelligence**: Processes and searches both text and images using M-CLIP embeddings
- **Research-Optimized Workflow**: Three-tier permission system (context/working/output) matching academic patterns
- **Agent File Management**: AI agents can create organized folder structures and files
- **Advanced Search**: Keyword (FlexSearch) + Semantic (M-CLIP) + Cross-modal search capabilities
- **Multilingual Support**: M-CLIP enables multilingual text processing and search
- **Visual Document Processing**: Extracts and indexes images from PDFs even without captions

## Technology Stack
Final architecture using best-in-class tools for multimodal research:

### Core MCP Server
- **Runtime:** Node.js (TypeScript) - Official MCP SDK support
- **Framework:** Express.js - HTTP server + WebSocket for real-time UI updates
- **MCP Library:** @modelcontextprotocol/sdk - Official TypeScript SDK
- **File System:** Node.js fs/promises with chokidar monitoring
- **Security:** Granular file permission system with path validation

### Multimodal AI Pipeline  
- **M-CLIP:** Multilingual + multimodal embeddings (text + images)
- **Docling:** PDF parsing with comprehensive image extraction
- **LlamaIndex:** Document processing orchestration and chunking
- **TikToken:** Optimal token counting for chunk sizing
- **Qdrant:** Local vector database for multimodal embeddings

### Search Technologies
- **FlexSearch:** Fast keyword/phrase search with multilingual support
- **M-CLIP Embeddings:** Semantic and cross-modal search capabilities
- **Hybrid Architecture:** Agents choose search strategy via separate MCP tools

### Web Interface
- **React + TypeScript:** Modern file explorer with drag-and-drop
- **React-Window:** Virtualized lists for large file collections  
- **React-DnD:** File organization and permission assignment
- **WebSocket:** Real-time file system updates

### Development Tools
- **Build:** Vite for fast development and production builds
- **Linting:** ESLint with TypeScript rules + Prettier
- **Testing:** Vitest for unit tests + Playwright for UI testing
- **Package Manager:** pnpm for efficient dependency management

## Final Architecture

### Core Components
1. **MCP Server Core** (`src/server/`)
   - Multi-transport MCP server (stdio, WebSocket)
   - Tool registration for file operations and search
   - Connection health monitoring and auto-recovery

2. **Multimodal Search Engine** (`src/search/`)
   - **FlexSearch Integration**: Fast keyword/phrase matching with multilingual support
   - **M-CLIP Semantic Search**: Text embeddings for conceptual queries
   - **Cross-Modal Search**: Text→image and image→text search capabilities
   - **Agent Choice Architecture**: Separate MCP tools for each search strategy

3. **File Management System** (`src/files/`)
   - **Three-Tier Permissions**: Context (read-only) + Working (read/write) + Output (agent creation)
   - **Agent Folder Control**: Subfolder creation rights in output directory
   - **File System Monitoring**: Real-time change detection with chokidar
   - **Metadata Management**: File type, size, language, permissions tracking

4. **Document Processing Pipeline** (`src/processing/`)
   - **Docling Integration**: PDF parsing with comprehensive image extraction
   - **M-CLIP Embeddings**: Text + image embedding generation
   - **LlamaIndex Orchestration**: Document chunking and indexing workflow
   - **Multilingual Processing**: Automatic language detection and processing

5. **Vector Storage** (`src/storage/`)
   - **Qdrant Integration**: Local vector database with multimodal collections
   - **Embedding Management**: Text chunks, image chunks, cross-modal indexing
   - **Metadata Storage**: Document structure, relationships, and search optimization

6. **Web Interface** (`src/web/`)
   - **File Explorer**: Folder tree navigation with drag-and-drop organization
   - **List Views**: Advanced filtering and sorting capabilities
   - **Permission Management**: Visual assignment of read/write permissions
   - **Real-time Updates**: WebSocket integration for live file system changes

### Project Structure
```
/
├── src/
│   ├── server/           # MCP server core with multi-transport support
│   ├── search/           # Multimodal search engines (FlexSearch + M-CLIP)
│   ├── files/            # Three-tier file permission system
│   ├── processing/       # Document processing pipeline (Docling + LlamaIndex)
│   ├── storage/          # Qdrant vector storage and metadata management  
│   ├── web/              # React-based file explorer interface
│   ├── config/           # Environment and system configuration
│   ├── utils/            # Shared utilities and helpers
│   └── types/            # TypeScript definitions for multimodal data
├── tests/                # Comprehensive test suites
├── docs/                 # API documentation and user guides
├── docker/               # Qdrant containerization
└── examples/             # Sample research documents and workflows
```

## Development Workflow & Standards

### Setup Process
1. Initialize Node.js project with pnpm and TypeScript
2. Install MCP SDK, M-CLIP, Docling, LlamaIndex, Qdrant client
3. Configure development environment (Vite, ESLint, Prettier)
4. Set up local Qdrant instance via Docker
5. Implement basic MCP server with multimodal tool registration
6. Create React-based file explorer interface
7. Build document processing pipeline progressively

### Code Standards
- **TypeScript:** Strict mode enabled, full type coverage
- **Naming:** camelCase for variables/functions, PascalCase for classes/types
- **Error Handling:** Always use proper error types, never throw strings
- **Async:** Prefer async/await over Promises chains
- **Validation:** Validate all inputs using Zod schemas
- **Security:** Never trust user input, always sanitize paths

### Testing Strategy
- Unit tests for all core functions
- Integration tests for MCP protocol compliance
- Security tests for path traversal and access control
- Performance tests for file operations
- Mock file system for isolated testing

## Security Considerations
This file server will handle file system access, making security paramount:

### Path Security
- Implement strict path sanitization
- Prevent directory traversal attacks (../, ..\)
- Whitelist allowed directories only
- Validate all file paths before operations

### Authentication & Authorization
- JWT-based authentication
- Role-based access control (RBAC)
- Per-directory permissions
- API rate limiting

### File Operation Security
- File size limits
- File type restrictions
- Virus scanning integration (future)
- Audit logging of all operations

## MCP Protocol Compliance
Ensure full compliance with MCP specification:
- Proper message format handling
- Error response formatting
- Connection lifecycle management
- Protocol versioning support

## MCP Tools for AI Agents

### File Management Tools
- **`read_file`**: Read content from context or working files
- **`write_file`**: Modify files in working directories  
- **`create_file`**: Create new files in output folder with subfolder support
- **`list_files`**: Browse available files with permission filtering
- **`get_folder_structure`**: Navigate output directory for file organization
- **`get_file_metadata`**: Access file properties, permissions, and statistics

### Search Tools (Agent Choice)
- **`search_text`**: Fast keyword/phrase search with multilingual support
- **`search_semantic`**: Conceptual search using M-CLIP text embeddings
- **`search_multimodal`**: Cross-modal search across text and images

### Multimodal Capabilities
- **Text→Image Search**: "Find diagrams showing methodology flowcharts"
- **Image→Text Search**: Upload image, find related textual descriptions  
- **Multilingual Search**: Query in any language, find relevant content regardless of source language
- **Caption-Free Image Retrieval**: Find relevant images even without text descriptions

## Implementation Phases

### Phase 1: Foundation + File Management UI (Weeks 1-2)
- MCP server with TypeScript SDK integration
- React-based file explorer with drag-and-drop organization
- Three-tier permission system implementation  
- Basic file operation MCP tools
- Real-time file system monitoring

### Phase 2: Multimodal Document Processing (Weeks 3-4)
- M-CLIP integration for text + image embeddings
- Docling PDF parsing with comprehensive image extraction
- LlamaIndex document processing orchestration
- Qdrant local setup with multimodal collections
- Automated document indexing pipeline

### Phase 3: Advanced Search Implementation (Weeks 5-6)
- FlexSearch integration for keyword matching
- M-CLIP semantic and cross-modal search tools
- Search result ranking and relevance optimization
- Multilingual query processing
- Search interface in web UI for testing

### Phase 4: Agent File Management + UI Polish (Weeks 7-8)
- Agent subfolder creation in output directory
- Advanced file organization and metadata management
- UI enhancements (thumbnails, filtering, sorting)
- File conflict resolution and audit logging
- Performance optimization and caching

### Phase 5: Integration Testing + Documentation (Weeks 9-10)
- Claude Desktop integration and comprehensive testing
- ChatGPT Desktop integration with fallback solutions
- Complete API documentation with examples
- User setup guides and research workflow tutorials
- Performance benchmarking and optimization

## Environment Variables & Configuration
```
# MCP Server Configuration
MCP_PORT=3000
MCP_HOST=localhost
WEB_UI_PORT=3001

# File System Permissions
CONTEXT_FOLDERS=/path/to/reference,/path/to/policies
WORKING_FOLDERS=/path/to/proposals,/path/to/drafts  
OUTPUT_FOLDER=/path/to/agent-output
MAX_FILE_SIZE=50MB
MAX_FILES_PER_DIRECTORY=5000

# Qdrant Vector Database
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION_PREFIX=research_mcp
QDRANT_API_KEY=optional-for-cloud

# M-CLIP Configuration  
MCLIP_MODEL_NAME=sentence-transformers/clip-ViT-B-32-multilingual-v1
MCLIP_CACHE_DIR=./models/mclip
EMBEDDING_DIMENSION=512

# Document Processing
DOCLING_MAX_PAGES=500
IMAGE_EXTRACTION=true
LANGUAGES=en,de,fr,es,it
CHUNK_SIZE=800
CHUNK_OVERLAP=50

# Performance & Caching
ENABLE_CACHING=true
CACHE_TTL=3600
MAX_CONCURRENT_PROCESSING=4

# Logging
LOG_LEVEL=info
LOG_FILE=logs/mcp-research-server.log
```

## Common Commands & Scripts
Development and operational commands for the multimodal MCP server:

```bash
# Development
pnpm dev             # Start MCP server + Web UI with hot reload
pnpm build           # Build production bundles (server + web)
pnpm test            # Run test suite (unit + integration)
pnpm test:ui         # Run Playwright UI tests
pnpm lint            # Run ESLint with TypeScript rules
pnpm format          # Format code with Prettier

# Qdrant Management
pnpm qdrant:start    # Start local Qdrant via Docker
pnpm qdrant:stop     # Stop Qdrant container  
pnpm qdrant:reset    # Clear all collections and restart

# Document Processing
pnpm index:docs      # Process and index all documents in configured folders
pnpm index:check     # Validate embedding consistency and search functionality

# Production
pnpm start           # Start production server (MCP + Web UI)
pnpm start:mcp-only  # Start MCP server without Web UI
pnpm logs            # View structured server logs
pnpm health          # Check system health (Qdrant, embeddings, file access)

# Development Utilities
pnpm dev:mcp         # Start MCP server only for Claude Desktop testing
pnpm dev:web         # Start Web UI only for interface development
pnpm test:search     # Test search functionality with sample queries
```

## Key Decisions & Rationale

### Why Multimodal Architecture (M-CLIP)?
- **Research Requirement**: Academic documents contain critical visual information (diagrams, charts, figures)
- **Caption-Free Image Retrieval**: Many research images lack descriptive captions but are semantically important
- **Cross-Modal Search**: Enables text queries to find relevant visual content and vice versa
- **Multilingual Support**: M-CLIP handles multiple languages essential for international research

### Why Agent Choice Search Strategy?
- **Flexibility**: AI agents understand their query intent better than heuristic classification
- **Simplicity**: No complex query analysis - agents choose appropriate search tool
- **Extensibility**: Easy to add new search strategies as separate MCP tools
- **Performance**: Agents can optimize by using fastest appropriate search method

### Why LlamaIndex + Docling + Qdrant Stack?
- **LlamaIndex**: Proven document processing orchestration, handles complexity of chunking/indexing
- **Docling**: Best-in-class PDF parsing with comprehensive image extraction capabilities  
- **Qdrant**: High-performance local vector database with excellent multimodal support
- **Minimal Custom Code**: Leverage battle-tested tools instead of building from scratch

### Why Three-Tier Permission System?
- **Context Files**: Read-only reference materials (funding docs, policies, examples)
- **Working Files**: Editable proposal sections and drafts
- **Output Files**: Agent-controlled creation zone with subfolder management rights
- **Research Workflow Match**: Mirrors how researchers actually organize and protect their documents

### Why Local-First Architecture?
- **Data Privacy**: Research documents often contain sensitive or proprietary information
- **Performance**: Local embeddings and search provide sub-second response times
- **Reliability**: No dependence on external APIs for core functionality
- **Cost Control**: No per-query costs for embedding or search operations

## Development Notes & Reminders

### Critical Implementation Points
1. Always validate and sanitize file paths
2. Implement proper error boundaries
3. Log all file operations for audit trails
4. Use streaming for large file operations
5. Implement circuit breakers for external dependencies

### Testing Priorities
1. Security testing (path traversal, access control)
2. MCP protocol compliance
3. File operation correctness
4. Performance under load
5. Error handling edge cases

### UI Testing with Playwright
We use Playwright for automated UI testing and visual verification of the MCP Research File Server frontend:

**Setup & Usage:**
```javascript
// screenshot.cjs - Example Playwright test script
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: false });
  const page = await browser.newPage();
  
  // Navigate to the frontend
  await page.goto('http://localhost:3004');
  
  // Take a screenshot
  await page.screenshot({ path: 'mcp-frontend-screenshot.png', fullPage: true });
  
  await browser.close();
})();
```

**Running Tests:**
```bash
# Take a screenshot of the running application
node screenshot.cjs

# For automated testing (future implementation)
npm run test:e2e
```

**Test Coverage:**
- Visual regression testing of UI components
- File explorer navigation and interaction
- Permission system verification
- Real-time WebSocket update testing
- API integration verification

### Performance Considerations
- Stream large files instead of loading into memory
- Implement file operation caching where appropriate
- Use worker threads for CPU-intensive operations
- Monitor memory usage during bulk operations

## Future Enhancements
- Docker containerization
- Kubernetes deployment configs
- Prometheus metrics integration
- GraphQL API layer (in addition to MCP)
- File preview generation
- Real-time collaboration features

---

**Last Updated:** 2025-08-31  
**Next Review:** After Phase 1 completion

This cloudmd file serves as the single source of truth for project context, architecture decisions, and development guidelines. Update it as the project evolves to maintain accurate context for all future AI interactions.