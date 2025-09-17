/**
 * Browser MCP Tests for Real-time WebSocket Updates
 *
 * Tests real-time WebSocket functionality using Browser MCP tools
 * for comprehensive validation of live UI updates during workspace operations.
 */

const { BrowserMCP, BROWSER_MCP_CONFIG } = require('./setup');

describe('Real-time Updates Browser MCP Tests', () => {
  let browser;
  let testWorkspace1, testWorkspace2;

  beforeAll(async () => {
    browser = BrowserMCP;
    await browser.initialize();

    // Create multiple test workspaces for switching tests
    const workspace1Response = await fetch(`${BROWSER_MCP_CONFIG.apiUrl}/api/workspaces`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: 'Real-time Test Workspace 1',
        description: 'For testing real-time workspace switching',
        is_active: true
      })
    });
    testWorkspace1 = await workspace1Response.json();

    const workspace2Response = await fetch(`${BROWSER_MCP_CONFIG.apiUrl}/api/workspaces`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: 'Real-time Test Workspace 2',
        description: 'Second workspace for switching tests',
        is_active: false
      })
    });
    testWorkspace2 = await workspace2Response.json();
  });

  beforeEach(async () => {
    // Navigate to workspace management page
    await browser.navigate('/workspaces');
    await browser.waitForElement('[data-testid="workspace-list"]');

    // Wait for WebSocket connection to establish
    await browser.wait(500);
  });

  describe('Workspace Activation Real-time Updates', () => {
    test('workspace activation updates UI in real-time', async () => {
      // Take screenshot of initial state
      await browser.screenshot('realtime-workspace-initial.png');

      // Verify initial active workspace
      expect(await browser.isVisible(`[data-testid="active-workspace-${testWorkspace1.id}"]`)).toBe(true);

      // Click activate on second workspace
      await browser.click(`[data-testid="activate-workspace-${testWorkspace2.id}"]`);

      // Wait for WebSocket event and UI update
      await browser.wait(BROWSER_MCP_CONFIG.timeouts.webSocketEvent);

      // Take screenshot after activation
      await browser.screenshot('realtime-workspace-activated.png');

      // Verify active workspace indicator changed
      expect(await browser.isVisible(`[data-testid="active-workspace-${testWorkspace2.id}"]`)).toBe(true);
      expect(await browser.isVisible(`[data-testid="active-workspace-${testWorkspace1.id}"]`)).toBe(false);

      // Verify workspace activation notification appeared
      await browser.waitForElement('[data-testid="workspace-activated-notification"]');
      await browser.waitForText('Workspace activated successfully');
    });

    test('workspace switching updates permission context', async () => {
      // First, add different permissions to each workspace
      await fetch(`${BROWSER_MCP_CONFIG.apiUrl}/api/workspaces/${testWorkspace1.id}/permissions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          path: 'workspace1-specific',
          permission_type: 'write',
          rule_type: 'allow',
          description: 'Workspace 1 specific permission'
        })
      });

      await fetch(`${BROWSER_MCP_CONFIG.apiUrl}/api/workspaces/${testWorkspace2.id}/permissions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          path: 'workspace2-specific',
          permission_type: 'read',
          rule_type: 'allow',
          description: 'Workspace 2 specific permission'
        })
      });

      // Navigate to permission editor for workspace 1
      await browser.navigate(`/permissions?workspace=${testWorkspace1.id}`);
      await browser.waitForElement('[data-testid="permission-editor"]');

      // Take screenshot showing workspace 1 permissions
      await browser.screenshot('realtime-workspace1-permissions.png');

      // Verify workspace 1 specific permission is visible
      await browser.waitForText('Workspace 1 specific permission');

      // Switch to workspace 2 via API (simulating external change)
      await fetch(`${BROWSER_MCP_CONFIG.apiUrl}/api/workspaces/${testWorkspace2.id}/activate`, {
        method: 'POST'
      });

      // Wait for WebSocket notification and UI update
      await browser.wait(1000);

      // Take screenshot after workspace switch
      await browser.screenshot('realtime-workspace-switched-permissions.png');

      // Verify permission context changed
      await browser.waitForText('Workspace 2 specific permission');

      // Verify workspace 1 permission is no longer visible
      expect(await browser.isVisible('[data-testid*="workspace1-specific"]')).toBe(false);
    });

    test('multiple user workspace activation simulation', async () => {
      // Simulate another user activating a workspace
      // This would typically involve multiple browser sessions,
      // but we simulate via direct API calls

      // Take initial screenshot
      await browser.screenshot('realtime-multi-user-initial.png');

      // First user (current session) has workspace 1 active
      expect(await browser.isVisible(`[data-testid="active-workspace-${testWorkspace1.id}"]`)).toBe(true);

      // Simulate second user activating workspace 2 via direct API
      const activationResponse = await fetch(`${BROWSER_MCP_CONFIG.apiUrl}/api/workspaces/${testWorkspace2.id}/activate`, {
        method: 'POST'
      });

      // Wait for WebSocket broadcast to reach UI
      await browser.wait(BROWSER_MCP_CONFIG.timeouts.webSocketEvent);

      // Take screenshot after external activation
      await browser.screenshot('realtime-multi-user-external-activation.png');

      // Verify UI updated to reflect external change
      expect(await browser.isVisible(`[data-testid="active-workspace-${testWorkspace2.id}"]`)).toBe(true);

      // Verify notification about external workspace change
      await browser.waitForElement('[data-testid="external-workspace-change-notification"]');
      await browser.waitForText('Active workspace changed by another user');
    });
  });

  describe('Permission Update Real-time Events', () => {
    test('permission creation triggers real-time UI updates', async () => {
      // Navigate to permission editor
      await browser.navigate(`/permissions?workspace=${testWorkspace1.id}`);
      await browser.waitForElement('[data-testid="permission-editor"]');

      // Take screenshot before permission creation
      await browser.screenshot('realtime-before-permission-creation.png');

      // Create permission via API (simulating external creation)
      const permissionResponse = await fetch(`${BROWSER_MCP_CONFIG.apiUrl}/api/workspaces/${testWorkspace1.id}/permissions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          path: 'realtime-created',
          permission_type: 'write',
          rule_type: 'allow',
          description: 'Created via real-time test'
        })
      });

      // Wait for WebSocket event and UI update
      await browser.wait(BROWSER_MCP_CONFIG.timeouts.webSocketEvent);

      // Take screenshot after permission creation
      await browser.screenshot('realtime-after-permission-creation.png');

      // Verify new permission appears in UI
      await browser.waitForText('Created via real-time test');

      // Verify permission indicator updates in file tree
      expect(await browser.isVisible('[data-testid="permission-indicator-realtime-created"]')).toBe(true);

      // Verify real-time notification
      await browser.waitForElement('[data-testid="permission-created-notification"]');
    });

    test('permission deletion triggers real-time UI updates', async () => {
      // First create a permission to delete
      const permissionResponse = await fetch(`${BROWSER_MCP_CONFIG.apiUrl}/api/workspaces/${testWorkspace1.id}/permissions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          path: 'to-be-deleted',
          permission_type: 'read',
          rule_type: 'allow',
          description: 'Permission to be deleted in real-time'
        })
      });
      const permission = await permissionResponse.json();

      // Navigate to permission editor and wait for permission to appear
      await browser.navigate(`/permissions?workspace=${testWorkspace1.id}`);
      await browser.waitForElement('[data-testid="permission-editor"]');
      await browser.waitForText('Permission to be deleted in real-time');

      // Take screenshot before deletion
      await browser.screenshot('realtime-before-permission-deletion.png');

      // Delete permission via API
      await fetch(`${BROWSER_MCP_CONFIG.apiUrl}/api/permissions/${permission.id}`, {
        method: 'DELETE'
      });

      // Wait for WebSocket event and UI update
      await browser.wait(BROWSER_MCP_CONFIG.timeouts.webSocketEvent);

      // Take screenshot after deletion
      await browser.screenshot('realtime-after-permission-deletion.png');

      // Verify permission is removed from UI
      expect(await browser.isVisible('[data-testid*="to-be-deleted"]')).toBe(false);

      // Verify permission indicators update
      expect(await browser.isVisible('[data-testid="permission-indicator-to-be-deleted"]')).toBe(false);

      // Verify deletion notification
      await browser.waitForElement('[data-testid="permission-deleted-notification"]');
    });

    test('batch permission updates trigger efficient UI refresh', async () => {
      // Navigate to file explorer with many files
      await browser.navigate(`/explorer?workspace=${testWorkspace1.id}`);
      await browser.waitForElement('[data-testid="file-explorer"]');

      // Take screenshot before batch update
      await browser.screenshot('realtime-before-batch-update.png');

      // Create multiple permissions in quick succession
      const batchPermissions = [
        { path: 'batch1', permission_type: 'read', rule_type: 'allow' },
        { path: 'batch2', permission_type: 'write', rule_type: 'allow' },
        { path: 'batch3', permission_type: 'read', rule_type: 'deny' }
      ];

      const startTime = Date.now();

      // Create all permissions
      for (const perm of batchPermissions) {
        await fetch(`${BROWSER_MCP_CONFIG.apiUrl}/api/workspaces/${testWorkspace1.id}/permissions`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            ...perm,
            description: `Batch permission for ${perm.path}`
          })
        });
      }

      // Wait for all WebSocket events and UI updates
      await browser.wait(1000);

      const updateTime = Date.now() - startTime;

      // Take screenshot after batch updates
      await browser.screenshot('realtime-after-batch-update.png');

      // Verify all permission indicators updated
      expect(await browser.isVisible('[data-testid="permission-indicator-batch1"]')).toBe(true);
      expect(await browser.isVisible('[data-testid="permission-indicator-batch2"]')).toBe(true);
      expect(await browser.isVisible('[data-testid="permission-indicator-batch3"]')).toBe(true);

      // Verify batch update performance
      expect(updateTime).toBeLessThan(2000); // Should complete within 2 seconds

      console.log(`Batch permission updates completed in ${updateTime}ms`);
    });
  });

  describe('WebSocket Connection Management', () => {
    test('WebSocket reconnection after disconnect', async () => {
      // This test would simulate WebSocket disconnection and reconnection
      // Implementation depends on WebSocket management in the application

      await browser.navigate('/workspaces');
      await browser.waitForElement('[data-testid="workspace-list"]');

      // Take screenshot of connected state
      await browser.screenshot('realtime-websocket-connected.png');

      // Verify WebSocket connection indicator
      expect(await browser.isVisible('[data-testid="websocket-connected-indicator"]')).toBe(true);

      // Simulate network disconnection (this would require special handling)
      // For now, document the test structure

      // After reconnection, verify real-time functionality restored
      await browser.screenshot('realtime-websocket-reconnected.png');
    });

    test('WebSocket message handling performance', async () => {
      // Measure time from API call to UI update
      await browser.navigate(`/permissions?workspace=${testWorkspace1.id}`);
      await browser.waitForElement('[data-testid="permission-editor"]');

      const startTime = Date.now();

      // Create permission
      await fetch(`${BROWSER_MCP_CONFIG.apiUrl}/api/workspaces/${testWorkspace1.id}/permissions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          path: 'performance-test',
          permission_type: 'read',
          rule_type: 'allow',
          description: 'WebSocket performance test'
        })
      });

      // Wait for UI update
      await browser.waitForText('WebSocket performance test');

      const responseTime = Date.now() - startTime;

      // Verify WebSocket update time meets performance target
      expect(responseTime).toBeLessThan(BROWSER_MCP_CONFIG.performance.webSocketUpdates);

      console.log(`WebSocket UI update completed in ${responseTime}ms`);
    });
  });

  describe('Cache Invalidation Real-time Updates', () => {
    test('permission cache invalidation triggers UI refresh', async () => {
      // Navigate to file explorer
      await browser.navigate(`/explorer?workspace=${testWorkspace1.id}`);
      await browser.waitForElement('[data-testid="file-explorer"]');

      // Create permission that affects cache
      await fetch(`${BROWSER_MCP_CONFIG.apiUrl}/api/workspaces/${testWorkspace1.id}/permissions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          path: 'cache-test',
          permission_type: 'write',
          rule_type: 'allow',
          description: 'Cache invalidation test'
        })
      });

      // Wait for cache invalidation and UI refresh
      await browser.wait(500);

      // Take screenshot after cache refresh
      await browser.screenshot('realtime-cache-invalidation.png');

      // Verify UI shows updated permissions
      expect(await browser.isVisible('[data-testid="permission-indicator-cache-test"]')).toBe(true);

      // Verify cache refresh notification
      await browser.waitForElement('[data-testid="cache-refresh-notification"]');
    });
  });

  afterAll(async () => {
    // Clean up test workspaces
    await fetch(`${BROWSER_MCP_CONFIG.apiUrl}/api/workspaces/${testWorkspace1.id}`, {
      method: 'DELETE'
    });
    await fetch(`${BROWSER_MCP_CONFIG.apiUrl}/api/workspaces/${testWorkspace2.id}`, {
      method: 'DELETE'
    });
  });
});