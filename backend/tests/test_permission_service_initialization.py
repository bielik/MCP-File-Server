"""
Regression tests for database permission service initialization.

These tests specifically target the "NoneType object is not callable" bug
that occurred when the service was created before database initialization.
"""

import pytest
from unittest.mock import patch
from sqlalchemy.orm import Session

from app.services.database_permission_service import (
    DatabasePermissionService,
    get_database_permission_service,
    reset_database_permission_service
)


class TestDatabasePermissionServiceInitialization:
    """Test suite for permission service initialization edge cases."""

    def teardown_method(self):
        """Reset global service state after each test."""
        reset_database_permission_service()

    def test_service_creation_with_none_session_local(self):
        """
        Regression test: Service should not fail when SessionLocal is None.

        This tests the scenario that caused the original NoneType error:
        1. Service is created before database initialization
        2. SessionLocal is None at creation time
        3. Dynamic property should initialize database when accessed
        """
        # Mock SessionLocal as None initially, then return a valid factory
        mock_session = Session()

        def mock_session_factory():
            return mock_session

        with patch('app.services.database_permission_service.SessionLocal', None):
            with patch('app.services.database_permission_service.initialize_database') as mock_init:
                with patch('app.database.SessionLocal', mock_session_factory) as mock_session_local:
                    # Create service when SessionLocal is None
                    service = DatabasePermissionService()

                    # The dynamic property should initialize database when accessed
                    factory = service.session_factory

                    # Verify database was initialized
                    mock_init.assert_called_once()

                    # Verify we can get a session without errors
                    session = service._get_db_session()
                    assert session is mock_session

    def test_global_service_with_none_session_local(self):
        """
        Test the global service accessor with None SessionLocal.

        This tests the guard logic added to prevent the singleton from being
        created with a None session factory.
        """
        mock_session = Session()

        def mock_session_factory():
            return mock_session

        with patch('app.database.SessionLocal', None) as mock_session_local:
            with patch('app.database.initialize_database') as mock_init:
                with patch('app.services.database_permission_service.SessionLocal', mock_session_factory):
                    # This should not fail even when SessionLocal is initially None
                    service = get_database_permission_service()

                    # Verify database initialization was called
                    mock_init.assert_called_once()

                    # Verify service is functional
                    assert service is not None
                    factory = service.session_factory
                    assert factory is not None

    def test_session_factory_property_self_heal(self):
        """
        Test the self-healing behavior of the session_factory property.

        This ensures that if SessionLocal becomes None during runtime,
        the property will reinitialize the database.
        """
        mock_session = Session()

        def mock_session_factory():
            return mock_session

        service = DatabasePermissionService()

        # Mock SessionLocal becoming None during runtime
        with patch('app.database.SessionLocal', None):
            with patch('app.database.initialize_database') as mock_init:
                with patch('app.services.database_permission_service.SessionLocal', mock_session_factory):
                    # Access the property - should trigger self-heal
                    factory = service.session_factory

                    # Verify database was reinitialized
                    mock_init.assert_called_once()

                    # Verify we get a valid factory
                    assert factory is mock_session_factory

    def test_batch_permissions_no_nonetype_error(self):
        """
        Integration test: Batch permissions should not fail with NoneType error.

        This is the specific API endpoint that was failing in the original bug.
        """
        mock_session = Session()

        def mock_session_factory():
            return mock_session

        with patch('app.database.SessionLocal', None):
            with patch('app.database.initialize_database'):
                with patch('app.services.database_permission_service.SessionLocal', mock_session_factory):
                    with patch.object(mock_session, 'close'):  # Prevent actual close
                        with patch('app.crud.workspace.workspace_crud.get_active_workspace', return_value=None):
                            # Create service and try batch permissions
                            service = get_database_permission_service()

                            # This should not raise a "NoneType object is not callable" error
                            results = service.batch_check_permissions(["test/path"], workspace_id=None)

                            # Should return empty results (no active workspace)
                            assert isinstance(results, list)

    def test_service_with_injected_factory(self):
        """
        Test that injected session factory bypasses the dynamic property.

        This ensures testing scenarios work correctly.
        """
        mock_session = Session()

        def mock_session_factory():
            return mock_session

        # Create service with injected factory
        service = DatabasePermissionService(session_factory=mock_session_factory)

        # Should use injected factory, not dynamic property
        factory = service.session_factory
        assert factory is mock_session_factory

        # Should be able to get session without database initialization
        session = service._get_db_session()
        assert session is mock_session


@pytest.fixture(autouse=True)
def cleanup_global_service():
    """Ensure global service is reset between tests."""
    yield
    reset_database_permission_service()