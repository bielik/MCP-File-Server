# Claude Code Agents Reference Guide

## Overview
Seven specialized Claude Code agents have been configured for the MCP Research File Server project, each with deep expertise in specific technical domains.

## Agent Roster & Specializations

### 🎯 **Priority 1: Critical for Phase 2**

#### **1. multimodal-ai-integration**
**Expertise:** M-CLIP + Docling + LlamaIndex integration  
**Best for:**
- Setting up M-CLIP embeddings (sentence-transformers/clip-ViT-B-32-multilingual-v1)
- Implementing Docling PDF parsing with image extraction
- Creating LlamaIndex document processing pipelines
- Cross-modal search implementation (text↔image)
- Performance tuning embedding generation

**Usage:** `@multimodal-ai-integration help me set up M-CLIP embeddings`

#### **2. rag-evaluation-specialist**
**Expertise:** RAGAS framework and comprehensive testing  
**Best for:**
- Expanding existing RAGAS evaluation capabilities at `tests/rag-evaluation/`
- Custom metrics development for multimodal search
- Large-scale dataset management and automated evaluation
- Quality assurance and regression testing
- Integration with existing Python evaluation services

**Usage:** `@rag-evaluation-specialist enhance the RAGAS framework for multimodal testing`

### 🎯 **Priority 2: High Impact**

#### **3. vector-search-architect**
**Expertise:** Qdrant + advanced search algorithms  
**Best for:**
- Designing optimal Qdrant collections for multimodal data
- Implementing hybrid search (keyword + semantic + multimodal)
- Performance optimization for sub-second response times
- Vector storage architecture and scalability planning
- Search result ranking and relevance tuning

**Usage:** `@vector-search-architect set up Qdrant multimodal collections`

#### **4. mcp-protocol-integration**
**Expertise:** MCP protocol and AI agent connectivity  
**Best for:**
- Claude Desktop and ChatGPT Desktop integration testing
- MCP tool optimization and new tool development
- Protocol compliance validation and error handling
- Agent behavior testing and performance monitoring
- Security validation and sandboxing

**Usage:** `@mcp-protocol-integration test integration with Claude Desktop`

### 🎯 **Priority 3: Valuable Support**

#### **5. react-ui-specialist**
**Expertise:** Advanced React/TypeScript frontend  
**Best for:**
- Advanced file explorer features and performance optimization
- Real-time UI updates and WebSocket state management
- Research workflow UX and accessibility improvements
- Virtualized lists and bulk operations
- Integration with backend search systems

**Usage:** `@react-ui-specialist optimize the file explorer for large collections`

#### **6. security-file-system**
**Expertise:** Security hardening and file system optimization  
**Best for:**
- Advanced security hardening and vulnerability assessment
- File system performance optimization
- Audit logging and compliance features
- Agent sandboxing and permission refinement
- Research data handling security

**Usage:** `@security-file-system audit the three-tier permission system`

#### **7. documentation-api-design**
**Expertise:** Technical writing and developer experience  
**Best for:**
- Comprehensive API documentation generation
- User guides and setup instructions
- Architecture documentation and diagrams
- Integration examples and usage patterns
- Developer onboarding materials

**Usage:** `@documentation-api-design create comprehensive API docs for MCP tools`

## How to Use the Agents

### Command Format
```
@agent-name [your request]
```

### Agent Selection Guidelines

**For Phase 2 Implementation (Current Priority):**
1. **Start with:** `@multimodal-ai-integration` for M-CLIP and Docling setup
2. **Test with:** `@rag-evaluation-specialist` for validation
3. **Scale with:** `@vector-search-architect` for Qdrant optimization

**For Integration & Testing:**
- Use `@mcp-protocol-integration` for AI agent connectivity
- Use `@rag-evaluation-specialist` for comprehensive testing

**For Enhancement & Polish:**
- Use `@react-ui-specialist` for frontend improvements
- Use `@security-file-system` for hardening
- Use `@documentation-api-design` for documentation

### Agent Collaboration Patterns

#### **Multimodal Pipeline Setup:**
1. `@multimodal-ai-integration` → Sets up M-CLIP and processing
2. `@rag-evaluation-specialist` → Tests and validates quality
3. `@vector-search-architect` → Optimizes storage and search

#### **Integration Testing:**
1. `@mcp-protocol-integration` → Tests agent connectivity
2. `@rag-evaluation-specialist` → Validates end-to-end performance
3. `@security-file-system` → Ensures security compliance

#### **Feature Development:**
1. Any technical agent → Implements feature
2. `@rag-evaluation-specialist` → Tests functionality
3. `@documentation-api-design` → Documents usage

## Agent Context & Knowledge

### Shared Project Context
All agents understand:
- Project structure and current Phase 2 status
- Existing RAGAS evaluation framework
- Three-tier permission system
- Technology stack (Node.js/TypeScript, React, Python)
- Docker Qdrant setup availability

### Agent-Specific Knowledge
Each agent has deep expertise in their domain and access to:
- Relevant documentation and best practices
- Performance benchmarks and success criteria
- Integration patterns with existing systems
- Testing methodologies for their specialty

## Success Metrics by Agent

### **multimodal-ai-integration**
- ✅ 512-dimensional embeddings generated
- ✅ PDF processing >95% accuracy
- ✅ Cross-modal search >0.7 relevance

### **rag-evaluation-specialist**
- ✅ RAGAS scores >0.7 across all metrics
- ✅ Automated testing pipeline operational
- ✅ Custom multimodal metrics implemented

### **vector-search-architect**
- ✅ Query response times <200ms
- ✅ Vector storage latency <100ms
- ✅ Search relevance >0.8 scores

### **mcp-protocol-integration**
- ✅ All MCP tools working with AI agents
- ✅ Protocol compliance validated
- ✅ Error handling robust

### **react-ui-specialist**
- ✅ Smooth performance with 1000+ files
- ✅ Real-time updates working seamlessly
- ✅ Accessible and responsive design

### **security-file-system**
- ✅ Zero security vulnerabilities
- ✅ Complete audit trail
- ✅ Agent sandboxing effective

### **documentation-api-design**
- ✅ Complete API documentation
- ✅ Clear setup instructions
- ✅ Integration examples provided

## Getting Started

### Immediate Next Steps
1. Use `@vector-search-architect` to start Qdrant setup
2. Use `@multimodal-ai-integration` for M-CLIP installation
3. Use `@rag-evaluation-specialist` to validate each component

### Pro Tips
- **Be specific:** Include context about what you're trying to achieve
- **Reference existing work:** Mention current implementations and constraints
- **Ask for validation:** Request testing and quality checks
- **Combine agents:** Use multiple agents for complex tasks

---

## ✅ Successfully Created Agents

All 7 specialized agents have been created as individual Markdown files in the correct Claude Code format:

**Agent Files:** `.claude/agents/` directory
- `multimodal-ai-integration.md` - Critical for Phase 2
- `rag-evaluation-specialist.md` - Critical for Phase 2  
- `vector-search-architect.md` - High priority
- `mcp-protocol-integration.md` - High priority
- `react-ui-specialist.md` - Medium priority
- `security-file-system.md` - Medium priority
- `documentation-api-design.md` - Low priority

**Created:** 2025-09-03  
**Status:** ✅ All agents configured and ready for use with proper Markdown + YAML frontmatter format