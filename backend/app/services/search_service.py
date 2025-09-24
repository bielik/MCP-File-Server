"""
Search Service for MCP KnowledgeExplorer Phase 4A

This module provides metadata search capabilities and forms the foundation
for the more advanced search features in Phase 4B.
"""

import base64
import json
import logging
import os
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, text

from app.models.indexing import IndexedFile, DocumentChunk
from app.services.permission_service import check_access
from app.services.permission_postprocessor import PermissionPostprocessor

logger = logging.getLogger(__name__)


class SearchService:
    """
    Provides search capabilities for the MCP KnowledgeExplorer.

    Phase 4A implements metadata search functionality. Phase 4B will extend
    this with full-text and semantic search capabilities.
    """

    def __init__(self):
        """Initialize the search service."""
        self.permission_postprocessor = PermissionPostprocessor()

    def _encode_cursor(self, value: Any, sort_by: str) -> str:
        """
        Encode a cursor value for pagination.

        Args:
            value: The value to encode
            sort_by: The sort field

        Returns:
            Base64-encoded cursor string
        """
        cursor_data = {
            "value": value,
            "sort_by": sort_by
        }
        cursor_json = json.dumps(cursor_data)
        return base64.b64encode(cursor_json.encode()).decode()

    def _decode_cursor(self, cursor: str, expected_sort_by: str) -> Optional[Any]:
        """
        Decode a cursor value for pagination.

        Args:
            cursor: Base64-encoded cursor string
            expected_sort_by: Expected sort field

        Returns:
            Decoded cursor value or None if invalid
        """
        try:
            cursor_json = base64.b64decode(cursor.encode()).decode()
            cursor_data = json.loads(cursor_json)

            if cursor_data.get("sort_by") != expected_sort_by:
                logger.warning(f"Cursor sort_by mismatch: {cursor_data.get('sort_by')} != {expected_sort_by}")
                return None

            return cursor_data.get("value")
        except Exception as e:
            logger.warning(f"Failed to decode cursor: {e}")
            return None

    def list_all_files(
        self,
        session: Session,
        limit: int = 1000,
        offset: int = 0,
        cursor: Optional[str] = None,
        include_directories: bool = False,
        max_depth: Optional[int] = None,
        sort_by: str = "path"
    ) -> Dict[str, Any]:
        """
        List all discoverable files and directories within the workspace scope.

        Args:
            session: Database session
            limit: Maximum number of results to return
            offset: Number of results to skip (used when cursor is None)
            cursor: Base64-encoded cursor for pagination
            include_directories: Whether to include directories in results
            max_depth: Maximum directory depth to traverse (None for unlimited)
            sort_by: Field to sort by ('path', 'size', 'mtime', 'discovered')

        Returns:
            Dictionary with 'files' list and pagination info including 'next_cursor'
        """
        try:
            # Build query for indexed files
            query = session.query(IndexedFile)

            # Apply consistent sorting first (before any filters/pagination)
            if sort_by == "size":
                query = query.order_by(desc(IndexedFile.size_bytes), IndexedFile.id)
            elif sort_by == "mtime":
                query = query.order_by(desc(IndexedFile.mtime_epoch), IndexedFile.id)
            elif sort_by == "discovered":
                query = query.order_by(desc(IndexedFile.discovered_at), IndexedFile.id)
            else:  # Default to path
                query = query.order_by(IndexedFile.path, IndexedFile.id)

            # Apply cursor filtering (after sorting)
            if cursor:
                # Decode cursor to get last value
                cursor_value = self._decode_cursor(cursor, sort_by)
                if cursor_value:
                    if sort_by == "size":
                        query = query.filter(IndexedFile.size_bytes < cursor_value)
                    elif sort_by == "mtime":
                        query = query.filter(IndexedFile.mtime_epoch < cursor_value)
                    elif sort_by == "discovered":
                        query = query.filter(IndexedFile.discovered_at < cursor_value)
                    else:  # Default to path
                        query = query.filter(IndexedFile.path > cursor_value)
                else:
                    # Invalid cursor, fall back to offset
                    logger.warning(f"Invalid cursor provided: {cursor}, falling back to offset")
                    query = query.offset(offset)
            else:
                # Use offset-based pagination as fallback
                query = query.offset(offset)

            # Apply limit (+1 to check if there are more results)
            files = query.limit(limit + 1).all()

            # Check if there are more results
            has_more = len(files) > limit
            if has_more:
                files = files[:limit]  # Remove the extra record

            # Convert to response format and apply permission filtering
            results = []
            for file_obj in files:
                try:
                    # Check if file is accessible
                    check_access(file_obj.path, 'read')

                    # Apply depth filtering if specified
                    if max_depth is not None:
                        path_depth = len(Path(file_obj.path).parts)
                        if path_depth > max_depth:
                            continue

                    file_info = {
                        "doc_id": file_obj.doc_id,
                        "path": file_obj.path,
                        "name": Path(file_obj.path).name,
                        "size_bytes": file_obj.size_bytes,
                        "mtime_epoch": file_obj.mtime_epoch,
                        "mtime_iso": datetime.fromtimestamp(file_obj.mtime_epoch).isoformat(),
                        "is_indexed": file_obj.is_indexed,
                        "mime_type": file_obj.mime_type,
                        "discovered_at": file_obj.discovered_at,
                        "last_indexed_at": file_obj.last_indexed_at,
                        "is_directory": False,  # Phase 4A only tracks files
                        "has_ocr": file_obj.has_ocr if hasattr(file_obj, 'has_ocr') else False,
                    }

                    results.append(file_info)

                except Exception:
                    # File not accessible, skip it
                    continue

            # Generate next cursor if there are more results
            next_cursor = None
            if has_more and files:
                last_file = files[-1]
                if sort_by == "size":
                    cursor_value = last_file.size_bytes
                elif sort_by == "mtime":
                    cursor_value = last_file.mtime_epoch
                elif sort_by == "discovered":
                    cursor_value = last_file.discovered_at
                else:  # path
                    cursor_value = last_file.path

                next_cursor = self._encode_cursor(cursor_value, sort_by)

            logger.debug(f"Listed {len(results)} files (filtered from {len(files)})")

            return {
                "files": results,
                "has_more": has_more,
                "next_cursor": next_cursor,
                "total_returned": len(results)
            }

        except Exception as e:
            logger.error(f"Failed to list all files: {e}")
            raise

    def search_files_by_metadata(
        self,
        session: Session,
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
        Search for files based on metadata criteria.

        Args:
            session: Database session
            filename_pattern: Pattern to match against filename (supports wildcards)
            file_types: List of file extensions to include (e.g., ['.txt', '.pdf'])
            size_min: Minimum file size in bytes
            size_max: Maximum file size in bytes
            mtime_after: Files modified after this epoch timestamp
            mtime_before: Files modified before this epoch timestamp
            indexed_only: If True, only return indexed files
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of matching file metadata
        """
        try:
            # Build query with filters
            query = session.query(IndexedFile)

            # Apply filename pattern filter
            if filename_pattern:
                # Convert simple wildcards to SQL LIKE pattern
                sql_pattern = filename_pattern.replace('*', '%').replace('?', '_')
                query = query.filter(IndexedFile.path.like(f"%{sql_pattern}%"))

            # Apply file type filters
            if file_types:
                # Create OR conditions for each file type
                type_conditions = []
                for file_type in file_types:
                    if not file_type.startswith('.'):
                        file_type = '.' + file_type
                    type_conditions.append(IndexedFile.path.like(f"%{file_type}"))

                if type_conditions:
                    query = query.filter(or_(*type_conditions))

            # Apply size filters
            if size_min is not None:
                query = query.filter(IndexedFile.size_bytes >= size_min)
            if size_max is not None:
                query = query.filter(IndexedFile.size_bytes <= size_max)

            # Apply modification time filters
            if mtime_after is not None:
                query = query.filter(IndexedFile.mtime_epoch >= mtime_after)
            if mtime_before is not None:
                query = query.filter(IndexedFile.mtime_epoch <= mtime_before)

            # Apply indexed filter
            if indexed_only:
                query = query.filter(IndexedFile.is_indexed == True)

            # Order by relevance (filename match first, then modification time)
            if filename_pattern:
                # Files with pattern in name first, then by modification time
                query = query.order_by(
                    IndexedFile.path.like(f"%{filename_pattern}%").desc(),
                    desc(IndexedFile.mtime_epoch)
                )
            else:
                query = query.order_by(desc(IndexedFile.mtime_epoch))

            # Apply pagination
            files = query.offset(offset).limit(limit).all()

            # Convert to response format and apply permission filtering
            results = []
            for file_obj in files:
                try:
                    # Check if file is accessible
                    check_access(file_obj.path, 'read')

                    file_info = {
                        "doc_id": file_obj.doc_id,
                        "path": file_obj.path,
                        "name": Path(file_obj.path).name,
                        "size_bytes": file_obj.size_bytes,
                        "size_human": self._format_file_size(file_obj.size_bytes),
                        "mtime_epoch": file_obj.mtime_epoch,
                        "mtime_iso": datetime.fromtimestamp(file_obj.mtime_epoch).isoformat(),
                        "is_indexed": file_obj.is_indexed,
                        "mime_type": file_obj.mime_type,
                        "discovered_at": file_obj.discovered_at,
                        "last_indexed_at": file_obj.last_indexed_at,
                        "file_extension": Path(file_obj.path).suffix.lower(),
                        "directory": str(Path(file_obj.path).parent),
                    }

                    # Add search relevance information
                    if filename_pattern:
                        file_info["matches_filename"] = filename_pattern.lower() in file_obj.path.lower()

                    results.append(file_info)

                except Exception:
                    # File not accessible, skip it
                    continue

            logger.info(f"Metadata search returned {len(results)} files (filtered from {len(files)})")
            return results

        except Exception as e:
            logger.error(f"Metadata search failed: {e}")
            raise

    def get_file_info(self, session: Session, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific file.

        Args:
            session: Database session
            doc_id: Document ID of the file

        Returns:
            File information dictionary or None if not found/accessible
        """
        try:
            file_obj = session.query(IndexedFile).filter(IndexedFile.doc_id == doc_id).first()

            if not file_obj:
                return None

            # Check permissions
            try:
                check_access(file_obj.path, 'read')
            except Exception:
                return None  # File not accessible

            return {
                "doc_id": file_obj.doc_id,
                "path": file_obj.path,
                "name": Path(file_obj.path).name,
                "size_bytes": file_obj.size_bytes,
                "size_human": self._format_file_size(file_obj.size_bytes),
                "mtime_epoch": file_obj.mtime_epoch,
                "mtime_iso": datetime.fromtimestamp(file_obj.mtime_epoch).isoformat(),
                "is_indexed": file_obj.is_indexed,
                "index_version": file_obj.index_version,
                "mime_type": file_obj.mime_type,
                "discovered_at": file_obj.discovered_at,
                "discovered_iso": datetime.fromtimestamp(file_obj.discovered_at).isoformat(),
                "last_indexed_at": file_obj.last_indexed_at,
                "last_indexed_iso": datetime.fromtimestamp(file_obj.last_indexed_at).isoformat() if file_obj.last_indexed_at else None,
                "file_extension": Path(file_obj.path).suffix.lower(),
                "directory": str(Path(file_obj.path).parent),
                "file_hash": file_obj.file_hash,
                "is_text": file_obj.is_text if hasattr(file_obj, 'is_text') else None,
                "is_binary": file_obj.is_binary if hasattr(file_obj, 'is_binary') else None,
                "has_ocr": file_obj.has_ocr if hasattr(file_obj, 'has_ocr') else False,
            }

        except Exception as e:
            logger.error(f"Failed to get file info for {doc_id}: {e}")
            return None

    def get_search_statistics(self, session: Session) -> Dict[str, Any]:
        """
        Get search and indexing statistics.

        Args:
            session: Database session

        Returns:
            Statistics dictionary
        """
        try:
            total_files = session.query(IndexedFile).count()
            indexed_files = session.query(IndexedFile).filter(IndexedFile.is_indexed == True).count()

            # Get file type distribution
            file_types = {}
            files = session.query(IndexedFile).all()

            accessible_count = 0
            for file_obj in files:
                try:
                    check_access(file_obj.path, 'read')
                    accessible_count += 1

                    extension = Path(file_obj.path).suffix.lower()
                    if not extension:
                        extension = "[no extension]"

                    file_types[extension] = file_types.get(extension, 0) + 1
                except Exception:
                    continue

            # Calculate size statistics
            total_size = sum(f.size_bytes for f in files)

            return {
                "total_files": total_files,
                "accessible_files": accessible_count,
                "indexed_files": indexed_files,
                "pending_files": total_files - indexed_files,
                "indexing_progress": (indexed_files / total_files * 100) if total_files > 0 else 100,
                "total_size_bytes": total_size,
                "total_size_human": self._format_file_size(total_size),
                "file_types": file_types,
                "most_common_types": sorted(file_types.items(), key=lambda x: x[1], reverse=True)[:10]
            }

        except Exception as e:
            logger.error(f"Failed to get search statistics: {e}")
            return {"error": str(e)}

    def _format_file_size(self, size_bytes: int) -> str:
        """
        Format file size in human-readable format.

        Args:
            size_bytes: Size in bytes

        Returns:
            Formatted size string
        """
        if size_bytes == 0:
            return "0 B"

        size_names = ["B", "KB", "MB", "GB", "TB"]
        size_index = 0

        while size_bytes >= 1024 and size_index < len(size_names) - 1:
            size_bytes /= 1024
            size_index += 1

        return f"{size_bytes:.1f} {size_names[size_index]}"

    def search_fulltext(
        self,
        session: Session,
        query: str,
        workspace_id: int,
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
        Perform full-text search using FTS5 with permission filtering.

        Args:
            session: Database session
            query: Search query string
            workspace_id: Active workspace ID for permission filtering
            limit: Maximum number of results to return
            cursor: Cursor for pagination
            highlight: Whether to include highlighted snippets
            highlight_start: Start marker for highlighting
            highlight_end: End marker for highlighting
            file_types: Optional list of file extensions to filter by
            date_from: Optional start timestamp for date filtering
            date_to: Optional end timestamp for date filtering

        Returns:
            Dictionary with search results and pagination info
        """
        try:
            if not query or not query.strip():
                return {
                    "results": [],
                    "total_results": 0,
                    "has_more": False,
                    "cursor": None,
                    "query": query,
                    "search_time_ms": 0
                }

            start_time = datetime.now()

            # Clean and prepare the FTS5 query
            fts_query = self._prepare_fts_query(query)

            # Build base FTS search query
            sql_params = {"fts_query": fts_query, "limit": limit + 1}

            # Build FTS search with JOIN to get file information
            base_query = """
                SELECT
                    c.id as chunk_id,
                    c.file_id,
                    c.ordinal,
                    c.text as chunk_text,
                    c.start_byte,
                    c.end_byte,
                    f.doc_id,
                    f.path as file_path,
                    f.size_bytes,
                    f.mtime_epoch,
                    fts.rank
                FROM chunks_fts fts
                JOIN document_chunks c ON c.id = fts.rowid
                JOIN indexed_files f ON f.id = c.file_id
                WHERE chunks_fts MATCH :fts_query
            """

            # Add file type filtering
            if file_types:
                type_conditions = []
                for i, ext in enumerate(file_types):
                    type_conditions.append(f"f.path GLOB :ext{i}")
                    sql_params[f"ext{i}"] = f"*{ext}"
                base_query += f" AND ({' OR '.join(type_conditions)})"

            # Add date range filtering
            if date_from:
                base_query += " AND f.mtime_epoch >= :date_from"
                sql_params["date_from"] = date_from

            if date_to:
                base_query += " AND f.mtime_epoch <= :date_to"
                sql_params["date_to"] = date_to

            # Handle cursor pagination before ordering
            if cursor:
                cursor_value = self._decode_cursor(cursor, "rank")
                if cursor_value:
                    base_query += " AND fts.rank < :cursor_rank"
                    sql_params["cursor_rank"] = cursor_value

            # Add ordering and pagination
            base_query += " ORDER BY fts.rank DESC, f.path, c.ordinal"

            base_query += " LIMIT :limit"

            # Execute the FTS search
            raw_results = session.execute(text(base_query), sql_params).fetchall()

            # Check if there are more results
            has_more = len(raw_results) > limit
            if has_more:
                raw_results = raw_results[:limit]

            # Process results
            search_results = []
            processed_files = set()  # To avoid duplicate files

            for row in raw_results:
                try:
                    # Generate highlighted snippet if requested
                    highlighted_text = None
                    if highlight:
                        highlighted_text = self._generate_highlighted_snippet(
                            row.chunk_text,
                            query,
                            highlight_start,
                            highlight_end
                        )

                    result = {
                        "doc_id": row.doc_id,
                        "file_path": row.file_path,
                        "chunk_id": row.chunk_id,
                        "chunk_ordinal": row.ordinal,
                        "score": float(row.rank) if row.rank else 1.0,
                        "chunk_text": row.chunk_text,
                        "start_byte": row.start_byte,
                        "end_byte": row.end_byte,
                        "file_size": row.size_bytes,
                        "file_mtime": row.mtime_epoch
                    }

                    if highlighted_text:
                        result["highlighted_text"] = highlighted_text

                    search_results.append(result)
                    processed_files.add(row.doc_id)

                except Exception as e:
                    logger.warning(f"Error processing search result: {e}")
                    continue

            # Apply permission filtering
            filtered_results = self.permission_postprocessor.filter_results(
                search_results, workspace_id, session
            )

            # Generate next cursor
            next_cursor = None
            if has_more and filtered_results:
                last_rank = filtered_results[-1]["score"]
                next_cursor = self._encode_cursor(last_rank, "rank")

            # Calculate search time
            end_time = datetime.now()
            search_time_ms = int((end_time - start_time).total_seconds() * 1000)

            return {
                "results": filtered_results,
                "total_results": len(filtered_results),
                "has_more": has_more and len(filtered_results) >= limit,
                "cursor": next_cursor,
                "query": query,
                "search_time_ms": search_time_ms,
                "files_found": len(processed_files)
            }

        except Exception as e:
            logger.error(f"Full-text search failed: {e}")
            return {
                "results": [],
                "total_results": 0,
                "has_more": False,
                "cursor": None,
                "query": query,
                "error": str(e),
                "search_time_ms": 0
            }

    def _prepare_fts_query(self, query: str) -> str:
        """
        Prepare and sanitize FTS5 query.

        Args:
            query: Raw search query

        Returns:
            Sanitized FTS5 query string
        """
        try:
            # Basic sanitization
            query = query.strip()

            # Handle quoted phrases (keep as-is)
            if query.startswith('"') and query.endswith('"'):
                return query

            # Handle boolean operators
            boolean_operators = ['AND', 'OR', 'NOT']
            for op in boolean_operators:
                if op in query.upper():
                    # Query contains boolean operators, pass through with basic validation
                    # Remove potentially problematic characters but preserve operators
                    query = query.replace('"', '""')  # Escape quotes
                    return query

            # Handle wildcard queries
            if '*' in query:
                return query

            # For simple queries, add implicit wildcards for better matching
            terms = query.split()
            if len(terms) == 1:
                # Single term - add wildcard for prefix matching
                return f"{terms[0]}*"
            else:
                # Multiple terms - treat as phrase or AND query
                return ' '.join(terms)

        except Exception as e:
            logger.warning(f"Error preparing FTS query '{query}': {e}")
            return query  # Return original query as fallback

    def _generate_highlighted_snippet(
        self,
        text: str,
        query: str,
        start_marker: str,
        end_marker: str,
        max_length: int = 200
    ) -> str:
        """
        Generate a highlighted snippet from text.

        Args:
            text: Source text
            query: Search query
            start_marker: Start highlight marker
            end_marker: End highlight marker
            max_length: Maximum snippet length

        Returns:
            Highlighted text snippet
        """
        try:
            if not text or not query:
                return text

            # Simple highlighting - find query terms in text
            query_terms = query.lower().strip('"').split()
            highlighted_text = text

            # Highlight each term
            for term in query_terms:
                if not term or len(term) < 2:
                    continue

                # Use case-insensitive replacement
                import re
                pattern = re.compile(re.escape(term), re.IGNORECASE)
                highlighted_text = pattern.sub(
                    lambda m: f"{start_marker}{m.group()}{end_marker}",
                    highlighted_text
                )

            # Truncate if too long, trying to keep highlights
            if len(highlighted_text) > max_length:
                # Find first highlight position
                highlight_pos = highlighted_text.find(start_marker)
                if highlight_pos != -1:
                    # Center snippet around first highlight
                    start_pos = max(0, highlight_pos - max_length // 2)
                    end_pos = min(len(highlighted_text), start_pos + max_length)
                    snippet = highlighted_text[start_pos:end_pos]

                    # Add ellipsis if truncated
                    if start_pos > 0:
                        snippet = "..." + snippet
                    if end_pos < len(highlighted_text):
                        snippet = snippet + "..."

                    return snippet
                else:
                    # No highlights found, just truncate from beginning
                    return highlighted_text[:max_length] + "..."

            return highlighted_text

        except Exception as e:
            logger.warning(f"Error generating highlighted snippet: {e}")
            return text  # Return original text as fallback