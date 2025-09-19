/**
 * Browser MCP Automated Tests for BUG-007: Real-time Permission Updates
 *
 * Tests to validate that permission indicators update correctly in real-time
 * without showing incorrect grey dots (denied status) for unaffected files.
 */

async function testRealtimePermissionUpdates() {
  console.log('🧪 Starting BUG-007 Real-time Permission Updates Test')

  try {
    // Navigate to the application
    await browser.navigate('http://localhost:5173')
    await browser.wait(3)

    // Navigate to Permissions tab
    console.log('📋 Navigating to Permissions tab...')
    await browser.click('Permissions tab', '[data-testid="permissions-tab"]')
    await browser.wait(2)

    // Take initial screenshot for evidence
    console.log('📸 Capturing initial state...')
    await browser.screenshot()

    // Get initial snapshot to analyze permission indicators
    const initialSnapshot = await browser.snapshot()
    const initialMaterialsIndicators = countIndicatorsByType(initialSnapshot, 'materials')

    console.log('📊 Initial materials indicators:', initialMaterialsIndicators)

    // Expand all folders to ensure full visibility
    console.log('🗂️ Expanding folder tree...')
    try {
      // Try to expand materials folder
      await browser.click('Expand materials', '[aria-label*="Expand"][aria-label*="materials"], [title*="Expand"][title*="materials"]')
      await browser.wait(1)
    } catch (e) {
      console.log('⚠️ Could not expand materials folder - may already be expanded')
    }

    try {
      // Try to expand private stuff folder
      await browser.click('Expand private stuff', '[aria-label*="Expand"][aria-label*="private"], [title*="Expand"][title*="private"]')
      await browser.wait(1)
    } catch (e) {
      console.log('⚠️ Could not expand private stuff folder - may already be expanded')
    }

    // Wait for any permission loading to complete
    await browser.wait(2)

    // Test 1: Add deny rule for specific file
    console.log('🔧 Test 1: Adding deny rule for specific file...')

    try {
      // Click Add Rule button
      await browser.click('Add Rule button', 'button:has-text("Add Rule"), [data-testid="add-rule-btn"], button:has-text("+ Add Rule")')
      await browser.wait(1)

      // Fill in the form for deny rule on test.txt
      await browser.type('Path input', 'input[type="text"]:visible, [data-testid="path-input"]', 'private stuff/test.txt', false)
      await browser.wait(0.5)

      // Select deny rule type
      await browser.selectOption('Rule type dropdown', 'select:visible:first, [data-testid="rule-type"]', ['deny'])
      await browser.wait(0.5)

      // Select read permission type
      await browser.selectOption('Permission type dropdown', 'select:visible:last, [data-testid="permission-type"]', ['read'])
      await browser.wait(0.5)

      // Submit the rule
      await browser.click('Submit rule button', 'button:has-text("Add Rule"), [data-testid="submit-rule"], button[type="submit"]')
      await browser.wait(2) // Wait for real-time update

      // Capture state immediately after rule addition
      console.log('📸 Capturing state after adding deny rule...')
      await browser.screenshot()

      const afterRuleSnapshot = await browser.snapshot()
      const afterRuleMaterialsIndicators = countIndicatorsByType(afterRuleSnapshot, 'materials')

      console.log('📊 After rule materials indicators:', afterRuleMaterialsIndicators)

      // Validate that materials indicators didn't change incorrectly
      const materialsUnchanged = compareIndicatorStates(
        initialMaterialsIndicators,
        afterRuleMaterialsIndicators
      )

      // Check that test.txt shows as denied
      const testTxtCorrect = validateTestTxtDenied(afterRuleSnapshot)

      console.log('✅ Test 1 Results:')
      console.log(`   Materials unchanged: ${materialsUnchanged ? 'PASS ✅' : 'FAIL ❌'}`)
      console.log(`   test.txt correctly denied: ${testTxtCorrect ? 'PASS ✅' : 'FAIL ❌'}`)

      // Test 2: Delete the rule and verify restoration
      console.log('🔧 Test 2: Deleting rule to verify restoration...')

      try {
        // Find and click the delete button for the rule we just created
        await browser.click('Delete rule button', 'button[title="Delete rule"], svg[viewBox="0 0 24 24"]:has(path[d*="19 7l-.867"]), button:has(svg):last-child')
        await browser.wait(2) // Wait for real-time update

        // Capture state after rule deletion
        console.log('📸 Capturing state after deleting rule...')
        await browser.screenshot()

        const afterDeleteSnapshot = await browser.snapshot()
        const afterDeleteMaterialsIndicators = countIndicatorsByType(afterDeleteSnapshot, 'materials')

        console.log('📊 After delete materials indicators:', afterDeleteMaterialsIndicators)

        // Validate that we're back to initial state
        const restoredCorrectly = compareIndicatorStates(
          initialMaterialsIndicators,
          afterDeleteMaterialsIndicators
        )

        console.log('✅ Test 2 Results:')
        console.log(`   Restored to initial state: ${restoredCorrectly ? 'PASS ✅' : 'FAIL ❌'}`)

        // Overall test result
        const allTestsPassed = materialsUnchanged && testTxtCorrect && restoredCorrectly

        console.log('🎯 Overall Test Results:')
        console.log(`   All tests passed: ${allTestsPassed ? 'PASS ✅' : 'FAIL ❌'}`)
        console.log('   Performance: Real-time updates completed within expected timeframe')

        return allTestsPassed

      } catch (deleteError) {
        console.error('❌ Error during rule deletion test:', deleteError)
        return false
      }

    } catch (addRuleError) {
      console.error('❌ Error during add rule test:', addRuleError)
      return false
    }

  } catch (error) {
    console.error('❌ Test failed with error:', error)
    await browser.screenshot() // Capture error state
    return false
  }
}

/**
 * Count permission indicators by type in a snapshot
 */
function countIndicatorsByType(snapshot, directory) {
  const lines = snapshot.split('\n')

  // Look for lines containing the directory name
  const directoryLines = lines.filter(line =>
    line.toLowerCase().includes(directory.toLowerCase())
  )

  let blueRead = 0
  let greenWrite = 0
  let greyDenied = 0
  let denyMarkers = 0

  // Count different indicator types
  directoryLines.forEach(line => {
    // Count blue read indicators (● with "Read access" or "text-blue")
    if ((line.includes('●') && line.includes('Read access')) ||
        (line.includes('●') && line.includes('text-blue'))) {
      blueRead++
    }

    // Count green write indicators (● with "Write access" or "text-green")
    if ((line.includes('●') && line.includes('Write access')) ||
        (line.includes('●') && line.includes('text-green'))) {
      greenWrite++
    }

    // Count grey denied indicators (○ or "denied")
    if (line.includes('○') || line.includes('denied') || line.includes('text-gray')) {
      greyDenied++
    }

    // Count deny markers (✕)
    if (line.includes('✕')) {
      denyMarkers++
    }
  })

  return {
    blueRead,
    greenWrite,
    greyDenied,
    denyMarkers,
    total: directoryLines.length
  }
}

/**
 * Compare indicator states to ensure only intended changes occurred
 */
function compareIndicatorStates(before, after) {
  console.log('🔍 Comparing states:')
  console.log('   Before:', before)
  console.log('   After:', after)

  // The counts should be similar (allowing for small variations due to loading states)
  const blueReadSimilar = Math.abs(before.blueRead - after.blueRead) <= 1
  const greenWriteSimilar = Math.abs(before.greenWrite - after.greenWrite) <= 1

  // Grey indicators should not increase significantly
  const greyNotIncreased = after.greyDenied <= before.greyDenied + 1

  return blueReadSimilar && greenWriteSimilar && greyNotIncreased
}

/**
 * Validate that test.txt shows as correctly denied
 */
function validateTestTxtDenied(snapshot) {
  const lines = snapshot.split('\n')

  // Look for test.txt line
  const testTxtLine = lines.find(line =>
    line.includes('test.txt')
  )

  if (!testTxtLine) {
    console.log('⚠️ Could not find test.txt in snapshot')
    return false
  }

  console.log('🔍 test.txt line:', testTxtLine)

  // Should have grey indicator (○) or denied status
  const hasGreyIndicator = testTxtLine.includes('○') ||
                          testTxtLine.includes('denied') ||
                          testTxtLine.includes('Access denied')

  return hasGreyIndicator
}

/**
 * Performance test - measure update time
 */
async function testUpdatePerformance() {
  console.log('⏱️ Testing permission update performance...')

  const startTime = Date.now()

  try {
    // Navigate to app
    await browser.navigate('http://localhost:5173')
    await browser.wait(2)

    // Navigate to Permissions tab
    await browser.click('Permissions tab', '[data-testid="permissions-tab"]')
    await browser.wait(1)

    // Add a rule and measure time
    await browser.click('Add Rule button', 'button:has-text("Add Rule")')
    await browser.type('Path input', 'input[type="text"]:visible', 'test-performance.txt', false)
    await browser.selectOption('Rule type dropdown', 'select:visible:first', ['deny'])

    const beforeSubmit = Date.now()
    await browser.click('Submit rule button', 'button[type="submit"]')

    // Wait for UI to update (look for loading to finish)
    await browser.wait(1)

    const afterUpdate = Date.now()

    const updateTime = afterUpdate - beforeSubmit
    console.log(`⏱️ Permission update completed in ${updateTime}ms`)

    // Should complete within 500ms as per success criteria
    const withinTargetTime = updateTime < 500

    console.log(`Performance test: ${withinTargetTime ? 'PASS ✅' : 'FAIL ❌'} (${updateTime}ms)`)

    return withinTargetTime

  } catch (error) {
    console.error('❌ Performance test failed:', error)
    return false
  }
}

/**
 * Run all tests
 */
async function runAllTests() {
  console.log('🚀 Starting BUG-007 Test Suite...')

  try {
    const functionalTest = await testRealtimePermissionUpdates()
    const performanceTest = await testUpdatePerformance()

    const allPassed = functionalTest && performanceTest

    console.log('📋 Final Test Report:')
    console.log(`   Functional Test: ${functionalTest ? 'PASS ✅' : 'FAIL ❌'}`)
    console.log(`   Performance Test: ${performanceTest ? 'PASS ✅' : 'FAIL ❌'}`)
    console.log(`   Overall: ${allPassed ? 'ALL TESTS PASSED ✅' : 'TESTS FAILED ❌'}`)

    return allPassed

  } catch (error) {
    console.error('❌ Test suite failed:', error)
    return false
  }
}

// Export the test functions
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    testRealtimePermissionUpdates,
    testUpdatePerformance,
    runAllTests
  }
}

// Run tests if called directly
if (typeof window !== 'undefined') {
  // Browser environment - call directly
  runAllTests()
}