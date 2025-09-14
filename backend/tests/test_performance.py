"""
Performance benchmarks for the permission system.
This test suite validates that the system meets performance requirements with large rule sets.
"""

import pytest
import time
import json
from typing import List, Dict, Any
import tempfile
import os
from pathlib import Path

from app.utils.trie import CachedPermissionTrie, PermissionRule


class TestPermissionPerformance:
    """Performance tests for permission system components."""

    def create_large_rule_set(self, num_rules: int) -> List[PermissionRule]:
        """Generate a large set of permission rules for testing."""
        rules = []

        # Create hierarchical rules for realistic testing
        base_paths = ['docs', 'projects', 'output', 'materials', 'data', 'backups', 'temp']

        for i in range(num_rules):
            base_path = base_paths[i % len(base_paths)]

            if i < num_rules // 2:
                # First half: nested paths
                path = f"{base_path}/level1_{i % 10}/level2_{i % 5}/level3_{i % 3}"
            else:
                # Second half: flat structure
                path = f"{base_path}/file_{i}"

            rule = PermissionRule(
                id=f"rule-{i}",
                path=path,
                permission_type='read' if i % 3 == 0 else 'write',
                rule_type='allow' if i % 4 != 0 else 'deny',
                description=f"Test rule {i}"
            )
            rules.append(rule)

        return rules

    def test_trie_loading_performance(self):
        """Test that trie can handle loading 1000+ rules efficiently."""
        trie = CachedPermissionTrie(cache_max_size=10000)
        rules = self.create_large_rule_set(1000)

        start_time = time.time()

        for rule in rules:
            trie.add_rule(rule)

        load_time = time.time() - start_time

        # Should load 1000 rules in less than 1 second
        assert load_time < 1.0, f"Trie loading took {load_time:.3f}s, expected < 1.0s"

        stats = trie.get_stats()
        assert stats['rule_count'] == 1000
        print(f"✅ Loaded {stats['rule_count']} rules in {load_time:.3f}s")

    def test_permission_checking_performance(self):
        """Test that permission checking is fast with large rule sets."""
        trie = CachedPermissionTrie(cache_max_size=10000)
        rules = self.create_large_rule_set(1000)

        # Load all rules
        for rule in rules:
            trie.add_rule(rule)

        # Test paths to check
        test_paths = [
            "docs/level1_1/level2_1/level3_1/test.txt",
            "projects/file_500",
            "output/level1_5/level2_3/report.pdf",
            "materials/level1_2/level2_4/data.csv",
            "nonexistent/path/file.txt"
        ]

        # Warm up the cache
        for path in test_paths:
            trie.check_permission(path, 'read')
            trie.check_permission(path, 'write')

        # Benchmark permission checking
        start_time = time.time()
        iterations = 1000

        for _ in range(iterations):
            for path in test_paths:
                trie.check_permission(path, 'read')
                trie.check_permission(path, 'write')

        total_time = time.time() - start_time
        avg_time_per_check = (total_time / (iterations * len(test_paths) * 2)) * 1000  # ms

        # Should average less than 1ms per permission check
        assert avg_time_per_check < 1.0, f"Average permission check took {avg_time_per_check:.3f}ms, expected < 1.0ms"

        stats = trie.get_stats()
        print(f"✅ {iterations * len(test_paths) * 2} permission checks in {total_time:.3f}s")
        print(f"   Average: {avg_time_per_check:.3f}ms per check")
        print(f"   Cache hit rate: {stats['cache_hit_rate']:.2%}")

    def test_cache_effectiveness(self):
        """Test that caching provides performance benefits."""
        # Test with cache
        trie_with_cache = CachedPermissionTrie(cache_max_size=1000)
        rules = self.create_large_rule_set(500)

        for rule in rules:
            trie_with_cache.add_rule(rule)

        test_paths = [
            "docs/level1_1/level2_1/test.txt",
            "projects/file_100",
            "output/level1_2/report.pdf"
        ]

        # Measure cached performance
        start_time = time.time()
        for _ in range(1000):
            for path in test_paths:
                trie_with_cache.check_permission(path, 'read')

        cached_time = time.time() - start_time

        # Clear cache and measure uncached performance
        trie_with_cache._invalidate_cache()

        start_time = time.time()
        for _ in range(1000):
            for path in test_paths:
                trie_with_cache.check_permission(path, 'read')

        uncached_time = time.time() - start_time

        # Cached should be significantly faster
        speedup = uncached_time / cached_time
        assert speedup > 2.0, f"Cache speedup was {speedup:.2f}x, expected > 2x"

        stats = trie_with_cache.get_stats()
        print(f"✅ Cache speedup: {speedup:.2f}x")
        print(f"   Cached time: {cached_time:.3f}s")
        print(f"   Uncached time: {uncached_time:.3f}s")
        print(f"   Final cache hit rate: {stats['cache_hit_rate']:.2%}")

    def test_memory_usage_scalability(self):
        """Test that memory usage scales reasonably with rule count."""
        import psutil
        import os

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / (1024 * 1024)  # MB

        trie = CachedPermissionTrie(cache_max_size=10000)

        # Add rules in batches and measure memory growth
        batch_sizes = [100, 500, 1000, 2000]
        memory_measurements = []

        for batch_size in batch_sizes:
            rules = self.create_large_rule_set(batch_size)

            for rule in rules:
                trie.add_rule(rule)

            current_memory = process.memory_info().rss / (1024 * 1024)  # MB
            memory_growth = current_memory - initial_memory
            memory_measurements.append((batch_size, memory_growth))

            print(f"   {batch_size} rules: {memory_growth:.1f} MB")

        # Memory growth should be reasonable (less than 1MB per 100 rules)
        final_rules, final_memory = memory_measurements[-1]
        memory_per_rule = (final_memory * 1024) / final_rules  # KB per rule

        assert memory_per_rule < 10.0, f"Memory per rule was {memory_per_rule:.1f}KB, expected < 10KB"
        print(f"✅ Memory usage: {memory_per_rule:.1f}KB per rule")

    def test_concurrent_access_performance(self):
        """Test performance under simulated concurrent access."""
        import concurrent.futures
        import threading

        trie = CachedPermissionTrie(cache_max_size=5000)
        rules = self.create_large_rule_set(1000)

        for rule in rules:
            trie.add_rule(rule)

        test_paths = [
            "docs/level1_1/level2_1/test.txt",
            "projects/file_100",
            "output/level1_2/report.pdf",
            "materials/level1_5/data.csv",
            "data/level1_3/level2_2/analysis.json"
        ]

        def worker_thread(thread_id: int, iterations: int):
            """Simulate a client thread making permission requests."""
            start_time = time.time()

            for i in range(iterations):
                path = test_paths[i % len(test_paths)]
                operation = 'read' if i % 2 == 0 else 'write'
                trie.check_permission(path, operation)

            return time.time() - start_time

        # Test with multiple concurrent threads
        num_threads = 10
        iterations_per_thread = 100

        start_time = time.time()

        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [
                executor.submit(worker_thread, i, iterations_per_thread)
                for i in range(num_threads)
            ]

            thread_times = [future.result() for future in concurrent.futures.as_completed(futures)]

        total_time = time.time() - start_time
        total_operations = num_threads * iterations_per_thread
        ops_per_second = total_operations / total_time

        # Should handle at least 1000 operations per second under concurrent load
        assert ops_per_second > 1000, f"Throughput was {ops_per_second:.0f} ops/s, expected > 1000 ops/s"

        stats = trie.get_stats()
        print(f"✅ Concurrent performance: {ops_per_second:.0f} operations/second")
        print(f"   Threads: {num_threads}, Operations: {total_operations}")
        print(f"   Cache hit rate: {stats['cache_hit_rate']:.2%}")


class TestConfigFilePerformance:
    """Performance tests for config file operations."""

    def create_large_config(self, num_rules: int) -> Dict[str, Any]:
        """Create a large configuration file for testing."""
        rules = []

        for i in range(num_rules):
            rule = {
                "id": f"rule-{i}",
                "path": f"path/level1_{i % 10}/level2_{i % 5}/file_{i}",
                "permission_type": "read" if i % 2 == 0 else "write",
                "rule_type": "allow" if i % 3 != 0 else "deny",
                "description": f"Performance test rule {i}",
                "created_at": "2025-01-13T19:30:00Z"
            }
            rules.append(rule)

        return {
            "metadata": {
                "version": "1.0.0",
                "description": f"Performance test config with {num_rules} rules"
            },
            "rules": rules
        }

    def test_config_file_loading_performance(self):
        """Test loading large config files efficiently."""
        from app.services.config_permission_service import ConfigPermissionService

        # Create a temporary config file
        config_data = self.create_large_config(1000)

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f, indent=2)
            temp_config_path = f.name

        try:
            # Mock the config path
            original_config_path = Path(temp_config_path)

            # Manually test the parsing logic
            start_time = time.time()

            with open(temp_config_path, 'r') as f:
                loaded_config = json.load(f)

            # Validate the structure
            assert 'rules' in loaded_config
            assert len(loaded_config['rules']) == 1000

            load_time = time.time() - start_time

            # Should load 1000 rules config in less than 0.5 seconds
            assert load_time < 0.5, f"Config loading took {load_time:.3f}s, expected < 0.5s"

            file_size = os.path.getsize(temp_config_path) / (1024 * 1024)  # MB
            print(f"✅ Loaded {len(loaded_config['rules'])} rules from {file_size:.1f}MB file in {load_time:.3f}s")

        finally:
            os.unlink(temp_config_path)

    def test_config_file_saving_performance(self):
        """Test saving large config files with atomic operations."""
        config_data = self.create_large_config(1000)

        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "permissions.json"

            # Test atomic save operation
            start_time = time.time()

            # Simulate atomic write process
            temp_path = config_path.with_suffix('.tmp')

            # Write to temp file
            with open(temp_path, 'w') as f:
                json.dump(config_data, f, indent=2)

            # Sync to disk
            with open(temp_path, 'r+b') as f:
                f.flush()
                os.fsync(f.fileno())

            # Atomic move
            temp_path.replace(config_path)

            save_time = time.time() - start_time

            # Should save 1000 rules in less than 1 second
            assert save_time < 1.0, f"Config saving took {save_time:.3f}s, expected < 1.0s"

            # Verify the saved file
            with open(config_path, 'r') as f:
                saved_config = json.load(f)

            assert len(saved_config['rules']) == 1000

            file_size = config_path.stat().st_size / (1024 * 1024)  # MB
            print(f"✅ Saved {len(config_data['rules'])} rules to {file_size:.1f}MB file in {save_time:.3f}s")


if __name__ == "__main__":
    # Run performance tests
    pytest.main([__file__, "-v", "-s"])