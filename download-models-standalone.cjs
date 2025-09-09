#!/usr/bin/env node

/**
 * Standalone Model Download Script
 * Downloads the M-CLIP model for the AI service
 */

const { pipeline, env } = require('@xenova/transformers');
const path = require('path');

// Configure cache directory
env.cacheDir = path.resolve(process.cwd(), './backend/models/mclip');

async function downloadModels() {
  console.log('🚀 Starting AI model download...');
  console.log('This is a one-time setup and may take several minutes depending on your internet connection.');
  console.log('Model: sentence-transformers/clip-ViT-B-32-multilingual-v1 (~500MB)');
  console.log('Cache directory:', env.cacheDir);
  console.log('');
  
  const onProgress = (data) => {
    if (data.status === 'progress') {
      const progress = (data.progress || 0).toFixed(2);
      const downloaded = ((data.downloaded || 0) / 1024 / 1024).toFixed(2);
      const total = ((data.total || 0) / 1024 / 1024).toFixed(2);
      process.stdout.write(`  Downloading ${data.file}: ${progress}% (${downloaded}MB / ${total}MB)\r`);
    } else if (data.status === 'done') {
      process.stdout.write(`\n`);
      console.log(`✓ Downloaded ${data.file}`);
    }
  };
  
  try {
    console.log('Loading model pipeline...');
    const textPipeline = await pipeline(
      'feature-extraction',
      'sentence-transformers/clip-ViT-B-32-multilingual-v1',
      {
        revision: 'main',
        device: 'cpu',
        progress_callback: onProgress,
      }
    );
    
    console.log('\n✅ All AI models downloaded and cached successfully!');
    console.log('You can now start the server with: npm run dev');
    process.exit(0);
  } catch (error) {
    console.error('\n❌ Model download failed:', error);
    process.exit(1);
  }
}

downloadModels();