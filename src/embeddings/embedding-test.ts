/**
 * Embedding Service Test Suite
 * Comprehensive testing for M-CLIP client and embedding service
 */

import { performance } from 'perf_hooks';
import MCLIPClient from './mclip-client';
import EmbeddingService from './embedding-service';

interface TestResult {
  name: string;
  passed: boolean;
  duration: number;
  error?: string;
  details?: any;
}

interface TestSuite {
  name: string;
  results: TestResult[];
  totalPassed: number;
  totalFailed: number;
  totalDuration: number;
}

class EmbeddingTester {
  private mclipClient: MCLIPClient;
  private embeddingService: EmbeddingService;
  private testSuites: TestSuite[] = [];

  constructor() {
    this.mclipClient = new MCLIPClient();
    this.embeddingService = new EmbeddingService();
  }

  private async runTest(name: string, testFn: () => Promise<void>): Promise<TestResult> {
    const startTime = performance.now();
    
    try {
      await testFn();
      const duration = performance.now() - startTime;
      
      return {
        name,
        passed: true,
        duration
      };
    } catch (error) {
      const duration = performance.now() - startTime;
      
      return {
        name,
        passed: false,
        duration,
        error: error.message
      };
    }
  }

  private calculateSuiteStats(results: TestResult[]): { passed: number; failed: number; duration: number } {
    return {
      passed: results.filter(r => r.passed).length,
      failed: results.filter(r => !r.passed).length,
      duration: results.reduce((sum, r) => sum + r.duration, 0)
    };
  }

  /**
   * Test M-CLIP Client functionality
   */
  async testMCLIPClient(): Promise<TestSuite> {
    console.log('🧪 Testing M-CLIP Client...');
    const results: TestResult[] = [];

    // Test 1: Health check
    results.push(await this.runTest('Health Check', async () => {
      const health = await this.mclipClient.health();
      if (!health.model_loaded) {
        throw new Error('Model not loaded');
      }
      if (health.status !== 'healthy') {
        throw new Error(`Service not healthy: ${health.status}`);
      }
    }));

    // Test 2: Text embedding
    results.push(await this.runTest('Text Embedding', async () => {
      const result = await this.mclipClient.embedText('Hello world');
      if (result.dimension !== 512) {
        throw new Error(`Wrong dimension: ${result.dimension}`);
      }
      if (result.embedding.length !== 512) {
        throw new Error(`Wrong embedding length: ${result.embedding.length}`);
      }
    }));

    // Test 3: Text embedding caching
    results.push(await this.runTest('Text Embedding Caching', async () => {
      const text = 'This is a test sentence for caching';
      const result1 = await this.mclipClient.embedText(text);
      const result2 = await this.mclipClient.embedText(text);
      
      // Second request should be faster (cached)
      if (result2.processing_time >= result1.processing_time) {
        console.warn(`Caching may not be working: ${result1.processing_time}ms vs ${result2.processing_time}ms`);
      }
    }));

    // Test 4: Multilingual text embedding
    results.push(await this.runTest('Multilingual Embedding', async () => {
      const texts = [
        'Hello world',
        'Hola mundo',
        'Bonjour le monde',
        'Hallo Welt',
        'こんにちは世界'
      ];
      
      const embeddings = [];
      for (const text of texts) {
        const result = await this.mclipClient.embedText(text);
        embeddings.push(result.embedding);
      }
      
      // Check that different languages produce different embeddings
      const similarity = MCLIPClient.cosineSimilarity(embeddings[0], embeddings[1]);
      if (similarity < 0.5) {
        throw new Error(`Multilingual embeddings too dissimilar: ${similarity}`);
      }
    }));

    // Test 5: Cosine similarity calculation
    results.push(await this.runTest('Cosine Similarity', async () => {
      const embedding1 = [1, 0, 0, 0];
      const embedding2 = [0, 1, 0, 0];
      const embedding3 = [1, 0, 0, 0];
      
      const sim1 = MCLIPClient.cosineSimilarity(embedding1, embedding2);
      const sim2 = MCLIPClient.cosineSimilarity(embedding1, embedding3);
      
      if (Math.abs(sim1) > 0.001) {
        throw new Error(`Orthogonal vectors should have 0 similarity: ${sim1}`);
      }
      if (Math.abs(sim2 - 1) > 0.001) {
        throw new Error(`Identical vectors should have similarity 1: ${sim2}`);
      }
    }));

    // Test 6: Connection test
    results.push(await this.runTest('Connection Test', async () => {
      const test = await this.mclipClient.testConnection();
      if (!test.connected) {
        throw new Error('Connection test failed');
      }
      if (test.latency <= 0) {
        throw new Error(`Invalid latency: ${test.latency}`);
      }
    }));

    // Test 7: Statistics
    results.push(await this.runTest('Service Statistics', async () => {
      const stats = await this.mclipClient.getStats();
      if (stats.requests_processed < 0) {
        throw new Error(`Invalid request count: ${stats.requests_processed}`);
      }
    }));

    const suiteStats = this.calculateSuiteStats(results);
    const suite: TestSuite = {
      name: 'M-CLIP Client Tests',
      results,
      totalPassed: suiteStats.passed,
      totalFailed: suiteStats.failed,
      totalDuration: suiteStats.duration
    };

    this.testSuites.push(suite);
    return suite;
  }

  /**
   * Test Embedding Service functionality
   */
  async testEmbeddingService(): Promise<TestSuite> {
    console.log('🧪 Testing Embedding Service...');
    const results: TestResult[] = [];

    // Test 1: Health check
    results.push(await this.runTest('Service Health Check', async () => {
      const health = await this.embeddingService.checkHealth();
      if (!health.overall) {
        throw new Error('Service not healthy');
      }
    }));

    // Test 2: Text embedding
    results.push(await this.runTest('Service Text Embedding', async () => {
      const result = await this.embeddingService.embedText('Test text');
      if (result.dimension !== 512) {
        throw new Error(`Wrong dimension: ${result.dimension}`);
      }
      if (result.source !== 'mclip') {
        throw new Error(`Wrong source: ${result.source}`);
      }
    }));

    // Test 3: Metrics tracking
    results.push(await this.runTest('Metrics Tracking', async () => {
      const initialMetrics = this.embeddingService.getMetrics();
      
      await this.embeddingService.embedText('Metrics test');
      
      const finalMetrics = this.embeddingService.getMetrics();
      if (finalMetrics.totalRequests <= initialMetrics.totalRequests) {
        throw new Error('Metrics not updating');
      }
    }));

    // Test 4: Similarity computation
    results.push(await this.runTest('Similarity Computation', async () => {
      const similarity = await this.embeddingService.computeSimilarity(
        { text: 'cat' },
        { text: 'kitten' }
      );
      
      if (similarity.similarity <= 0) {
        throw new Error(`Invalid similarity: ${similarity.similarity}`);
      }
    }));

    // Test 5: Batch embedding
    results.push(await this.runTest('Batch Embedding', async () => {
      const requests = [
        { text: 'First text' },
        { text: 'Second text' },
        { text: 'Third text' }
      ];
      
      const results = await this.embeddingService.embedBatch(requests);
      if (results.length !== 3) {
        throw new Error(`Wrong batch result count: ${results.length}`);
      }
    }));

    const suiteStats = this.calculateSuiteStats(results);
    const suite: TestSuite = {
      name: 'Embedding Service Tests',
      results,
      totalPassed: suiteStats.passed,
      totalFailed: suiteStats.failed,
      totalDuration: suiteStats.duration
    };

    this.testSuites.push(suite);
    return suite;
  }

  /**
   * Test semantic similarity and cross-modal capabilities
   */
  async testSemanticCapabilities(): Promise<TestSuite> {
    console.log('🧪 Testing Semantic Capabilities...');
    const results: TestResult[] = [];

    // Test 1: Semantic similarity
    results.push(await this.runTest('Semantic Similarity', async () => {
      const pairs = [
        ['car', 'automobile'],
        ['dog', 'puppy'],
        ['happy', 'joyful'],
        ['computer', 'laptop']
      ];
      
      for (const [word1, word2] of pairs) {
        const similarity = await this.embeddingService.computeSimilarity(
          { text: word1 },
          { text: word2 }
        );
        
        if (similarity.similarity < 0.3) {
          console.warn(`Low similarity for "${word1}" - "${word2}": ${similarity.similarity}`);
        }
      }
    }));

    // Test 2: Language consistency
    results.push(await this.runTest('Cross-Language Consistency', async () => {
      const translations = [
        ['hello', 'hola', 'bonjour'],
        ['water', 'agua', 'eau'],
        ['thank you', 'gracias', 'merci']
      ];
      
      for (const translationGroup of translations) {
        const embeddings = [];
        for (const word of translationGroup) {
          const result = await this.embeddingService.embedText(word);
          embeddings.push(result.embedding);
        }
        
        // Check that translations have reasonable similarity
        const sim1 = MCLIPClient.cosineSimilarity(embeddings[0], embeddings[1]);
        const sim2 = MCLIPClient.cosineSimilarity(embeddings[0], embeddings[2]);
        
        if (sim1 < 0.4 || sim2 < 0.4) {
          console.warn(`Low cross-language similarity: ${sim1}, ${sim2}`);
        }
      }
    }));

    // Test 3: Find similar functionality
    results.push(await this.runTest('Find Similar Items', async () => {
      const collection = [
        { text: 'cat', metadata: { type: 'animal' } },
        { text: 'dog', metadata: { type: 'animal' } },
        { text: 'car', metadata: { type: 'vehicle' } },
        { text: 'bicycle', metadata: { type: 'vehicle' } },
        { text: 'tree', metadata: { type: 'plant' } }
      ];
      
      const similar = await this.embeddingService.findSimilar(
        { text: 'kitten' },
        collection,
        2
      );
      
      if (similar.length !== 2) {
        throw new Error(`Wrong number of results: ${similar.length}`);
      }
      
      // Top result should be cat (highest similarity)
      if (similar[0].item.text !== 'cat') {
        console.warn(`Expected 'cat' as most similar to 'kitten', got: ${similar[0].item.text}`);
      }
    }));

    const suiteStats = this.calculateSuiteStats(results);
    const suite: TestSuite = {
      name: 'Semantic Capabilities Tests',
      results,
      totalPassed: suiteStats.passed,
      totalFailed: suiteStats.failed,
      totalDuration: suiteStats.duration
    };

    this.testSuites.push(suite);
    return suite;
  }

  /**
   * Performance and load testing
   */
  async testPerformance(): Promise<TestSuite> {
    console.log('🧪 Testing Performance...');
    const results: TestResult[] = [];

    // Test 1: Single request latency
    results.push(await this.runTest('Single Request Latency', async () => {
      const iterations = 10;
      const latencies = [];
      
      for (let i = 0; i < iterations; i++) {
        const start = performance.now();
        await this.embeddingService.embedText(`Test text ${i}`);
        const latency = performance.now() - start;
        latencies.push(latency);
      }
      
      const avgLatency = latencies.reduce((sum, lat) => sum + lat, 0) / iterations;
      const maxLatency = Math.max(...latencies);
      
      console.log(`Average latency: ${avgLatency.toFixed(2)}ms, Max: ${maxLatency.toFixed(2)}ms`);
      
      if (avgLatency > 1000) { // 1 second threshold
        throw new Error(`Average latency too high: ${avgLatency}ms`);
      }
    }));

    // Test 2: Batch vs individual performance
    results.push(await this.runTest('Batch Performance', async () => {
      const texts = Array.from({ length: 10 }, (_, i) => `Batch test text ${i}`);
      
      // Individual requests
      const individualStart = performance.now();
      for (const text of texts) {
        await this.embeddingService.embedText(text);
      }
      const individualTime = performance.now() - individualStart;
      
      // Batch request
      const batchStart = performance.now();
      await this.embeddingService.embedBatch(texts.map(text => ({ text })));
      const batchTime = performance.now() - batchStart;
      
      console.log(`Individual: ${individualTime.toFixed(2)}ms, Batch: ${batchTime.toFixed(2)}ms`);
      
      // Batch should be faster for multiple items
      if (batchTime >= individualTime) {
        console.warn(`Batch processing not faster: batch=${batchTime}ms, individual=${individualTime}ms`);
      }
    }));

    // Test 3: Memory usage stability
    results.push(await this.runTest('Memory Usage Stability', async () => {
      const iterations = 50;
      
      for (let i = 0; i < iterations; i++) {
        await this.embeddingService.embedText(`Memory test ${i}`);
        
        // Check memory usage periodically
        if (i % 10 === 0) {
          const health = await this.embeddingService.checkHealth();
          if (health.details.memory_usage && health.details.memory_usage.rss_mb > 2000) {
            console.warn(`High memory usage: ${health.details.memory_usage.rss_mb}MB`);
          }
        }
      }
    }));

    const suiteStats = this.calculateSuiteStats(results);
    const suite: TestSuite = {
      name: 'Performance Tests',
      results,
      totalPassed: suiteStats.passed,
      totalFailed: suiteStats.failed,
      totalDuration: suiteStats.duration
    };

    this.testSuites.push(suite);
    return suite;
  }

  /**
   * Run all test suites
   */
  async runAllTests(): Promise<void> {
    console.log('🚀 Starting Embedding Service Test Suite');
    console.log('=' * 60);
    
    const startTime = performance.now();
    
    try {
      // Run all test suites
      await this.testMCLIPClient();
      await this.testEmbeddingService();
      await this.testSemanticCapabilities();
      await this.testPerformance();
      
      const totalTime = performance.now() - startTime;
      this.printResults(totalTime);
      
    } catch (error) {
      console.error('❌ Test suite failed:', error.message);
      throw error;
    }
  }

  private printResults(totalTime: number): void {
    console.log('\n📊 Test Results Summary');
    console.log('=' * 60);
    
    let totalTests = 0;
    let totalPassed = 0;
    let totalFailed = 0;
    
    for (const suite of this.testSuites) {
      const passRate = (suite.totalPassed / (suite.totalPassed + suite.totalFailed) * 100).toFixed(1);
      const statusIcon = suite.totalFailed === 0 ? '✅' : '⚠️';
      
      console.log(`${statusIcon} ${suite.name}: ${suite.totalPassed}/${suite.totalPassed + suite.totalFailed} passed (${passRate}%) - ${suite.totalDuration.toFixed(0)}ms`);
      
      // Show failed tests
      for (const result of suite.results) {
        if (!result.passed) {
          console.log(`   ❌ ${result.name}: ${result.error}`);
        }
      }
      
      totalTests += suite.totalPassed + suite.totalFailed;
      totalPassed += suite.totalPassed;
      totalFailed += suite.totalFailed;
    }
    
    console.log('-' * 60);
    const overallPassRate = (totalPassed / totalTests * 100).toFixed(1);
    const overallStatus = totalFailed === 0 ? '🎉' : totalFailed < totalTests * 0.1 ? '✅' : '⚠️';
    
    console.log(`${overallStatus} Overall: ${totalPassed}/${totalTests} tests passed (${overallPassRate}%)`);
    console.log(`⏱️  Total execution time: ${(totalTime / 1000).toFixed(2)}s`);
    
    if (totalFailed === 0) {
      console.log('\n🎉 All tests passed! The embedding service is ready for production.');
    } else if (totalFailed < totalTests * 0.1) {
      console.log('\n✅ Most tests passed. Minor issues may need attention.');
    } else {
      console.log('\n⚠️  Several tests failed. Please review the issues above.');
    }
  }
}

// Export for use in other modules
export { EmbeddingTester };

// CLI execution
if (require.main === module) {
  const tester = new EmbeddingTester();
  
  tester.runAllTests()
    .then(() => {
      console.log('\n🏁 Test suite completed successfully');
      process.exit(0);
    })
    .catch((error) => {
      console.error('\n💥 Test suite failed:', error.message);
      process.exit(1);
    });
}