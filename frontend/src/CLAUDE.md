# Frontend Source Context - MCP KnowledgeExplorer

## Directory Overview
This is the React TypeScript frontend source directory for the MCP KnowledgeExplorer web interface. The frontend provides a dashboard for configuring the MCP server, managing file permissions, and monitoring AI agent activity in real-time.

## Current File Structure

### Core Application Files
- **`main.tsx`** - React application entry point
  - Renders root App component
  - Sets up React strict mode
  - Mounts to DOM element with id 'root'

- **`App.tsx`** - Main React component (3397 lines - comprehensive implementation)
  - Primary application layout and logic
  - State management integration
  - Component composition and routing
  - WebSocket connection handling

- **`index.css`** - Global styles and Tailwind CSS imports
  - Tailwind base, components, and utilities
  - Global CSS reset and base styles

## Technology Configuration

### Build and Development
- **Vite** - Fast development server and build tool
- **TypeScript** - Full type safety with strict mode
- **React 18** - Modern React with concurrent features
- **Tailwind CSS** - Utility-first CSS framework

### State Management
- **Zustand** - Lightweight state management library
- **Rationale:** Simpler than Redux, perfect for this project's scale
- **Usage:** Global state for file explorer, permissions, and WebSocket data

## Planned Component Architecture

### Core Components (To Be Implemented)

#### 1. File Explorer Component
**File:** `components/FileExplorer.tsx`
- **Purpose:** Main file system navigation interface
- **Features:**
  - Breadcrumb navigation with editable path
  - Tree view of directories and files
  - Multi-select with checkboxes for bulk operations
  - Context menu for file operations
  - Keyboard navigation (arrow keys, enter, escape)
- **State:** Uses Zustand store for current path, selected items, expanded directories
- **Props Interface:**
```typescript
interface FileExplorerProps {
  rootPath: string;
  onSelectionChange: (selectedPaths: string[]) => void;
  selectedPaths: string[];
  permissions: PermissionMap;
}
```

#### 2. Permission Management Panel
**File:** `components/PermissionPanel.tsx`
- **Purpose:** Assign and manage file system permissions
- **Features:**
  - Permission level selection (Context/Working/Output)
  - Bulk permission assignment
  - Visual permission indicators
  - Permission inheritance settings
- **State:** Selected items, current permission levels
- **Props Interface:**
```typescript
interface PermissionPanelProps {
  selectedPaths: string[];
  currentPermissions: PermissionMap;
  onPermissionChange: (paths: string[], level: PermissionLevel) => void;
}
```

#### 3. Activity Log Component
**File:** `components/ActivityLog.tsx`
- **Purpose:** Real-time monitoring of MCP client actions
- **Features:**
  - Live activity feed via WebSocket
  - Activity filtering and search
  - Export functionality
  - Auto-scroll to latest activity
  - Activity type icons and color coding
- **WebSocket Integration:** Listens to `/ws/ui` for activity updates
- **Props Interface:**
```typescript
interface ActivityLogProps {
  maxEntries?: number;
  autoScroll?: boolean;
  filters: ActivityFilter[];
}
```

#### 4. Configuration Dashboard
**File:** `components/ConfigDashboard.tsx`
- **Purpose:** Server configuration and system status
- **Features:**
  - Server port and connection status
  - File system statistics
  - Permission summary
  - Connected client list
- **API Integration:** REST API calls to `/api/config`

### Layout Components

#### 5. Main Layout
**File:** `components/Layout.tsx`
- **Purpose:** Application shell and navigation
- **Features:**
  - Header with title and status indicators
  - Sidebar with navigation menu
  - Main content area with routing
  - Responsive design breakpoints

#### 6. Navigation Sidebar
**File:** `components/Sidebar.tsx`
- **Purpose:** Primary navigation interface
- **Features:**
  - Navigation menu items
  - Collapsible sections
  - Active state indicators
  - Quick access shortcuts

## State Management Architecture

### Zustand Store Structure
**File:** `store/index.ts`

```typescript
interface AppState {
  // File Explorer State
  currentPath: string;
  selectedPaths: string[];
  expandedDirectories: Set<string>;
  
  // Permission State  
  permissions: PermissionMap;
  
  // Activity State
  activities: Activity[];
  
  // WebSocket State
  isConnected: boolean;
  connectionStatus: 'connecting' | 'connected' | 'disconnected';
  
  // Configuration State
  serverConfig: ServerConfig;
  
  // Actions
  setCurrentPath: (path: string) => void;
  setSelectedPaths: (paths: string[]) => void;
  toggleDirectory: (path: string) => void;
  updatePermissions: (path: string, level: PermissionLevel) => void;
  addActivity: (activity: Activity) => void;
  setConnectionStatus: (status: ConnectionStatus) => void;
}
```

## WebSocket Integration

### Connection Management
**File:** `hooks/useWebSocket.ts`
- **Purpose:** Custom hook for WebSocket connection to backend
- **Features:**
  - Automatic reconnection logic
  - Message parsing and routing
  - Connection state management
  - Error handling and logging

```typescript
interface UseWebSocketReturn {
  isConnected: boolean;
  send: (message: any) => void;
  lastMessage: any;
  connectionState: 'connecting' | 'connected' | 'disconnected';
}
```

## API Integration

### HTTP Client
**File:** `services/api.ts`
- **Purpose:** HTTP client for REST API communication
- **Features:**
  - Async/await API calls
  - Error handling and response parsing
  - TypeScript interfaces for all endpoints
  - Request/response logging

```typescript
interface ApiClient {
  getConfig: () => Promise<ServerConfig>;
  updatePermissions: (permissions: PermissionUpdate) => Promise<void>;
  getFileInfo: (path: string) => Promise<FileInfo>;
  exportSettings: () => Promise<ExportData>;
}
```

## TypeScript Interfaces

### Core Data Types
**File:** `types/index.ts`

```typescript
enum PermissionLevel {
  CONTEXT = 'context',    // Read-only
  WORKING = 'working',    // Read-write  
  OUTPUT = 'output'       // Agent-controlled
}

interface FileInfo {
  path: string;
  name: string;
  isDirectory: boolean;
  size: number;
  modified: Date;
  permissions: PermissionLevel | null;
}

interface Activity {
  id: string;
  timestamp: Date;
  clientId: string;
  operation: string;
  path: string;
  result: 'success' | 'error';
  details?: string;
}

interface ServerConfig {
  backendPort: number;
  frontendPort: number;
  databasePath: string;
  sharedFsPath: string;
}
```

## Styling Strategy

### Tailwind CSS Configuration
**File:** `tailwind.config.js`
- **Design System:** Custom color palette, typography scale, spacing
- **Component Classes:** Reusable utility combinations
- **Dark Mode:** Class-based dark mode support
- **Responsive Design:** Mobile-first breakpoint system

### Component Styling Patterns
```typescript
// Consistent styling patterns
const buttonStyles = {
  base: "px-4 py-2 rounded font-medium transition-colors",
  primary: "bg-blue-600 text-white hover:bg-blue-700",
  secondary: "bg-gray-200 text-gray-800 hover:bg-gray-300"
};

// Permission level colors
const permissionColors = {
  context: "text-blue-600 bg-blue-50",
  working: "text-green-600 bg-green-50", 
  output: "text-purple-600 bg-purple-50"
};
```

## Development Workflow

### Component Development Pattern
1. **Create component file** with TypeScript interface
2. **Implement basic structure** with proper props typing
3. **Add Zustand integration** for state management
4. **Implement styling** with Tailwind classes
5. **Add error handling** and loading states
6. **Write component documentation**

### Testing Strategy
- **Component testing** with React Testing Library
- **State testing** with Zustand store tests
- **Integration testing** with WebSocket mocking
- **E2E testing** with Playwright

### Code Quality Standards
- **ESLint** with React and TypeScript rules
- **Prettier** for code formatting
- **TypeScript strict mode** for maximum type safety
- **Component prop validation** with TypeScript interfaces

## Performance Considerations

### Optimization Techniques
- **React.memo** for expensive components
- **useMemo/useCallback** for computed values and functions
- **Virtual scrolling** for large file lists
- **Debounced search** for file filtering
- **WebSocket message batching** for high-frequency updates

### Bundle Optimization
- **Tree shaking** with Vite
- **Code splitting** with dynamic imports
- **Asset optimization** with Vite plugins
- **Bundle analysis** with rollup-plugin-analyzer

## Accessibility Features

### WCAG Compliance
- **Semantic HTML** structure
- **ARIA labels** and roles
- **Keyboard navigation** support
- **Screen reader** compatibility
- **Color contrast** meeting AA standards
- **Focus management** for modal dialogs

## Future Enhancements

### Advanced Features
- **Drag and drop** file operations
- **Context menu** with right-click actions
- **Keyboard shortcuts** for power users
- **File preview** in modal dialogs
- **Batch operations** with progress indicators

### UI/UX Improvements
- **Shadcn/ui integration** for professional components
- **Animation library** (Framer Motion) for smooth transitions
- **Toast notifications** for user feedback
- **Loading skeletons** for better perceived performance

---

*This context file should be updated as frontend components are implemented, particularly when new components are added or major architectural changes are made.*