#!/bin/bash

# Phase 3B Test Runner Script
#
# This script provides comprehensive test execution for Phase 3B testing.
# It can run individual test categories or the complete test suite with
# detailed reporting and performance analysis.
#
# Usage:
#   ./scripts/run-phase3b-tests.sh [options]
#
# Options:
#   --backend-only      Run only backend tests
#   --frontend-only     Run only frontend tests
#   --performance-only  Run only performance tests
#   --quick            Run quick smoke tests only
#   --coverage         Generate coverage reports
#   --real-system      Test against real running system
#   --report           Generate detailed HTML report
#   --help             Show this help message

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT/frontend"
REPORTS_DIR="$PROJECT_ROOT/test-reports"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Default settings
RUN_BACKEND=true
RUN_FRONTEND=true
RUN_PERFORMANCE=true
QUICK_MODE=false
GENERATE_COVERAGE=false
USE_REAL_SYSTEM=false
GENERATE_REPORT=false

# Test result tracking
BACKEND_RESULTS=""
FRONTEND_RESULTS=""
PERFORMANCE_RESULTS=""
OVERALL_STATUS=0

# Function definitions
print_banner() {
    echo -e "${BLUE}"
    echo "================================="
    echo "  Phase 3B Test Runner v1.0"
    echo "  MCP KnowledgeExplorer"
    echo "================================="
    echo -e "${NC}"
}

print_help() {
    cat << EOF
Phase 3B Test Runner

Usage: $0 [OPTIONS]

Options:
    --backend-only      Run only backend tests
    --frontend-only     Run only frontend tests
    --performance-only  Run only performance tests
    --quick            Run quick smoke tests only
    --coverage         Generate coverage reports
    --real-system      Test against real running system
    --report           Generate detailed HTML report
    --help             Show this help message

Examples:
    $0                          # Run all tests
    $0 --quick                  # Quick smoke test
    $0 --backend-only --coverage # Backend tests with coverage
    $0 --real-system --report    # Full system test with report

EOF
}

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_section() {
    echo -e "\n${PURPLE}=== $1 ===${NC}"
}

check_dependencies() {
    log_section "Checking Dependencies"

    local missing_deps=()

    # Check Python and pytest
    if ! command -v python3 &> /dev/null; then
        missing_deps+=("python3")
    fi

    if ! python3 -c "import pytest" 2> /dev/null; then
        missing_deps+=("pytest")
    fi

    # Check Node.js and npm
    if ! command -v node &> /dev/null; then
        missing_deps+=("node")
    fi

    if ! command -v npm &> /dev/null; then
        missing_deps+=("npm")
    fi

    # Check Docker (for real system tests)
    if [[ "$USE_REAL_SYSTEM" == true ]] && ! command -v docker &> /dev/null; then
        missing_deps+=("docker")
    fi

    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        log_error "Missing dependencies: ${missing_deps[*]}"
        log_info "Please install missing dependencies and try again"
        exit 1
    fi

    log_success "All dependencies available"
}

setup_test_environment() {
    log_section "Setting Up Test Environment"

    # Create reports directory
    mkdir -p "$REPORTS_DIR"

    # Set environment variables for testing
    export NODE_ENV=test
    export PYTEST_TIMEOUT=300
    export TEST_DATABASE_URL="sqlite:///./test_phase3b_${TIMESTAMP}.db"

    # Clean up any existing test artifacts
    find "$PROJECT_ROOT" -name "test_*.db" -type f -delete 2>/dev/null || true
    find "$PROJECT_ROOT" -name "*.pyc" -type f -delete 2>/dev/null || true
    find "$PROJECT_ROOT" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

    log_success "Test environment ready"
}

start_real_system() {
    if [[ "$USE_REAL_SYSTEM" != true ]]; then
        return 0
    fi

    log_section "Starting Real System"

    cd "$PROJECT_ROOT"

    # Check if system is already running
    if curl -s http://localhost:8000/api/workspaces > /dev/null 2>&1; then
        log_info "System already running, using existing instance"
        return 0
    fi

    # Start system with docker-compose
    log_info "Starting system with docker-compose..."
    docker-compose up -d

    # Wait for system to be ready
    log_info "Waiting for system to be ready..."
    local max_attempts=30
    local attempt=0

    while [[ $attempt -lt $max_attempts ]]; do
        if curl -s http://localhost:8000/api/workspaces > /dev/null 2>&1; then
            log_success "System is ready"
            return 0
        fi

        ((attempt++))
        log_info "Attempt $attempt/$max_attempts - waiting for system..."
        sleep 2
    done

    log_error "System failed to start within timeout"
    docker-compose logs
    exit 1
}

run_backend_tests() {
    if [[ "$RUN_BACKEND" != true ]]; then
        return 0
    fi

    log_section "Running Backend Tests"

    cd "$BACKEND_DIR"

    local pytest_args=("tests/phase3b/" "-v" "--tb=short")

    # Add coverage if requested
    if [[ "$GENERATE_COVERAGE" == true ]]; then
        pytest_args+=("--cov=app" "--cov-report=html:$REPORTS_DIR/backend-coverage" "--cov-report=term-missing")
    fi

    # Add performance reporting
    pytest_args+=("--durations=10")

    # Quick mode - run only smoke tests
    if [[ "$QUICK_MODE" == true ]]; then
        pytest_args+=("-m" "smoke")
    fi

    # Real system mode
    if [[ "$USE_REAL_SYSTEM" == true ]]; then
        pytest_args+=("--real-system")
    fi

    # Add JSON report for processing
    pytest_args+=("--json-report" "--json-report-file=$REPORTS_DIR/backend-results.json")

    log_info "Running pytest with args: ${pytest_args[*]}"

    local start_time=$(date +%s)

    if python3 -m pytest "${pytest_args[@]}"; then
        BACKEND_RESULTS="✅ PASSED"
        log_success "Backend tests completed successfully"
    else
        BACKEND_RESULTS="❌ FAILED"
        log_error "Backend tests failed"
        OVERALL_STATUS=1
    fi

    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    log_info "Backend tests completed in ${duration}s"
}

run_frontend_tests() {
    if [[ "$RUN_FRONTEND" != true ]]; then
        return 0
    fi

    log_section "Running Frontend Tests"

    cd "$FRONTEND_DIR"

    # Ensure dependencies are installed
    if [[ ! -d "node_modules" ]]; then
        log_info "Installing frontend dependencies..."
        npm install
    fi

    local npm_args=()

    # Add coverage if requested
    if [[ "$GENERATE_COVERAGE" == true ]]; then
        npm_args+=("--" "--coverage" "--coverageDirectory=$REPORTS_DIR/frontend-coverage")
    fi

    # Quick mode - run only smoke tests
    if [[ "$QUICK_MODE" == true ]]; then
        npm_args+=("--" "--testNamePattern=smoke")
    fi

    # Real system mode
    if [[ "$USE_REAL_SYSTEM" == true ]]; then
        npm_args+=("--" "--testNamePattern=real-backend")
    fi

    # Add reporter for CI
    npm_args+=("--" "--reporter=json" "--outputFile=$REPORTS_DIR/frontend-results.json")

    log_info "Running npm test with args: ${npm_args[*]}"

    local start_time=$(date +%s)

    if npm test "${npm_args[@]}"; then
        FRONTEND_RESULTS="✅ PASSED"
        log_success "Frontend tests completed successfully"
    else
        FRONTEND_RESULTS="❌ FAILED"
        log_error "Frontend tests failed"
        OVERALL_STATUS=1
    fi

    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    log_info "Frontend tests completed in ${duration}s"
}

run_performance_tests() {
    if [[ "$RUN_PERFORMANCE" != true ]] || [[ "$QUICK_MODE" == true ]]; then
        return 0
    fi

    log_section "Running Performance Tests"

    cd "$BACKEND_DIR"

    local start_time=$(date +%s)

    # Run performance-specific tests
    local perf_args=("tests/phase3b/test_performance.py" "-v" "-s" "--benchmark-only")

    if [[ "$USE_REAL_SYSTEM" == true ]]; then
        perf_args+=("--real-system")
    fi

    perf_args+=("--json-report" "--json-report-file=$REPORTS_DIR/performance-results.json")

    if python3 -m pytest "${perf_args[@]}"; then
        PERFORMANCE_RESULTS="✅ PASSED"
        log_success "Performance tests completed successfully"

        # Extract performance metrics if JSON report exists
        if [[ -f "$REPORTS_DIR/performance-results.json" ]]; then
            log_info "Performance Summary:"
            python3 -c "
import json
with open('$REPORTS_DIR/performance-results.json') as f:
    data = json.load(f)
    if 'tests' in data:
        for test in data['tests']:
            if 'call' in test and 'duration' in test['call']:
                print(f'  {test[\"nodeid\"]}: {test[\"call\"][\"duration\"]:.2f}s')
"
        fi
    else
        PERFORMANCE_RESULTS="❌ FAILED"
        log_error "Performance tests failed"
        OVERALL_STATUS=1
    fi

    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    log_info "Performance tests completed in ${duration}s"
}

generate_report() {
    if [[ "$GENERATE_REPORT" != true ]]; then
        return 0
    fi

    log_section "Generating Test Report"

    local report_file="$REPORTS_DIR/phase3b-test-report-${TIMESTAMP}.html"

    cat > "$report_file" << EOF
<!DOCTYPE html>
<html>
<head>
    <title>Phase 3B Test Report - $(date)</title>
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
        <p><strong>Generated:</strong> $(date)</p>
        <p><strong>System:</strong> $(uname -a)</p>
        <p><strong>Overall Status:</strong> $([ $OVERALL_STATUS -eq 0 ] && echo "✅ PASSED" || echo "❌ FAILED")</p>
    </div>

    <div class="section">
        <h2>Test Results Summary</h2>
        <table>
            <tr><th>Test Category</th><th>Status</th><th>Details</th></tr>
            <tr><td>Backend Tests</td><td>$BACKEND_RESULTS</td><td>Full backend test suite</td></tr>
            <tr><td>Frontend Tests</td><td>$FRONTEND_RESULTS</td><td>React component and integration tests</td></tr>
            <tr><td>Performance Tests</td><td>$PERFORMANCE_RESULTS</td><td>API performance and benchmarks</td></tr>
        </table>
    </div>

    <div class="section">
        <h2>Configuration</h2>
        <table>
            <tr><th>Setting</th><th>Value</th></tr>
            <tr><td>Quick Mode</td><td>$QUICK_MODE</td></tr>
            <tr><td>Coverage Enabled</td><td>$GENERATE_COVERAGE</td></tr>
            <tr><td>Real System</td><td>$USE_REAL_SYSTEM</td></tr>
            <tr><td>Backend Tests</td><td>$RUN_BACKEND</td></tr>
            <tr><td>Frontend Tests</td><td>$RUN_FRONTEND</td></tr>
            <tr><td>Performance Tests</td><td>$RUN_PERFORMANCE</td></tr>
        </table>
    </div>
EOF

    # Add coverage information if available
    if [[ "$GENERATE_COVERAGE" == true ]]; then
        cat >> "$report_file" << EOF
    <div class="section">
        <h2>Coverage Reports</h2>
        <ul>
            <li><a href="backend-coverage/index.html">Backend Coverage Report</a></li>
            <li><a href="frontend-coverage/index.html">Frontend Coverage Report</a></li>
        </ul>
    </div>
EOF
    fi

    cat >> "$report_file" << EOF
    <div class="section">
        <h2>Raw Results</h2>
        <p>Detailed test results are available in:</p>
        <ul>
            <li><code>$REPORTS_DIR/backend-results.json</code></li>
            <li><code>$REPORTS_DIR/frontend-results.json</code></li>
            <li><code>$REPORTS_DIR/performance-results.json</code></li>
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
EOF

    log_success "Test report generated: $report_file"

    # Try to open report in browser (Linux/macOS)
    if command -v xdg-open &> /dev/null; then
        xdg-open "$report_file" 2>/dev/null || true
    elif command -v open &> /dev/null; then
        open "$report_file" 2>/dev/null || true
    fi
}

cleanup() {
    log_section "Cleanup"

    # Stop real system if we started it
    if [[ "$USE_REAL_SYSTEM" == true ]]; then
        log_info "Stopping docker-compose services..."
        cd "$PROJECT_ROOT"
        docker-compose down > /dev/null 2>&1 || true
    fi

    # Clean up test databases
    find "$PROJECT_ROOT" -name "test_*.db" -type f -delete 2>/dev/null || true

    log_success "Cleanup completed"
}

print_summary() {
    log_section "Test Execution Summary"

    echo -e "${CYAN}Backend Tests:${NC} $BACKEND_RESULTS"
    echo -e "${CYAN}Frontend Tests:${NC} $FRONTEND_RESULTS"
    echo -e "${CYAN}Performance Tests:${NC} $PERFORMANCE_RESULTS"
    echo

    if [[ $OVERALL_STATUS -eq 0 ]]; then
        echo -e "${GREEN}🎉 All tests completed successfully!${NC}"
        echo -e "${CYAN}Reports available in:${NC} $REPORTS_DIR"
    else
        echo -e "${RED}❌ Some tests failed. Check the logs above for details.${NC}"
        echo -e "${CYAN}Reports available in:${NC} $REPORTS_DIR"
    fi

    echo
    echo -e "${BLUE}For more details, run with --report flag to generate HTML report${NC}"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --backend-only)
            RUN_BACKEND=true
            RUN_FRONTEND=false
            RUN_PERFORMANCE=false
            shift
            ;;
        --frontend-only)
            RUN_BACKEND=false
            RUN_FRONTEND=true
            RUN_PERFORMANCE=false
            shift
            ;;
        --performance-only)
            RUN_BACKEND=false
            RUN_FRONTEND=false
            RUN_PERFORMANCE=true
            shift
            ;;
        --quick)
            QUICK_MODE=true
            shift
            ;;
        --coverage)
            GENERATE_COVERAGE=true
            shift
            ;;
        --real-system)
            USE_REAL_SYSTEM=true
            shift
            ;;
        --report)
            GENERATE_REPORT=true
            shift
            ;;
        --help)
            print_help
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            print_help
            exit 1
            ;;
    esac
done

# Main execution
main() {
    print_banner

    # Set up trap for cleanup
    trap cleanup EXIT

    check_dependencies
    setup_test_environment
    start_real_system

    # Run tests
    run_backend_tests
    run_frontend_tests
    run_performance_tests

    # Generate report if requested
    generate_report

    # Print summary
    print_summary

    exit $OVERALL_STATUS
}

# Run main function
main "$@"