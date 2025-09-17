/**
 * Browser MCP Tests for Permission Inspector
 *
 * Tests the permission inspector tooltip and modal functionality
 * using Browser MCP tools for comprehensive visual and interaction testing.
 */

const { BrowserMCP, BROWSER_MCP_CONFIG } = require('./setup');

describe('Permission Inspector Browser MCP Tests', () => {
  let browser;
  let testWorkspace;

  beforeAll(async () => {
    browser = BrowserMCP;
    await browser.initialize();

    // Create test workspace with complex permission structure
    const workspaceResponse = await fetch(`${BROWSER_MCP_CONFIG.apiUrl}/api/workspaces`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: 'Permission Inspector Test Workspace',
        description: 'For testing permission inspector functionality',
        is_active: true
      })
    });
    testWorkspace = await workspaceResponse.json();

    // Create complex permission structure for testing
    const permissions = [
      {
        path: 'documents',
        permission_type: 'read',
        rule_type: 'allow',
        description: 'General document access for team members'
      },
      {
        path: 'documents/confidential',
        permission_type: 'read',
        rule_type: 'deny',
        description: 'Confidential documents - manager approval required'
      },
      {
        path: 'code',
        permission_type: 'write',
        rule_type: 'allow',
        description: 'Full code repository access for developers'
      },
      {
        path: 'projects/webapp',
        permission_type: 'write',
        rule_type: 'allow',
        description: 'Web application development access'
      }
    ];

    for (const perm of permissions) {
      await fetch(`${BROWSER_MCP_CONFIG.apiUrl}/api/workspaces/${testWorkspace.id}/permissions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(perm)
      });
    }
  });

  beforeEach(async () => {
    // Navigate to file explorer or permission editor with inspector
    await browser.navigate(`/explorer?workspace=${testWorkspace.id}`);
    await browser.waitForElement('[data-testid="file-explorer"]');

    // Wait for permission indicators to load
    await browser.wait(500);
  });

  describe('Tooltip Display Testing', () => {
    test('permission tooltip appears on hover', async () => {
      // Find a file with permission indicator
      await browser.waitForElement('[data-testid="permission-indicator-read"]');

      // Hover over permission indicator
      await browser.hover('[data-testid="permission-indicator-read"]');

      // Wait for tooltip to appear
      await browser.waitForElement('[data-testid="permission-tooltip"]');

      // Take screenshot of tooltip
      await browser.screenshot('permission-inspector-tooltip-display.png');

      // Verify tooltip is visible
      expect(await browser.isVisible('[data-testid="permission-tooltip"]')).toBe(true);

      // Verify tooltip contains permission information
      expect(await browser.isVisible('[data-testid="tooltip-permission-type"]')).toBe(true);
      expect(await browser.isVisible('[data-testid="tooltip-rule-type"]')).toBe(true);
    });

    test('tooltip shows correct permission details', async () => {
      // Hover over a specific permission indicator
      await browser.hover('[data-testid="file-item-documents/readme.md"] [data-testid="permission-indicator"]');

      // Wait for tooltip
      await browser.waitForElement('[data-testid="permission-tooltip"]');

      // Take screenshot of detailed tooltip
      await browser.screenshot('permission-inspector-tooltip-details.png');

      // Verify tooltip shows correct information
      await browser.waitForText('read access');
      await browser.waitForText('General document access');

      // Verify rule source information
      expect(await browser.isVisible('[data-testid="tooltip-rule-path"]')).toBe(true);
      expect(await browser.isVisible('[data-testid="tooltip-rule-description"]')).toBe(true);
    });

    test('tooltip disappears on mouse leave', async () => {
      // Show tooltip first
      await browser.hover('[data-testid="permission-indicator-read"]');
      await browser.waitForElement('[data-testid="permission-tooltip"]');

      // Move mouse away
      await browser.hover('[data-testid="file-explorer"]');

      // Wait for tooltip to disappear
      await browser.wait(300);

      // Take screenshot showing tooltip is gone
      await browser.screenshot('permission-inspector-tooltip-hidden.png');

      // Verify tooltip is no longer visible
      expect(await browser.isVisible('[data-testid="permission-tooltip"]')).toBe(false);
    });
  });

  describe('Modal Display Testing', () => {
    test('permission modal opens on click', async () => {
      // Click on permission indicator to open modal
      await browser.click('[data-testid="permission-indicator-write"]');

      // Wait for modal to appear
      await browser.waitForElement('[data-testid="permission-inspector-modal"]');

      // Take screenshot of modal
      await browser.screenshot('permission-inspector-modal-open.png');

      // Verify modal elements are visible
      expect(await browser.isVisible('[data-testid="modal-title"]')).toBe(true);
      expect(await browser.isVisible('[data-testid="modal-permission-details"]')).toBe(true);
      expect(await browser.isVisible('[data-testid="modal-matched-rule"]')).toBe(true);
      expect(await browser.isVisible('[data-testid="modal-close-button"]')).toBe(true);
    });

    test('modal shows comprehensive permission information', async () => {
      // Click on a file with complex permission rules
      await browser.click('[data-testid="file-item-documents/confidential/secret.pdf"] [data-testid="permission-indicator"]');

      // Wait for modal
      await browser.waitForElement('[data-testid="permission-inspector-modal"]');

      // Take screenshot of detailed modal
      await browser.screenshot('permission-inspector-modal-detailed.png');

      // Verify comprehensive information is displayed
      await browser.waitForText('Access Denied');
      await browser.waitForText('documents/confidential');
      await browser.waitForText('Confidential documents - manager approval required');

      // Verify rule precedence explanation
      expect(await browser.isVisible('[data-testid="precedence-explanation"]')).toBe(true);
      expect(await browser.isVisible('[data-testid="rule-hierarchy"]')).toBe(true);
    });

    test('modal shows rule hierarchy for complex permissions', async () => {
      // Click on a file that has multiple overlapping rules
      await browser.click('[data-testid="file-item-code/webapp/main.py"] [data-testid="permission-indicator"]');

      // Wait for modal
      await browser.waitForElement('[data-testid="permission-inspector-modal"]');

      // Take screenshot of rule hierarchy
      await browser.screenshot('permission-inspector-rule-hierarchy.png');

      // Verify rule hierarchy section
      expect(await browser.isVisible('[data-testid="rule-hierarchy"]')).toBe(true);
      expect(await browser.isVisible('[data-testid="matching-rules-list"]')).toBe(true);

      // Verify precedence explanation
      await browser.waitForText('Most specific rule applies');
      await browser.waitForText('Write permission includes read access');
    });

    test('modal closes properly', async () => {
      // Open modal
      await browser.click('[data-testid="permission-indicator-read"]');
      await browser.waitForElement('[data-testid="permission-inspector-modal"]');

      // Click close button
      await browser.click('[data-testid="modal-close-button"]');

      // Wait for modal to close
      await browser.wait(300);

      // Take screenshot showing modal is closed
      await browser.screenshot('permission-inspector-modal-closed.png');

      // Verify modal is no longer visible
      expect(await browser.isVisible('[data-testid="permission-inspector-modal"]')).toBe(false);
    });

    test('modal closes on backdrop click', async () => {
      // Open modal
      await browser.click('[data-testid="permission-indicator-write"]');
      await browser.waitForElement('[data-testid="permission-inspector-modal"]');

      // Click on modal backdrop
      await browser.click('[data-testid="modal-backdrop"]');

      // Wait for modal to close
      await browser.wait(300);

      // Verify modal is closed
      expect(await browser.isVisible('[data-testid="permission-inspector-modal"]')).toBe(false);
    });
  });

  describe('Rule Explanation Testing', () => {
    test('permission precedence visualization', async () => {
      // Click on a file with deny rule that overrides allow rule
      await browser.click('[data-testid="file-item-documents/confidential/data.xlsx"] [data-testid="permission-indicator"]');

      // Wait for modal
      await browser.waitForElement('[data-testid="permission-inspector-modal"]');

      // Take screenshot of precedence visualization
      await browser.screenshot('permission-inspector-precedence-visualization.png');

      // Verify precedence rules are explained
      await browser.waitForText('Deny rule overrides allow rule');
      await browser.waitForText('More specific path takes precedence');

      // Verify visual indicators for rule precedence
      expect(await browser.isVisible('[data-testid="rule-precedence-arrows"]')).toBe(true);
      expect(await browser.isVisible('[data-testid="winning-rule-highlight"]')).toBe(true);
    });

    test('write permission implies read explanation', async () => {
      // Click on a file with write permission
      await browser.click('[data-testid="file-item-code/src/app.py"] [data-testid="permission-indicator"]');

      // Wait for modal
      await browser.waitForElement('[data-testid="permission-inspector-modal"]');

      // Take screenshot of write permission explanation
      await browser.screenshot('permission-inspector-write-implies-read.png');

      // Verify write permission explanation
      await browser.waitForText('Write access includes read access');
      await browser.waitForText('You can both read and modify this file');

      // Verify permission scope visualization
      expect(await browser.isVisible('[data-testid="permission-scope-diagram"]')).toBe(true);
    });

    test('no matching rule explanation', async () => {
      // Click on a file with no permissions
      await browser.click('[data-testid="file-item-unmapped/file.txt"] [data-testid="permission-indicator"]');

      // Wait for modal
      await browser.waitForElement('[data-testid="permission-inspector-modal"]');

      // Take screenshot of no permission explanation
      await browser.screenshot('permission-inspector-no-permission.png');

      // Verify no permission explanation
      await browser.waitForText('No access granted');
      await browser.waitForText('No permission rules match this path');

      // Verify suggestions for access
      expect(await browser.isVisible('[data-testid="access-request-suggestions"]')).toBe(true);
    });
  });

  describe('Copy Rule ID Functionality', () => {
    test('copy rule ID button functionality', async () => {
      // Open modal with a specific rule
      await browser.click('[data-testid="file-item-documents/readme.md"] [data-testid="permission-indicator"]');
      await browser.waitForElement('[data-testid="permission-inspector-modal"]');

      // Find and click copy rule ID button
      await browser.click('[data-testid="copy-rule-id-button"]');

      // Wait for copy confirmation
      await browser.waitForElement('[data-testid="copy-success-message"]');

      // Take screenshot of copy confirmation
      await browser.screenshot('permission-inspector-copy-rule-id.png');

      // Verify copy success message
      await browser.waitForText('Rule ID copied to clipboard');

      // Verify copy button shows success state
      expect(await browser.isVisible('[data-testid="copy-success-icon"]')).toBe(true);
    });

    test('rule ID format and content', async () => {
      // Open modal
      await browser.click('[data-testid="permission-indicator-read"]');
      await browser.waitForElement('[data-testid="permission-inspector-modal"]');

      // Verify rule ID is displayed
      expect(await browser.isVisible('[data-testid="rule-id-display"]')).toBe(true);

      // Take screenshot showing rule ID
      await browser.screenshot('permission-inspector-rule-id-display.png');

      // Verify rule ID format (should start with "db-rule-")
      await browser.waitForText('db-rule-');

      // Verify rule ID is selectable for manual copy
      expect(await browser.isVisible('[data-testid="selectable-rule-id"]')).toBe(true);
    });
  });

  describe('Performance and Responsiveness', () => {
    test('tooltip appears within performance threshold', async () => {
      const startTime = Date.now();

      // Hover to trigger tooltip
      await browser.hover('[data-testid="permission-indicator-read"]');
      await browser.waitForElement('[data-testid="permission-tooltip"]');

      const tooltipTime = Date.now() - startTime;

      // Verify tooltip appears quickly
      expect(tooltipTime).toBeLessThan(200); // 200ms threshold

      console.log(`Permission tooltip appeared in ${tooltipTime}ms`);
    });

    test('modal opens within performance threshold', async () => {
      const startTime = Date.now();

      // Click to open modal
      await browser.click('[data-testid="permission-indicator-write"]');
      await browser.waitForElement('[data-testid="permission-inspector-modal"]');

      const modalTime = Date.now() - startTime;

      // Verify modal opens quickly
      expect(modalTime).toBeLessThan(300); // 300ms threshold

      console.log(`Permission modal opened in ${modalTime}ms`);
    });

    test('batch permission data loads efficiently', async () => {
      // Navigate to page with many files
      await browser.navigate(`/explorer?workspace=${testWorkspace.id}&path=large-directory`);

      const startTime = Date.now();

      // Wait for all permission indicators to load
      await browser.waitForElement('[data-testid="permission-indicators-loaded"]');

      const loadTime = Date.now() - startTime;

      // Verify batch loading performance
      expect(loadTime).toBeLessThan(1000); // 1 second for large directory

      console.log(`Batch permission indicators loaded in ${loadTime}ms`);
    });
  });

  afterAll(async () => {
    // Clean up test workspace
    await fetch(`${BROWSER_MCP_CONFIG.apiUrl}/api/workspaces/${testWorkspace.id}`, {
      method: 'DELETE'
    });
  });
});