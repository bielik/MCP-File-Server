import { chromium } from 'playwright';

async function debugPermissions() {
  const browser = await chromium.launch({ headless: false });
  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 }
  });
  const page = await context.newPage();

  // Listen to console messages
  page.on('console', msg => {
    if (msg.text().includes('currentPermissions') || msg.text().includes('entry.path')) {
      console.log('🐛 Browser Console:', msg.text());
    }
  });

  try {
    console.log('🔍 Debugging permission data...');
    
    await page.goto('http://localhost:3004', { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);
    
    // Inspect the permission data structure
    const permissionData = await page.evaluate(() => {
      // Try to find React state or permission data
      const app = window.React || window.__REACT_DEVTOOLS_GLOBAL_HOOK__;
      
      // Get some sample file entries and permission data
      const fileItems = Array.from(document.querySelectorAll('[class*="flex items-center py-1"]')).slice(0, 5);
      const items = fileItems.map(item => {
        const nameElement = item.querySelector('[class*="text-sm text-gray-900"]');
        const dotElement = item.querySelector('[class*="rounded-full"]');
        return {
          name: nameElement?.textContent?.trim(),
          dotClasses: dotElement?.className,
          title: dotElement?.title
        };
      });
      
      return items;
    });
    
    console.log('🗂️ File items with permission data:');
    permissionData.forEach((item, i) => {
      console.log(`${i + 1}. ${item.name}`);
      console.log(`   Dot classes: ${item.dotClasses}`);
      console.log(`   Title: ${item.title}`);
      console.log('');
    });
    
    // Hover over the Contacts folder to see tooltip
    try {
      const contactsFolder = await page.$('text=Contacts');
      if (contactsFolder) {
        await contactsFolder.hover();
        await page.waitForTimeout(1000);
        console.log('💡 Hovered over Contacts folder to show tooltip');
      }
    } catch (error) {
      console.log('⚠️ Could not hover over Contacts folder');
    }
    
    await page.waitForTimeout(3000);
    
  } catch (error) {
    console.error('❌ Debug error:', error.message);
  } finally {
    await browser.close();
  }
}

debugPermissions();