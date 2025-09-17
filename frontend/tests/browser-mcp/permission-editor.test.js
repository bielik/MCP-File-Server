/**
 * Browser MCP Tests for Two-Panel Permission Editor
 *
 * Tests the two-panel permission editor interface using Browser MCP tools
 * for comprehensive visual and interaction testing.
 */

const { BrowserMCP, BROWSER_MCP_CONFIG } = require('./setup');

describe('Permission Editor Browser MCP Tests', () => {
  let browser;
  let testWorkspace;

  beforeAll(async () => {
    browser = BrowserMCP;
    await browser.initialize();

    // Create test workspace for permission testing
    const workspaceResponse = await fetch(`${BROWSER_MCP_CONFIG.apiUrl}/api/workspaces`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: 'Permission Editor Test Workspace',
        description: 'For testing permission editor functionality',
        is_active: true
      })
    });
    testWorkspace = await workspaceResponse.json();
  });

  beforeEach(async () => {
    // Navigate to permission editor
    await browser.navigate(`/permissions?workspace=${testWorkspace.id}`);
    await browser.waitForElement('[data-testid="permission-editor"]');
  });

  describe('Two-Panel Layout Testing', () => {
    test('two-panel layout renders correctly', async () => {
      // Wait for both panels to load
      await browser.waitForElement('[data-testid="file-tree-panel"]');
      await browser.waitForElement('[data-testid="permission-rules-panel"]');

      // Take screenshot of two-panel layout
      await browser.screenshot('permission-editor-two-panel-layout.png');

      // Verify both panels are visible
      expect(await browser.isVisible('[data-testid="file-tree-panel"]')).toBe(true);
      expect(await browser.isVisible('[data-testid="permission-rules-panel"]')).toBe(true);

      // Verify panel sizing and layout
      expect(await browser.isVisible('[data-testid="panel-splitter"]')).toBe(true);
    });

    test('file tree navigation functionality', async () => {
      // Wait for file tree to load
      await browser.waitForElement('[data-testid="file-tree"]');

      // Expand a directory in the file tree
      await browser.click('[data-testid="expand-projects"]');
      await browser.waitForElement('[data-testid="file-item-projects/webapp"]');

      // Take screenshot of expanded tree
      await browser.screenshot('permission-editor-file-tree-expanded.png');

      // Select a file
      await browser.click('[data-testid="file-item-projects/webapp/src/main.py"]');

      // Verify file selection highlighting
      expect(await browser.isVisible('[data-testid="selected-file-indicator"]')).toBe(true);

      // Take screenshot of file selection
      await browser.screenshot('permission-editor-file-selected.png');
    });

    test('permission indicator display', async () => {
      // Add a permission rule first via API
      await fetch(`${BROWSER_MCP_CONFIG.apiUrl}/api/workspaces/${testWorkspace.id}/permissions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          path: 'projects',
          permission_type: 'write',
          rule_type: 'allow',
          description: 'Allow write access to projects'
        })
      });

      // Refresh the page to see permission indicators
      await browser.navigate(`/permissions?workspace=${testWorkspace.id}`);
      await browser.waitForElement('[data-testid="file-tree"]');

      // Wait for permission indicators to load
      await browser.wait(500);

      // Take screenshot of permission indicators
      await browser.screenshot('permission-editor-with-indicators.png');

      // Verify permission indicators are visible
      expect(await browser.isVisible('[data-testid="permission-indicator-write"]')).toBe(true);
    });
  });

  describe('Permission Rule Management', () => {
    test('add permission rule workflow', async () => {
      // Click add permission button
      await browser.click('[data-testid="add-permission-button"]');

      // Wait for permission form to appear
      await browser.waitForElement('[data-testid="permission-form"]');

      // Fill in permission details
      await browser.type('[data-testid="permission-path"]', 'materials');
      await browser.select('[data-testid="permission-type"]', 'read');
      await browser.select('[data-testid="rule-type"]', 'allow');
      await browser.type('[data-testid="permission-description"]', 'Allow read access to materials');

      // Take screenshot of filled form
      await browser.screenshot('permission-editor-add-permission-form.png');

      // Submit permission
      await browser.click('[data-testid="submit-permission"]');

      // Wait for permission to appear in list
      await browser.waitForElement('[data-testid="permission-rule-materials"]');

      // Take screenshot of updated permission list
      await browser.screenshot('permission-editor-permission-added.png');

      // Verify permission appears in rules panel
      expect(await browser.isVisible('[data-testid="permission-rule-materials"]')).toBe(true);
    });

    test('edit permission rule workflow', async () => {
      // First create a permission to edit
      await fetch(`${BROWSER_MCP_CONFIG.apiUrl}/api/workspaces/${testWorkspace.id}/permissions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          path: 'output',
          permission_type: 'read',
          rule_type: 'allow',
          description: 'Initial read access'
        })
      });

      // Refresh page
      await browser.navigate(`/permissions?workspace=${testWorkspace.id}`);
      await browser.waitForElement('[data-testid="permission-editor"]');

      // Click edit button on permission rule
      await browser.click('[data-testid="edit-permission-output"]');

      // Wait for edit form
      await browser.waitForElement('[data-testid="permission-edit-form"]');

      // Change permission type
      await browser.select('[data-testid="permission-type"]', 'write');
      await browser.type('[data-testid="permission-description"]', 'Updated to write access');

      // Take screenshot of edit form
      await browser.screenshot('permission-editor-edit-permission-form.png');

      // Save changes
      await browser.click('[data-testid="save-permission"]');

      // Wait for update to complete
      await browser.wait(500);

      // Take screenshot of updated permission
      await browser.screenshot('permission-editor-permission-updated.png');

      // Verify permission was updated
      await browser.waitForText('Updated to write access');
    });

    test('delete permission rule workflow', async () => {
      // Create permission to delete
      const permissionResponse = await fetch(`${BROWSER_MCP_CONFIG.apiUrl}/api/workspaces/${testWorkspace.id}/permissions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          path: 'temp',
          permission_type: 'write',
          rule_type: 'allow',
          description: 'Temporary permission for deletion test'
        })
      });
      const permission = await permissionResponse.json();

      // Refresh page
      await browser.navigate(`/permissions?workspace=${testWorkspace.id}`);
      await browser.waitForElement('[data-testid="permission-editor"]');

      // Wait for permission to appear
      await browser.waitForText('Temporary permission for deletion test');

      // Click delete button
      await browser.click(`[data-testid="delete-permission-${permission.id}"]`);

      // Wait for confirmation dialog
      await browser.waitForElement('[data-testid="delete-permission-confirmation"]');

      // Take screenshot of confirmation dialog
      await browser.screenshot('permission-editor-delete-confirmation.png');

      // Confirm deletion
      await browser.click('[data-testid="confirm-permission-delete"]');

      // Wait for permission to be removed
      await browser.wait(500);

      // Take screenshot of updated list
      await browser.screenshot('permission-editor-permission-deleted.png');

      // Verify permission is no longer visible
      // Implementation would depend on specific deletion behavior
    });
  });

  describe('Batch API Integration Testing', () => {
    test('file tree permission status updates', async () => {
      // Add multiple permissions
      const permissions = [
        { path: 'projects', permission_type: 'write', rule_type: 'allow' },
        { path: 'materials', permission_type: 'read', rule_type: 'allow' },
        { path: 'materials/private', permission_type: 'read', rule_type: 'deny' }
      ];

      for (const perm of permissions) {
        await fetch(`${BROWSER_MCP_CONFIG.apiUrl}/api/workspaces/${testWorkspace.id}/permissions`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            ...perm,
            description: `Test permission for ${perm.path}`
          })
        });
      }

      // Refresh page to see all permissions
      await browser.navigate(`/permissions?workspace=${testWorkspace.id}`);
      await browser.waitForElement('[data-testid="file-tree"]');

      // Wait for batch API to load permission statuses
      await browser.wait(1000);

      // Take screenshot of file tree with various permission indicators
      await browser.screenshot('permission-editor-batch-api-integration.png');

      // Verify different permission indicators are visible
      expect(await browser.isVisible('[data-testid="permission-indicator-write"]')).toBe(true);
      expect(await browser.isVisible('[data-testid="permission-indicator-read"]')).toBe(true);
      expect(await browser.isVisible('[data-testid="permission-indicator-denied"]')).toBe(true);
    });

    test('real-time permission updates via batch API', async () => {
      // Take initial screenshot
      await browser.screenshot('permission-editor-before-real-time-update.png');

      // Add permission via API (simulating backend change)
      await fetch(`${BROWSER_MCP_CONFIG.apiUrl}/api/workspaces/${testWorkspace.id}/permissions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          path: 'realtime-test',
          permission_type: 'read',
          rule_type: 'allow',
          description: 'Real-time update test'
        })
      });

      // Wait for WebSocket update and UI refresh
      await browser.wait(1000);

      // Take screenshot after update
      await browser.screenshot('permission-editor-after-real-time-update.png');

      // Verify new permission appears in UI
      await browser.waitForText('Real-time update test');
    });
  });

  describe('Performance Testing', () => {
    test('permission editor load performance', async () => {
      const startTime = Date.now();

      // Navigate to permission editor
      await browser.navigate(`/permissions?workspace=${testWorkspace.id}`);
      await browser.waitForElement('[data-testid="permission-editor"]');

      const loadTime = Date.now() - startTime;

      // Verify load time meets performance target
      expect(loadTime).toBeLessThan(BROWSER_MCP_CONFIG.performance.permissionEditorLoad);

      console.log(`Permission editor loaded in ${loadTime}ms`);
    });

    test('batch API response performance', async () => {
      // Create multiple test paths for performance testing
      const testPaths = [];
      for (let i = 1; i <= 50; i++) {
        testPaths.push(`performance-test/path-${i}/file.txt`);
      }

      const startTime = Date.now();

      // Trigger batch permission check (this would happen during file tree load)
      const response = await fetch(`${BROWSER_MCP_CONFIG.apiUrl}/api/workspaces/${testWorkspace.id}/effective-permissions:batch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ paths: testPaths })
      });

      const responseTime = Date.now() - startTime;
      const results = await response.json();

      // Verify response time and completeness
      expect(responseTime).toBeLessThan(100); // 100ms target for 50 paths
      expect(results.results).toHaveLength(50);

      console.log(`Batch API responded in ${responseTime}ms for 50 paths`);
    });
  });

  afterAll(async () => {
    // Clean up test workspace
    await fetch(`${BROWSER_MCP_CONFIG.apiUrl}/api/workspaces/${testWorkspace.id}`, {
      method: 'DELETE'
    });
  });
});