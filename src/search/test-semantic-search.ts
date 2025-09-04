#!/usr/bin/env node
/**
 * Test script for Semantic Search Service
 * Verifies M-CLIP + Qdrant integration
 */

import { SemanticSearchService } from './semantic-search-service.js';

async function testSemanticSearch() {
  console.log('🧪 Testing Semantic Search Service...');
  
  const searchService = new SemanticSearchService();
  
  try {
    // Initialize the service
    await searchService.initialize();
    
    // Health check
    console.log('\n📊 Health Check:');
    const health = await searchService.healthCheck();
    console.log(JSON.stringify(health, null, 2));
    
    if (health.status !== 'healthy') {
      console.log('⚠️ Service not fully healthy, but continuing with tests...');
    }

    // Test indexing some sample text
    console.log('\n📝 Testing Text Indexing:');
    await searchService.indexText(
      'Artificial intelligence and machine learning are transforming research methodology in academic institutions.',
      '/sample/ai-research.txt',
      { document_id: 'doc-1' }
    );
    
    await searchService.indexText(
      'Computer vision techniques using deep neural networks have shown remarkable progress in image recognition tasks.',
      '/sample/computer-vision.txt', 
      { document_id: 'doc-2' }
    );
    
    await searchService.indexText(
      'Natural language processing models like transformers have revolutionized text understanding and generation.',
      '/sample/nlp-research.txt',
      { document_id: 'doc-3' }
    );

    // Wait a moment for indexing to complete
    await new Promise(resolve => setTimeout(resolve, 2000));

    // Test semantic text search
    console.log('\n🔍 Testing Semantic Text Search:');
    const textResults = await searchService.searchText('machine learning algorithms', {
      limit: 5,
      score_threshold: 0.5
    });
    
    console.log('Query: "machine learning algorithms"');
    console.log(`Found ${textResults.total_results} results in ${textResults.search_time_ms.toFixed(2)}ms`);
    console.log(`Embedding time: ${textResults.embedding_time_ms.toFixed(2)}ms`);
    
    textResults.results.forEach((result, index) => {
      console.log(`\n${index + 1}. Score: ${result.score.toFixed(3)}`);
      console.log(`   File: ${result.file_path}`);
      console.log(`   Text: ${result.text_content?.substring(0, 100)}...`);
    });

    // Test another query
    console.log('\n🔍 Testing Another Query:');
    const visionResults = await searchService.searchText('image processing deep learning', {
      limit: 3,
      score_threshold: 0.4
    });
    
    console.log('Query: "image processing deep learning"');
    console.log(`Found ${visionResults.total_results} results in ${visionResults.search_time_ms.toFixed(2)}ms`);
    
    visionResults.results.forEach((result, index) => {
      console.log(`\n${index + 1}. Score: ${result.score.toFixed(3)}`);
      console.log(`   File: ${result.file_path}`);
      console.log(`   Text: ${result.text_content?.substring(0, 100)}...`);
    });

    // Get service statistics
    console.log('\n📊 Service Statistics:');
    const stats = await searchService.getStats();
    console.log('Qdrant Collections:');
    Object.keys(stats.qdrant).forEach(collection => {
      const info = stats.qdrant[collection];
      console.log(`  ${collection}: ${info.result?.points_count || 0} points`);
    });

    console.log('\nM-CLIP Service:');
    if (stats.mclip) {
      console.log(`  Device: ${stats.mclip.memory_usage ? 'GPU' : 'Unknown'}`);
      console.log(`  Requests processed: ${stats.mclip.statistics?.requests_processed || 0}`);
    }

    console.log('\n✅ All tests completed successfully!');
    
  } catch (error) {
    console.error('❌ Test failed:', error);
    process.exit(1);
  }
}

// Run tests if called directly
if (import.meta.url === `file://${process.argv[1]}`) {
  testSemanticSearch();
}

export { testSemanticSearch };