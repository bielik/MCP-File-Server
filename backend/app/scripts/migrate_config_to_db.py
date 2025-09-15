#!/usr/bin/env python3
"""
Migration script to migrate permission configuration from permissions.json to database.

This script provides a one-shot, idempotent migration from Phase 2 config files
to Phase 3A database storage. It can be run multiple times safely.

Usage:
    python -m app.scripts.migrate_config_to_db [--config-file path] [--workspace-name name] [--dry-run]

Example:
    python -m app.scripts.migrate_config_to_db --workspace-name "Legacy Config" --dry-run
"""

import os
import sys
import json
import argparse
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

# Add the parent directory to sys.path so we can import app modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.database import SessionLocal, create_db_and_tables
from app.config import get_config, get_feature_flags
from app.models.workspace import Workspace, Permission
from app.crud import workspace_crud, permission_crud
from app.schemas.workspace import WorkspaceCreate, PermissionCreate, WorkspaceUpdate


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MigrationError(Exception):
    """Custom exception for migration errors."""
    pass


class ConfigToDbMigrator:
    """Handles migration from config file to database."""

    def __init__(self, config_file_path: Optional[Path] = None, workspace_name: str = "Migrated Config"):
        self.config = get_config()
        self.workspace_name = workspace_name
        self.config_file_path = config_file_path or self.config.get_permissions_config_path()
        self.migration_summary = {
            "workspace_created": False,
            "workspace_id": None,
            "rules_migrated": 0,
            "rules_skipped": 0,
            "errors": []
        }

    def validate_prerequisites(self) -> None:
        """Validate that migration can proceed."""
        # Check that database permissions are enabled
        feature_flags = get_feature_flags()
        if not feature_flags.is_database_permissions_enabled():
            raise MigrationError(
                "Database permissions are not enabled. Set ENABLE_DATABASE_PERMISSIONS=true before migrating."
            )

        # Check that config file exists
        if not self.config_file_path.exists():
            raise MigrationError(f"Config file not found: {self.config_file_path}")

        # Try to parse config file
        try:
            with open(self.config_file_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
        except json.JSONDecodeError as e:
            raise MigrationError(f"Invalid JSON in config file: {e}")
        except Exception as e:
            raise MigrationError(f"Failed to read config file: {e}")

        if 'rules' not in config_data:
            raise MigrationError("Config file must contain 'rules' array")

        logger.info(f"Prerequisites validated. Found {len(config_data['rules'])} rules to migrate.")

    def load_config_data(self) -> Dict[str, Any]:
        """Load and validate config data."""
        with open(self.config_file_path, 'r', encoding='utf-8') as f:
            config_data = json.load(f)

        # Validate structure
        if not isinstance(config_data.get('rules'), list):
            raise MigrationError("Config 'rules' must be an array")

        return config_data

    def check_existing_workspace(self, db: Session) -> Optional[Workspace]:
        """Check if a workspace with this name already exists."""
        return workspace_crud.get_workspace_by_name(db, self.workspace_name)

    def create_or_update_workspace(self, db: Session, config_data: Dict[str, Any], dry_run: bool = False) -> Workspace:
        """Create or update the workspace for migrated rules."""
        existing_workspace = self.check_existing_workspace(db)

        if existing_workspace:
            logger.info(f"Found existing workspace '{self.workspace_name}' (ID: {existing_workspace.id})")

            if not dry_run:
                # Check if we should update the workspace description
                metadata = config_data.get('metadata', {})
                new_description = f"Migrated from config file on {datetime.now().isoformat()}"
                if metadata.get('description'):
                    new_description = f"{metadata['description']} (migrated on {datetime.now().isoformat()})"

                workspace_crud.update_workspace(
                    db=db,
                    workspace_id=existing_workspace.id,
                    workspace_update=WorkspaceUpdate(description=new_description),
                    updated_by="migration_script"
                )

            self.migration_summary["workspace_id"] = existing_workspace.id
            return existing_workspace

        else:
            logger.info(f"Creating new workspace '{self.workspace_name}'")

            if dry_run:
                # Create a mock workspace for dry run
                mock_workspace = Workspace(
                    id=999999,
                    name=self.workspace_name,
                    description="DRY RUN - Not actually created",
                    is_active=False
                )
                self.migration_summary["workspace_created"] = True
                self.migration_summary["workspace_id"] = mock_workspace.id
                return mock_workspace

            # Create workspace description from config metadata
            metadata = config_data.get('metadata', {})
            description = f"Migrated from config file: {self.config_file_path.name}"
            if metadata.get('description'):
                description = f"{metadata['description']} (migrated from {self.config_file_path.name})"

            workspace = workspace_crud.create_workspace(
                db=db,
                workspace=WorkspaceCreate(
                    name=self.workspace_name,
                    description=description
                ),
                created_by="migration_script"
            )

            self.migration_summary["workspace_created"] = True
            self.migration_summary["workspace_id"] = workspace.id
            logger.info(f"Created workspace '{self.workspace_name}' with ID: {workspace.id}")
            return workspace

    def migrate_rules(self, db: Session, workspace: Workspace, config_data: Dict[str, Any], dry_run: bool = False) -> None:
        """Migrate permission rules to the database."""
        rules = config_data.get('rules', [])
        logger.info(f"Migrating {len(rules)} permission rules...")

        for rule_data in rules:
            try:
                self._migrate_single_rule(db, workspace, rule_data, dry_run)
            except Exception as e:
                error_msg = f"Failed to migrate rule {rule_data.get('id', 'unknown')}: {e}"
                logger.error(error_msg)
                self.migration_summary["errors"].append(error_msg)
                self.migration_summary["rules_skipped"] += 1

    def _migrate_single_rule(self, db: Session, workspace: Workspace, rule_data: Dict[str, Any], dry_run: bool = False) -> None:
        """Migrate a single permission rule."""
        # Validate required fields
        required_fields = ['id', 'path', 'permission_type', 'rule_type']
        for field in required_fields:
            if field not in rule_data:
                raise ValueError(f"Rule missing required field: {field}")

        # Validate field values
        if rule_data['permission_type'] not in ['read', 'write']:
            raise ValueError(f"Invalid permission_type: {rule_data['permission_type']}")

        if rule_data['rule_type'] not in ['allow', 'deny']:
            raise ValueError(f"Invalid rule_type: {rule_data['rule_type']}")

        if dry_run:
            logger.info(f"DRY RUN: Would migrate rule {rule_data['id']} - {rule_data['rule_type']} {rule_data['permission_type']} on {rule_data['path']}")
            self.migration_summary["rules_migrated"] += 1
            return

        # Check for existing rule (idempotency)
        existing_rule = permission_crud.find_duplicate_rule(
            db=db,
            workspace_id=workspace.id,
            path=rule_data['path'],
            permission_type=rule_data['permission_type'],
            rule_type=rule_data['rule_type']
        )

        if existing_rule:
            logger.info(f"Rule already exists for {rule_data['path']} - {rule_data['permission_type']} - {rule_data['rule_type']}, skipping")
            self.migration_summary["rules_skipped"] += 1
            return

        # Create the permission
        permission = permission_crud.create_permission(
            db=db,
            workspace_id=workspace.id,
            permission=PermissionCreate(
                path=rule_data['path'],
                permission_type=rule_data['permission_type'],
                rule_type=rule_data['rule_type'],
                description=rule_data.get('description', f"Migrated rule: {rule_data['id']}")
            ),
            created_by="migration_script"
        )

        logger.info(f"Migrated rule {rule_data['id']} -> Permission ID {permission.id}")
        self.migration_summary["rules_migrated"] += 1

    def activate_workspace_if_requested(self, db: Session, workspace: Workspace, activate: bool = False, dry_run: bool = False) -> None:
        """Activate the migrated workspace if requested."""
        if not activate:
            return

        if dry_run:
            logger.info(f"DRY RUN: Would activate workspace '{workspace.name}'")
            return

        # Check if there's already an active workspace
        current_active = workspace_crud.get_active_workspace(db)
        if current_active:
            logger.warning(f"Deactivating current workspace '{current_active.name}' (ID: {current_active.id})")

        activated_workspace = workspace_crud.activate_workspace(db, workspace.id)
        if activated_workspace:
            logger.info(f"Activated workspace '{workspace.name}' - it is now the active workspace for permission resolution")
        else:
            logger.error(f"Failed to activate workspace '{workspace.name}'")

    def run_migration(self, activate_workspace: bool = False, dry_run: bool = False) -> Dict[str, Any]:
        """Run the complete migration process."""
        logger.info(f"Starting migration from {self.config_file_path} to database...")

        if dry_run:
            logger.info("DRY RUN MODE - No changes will be made to the database")

        try:
            # Validate prerequisites
            self.validate_prerequisites()

            # Load config data
            config_data = self.load_config_data()

            # Ensure database tables exist
            if not dry_run:
                create_db_and_tables()

            # Run migration in database session
            db = SessionLocal()
            try:
                # Create or get workspace
                workspace = self.create_or_update_workspace(db, config_data, dry_run)

                # Migrate rules
                self.migrate_rules(db, workspace, config_data, dry_run)

                # Activate workspace if requested
                self.activate_workspace_if_requested(db, workspace, activate_workspace, dry_run)

                if not dry_run:
                    db.commit()
                    logger.info("Migration completed successfully")
                else:
                    logger.info("DRY RUN completed - no changes made")

            except Exception as e:
                if not dry_run:
                    db.rollback()
                raise
            finally:
                db.close()

        except Exception as e:
            error_msg = f"Migration failed: {e}"
            logger.error(error_msg)
            self.migration_summary["errors"].append(error_msg)
            raise MigrationError(error_msg)

        return self.migration_summary

    def print_summary(self) -> None:
        """Print migration summary."""
        print("\n" + "="*60)
        print("MIGRATION SUMMARY")
        print("="*60)

        if self.migration_summary["workspace_created"]:
            print(f"✅ Created new workspace: '{self.workspace_name}' (ID: {self.migration_summary['workspace_id']})")
        else:
            print(f"ℹ️  Used existing workspace: '{self.workspace_name}' (ID: {self.migration_summary['workspace_id']})")

        print(f"✅ Rules migrated: {self.migration_summary['rules_migrated']}")
        print(f"⚠️  Rules skipped: {self.migration_summary['rules_skipped']}")

        if self.migration_summary["errors"]:
            print(f"❌ Errors encountered: {len(self.migration_summary['errors'])}")
            for error in self.migration_summary["errors"]:
                print(f"   - {error}")
        else:
            print("✅ No errors encountered")

        print("="*60)


def main():
    """Main entry point for the migration script."""
    parser = argparse.ArgumentParser(description="Migrate permissions from config file to database")
    parser.add_argument(
        "--config-file",
        type=Path,
        help="Path to permissions.json file (default: from app config)"
    )
    parser.add_argument(
        "--workspace-name",
        default="Migrated Config",
        help="Name for the workspace containing migrated rules (default: 'Migrated Config')"
    )
    parser.add_argument(
        "--activate",
        action="store_true",
        help="Activate the migrated workspace after migration"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be migrated without making changes"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        # Create migrator
        migrator = ConfigToDbMigrator(
            config_file_path=args.config_file,
            workspace_name=args.workspace_name
        )

        # Run migration
        summary = migrator.run_migration(
            activate_workspace=args.activate,
            dry_run=args.dry_run
        )

        # Print summary
        migrator.print_summary()

        # Exit with success
        sys.exit(0)

    except MigrationError as e:
        logger.error(f"Migration failed: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Migration cancelled by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()