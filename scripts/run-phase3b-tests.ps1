# Phase 3B Test Runner Script for Windows PowerShell
#
# This script provides comprehensive test execution for Phase 3B testing on Windows.
# It mirrors the functionality of the bash script but uses PowerShell syntax.
#
# Usage:
#   .\scripts\run-phase3b-tests.ps1 [options]
#
# Examples:
#   .\scripts\run-phase3b-tests.ps1
#   .\scripts\run-phase3b-tests.ps1 -BackendOnly -Coverage
#   .\scripts\run-phase3b-tests.ps1 -Quick -Report

param(
    [switch]$BackendOnly,
    [switch]$FrontendOnly,
    [switch]$PerformanceOnly,
    [switch]$Quick,
    [switch]$Coverage,
    [switch]$RealSystem,
    [switch]$Report,
    [switch]$Help
)

# Color definitions
$Colors = @{
    Red = "Red"
    Green = "Green"
    Yellow = "Yellow"
    Blue = "Blue"
    Purple = "Magenta"
    Cyan = "Cyan"
    White = "White"
}

# Configuration
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$ProjectRoot = Split-Path -Parent $ScriptDir
$BackendDir = Join-Path $ProjectRoot "backend"
$FrontendDir = Join-Path $ProjectRoot "frontend"
$ReportsDir = Join-Path $ProjectRoot "test-reports"
$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"

# Default settings
$RunBackend = $true
$RunFrontend = $true
$RunPerformance = $true
$QuickMode = $false
$GenerateCoverage = $false
$UseRealSystem = $false
$GenerateReport = $false

# Test result tracking
$BackendResults = ""
$FrontendResults = ""
$PerformanceResults = ""
$OverallStatus = 0

# Function definitions
function Write-Banner {
    Write-Host "=================================" -ForegroundColor $Colors.Blue
    Write-Host "  Phase 3B Test Runner v1.0" -ForegroundColor $Colors.Blue
    Write-Host "  MCP KnowledgeExplorer" -ForegroundColor $Colors.Blue
    Write-Host "=================================" -ForegroundColor $Colors.Blue
}

function Write-Help {
    @"
Phase 3B Test Runner for Windows

Usage: .\run-phase3b-tests.ps1 [OPTIONS]

Options:
    -BackendOnly        Run only backend tests
    -FrontendOnly       Run only frontend tests
    -PerformanceOnly    Run only performance tests
    -Quick             Run quick smoke tests only
    -Coverage          Generate coverage reports
    -RealSystem        Test against real running system
    -Report            Generate detailed HTML report
    -Help              Show this help message

Examples:
    .\run-phase3b-tests.ps1                    # Run all tests
    .\run-phase3b-tests.ps1 -Quick             # Quick smoke test
    .\run-phase3b-tests.ps1 -BackendOnly -Coverage # Backend with coverage
    .\run-phase3b-tests.ps1 -RealSystem -Report    # Full system test with report
"@
}

function Write-LogInfo {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor $Colors.Blue
}

function Write-LogSuccess {
    param([string]$Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor $Colors.Green
}

function Write-LogWarning {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor $Colors.Yellow
}

function Write-LogError {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor $Colors.Red
}

function Write-LogSection {
    param([string]$Message)
    Write-Host "`n=== $Message ===" -ForegroundColor $Colors.Purple
}

function Test-Dependencies {
    Write-LogSection "Checking Dependencies"

    $MissingDeps = @()

    # Check Python
    try {
        $null = Get-Command python -ErrorAction Stop
        $null = python -c "import pytest" 2>$null
    }
    catch {
        $MissingDeps += "python/pytest"
    }

    # Check Node.js and npm
    try {
        $null = Get-Command node -ErrorAction Stop
        $null = Get-Command npm -ErrorAction Stop
    }
    catch {
        $MissingDeps += "node/npm"
    }

    # Check Docker (for real system tests)
    if ($UseRealSystem) {
        try {
            $null = Get-Command docker -ErrorAction Stop
        }
        catch {
            $MissingDeps += "docker"
        }
    }

    if ($MissingDeps.Count -gt 0) {
        Write-LogError "Missing dependencies: $($MissingDeps -join ', ')"
        Write-LogInfo "Please install missing dependencies and try again"
        exit 1
    }

    Write-LogSuccess "All dependencies available"
}

function Initialize-TestEnvironment {
    Write-LogSection "Setting Up Test Environment"

    # Create reports directory
    if (!(Test-Path $ReportsDir)) {
        New-Item -ItemType Directory -Path $ReportsDir -Force | Out-Null
    }

    # Set environment variables
    $env:NODE_ENV = "test"
    $env:PYTEST_TIMEOUT = "300"
    $env:TEST_DATABASE_URL = "sqlite:///./test_phase3b_$Timestamp.db"

    # Clean up test artifacts
    Get-ChildItem -Path $ProjectRoot -Filter "test_*.db" -Recurse | Remove-Item -Force -ErrorAction SilentlyContinue
    Get-ChildItem -Path $ProjectRoot -Filter "*.pyc" -Recurse | Remove-Item -Force -ErrorAction SilentlyContinue
    Get-ChildItem -Path $ProjectRoot -Filter "__pycache__" -Recurse -Directory | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

    Write-LogSuccess "Test environment ready"
}

function Start-RealSystem {
    if (!$UseRealSystem) {
        return
    }

    Write-LogSection "Starting Real System"

    Push-Location $ProjectRoot

    # Check if system is already running
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/api/workspaces" -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
        Write-LogInfo "System already running, using existing instance"
        Pop-Location
        return
    }
    catch {
        # System not running, start it
    }

    # Start system with docker-compose
    Write-LogInfo "Starting system with docker-compose..."
    & docker-compose up -d

    if ($LASTEXITCODE -ne 0) {
        Write-LogError "Failed to start docker-compose"
        Pop-Location
        exit 1
    }

    # Wait for system to be ready
    Write-LogInfo "Waiting for system to be ready..."
    $MaxAttempts = 30
    $Attempt = 0

    while ($Attempt -lt $MaxAttempts) {
        try {
            $null = Invoke-WebRequest -Uri "http://localhost:8000/api/workspaces" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
            Write-LogSuccess "System is ready"
            Pop-Location
            return
        }
        catch {
            $Attempt++
            Write-LogInfo "Attempt $Attempt/$MaxAttempts - waiting for system..."
            Start-Sleep -Seconds 2
        }
    }

    Write-LogError "System failed to start within timeout"
    & docker-compose logs
    Pop-Location
    exit 1
}

function Invoke-BackendTests {
    if (!$RunBackend) {
        return
    }

    Write-LogSection "Running Backend Tests"

    Push-Location $BackendDir

    $PytestArgs = @("tests/phase3b/", "-v", "--tb=short")

    # Add coverage if requested
    if ($GenerateCoverage) {
        $PytestArgs += "--cov=app"
        $PytestArgs += "--cov-report=html:$ReportsDir/backend-coverage"
        $PytestArgs += "--cov-report=term-missing"
    }

    # Add performance reporting
    $PytestArgs += "--durations=10"

    # Quick mode
    if ($QuickMode) {
        $PytestArgs += "-m"
        $PytestArgs += "smoke"
    }

    # Real system mode
    if ($UseRealSystem) {
        $PytestArgs += "--real-system"
    }

    # JSON report
    $PytestArgs += "--json-report"
    $PytestArgs += "--json-report-file=$ReportsDir/backend-results.json"

    Write-LogInfo "Running pytest with args: $($PytestArgs -join ' ')"

    $StartTime = Get-Date

    & python -m pytest @PytestArgs
    $ExitCode = $LASTEXITCODE

    $EndTime = Get-Date
    $Duration = ($EndTime - $StartTime).TotalSeconds

    if ($ExitCode -eq 0) {
        $script:BackendResults = "✅ PASSED"
        Write-LogSuccess "Backend tests completed successfully"
    }
    else {
        $script:BackendResults = "❌ FAILED"
        Write-LogError "Backend tests failed"
        $script:OverallStatus = 1
    }

    Write-LogInfo "Backend tests completed in $([math]::Round($Duration))s"
    Pop-Location
}

function Invoke-FrontendTests {
    if (!$RunFrontend) {
        return
    }

    Write-LogSection "Running Frontend Tests"

    Push-Location $FrontendDir

    # Ensure dependencies are installed
    if (!(Test-Path "node_modules")) {
        Write-LogInfo "Installing frontend dependencies..."
        & npm install
        if ($LASTEXITCODE -ne 0) {
            Write-LogError "Failed to install frontend dependencies"
            Pop-Location
            return
        }
    }

    $NpmArgs = @()

    # Add coverage if requested
    if ($GenerateCoverage) {
        $NpmArgs += "--"
        $NpmArgs += "--coverage"
        $NpmArgs += "--coverageDirectory=$ReportsDir/frontend-coverage"
    }

    # Quick mode
    if ($QuickMode) {
        $NpmArgs += "--"
        $NpmArgs += "--testNamePattern=smoke"
    }

    # Real system mode
    if ($UseRealSystem) {
        $NpmArgs += "--"
        $NpmArgs += "--testNamePattern=real-backend"
    }

    # JSON report
    $NpmArgs += "--"
    $NpmArgs += "--reporter=json"
    $NpmArgs += "--outputFile=$ReportsDir/frontend-results.json"

    Write-LogInfo "Running npm test with args: $($NpmArgs -join ' ')"

    $StartTime = Get-Date

    if ($NpmArgs.Count -gt 0) {
        & npm test @NpmArgs
    }
    else {
        & npm test
    }
    $ExitCode = $LASTEXITCODE

    $EndTime = Get-Date
    $Duration = ($EndTime - $StartTime).TotalSeconds

    if ($ExitCode -eq 0) {
        $script:FrontendResults = "✅ PASSED"
        Write-LogSuccess "Frontend tests completed successfully"
    }
    else {
        $script:FrontendResults = "❌ FAILED"
        Write-LogError "Frontend tests failed"
        $script:OverallStatus = 1
    }

    Write-LogInfo "Frontend tests completed in $([math]::Round($Duration))s"
    Pop-Location
}

function Invoke-PerformanceTests {
    if (!$RunPerformance -or $QuickMode) {
        return
    }

    Write-LogSection "Running Performance Tests"

    Push-Location $BackendDir

    $StartTime = Get-Date

    $PerfArgs = @("tests/phase3b/test_performance.py", "-v", "-s", "--benchmark-only")

    if ($UseRealSystem) {
        $PerfArgs += "--real-system"
    }

    $PerfArgs += "--json-report"
    $PerfArgs += "--json-report-file=$ReportsDir/performance-results.json"

    & python -m pytest @PerfArgs
    $ExitCode = $LASTEXITCODE

    if ($ExitCode -eq 0) {
        $script:PerformanceResults = "✅ PASSED"
        Write-LogSuccess "Performance tests completed successfully"

        # Extract performance metrics if JSON report exists
        $ReportFile = Join-Path $ReportsDir "performance-results.json"
        if (Test-Path $ReportFile) {
            Write-LogInfo "Performance Summary:"
            try {
                $PerfData = Get-Content $ReportFile | ConvertFrom-Json
                if ($PerfData.tests) {
                    foreach ($test in $PerfData.tests) {
                        if ($test.call -and $test.call.duration) {
                            Write-Host "  $($test.nodeid): $([math]::Round($test.call.duration, 2))s" -ForegroundColor $Colors.Cyan
                        }
                    }
                }
            }
            catch {
                Write-LogWarning "Could not parse performance results"
            }
        }
    }
    else {
        $script:PerformanceResults = "❌ FAILED"
        Write-LogError "Performance tests failed"
        $script:OverallStatus = 1
    }

    $EndTime = Get-Date
    $Duration = ($EndTime - $StartTime).TotalSeconds
    Write-LogInfo "Performance tests completed in $([math]::Round($Duration))s"
    Pop-Location
}

function New-TestReport {
    if (!$GenerateReport) {
        return
    }

    Write-LogSection "Generating Test Report"

    $ReportFile = Join-Path $ReportsDir "phase3b-test-report-$Timestamp.html"
    $CurrentDate = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $SystemInfo = "$env:COMPUTERNAME - $env:OS"
    $OverallStatusText = if ($OverallStatus -eq 0) { "✅ PASSED" } else { "❌ FAILED" }

    $HtmlContent = @"
<!DOCTYPE html>
<html>
<head>
    <title>Phase 3B Test Report - $CurrentDate</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .header { background-color: #f5f5f5; padding: 20px; border-radius: 5px; }
        .section { margin: 20px 0; padding: 15px; border-left: 4px solid #007acc; }
        .success { color: #28a745; }
        .failure { color: #dc3545; }
        .warning { color: #ffc107; }
        .code { background-color: #f8f9fa; padding: 10px; border-radius: 3px; font-family: monospace; }
        table { border-collapse: collapse; width: 100%; margin: 15px 0; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Phase 3B Test Report</h1>
        <p><strong>Generated:</strong> $CurrentDate</p>
        <p><strong>System:</strong> $SystemInfo</p>
        <p><strong>Overall Status:</strong> $OverallStatusText</p>
    </div>

    <div class="section">
        <h2>Test Results Summary</h2>
        <table>
            <tr><th>Test Category</th><th>Status</th><th>Details</th></tr>
            <tr><td>Backend Tests</td><td>$BackendResults</td><td>Full backend test suite</td></tr>
            <tr><td>Frontend Tests</td><td>$FrontendResults</td><td>React component and integration tests</td></tr>
            <tr><td>Performance Tests</td><td>$PerformanceResults</td><td>API performance and benchmarks</td></tr>
        </table>
    </div>

    <div class="section">
        <h2>Configuration</h2>
        <table>
            <tr><th>Setting</th><th>Value</th></tr>
            <tr><td>Quick Mode</td><td>$QuickMode</td></tr>
            <tr><td>Coverage Enabled</td><td>$GenerateCoverage</td></tr>
            <tr><td>Real System</td><td>$UseRealSystem</td></tr>
            <tr><td>Backend Tests</td><td>$RunBackend</td></tr>
            <tr><td>Frontend Tests</td><td>$RunFrontend</td></tr>
            <tr><td>Performance Tests</td><td>$RunPerformance</td></tr>
        </table>
    </div>
"@

    # Add coverage section if enabled
    if ($GenerateCoverage) {
        $HtmlContent += @"
    <div class="section">
        <h2>Coverage Reports</h2>
        <ul>
            <li><a href="backend-coverage/index.html">Backend Coverage Report</a></li>
            <li><a href="frontend-coverage/index.html">Frontend Coverage Report</a></li>
        </ul>
    </div>
"@
    }

    $HtmlContent += @"
    <div class="section">
        <h2>Raw Results</h2>
        <p>Detailed test results are available in:</p>
        <ul>
            <li><code>$ReportsDir\backend-results.json</code></li>
            <li><code>$ReportsDir\frontend-results.json</code></li>
            <li><code>$ReportsDir\performance-results.json</code></li>
        </ul>
    </div>

    <div class="section">
        <h2>Next Steps</h2>
        <ul>
            <li>Review failed tests and error messages</li>
            <li>Check coverage reports for untested code</li>
            <li>Analyze performance benchmarks</li>
            <li>Update documentation if needed</li>
        </ul>
    </div>
</body>
</html>
"@

    Set-Content -Path $ReportFile -Value $HtmlContent -Encoding UTF8
    Write-LogSuccess "Test report generated: $ReportFile"

    # Try to open report in browser
    try {
        Start-Process $ReportFile -ErrorAction SilentlyContinue
    }
    catch {
        Write-LogInfo "Report saved to: $ReportFile"
    }
}

function Stop-RealSystem {
    if (!$UseRealSystem) {
        return
    }

    Write-LogSection "Cleanup"

    Push-Location $ProjectRoot
    Write-LogInfo "Stopping docker-compose services..."
    & docker-compose down 2>$null | Out-Null
    Pop-Location

    # Clean up test databases
    Get-ChildItem -Path $ProjectRoot -Filter "test_*.db" -Recurse | Remove-Item -Force -ErrorAction SilentlyContinue

    Write-LogSuccess "Cleanup completed"
}

function Write-Summary {
    Write-LogSection "Test Execution Summary"

    Write-Host "Backend Tests: $BackendResults" -ForegroundColor $Colors.Cyan
    Write-Host "Frontend Tests: $FrontendResults" -ForegroundColor $Colors.Cyan
    Write-Host "Performance Tests: $PerformanceResults" -ForegroundColor $Colors.Cyan
    Write-Host

    if ($OverallStatus -eq 0) {
        Write-Host "🎉 All tests completed successfully!" -ForegroundColor $Colors.Green
        Write-Host "Reports available in: $ReportsDir" -ForegroundColor $Colors.Cyan
    }
    else {
        Write-Host "❌ Some tests failed. Check the logs above for details." -ForegroundColor $Colors.Red
        Write-Host "Reports available in: $ReportsDir" -ForegroundColor $Colors.Cyan
    }

    Write-Host
    Write-Host "For more details, run with -Report flag to generate HTML report" -ForegroundColor $Colors.Blue
}

# Parse parameters
if ($Help) {
    Write-Help
    exit 0
}

if ($BackendOnly) {
    $RunBackend = $true
    $RunFrontend = $false
    $RunPerformance = $false
}

if ($FrontendOnly) {
    $RunBackend = $false
    $RunFrontend = $true
    $RunPerformance = $false
}

if ($PerformanceOnly) {
    $RunBackend = $false
    $RunFrontend = $false
    $RunPerformance = $true
}

if ($Quick) { $QuickMode = $true }
if ($Coverage) { $GenerateCoverage = $true }
if ($RealSystem) { $UseRealSystem = $true }
if ($Report) { $GenerateReport = $true }

# Main execution
try {
    Write-Banner

    Test-Dependencies
    Initialize-TestEnvironment
    Start-RealSystem

    # Run tests
    Invoke-BackendTests
    Invoke-FrontendTests
    Invoke-PerformanceTests

    # Generate report if requested
    New-TestReport

    # Print summary
    Write-Summary
}
finally {
    Stop-RealSystem
}

exit $OverallStatus