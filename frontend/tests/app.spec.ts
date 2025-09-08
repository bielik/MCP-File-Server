import { test, expect } from '@playwright/test';

test.describe('MCP Research File Server Frontend', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the home page
    await page.goto('/');
    
    // Wait for the page to load
    await page.waitForLoadState('networkidle');
  });

  test('loads the main page and takes screenshots', async ({ page }) => {
    // Verify the page loads
    await expect(page).toHaveTitle(/MCP Research File Server/);
    
    // Take a screenshot of the main page
    await page.screenshot({ 
      path: './screenshots/main-page.png', 
      fullPage: true 
    });
    
    // Check if main elements are visible
    const header = page.locator('header, .header, h1').first();
    await expect(header).toBeVisible();
    
    // Look for file explorer or list components
    const fileArea = page.locator('[class*="file"], [class*="explorer"], [class*="list"]').first();
    if (await fileArea.isVisible()) {
      await page.screenshot({ 
        path: './screenshots/file-explorer.png',
        clip: await fileArea.boundingBox() 
      });
    }
  });

  test('tests search functionality', async ({ page }) => {
    // Look for search input
    const searchInput = page.locator('input[type="search"], input[placeholder*="search" i], input[placeholder*="filter" i]');
    
    if (await searchInput.count() > 0) {
      await searchInput.first().fill('test');
      await page.keyboard.press('Enter');
      
      // Wait for search results
      await page.waitForTimeout(1000);
      
      // Take screenshot of search results
      await page.screenshot({ 
        path: './screenshots/search-results.png', 
        fullPage: true 
      });
    }
  });

  test('tests navigation and UI components', async ({ page }) => {
    // Test any buttons or navigation elements
    const buttons = page.locator('button');
    const buttonCount = await buttons.count();
    
    if (buttonCount > 0) {
      // Take screenshot showing buttons
      await page.screenshot({ 
        path: './screenshots/ui-components.png', 
        fullPage: true 
      });
      
      // Try clicking a safe button (not delete or destructive actions)
      const safeButtons = buttons.filter({ hasText: /create|new|add|view|sort|filter/i });
      const safeButtonCount = await safeButtons.count();
      
      if (safeButtonCount > 0) {
        await safeButtons.first().click();
        await page.waitForTimeout(500);
        
        // Take screenshot after interaction
        await page.screenshot({ 
          path: './screenshots/after-interaction.png', 
          fullPage: true 
        });
      }
    }
  });

  test('checks responsive design', async ({ page }) => {
    // Test desktop view
    await page.setViewportSize({ width: 1200, height: 800 });
    await page.screenshot({ 
      path: './screenshots/desktop-view.png', 
      fullPage: true 
    });
    
    // Test tablet view
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.screenshot({ 
      path: './screenshots/tablet-view.png', 
      fullPage: true 
    });
    
    // Test mobile view
    await page.setViewportSize({ width: 375, height: 667 });
    await page.screenshot({ 
      path: './screenshots/mobile-view.png', 
      fullPage: true 
    });
  });

  test('tests backend connectivity', async ({ page, request }) => {
    // Test if backend is accessible through the frontend
    try {
      // Try to make API calls through the frontend's proxy
      const configResponse = await request.get('/api/config');
      const filesResponse = await request.get('/api/files');
      
      console.log('Config API Status:', configResponse.status());
      console.log('Files API Status:', filesResponse.status());
      
      // Take screenshot regardless of API status
      await page.screenshot({ 
        path: './screenshots/connectivity-test.png', 
        fullPage: true 
      });
      
      // At least one API should be working
      const hasWorkingAPI = configResponse.ok() || filesResponse.ok();
      expect(hasWorkingAPI).toBeTruthy();
      
    } catch (error) {
      console.log('API connectivity test failed:', error);
      // Still take screenshot to show current state
      await page.screenshot({ 
        path: './screenshots/api-error-state.png', 
        fullPage: true 
      });
    }
  });

  test('checks for common UI elements', async ({ page }) => {
    // Check for common file manager elements
    const commonElements = [
      'input', 'button', 'table', 'div[class*="grid"]', 
      'div[class*="list"]', 'div[class*="card"]'
    ];
    
    for (const selector of commonElements) {
      const elements = page.locator(selector);
      const count = await elements.count();
      console.log(`Found ${count} ${selector} elements`);
    }
    
    // Take a comprehensive screenshot
    await page.screenshot({ 
      path: './screenshots/ui-elements-overview.png', 
      fullPage: true 
    });
    
    // Verify basic page structure
    const body = page.locator('body');
    await expect(body).toBeVisible();
  });
});