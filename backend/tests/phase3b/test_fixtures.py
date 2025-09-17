"""
Test Data Fixtures for Phase 3B Testing

This module provides comprehensive test data fixtures that can be used across
all Phase 3B tests. The fixtures are designed to be realistic, consistent,
and cover all edge cases required for thorough testing.

For independent testers:
- All fixtures are self-contained and require no external dependencies
- Data is generated programmatically for consistency across test runs
- Fixtures include both simple and complex scenarios
- All data follows the exact schema used in production
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict

from app.models.workspace import Workspace, Permission
from app.schemas.workspace import WorkspaceCreate, PermissionCreate


@dataclass
class TestScenarioData:
    """Container for complete test scenario data."""
    name: str
    description: str
    workspaces: List[Dict[str, Any]]
    permissions: List[Dict[str, Any]]
    expected_outcomes: Dict[str, Any]
    performance_targets: Dict[str, int]


class TestDataFixtures:
    """
    Comprehensive test data fixture generator.

    This class provides methods to generate realistic test data for all
    Phase 3B testing scenarios including workspace management, permission
    systems, and performance testing.
    """

    @staticmethod
    def create_basic_workspace_data() -> Dict[str, Any]:
        """Create basic workspace data for simple tests."""
        return {
            "name": "Basic Test Workspace",
            "description": "A basic workspace for simple testing scenarios",
            "is_active": False
        }

    @staticmethod
    def create_complex_workspace_data() -> Dict[str, Any]:
        """Create complex workspace data with edge cases."""
        return {
            "name": "Complex Test Workspace with Unicode 测试空间",
            "description": "A complex workspace with special characters and edge cases for thorough testing",
            "is_active": True
        }

    @staticmethod
    def create_workspace_list(count: int = 5) -> List[Dict[str, Any]]:
        """Create a list of diverse workspaces for testing."""
        workspaces = []

        workspace_templates = [
            {
                "name": "Development Environment",
                "description": "Workspace for active development with full access to projects",
                "is_active": True,
                "category": "development"
            },
            {
                "name": "Research Analysis",
                "description": "Read-only workspace for research and data analysis",
                "is_active": False,
                "category": "research"
            },
            {
                "name": "Presentation Mode",
                "description": "Minimal workspace for presentations and demos",
                "is_active": False,
                "category": "presentation"
            },
            {
                "name": "Testing & QA",
                "description": "Isolated workspace for testing and quality assurance",
                "is_active": False,
                "category": "testing"
            },
            {
                "name": "Documentation",
                "description": "Workspace focused on documentation and knowledge management",
                "is_active": False,
                "category": "documentation"
            }
        ]

        for i in range(count):
            template = workspace_templates[i % len(workspace_templates)]
            workspace = {
                **template,
                "name": f"{template['name']} {i + 1}" if i >= len(workspace_templates) else template["name"]
            }

            # Only one workspace should be active
            if i > 0:
                workspace["is_active"] = False

            workspaces.append(workspace)

        return workspaces

    @staticmethod
    def create_permission_scenarios() -> Dict[str, List[Dict[str, Any]]]:
        """
        Create comprehensive permission scenarios for testing precedence rules.

        Returns:
            Dictionary of scenario names to permission lists
        """
        scenarios = {
            "basic_allow_deny": [
                {
                    "path": "materials",
                    "permission_type": "read",
                    "rule_type": "allow",
                    "description": "Allow read access to materials directory"
                },
                {
                    "path": "projects",
                    "permission_type": "write",
                    "rule_type": "allow",
                    "description": "Allow write access to projects directory"
                },
                {
                    "path": "private",
                    "permission_type": "read",
                    "rule_type": "deny",
                    "description": "Deny access to private directory"
                }
            ],

            "precedence_specificity": [
                # Test specificity: child overrides parent
                {
                    "path": "materials",
                    "permission_type": "read",
                    "rule_type": "allow",
                    "description": "Allow read access to all materials"
                },
                {
                    "path": "materials/sensitive",
                    "permission_type": "read",
                    "rule_type": "deny",
                    "description": "Deny access to sensitive materials (child overrides parent)"
                },
                {
                    "path": "materials/sensitive/public",
                    "permission_type": "read",
                    "rule_type": "allow",
                    "description": "Allow access to public files in sensitive dir (grandchild overrides)"
                }
            ],

            "deny_wins": [
                # Test deny wins over allow at same specificity
                {
                    "path": "projects/shared",
                    "permission_type": "read",
                    "rule_type": "allow",
                    "description": "Allow read access to shared projects"
                },
                {
                    "path": "projects/shared",
                    "permission_type": "read",
                    "rule_type": "deny",
                    "description": "Deny read access to shared projects (deny wins)"
                }
            ],

            "write_implies_read": [
                # Test write permission implies read
                {
                    "path": "output",
                    "permission_type": "write",
                    "rule_type": "allow",
                    "description": "Allow write access (should imply read)"
                }
                # No explicit read rule - should be implied
            ],

            "complex_hierarchy": [
                # Complex real-world scenario
                {
                    "path": "workspace",
                    "permission_type": "read",
                    "rule_type": "allow",
                    "description": "Base workspace read access"
                },
                {
                    "path": "workspace/public",
                    "permission_type": "write",
                    "rule_type": "allow",
                    "description": "Public area with write access"
                },
                {
                    "path": "workspace/restricted",
                    "permission_type": "read",
                    "rule_type": "deny",
                    "description": "Restricted area - no access"
                },
                {
                    "path": "workspace/restricted/admin",
                    "permission_type": "write",
                    "rule_type": "allow",
                    "description": "Admin area with special access"
                },
                {
                    "path": "workspace/temp",
                    "permission_type": "write",
                    "rule_type": "allow",
                    "description": "Temporary files area"
                },
                {
                    "path": "workspace/temp/logs",
                    "permission_type": "read",
                    "rule_type": "deny",
                    "description": "No access to temp logs"
                }
            ]
        }

        return scenarios

    @staticmethod
    def create_realistic_file_tree() -> List[str]:
        """
        Create a realistic file tree structure that mirrors actual project layouts.

        Returns:
            List of file paths for testing
        """
        return [
            # Materials structure - course content
            "materials/README.md",
            "materials/course-overview.pdf",
            "materials/syllabus.docx",
            "materials/01_introduction/slides.pptx",
            "materials/01_introduction/exercises.pdf",
            "materials/01_introduction/solutions.py",
            "materials/02_fundamentals/theory.md",
            "materials/02_fundamentals/examples.py",
            "materials/02_fundamentals/homework.ipynb",
            "materials/03_advanced/concepts.md",
            "materials/03_advanced/demo.ipynb",
            "materials/03_advanced/project-specs.pdf",
            "materials/sensitive/admin-notes.txt",
            "materials/sensitive/answer-keys.pdf",
            "materials/sensitive/grades.xlsx",
            "materials/sensitive/public/general-info.md",

            # Projects structure - development work
            "projects/README.md",
            "projects/webapp/requirements.txt",
            "projects/webapp/src/main.py",
            "projects/webapp/src/models.py",
            "projects/webapp/src/views.py",
            "projects/webapp/src/utils.py",
            "projects/webapp/tests/test_main.py",
            "projects/webapp/tests/test_models.py",
            "projects/webapp/tests/test_utils.py",
            "projects/webapp/static/css/styles.css",
            "projects/webapp/static/js/app.js",
            "projects/webapp/templates/base.html",
            "projects/mobile-app/package.json",
            "projects/mobile-app/src/App.tsx",
            "projects/mobile-app/src/components/Header.tsx",
            "projects/mobile-app/src/components/Footer.tsx",
            "projects/mobile-app/src/screens/Home.tsx",
            "projects/mobile-app/tests/App.test.tsx",
            "projects/mobile-app/tests/components/Header.test.tsx",
            "projects/data-analysis/requirements.txt",
            "projects/data-analysis/notebooks/exploration.ipynb",
            "projects/data-analysis/notebooks/visualization.ipynb",
            "projects/data-analysis/scripts/preprocess.py",
            "projects/data-analysis/scripts/analyze.py",
            "projects/data-analysis/data/raw/dataset.csv",
            "projects/data-analysis/data/processed/cleaned.csv",
            "projects/data-analysis/results/summary.json",
            "projects/shared/common-utils.py",
            "projects/shared/config.yaml",
            "projects/shared/documentation.md",

            # Private structure - sensitive data
            "private/config/api-keys.json",
            "private/config/database.env",
            "private/config/secrets.yaml",
            "private/personal/notes.md",
            "private/personal/todo.txt",
            "private/personal/contacts.csv",
            "private/admin/user-management.json",
            "private/admin/system-config.yaml",
            "private/admin/backup-schedule.cron",

            # Output structure - generated content
            "output/reports/weekly-summary.pdf",
            "output/reports/performance-metrics.json",
            "output/reports/analysis-results.html",
            "output/exports/data-export-2025-01.csv",
            "output/exports/configuration-backup.json",
            "output/logs/application.log",
            "output/logs/error.log",
            "output/logs/access.log",
            "output/generated/charts/performance.png",
            "output/generated/charts/usage-stats.svg",
            "output/generated/documents/report.docx",

            # Temporary structure - transient files
            "temp/cache/session-data.json",
            "temp/cache/api-responses.cache",
            "temp/uploads/document-2025-01-15.pdf",
            "temp/uploads/image-upload.jpg",
            "temp/processed/batch-job-123.json",
            "temp/processed/conversion-output.xml",
            "temp/logs/debug.log",
            "temp/logs/temp-operations.log",

            # Workspace structure - collaborative areas
            "workspace/README.md",
            "workspace/project-docs/specifications.md",
            "workspace/project-docs/architecture.md",
            "workspace/project-docs/api-docs.json",
            "workspace/public/shared-resources.md",
            "workspace/public/team-calendar.ics",
            "workspace/public/meeting-notes.md",
            "workspace/restricted/confidential.pdf",
            "workspace/restricted/legal-docs.docx",
            "workspace/restricted/admin/system-access.json",
            "workspace/restricted/admin/user-roles.yaml",
            "workspace/temp/scratch.txt",
            "workspace/temp/draft-document.md",
            "workspace/temp/logs/workspace-activity.log",

            # Edge cases - special characters and deep nesting
            "files with spaces/document.txt",
            "files-with-hyphens/config.yaml",
            "files_with_underscores/data.json",
            "unicode-测试/文件.txt",
            "very/deeply/nested/directory/structure/that/goes/many/levels/deep/final-file.txt",
            "mixed-Case-FILE.PDF",
            "file.with.multiple.dots.txt",
            ".hidden-file",
            ".hidden-directory/.config",
            "UPPER_CASE_DIRECTORY/file.txt",
        ]

    @staticmethod
    def create_batch_test_paths(size: int = 150) -> List[str]:
        """
        Create a large list of paths for batch API performance testing.

        Args:
            size: Number of paths to generate

        Returns:
            List of test paths
        """
        file_tree = TestDataFixtures.create_realistic_file_tree()

        # If we need more paths than available, generate additional ones
        if size > len(file_tree):
            additional_paths = []
            base_paths = ["materials", "projects", "private", "output", "temp"]
            file_extensions = [".txt", ".py", ".md", ".json", ".pdf", ".docx", ".csv"]

            for i in range(size - len(file_tree)):
                base_path = base_paths[i % len(base_paths)]
                subdir = f"generated_{i // 50}"
                filename = f"file_{i:04d}{file_extensions[i % len(file_extensions)]}"
                additional_paths.append(f"{base_path}/{subdir}/{filename}")

            file_tree.extend(additional_paths)

        return file_tree[:size]

    @staticmethod
    def create_test_scenarios() -> Dict[str, TestScenarioData]:
        """
        Create comprehensive test scenarios combining workspaces and permissions.

        Returns:
            Dictionary of scenario names to complete test scenario data
        """
        scenarios = {}

        # Scenario 1: Development Environment
        dev_workspaces = [
            {
                "name": "Development Workspace",
                "description": "Active development environment with comprehensive permissions",
                "is_active": True
            }
        ]

        dev_permissions = [
            {
                "path": "projects",
                "permission_type": "write",
                "rule_type": "allow",
                "description": "Full access to projects for development"
            },
            {
                "path": "materials",
                "permission_type": "read",
                "rule_type": "allow",
                "description": "Read access to reference materials"
            },
            {
                "path": "output",
                "permission_type": "write",
                "rule_type": "allow",
                "description": "Write access to output directory"
            },
            {
                "path": "materials/sensitive",
                "permission_type": "read",
                "rule_type": "deny",
                "description": "Block access to sensitive materials"
            }
        ]

        scenarios["development_environment"] = TestScenarioData(
            name="Development Environment",
            description="Complete development setup with typical permissions",
            workspaces=dev_workspaces,
            permissions=dev_permissions,
            expected_outcomes={
                "projects/webapp/src/main.py": {"status": "write", "rule_matched": True},
                "materials/course-overview.pdf": {"status": "read", "rule_matched": True},
                "materials/sensitive/grades.xlsx": {"status": "denied", "rule_matched": True},
                "output/reports/summary.pdf": {"status": "write", "rule_matched": True},
                "private/config/api-keys.json": {"status": "denied", "rule_matched": False}
            },
            performance_targets={
                "batch_api_50_paths": 50,
                "batch_api_150_paths": 100,
                "workspace_activation": 200
            }
        )

        # Scenario 2: Multi-workspace Research Environment
        research_workspaces = [
            {
                "name": "Primary Research",
                "description": "Main research workspace with data access",
                "is_active": False
            },
            {
                "name": "Analysis Workspace",
                "description": "Data analysis and visualization workspace",
                "is_active": True
            },
            {
                "name": "Publication Workspace",
                "description": "Document preparation and publication workspace",
                "is_active": False
            }
        ]

        research_permissions = [
            # Primary Research permissions
            {
                "workspace_name": "Primary Research",
                "path": "materials",
                "permission_type": "read",
                "rule_type": "allow",
                "description": "Access to research materials"
            },
            {
                "workspace_name": "Primary Research",
                "path": "projects/data-analysis",
                "permission_type": "read",
                "rule_type": "allow",
                "description": "Read access to analysis code"
            },

            # Analysis Workspace permissions
            {
                "workspace_name": "Analysis Workspace",
                "path": "projects/data-analysis",
                "permission_type": "write",
                "rule_type": "allow",
                "description": "Full access to analysis workspace"
            },
            {
                "workspace_name": "Analysis Workspace",
                "path": "output",
                "permission_type": "write",
                "rule_type": "allow",
                "description": "Output access for analysis results"
            },

            # Publication Workspace permissions
            {
                "workspace_name": "Publication Workspace",
                "path": "materials",
                "permission_type": "read",
                "rule_type": "allow",
                "description": "Reference materials for publication"
            },
            {
                "workspace_name": "Publication Workspace",
                "path": "output/reports",
                "permission_type": "read",
                "rule_type": "allow",
                "description": "Access to generated reports"
            }
        ]

        scenarios["multi_workspace_research"] = TestScenarioData(
            name="Multi-workspace Research",
            description="Complex research environment with workspace isolation",
            workspaces=research_workspaces,
            permissions=research_permissions,
            expected_outcomes={
                "workspace_switching_time": 150,
                "permission_isolation": True,
                "context_preservation": True
            },
            performance_targets={
                "workspace_switch_time": 200,
                "batch_api_cross_workspace": 120,
                "ui_refresh_time": 150
            }
        )

        # Scenario 3: Edge Cases and Security Testing
        security_workspaces = [
            {
                "name": "Security Test Workspace",
                "description": "Workspace for testing edge cases and security scenarios",
                "is_active": True
            }
        ]

        security_permissions = [
            # Path traversal attempts (should be blocked at validation level)
            {
                "path": "materials/../private",
                "permission_type": "read",
                "rule_type": "allow",
                "description": "Attempted path traversal (should be rejected)"
            },

            # Unicode and special characters
            {
                "path": "unicode-测试",
                "permission_type": "read",
                "rule_type": "allow",
                "description": "Unicode path handling"
            },
            {
                "path": "files with spaces",
                "permission_type": "read",
                "rule_type": "allow",
                "description": "Spaces in paths"
            },

            # Deep nesting
            {
                "path": "very/deeply/nested/directory/structure",
                "permission_type": "read",
                "rule_type": "allow",
                "description": "Deep directory nesting"
            },

            # Case sensitivity
            {
                "path": "UPPER_CASE_DIRECTORY",
                "permission_type": "read",
                "rule_type": "allow",
                "description": "Case sensitivity testing"
            },
            {
                "path": "upper_case_directory",
                "permission_type": "read",
                "rule_type": "deny",
                "description": "Different case should be separate rule"
            }
        ]

        scenarios["edge_cases_security"] = TestScenarioData(
            name="Edge Cases and Security",
            description="Comprehensive edge case and security testing scenarios",
            workspaces=security_workspaces,
            permissions=security_permissions,
            expected_outcomes={
                "path_traversal_blocked": True,
                "unicode_support": True,
                "space_handling": True,
                "case_sensitivity": True,
                "deep_nesting_support": True
            },
            performance_targets={
                "validation_time": 10,
                "error_handling_time": 50,
                "security_check_time": 25
            }
        )

        return scenarios

    @staticmethod
    def create_performance_test_data() -> Dict[str, Dict[str, Any]]:
        """
        Create specialized data sets for performance testing.

        Returns:
            Dictionary of performance test scenarios
        """
        return {
            "small_batch": {
                "name": "Small Batch Performance",
                "description": "10 paths for baseline performance",
                "paths": TestDataFixtures.create_batch_test_paths(10),
                "expected_time_ms": 25,
                "threshold_ms": 50
            },

            "medium_batch": {
                "name": "Medium Batch Performance",
                "description": "50 paths for typical usage",
                "paths": TestDataFixtures.create_batch_test_paths(50),
                "expected_time_ms": 45,
                "threshold_ms": 75
            },

            "large_batch": {
                "name": "Large Batch Performance",
                "description": "150 paths for stress testing",
                "paths": TestDataFixtures.create_batch_test_paths(150),
                "expected_time_ms": 85,
                "threshold_ms": 100
            },

            "duplicate_paths": {
                "name": "Duplicate Path Caching",
                "description": "Same path repeated for cache testing",
                "paths": ["materials/common/file.txt"] * 100,
                "expected_time_ms": 15,
                "threshold_ms": 25,
                "tests_caching": True
            },

            "mixed_depths": {
                "name": "Mixed Path Depths",
                "description": "Paths of varying depths for complexity testing",
                "paths": [
                    "root.txt",
                    "level1/file.txt",
                    "level1/level2/file.txt",
                    "level1/level2/level3/file.txt",
                    "level1/level2/level3/level4/file.txt",
                    "level1/level2/level3/level4/level5/deep.txt"
                ] * 25,  # Repeat to create 150 paths
                "expected_time_ms": 65,
                "threshold_ms": 90
            }
        }

    @staticmethod
    def export_test_data(file_path: str, scenario_name: str = "all") -> None:
        """
        Export test data to JSON file for external use or debugging.

        Args:
            file_path: Path where to save the test data
            scenario_name: Name of specific scenario to export, or "all"
        """
        if scenario_name == "all":
            data = {
                "scenarios": {name: asdict(scenario)
                             for name, scenario in TestDataFixtures.create_test_scenarios().items()},
                "permission_scenarios": TestDataFixtures.create_permission_scenarios(),
                "file_tree": TestDataFixtures.create_realistic_file_tree(),
                "performance_data": TestDataFixtures.create_performance_test_data(),
                "metadata": {
                    "generated_at": datetime.utcnow().isoformat(),
                    "version": "1.0",
                    "description": "Phase 3B comprehensive test data fixtures"
                }
            }
        else:
            scenarios = TestDataFixtures.create_test_scenarios()
            if scenario_name not in scenarios:
                raise ValueError(f"Unknown scenario: {scenario_name}")
            data = asdict(scenarios[scenario_name])

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)

    @staticmethod
    def validate_test_data() -> Dict[str, bool]:
        """
        Validate that all test data fixtures are properly formatted.

        Returns:
            Dictionary of validation results
        """
        validation_results = {}

        try:
            # Test workspace data
            workspaces = TestDataFixtures.create_workspace_list()
            validation_results["workspace_list"] = all(
                isinstance(w, dict) and "name" in w and "description" in w
                for w in workspaces
            )

            # Test permission scenarios
            scenarios = TestDataFixtures.create_permission_scenarios()
            validation_results["permission_scenarios"] = all(
                isinstance(perms, list) and all(
                    isinstance(p, dict) and all(
                        key in p for key in ["path", "permission_type", "rule_type"]
                    ) for p in perms
                ) for perms in scenarios.values()
            )

            # Test file tree
            file_tree = TestDataFixtures.create_realistic_file_tree()
            validation_results["file_tree"] = (
                isinstance(file_tree, list) and
                len(file_tree) > 0 and
                all(isinstance(path, str) for path in file_tree)
            )

            # Test batch paths
            batch_paths = TestDataFixtures.create_batch_test_paths(150)
            validation_results["batch_paths"] = (
                len(batch_paths) == 150 and
                all(isinstance(path, str) for path in batch_paths)
            )

            # Test complete scenarios
            test_scenarios = TestDataFixtures.create_test_scenarios()
            validation_results["test_scenarios"] = all(
                isinstance(scenario, TestScenarioData) for scenario in test_scenarios.values()
            )

            # Test performance data
            perf_data = TestDataFixtures.create_performance_test_data()
            validation_results["performance_data"] = all(
                "paths" in data and "threshold_ms" in data
                for data in perf_data.values()
            )

        except Exception as e:
            validation_results["error"] = str(e)
            return {"validation_failed": False, "error": str(e)}

        validation_results["all_valid"] = all(validation_results.values())
        return validation_results