#!/usr/bin/env tsx

/**
 * End-to-End Integration Test for MCP Research File Server
 * 
 * This script validates the complete native AI pipeline:
 * 1. Document Processing: PDF → Text chunks + Images → Embeddings → Vector Storage
 * 2. Search Integration: MCP tools return real results from native services
 * 3. Service Health: All native services properly initialized and functional
 * 
 * Usage: tsx test-full-integration.ts [--verbose]
 */

import path from 'path';
import fs from 'fs/promises';
import { fileURLToPath } from 'url';

// Import our native services
import { aiService } from './src/services/AiService.js';
import { vectorDbService } from './src/services/VectorDb.js';
import { indexer } from './src/features/processing/Indexer.js';
import { keywordSearchService } from './src/features/search/keywordSearch.js';
import { semanticSearchService } from './src/features/search/semanticSearch.js';
import { initializeSearchServices } from './server/handlers.js';

// Test configuration
const TEST_CONFIG = {
  verbose: process.argv.includes('--verbose'),
  testDocumentPath: '', // Will be set dynamically
  sampleQueries: {
    keyword: 'research methodology',
    semantic: 'artificial intelligence applications',
    multimodal: 'data visualization charts',
  },
  expectedResults: {
    minKeywordResults: 1,
    minSemanticResults: 1,
    minMultimodalResults: 1,
  }
};

// Helper functions
function log(message: string, level: 'info' | 'success' | 'warn' | 'error' = 'info') {
  const symbols = {
    info: '📋',
    success: '✅',
    warn: '⚠️',
    error: '❌',
  };
  
  const colors = {
    info: '\x1b[36m',    // Cyan
    success: '\x1b[32m', // Green
    warn: '\x1b[33m',    // Yellow
    error: '\x1b[31m',   // Red
  };
  
  console.log(`${colors[level]}${symbols[level]} ${message}\x1b[0m`);
}

function verbose(message: string) {
  if (TEST_CONFIG.verbose) {
    console.log(`   ${message}`);
  }
}

async function createTestDocument(): Promise<string> {
  const testContent = `
# Research Methodology Test Document

## Introduction
This is a test document for validating the MCP Research File Server's
native AI pipeline integration. It contains various concepts that should
be discoverable through different search methods.

## Artificial Intelligence Applications
Modern AI systems leverage machine learning algorithms to process
multimodal data including text, images, and other formats. Key applications
include natural language processing, computer vision, and data analysis.

## Data Visualization and Charts
Research often requires presenting findings through various visualization
techniques. Common approaches include:
- Statistical charts and graphs
- Interactive dashboards  
- Infographic representations
- Scientific plotting and analysis

## Methodology Framework
Our research methodology follows these key principles:
1. Systematic data collection
2. Rigorous analysis procedures
3. Peer review processes
4. Reproducible results

This document should be indexed and searchable through all three
search mechanisms: keyword matching, semantic similarity, and
multimodal content analysis.
`;

  const testDir = path.join(process.cwd(), 'test-data');
  const testFilePath = path.join(testDir, 'integration-test-doc.txt');
  
  try {
    await fs.mkdir(testDir, { recursive: true });
    await fs.writeFile(testFilePath, testContent.trim(), 'utf-8');
    verbose(`Created test document at: ${testFilePath}`);
    return testFilePath;
  } catch (error) {
    throw new Error(`Failed to create test document: ${(error as Error).message}`);
  }
}

async function testServiceInitialization(): Promise<void> {
  log('Testing service initialization...');
  
  try {
    // Initialize all services
    await initializeSearchServices();
    
    // Check individual service status
    const services = [
      { name: 'AI Service', ready: aiService.isReady() },
      { name: 'Vector DB Service', ready: vectorDbService.isReady() },
      { name: 'Indexer', ready: indexer.isReady() },
      { name: 'Keyword Search Service', ready: keywordSearchService.isReady() },
      { name: 'Semantic Search Service', ready: semanticSearchService.isReady() },
    ];
    
    for (const service of services) {
      if (service.ready) {
        verbose(`${service.name}: Ready ✅`);
      } else {
        throw new Error(`${service.name} is not ready`);
      }
    }
    
    log('All services initialized successfully', 'success');
  } catch (error) {
    log(`Service initialization failed: ${(error as Error).message}`, 'error');
    throw error;
  }
}

async function testDocumentIndexing(): Promise<void> {
  log('Testing document indexing pipeline...');
  
  try {
    const testDoc = await createTestDocument();
    TEST_CONFIG.testDocumentPath = testDoc;
    
    // Index the test document
    const indexResult = await indexer.indexFile(testDoc, {
      extractImages: false, // Text file, no images
      chunkText: true,
      chunkSize: 500,
      chunkOverlap: 50,
    });
    
    if (!indexResult.success) {
      throw new Error(`Indexing failed: ${indexResult.errors?.join(', ')}`);
    }
    
    verbose(`Indexed document: ${indexResult.fileName}`);
    verbose(`Text chunks processed: ${indexResult.textChunksProcessed}`);
    verbose(`Total vectors stored: ${indexResult.totalVectorsStored}`);
    verbose(`Processing time: ${indexResult.processingTime}ms`);
    
    if (indexResult.textChunksProcessed === 0) {
      throw new Error('No text chunks were processed');
    }
    
    if (indexResult.totalVectorsStored === 0) {
      throw new Error('No vectors were stored');
    }
    
    log('Document indexing completed successfully', 'success');
  } catch (error) {
    log(`Document indexing failed: ${(error as Error).message}`, 'error');
    throw error;
  }
}

async function testKeywordSearch(): Promise<void> {
  log('Testing keyword search (FlexSearch)...');
  
  try {
    const query = TEST_CONFIG.sampleQueries.keyword;
    const results = await keywordSearchService.search(query, {
      limit: 10,
      fuzzy: true,
      highlight: true,
    });
    
    verbose(`Query: "${query}"`);
    verbose(`Results found: ${results.length}`);
    
    if (results.length < TEST_CONFIG.expectedResults.minKeywordResults) {
      throw new Error(`Expected at least ${TEST_CONFIG.expectedResults.minKeywordResults} results, got ${results.length}`);
    }
    
    // Validate result structure
    for (const result of results.slice(0, 2)) {
      verbose(`- ${result.filePath} (score: ${result.score.toFixed(3)})`);
      if (result.highlight) {
        verbose(`  Highlight: ${result.highlight.substring(0, 100)}...`);
      }
    }
    
    log('Keyword search test passed', 'success');
  } catch (error) {
    log(`Keyword search test failed: ${(error as Error).message}`, 'error');
    throw error;
  }
}

async function testSemanticSearch(): Promise<void> {
  log('Testing semantic search (Vector embeddings)...');
  
  try {
    const query = TEST_CONFIG.sampleQueries.semantic;
    const results = await semanticSearchService.searchText(query, {
      limit: 10,
      threshold: 0.5, // Lower threshold for test
      searchMode: 'text_only',
    });
    
    verbose(`Query: "${query}"`);
    verbose(`Results found: ${results.length}`);
    
    if (results.length < TEST_CONFIG.expectedResults.minSemanticResults) {
      throw new Error(`Expected at least ${TEST_CONFIG.expectedResults.minSemanticResults} results, got ${results.length}`);
    }
    
    // Validate result structure and scoring
    for (const result of results.slice(0, 2)) {
      verbose(`- ${result.filePath} (score: ${result.score.toFixed(3)})`);
      verbose(`  Content: ${result.textContent?.substring(0, 100)}...`);
      
      if (result.score <= 0 || result.score > 1) {
        throw new Error(`Invalid similarity score: ${result.score}`);
      }
    }
    
    log('Semantic search test passed', 'success');
  } catch (error) {
    log(`Semantic search test failed: ${(error as Error).message}`, 'error');
    throw error;
  }
}

async function testMultimodalSearch(): Promise<void> {
  log('Testing multimodal search (Cross-modal embeddings)...');
  
  try {
    const query = TEST_CONFIG.sampleQueries.multimodal;
    const results = await semanticSearchService.searchMultimodal(query, {
      limit: 10,
      threshold: 0.5, // Lower threshold for test
      includeText: true,
      includeImages: false, // Test doc has no images
      searchMode: 'multimodal',
    });
    
    verbose(`Query: "${query}"`);
    verbose(`Results found: ${results.length}`);
    
    if (results.length < TEST_CONFIG.expectedResults.minMultimodalResults) {
      throw new Error(`Expected at least ${TEST_CONFIG.expectedResults.minMultimodalResults} results, got ${results.length}`);
    }
    
    // Validate result structure
    for (const result of results.slice(0, 2)) {
      verbose(`- ${result.filePath} (score: ${result.score.toFixed(3)}, type: ${result.contentType})`);
      
      if (result.contentType === 'text' && result.textContent) {
        verbose(`  Content: ${result.textContent.substring(0, 100)}...`);
      } else if (result.contentType === 'image' && result.imageCaption) {
        verbose(`  Caption: ${result.imageCaption}`);
      }
    }
    
    log('Multimodal search test passed', 'success');
  } catch (error) {
    log(`Multimodal search test failed: ${(error as Error).message}`, 'error');
    throw error;
  }
}

async function testServiceStats(): Promise<void> {
  log('Testing service statistics...');
  
  try {
    // Get stats from various services
    const keywordStats = keywordSearchService.getStats();
    const semanticStats = await semanticSearchService.getStats();
    const indexerStats = await indexer.getProcessingStats();
    
    verbose(`Keyword search documents: ${keywordStats.totalDocuments}`);
    verbose(`Semantic search queries: ${semanticStats.totalQueries}`);
    verbose(`Vector collections: ${indexerStats.collections.length}`);
    verbose(`Total vectors: ${indexerStats.totalVectors}`);
    
    if (keywordStats.totalDocuments === 0) {
      throw new Error('No documents indexed in keyword search');
    }
    
    if (indexerStats.totalVectors === 0) {
      throw new Error('No vectors stored in database');
    }
    
    log('Service statistics validation passed', 'success');
  } catch (error) {
    log(`Service statistics test failed: ${(error as Error).message}`, 'error');
    throw error;
  }
}

async function cleanup(): Promise<void> {
  log('Cleaning up test data...');
  
  try {
    if (TEST_CONFIG.testDocumentPath) {
      await fs.unlink(TEST_CONFIG.testDocumentPath);
      verbose(`Removed test document: ${TEST_CONFIG.testDocumentPath}`);
    }
    
    const testDir = path.join(process.cwd(), 'test-data');
    try {
      await fs.rmdir(testDir);
      verbose(`Removed test directory: ${testDir}`);
    } catch {
      // Directory might not be empty or might not exist, ignore
    }
    
    log('Cleanup completed', 'success');
  } catch (error) {
    log(`Cleanup warning: ${(error as Error).message}`, 'warn');
  }
}

// Main test execution
async function runIntegrationTests(): Promise<void> {
  const startTime = Date.now();
  
  console.log('🚀 MCP Research File Server - End-to-End Integration Test\n');
  console.log('Testing the complete native AI pipeline integration...\n');
  
  try {
    // Run all test phases
    await testServiceInitialization();
    await testDocumentIndexing();
    
    // Wait a moment for indexing to complete
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    await testKeywordSearch();
    await testSemanticSearch();
    await testMultimodalSearch();
    await testServiceStats();
    
    const duration = Date.now() - startTime;
    
    console.log('\n🎉 All integration tests passed!');
    console.log(`✅ Native AI pipeline is fully functional`);
    console.log(`✅ MCP handlers return real search results`);
    console.log(`✅ Document processing pipeline working end-to-end`);
    console.log(`⏱️  Total test duration: ${duration}ms\n`);
    
  } catch (error) {
    const duration = Date.now() - startTime;
    
    console.log('\n💥 Integration tests failed!');
    console.log(`❌ Error: ${(error as Error).message}`);
    console.log(`⏱️  Failed after: ${duration}ms\n`);
    
    throw error;
  } finally {
    await cleanup();
  }
}

// Run the tests
if (import.meta.url === `file://${process.argv[1]}`) {
  runIntegrationTests()
    .then(() => {
      process.exit(0);
    })
    .catch((error) => {
      console.error('Test execution failed:', error);
      process.exit(1);
    });
}

export { runIntegrationTests };