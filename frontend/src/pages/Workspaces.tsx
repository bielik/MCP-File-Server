/**
 * Workspaces Page
 * Phase 3B: Advanced UI & Full Workspace Experience
 *
 * Container page for workspace management functionality
 */

import WorkspaceManager from '../components/WorkspaceManager'

export default function Workspaces() {
  return (
    <div className="min-h-screen bg-gray-900 text-white">
      <div className="container mx-auto max-w-7xl p-8">
        <WorkspaceManager />
      </div>
    </div>
  )
}