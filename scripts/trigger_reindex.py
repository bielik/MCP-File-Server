#!/usr/bin/env python3
"""
CLI script for triggering Force Reindex operations programmatically.

This script provides a command-line interface for managing reindex operations
without using the web UI. It can be called directly or imported as a module.

Usage:
    python trigger_reindex.py --mode soft
    python trigger_reindex.py --mode hard --path /projects --no-text-only
    python trigger_reindex.py --status <batch_id>
    python trigger_reindex.py --list
    python trigger_reindex.py --cancel <batch_id>
"""

import os
import sys
import json
import argparse
import time
from typing import Optional, Dict, Any
import requests
from datetime import datetime


class ReindexClient:
    """Client for interacting with the Force Reindex API."""

    def __init__(self, api_base: str = "http://localhost:8000", api_key: Optional[str] = None):
        """
        Initialize ReindexClient.

        Args:
            api_base: Base URL for the API
            api_key: Admin API key (defaults to environment variable)
        """
        self.api_base = api_base
        self.api_key = api_key or os.getenv("ADMIN_API_KEY", "admin-secret-key-change-me")
        self.headers = {
            "Content-Type": "application/json",
            "X-Admin-Key": self.api_key
        }

    def trigger_reindex(
        self,
        mode: str = "soft",
        path_prefix: Optional[str] = None,
        text_only: bool = True,
        dry_run: bool = False
    ) -> Optional[str]:
        """
        Trigger a force reindex operation.

        Args:
            mode: Reindex mode ('soft' or 'hard')
            path_prefix: Optional path filter
            text_only: Whether to only reindex text files
            dry_run: If True, only calculate counts without executing

        Returns:
            Batch ID if successful, None otherwise
        """
        url = f"{self.api_base}/admin/reindex/force"
        payload = {
            "mode": mode,
            "scope": {
                "path_prefix": path_prefix,
                "text_only": text_only
            },
            "dry_run": dry_run
        }

        try:
            response = requests.post(url, json=payload, headers=self.headers, timeout=30)

            if response.status_code == 200:
                result = response.json()
                batch_id = result.get("batch_id")

                if dry_run:
                    print(f"[OK] Dry run complete: {result.get('message')}")
                    print(f"   Would reindex {result['counts']['candidates']} files")
                else:
                    print(f"[OK] Reindex started successfully")
                    print(f"   Batch ID: {batch_id}")
                    print(f"   Mode: {mode}")
                    print(f"   Files to process: {result['counts']['candidates']}")
                    if path_prefix:
                        print(f"   Path filter: {path_prefix}")

                return batch_id

            elif response.status_code == 400:
                error = response.json()
                print(f"[ERROR] Error: {error.get('detail', 'Bad request')}")
                return None

            elif response.status_code == 403:
                print("[ERROR] Error: Admin access required. Check your API key.")
                return None

            else:
                print(f"[ERROR] Error: HTTP {response.status_code} - {response.text}")
                return None

        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Connection error: {e}")
            return None

    def get_batch_status(self, batch_id: str) -> Optional[Dict[str, Any]]:
        """
        Get status of a reindex batch.

        Args:
            batch_id: Batch ID

        Returns:
            Batch status information or None
        """
        url = f"{self.api_base}/admin/reindex/batches/{batch_id}"

        try:
            response = requests.get(url, headers=self.headers, timeout=10)

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                print(f"[ERROR] Error: Batch not found: {batch_id}")
                return None
            else:
                print(f"[ERROR] Error: HTTP {response.status_code}")
                return None

        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Connection error: {e}")
            return None

    def list_batches(self, include_completed: bool = False) -> Optional[list]:
        """
        List reindex batches.

        Args:
            include_completed: Whether to include completed batches

        Returns:
            List of batches or None
        """
        url = f"{self.api_base}/admin/reindex/batches"
        params = {"include_completed": include_completed}

        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=10)

            if response.status_code == 200:
                return response.json()
            else:
                print(f"[ERROR] Error: HTTP {response.status_code}")
                return None

        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Connection error: {e}")
            return None

    def control_batch(self, batch_id: str, action: str) -> bool:
        """
        Control a reindex batch (pause/resume/cancel).

        Args:
            batch_id: Batch ID
            action: Control action ('pause', 'resume', or 'cancel')

        Returns:
            True if successful
        """
        url = f"{self.api_base}/admin/reindex/batches/{batch_id}/{action}"

        try:
            response = requests.post(url, headers=self.headers, timeout=10)

            if response.status_code == 200:
                result = response.json()
                print(f"[OK] Batch {action}d successfully")
                return True
            else:
                error = response.json()
                print(f"[ERROR] Error: {error.get('detail', f'Failed to {action} batch')}")
                return False

        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Connection error: {e}")
            return False

    def get_system_status(self) -> Optional[Dict[str, Any]]:
        """
        Get overall reindex system status.

        Returns:
            System status or None
        """
        url = f"{self.api_base}/admin/reindex/status"

        try:
            response = requests.get(url, headers=self.headers, timeout=10)

            if response.status_code == 200:
                return response.json()
            else:
                print(f"[ERROR] Error: HTTP {response.status_code}")
                return None

        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Connection error: {e}")
            return None

    def clear_maintenance_mode(self) -> bool:
        """
        Clear maintenance mode (emergency operation).

        Returns:
            True if successful
        """
        url = f"{self.api_base}/admin/reindex/maintenance-mode"

        try:
            response = requests.delete(url, headers=self.headers, timeout=10)

            if response.status_code == 200:
                print("[OK] Maintenance mode cleared")
                return True
            else:
                print(f"[ERROR] Error: HTTP {response.status_code}")
                return False

        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Connection error: {e}")
            return False


def format_batch_status(status: Dict[str, Any]) -> None:
    """Format and print batch status information."""
    print("\n=== Batch Status ===")
    print(f"   ID: {status['batch_id']}")
    print(f"   Mode: {status['mode']}")
    print(f"   Status: {status['status']}")

    if status.get('path_prefix'):
        print(f"   Path filter: {status['path_prefix']}")

    print(f"\n=== Progress ===")
    print(f"   Files to process: {status['candidates_count']}")
    print(f"   Jobs created: {status['jobs_created']}")
    print(f"   Files processed: {status['files_processed']}")
    print(f"   Files failed: {status['files_failed']}")
    print(f"   Progress: {status['progress_percentage']:.1f}%")

    if status.get('processing_rate') and status['processing_rate'] > 0:
        print(f"   Processing rate: {status['processing_rate']:.1f} files/sec")

        if status.get('eta_seconds'):
            eta_minutes = status['eta_seconds'] / 60
            print(f"   ETA: {eta_minutes:.1f} minutes")

    if status.get('job_summary'):
        print(f"\n=== Job Summary ===")
        for job_status, count in status['job_summary'].items():
            if count > 0:
                print(f"   {job_status}: {count}")

    if status.get('recent_errors'):
        print(f"\nWARNING:  Recent Errors:")
        for error in status['recent_errors'][:3]:
            print(f"   - {error[:100]}...")

    if status.get('created_at'):
        created = datetime.fromisoformat(status['created_at'])
        print(f"\nTime:  Created: {created.strftime('%Y-%m-%d %H:%M:%S')}")

    if status.get('completed_at'):
        completed = datetime.fromisoformat(status['completed_at'])
        print(f"   Completed: {completed.strftime('%Y-%m-%d %H:%M:%S')}")


def format_batch_list(batches: list) -> None:
    """Format and print list of batches."""
    if not batches:
        print("No active batches found")
        return

    print(f"\n=== Found {len(batches)} batch(es) ===\n")

    for batch in batches:
        print(f"Batch: {batch['id']}")
        print(f"  Mode: {batch['mode']}")
        print(f"  Status: {batch['status']}")
        print(f"  Progress: {batch.get('progress_percentage', 0):.1f}%")
        print(f"  Files: {batch.get('files_processed', 0)}/{batch.get('candidates_count', 0)}")

        if batch.get('path_prefix'):
            print(f"  Path: {batch['path_prefix']}")

        if batch.get('created_at'):
            created = datetime.fromisoformat(batch['created_at'])
            print(f"  Created: {created.strftime('%Y-%m-%d %H:%M:%S')}")

        print()


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Force Reindex CLI - Trigger and manage reindex operations"
    )

    # API configuration
    parser.add_argument(
        "--api-base",
        default=os.getenv("API_BASE_URL", "http://localhost:8000"),
        help="API base URL (default: http://localhost:8000)"
    )
    parser.add_argument(
        "--api-key",
        default=os.getenv("ADMIN_API_KEY"),
        help="Admin API key (defaults to ADMIN_API_KEY env var)"
    )

    # Commands
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Trigger command
    trigger_parser = subparsers.add_parser("trigger", help="Trigger a new reindex")
    trigger_parser.add_argument(
        "--mode",
        choices=["soft", "hard"],
        default="soft",
        help="Reindex mode (default: soft)"
    )
    trigger_parser.add_argument(
        "--path",
        help="Path prefix filter (e.g., /projects)"
    )
    trigger_parser.add_argument(
        "--no-text-only",
        action="store_true",
        help="Include non-text files"
    )
    trigger_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry run - show counts only"
    )
    trigger_parser.add_argument(
        "--wait",
        action="store_true",
        help="Wait for completion and show progress"
    )

    # Status command
    status_parser = subparsers.add_parser("status", help="Get batch status")
    status_parser.add_argument("batch_id", help="Batch ID")
    status_parser.add_argument(
        "--watch",
        action="store_true",
        help="Watch status until completion"
    )

    # List command
    list_parser = subparsers.add_parser("list", help="List batches")
    list_parser.add_argument(
        "--all",
        action="store_true",
        help="Include completed batches"
    )

    # Control commands
    pause_parser = subparsers.add_parser("pause", help="Pause a batch")
    pause_parser.add_argument("batch_id", help="Batch ID")

    resume_parser = subparsers.add_parser("resume", help="Resume a batch")
    resume_parser.add_argument("batch_id", help="Batch ID")

    cancel_parser = subparsers.add_parser("cancel", help="Cancel a batch")
    cancel_parser.add_argument("batch_id", help="Batch ID")

    # System commands
    subparsers.add_parser("system", help="Get system status")
    subparsers.add_parser("clear-maintenance", help="Clear maintenance mode")

    args = parser.parse_args()

    # Create client
    client = ReindexClient(api_base=args.api_base, api_key=args.api_key)

    # Execute command
    if not args.command or args.command == "trigger":
        # Default to trigger if no command specified
        if not hasattr(args, 'mode'):
            args.mode = "soft"
            args.path = None
            args.no_text_only = False
            args.dry_run = False
            args.wait = False

        batch_id = client.trigger_reindex(
            mode=args.mode,
            path_prefix=args.path,
            text_only=not args.no_text_only,
            dry_run=args.dry_run
        )

        if batch_id and args.wait and not args.dry_run:
            print("\n[INFO] Waiting for completion...")
            while True:
                time.sleep(5)
                status = client.get_batch_status(batch_id)
                if status:
                    format_batch_status(status)
                    if status['status'] in ['COMPLETED', 'FAILED', 'CANCELLED']:
                        break
                else:
                    break

    elif args.command == "status":
        status = client.get_batch_status(args.batch_id)
        if status:
            format_batch_status(status)

            if args.watch:
                print("\n[INFO] Watching status...")
                while status['status'] in ['PLANNING', 'RUNNING', 'PAUSED']:
                    time.sleep(5)
                    status = client.get_batch_status(args.batch_id)
                    if status:
                        print("\033[2J\033[H")  # Clear screen
                        format_batch_status(status)
                    else:
                        break

    elif args.command == "list":
        batches = client.list_batches(include_completed=args.all)
        if batches is not None:
            format_batch_list(batches)

    elif args.command == "pause":
        client.control_batch(args.batch_id, "pause")

    elif args.command == "resume":
        client.control_batch(args.batch_id, "resume")

    elif args.command == "cancel":
        client.control_batch(args.batch_id, "cancel")

    elif args.command == "system":
        status = client.get_system_status()
        if status:
            print("\n=== System Status ===")
            print(f"   Active batch: {'Yes' if status['has_active_batch'] else 'No'}")
            if status['active_batch_id']:
                print(f"   Batch ID: {status['active_batch_id']}")
                print(f"   Batch status: {status['active_batch_status']}")
            print(f"   Maintenance mode: {'ON' if status['maintenance_mode'] else 'OFF'}")

    elif args.command == "clear-maintenance":
        client.clear_maintenance_mode()


if __name__ == "__main__":
    main()