#!/usr/bin/env node

/**
 * Standalone Model Download Script
 * Downloads the M-CLIP model for the AI service
 */

import { pipeline, env } from '@xenova/transformers';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Configure cache directory
env.cacheDir = path.resolve(__dirname, './backend/models/mclip');

async function downloadModels() {
  console.log('🚀 Starting AI model download...');
  console.log('This is a one-time setup and may take several minutes depending on your internet connection.');
  console.log('Model: Xenova/clip-vit-base-patch32 (ONNX-compatible CLIP model)');
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
      'Xenova/clip-vit-base-patch32',
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