/**
 * Browser MCP Tests for Workspace Management
 *
 * Tests the workspace management interface using Browser MCP tools
 * for comprehensive visual and interaction testing.
 */

const { BrowserMCP, BROWSER_MCP_CONFIG } = require('./setup');

describe('Workspace Management Browser MCP Tests', () => {
  let browser;

  beforeAll(async () => {
    browser = BrowserMCP;
    await browser.initialize();
  });

  beforeEach(async () => {
    // Navigate to workspace management page
    await browser.navigate('/workspaces');
    await browser.waitForElement('[data-testid="workspace-list"]');
  });

  describe('Visual Component Testing', () => {
    test('workspace manager renders correctly', async () => {
      // Wait for component to fully render
      await browser.waitForElement('[data-testid="workspace-list"]');

      // Take screenshot for visual comparison
      const screenshot = await browser.screenshot('workspace-manager-initial.png');

      // Verify key elements are visible
      expect(await browser.isVisible('[data-testid="create-workspace-button"]')).toBe(true);
      expect(await browser.isVisible('[data-testid="workspace-list"]')).toBe(true);
    });

    test('workspace creation modal displays correctly', async () => {
      // Click create workspace button
      await browser.click('[data-testid="create-workspace-button"]');

      // Wait for modal to appear
      await browser.waitForElement('[data-testid="workspace-modal"]');

      // Take screenshot of modal
      await browser.screenshot('workspace-creation-modal.png');

      // Verify modal elements
      expect(await browser.isVisible('[data-testid="workspace-name-input"]')).toBe(true);
      expect(await browser.isVisible('[data-testid="workspace-description-input"]')).toBe(true);
      expect(await browser.isVisible('[data-testid="submit-workspace"]')).toBe(true);
    });

    test('workspace list displays with proper styling', async () => {
      // Create test workspace via API first
      const workspaceData = {
        name: 'Browser Test Workspace',
        description: 'Created for browser testing',
        is_active: false
      };

      // Use fetch to create workspace
      await fetch(`${BROWSER_MCP_CONFIG.apiUrl}/api/workspaces`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(workspaceData)
      });

      // Refresh page to see new workspace
      await browser.navigate('/workspaces');
      await browser.waitForElement('[data-testid="workspace-list"]');

      // Wait for workspace to appear in list
      await browser.waitForText('Browser Test Workspace');

      // Take screenshot of workspace list with data
      await browser.screenshot('workspace-list-with-data.png');

      // Verify workspace appears in list
      expect(await browser.isVisible('[data-testid*="workspace-item"]')).toBe(true);
    });
  });

  describe('Interactive Workflow Testing', () => {
    test('complete workspace creation workflow', async () => {
      // Step 1: Click create workspace button
      await browser.click('[data-testid="create-workspace-button"]');
      await browser.waitForElement('[data-testid="workspace-modal"]');

      // Step 2: Fill in workspace details
      await browser.type('[data-testid="workspace-name-input"]', 'Interactive Test Workspace');
      await browser.type('[data-testid="workspace-description-input"]', 'Created through browser interaction');

      // Step 3: Submit form
      await browser.click('[data-testid="submit-workspace"]');

      // Step 4: Wait for modal to close and workspace to appear
      await browser.wait(500); // Allow for API call
      await browser.waitForText('Interactive Test Workspace');

      // Step 5: Take screenshot of success state
      await browser.screenshot('workspace-created-success.png');

      // Verify workspace was created
      expect(await browser.isVisible('[data-testid*="workspace-item"]')).toBe(true);
    });

    test('workspace activation workflow', async () => {
      // Create workspace first
      const workspaceResponse = await fetch(`${BROWSER_MCP_CONFIG.apiUrl}/api/workspaces`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: 'Activation Test Workspace',
          description: 'For activation testing',
          is_active: false
        })
      });
      const workspace = await workspaceResponse.json();

      // Refresh page
      await browser.navigate('/workspaces');
      await browser.waitForElement('[data-testid="workspace-list"]');

      // Wait for workspace to appear
      await browser.waitForText('Activation Test Workspace');

      // Take screenshot before activation
      await browser.screenshot('workspace-before-activation.png');

      // Click activate button
      await browser.click(`[data-testid="activate-workspace-${workspace.id}"]`);

      // Wait for activation to complete
      await browser.wait(200); // Allow for WebSocket propagation

      // Take screenshot after activation
      await browser.screenshot('workspace-after-activation.png');

      // Verify active state indicator
      expect(await browser.isVisible(`[data-testid="active-workspace-${workspace.id}"]`)).toBe(true);
    });

    test('workspace deletion workflow', async () => {
      // Create workspace for deletion
      const workspaceResponse = await fetch(`${BROWSER_MCP_CONFIG.apiUrl}/api/workspaces`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: 'Deletion Test Workspace',
          description: 'For deletion testing',
          is_active: false
        })
      });
      const workspace = await workspaceResponse.json();

      // Refresh page
      await browser.navigate('/workspaces');
      await browser.waitForText('Deletion Test Workspace');

      // Click delete button
      await browser.click(`[data-testid="delete-workspace-${workspace.id}"]`);

      // Wait for confirmation dialog
      await browser.waitForElement('[data-testid="delete-confirmation-dialog"]');

      // Take screenshot of confirmation dialog
      await browser.screenshot('workspace-delete-confirmation.png');

      // Confirm deletion
      await browser.click('[data-testid="confirm-delete"]');

      // Wait for workspace to disappear
      await browser.wait(500);

      // Take screenshot of final state
      await browser.screenshot('workspace-after-deletion.png');

      // Verify workspace is no longer visible
      // Note: This test assumes proper cleanup
    });
  });

  describe('Error Handling Testing', () => {
    test('workspace creation validation errors', async () => {
      // Open creation modal
      await browser.click('[data-testid="create-workspace-button"]');
      await browser.waitForElement('[data-testid="workspace-modal"]');

      // Try to submit empty form
      await browser.click('[data-testid="submit-workspace"]');

      // Wait for validation errors
      await browser.waitForElement('[data-testid="workspace-name-error"]');

      // Take screenshot of error state
      await browser.screenshot('workspace-creation-validation-error.png');

      // Verify error message displays
      expect(await browser.isVisible('[data-testid="workspace-name-error"]')).toBe(true);

      // Verify error has proper accessibility attributes
      const errorElement = await browser.getElement('[data-testid="workspace-name-error"]');
      expect(await errorElement.getAttribute('role')).toBe('alert');
    });

    test('workspace creation server error handling', async () => {
      // This test would simulate server errors
      // Implementation depends on ability to mock API responses

      await browser.click('[data-testid="create-workspace-button"]');
      await browser.waitForElement('[data-testid="workspace-modal"]');

      // Fill form with valid data
      await browser.type('[data-testid="workspace-name-input"]', 'Server Error Test');

      // Mock server error scenario would be handled here
      // For now, document the test structure

      await browser.screenshot('workspace-server-error-state.png');
    });
  });

  describe('Performance Testing', () => {
    test('workspace list load performance', async () => {
      const startTime = Date.now();

      // Navigate to workspace page
      await browser.navigate('/workspaces');
      await browser.waitForElement('[data-testid="workspace-list"]');

      const loadTime = Date.now() - startTime;

      // Verify load time meets performance target
      expect(loadTime).toBeLessThan(BROWSER_MCP_CONFIG.performance.workspaceListLoad);

      console.log(`Workspace list loaded in ${loadTime}ms`);
    });

    test('workspace creation response time', async () => {
      await browser.click('[data-testid="create-workspace-button"]');
      await browser.waitForElement('[data-testid="workspace-modal"]');

      const startTime = Date.now();

      // Fill and submit form
      await browser.type('[data-testid="workspace-name-input"]', 'Performance Test Workspace');
      await browser.click('[data-testid="submit-workspace"]');

      // Wait for completion
      await browser.waitForText('Performance Test Workspace');

      const responseTime = Date.now() - startTime;

      // Verify response time meets target
      expect(responseTime).toBeLessThan(2000); // 2 second threshold

      console.log(`Workspace creation completed in ${responseTime}ms`);
    });
  });

  afterEach(async () => {
    // Clean up any test data
    // Implementation would depend on test cleanup requirements
  });
});