#!/usr/bin/env tsx

/**
 * One-Time Model Download Script
 * This script initializes the AiService to trigger the download and caching
 * of the required M-CLIP model from Hugging Face.
 */

import { aiService } from '../backend/src/services/AiService.js';
import { logWithContext } from '../backend/src/utils/logger.js';

async function downloadModels() {
  console.log('🚀 Starting AI model download...');
  console.log('This is a one-time setup and may take several minutes depending on your internet connection.');
  console.log('Model: sentence-transformers/clip-ViT-B-32-multilingual-v1 (~500MB)');
  console.log('');
  
  try {
    await aiService.initialize();
    console.log('\n✅ All AI models downloaded and cached successfully!');
    console.log('You can now start the server with: npm run dev');
    logWithContext.info('Model download script completed successfully');
    process.exit(0);
  } catch (error) {
    console.error('\n❌ Model download failed:', error);
    logWithContext.error('Model download script failed', error as Error);
    process.exit(1);
  }
}

downloadModels();