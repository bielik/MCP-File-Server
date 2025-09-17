"""
Performance Tests for Phase 3B
Phase 3B: Advanced UI & Full Workspace Experience

Performance benchmarks and stress tests for workspace operations,
batch APIs, and UI responsiveness requirements.
"""

import pytest
import time
import threading
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.main import app
from app.database import get_db
from app.models.workspace import Workspace, Permission
from .conftest import (
    test_db_session,
    clear_test_data,
    create_test_workspace,
    create_test_permission,
    PerformanceTimer,
    PerformanceBenchmark
)


class TestBatchAPIPerformance:
    """Test batch effective permissions API performance."""

    def test_batch_api_response_times(self, test_db_session: Session):
        """Test batch API meets response time targets for different load sizes."""
        clear_test_data(test_db_session)
        client = TestClient(app)

        app.dependency_overrides[get_db] = lambda: test_db_session

        try:
            # Create workspace with complex permission structure
            workspace = create_test_workspace(test_db_session, "Performance Workspace", is_active=True)

            # Create comprehensive permission set (realistic scenario)
            permission_patterns = [
                # Project access patterns
                {"path": "projects", "permission_type": "write", "rule_type": "allow"},
                {"path": "projects/archive", "permission_type": "read", "rule_type": "allow"},
                {"path": "projects/archive/sensitive", "permission_type": "read", "rule_type": "deny"},
                {"path": "projects/current", "permission_type": "write", "rule_type": "allow"},
                {"path": "projects/current/restricted", "permission_type": "write", "rule_type": "deny"},

                # Documentation patterns
                {"path": "docs", "permission_type": "read", "rule_type": "allow"},
                {"path": "docs/internal", "permission_type": "read", "rule_type": "deny"},
                {"path": "docs/internal/public", "permission_type": "read", "rule_type": "allow"},

                # Output patterns
                {"path": "output", "permission_type": "write", "rule_type": "allow"},
                {"path": "output/logs", "permission_type": "read", "rule_type": "allow"},
                {"path": "output/temp", "permission_type": "write", "rule_type": "allow"},

                # Materials patterns
                {"path": "materials", "permission_type": "read", "rule_type": "allow"},
                {"path": "materials/private", "permission_type": "read", "rule_type": "deny"},
                {"path": "materials/shared", "permission_type": "read", "rule_type": "allow"},

                # Complex nested patterns
                {"path": "complex/level1", "permission_type": "read", "rule_type": "allow"},
                {"path": "complex/level1/level2", "permission_type": "write", "rule_type": "allow"},
                {"path": "complex/level1/level2/level3", "permission_type": "read", "rule_type": "deny"},
                {"path": "complex/level1/level2/level3/level4", "permission_type": "read", "rule_type": "allow"},
            ]

            for pattern in permission_patterns:
                create_test_permission(test_db_session, workspace.id, **pattern)

            # Performance test scenarios
            performance_scenarios = [
                {
                    "name": "Small batch - 10 paths",
                    "path_count": 10,
                    "target_ms": 50,
                    "description": "Quick UI updates"
                },
                {
                    "name": "Medium batch - 50 paths",
                    "path_count": 50,
                    "target_ms": 75,
                    "description": "File explorer refresh"
                },
                {
                    "name": "Large batch - 150 paths",
                    "path_count": 150,
                    "target_ms": 100,
                    "description": "Full directory tree"
                },
                {
                    "name": "Extra large batch - 300 paths",
                    "path_count": 300,
                    "target_ms": 200,
                    "description": "Deep directory scan"
                }
            ]

            benchmark = PerformanceBenchmark("Batch API Performance")

            for scenario in performance_scenarios:
                print(f"\n🔥 Testing {scenario['name']}: {scenario['description']}")

                # Generate realistic test paths
                test_paths = self._generate_realistic_paths(scenario["path_count"])

                # Run multiple iterations for statistical accuracy
                response_times = []
                iterations = 10

                for i in range(iterations):
                    with PerformanceTimer(f"{scenario['name']}_iteration_{i+1}") as timer:
                        batch_request = {"paths": test_paths}
                        response = client.post(
                            f"/api/workspaces/{workspace.id}/effective-permissions:batch",
                            json=batch_request
                        )

                    assert response.status_code == 200, f"Batch API failed: {response.text}"
                    response_times.append(timer.elapsed_ms)

                    # Verify response completeness
                    results = response.json()["results"]
                    assert len(results) == scenario["path_count"]

                    # Verify all required fields are present
                    for result in results:
                        assert "path" in result
                        assert "status" in result
                        assert result["status"] in ["none", "read", "write", "denied"]

                # Statistical analysis
                avg_time = statistics.mean(response_times)
                median_time = statistics.median(response_times)
                p95_time = sorted(response_times)[int(0.95 * len(response_times))]
                min_time = min(response_times)
                max_time = max(response_times)

                print(f"📊 {scenario['name']} Statistics:")
                print(f"   Average: {avg_time:.2f}ms")
                print(f"   Median:  {median_time:.2f}ms")
                print(f"   P95:     {p95_time:.2f}ms")
                print(f"   Min:     {min_time:.2f}ms")
                print(f"   Max:     {max_time:.2f}ms")
                print(f"   Target:  {scenario['target_ms']}ms")

                # Record benchmark
                benchmark.record_metric(
                    f"{scenario['name']}_avg",
                    avg_time,
                    "ms",
                    scenario["target_ms"]
                )

                # Performance assertions
                assert avg_time < scenario["target_ms"], \
                    f"{scenario['name']} average time {avg_time:.2f}ms exceeds target {scenario['target_ms']}ms"

                assert p95_time < scenario["target_ms"] * 1.5, \
                    f"{scenario['name']} P95 time {p95_time:.2f}ms exceeds acceptable threshold"

            benchmark.print_summary()

        finally:
            app.dependency_overrides.clear()

    def test_batch_api_concurrent_load(self, test_db_session: Session):
        """Test batch API under concurrent load from multiple clients."""
        clear_test_data(test_db_session)
        client = TestClient(app)

        app.dependency_overrides[get_db] = lambda: test_db_session

        try:
            workspace = create_test_workspace(test_db_session, "Concurrent Load Test", is_active=True)

            # Create moderate permission set
            for i in range(20):
                create_test_permission(
                    test_db_session,
                    workspace.id,
                    path=f"path{i}",
                    permission_type="read" if i % 2 == 0 else "write",
                    rule_type="allow"
                )

            # Concurrent load test parameters
            num_threads = 10
            requests_per_thread = 5
            test_paths = self._generate_realistic_paths(30)

            def make_batch_request(thread_id: int) -> dict:
                """Make a batch request and return timing info."""
                thread_times = []

                for request_id in range(requests_per_thread):
                    start_time = time.time()

                    batch_request = {"paths": test_paths}
                    response = client.post(
                        f"/api/workspaces/{workspace.id}/effective-permissions:batch",
                        json=batch_request
                    )

                    elapsed_ms = (time.time() - start_time) * 1000

                    assert response.status_code == 200, \
                        f"Thread {thread_id}, Request {request_id} failed: {response.text}"

                    results = response.json()["results"]
                    assert len(results) == len(test_paths)

                    thread_times.append(elapsed_ms)

                return {
                    "thread_id": thread_id,
                    "times": thread_times,
                    "avg_time": statistics.mean(thread_times),
                    "max_time": max(thread_times)
                }

            # Execute concurrent requests
            print(f"\n🚀 Running concurrent load test: {num_threads} threads, {requests_per_thread} requests each")

            start_time = time.time()
            with ThreadPoolExecutor(max_workers=num_threads) as executor:
                futures = [executor.submit(make_batch_request, i) for i in range(num_threads)]
                thread_results = [future.result() for future in as_completed(futures)]

            total_time = time.time() - start_time
            total_requests = num_threads * requests_per_thread

            # Analyze results
            all_times = []
            for result in thread_results:
                all_times.extend(result["times"])

            avg_response_time = statistics.mean(all_times)
            p95_response_time = sorted(all_times)[int(0.95 * len(all_times))]
            requests_per_second = total_requests / total_time

            print(f"📈 Concurrent Load Results:")
            print(f"   Total requests: {total_requests}")
            print(f"   Total time: {total_time:.2f}s")
            print(f"   Requests/sec: {requests_per_second:.2f}")
            print(f"   Avg response: {avg_response_time:.2f}ms")
            print(f"   P95 response: {p95_response_time:.2f}ms")

            # Performance assertions for concurrent load
            assert avg_response_time < 150, f"Average response time {avg_response_time:.2f}ms too high under concurrent load"
            assert p95_response_time < 300, f"P95 response time {p95_response_time:.2f}ms too high under concurrent load"
            assert requests_per_second > 20, f"Throughput {requests_per_second:.2f} req/s too low"

        finally:
            app.dependency_overrides.clear()

    def _generate_realistic_paths(self, count: int) -> list[str]:
        """Generate realistic file paths for testing."""
        base_patterns = [
            "projects/webapp/src",
            "projects/webapp/tests",
            "projects/api/controllers",
            "projects/api/models",
            "materials/courses/week",
            "materials/assignments",
            "docs/api",
            "docs/user_guides",
            "output/reports",
            "output/logs",
            "complex/level1/level2",
            "temp/cache",
            "temp/uploads"
        ]

        file_extensions = [".py", ".js", ".json", ".md", ".txt", ".pdf", ".xlsx"]
        paths = []

        for i in range(count):
            base = base_patterns[i % len(base_patterns)]
            ext = file_extensions[i % len(file_extensions)]
            paths.append(f"{base}/file_{i}{ext}")

        return paths


class TestWorkspaceSwitchingPerformance:
    """Test workspace activation and switching performance."""

    def test_workspace_activation_performance(self, test_db_session: Session):
        """Test workspace activation meets timing requirements."""
        clear_test_data(test_db_session)
        client = TestClient(app)

        app.dependency_overrides[get_db] = lambda: test_db_session

        try:
            # Create multiple workspaces with varying permission counts
            workspaces = []
            permission_counts = [10, 50, 100, 200]

            for i, perm_count in enumerate(permission_counts):
                workspace = create_test_workspace(
                    test_db_session,
                    f"Workspace_{i+1}_with_{perm_count}_permissions",
                    is_active=False
                )

                # Add permissions
                for j in range(perm_count):
                    create_test_permission(
                        test_db_session,
                        workspace.id,
                        path=f"path{j}/subpath{j%10}",
                        permission_type="read" if j % 2 == 0 else "write",
                        rule_type="allow"
                    )

                workspaces.append((workspace, perm_count))

            benchmark = PerformanceBenchmark("Workspace Switching Performance")

            # Test activation performance for each workspace size
            for workspace, perm_count in workspaces:
                print(f"\n⚡ Testing workspace activation with {perm_count} permissions")

                # Multiple activation attempts for statistical accuracy
                activation_times = []
                iterations = 5

                for iteration in range(iterations):
                    with PerformanceTimer(f"activate_workspace_{perm_count}_perms_iter_{iteration+1}") as timer:
                        response = client.post(f"/api/workspaces/{workspace.id}/activate")

                    assert response.status_code == 200, f"Activation failed: {response.text}"
                    activation_times.append(timer.elapsed_ms)

                    # Verify activation worked
                    activated_workspace = response.json()
                    assert activated_workspace["is_active"] is True

                    # Small delay between iterations to avoid potential conflicts
                    time.sleep(0.1)

                avg_time = statistics.mean(activation_times)
                max_time = max(activation_times)

                print(f"   Average activation time: {avg_time:.2f}ms")
                print(f"   Maximum activation time: {max_time:.2f}ms")

                # Record benchmark
                benchmark.record_metric(
                    f"activation_{perm_count}_permissions",
                    avg_time,
                    "ms",
                    200  # Target: under 200ms
                )

                # Performance assertions (should be under 200ms for good UX)
                assert avg_time < 200, f"Average activation time {avg_time:.2f}ms exceeds 200ms target"
                assert max_time < 400, f"Max activation time {max_time:.2f}ms exceeds 400ms threshold"

            # Test rapid workspace switching
            print(f"\n🔄 Testing rapid workspace switching")
            switching_sequence = workspaces[:3]  # Use first 3 workspaces
            switch_times = []

            for i in range(len(switching_sequence) * 2):  # Do two complete cycles
                workspace, _ = switching_sequence[i % len(switching_sequence)]

                with PerformanceTimer(f"rapid_switch_{i+1}") as timer:
                    response = client.post(f"/api/workspaces/{workspace.id}/activate")

                assert response.status_code == 200
                switch_times.append(timer.elapsed_ms)

            avg_switch_time = statistics.mean(switch_times)
            print(f"   Average rapid switch time: {avg_switch_time:.2f}ms")

            benchmark.record_metric("rapid_switching", avg_switch_time, "ms", 150)
            benchmark.print_summary()

            # Rapid switching should be even faster (under 150ms)
            assert avg_switch_time < 150, f"Rapid switching average {avg_switch_time:.2f}ms too slow"

        finally:
            app.dependency_overrides.clear()


class TestUIResponsivenessSimulation:
    """Test scenarios that simulate UI interaction patterns."""

    def test_permission_editor_usage_pattern(self, test_db_session: Session):
        """Simulate typical permission editor usage patterns."""
        clear_test_data(test_db_session)
        client = TestClient(app)

        app.dependency_overrides[get_db] = lambda: test_db_session

        try:
            workspace = create_test_workspace(test_db_session, "UI Simulation Workspace", is_active=True)

            # Simulate adding permissions one by one (as user builds rules)
            permission_build_times = []
            file_tree_refresh_times = []

            # Simulate building a permission set progressively
            permission_scenarios = [
                {"path": "projects", "permission_type": "write", "rule_type": "allow"},
                {"path": "materials", "permission_type": "read", "rule_type": "allow"},
                {"path": "materials/private", "permission_type": "read", "rule_type": "deny"},
                {"path": "output", "permission_type": "write", "rule_type": "allow"},
                {"path": "temp", "permission_type": "write", "rule_type": "allow"},
            ]

            print(f"\n🎨 Simulating permission editor workflow")

            for i, perm_data in enumerate(permission_scenarios):
                # Time permission creation (user adds rule)
                with PerformanceTimer(f"add_permission_{i+1}") as add_timer:
                    response = client.post(f"/api/workspaces/{workspace.id}/permissions", json=perm_data)

                assert response.status_code == 201
                permission_build_times.append(add_timer.elapsed_ms)

                # Simulate file tree refresh after each permission addition
                test_paths = [
                    "projects/webapp/src/main.py",
                    "projects/api/server.js",
                    "materials/course_1/notes.pdf",
                    "materials/private/grades.xlsx",
                    "output/reports/summary.pdf",
                    "temp/cache/data.json"
                ]

                with PerformanceTimer(f"refresh_tree_{i+1}") as refresh_timer:
                    batch_request = {"paths": test_paths}
                    response = client.post(
                        f"/api/workspaces/{workspace.id}/effective-permissions:batch",
                        json=batch_request
                    )

                assert response.status_code == 200
                file_tree_refresh_times.append(refresh_timer.elapsed_ms)

                print(f"   Step {i+1}: Add permission ({add_timer.elapsed_ms:.1f}ms) + Refresh tree ({refresh_timer.elapsed_ms:.1f}ms)")

            # Analyze UI responsiveness
            avg_permission_add = statistics.mean(permission_build_times)
            avg_tree_refresh = statistics.mean(file_tree_refresh_times)

            print(f"\n📊 UI Responsiveness Analysis:")
            print(f"   Avg permission add: {avg_permission_add:.2f}ms")
            print(f"   Avg tree refresh: {avg_tree_refresh:.2f}ms")

            # UI responsiveness targets (under 100ms feels instant to users)
            assert avg_permission_add < 100, f"Permission addition {avg_permission_add:.2f}ms too slow for good UX"
            assert avg_tree_refresh < 80, f"Tree refresh {avg_tree_refresh:.2f}ms too slow for responsive UI"

            # Test permission deletion workflow
            response = client.get(f"/api/workspaces/{workspace.id}/permissions")
            permissions = response.json()["permissions"]

            deletion_times = []
            for permission in permissions[:3]:  # Delete first 3
                with PerformanceTimer(f"delete_permission_{permission['id']}") as delete_timer:
                    response = client.delete(f"/api/permissions/{permission['id']}")

                assert response.status_code == 204
                deletion_times.append(delete_timer.elapsed_ms)

            avg_deletion = statistics.mean(deletion_times)
            print(f"   Avg permission deletion: {avg_deletion:.2f}ms")

            assert avg_deletion < 50, f"Permission deletion {avg_deletion:.2f}ms too slow"

        finally:
            app.dependency_overrides.clear()

    def test_memory_usage_stability(self, test_db_session: Session):
        """Test for memory leaks during extended operations."""
        clear_test_data(test_db_session)
        client = TestClient(app)

        app.dependency_overrides[get_db] = lambda: test_db_session

        try:
            workspace = create_test_workspace(test_db_session, "Memory Test Workspace", is_active=True)

            # Create substantial permission set
            for i in range(100):
                create_test_permission(
                    test_db_session,
                    workspace.id,
                    path=f"path{i}/level{i%5}",
                    permission_type="read" if i % 2 == 0 else "write",
                    rule_type="allow"
                )

            # Simulate extended usage
            test_paths = [f"path{i}/level{i%5}/file.txt" for i in range(50)]
            batch_request = {"paths": test_paths}

            print(f"\n🧠 Testing memory stability over extended usage")

            # Run many iterations to detect memory issues
            iterations = 100
            response_times = []

            for i in range(iterations):
                start_time = time.time()

                response = client.post(
                    f"/api/workspaces/{workspace.id}/effective-permissions:batch",
                    json=batch_request
                )

                elapsed_ms = (time.time() - start_time) * 1000

                assert response.status_code == 200
                response_times.append(elapsed_ms)

                if (i + 1) % 20 == 0:
                    avg_recent = statistics.mean(response_times[-20:])
                    print(f"   Iteration {i+1}: Recent avg {avg_recent:.2f}ms")

            # Analyze for performance degradation (sign of memory issues)
            first_quarter = response_times[:25]
            last_quarter = response_times[-25:]

            avg_first_quarter = statistics.mean(first_quarter)
            avg_last_quarter = statistics.mean(last_quarter)

            performance_degradation = (avg_last_quarter - avg_first_quarter) / avg_first_quarter * 100

            print(f"   First quarter avg: {avg_first_quarter:.2f}ms")
            print(f"   Last quarter avg: {avg_last_quarter:.2f}ms")
            print(f"   Performance change: {performance_degradation:+.1f}%")

            # Should not degrade more than 20% over extended usage
            assert performance_degradation < 20, \
                f"Performance degraded {performance_degradation:.1f}% - possible memory leak"

        finally:
            app.dependency_overrides.clear()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--benchmark"])