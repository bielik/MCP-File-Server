"""
Shim module to expose configuration from config/env_config.py at repository root.

This allows imports like `from env_config import get_config` to work when the
current working directory is not the repository root (e.g., running tests from
backend/).
"""

from config.env_config import *  # noqa: F401,F403

