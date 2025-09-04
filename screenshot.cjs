const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: false });
  const page = await browser.newPage();
  
  // Navigate to the frontend
  await page.goto('http://localhost:3004');
  
  // Wait for the page to load
  await page.waitForTimeout(2000);
  
  // Take a screenshot
  await page.screenshot({ path: 'mcp-frontend-screenshot.png', fullPage: true });
  console.log('Screenshot saved as mcp-frontend-screenshot.png');
  
  // Keep browser open for a moment to see the page
  await page.waitForTimeout(3000);
  
  await browser.close();
})();