# Frontend Source Context - MCP KnowledgeExplorer

## Directory Overview
This is the React TypeScript frontend source directory for the MCP KnowledgeExplorer web interface. The frontend provides a comprehensive dashboard for workspace management, file permissions, indexer monitoring, and real-time AI agent activity tracking.

## Current File Structure

### Core Application Files
- **`main.tsx`** - React application entry point
  - Renders root App component
  - Sets up React strict mode
  - Mounts to DOM element with id 'root'

- **`App.tsx`** - Main React component (3397 lines - Phase 4A complete implementation)
  - Three-tab interface: Workspaces, Permissions, Server Status
  - Advanced workspace management with create/delete/activate
  - Two-panel permission editor with batch operations
  - Phase 4A indexer dashboard with pause/resume controls
  - Real-time WebSocket integration for live updates

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

## ✅ Implemented Component Architecture (Phase 4A Complete)

### ✅ Core Components (Fully Implemented)

#### 1. ✅ Workspace Management (Implemented)
**Location:** Integrated in `App.tsx`
- **Purpose:** Complete workspace CRUD operations
- **Features:**
  - Create new workspaces with name and description
  - Delete workspaces with confirmation dialogs
  - Activate/switch between workspaces with real-time updates
  - Workspace list with active status indicators
  - Form validation and error handling
- **State:** React useState with WebSocket integration for live updates

#### 2. ✅ Two-Panel Permission Editor (Implemented)
**Location:** Integrated in `App.tsx`
- **Purpose:** Visual workspace permission management
- **Features:**
  - Left panel: File tree navigation with permission status indicators
  - Right panel: Permission rule list with add/edit/delete controls
  - "Inspect Permission" feature with detailed rule explanations
  - Batch permission operations via backend API
  - Real-time permission status updates
  - Color-coded permission indicators (Read: Blue, Write: Green, Denied: Red)
- **API Integration:** Uses batch effective permissions endpoint for performance

#### 3. ✅ Indexer Dashboard (Phase 4A Implemented)
**Location:** Integrated in `App.tsx` Server Status tab
- **Purpose:** Monitor and control the Phase 4A indexer service
- **Features:**
  - Real-time indexer status display (Idle, Running, Paused)
  - File processing metrics and progress tracking
  - Pause/Resume controls for indexer service
  - Job queue statistics and performance metrics
  - File discovery and indexing progress indicators
  - Error reporting and status messages
- **API Integration:** Uses indexer control and status endpoints

#### 4. ✅ Real-time Activity Monitoring (Implemented)
**Location:** Integrated in `App.tsx` Server Status tab
- **Purpose:** Live monitoring of MCP operations and system events
- **Features:**
  - Real-time activity feed via WebSocket connection
  - MCP operation logging (tool calls, permission checks)
  - System event tracking (workspace changes, indexer status)
  - Activity filtering and search capabilities
  - Connection status indicators and health monitoring
  - Auto-scroll and activity history management
- **WebSocket Integration:** Listens to `/ws/ui` for real-time updates

### ✅ Layout & Navigation (Implemented)

#### 5. ✅ Tabbed Interface Layout (Implemented)
**Location:** Integrated in `App.tsx`
- **Purpose:** Clean three-tab application interface
- **Features:**
  - Tab navigation: Workspaces, Permissions, Server Status
  - Active tab highlighting and smooth transitions
  - Responsive design with mobile-friendly breakpoints
  - Header with title and connection status indicators
  - Consistent spacing and professional styling
- **Design:** Simplified from complex sidebar to clean tab interface

## ✅ State Management Architecture (Phase 4A Implementation)

### React useState Pattern (Implemented)
**Location:** `App.tsx` component state
**Approach:** Direct React state management for Phase 4A implementation

```typescript
// Implemented State Structure in App.tsx
interface AppState {
  // Workspace State
  workspaces: Workspace[];
  activeWorkspace: Workspace | null;

  // Permission State (Two-Panel Editor)
  selectedPaths: string[];
  pathPermissions: Record<string, PermissionStatus>;
  workspacePermissions: Permission[];

  // Indexer State (Phase 4A)
  indexerStatus: 'idle' | 'running' | 'paused';
  indexingProgress: IndexingMetrics;

  // Activity State
  activities: Activity[];

  // WebSocket State
  isConnected: boolean;
  connectionStatus: 'connecting' | 'connected' | 'disconnected';

  // UI State
  activeTab: 'workspaces' | 'permissions' | 'server';
  confirmDialog: ConfirmDialogState | null;
}
```

## ✅ WebSocket Integration (Phase 4A Implemented)

### Direct WebSocket Management (Implemented)
**Location:** `App.tsx` useEffect hooks
- **Purpose:** Real-time communication with backend for live updates
- **Features:**
  - Automatic connection establishment on component mount
  - Real-time workspace change notifications
  - Live indexer status and progress updates
  - MCP operation activity streaming
  - Connection state management with retry logic
  - Message parsing and state synchronization

```typescript
// Implemented WebSocket Integration
useEffect(() => {
  const ws = new WebSocket(`ws://localhost:8000/ws/ui`);

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.type === 'workspace_activated') {
      fetchWorkspaces(); // Refresh workspace list
    }
    if (data.type === 'indexer_status_update') {
      setIndexerStatus(data.status);
    }
    if (data.type === 'activity') {
      setActivities(prev => [...prev, data.activity]);
    }
  };
}, []);
```

## ✅ API Integration (Phase 4A Implemented)

### Direct Fetch API Calls (Implemented)
**Location:** Inline fetch calls in `App.tsx`
- **Purpose:** REST API communication with backend for all operations
- **Features:**
  - Workspace CRUD operations (create, delete, activate, list)
  - Permission management (batch effective permissions, CRUD)
  - Indexer control operations (pause, resume, status)
  - Real-time data fetching with error handling
  - TypeScript response typing for all endpoints

```typescript
// Implemented API Integration Examples
const fetchWorkspaces = async () => {
  const response = await fetch('/api/workspaces');
  const workspaces = await response.json();
  setWorkspaces(workspaces);
};

const activateWorkspace = async (workspaceId: number) => {
  await fetch(`/api/workspaces/${workspaceId}/activate`, { method: 'PUT' });
  fetchWorkspaces(); // Refresh list
};

const batchEffectivePermissions = async (paths: string[]) => {
  const response = await fetch(`/api/workspaces/${activeWorkspace.id}/effective-permissions:batch`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ paths })
  });
  return response.json();
};
```

## ✅ TypeScript Interfaces (Phase 4A Implemented)

### Core Data Types (Implemented)
**Location:** Inline type definitions in `App.tsx`

```typescript
// Phase 4A Implemented Types
interface Workspace {
  id: number;
  name: string;
  description?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

interface Permission {
  id: number;
  workspace_id: number;
  path: string;
  permission_type: 'read' | 'write';
  rule_type: 'allow' | 'deny';
  description?: string;
}

interface PermissionStatus {
  has_permission: boolean;
  permission_type: 'read' | 'write' | null;
  rule_type: 'allow' | 'deny' | null;
  matched_rule: Permission | null;
  explanation: string;
}

interface IndexingMetrics {
  total_files: number;
  indexed_files: number;
  pending_jobs: number;
  failed_jobs: number;
  indexer_status: 'idle' | 'running' | 'paused';
}

interface Activity {
  id: string;
  timestamp: string;
  type: string;
  message: string;
  level: 'info' | 'warning' | 'error';
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

## ✅ Phase 4A Frontend Implementation Status

### Completed Features
- **✅ Workspace Management**: Full CRUD with real-time updates
- **✅ Two-Panel Permission Editor**: Visual file tree with permission status
- **✅ Indexer Dashboard**: Phase 4A monitoring and control interface
- **✅ Real-time Integration**: WebSocket connectivity for live updates
- **✅ Professional UI**: Clean three-tab interface with Tailwind styling
- **✅ API Integration**: Complete REST API integration with error handling
- **✅ TypeScript Safety**: Full type definitions for all data structures

### Architecture Achievements
- **Monolithic Component**: All functionality integrated in single `App.tsx` for Phase 4A
- **Direct State Management**: React useState for simplicity and direct control
- **Inline API Calls**: Direct fetch integration without abstraction layers
- **Real-time Updates**: WebSocket integration for live system monitoring
- **Responsive Design**: Mobile-friendly layout with professional styling

### Ready for Phase 4B
The frontend now provides a complete foundation for Phase 4B semantic search features:
- Indexer monitoring infrastructure in place
- Real-time status and progress tracking
- Error handling and user feedback systems
- API integration patterns established
- Professional UI framework ready for search tool integration

---

*Last updated: 2025-01-23 - Phase 4A Frontend Implementation Complete*
### Post-4A Frontend Notes
- Indexer Dashboard uses VITE_API_BASE_URL if set to reach backend.
- Added periodic refresh for recent files and jobs in the dashboard.

