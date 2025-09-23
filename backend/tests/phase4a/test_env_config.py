"""
Tests for Phase 4A environment configuration system.

Tests hardware detection, configuration validation, and startup requirements.
"""

import pytest
import tempfile
import os
from unittest.mock import patch, MagicMock

# We need to add the config directory to the Python path
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))
# Also add /config for Docker environments
if os.path.exists('/config'):
    sys.path.append('/config')

from env_config import (
    HardwareDetector,
    Phase4AConfig,
    DeviceType,
    RetrievalMode,
    QuantizationType,
    get_config
)


class TestHardwareDetector:
    """Test hardware detection functionality."""

    def test_detect_gpu_availability_no_torch(self):
        """Test GPU detection when torch is not available."""
        with patch('importlib.import_module') as mock_import:
            mock_import.side_effect = ImportError("No module named 'torch'")
            result = HardwareDetector.detect_gpu_availability()
            assert result is False

    def test_detect_gpu_availability_no_cuda(self):
        """Test GPU detection when CUDA is not available."""
        with patch('importlib.import_module') as mock_import:
            mock_torch = MagicMock()
            mock_torch.cuda.is_available.return_value = False
            mock_import.return_value = mock_torch

            result = HardwareDetector.detect_gpu_availability()
            assert result is False

    def test_detect_gpu_availability_with_cuda(self):
        """Test GPU detection when CUDA is available."""
        with patch('importlib.import_module') as mock_import:
            mock_torch = MagicMock()
            mock_torch.cuda.is_available.return_value = True
            mock_import.return_value = mock_torch

            result = HardwareDetector.detect_gpu_availability()
            assert result is True

    def test_get_recommended_device_cpu_fallback(self):
        """Test that CPU is recommended when GPU is not available."""
        with patch.object(HardwareDetector, 'detect_gpu_availability', return_value=False):
            device = HardwareDetector.get_recommended_device()
            assert device == DeviceType.CPU

    def test_get_recommended_device_gpu_with_memory(self):
        """Test that GPU is recommended when available with sufficient memory."""
        with patch.object(HardwareDetector, 'detect_gpu_availability', return_value=True):
            with patch.object(HardwareDetector, 'get_gpu_memory', return_value=8192):  # 8GB
                device = HardwareDetector.get_recommended_device()
                assert device == DeviceType.GPU

    def test_get_recommended_device_gpu_insufficient_memory(self):
        """Test that CPU is recommended when GPU has insufficient memory."""
        with patch.object(HardwareDetector, 'detect_gpu_availability', return_value=True):
            with patch.object(HardwareDetector, 'get_gpu_memory', return_value=2048):  # 2GB
                device = HardwareDetector.get_recommended_device()
                assert device == DeviceType.CPU

    def test_validate_model_compatibility_cpu(self):
        """Test model compatibility validation for CPU."""
        result = HardwareDetector.validate_model_compatibility(
            "paraphrase-multilingual-MiniLM-L12-v2",
            DeviceType.CPU
        )
        assert result is True

    def test_validate_model_compatibility_gpu_no_memory(self):
        """Test model compatibility validation for GPU without memory."""
        with patch.object(HardwareDetector, 'get_gpu_memory', return_value=None):
            result = HardwareDetector.validate_model_compatibility(
                "paraphrase-multilingual-MiniLM-L12-v2",
                DeviceType.GPU
            )
            assert result is False

    def test_validate_model_compatibility_gpu_sufficient_memory(self):
        """Test model compatibility validation for GPU with sufficient memory."""
        with patch.object(HardwareDetector, 'get_gpu_memory', return_value=4096):  # 4GB
            result = HardwareDetector.validate_model_compatibility(
                "paraphrase-multilingual-MiniLM-L12-v2",
                DeviceType.GPU
            )
            assert result is True


class TestPhase4AConfig:
    """Test Phase 4A configuration class."""

    def test_default_configuration(self):
        """Test default configuration values."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a temporary .env file
            env_file = os.path.join(temp_dir, '.env')
            with open(env_file, 'w') as f:
                f.write("# Empty env file for testing\n")

            # Set the environment to use our temp file
            with patch.dict(os.environ, {}, clear=True):
                config = Phase4AConfig(_env_file=env_file)

                # Test default values
                assert config.INDEX_EMBED_DEVICE == DeviceType.CPU
                assert config.INDEX_EMBED_QUANT == QuantizationType.FP16
                assert config.INDEX_EMBED_MODEL == "paraphrase-multilingual-MiniLM-L12-v2"
                assert config.OCR_ENABLED is True
                assert config.RERANK_ENABLED is False
                assert config.RETRIEVAL_MODE == RetrievalMode.HYBRID
                assert config.INDEXER_BATCH_SIZE == 50
                assert config.INDEXER_MAX_WORKERS == 2
                assert config.INDEXER_PORT == 8002

    def test_configuration_validation_device_fallback(self):
        """Test that GPU device falls back to CPU when not available."""
        with tempfile.TemporaryDirectory() as temp_dir:
            env_file = os.path.join(temp_dir, '.env')
            with open(env_file, 'w') as f:
                f.write("INDEX_EMBED_DEVICE=gpu\n")

            with patch.object(HardwareDetector, 'detect_gpu_availability', return_value=False):
                with patch.dict(os.environ, {}, clear=True):
                    config = Phase4AConfig(_env_file=env_file)
                    assert config.INDEX_EMBED_DEVICE == DeviceType.CPU

    def test_configuration_validation_worker_count_warning(self):
        """Test worker count validation against CPU count."""
        with tempfile.TemporaryDirectory() as temp_dir:
            env_file = os.path.join(temp_dir, '.env')
            with open(env_file, 'w') as f:
                f.write("INDEXER_MAX_WORKERS=16\n")

            with patch('os.cpu_count', return_value=4):
                with patch.dict(os.environ, {}, clear=True):
                    config = Phase4AConfig(_env_file=env_file)
                    assert config.INDEXER_MAX_WORKERS == 16  # Value is set but warned

    def test_get_hardware_info(self):
        """Test hardware information gathering."""
        config = Phase4AConfig()

        with patch.object(HardwareDetector, 'detect_gpu_availability', return_value=True):
            with patch.object(HardwareDetector, 'get_gpu_memory', return_value=8192):
                with patch.object(HardwareDetector, 'get_recommended_device', return_value=DeviceType.GPU):
                    with patch('os.cpu_count', return_value=8):
                        hw_info = config.get_hardware_info()

                        assert hw_info['gpu_available'] is True
                        assert hw_info['gpu_memory_mb'] == 8192
                        assert hw_info['recommended_device'] == DeviceType.GPU
                        assert hw_info['cpu_count'] == 8
                        assert 'model_compatible' in hw_info

    def test_validate_startup_requirements_missing_paths(self):
        """Test startup validation with missing paths."""
        with tempfile.TemporaryDirectory() as temp_dir:
            env_file = os.path.join(temp_dir, '.env')
            with open(env_file, 'w') as f:
                f.write(f"DATABASE_PATH=/nonexistent/path\n")
                f.write(f"SHARED_FS_PATH=/another/nonexistent/path\n")

            with patch.dict(os.environ, {}, clear=True):
                config = Phase4AConfig(_env_file=env_file)
                warnings = config.validate_startup_requirements()

                # Should have warnings about missing paths
                assert len(warnings) >= 2
                assert any("Database path" in warning for warning in warnings)
                assert any("Shared filesystem path" in warning for warning in warnings)

    def test_validate_startup_requirements_large_batch_size(self):
        """Test startup validation with large batch size."""
        with tempfile.TemporaryDirectory() as temp_dir:
            env_file = os.path.join(temp_dir, '.env')
            with open(env_file, 'w') as f:
                f.write("INDEXER_BATCH_SIZE=500\n")

            with patch.dict(os.environ, {}, clear=True):
                config = Phase4AConfig(_env_file=env_file)
                warnings = config.validate_startup_requirements()

                # Should have warning about large batch size
                assert any("Large batch size" in warning for warning in warnings)

    def test_validate_startup_requirements_gpu_unavailable(self):
        """Test startup validation when GPU is requested but unavailable."""
        with tempfile.TemporaryDirectory() as temp_dir:
            env_file = os.path.join(temp_dir, '.env')
            with open(env_file, 'w') as f:
                f.write("INDEX_EMBED_DEVICE=gpu\n")

            with patch.object(HardwareDetector, 'detect_gpu_availability', return_value=False):
                with patch.dict(os.environ, {}, clear=True):
                    config = Phase4AConfig(_env_file=env_file)
                    warnings = config.validate_startup_requirements()

                    # Should have warning about GPU unavailable
                    assert any("GPU device selected but no GPU detected" in warning for warning in warnings)


class TestConfigurationIntegration:
    """Test configuration integration and get_config function."""

    def test_get_config_success(self):
        """Test successful configuration loading."""
        with patch.object(Phase4AConfig, '__init__', return_value=None):
            mock_config = MagicMock()
            mock_config.validate_startup_requirements.return_value = []
            mock_config.get_hardware_info.return_value = {'test': 'info'}

            with patch('config.env_config.Phase4AConfig', return_value=mock_config):
                config = get_config()
                assert config is mock_config

    def test_get_config_validation_failure(self):
        """Test configuration loading with validation failure."""
        with patch.object(Phase4AConfig, '__init__', side_effect=ValueError("Invalid config")):
            with pytest.raises(ValueError, match="Invalid configuration"):
                get_config()


if __name__ == "__main__":
    pytest.main([__file__])