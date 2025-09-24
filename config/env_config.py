"""
Configuration System Foundation for MCP KnowledgeExplorer Phase 4A

This module provides centralized configuration management with hardware detection,
validation, and flexible deployment support across different hardware configurations.
"""

import os
import sys
import logging
from typing import Optional, Dict, Any, List
from enum import Enum
from pathlib import Path
from pydantic import Field, validator
from pydantic_settings import BaseSettings


logger = logging.getLogger(__name__)


class DeviceType(str, Enum):
    """Supported device types for ML operations."""
    CPU = "cpu"
    GPU = "gpu"


class RetrievalMode(str, Enum):
    """Search retrieval strategies."""
    HYBRID = "hybrid"     # FTS + Vector + RRF
    FTS = "fts"          # Full-text search only
    VECTOR = "vector"    # Vector search only


class QuantizationType(str, Enum):
    """Model quantization options (future use)."""
    FP16 = "fp16"
    INT8 = "int8"
    INT4 = "int4"


class HardwareDetector:
    """Detects available hardware capabilities."""

    @staticmethod
    def detect_gpu_availability() -> bool:
        """
        Detect if GPU is available for ML operations.

        Returns:
            bool: True if GPU is available, False otherwise
        """
        try:
            # Try importing torch to check for CUDA
            import torch
            return torch.cuda.is_available()
        except ImportError:
            try:
                # Try alternative GPU detection methods
                import subprocess
                result = subprocess.run(['nvidia-smi'],
                                      capture_output=True,
                                      text=True,
                                      timeout=5)
                return result.returncode == 0
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass

        return False

    @staticmethod
    def get_gpu_memory() -> Optional[int]:
        """
        Get available GPU memory in MB.

        Returns:
            Optional[int]: GPU memory in MB, None if not available
        """
        try:
            import torch
            if torch.cuda.is_available():
                return torch.cuda.get_device_properties(0).total_memory // (1024 * 1024)
        except ImportError:
            pass

        return None

    @staticmethod
    def get_recommended_device() -> DeviceType:
        """
        Get recommended device based on hardware detection.

        Returns:
            DeviceType: Recommended device type
        """
        if HardwareDetector.detect_gpu_availability():
            gpu_memory = HardwareDetector.get_gpu_memory()
            if gpu_memory and gpu_memory >= 4096:  # Minimum 4GB for ML models
                return DeviceType.GPU

        return DeviceType.CPU

    @staticmethod
    def validate_model_compatibility(model_name: str, device: DeviceType) -> bool:
        """
        Validate if a model is compatible with the specified device.

        Args:
            model_name: Name of the embedding model
            device: Target device type

        Returns:
            bool: True if compatible, False otherwise
        """
        # CPU models are always compatible
        if device == DeviceType.CPU:
            return True

        # GPU compatibility checks
        if device == DeviceType.GPU:
            gpu_memory = HardwareDetector.get_gpu_memory()
            if not gpu_memory:
                return False

            # Model-specific memory requirements (estimates in MB)
            model_memory_requirements = {
                "paraphrase-multilingual-MiniLM-L12-v2": 512,
                "all-MiniLM-L6-v2": 256,
                "all-mpnet-base-v2": 1024,
                # Add more models as needed
            }

            required_memory = model_memory_requirements.get(model_name, 1024)  # Default 1GB
            return gpu_memory >= required_memory * 2  # 2x safety margin

        return False


class Phase4AConfig(BaseSettings):
    """
    Comprehensive configuration for Phase 4A implementation.

    This configuration class manages all environment variables for the
    indexer service and search functionality with hardware-adaptive settings.
    """

    # Hardware & Model Selection (Critical for RTX 4060 Support)
    INDEX_EMBED_DEVICE: DeviceType = Field(
        default=DeviceType.CPU,
        description="Device for embedding model (cpu/gpu)"
    )
    INDEX_EMBED_QUANT: QuantizationType = Field(
        default=QuantizationType.FP16,
        description="Model quantization type (fp16/int8/int4)"
    )
    INDEX_EMBED_MODEL: str = Field(
        default="paraphrase-multilingual-MiniLM-L12-v2",
        description="Embedding model name"
    )

    # Feature Toggles
    OCR_ENABLED: bool = Field(
        default=True,
        description="Enable Tesseract OCR processing"
    )
    RERANK_ENABLED: bool = Field(
        default=False,
        description="Enable optional cross-encoder reranker"
    )

    # Performance Tuning
    RETRIEVAL_MODE: RetrievalMode = Field(
        default=RetrievalMode.HYBRID,
        description="Search strategy (hybrid/fts/vector)"
    )
    INDEXER_BATCH_SIZE: int = Field(
        default=50,
        ge=1,
        le=1000,
        description="Files processed per batch"
    )
    INDEXER_MAX_WORKERS: int = Field(
        default=2,
        ge=1,
        le=8,
        description="Maximum parallel processing workers"
    )

    # Indexer Control
    INDEXER_PORT: int = Field(
        default=8002,
        description="Indexer service port"
    )
    INDEXER_POLL_INTERVAL: int = Field(
        default=5,
        ge=1,
        le=60,
        description="Control polling interval in seconds"
    )

    # File Watching
    WATCHER_DEBOUNCE_SECONDS: float = Field(
        default=2.0,
        ge=0.1,
        le=30.0,
        description="File change debounce time"
    )
    WATCHER_STABILITY_CHECKS: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Number of stability checks for file changes"
    )

    # Database Configuration
    DB_WAL_MODE: bool = Field(
        default=True,
        description="Enable SQLite WAL mode for concurrency"
    )
    DB_BUSY_TIMEOUT: int = Field(
        default=5000,
        ge=1000,
        le=30000,
        description="SQLite busy timeout in milliseconds"
    )

    # Job Queue Settings
    JOB_RETRY_MAX_ATTEMPTS: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum retry attempts for failed jobs"
    )
    JOB_RETENTION_DAYS: int = Field(
        default=30,
        ge=1,
        le=365,
        description="Job retention period in days"
    )

    # Existing configuration from previous phases
    BACKEND_PORT: int = Field(default=8000, description="Backend service port")
    FRONTEND_PORT: int = Field(default=5173, description="Frontend service port")
    DATABASE_PATH: str = Field(default="./data", description="Database storage path")
    SHARED_FS_PATH: str = Field(default="./shared-fs", description="Shared filesystem path")

    # Legacy feature flags (maintained for compatibility)
    ENABLE_CONFIG_FILE_PERMISSIONS: bool = Field(default=True)
    ENABLE_DATABASE_PERMISSIONS: bool = Field(default=True)
    ENABLE_SOURCE_MOUNT: bool = Field(default=True)
    SHOW_DEPRECATION_WARNING: bool = Field(default=True)

    # Performance settings
    PERMISSION_CACHE_TTL: int = Field(default=300)
    PERMISSION_CACHE_MAX_SIZE: int = Field(default=10000)
    DEBUG_PERMISSION_CACHE: bool = Field(default=False)
    ENABLE_PERFORMANCE_METRICS: bool = Field(default=True)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

    @validator("INDEX_EMBED_DEVICE", pre=True)
    def validate_device_compatibility(cls, v, values):
        """Validate device selection against hardware capabilities."""
        if isinstance(v, str):
            device = DeviceType(v.lower())
        else:
            device = v

        if device == DeviceType.GPU:
            if not HardwareDetector.detect_gpu_availability():
                logger.warning(
                    "GPU requested but not available. Falling back to CPU."
                )
                return DeviceType.CPU

        return device

    @validator("INDEX_EMBED_MODEL")
    def validate_model_compatibility(cls, v, values):
        """Validate model compatibility with selected device."""
        device = values.get("INDEX_EMBED_DEVICE", DeviceType.CPU)

        if not HardwareDetector.validate_model_compatibility(v, device):
            logger.warning(
                f"Model {v} may not be compatible with {device}. "
                "Consider adjusting device selection or model choice."
            )

        return v

    @validator("INDEXER_MAX_WORKERS")
    def validate_worker_count(cls, v):
        """Validate worker count against system capabilities."""
        import os
        cpu_count = os.cpu_count() or 2

        if v > cpu_count:
            logger.warning(
                f"Worker count {v} exceeds CPU count {cpu_count}. "
                f"Consider reducing to {cpu_count} for optimal performance."
            )

        return v

    def get_hardware_info(self) -> Dict[str, Any]:
        """
        Get comprehensive hardware information.

        Returns:
            Dict containing hardware capabilities and recommendations
        """
        return {
            "gpu_available": HardwareDetector.detect_gpu_availability(),
            "gpu_memory_mb": HardwareDetector.get_gpu_memory(),
            "recommended_device": HardwareDetector.get_recommended_device(),
            "model_compatible": HardwareDetector.validate_model_compatibility(
                self.INDEX_EMBED_MODEL, self.INDEX_EMBED_DEVICE
            ),
            "cpu_count": os.cpu_count(),
            "selected_device": self.INDEX_EMBED_DEVICE,
            "selected_model": self.INDEX_EMBED_MODEL,
        }

    def validate_startup_requirements(self) -> List[str]:
        """
        Validate configuration and return any startup warnings.

        Returns:
            List of warning messages
        """
        warnings = []

        # Hardware compatibility checks
        if self.INDEX_EMBED_DEVICE == DeviceType.GPU:
            if not HardwareDetector.detect_gpu_availability():
                warnings.append(
                    "GPU device selected but no GPU detected. "
                    "Consider setting INDEX_EMBED_DEVICE=cpu"
                )

        # Performance warnings
        if self.INDEXER_BATCH_SIZE > 100:
            warnings.append(
                f"Large batch size ({self.INDEXER_BATCH_SIZE}) may cause memory issues"
            )

        # Path validation
        if not Path(self.DATABASE_PATH).exists():
            warnings.append(f"Database path {self.DATABASE_PATH} does not exist")

        # If running inside Docker with a mounted source, accept /source even if the
        # SHARED_FS_PATH string is a host path that doesn't exist in the container.
        from pathlib import Path as _Path
        if not Path(self.SHARED_FS_PATH).exists():
            if _Path('/source').exists():
                # Suppress warning: mount is present at /source
                pass
            else:
                warnings.append(f"Shared filesystem path {self.SHARED_FS_PATH} does not exist")

        return warnings


def get_config() -> Phase4AConfig:
    """
    Get validated configuration instance.

    Returns:
        Phase4AConfig: Validated configuration object

    Raises:
        ValueError: If configuration validation fails
    """
    try:
        config = Phase4AConfig()

        # Log startup warnings
        warnings = config.validate_startup_requirements()
        for warning in warnings:
            logger.warning(warning)

        # Log hardware info
        hw_info = config.get_hardware_info()
        logger.info(f"Hardware detection: {hw_info}")

        return config

    except Exception as e:
        logger.error(f"Configuration validation failed: {e}")
        raise ValueError(f"Invalid configuration: {e}")


def create_env_example() -> str:
    """
    Generate .env.example content with all Phase 4A variables documented.

    Returns:
        str: Formatted .env.example content
    """
    return """# MCP KnowledgeExplorer Phase 4A Configuration
# Copy this file to .env and adjust values for your setup

# ============================================================================
# Hardware & Model Selection (Critical for RTX 4060 Support)
# ============================================================================

# Device for embedding model operations
# Options: cpu, gpu
# GPU requires CUDA-compatible hardware with 4GB+ VRAM
INDEX_EMBED_DEVICE=cpu

# Model quantization for VRAM management (future use)
# Options: fp16, int8, int4
INDEX_EMBED_QUANT=fp16

# Embedding model selection
# CPU-optimized: paraphrase-multilingual-MiniLM-L12-v2
# GPU-optimized: all-mpnet-base-v2
INDEX_EMBED_MODEL=paraphrase-multilingual-MiniLM-L12-v2

# ============================================================================
# Feature Toggles
# ============================================================================

# Enable OCR processing for scanned documents
# Requires Tesseract installation
OCR_ENABLED=true

# Enable cross-encoder reranker for improved search quality
# Increases CPU usage and response time
RERANK_ENABLED=false

# ============================================================================
# Performance & Behavior Tuning
# ============================================================================

# Search strategy selection
# Options: hybrid (FTS+Vector+RRF), fts (keyword only), vector (semantic only)
RETRIEVAL_MODE=hybrid

# Files processed per indexing batch
# Higher values = faster indexing, more memory usage
INDEXER_BATCH_SIZE=50

# Maximum parallel processing workers
# Should not exceed CPU core count
INDEXER_MAX_WORKERS=2

# ============================================================================
# Service Configuration
# ============================================================================

# Service ports
BACKEND_PORT=8000
FRONTEND_PORT=5173
INDEXER_PORT=8002

# File system paths
DATABASE_PATH=./data
SHARED_FS_PATH=C:/Users/MartinBielik/MCP Test

# ============================================================================
# Advanced Settings
# ============================================================================

# File watching configuration
WATCHER_DEBOUNCE_SECONDS=2.0
WATCHER_STABILITY_CHECKS=3

# Database settings
DB_WAL_MODE=true
DB_BUSY_TIMEOUT=5000

# Job queue settings
JOB_RETRY_MAX_ATTEMPTS=3
JOB_RETENTION_DAYS=30
INDEXER_POLL_INTERVAL=5

# Legacy compatibility (Phase 2/3)
ENABLE_CONFIG_FILE_PERMISSIONS=true
ENABLE_DATABASE_PERMISSIONS=true
ENABLE_SOURCE_MOUNT=true
SHOW_DEPRECATION_WARNING=true

# Performance monitoring
PERMISSION_CACHE_TTL=300
PERMISSION_CACHE_MAX_SIZE=10000
DEBUG_PERMISSION_CACHE=false
ENABLE_PERFORMANCE_METRICS=true
"""


if __name__ == "__main__":
    # CLI utility for configuration management
    import argparse

    parser = argparse.ArgumentParser(description="MCP KnowledgeExplorer Configuration")
    parser.add_argument("--validate", action="store_true", help="Validate current configuration")
    parser.add_argument("--hardware-info", action="store_true", help="Show hardware information")
    parser.add_argument("--create-example", action="store_true", help="Create .env.example file")

    args = parser.parse_args()

    if args.create_example:
        with open(".env.example", "w") as f:
            f.write(create_env_example())
        print("Created .env.example file")

    if args.validate or args.hardware_info:
        try:
            config = get_config()

            if args.hardware_info:
                print("Hardware Information:")
                for key, value in config.get_hardware_info().items():
                    print(f"  {key}: {value}")

            if args.validate:
                warnings = config.validate_startup_requirements()
                if warnings:
                    print("Configuration Warnings:")
                    for warning in warnings:
                        print(f"  - {warning}")
                else:
                    print("Configuration validation passed!")

        except Exception as e:
            print(f"Configuration error: {e}")
            sys.exit(1)
