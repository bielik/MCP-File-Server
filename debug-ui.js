import { chromium } from 'playwright';

async function debugUI() {
  const browser = await chromium.launch({ headless: false }); // Run with visible browser
  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 }
  });
  const page = await context.newPage();

  try {
    console.log('🔍 Debugging MCP File Server UI navigation...');
    
    // Navigate to the frontend
    await page.goto('http://localhost:3004', { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);
    
    console.log('📄 Current page title:', await page.title());
    console.log('🔗 Current URL:', page.url());
    
    // Check for tab buttons
    const fileExplorerTab = await page.$('button:has-text("File Explorer")');
    const configTab = await page.$('button:has-text("Configuration")');
    
    console.log('🗂️ File Explorer tab found:', !!fileExplorerTab);
    console.log('⚙️ Configuration tab found:', !!configTab);
    
    if (configTab) {
      console.log('🎯 Clicking Configuration tab...');
      await configTab.click();
      await page.waitForTimeout(2000);
      
      // Check what's visible now
      const isFileExplorerVisible = await page.isVisible('h2:has-text("File Explorer")');
      const isConfigVisible = await page.isVisible('h3:has-text("Server Configuration")') || 
                             await page.isVisible('h3:has-text("File Permissions")');
      
      console.log('📁 File Explorer section visible:', isFileExplorerVisible);
      console.log('⚙️ Configuration section visible:', isConfigVisible);
      
      // Look for the clear embeddings button specifically
      const clearButton = await page.$('button:has-text("Clear All Embeddings")');
      console.log('🧹 Clear embeddings button found:', !!clearButton);
      
      // Check if there are any errors in browser console
      const consoleMessages = [];
      page.on('console', msg => consoleMessages.push(msg.text()));
      
      await page.waitForTimeout(1000);
      
      if (consoleMessages.length > 0) {
        console.log('🚨 Browser console messages:');
        consoleMessages.forEach(msg => console.log('  -', msg));
      }
      
      // Take final screenshot
      await page.screenshot({ 
        path: 'debug-after-config-click.png',
        fullPage: true 
      });
      console.log('📸 Debug screenshot saved: debug-after-config-click.png');
    }
    
    console.log('✅ Debug completed');
    
  } catch (error) {
    console.error('❌ Error during debugging:', error.message);
  } finally {
    await browser.close();
  }
}

debugUI();