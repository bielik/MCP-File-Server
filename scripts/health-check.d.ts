#!/usr/bin/env tsx
declare class HealthChecker {
    private results;
    private addResult;
    checkNodeVersion(): Promise<void>;
    checkDirectories(): Promise<void>;
    checkLogDirectory(): Promise<void>;
    checkModelCache(): Promise<void>;
    checkQdrant(): Promise<void>;
    checkDependencies(): Promise<void>;
    checkConfiguration(): Promise<void>;
    runAllChecks(): Promise<void>;
    printResults(): void;
    getOverallHealth(): boolean;
}
export { HealthChecker };
//# sourceMappingURL=health-check.d.ts.map