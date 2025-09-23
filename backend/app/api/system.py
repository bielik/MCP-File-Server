"""
System information and deprecation API endpoints.

This module provides endpoints for system status, deprecation warnings,
and migration guidance during the transition from legacy mount points.
"""

from typing import Dict, Any
from fastapi import APIRouter, HTTPException
from app.services.path_resolver import get_path_resolver
from app.config import get_config, get_feature_flags
from app.crud import permission_crud
from app.database import SessionLocal, engine, get_db
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/deprecation-status")
async def get_deprecation_status() -> Dict[str, Any]:
    """
    Get deprecation status for legacy mount points and migration guidance.

    This endpoint provides information about:
    - Whether legacy mount points are detected
    - Current and recommended mount points
    - Number of rules using legacy paths
    - Migration guidance URLs
    """
    try:
        # Get path resolver information
        path_resolver = get_path_resolver()
        deprecation_info = path_resolver.get_deprecation_info()
        mount_status = path_resolver.get_mount_status()

        # Get feature flags
        feature_flags = get_feature_flags()
        config = get_config()

        # Count rules using legacy paths (if database permissions enabled)
        rules_using_legacy_paths = 0
        if feature_flags.is_database_permissions_enabled():
            try:
                db = SessionLocal()
                # Get all permissions and check for legacy path references
                all_permissions = permission_crud.get_all_permissions(db)

                # Count permissions that might be referencing legacy paths
                # (This is a heuristic - in practice you might want more sophisticated detection)
                for permission in all_permissions:
                    if permission.path and not permission.path.startswith(('/source', 'source')):
                        # Paths that don't explicitly start with /source might be legacy
                        rules_using_legacy_paths += 1

                db.close()
            except Exception as e:
                logger.warning(f"Could not count legacy path rules: {e}")
                rules_using_legacy_paths = -1  # Indicate unknown

        # Build response
        response = {
            "legacy_mount_detected": deprecation_info["legacy_mount_detected"],
            "current_mount": deprecation_info["current_mount"],
            "recommended_mount": deprecation_info["recommended_mount"],
            "migration_required": deprecation_info["migration_required"],
            "dual_mount_available": deprecation_info["dual_mount_available"],
            "rules_using_legacy_paths": rules_using_legacy_paths,
            "migration_guide_url": "/docs/migration-guide",
            "feature_flags": {
                "source_mount_enabled": mount_status["source_mount_enabled"],
                "show_deprecation_warning": feature_flags.SHOW_DEPRECATION_WARNING if hasattr(feature_flags, 'SHOW_DEPRECATION_WARNING') else True,
                "database_permissions_enabled": feature_flags.is_database_permissions_enabled(),
            },
            "mount_points": mount_status["available_mounts"],
            "recommendations": _get_migration_recommendations(mount_status, deprecation_info)
        }

        return response

    except Exception as e:
        logger.error(f"Error getting deprecation status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get deprecation status: {str(e)}")


@router.get("/mount-status")
async def get_mount_status() -> Dict[str, Any]:
    """
    Get detailed mount point status information.

    Returns comprehensive information about available mount points,
    their status, and current configuration.
    """
    try:
        path_resolver = get_path_resolver()
        mount_status = path_resolver.get_mount_status()

        return {
            "status": "success",
            "mount_status": mount_status,
            "timestamp": "2025-01-17T16:00:00Z"  # Would use real timestamp in production
        }

    except Exception as e:
        logger.error(f"Error getting mount status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get mount status: {str(e)}")


@router.get("/health")
async def get_system_health() -> Dict[str, Any]:
    """
    Get overall system health including mount points and feature flags.
    """
    try:
        feature_flags = get_feature_flags()
        config = get_config()
        path_resolver = get_path_resolver()

        # Check database connectivity
        database_healthy = True
        try:
            if feature_flags.is_database_permissions_enabled():
                db = SessionLocal()
                # Simple query to check database health
                from sqlalchemy import text
                db.execute(text("SELECT 1"))
                db.close()
        except Exception as e:
            logger.warning(f"Database health check failed: {e}")
            database_healthy = False

        mount_status = path_resolver.get_mount_status()

        return {
            "status": "healthy",
            "components": {
                "database": {
                    "healthy": database_healthy,
                    "enabled": feature_flags.is_database_permissions_enabled()
                },
                "mount_points": {
                    "healthy": len(mount_status["available_mounts"]) > 0,
                    "available_count": len(mount_status["available_mounts"]),
                    "primary_mount": mount_status["primary_mount"]
                },
                "feature_flags": {
                    "config_permissions": feature_flags.is_config_permissions_enabled(),
                    "database_permissions": feature_flags.is_database_permissions_enabled(),
                    "source_mount": getattr(feature_flags, 'ENABLE_SOURCE_MOUNT', False),
                    "deprecation_warnings": getattr(feature_flags, 'SHOW_DEPRECATION_WARNING', True)
                }
            },
            "version": "Phase 4 - Migration & Deprecation",
            "timestamp": "2025-01-17T16:00:00Z"
        }

    except Exception as e:
        logger.error(f"Error getting system health: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get system health: {str(e)}")


@router.get("/db-info")
async def get_database_info() -> Dict[str, Any]:
    """
    Get comprehensive database information for debugging.

    Returns effective database URL, table counts, WAL status, and other
    diagnostic information to help troubleshoot database connectivity issues.
    """
    try:
        config = get_config()

        # Get effective database URL and file path
        db_url = getattr(config, 'DATABASE_URL', 'Unknown')
        db_path = getattr(config, 'DATABASE_PATH', 'Unknown')

        # Extract actual file path from SQLite URL
        file_path = None
        if db_url.startswith('sqlite:///'):
            file_path = db_url[10:]  # Remove 'sqlite:///' prefix

        # Check if database file exists
        file_exists = False
        file_size = 0
        if file_path:
            file_exists = os.path.exists(file_path)
            if file_exists:
                file_size = os.path.getsize(file_path)

        # Get database statistics
        table_counts = {}
        wal_mode = None
        db_version = None

        try:
            session = next(get_db())
            try:
                # Check WAL mode
                from sqlalchemy import text
                wal_result = session.execute(text("PRAGMA journal_mode")).fetchone()
                wal_mode = wal_result[0] if wal_result else "unknown"

                # Get SQLite version
                version_result = session.execute(text("SELECT sqlite_version()")).fetchone()
                db_version = version_result[0] if version_result else "unknown"

                # Get table counts for core tables
                tables = ['workspaces', 'permissions', 'indexed_files', 'index_jobs', 'control_settings']
                for table in tables:
                    try:
                        count_result = session.execute(text(f"SELECT COUNT(*) FROM {table}")).fetchone()
                        table_counts[table] = count_result[0] if count_result else 0
                    except Exception as e:
                        table_counts[table] = f"Error: {str(e)}"
            finally:
                session.close()

        except Exception as e:
            logger.error(f"Database query failed: {e}")
            table_counts = {"error": str(e)}

        return {
            "status": "success",
            "database": {
                "config_url": db_url,
                "config_path": db_path,
                "resolved_file_path": file_path,
                "file_exists": file_exists,
                "file_size_bytes": file_size,
                "wal_mode": wal_mode,
                "sqlite_version": db_version,
                "engine_url": str(engine.url) if engine else "Not initialized"
            },
            "tables": table_counts,
            "environment": {
                "DATABASE_PATH": os.environ.get('DATABASE_PATH', 'Not set'),
                "working_directory": os.getcwd(),
                "container_data_dir_exists": os.path.exists('/data'),
                "container_data_contents": os.listdir('/data') if os.path.exists('/data') else None
            },
            "timestamp": "2025-01-23T00:00:00Z"
        }

    except Exception as e:
        logger.error(f"Error getting database info: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get database info: {str(e)}")


def _get_migration_recommendations(mount_status: Dict[str, Any], deprecation_info: Dict[str, Any]) -> list:
    """Generate migration recommendations based on current system state."""
    recommendations = []

    if deprecation_info["legacy_mount_detected"] and not mount_status["source_mount_enabled"]:
        recommendations.append({
            "priority": "high",
            "action": "Enable source mount",
            "description": "Add ENABLE_SOURCE_MOUNT=true to your .env file and restart the application",
            "documentation": "/docs/migration-guide#enable-source-mount"
        })

    if deprecation_info["migration_required"]:
        recommendations.append({
            "priority": "medium",
            "action": "Update Docker configuration",
            "description": "Ensure both /shared-fs and /source mount points are configured in docker-compose.yml",
            "documentation": "/docs/migration-guide#docker-configuration"
        })

    if mount_status["dual_mount_active"]:
        recommendations.append({
            "priority": "low",
            "action": "Plan legacy mount removal",
            "description": "Once migration is complete, you can remove the /shared-fs mount point",
            "documentation": "/docs/migration-guide#removing-legacy-mount"
        })

    return recommendations