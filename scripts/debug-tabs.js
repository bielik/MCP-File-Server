import { chromium } from 'playwright';

async function debugTabs() {
  const browser = await chromium.launch({ headless: false }); // Run visible to see what happens
  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 }
  });
  const page = await context.newPage();

  try {
    console.log('🔍 Debugging tab navigation...');
    
    // Navigate to the frontend
    await page.goto(`http://localhost:${process.env.FRONTEND_PORT || 3004}`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);
    
    // Log all available tabs/buttons
    const buttons = await page.$$eval('button, a, [role="tab"]', els => 
      els.map(el => ({
        text: el.textContent?.trim(),
        classes: el.className,
        id: el.id,
        href: el.href,
        role: el.getAttribute('role')
      }))
    );
    console.log('🔘 Available clickable elements:', buttons.filter(b => b.text?.includes('Config') || b.text?.includes('File')));
    
    // Check current URL and page content
    console.log('🌐 Current URL:', page.url());
    
    // Get current page title/heading
    const heading = await page.$eval('h1, h2, .title, [class*="title"]', el => el.textContent?.trim()).catch(() => 'No heading found');
    console.log('📄 Current page heading:', heading);
    
    // Try to click Configuration and see what happens
    console.log('🖱️ Clicking Configuration tab...');
    await page.click('text=Configuration');
    await page.waitForTimeout(2000);
    
    // Check if URL changed
    console.log('🌐 URL after click:', page.url());
    
    // Check if content changed
    const newHeading = await page.$eval('h1, h2, .title, [class*="title"]', el => el.textContent?.trim()).catch(() => 'No heading found');
    console.log('📄 New page heading:', newHeading);
    
    // Get some unique text from the page
    const pageText = await page.evaluate(() => document.body.textContent?.substring(0, 500));
    console.log('📝 Current page content preview:', pageText?.substring(0, 200) + '...');
    
    // Take screenshot for manual inspection
    await page.screenshot({ 
      path: 'debug-after-config-click.png',
      fullPage: true
    });
    console.log('📸 Debug screenshot saved: debug-after-config-click.png');
    
    // Wait a bit to see the state
    await page.waitForTimeout(3000);
    
  } catch (error) {
    console.error('❌ Debug error:', error.message);
  } finally {
    await browser.close();
  }
}

debugTabs();