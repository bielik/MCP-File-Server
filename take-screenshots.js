import { chromium } from 'playwright';

async function takeScreenshots() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 }
  });
  const page = await context.newPage();

  try {
    console.log('🔍 Taking screenshots of the MCP File Server UI...');
    
    // Navigate to the frontend
    await page.goto('http://localhost:3004', { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000); // Wait for any loading states
    
    // Take screenshot of main File Explorer view
    await page.screenshot({ 
      path: 'ui-screenshot-file-explorer.png',
      fullPage: true
    });
    console.log('📸 File Explorer screenshot saved: ui-screenshot-file-explorer.png');
    
    // Click Configuration tab and wait for visual changes
    try {
      console.log('📂 Starting on File Explorer tab');
      
      // Click Configuration tab using the exact selector
      await page.click('#root > div > header > div > div > div.flex.items-center.space-x-4 > div.flex.items-center.space-x-2 > button.px-3.py-1.rounded.text-sm.text-gray-600.hover\\:text-gray-800');
      console.log('🖱️ Clicked Configuration tab using CSS selector');
      
      // Wait for the tab to become active (visual change)
      await page.waitForFunction(() => {
        const buttons = Array.from(document.querySelectorAll('button'));
        const configTab = buttons.find(btn => btn.textContent?.includes('Configuration'));
        return configTab && configTab.classList.contains('bg-blue-600');
      }, { timeout: 3000 });
      
      await page.waitForTimeout(2000); // Wait for any content loading
      console.log('✅ Configuration tab is now active');
      
      // Check if content actually changed by looking for the absence of file explorer content
      const hasFileExplorerContent = await page.$('text=Browse and assign MCP permissions to files and folders');
      if (!hasFileExplorerContent) {
        console.log('✅ Configuration content is different from File Explorer');
      } else {
        console.log('⚠️ Content appears similar - Configuration tab may show same view');
      }
      
    } catch (error) {
      console.log('⚠️ Configuration tab interaction failed:', error.message);
      
      // Fallback: just take screenshot after clicking, even if content doesn't change
      try {
        await page.click('#root > div > header > div > div > div.flex.items-center.space-x-4 > div.flex.items-center.space-x-2 > button.px-3.py-1.rounded.text-sm.text-gray-600.hover\\:text-gray-800');
        await page.waitForTimeout(2000);
        console.log('🔄 Used fallback approach - clicked Configuration and waited');
      } catch (fallbackError) {
        console.log('❌ Even fallback Configuration click failed');
      }
    }
    
    // Take screenshot of Configuration view
    await page.screenshot({ 
      path: 'ui-screenshot-configuration.png',
      fullPage: true 
    });
    console.log('📸 Configuration screenshot saved: ui-screenshot-configuration.png');
    
    // Check if there are any error messages or issues
    const errorElements = await page.$$('.error, .alert-error, [class*="error"], [class*="warning"]');
    if (errorElements.length > 0) {
      console.log(`⚠️  Found ${errorElements.length} potential error/warning elements`);
    }
    
    // Check if clear embeddings button is visible
    const clearButton = await page.$('text=Clear All Embeddings');
    if (clearButton) {
      console.log('✅ Clear embeddings button found');
    } else {
      console.log('❌ Clear embeddings button NOT found');
    }
    
    console.log('✅ Screenshots completed successfully');
    
  } catch (error) {
    console.error('❌ Error taking screenshots:', error.message);
  } finally {
    await browser.close();
  }
}

takeScreenshots();