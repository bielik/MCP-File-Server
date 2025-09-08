#!/usr/bin/env tsx
/**
 * Test Runner for Phase 3 Step 1: Connect Existing Search to MCP Tools
 * 
 * Comprehensive test suite runner with setup, execution, and reporting
 */

import { execSync } from 'child_process';
import { existsSync, mkdirSync, writeFileSync } from 'fs';
import path from 'path';
import { performance } from 'perf_hooks';

interface TestSuiteResult {
  name: string;
  passed: boolean;
  duration: number;
  testCount: number;
  passCount: number;
  failCount: number;
  skipCount: number;
  errors?: string[];
}

class Step1TestRunner {
  private readonly testDir = path.resolve(__dirname);
  private readonly rootDir = path.resolve(__dirname, '..');
  private readonly resultsDir = path.join(this.rootDir, 'test-results');
  
  constructor() {
    // Ensure results directory exists
    if (!existsSync(this.resultsDir)) {
      mkdirSync(this.resultsDir, { recursive: true });
    }
  }

  /**
   * Run all Phase 3 Step 1 tests
   */
  async runAllTests(): Promise<void> {
    console.log('🚀 Phase 3 Step 1: Testing Search Service Integration\n');
    
    const startTime = performance.now();
    const results: TestSuiteResult[] = [];

    try {
      // Setup test environment
      await this.setupTestEnvironment();

      // Run test suites in order
      const testSuites = [
        {
          name: 'MCP Protocol Compliance',
          file: 'mcp-protocol.test.ts',
          description: 'Tests MCP request/response format compliance'
        },
        {
          name: 'Search Handler Integration', 
          file: 'handlers.test.ts',
          description: 'Tests MCP handler integration with search services'
        },
        {
          name: 'Search Service Integration',
          file: 'search-service-integration.test.ts',
          description: 'Tests SemanticSearchService and MultimodalSearchEngine'
        }
      ];

      for (const suite of testSuites) {
        console.log(`\n📋 Running ${suite.name}...`);
        console.log(`   ${suite.description}`);
        
        const result = await this.runTestSuite(suite.file);
        results.push({ ...result, name: suite.name });
        
        if (result.passed) {
          console.log(`   ✅ ${suite.name}: ${result.passCount}/${result.testCount} tests passed (${result.duration.toFixed(2)}ms)`);
        } else {
          console.log(`   ❌ ${suite.name}: ${result.failCount} failures, ${result.skipCount} skipped`);
        }
      }

      // Generate summary report
      const totalTime = performance.now() - startTime;
      await this.generateSummaryReport(results, totalTime);

      // Print final summary
      this.printSummary(results, totalTime);

    } catch (error) {
      console.error('\n❌ Test runner failed:', error);
      process.exit(1);
    }
  }

  /**
   * Setup test environment and fixtures
   */
  private async setupTestEnvironment(): Promise<void> {
    console.log('🔧 Setting up test environment...');

    // Create test fixture directories
    const fixturesDirs = [
      'tests/fixtures/context',
      'tests/fixtures/working', 
      'tests/fixtures/output',
      'tests/fixtures/models/mclip',
      'tests/logs'
    ];

    for (const dir of fixturesDirs) {
      const fullPath = path.join(this.rootDir, dir);
      if (!existsSync(fullPath)) {
        mkdirSync(fullPath, { recursive: true });
      }
    }

    // Create sample test files
    const sampleFiles = [
      {
        path: 'tests/fixtures/context/sample-doc.txt',
        content: 'Sample research document for testing semantic search functionality.'
      },
      {
        path: 'tests/fixtures/working/draft.md', 
        content: '# Research Draft\n\nThis is a test document for multimodal search testing.'
      }
    ];

    for (const file of sampleFiles) {
      const fullPath = path.join(this.rootDir, file.path);
      if (!existsSync(fullPath)) {
        writeFileSync(fullPath, file.content);
      }
    }

    console.log('   ✅ Test environment ready');
  }

  /**
   * Run a specific test suite
   */
  private async runTestSuite(testFile: string): Promise<TestSuiteResult> {
    const startTime = performance.now();
    
    try {
      // Run vitest for specific test file
      const command = `npx vitest run ${testFile} --reporter=json --no-coverage`;
      const output = execSync(command, { 
        cwd: this.rootDir,
        encoding: 'utf8',
        stdio: 'pipe'
      });

      const duration = performance.now() - startTime;
      
      // Parse vitest JSON output
      const results = this.parseVitestOutput(output);
      
      return {
        name: testFile,
        passed: results.failed === 0,
        duration,
        testCount: results.total,
        passCount: results.passed,
        failCount: results.failed,
        skipCount: results.skipped
      };

    } catch (error) {
      const duration = performance.now() - startTime;
      
      return {
        name: testFile,
        passed: false,
        duration,
        testCount: 0,
        passCount: 0,
        failCount: 1,
        skipCount: 0,
        errors: [error.message]
      };
    }
  }

  /**
   * Parse Vitest JSON output
   */
  private parseVitestOutput(output: string): any {
    try {
      // Extract JSON from vitest output
      const lines = output.split('\n');
      const jsonLine = lines.find(line => line.trim().startsWith('{'));
      
      if (jsonLine) {
        const results = JSON.parse(jsonLine);
        return {
          total: results.numTotalTests || 0,
          passed: results.numPassedTests || 0,
          failed: results.numFailedTests || 0,
          skipped: results.numPendingTests || 0
        };
      }
    } catch (error) {
      console.warn('Could not parse vitest output:', error.message);
    }

    // Fallback parsing
    return {
      total: 0,
      passed: 0,
      failed: output.includes('FAIL') ? 1 : 0,
      skipped: 0
    };
  }

  /**
   * Generate comprehensive summary report
   */
  private async generateSummaryReport(results: TestSuiteResult[], totalTime: number): Promise<void> {
    const timestamp = new Date().toISOString();
    const reportPath = path.join(this.resultsDir, `step1-test-report-${Date.now()}.json`);

    const report = {
      phase: 'Phase 3 Step 1',
      description: 'Connect Existing Search to MCP Tools',
      timestamp,
      totalDuration: totalTime,
      summary: {
        totalSuites: results.length,
        passedSuites: results.filter(r => r.passed).length,
        failedSuites: results.filter(r => !r.passed).length,
        totalTests: results.reduce((sum, r) => sum + r.testCount, 0),
        passedTests: results.reduce((sum, r) => sum + r.passCount, 0),
        failedTests: results.reduce((sum, r) => sum + r.failCount, 0),
        skippedTests: results.reduce((sum, r) => sum + r.skipCount, 0)
      },
      suites: results,
      recommendations: this.generateRecommendations(results),
      nextSteps: this.getNextSteps(results)
    };

    writeFileSync(reportPath, JSON.stringify(report, null, 2));
    console.log(`\n📊 Detailed report saved: ${reportPath}`);
  }

  /**
   * Generate recommendations based on test results
   */
  private generateRecommendations(results: TestSuiteResult[]): string[] {
    const recommendations: string[] = [];
    const failedSuites = results.filter(r => !r.passed);

    if (failedSuites.length === 0) {
      recommendations.push('✅ All tests passing! Ready to proceed with Step 1 implementation.');
      recommendations.push('🔄 Consider implementing the actual search service connections in handlers.ts');
      recommendations.push('📈 Monitor performance when connecting to real services');
    } else {
      recommendations.push('🔧 Fix failing tests before proceeding with implementation');
      
      failedSuites.forEach(suite => {
        recommendations.push(`   - Address failures in ${suite.name}`);
      });

      recommendations.push('🧪 Run tests frequently during implementation');
      recommendations.push('📝 Update tests as implementation progresses');
    }

    // Performance recommendations
    const slowSuites = results.filter(r => r.duration > 5000);
    if (slowSuites.length > 0) {
      recommendations.push('⚡ Consider optimizing slow test suites for faster feedback');
    }

    return recommendations;
  }

  /**
   * Get next steps based on test results
   */
  private getNextSteps(results: TestSuiteResult[]): string[] {
    const allPassed = results.every(r => r.passed);

    if (allPassed) {
      return [
        '1. Implement SemanticSearchService integration in handlers.ts',
        '2. Connect MultimodalSearchEngine to handleSearchMultimodal',
        '3. Add proper error handling and logging',
        '4. Test with real M-CLIP and Qdrant services',
        '5. Update tests to verify actual search functionality',
        '6. Proceed to Step 2: FlexSearch integration'
      ];
    } else {
      return [
        '1. Fix failing unit tests',
        '2. Verify test environment setup',
        '3. Check mock implementations',
        '4. Re-run tests until all pass',
        '5. Then proceed with handler implementation'
      ];
    }
  }

  /**
   * Print summary to console
   */
  private printSummary(results: TestSuiteResult[], totalTime: number): void {
    console.log('\n' + '='.repeat(60));
    console.log('📊 PHASE 3 STEP 1 TEST SUMMARY');
    console.log('='.repeat(60));
    
    const totalTests = results.reduce((sum, r) => sum + r.testCount, 0);
    const totalPassed = results.reduce((sum, r) => sum + r.passCount, 0);
    const totalFailed = results.reduce((sum, r) => sum + r.failCount, 0);
    const totalSkipped = results.reduce((sum, r) => sum + r.skipCount, 0);

    console.log(`⏱️  Total Time: ${(totalTime / 1000).toFixed(2)}s`);
    console.log(`🧪 Total Tests: ${totalTests}`);
    console.log(`✅ Passed: ${totalPassed}`);
    console.log(`❌ Failed: ${totalFailed}`);
    console.log(`⏭️  Skipped: ${totalSkipped}`);
    console.log(`📈 Success Rate: ${((totalPassed / totalTests) * 100).toFixed(1)}%`);

    if (totalFailed === 0) {
      console.log('\n🎉 All tests passed! Ready for Step 1 implementation.');
    } else {
      console.log('\n⚠️  Fix failing tests before implementing Step 1.');
      process.exit(1);
    }

    console.log('\n' + '='.repeat(60));
  }
}

// Run tests if this script is executed directly
if (require.main === module) {
  const runner = new Step1TestRunner();
  runner.runAllTests().catch(error => {
    console.error('Test runner failed:', error);
    process.exit(1);
  });
}

export { Step1TestRunner };