#!/usr/bin/env tsx
import fs from 'fs/promises';
import path from 'path';
import { config, getAbsolutePath } from '../src/config/index.js';
import { logHealthCheck } from '../src/utils/logger.js';
class HealthChecker {
    results = [];
    addResult(component, healthy, message, details) {
        this.results.push({ component, healthy, message, details });
        logHealthCheck(component, healthy, details);
    }
    async checkNodeVersion() {
        const nodeVersion = process.version;
        const majorVersion = parseInt(nodeVersion.slice(1).split('.')[0], 10);
        const healthy = majorVersion >= 18;
        this.addResult('Node.js Version', healthy, healthy ? `Node.js ${nodeVersion} ✓` : `Node.js ${nodeVersion} - requires 18.0.0 or higher`, { version: nodeVersion, majorVersion });
    }
    async checkDirectories() {
        const directories = [
            ...config.filePermissions.contextFolders,
            ...config.filePermissions.workingFolders,
            config.filePermissions.outputFolder,
        ].filter(Boolean);
        let allHealthy = true;
        const directoryStatus = {};
        for (const dir of directories) {
            try {
                const absolutePath = getAbsolutePath(dir);
                const stats = await fs.stat(absolutePath);
                const exists = stats.isDirectory();
                directoryStatus[dir] = exists;
                if (!exists) {
                    allHealthy = false;
                }
            }
            catch (error) {
                directoryStatus[dir] = false;
                allHealthy = false;
            }
        }
        this.addResult('Configured Directories', allHealthy, allHealthy
            ? `All ${directories.length} directories exist ✓`
            : `Some directories missing - check configuration`, { directories: directoryStatus });
    }
    async checkLogDirectory() {
        const logPath = getAbsolutePath(config.server.logFile);
        const logDir = path.dirname(logPath);
        try {
            await fs.mkdir(logDir, { recursive: true });
            // Test write permissions
            const testFile = path.join(logDir, 'health-check.tmp');
            await fs.writeFile(testFile, 'test');
            await fs.unlink(testFile);
            this.addResult('Log Directory', true, `Log directory writable: ${logDir} ✓`, { logDirectory: logDir });
        }
        catch (error) {
            this.addResult('Log Directory', false, `Cannot write to log directory: ${logDir}`, { logDirectory: logDir, error: error.message });
        }
    }
    async checkModelCache() {
        const cacheDir = getAbsolutePath(config.mclip.cacheDir);
        try {
            await fs.mkdir(cacheDir, { recursive: true });
            this.addResult('Model Cache Directory', true, `Model cache directory ready: ${cacheDir} ✓`, { cacheDirectory: cacheDir });
        }
        catch (error) {
            this.addResult('Model Cache Directory', false, `Cannot create model cache directory: ${cacheDir}`, { cacheDirectory: cacheDir, error: error.message });
        }
    }
    async checkQdrant() {
        try {
            const response = await fetch(`${config.qdrant.url}/health`);
            const healthy = response.ok;
            if (healthy) {
                const healthData = await response.json();
                this.addResult('Qdrant Database', true, `Qdrant is healthy at ${config.qdrant.url} ✓`, { url: config.qdrant.url, status: healthData });
            }
            else {
                this.addResult('Qdrant Database', false, `Qdrant health check failed: HTTP ${response.status}`, { url: config.qdrant.url, status: response.status });
            }
        }
        catch (error) {
            this.addResult('Qdrant Database', false, `Cannot connect to Qdrant at ${config.qdrant.url}. Is it running?`, {
                url: config.qdrant.url,
                error: error.message,
                suggestion: 'Run: pnpm qdrant:start'
            });
        }
    }
    async checkDependencies() {
        const requiredPackages = [
            '@modelcontextprotocol/sdk',
            'express',
            'flexsearch',
            'winston',
            'zod',
        ];
        let allInstalled = true;
        const packageStatus = {};
        for (const pkg of requiredPackages) {
            try {
                await import(pkg);
                packageStatus[pkg] = true;
            }
            catch (error) {
                packageStatus[pkg] = false;
                allInstalled = false;
            }
        }
        this.addResult('Dependencies', allInstalled, allInstalled
            ? `All required packages installed ✓`
            : `Some dependencies missing - run: pnpm install`, { packages: packageStatus });
    }
    async checkConfiguration() {
        const issues = [];
        if (config.filePermissions.contextFolders.length === 0 &&
            config.filePermissions.workingFolders.length === 0) {
            issues.push('No context or working folders configured');
        }
        if (!config.filePermissions.outputFolder) {
            issues.push('No output folder configured');
        }
        if (config.processing.supportedLanguages.length === 0) {
            issues.push('No languages configured');
        }
        const healthy = issues.length === 0;
        this.addResult('Configuration', healthy, healthy ? 'Configuration is valid ✓' : `Configuration issues: ${issues.join(', ')}`, {
            issues,
            contextFolders: config.filePermissions.contextFolders.length,
            workingFolders: config.filePermissions.workingFolders.length,
            outputFolder: !!config.filePermissions.outputFolder,
            languages: config.processing.supportedLanguages,
        });
    }
    async runAllChecks() {
        console.log('🏥 MCP Research File Server - Health Check\n');
        const checks = [
            () => this.checkNodeVersion(),
            () => this.checkConfiguration(),
            () => this.checkDirectories(),
            () => this.checkLogDirectory(),
            () => this.checkModelCache(),
            () => this.checkDependencies(),
            () => this.checkQdrant(),
        ];
        for (const check of checks) {
            await check();
        }
    }
    printResults() {
        console.log('\n📊 Health Check Results:\n');
        const healthyCount = this.results.filter(r => r.healthy).length;
        const totalCount = this.results.length;
        for (const result of this.results) {
            const status = result.healthy ? '✅' : '❌';
            console.log(`${status} ${result.component}: ${result.message}`);
        }
        console.log('\n' + '─'.repeat(50));
        console.log(`Overall Health: ${healthyCount}/${totalCount} checks passed`);
        if (healthyCount === totalCount) {
            console.log('\n🎉 System is healthy and ready to use!');
            console.log('\nNext steps:');
            console.log('1. Start the MCP server: pnpm dev:mcp');
            console.log('2. Test with Claude Desktop or other MCP client');
        }
        else {
            console.log('\n⚠️  Some issues need attention before the server will work properly.');
            const failedComponents = this.results
                .filter(r => !r.healthy)
                .map(r => r.component);
            console.log(`\nFailed components: ${failedComponents.join(', ')}`);
            // Provide specific recommendations
            if (failedComponents.includes('Qdrant Database')) {
                console.log('\n🐳 To start Qdrant: pnpm qdrant:start');
            }
            if (failedComponents.includes('Dependencies')) {
                console.log('📦 To install dependencies: pnpm install');
            }
            if (failedComponents.includes('Configured Directories')) {
                console.log('📁 Update .env with correct folder paths');
            }
        }
    }
    getOverallHealth() {
        return this.results.every(r => r.healthy);
    }
}
async function main() {
    const checker = new HealthChecker();
    try {
        await checker.runAllChecks();
        checker.printResults();
        // Exit with appropriate code
        process.exit(checker.getOverallHealth() ? 0 : 1);
    }
    catch (error) {
        console.error('❌ Health check failed:', error);
        process.exit(1);
    }
}
// Run if called directly
if (import.meta.url === `file://${process.argv[1]}`) {
    main();
}
export { HealthChecker };
//# sourceMappingURL=health-check.js.map