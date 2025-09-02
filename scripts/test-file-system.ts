#!/usr/bin/env tsx

import fs from 'fs/promises';
import path from 'path';
import { validateFileSystemConfiguration, filePermissionManager } from '../src/files/index.js';
import { config, getAbsolutePath } from '../src/config/index.js';
import { logWithContext } from '../src/utils/logger.js';

async function testFileSystemPermissions(): Promise<void> {
  console.log('🧪 Testing File System Permissions\n');

  try {
    // 1. Validate configuration
    console.log('📋 Validating Configuration...');
    const validation = await validateFileSystemConfiguration();
    
    if (validation.valid) {
      console.log('✅ Configuration is valid');
    } else {
      console.log('❌ Configuration issues found:');
      validation.issues.forEach(issue => console.log(`   - ${issue}`));
      console.log('\n💡 Recommendations:');
      validation.recommendations.forEach(rec => console.log(`   - ${rec}`));
      return;
    }

    // 2. Test permission checking
    console.log('\n🔒 Testing Permission System...');
    
    const matrix = filePermissionManager.getPermissionMatrix();
    
    // Test context folders (read-only)
    if (matrix.contextFolders.length > 0) {
      console.log('\n📂 Context Folders (Read-Only):');
      for (const folder of matrix.contextFolders) {
        const absolutePath = getAbsolutePath(folder);
        const { permission, allowed } = filePermissionManager.getFilePermission(absolutePath);
        console.log(`   ${allowed ? '✅' : '❌'} ${folder} - Permission: ${permission}`);
      }
    }

    // Test working folders (read-write)
    if (matrix.workingFolders.length > 0) {
      console.log('\n📝 Working Folders (Read-Write):');
      for (const folder of matrix.workingFolders) {
        const absolutePath = getAbsolutePath(folder);
        const { permission, allowed } = filePermissionManager.getFilePermission(absolutePath);
        console.log(`   ${allowed ? '✅' : '❌'} ${folder} - Permission: ${permission}`);
      }
    }

    // Test output folder (agent-controlled)
    if (matrix.outputFolder) {
      console.log('\n🤖 Output Folder (Agent-Controlled):');
      const absolutePath = getAbsolutePath(matrix.outputFolder);
      const { permission, allowed } = filePermissionManager.getFilePermission(absolutePath);
      console.log(`   ${allowed ? '✅' : '❌'} ${matrix.outputFolder} - Permission: ${permission}`);
    }

    // 3. Test file operations
    console.log('\n📁 Testing File Operations...');
    
    const outputPath = getAbsolutePath(matrix.outputFolder);
    const testDir = path.join(outputPath, 'test-operations');
    const testFile = path.join(testDir, 'test.md');

    try {
      // Create test directory
      await fs.mkdir(testDir, { recursive: true });
      console.log('✅ Created test directory');

      // Test file creation
      const testContent = '# Test File\n\nThis is a test file created by the MCP server.';
      await fs.writeFile(testFile, testContent);
      console.log('✅ Created test file');

      // Test permission check on created file
      const { permission: testFilePermission, allowed: testFileAllowed } = 
        filePermissionManager.getFilePermission(testFile);
      console.log(`✅ Test file permission: ${testFilePermission} (${testFileAllowed ? 'allowed' : 'denied'})`);

      // Test file reading
      const readContent = await fs.readFile(testFile, 'utf-8');
      const readSuccess = readContent === testContent;
      console.log(`${readSuccess ? '✅' : '❌'} Read test file`);

      // Test subdirectory creation
      const subDir = path.join(testDir, 'subdirectory');
      await fs.mkdir(subDir, { recursive: true });
      console.log('✅ Created subdirectory');

      // Cleanup test files
      await fs.rm(testDir, { recursive: true, force: true });
      console.log('✅ Cleaned up test files');

    } catch (error) {
      console.log(`❌ File operations test failed: ${(error as Error).message}`);
    }

    // 4. Test file listing
    console.log('\n📋 Testing File Listing...');
    try {
      const allFiles = await filePermissionManager.getAllowedFiles({ recursive: true });
      console.log(`✅ Found ${allFiles.length} accessible files`);
      
      const filesByPermission = {
        'read-only': allFiles.filter(f => f.permissions === 'read-only').length,
        'read-write': allFiles.filter(f => f.permissions === 'read-write').length,
        'agent-controlled': allFiles.filter(f => f.permissions === 'agent-controlled').length,
      };
      
      console.log(`   - Read-only: ${filesByPermission['read-only']}`);
      console.log(`   - Read-write: ${filesByPermission['read-write']}`);
      console.log(`   - Agent-controlled: ${filesByPermission['agent-controlled']}`);

    } catch (error) {
      console.log(`❌ File listing test failed: ${(error as Error).message}`);
    }

    // 5. Test usage statistics
    console.log('\n📊 Getting Usage Statistics...');
    try {
      const stats = await filePermissionManager.getUsageStats();
      console.log(`✅ Statistics retrieved:`);
      console.log(`   - Context files: ${stats.contextFiles}`);
      console.log(`   - Working files: ${stats.workingFiles}`);
      console.log(`   - Output files: ${stats.outputFiles}`);
      console.log(`   - Total size: ${(stats.totalSize / 1024 / 1024).toFixed(2)} MB`);

    } catch (error) {
      console.log(`❌ Statistics test failed: ${(error as Error).message}`);
    }

    console.log('\n✅ File system testing completed successfully!');

  } catch (error) {
    console.error('❌ File system test failed:', error);
    process.exit(1);
  }
}

async function createSampleFiles(): Promise<void> {
  console.log('\n📝 Creating Sample Files for Testing...');

  try {
    const matrix = filePermissionManager.getPermissionMatrix();
    
    // Create sample files in output directory
    if (matrix.outputFolder) {
      const outputPath = getAbsolutePath(matrix.outputFolder);
      const samplesDir = path.join(outputPath, 'samples');
      
      await fs.mkdir(samplesDir, { recursive: true });
      
      // Create sample markdown files
      const samples = [
        {
          name: 'methodology-draft.md',
          content: `# Methodology Draft

## Research Approach
This document outlines our proposed methodology for the research project.

## Data Collection
- Survey design
- Interview protocols
- Observation guidelines

## Analysis Plan
Statistical analysis will be conducted using R and Python.
`,
        },
        {
          name: 'literature-review.md',
          content: `# Literature Review

## Introduction
This literature review examines the current state of research in our field.

## Key Studies
- Study 1: Important findings
- Study 2: Methodological insights
- Study 3: Theoretical contributions

## Research Gaps
Several gaps in the literature have been identified.
`,
        },
        {
          name: 'budget-notes.md',
          content: `# Budget Planning

## Personnel Costs
- Principal Investigator: 50% effort
- Research Assistant: 100% effort
- Consultant: 10 hours

## Equipment
- Computer hardware: $2,000
- Software licenses: $500
- Lab equipment: $5,000

## Travel
- Conference presentation: $1,500
- Data collection travel: $1,000
`,
        },
      ];
      
      for (const sample of samples) {
        const filePath = path.join(samplesDir, sample.name);
        await fs.writeFile(filePath, sample.content);
        console.log(`✅ Created sample file: ${sample.name}`);
      }
      
      // Create subfolder structure
      const subfolders = ['methodology', 'analysis', 'drafts'];
      for (const folder of subfolders) {
        const folderPath = path.join(samplesDir, folder);
        await fs.mkdir(folderPath, { recursive: true });
        
        // Create a README in each subfolder
        const readmePath = path.join(folderPath, 'README.md');
        const readmeContent = `# ${folder.charAt(0).toUpperCase() + folder.slice(1)}

This folder contains files related to ${folder}.
`;
        await fs.writeFile(readmePath, readmeContent);
        console.log(`✅ Created subfolder: ${folder}/`);
      }
      
      console.log(`✅ Sample files created in: ${samplesDir}`);
    }
    
  } catch (error) {
    console.error('❌ Failed to create sample files:', error);
  }
}

async function main(): Promise<void> {
  const args = process.argv.slice(2);
  
  if (args.includes('--create-samples')) {
    await createSampleFiles();
  }
  
  await testFileSystemPermissions();
}

// Run if called directly
if (import.meta.url === `file://${process.argv[1]}`) {
  main().catch(error => {
    console.error('Test failed:', error);
    process.exit(1);
  });
}