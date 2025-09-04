#!/usr/bin/env node
/**
 * Initialize Qdrant collections for MCP Research File Server
 */

import { QdrantVectorStore } from './qdrant-client.js';

async function setupQdrantCollections() {
  console.log('🚀 Setting up Qdrant collections...');
  
  const vectorStore = new QdrantVectorStore();
  
  try {
    // Health check first
    const isHealthy = await vectorStore.healthCheck();
    if (!isHealthy) {
      throw new Error('Qdrant is not accessible at http://localhost:6333');
    }
    
    console.log('✅ Qdrant is healthy and accessible');
    
    // Initialize all collections
    await vectorStore.initializeCollections();
    
    // Get collection info
    const info = await vectorStore.getCollectionInfo();
    console.log('📊 Collection information:');
    console.log(JSON.stringify(info, null, 2));
    
    console.log('🎉 Qdrant setup completed successfully!');
    
  } catch (error) {
    console.error('❌ Failed to set up Qdrant collections:', error);
    process.exit(1);
  }
}

// Run setup if called directly
if (import.meta.url === `file://${process.argv[1]}`) {
  setupQdrantCollections();
}

export { setupQdrantCollections };