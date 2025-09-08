#!/usr/bin/env tsx
import { spawn } from 'child_process';
const PREREQUISITES = [
    {
        name: 'Poppler (pdfimages)',
        command: 'pdfimages',
        versionArgs: ['-v'],
        versionPattern: /pdfimages version (.+)/i,
        installInstructions: `
Install Poppler utilities:

Windows:
  1. Download from: https://blog.alivate.com.au/poppler-windows/
  2. Extract and add to PATH, or use chocolatey: choco install poppler
  3. Verify with: pdfimages -v

macOS:
  brew install poppler

Ubuntu/Debian:
  sudo apt-get install poppler-utils

Other Linux:
  Check your package manager for 'poppler-utils' or 'poppler'
    `,
        required: true,
    }
];
/**
 * Execute a command and return stdout/stderr
 */
async function executeCommand(command, args, timeout = 5000) {
    return new Promise((resolve) => {
        const child = spawn(command, args, {
            stdio: ['ignore', 'pipe', 'pipe'],
            shell: true
        });
        let stdout = '';
        let stderr = '';
        const timer = setTimeout(() => {
            child.kill('SIGTERM');
            resolve({ stdout, stderr: stderr + ' (timeout)', code: -1 });
        }, timeout);
        child.stdout?.on('data', (data) => {
            stdout += data.toString();
        });
        child.stderr?.on('data', (data) => {
            stderr += data.toString();
        });
        child.on('close', (code) => {
            clearTimeout(timer);
            resolve({ stdout, stderr, code });
        });
        child.on('error', (error) => {
            clearTimeout(timer);
            resolve({ stdout, stderr: error.message, code: -1 });
        });
    });
}
/**
 * Check if a single prerequisite is available
 */
async function checkPrerequisite(prereq) {
    const result = {
        name: prereq.name,
        command: prereq.command,
        available: false,
        installInstructions: prereq.installInstructions,
    };
    try {
        console.log(`Checking ${prereq.name}...`);
        const { stdout, stderr, code } = await executeCommand(prereq.command, prereq.versionArgs);
        if (code === 0 || stdout || stderr) {
            // Some commands output version to stderr instead of stdout
            const output = stdout + stderr;
            const versionMatch = output.match(prereq.versionPattern);
            if (versionMatch) {
                result.available = true;
                result.version = versionMatch[1]?.trim();
                console.log(`✓ ${prereq.name} found: ${result.version}`);
            }
            else {
                // Command ran but couldn't parse version - still consider it available
                result.available = true;
                result.version = 'unknown';
                console.log(`✓ ${prereq.name} found (version unknown)`);
            }
        }
        else {
            result.error = `Command failed with code ${code}: ${stderr}`;
            console.log(`✗ ${prereq.name} not found: ${result.error}`);
        }
    }
    catch (error) {
        result.error = error.message;
        console.log(`✗ ${prereq.name} not found: ${result.error}`);
    }
    return result;
}
/**
 * Check all prerequisites
 */
export async function checkAllPrerequisites(showSuccess = true) {
    console.log('🔍 Checking system prerequisites...\n');
    const results = [];
    const missing = [];
    for (const prereq of PREREQUISITES) {
        const result = await checkPrerequisite(prereq);
        results.push(result);
        if (!result.available && prereq.required) {
            missing.push(result);
        }
    }
    const success = missing.length === 0;
    if (success && showSuccess) {
        console.log('\n✅ All prerequisites are satisfied!');
    }
    else if (!success) {
        console.log('\n❌ Missing prerequisites detected:');
        console.log('=========================================');
        for (const result of missing) {
            console.log(`\n${result.name}:`);
            console.log(`Command: ${result.command}`);
            console.log(`Error: ${result.error}`);
            console.log('Installation instructions:');
            console.log(result.installInstructions);
        }
    }
    return { success, results, missing };
}
/**
 * Startup validation - called by main server
 * Throws error if required prerequisites are missing
 */
export async function validatePrerequisitesForStartup() {
    const { success, missing } = await checkAllPrerequisites(false);
    if (!success) {
        const missingNames = missing.map(r => r.name).join(', ');
        throw new Error(`Missing required prerequisites: ${missingNames}. ` +
            'Run "npm run check:prereqs" for installation instructions.');
    }
}
/**
 * Get installation instructions for a specific prerequisite
 */
export function getInstallationInstructions(prerequisiteName) {
    if (!prerequisiteName) {
        return PREREQUISITES.map(p => `${p.name}:${p.installInstructions}`).join('\n\n');
    }
    const prereq = PREREQUISITES.find(p => p.name.toLowerCase().includes(prerequisiteName.toLowerCase()));
    return prereq ? prereq.installInstructions : 'Prerequisite not found';
}
/**
 * Main function - run when script is executed directly
 */
async function main() {
    try {
        const { success, results } = await checkAllPrerequisites();
        console.log('\n📊 Summary:');
        console.log('===========');
        for (const result of results) {
            const status = result.available ? '✓' : '✗';
            const version = result.version ? ` (${result.version})` : '';
            console.log(`${status} ${result.name}${version}`);
        }
        if (success) {
            console.log('\n🎉 System is ready for MCP Research File Server!');
            process.exit(0);
        }
        else {
            console.log('\n⚠️  Please install missing prerequisites before running the server.');
            process.exit(1);
        }
    }
    catch (error) {
        console.error('❌ Error checking prerequisites:', error);
        process.exit(1);
    }
}
// Run main function if this script is executed directly
if (import.meta.url === `file://${process.argv[1]}`) {
    main().catch(console.error);
}
//# sourceMappingURL=check-prerequisites.js.map