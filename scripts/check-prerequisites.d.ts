#!/usr/bin/env tsx
/**
 * Prerequisite Checker for MCP Research File Server
 *
 * This script validates that all required external dependencies are installed
 * and accessible in the system PATH. It's designed to be run both as a
 * standalone script and integrated into the server startup process.
 *
 * Required Dependencies:
 * - Poppler (pdfimages utility) - For robust PDF image extraction
 *
 * Usage:
 * - Standalone: npm run check:prereqs
 * - Integrated: Called during server startup in main.ts
 */
interface PrerequisiteResult {
    name: string;
    command: string;
    available: boolean;
    version?: string;
    error?: string;
    installInstructions: string;
}
/**
 * Check all prerequisites
 */
export declare function checkAllPrerequisites(showSuccess?: boolean): Promise<{
    success: boolean;
    results: PrerequisiteResult[];
    missing: PrerequisiteResult[];
}>;
/**
 * Startup validation - called by main server
 * Throws error if required prerequisites are missing
 */
export declare function validatePrerequisitesForStartup(): Promise<void>;
/**
 * Get installation instructions for a specific prerequisite
 */
export declare function getInstallationInstructions(prerequisiteName?: string): string;
export {};
//# sourceMappingURL=check-prerequisites.d.ts.map