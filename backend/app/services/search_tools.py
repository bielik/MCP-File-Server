"""
MCP Tool implementations for search functionality.

This module provides the tool functions that are called by the MCP server
when AI clients use the search tools.
"""

import logging
from typing import Dict, Any, Optional, List
from app.database import get_db
from app.services.search_service import SearchService

logger = logging.getLogger(__name__)


def list_all_files(
    limit: int = 1000,
    offset: int = 0,
    cursor: Optional[str] = None,
    max_depth: Optional[int] = None,
    sort_by: str = "path"
) -> Dict[str, Any]:
    """
    MCP tool implementation for listing all discoverable files.

    Args:
        limit: Maximum number of files to return
        offset: Number of files to skip (used when cursor is None)
        cursor: Base64-encoded cursor for pagination
        max_depth: Maximum directory depth to traverse
        sort_by: Field to sort by

    Returns:
        Dictionary with files list and pagination info
    """
    try:
        # Validate and constrain parameters
        limit = min(max(1, limit), 5000)
        offset = max(0, offset)

        search_service = SearchService()

        with next(get_db()) as session:
            results = search_service.list_all_files(
                session=session,
                limit=limit,
                offset=offset,
                cursor=cursor,
                max_depth=max_depth,
                sort_by=sort_by
            )

        try:
            total = len(results.get('files', [])) if isinstance(results, dict) else len(results)
        except Exception:
            total = 0
        logger.info(f"MCP list_all_files returned {total} files")
        return results

    except Exception as e:
        logger.error(f"MCP list_all_files failed: {e}")
        raise


def search_files_by_metadata(
    filename_pattern: Optional[str] = None,
    file_types: Optional[List[str]] = None,
    size_min: Optional[int] = None,
    size_max: Optional[int] = None,
    mtime_after: Optional[int] = None,
    mtime_before: Optional[int] = None,
    indexed_only: bool = False,
    limit: int = 100,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """
    MCP tool implementation for metadata-based file search.

    Args:
        filename_pattern: Pattern to match against filenames
        file_types: List of file extensions to include
        size_min: Minimum file size in bytes
        size_max: Maximum file size in bytes
        mtime_after: Files modified after this timestamp
        mtime_before: Files modified before this timestamp
        indexed_only: Only return indexed files
        limit: Maximum number of results
        offset: Number of results to skip

    Returns:
        List of matching file metadata
    """
    try:
        # Validate and constrain parameters
        limit = min(max(1, limit), 1000)
        offset = max(0, offset)

        search_service = SearchService()

        with next(get_db()) as session:
            results = search_service.search_files_by_metadata(
                session=session,
                filename_pattern=filename_pattern,
                file_types=file_types,
                size_min=size_min,
                size_max=size_max,
                mtime_after=mtime_after,
                mtime_before=mtime_before,
                indexed_only=indexed_only,
                limit=limit,
                offset=offset
            )

        logger.info(f"MCP search_files_by_metadata returned {len(results)} files")
        return results

    except Exception as e:
        logger.error(f"MCP search_files_by_metadata failed: {e}")
        raise


def get_file_info(doc_id: str) -> Optional[Dict[str, Any]]:
    """
    MCP tool implementation for getting detailed file information.

    Args:
        doc_id: Document ID of the file

    Returns:
        File information dictionary or None if not found/accessible
    """
    try:
        search_service = SearchService()

        with next(get_db()) as session:
            result = search_service.get_file_info(session, doc_id)

        if result:
            logger.info(f"MCP get_file_info returned info for {doc_id}")
        else:
            logger.warning(f"MCP get_file_info: file not found or not accessible: {doc_id}")

        return result

    except Exception as e:
        logger.error(f"MCP get_file_info failed for {doc_id}: {e}")
        raise


def get_search_statistics() -> Dict[str, Any]:
    """
    MCP tool implementation for getting search statistics.

    Returns:
        Statistics dictionary
    """
    try:
        search_service = SearchService()

        with next(get_db()) as session:
            stats = search_service.get_search_statistics(session)

        logger.info("MCP get_search_statistics returned statistics")
        return stats

    except Exception as e:
        logger.error(f"MCP get_search_statistics failed: {e}")
        raise


def search_fulltext(
    query: str,
    limit: int = 10,
    cursor: Optional[str] = None,
    highlight: bool = True,
    highlight_start: str = "<mark>",
    highlight_end: str = "</mark>",
    file_types: Optional[List[str]] = None,
    date_from: Optional[int] = None,
    date_to: Optional[int] = None
) -> Dict[str, Any]:
    """
    MCP tool implementation for full-text search.

    Args:
        query: Search query string
        limit: Maximum number of results to return
        cursor: Cursor for pagination
        highlight: Whether to include highlighted snippets
        highlight_start: Start marker for highlighting
        highlight_end: End marker for highlighting
        file_types: Optional list of file extensions to filter by
        date_from: Optional start timestamp for date filtering
        date_to: Optional end timestamp for date filtering

    Returns:
        Search results dictionary
    """
    try:
        search_service = SearchService()

        with next(get_db()) as session:
            # Get the active workspace ID
            # For now, we'll use workspace ID 1 as default
            # TODO: Implement proper workspace context detection from MCP session
            workspace_id = 1

            # Perform the search
            results = search_service.search_fulltext(
                session=session,
                query=query,
                workspace_id=workspace_id,
                limit=limit,
                cursor=cursor,
                highlight=highlight,
                highlight_start=highlight_start,
                highlight_end=highlight_end,
                file_types=file_types,
                date_from=date_from,
                date_to=date_to
            )

        logger.info(f"MCP search_fulltext for query '{query}' returned {results.get('total_results', 0)} results")
        return results

    except Exception as e:
        logger.error(f"MCP search_fulltext failed for query '{query}': {e}")
        raise
