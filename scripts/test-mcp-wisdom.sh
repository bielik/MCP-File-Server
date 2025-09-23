#!/bin/bash
#
# MCP Wisdom Comprehensive Test Suite
#
# This script runs comprehensive tests of the MCP Wisdom connection,
# validating tool functionality, permission enforcement, and security.
#
# Usage:
#   ./scripts/test-mcp-wisdom.sh                    # Quick test with current environment
#   ./scripts/test-mcp-wisdom.sh --comprehensive    # Full test suite
#   ./scripts/test-mcp-wisdom.sh --isolated         # Create isolated test environment
#   ./scripts/test-mcp-wisdom.sh --report-only      # Generate report from last run
#

set -e  # Exit on any error

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$PROJECT_ROOT/backend"
REPORT_FILE="$BACKEND_DIR/mcp_wisdom_test_report.json"
DETAILED_LOG="$PROJECT_ROOT/mcp_wisdom_test.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test modes
COMPREHENSIVE=false
ISOLATED=false
REPORT_ONLY=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --comprehensive)
            COMPREHENSIVE=true
            shift
            ;;
        --isolated)
            ISOLATED=true
            shift
            ;;
        --report-only)
            REPORT_ONLY=true
            shift
            ;;
        -h|--help)
            echo "MCP Wisdom Test Suite"
            echo ""
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --comprehensive    Run full test suite with all edge cases"
            echo "  --isolated         Create isolated test environment"
            echo "  --report-only      Generate report from last test run"
            echo "  -h, --help        Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                           # Quick test"
            echo "  $0 --comprehensive          # Full test suite"
            echo "  $0 --isolated               # Test in isolation"
            echo ""
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use -h or --help for usage information"
            exit 1
            ;;
    esac
done

# Logging function
log() {
    echo -e "$1" | tee -a "$DETAILED_LOG"
}

# Check if running in report-only mode
if [ "$REPORT_ONLY" = true ]; then
    log "${BLUE}=== MCP Wisdom Test Report ===${NC}"

    if [ -f "$REPORT_FILE" ]; then
        python -m json.tool "$REPORT_FILE"
        log "${GREEN}✅ Report displayed successfully${NC}"
    else
        log "${RED}❌ No test report found at $REPORT_FILE${NC}"
        log "${YELLOW}Run tests first: $0${NC}"
        exit 1
    fi
    exit 0
fi

# Initialize log
echo "=== MCP Wisdom Test Suite Started at $(date) ===" > "$DETAILED_LOG"

log "${BLUE}=== MCP WISDOM COMPREHENSIVE TEST SUITE ===${NC}"
log "Timestamp: $(date)"
log "Mode: $([ "$COMPREHENSIVE" = true ] && echo "Comprehensive" || ([ "$ISOLATED" = true ] && echo "Isolated" || echo "Quick"))"
log ""

# Step 1: Pre-flight checks
log "${YELLOW}1. Running pre-flight checks...${NC}"

# Check if Docker containers are running
if ! docker-compose ps | grep -q "Up"; then
    log "${RED}❌ Docker containers are not running${NC}"
    log "${YELLOW}Starting containers...${NC}"
    docker-compose up -d
    sleep 10
fi

# Check backend health
log "   Checking backend health..."
if ! curl -s -f http://localhost:8000/ > /dev/null 2>&1; then
    log "${RED}❌ Backend service not responding${NC}"
    log "   Waiting for backend to start..."
    sleep 15

    if ! curl -s -f http://localhost:8000/ > /dev/null 2>&1; then
        log "${RED}❌ Backend still not responding after wait${NC}"
        log "   Check docker-compose logs backend for details"
        exit 1
    fi
fi

# Check MCP endpoint
log "   Checking MCP endpoint..."
MCP_CHECK=$(curl -s -X POST http://localhost:8000/mcp \
    -H "Content-Type: application/json" \
    -d '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}' || echo "failed")

if [[ "$MCP_CHECK" == *"result"* ]]; then
    log "${GREEN}✅ MCP endpoint responding${NC}"
else
    log "${RED}❌ MCP endpoint not responding correctly${NC}"
    log "   Response: $MCP_CHECK"
    exit 1
fi

# Step 2: Environment validation
log "${YELLOW}2. Validating environment...${NC}"

# Get current workspace using python for JSON parsing
WORKSPACE_CHECK=$(curl -s http://localhost:8000/api/workspaces)
WORKSPACE_ID=$(echo "$WORKSPACE_CHECK" | python -c "
import sys, json
try:
    data = json.load(sys.stdin)
    for ws in data.get('workspaces', []):
        if ws.get('is_active'):
            print(ws['id'])
            exit(0)
    print('')
except:
    print('')
")

if [ -z "$WORKSPACE_ID" ]; then
    log "${RED}❌ No active workspace found${NC}"

    if [ "$ISOLATED" = true ]; then
        log "${YELLOW}   Creating isolated test workspace...${NC}"
        # Create test workspace with known permissions
        WORKSPACE_PAYLOAD='{
            "name": "MCP Test Workspace",
            "description": "Automated test workspace for MCP Wisdom validation",
            "is_active": true
        }'

        CREATED_WORKSPACE=$(curl -s -X POST http://localhost:8000/api/workspaces \
            -H "Content-Type: application/json" \
            -d "$WORKSPACE_PAYLOAD")

        WORKSPACE_ID=$(echo "$CREATED_WORKSPACE" | python -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('id', ''))
except:
    print('')
")

        # Add test permissions
        log "   Adding test permissions..."

        # Allow read to projects
        curl -s -X POST "http://localhost:8000/api/workspaces/$WORKSPACE_ID/permissions" \
            -H "Content-Type: application/json" \
            -d '{"path": "projects", "permission_type": "read", "rule_type": "allow", "description": "Test read access"}' > /dev/null

        # Allow write to private stuff
        curl -s -X POST "http://localhost:8000/api/workspaces/$WORKSPACE_ID/permissions" \
            -H "Content-Type: application/json" \
            -d '{"path": "private stuff", "permission_type": "write", "rule_type": "allow", "description": "Test write access"}' > /dev/null

        # Deny specific path for security testing
        curl -s -X POST "http://localhost:8000/api/workspaces/$WORKSPACE_ID/permissions" \
            -H "Content-Type: application/json" \
            -d '{"path": "materials/01_Introduction to Software Engineering", "permission_type": "read", "rule_type": "deny", "description": "Test deny rule"}' > /dev/null

        log "${GREEN}✅ Created isolated test environment${NC}"
    else
        log "${YELLOW}   Use --isolated flag to create test workspace${NC}"
        exit 1
    fi
else
    WORKSPACE_NAME=$(echo "$WORKSPACE_CHECK" | python -c "
import sys, json
try:
    data = json.load(sys.stdin)
    for ws in data.get('workspaces', []):
        if ws.get('is_active'):
            print(ws.get('name', 'Unknown'))
            exit(0)
    print('Unknown')
except:
    print('Unknown')
")
    log "${GREEN}✅ Using active workspace: $WORKSPACE_NAME (ID: $WORKSPACE_ID)${NC}"
fi

# Get permission count
PERMISSION_COUNT=$(curl -s "http://localhost:8000/api/workspaces/$WORKSPACE_ID/permissions" | python -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(len(data.get('permissions', [])))
except:
    print('0')
")
log "   Permissions configured: $PERMISSION_COUNT"

# Step 3: Run test suite
log ""
log "${YELLOW}3. Running MCP Wisdom test suite...${NC}"

cd "$BACKEND_DIR"

# Determine pytest options based on mode
PYTEST_OPTS="-v"
if [ "$COMPREHENSIVE" = true ]; then
    PYTEST_OPTS="$PYTEST_OPTS --tb=long"
    log "   Running comprehensive test suite..."
else
    PYTEST_OPTS="$PYTEST_OPTS --tb=short"
    log "   Running quick test suite..."
fi

# Run the tests
log "   Test command: python -m pytest tests/test_mcp_wisdom_comprehensive.py $PYTEST_OPTS"
log ""

# Use bash pipefail to capture pytest exit code properly
set -o pipefail
python -m pytest tests/test_mcp_wisdom_comprehensive.py $PYTEST_OPTS 2>&1 | tee -a "$DETAILED_LOG"
PYTEST_EXIT_CODE=$?
set +o pipefail

if [ $PYTEST_EXIT_CODE -eq 0 ]; then
    TEST_RESULT="PASSED"
    log ""
    log "${GREEN}✅ Test suite completed successfully${NC}"
else
    TEST_RESULT="FAILED"
    log ""
    log "${RED}❌ Test suite failed - check logs for details${NC}"
fi

# Step 4: Generate reports
log ""
log "${YELLOW}4. Generating test reports...${NC}"

# Check if JSON report was generated
if [ -f "$REPORT_FILE" ]; then
    log "${GREEN}✅ JSON report generated: $REPORT_FILE${NC}"

    # Extract key metrics from report
    TOTAL_OPERATIONS=$(python -c "
import json
try:
    with open('$REPORT_FILE') as f:
        data = json.load(f)
    print(data.get('performance', {}).get('total_operations', 0))
except:
    print('0')
")
    AVERAGE_TIME=$(python -c "
import json
try:
    with open('$REPORT_FILE') as f:
        data = json.load(f)
    print(data.get('performance', {}).get('average_time', 0))
except:
    print('0')
")
    WORKSPACE_NAME=$(python -c "
import json
try:
    with open('$REPORT_FILE') as f:
        data = json.load(f)
    print(data.get('environment', {}).get('workspace', 'Unknown'))
except:
    print('Unknown')
")

    log "   Workspace: $WORKSPACE_NAME"
    log "   Operations tested: $TOTAL_OPERATIONS"
    log "   Average response time: ${AVERAGE_TIME}s"

    # Check for warnings or errors in results
    if python -c "
import json
try:
    with open('$REPORT_FILE') as f:
        data = json.load(f)
    results = str(data.get('results', ''))
    if '⚠️' in results:
        exit(0)
    else:
        exit(1)
except:
    exit(1)
" > /dev/null 2>&1; then
        log "${YELLOW}⚠️  Some tests produced warnings - check detailed report${NC}"
    fi

    if python -c "
import json
try:
    with open('$REPORT_FILE') as f:
        data = json.load(f)
    results = str(data.get('results', ''))
    if '❌' in results:
        exit(0)
    else:
        exit(1)
except:
    exit(1)
" > /dev/null 2>&1; then
        log "${RED}❌ Some tests failed - check detailed report${NC}"
    fi

else
    log "${YELLOW}⚠️  JSON report not found - test may have failed early${NC}"
fi

# Step 5: Summary and recommendations
log ""
log "${YELLOW}5. Test Summary${NC}"
log "=================="
log "Test Result: $TEST_RESULT"
log "Detailed Log: $DETAILED_LOG"
log "JSON Report: $REPORT_FILE"
log ""

if [ "$TEST_RESULT" = "PASSED" ]; then
    log "${GREEN}🎉 MCP Wisdom is functioning correctly!${NC}"
    log ""
    log "✅ All MCP tools are operational"
    log "✅ Permission enforcement is working"
    log "✅ Security protections are active"
    log "✅ Performance is within acceptable limits"

    if [ "$ISOLATED" = true ]; then
        log ""
        log "${YELLOW}Note: Test was run in isolated environment${NC}"
        log "Consider running without --isolated flag to test production configuration"
    fi

else
    log "${RED}❌ MCP Wisdom has issues that need attention${NC}"
    log ""
    log "🔍 Troubleshooting steps:"
    log "   1. Check detailed log: $DETAILED_LOG"
    log "   2. Review JSON report: $REPORT_FILE"
    log "   3. Verify workspace permissions are correctly configured"
    log "   4. Check for known issues in tickets/ directory"
    log "   5. Restart services: docker-compose restart"

    # Show recent backend logs if available
    log ""
    log "Recent backend logs:"
    docker-compose logs backend --tail 10 2>/dev/null || log "Could not retrieve backend logs"
fi

# Step 6: Cleanup (if isolated)
if [ "$ISOLATED" = true ] && [ -n "$WORKSPACE_ID" ]; then
    log ""
    log "${YELLOW}6. Cleaning up isolated test environment...${NC}"

    # Delete the test workspace
    if curl -s -X DELETE "http://localhost:8000/api/workspaces/$WORKSPACE_ID" > /dev/null 2>&1; then
        log "${GREEN}✅ Cleaned up test workspace${NC}"
    else
        log "${YELLOW}⚠️  Could not clean up test workspace (ID: $WORKSPACE_ID)${NC}"
        log "   You may need to delete it manually from the UI"
    fi
fi

log ""
log "=== MCP Wisdom Test Suite Completed at $(date) ==="

# Exit with appropriate code
if [ "$TEST_RESULT" = "PASSED" ]; then
    exit 0
else
    exit 1
fi