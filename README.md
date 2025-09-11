# MCP KnowledgeExplorer

### \# 1. Introduction

#### **1.1. Purpose**

This document defines the high-level software architecture for the MCP Research File Server. It consolidates the learnings from previous iterations and establishes a clear, maintainable, and scalable blueprint for the project's development.

#### **1.2. Scope**

The project is a sophisticated, local-first Model Context Protocol (MCP) server that enables AI agents to assist with research. It provides a web-based user interface for configuration, real-time monitoring, and granular permission management over the local file system.

#### **1.3. Goals and Requirements**

  * **Functional Requirements:**

      * Provide an MCP-compliant server for AI clients (e.g., Claude Code).
      * Offer a web UI for server configuration and real-time monitoring.
      * Log all AI client activity in the UI as it happens.
      * Allow users to manage file and folder permissions on the fly.
      * Implement core file system tools (`read_file`, `list_files`, etc.) for AI agents.
      * The architecture must support future integration of keyword and semantic search.

  * **Non-Functional Requirements:**

      * **Simplicity:** The entire system must be startable with a single command (`docker-compose up`).
      * **Debuggability:** All server logs must be consolidated and easily accessible to simplify troubleshooting.
      * **Maintainability:** The codebase must have a clear separation of concerns to allow for easy updates and feature additions.
      * **Security:** File system access must be strictly controlled through an "allowlist" model, preventing unintended access.
      * **Reproducibility:** The entire development and production environment must be containerized with Docker.

-----

### \# 2. Architectural Vision: The "Unified Hub" Model

The architecture is built on the **"Unified Hub"** principle. This model eliminates the complexity of previous designs by establishing a **single, persistent backend server** that acts as the central point of control for all clients.

This is analogous to a **permanent restaurant**. The server is always open for business. All customers—whether it's you in the browser or an AI agent—come through the same front door and are handled by the same staff. This contrasts with previous models that involved temporary, freelance workers who were difficult to manage and monitor.

The core of this vision is a system that is easy to run, easy to understand, and robust enough for complex tasks.

-----

### \# 3. System Architecture

#### **3.1. High-Level Diagram**

The entire system is orchestrated by Docker Compose, which manages two distinct but interconnected services. All client interactions are funneled through the central Backend Hub.

```ascii
   User's Local Machine
+--------------------------------------------------------------------+
|                                                                    |
|  ┌──────────┐   Browser    ┌──────────┐      MCP      ┌───────────┐ |
|  │   You    ├─────────────>│ Frontend │<───┐ (HTTP)   │ AI Client │ |
|  └──────────┘              └──────────┘    │          └─────┬─────┘ |
|                                ▲           │                │(WS)   |
|                                │(Vite)      │                │       |
|                                │           │                │       |
|  +-----------------------------▼-----------▼----------------▼-----+ |
|  | Docker Environment (docker-compose up)                       | |
|  |                                                              | |
|  |  ┌────────────────────────────────────────────────────────┐  | |
|  |  │             Backend Container (FastAPI "Hub")          │  | |
|  |  │ 1. HTTP API Server (for UI)                            │  | |
|  |  │ 2. WebSocket Hub (for UI & MCP Clients)                │  | |
|  |  │ 3. File System & Service Logic                         │  | |
|  |  └───────────────────┬────────────────────────────────────┘  | |
|  |                       │(SQLite)                              | |
|  |  ┌────────────────────▼───────────────────────────────────┐  | |
|  |  │                                                      │  | |
|  |  │    ┌────────────┐               ┌────────────┐       │  | |
|  |  │    │ SQLite DB  │               │ Local Files│       │  | |
|  |  │    │ (Volume)   │               │ (Volume)   │       │  | |
|  |  │    └────────────┘               └────────────┘       │  | |
|  |  │                                                      │  | |
|  |  └──────────────────────────────────────────────────────┘  | |
|  |                                                              | |
|  +--------------------------------------------------------------+ |
|                                                                    |
+--------------------------------------------------------------------+
```

#### **3.2. Component Breakdown**

  * **Backend Hub (FastAPI)** 🧠
    This is the core of the system. It's a single Python server that handles all logic.

      * **Technology:** FastAPI
      * **Responsibilities:**
          * **HTTP API:** Serves REST endpoints for the frontend (e.g., `/api/config`).
          * **WebSocket Hub:** Manages persistent WebSocket connections for both the UI (`/ws/ui`) and AI clients (`/ws/mcp`). It will handle the MCP protocol directly over its WebSocket endpoint.
          * **Service Logic:** Contains modular services for file operations, permissions, and future search/indexing.

  * **Frontend UI (React)** 🎨
    The interactive dashboard for managing and monitoring the server.

      * **Technology:** React with Vite
      * **Responsibilities:**
          * Provides the file explorer and permission management interface.
          * Connects to the Hub's WebSocket to display the live activity log.
      * **State Management:** Uses **Zustand** for global state to ensure a clean and maintainable component structure.
      * **Core Functionality:** The UI provides two primary views: a File Explorer and a Configuration panel.
          * **File Explorer:** Features a breadcrumb navigation bar that can be edited for direct path entry, shortcuts to common directories, and a file/folder tree view. Users can select single or multiple items via checkboxes to perform bulk operations.
          * **Permission Management:** When items are selected, a panel appears allowing the user to assign `Context` (Read-Only), `Working` (Read-Write), or `Output` (Agent-Controlled) permissions.
          * **Configuration & Monitoring:** This view displays the current server port configuration, lists the folders assigned to each permission level, shows file system statistics, and includes an "Activity Log" for real-time monitoring of MCP client actions.

  * **Containerization (Docker)** 📦
    The foundation that makes the system easy to run and reproduce.

      * **Technology:** Docker & Docker Compose
      * **Services:** Manages two containers: `backend` and `frontend` (for development).
      * **File Access:** Uses Docker **bind mounts** to create a **controlled interface** to specific folders on your host computer. The security of this model relies on the backend application logic to strictly enforce the "allowlist" and prevent unauthorized file access.

-----

### \# 4. Data Flow & Interaction Scenarios

  * **Scenario 1: User Loads the Web UI**

    1.  The browser loads the React application from the **Frontend** container.
    2.  The UI makes an **HTTP API** call to the **Backend Hub** to fetch the initial configuration.
    3.  The UI also establishes a **WebSocket** connection to the **Backend Hub** to listen for real-time updates.

  * **Scenario 2: AI Client Executes a Tool**

    1.  The AI Client establishes a **WebSocket** connection to the **Backend Hub's** `/ws/mcp` endpoint.
    2.  It sends an MCP `tools/call` request over the WebSocket.
    3.  The **Backend Hub** executes the file system logic.
    4.  The Hub sends the tool result back to the AI client over the same MCP WebSocket.
    5.  Simultaneously, the Hub sends a log message about the tool call over the `/ws/ui` WebSocket to your browser, which appears instantly in the Activity Log.

-----

### \# 5. Technology Stack

| Category | Technology | Purpose |
| :--- | :--- | :--- |
| **Containerization** | Docker, Docker Compose | To create a reproducible, isolated, and easy-to-manage application environment. |
| **Backend** | Python, FastAPI | The main server hub; provides the API and WebSocket services. |
| **Frontend** | React, Vite, TypeScript | The interactive web UI for management and monitoring. |
| **Real-time Comms** | WebSockets | For live logging in the UI and MCP communication. |
| **State Management** | Zustand | For clean and simple global state management in the frontend UI. |
| **Styling** | Tailwind CSS | For utility-first CSS styling. |
| **Database (State)** | SQLite | For storing persistent application state. |

-----

### \# 6. UI/UX Design Strategy

To ensure the project has a modern, professional, and maintainable design, the following three-step strategy is recommended.

#### **6.1. Adopt a Component Library (Recommended: Shadcn/ui)**

Instead of writing all CSS from scratch, using a component library provides a foundation of well-designed, accessible, and consistent components.

  * **Action:** Integrate **Shadcn/ui**. It's not a traditional component library but a collection of reusable components built with Radix UI and Tailwind CSS. You "own" the code, making it fully customizable while ensuring a modern aesthetic and best practices for accessibility.

#### **6.2. Gather Inspiration from Best-in-Class UIs**

To define what "modern design" means for this project, it's helpful to study existing, high-quality applications, particularly developer tools and dashboards.

  * **Action:** Review the UI/UX of applications like **Vercel**, **Linear**, and the **Stripe Dashboard**. Pay attention to their use of space, typography, color, and how they present complex information clearly.

#### **6.3. Establish a Simple Design System**

A design system ensures consistency. This can be codified directly in the project's configuration.

  * **Action:** Use `frontend/tailwind.config.js` to define a simple design system:
      * **Color Palette:** Define specific shades for primary actions, status indicators (success, error, warning), and neutral backgrounds/text.
      * **Typography:** Set specific sizes and weights for headings, body text, and labels.
      * **Spacing:** Use a consistent spacing scale (e.g., multiples of 4 or 8 pixels) for all margins, padding, and layout gaps.

By following this strategy, you will build a UI that is not only visually appealing but also consistent, maintainable, and easy for users to navigate.

-----

### \# 7. Future Considerations

This architecture is explicitly designed for extensibility.

  * **Search Capabilities:** The planned search features will be implemented by adding new modules to the **Backend Hub's** service layer.
      * **Keyword Search:** A `KeywordSearchService` will be added to the backend.
      * **Semantic Search:** The `IndexingService` will be expanded to generate embeddings. When this feature is implemented, a **Qdrant** container will be added to the Docker environment to store and query the resulting vectors.
  * **WebSocket Scalability:** The current single WebSocket hub is simple and efficient. If the application needs to support a high volume of concurrent AI clients in the future, this component could be split into dedicated services for UI and MCP traffic to allow for independent scaling.