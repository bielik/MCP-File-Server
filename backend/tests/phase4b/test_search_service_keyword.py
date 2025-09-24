"""
Search Service Keyword Tests for Phase 4B M2

Unit tests for the FTS5 query logic in SearchService, testing phrase matching,
typo tolerance with trigram tokenizer, and ranking.

Following TDD methodology as specified in Phase 4B plan.
"""

import pytest
import tempfile
import os
import sys
from unittest.mock import patch, MagicMock
from typing import List, Dict, Any
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

# Add parent directories to path for imports
backend_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, backend_root)

from app.database import Base
from app.models.indexing import IndexedFile, DocumentChunk
from app.models.workspace import Workspace, Permission, RuleType, PermissionType

# Import SearchService (will be extended)
from app.services.search_service import SearchService


@pytest.fixture
def test_db():
    """Create a temporary database for testing."""
    # Create temporary database file
    db_fd, db_path = tempfile.mkstemp(suffix='.db')

    try:
        # Create engine and session
        engine = create_engine(f'sqlite:///{db_path}', echo=False)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

        # Create all tables
        Base.metadata.create_all(bind=engine)

        # Create FTS tables manually (since they aren't in Base.metadata)
        with engine.connect() as conn:
            conn.execute(text("""
                CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
                    text,
                    content='document_chunks',
                    content_rowid='id',
                    tokenize = 'trigram'
                );
            """))

            # Create FTS triggers
            conn.execute(text("""
                CREATE TRIGGER IF NOT EXISTS chunks_fts_insert AFTER INSERT ON document_chunks BEGIN
                    INSERT INTO chunks_fts(rowid, text) VALUES (new.id, new.text);
                END;
            """))

            conn.execute(text("""
                CREATE TRIGGER IF NOT EXISTS chunks_fts_delete AFTER DELETE ON document_chunks BEGIN
                    INSERT INTO chunks_fts(chunks_fts, rowid, text) VALUES('delete', old.id, old.text);
                END;
            """))

            conn.execute(text("""
                CREATE TRIGGER IF NOT EXISTS chunks_fts_update AFTER UPDATE ON document_chunks BEGIN
                    INSERT INTO chunks_fts(chunks_fts, rowid, text) VALUES('delete', old.id, old.text);
                    INSERT INTO chunks_fts(rowid, text) VALUES (new.id, new.text);
                END;
            """))

            conn.commit()

        session = SessionLocal()
        yield session
        session.close()

        # Properly dispose of engine before cleanup
        engine.dispose()

    finally:
        os.close(db_fd)
        try:
            os.unlink(db_path)
        except OSError:
            pass


@pytest.fixture
def sample_indexed_content(test_db):
    """Create sample indexed content for FTS testing."""
    # Create sample files with varied content
    files_data = [
        {
            "doc_id": "tech_doc_1",
            "path": "materials/machine_learning.txt",
            "chunks": [
                "Machine learning is a method of data analysis that automates analytical model building.",
                "Machine learning algorithms build mathematical models based on training data.",
                "Deep learning is a subset of machine learning using artificial neural networks."
            ]
        },
        {
            "doc_id": "tech_doc_2",
            "path": "materials/artificial_intelligence.txt",
            "chunks": [
                "Artificial intelligence encompasses machine learning and natural language processing.",
                "AI systems can perform tasks that typically require human intelligence.",
                "Neural networks are computational models inspired by biological neural networks."
            ]
        },
        {
            "doc_id": "project_doc",
            "path": "projects/readme.md",
            "chunks": [
                "This project implements a recommendation system using collaborative filtering.",
                "The system analyzes user behavior patterns to suggest relevant content.",
                "Machine learning algorithms power the recommendation engine."
            ]
        },
        {
            "doc_id": "misc_doc",
            "path": "materials/data_science.txt",
            "chunks": [
                "Data science combines statistics, mathematics, and computer science.",
                "Statistical analysis helps identify patterns in large datasets.",
                "Visualization techniques make complex data more understandable."
            ]
        }
    ]

    created_files = []
    created_chunks = []

    for file_data in files_data:
        # Create IndexedFile
        indexed_file = IndexedFile(
            doc_id=file_data["doc_id"],
            path=file_data["path"],
            file_hash=f"hash_{file_data['doc_id']}",
            size_bytes=len(' '.join(file_data["chunks"])),
            mtime_epoch=1234567890,
            is_indexed=True,
            is_text=True
        )
        test_db.add(indexed_file)
        test_db.commit()  # Commit to get ID
        created_files.append(indexed_file)

        # Create DocumentChunks
        for i, chunk_text in enumerate(file_data["chunks"]):
            chunk = DocumentChunk(
                file_id=indexed_file.id,
                ordinal=i,
                text=chunk_text,
                start_byte=i * 100,
                end_byte=(i + 1) * 100 - 1
            )
            test_db.add(chunk)
            created_chunks.append(chunk)

    test_db.commit()
    return created_files, created_chunks


class TestSearchServiceKeywordQueries:
    """Test FTS5 query construction and execution."""

    def test_simple_keyword_search(self, test_db, sample_indexed_content):
        """Test basic keyword search functionality."""
        created_files, created_chunks = sample_indexed_content

        # Initialize SearchService
        search_service = SearchService()

        # TODO: Implement search_fulltext method
        # Test simple keyword search
        # results = search_service.search_fulltext(test_db, query="machine learning")

        # Expected: Results containing "machine learning" should be found
        # assert len(results) > 0, "Should find results for 'machine learning'"

        # Verify results contain expected content
        # for result in results:
        #     assert "machine" in result.get("highlighted_text", "").lower() or \
        #            "learning" in result.get("highlighted_text", "").lower()

    def test_phrase_search(self, test_db, sample_indexed_content):
        """Test phrase matching with exact quotes."""
        created_files, created_chunks = sample_indexed_content

        search_service = SearchService()

        # TODO: Test exact phrase search
        # phrase_results = search_service.search_fulltext(test_db, query='"machine learning"')

        # Expected: Only exact phrase matches should be returned
        # assert len(phrase_results) >= 2, "Should find multiple exact phrase matches"

        # Non-phrase search should return more results
        # keyword_results = search_service.search_fulltext(test_db, query="machine learning")
        # assert len(keyword_results) >= len(phrase_results), "Keyword search should return same or more results"

    def test_boolean_operators(self, test_db, sample_indexed_content):
        """Test FTS5 boolean operators (AND, OR, NOT)."""
        created_files, created_chunks = sample_indexed_content

        search_service = SearchService()

        # TODO: Test AND operator
        # and_results = search_service.search_fulltext(test_db, query="machine AND learning")
        # assert len(and_results) > 0, "Should find results with both terms"

        # TODO: Test OR operator
        # or_results = search_service.search_fulltext(test_db, query="machine OR data")
        # assert len(or_results) > len(and_results), "OR should return more results than AND"

        # TODO: Test NOT operator
        # not_results = search_service.search_fulltext(test_db, query="machine NOT learning")
        # Results should contain "machine" but not "learning" in the same chunk

    def test_wildcard_search(self, test_db, sample_indexed_content):
        """Test wildcard search with asterisk."""
        created_files, created_chunks = sample_indexed_content

        search_service = SearchService()

        # TODO: Test prefix wildcard
        # wildcard_results = search_service.search_fulltext(test_db, query="learn*")

        # Should match "learning", "learn", etc.
        # assert len(wildcard_results) > 0, "Should find results with wildcard"

        # Verify wildcard expansion
        # for result in wildcard_results:
        #     text = result.get("highlighted_text", "").lower()
        #     assert "learn" in text, "Results should contain wildcard match"


class TestTrigramTokenizerFeatures:
    """Test trigram tokenizer specific features."""

    def test_trigram_substring_matching(self, test_db, sample_indexed_content):
        """Test trigram tokenizer's substring matching capability."""
        created_files, created_chunks = sample_indexed_content

        search_service = SearchService()

        # TODO: Test substring search that should work with trigrams
        # Trigram tokenizer should help with partial matches
        # substring_results = search_service.search_fulltext(test_db, query="achine")  # substring of "machine"

        # With trigrams, this should potentially match "machine"
        # The exact behavior depends on FTS5 trigram implementation

    def test_typo_tolerance(self, test_db):
        """Test typo tolerance capabilities of trigram tokenizer."""
        # Create content with common words that might have typos
        indexed_file = IndexedFile(
            doc_id="typo_test",
            path="test/typos.txt",
            file_hash="typo_hash",
            size_bytes=100,
            mtime_epoch=1234567890,
            is_indexed=True,
            is_text=True
        )
        test_db.add(indexed_file)
        test_db.commit()

        # Create chunks with correct spellings
        chunk = DocumentChunk(
            file_id=indexed_file.id,
            ordinal=0,
            text="The algorithm processes information efficiently and accurately.",
            start_byte=0,
            end_byte=60
        )
        test_db.add(chunk)
        test_db.commit()

        search_service = SearchService()

        # TODO: Test searching with slight misspellings
        # Note: Trigram tokenizer has limited typo tolerance compared to specialized fuzzy search
        # typo_results = search_service.search_fulltext(test_db, query="algoritm")  # missing 'h'

        # The trigram approach may or may not find this, depending on implementation
        # This test helps verify the current behavior


class TestSearchRankingAndRelevance:
    """Test search result ranking and relevance scoring."""

    def test_relevance_ranking(self, test_db, sample_indexed_content):
        """Test that search results are properly ranked by relevance."""
        created_files, created_chunks = sample_indexed_content

        search_service = SearchService()

        # TODO: Search for term that appears with different frequency/prominence
        # results = search_service.search_fulltext(test_db, query="machine learning")

        # Verify results are sorted by relevance (descending score)
        # scores = [result.get("score", 0) for result in results]
        # assert scores == sorted(scores, reverse=True), "Results should be sorted by score descending"

    def test_term_frequency_impact(self, test_db):
        """Test that term frequency affects ranking."""
        # Create files with different term frequencies
        files_data = [
            {
                "doc_id": "high_freq",
                "path": "test/high.txt",
                "text": "python programming python development python coding python scripts"
            },
            {
                "doc_id": "low_freq",
                "path": "test/low.txt",
                "text": "python is a programming language used for development"
            }
        ]

        for file_data in files_data:
            indexed_file = IndexedFile(
                doc_id=file_data["doc_id"],
                path=file_data["path"],
                file_hash=f"hash_{file_data['doc_id']}",
                size_bytes=len(file_data["text"]),
                mtime_epoch=1234567890,
                is_indexed=True,
                is_text=True
            )
            test_db.add(indexed_file)
            test_db.commit()

            chunk = DocumentChunk(
                file_id=indexed_file.id,
                ordinal=0,
                text=file_data["text"],
                start_byte=0,
                end_byte=len(file_data["text"])
            )
            test_db.add(chunk)

        test_db.commit()

        search_service = SearchService()

        # TODO: Search for "python"
        # results = search_service.search_fulltext(test_db, query="python")

        # High frequency document should rank higher
        # assert len(results) >= 2, "Should find both documents"
        # top_result = results[0]
        # assert top_result["doc_id"] == "high_freq", "High frequency doc should rank first"


class TestSearchPagination:
    """Test cursor-based pagination for search results."""

    def test_cursor_pagination(self, test_db, sample_indexed_content):
        """Test that search supports cursor-based pagination."""
        created_files, created_chunks = sample_indexed_content

        search_service = SearchService()

        # TODO: Test pagination
        # First page
        # page1 = search_service.search_fulltext(test_db, query="learning", limit=2)
        # assert len(page1) <= 2, "Should respect limit parameter"
        # assert "cursor" in page1, "Should include cursor for next page"

        # Second page using cursor
        # cursor = page1["cursor"]
        # page2 = search_service.search_fulltext(test_db, query="learning", limit=2, cursor=cursor)

        # Verify no overlap between pages
        # page1_ids = [result["doc_id"] for result in page1.get("results", [])]
        # page2_ids = [result["doc_id"] for result in page2.get("results", [])]
        # assert not set(page1_ids).intersection(set(page2_ids)), "Pages should not overlap"


class TestSearchFiltering:
    """Test additional filtering capabilities."""

    def test_file_type_filtering(self, test_db, sample_indexed_content):
        """Test filtering results by file type."""
        created_files, created_chunks = sample_indexed_content

        search_service = SearchService()

        # TODO: Test filtering by file extension
        # txt_results = search_service.search_fulltext(
        #     test_db,
        #     query="machine",
        #     file_types=[".txt"]
        # )

        # Verify only .txt files in results
        # for result in txt_results:
        #     assert result["file_path"].endswith(".txt"), "Should only return .txt files"

    def test_date_range_filtering(self, test_db, sample_indexed_content):
        """Test filtering results by date range."""
        created_files, created_chunks = sample_indexed_content

        search_service = SearchService()

        # TODO: Test date range filtering
        # recent_results = search_service.search_fulltext(
        #     test_db,
        #     query="learning",
        #     date_from=1234567000,  # Before our sample data
        #     date_to=1234568000     # After our sample data
        # )

        # Should include all sample results (within range)
        # assert len(recent_results) > 0, "Should find results in date range"


class TestSearchErrorHandling:
    """Test error handling in search functionality."""

    def test_invalid_fts_query(self, test_db, sample_indexed_content):
        """Test handling of invalid FTS5 queries."""
        created_files, created_chunks = sample_indexed_content

        search_service = SearchService()

        # TODO: Test with invalid FTS syntax
        # try:
        #     results = search_service.search_fulltext(test_db, query='invalid"quote')
        #     # Should either handle gracefully or raise appropriate error
        # except Exception as e:
        #     # Verify it's a handled error, not a crash
        #     assert "FTS" in str(e) or "query" in str(e)

    def test_empty_query(self, test_db, sample_indexed_content):
        """Test handling of empty or whitespace-only queries."""
        created_files, created_chunks = sample_indexed_content

        search_service = SearchService()

        # TODO: Test empty query
        # empty_results = search_service.search_fulltext(test_db, query="")
        # assert empty_results == [], "Empty query should return empty results"

        # TODO: Test whitespace query
        # whitespace_results = search_service.search_fulltext(test_db, query="   ")
        # assert whitespace_results == [], "Whitespace query should return empty results"

    def test_no_fts_index(self, test_db):
        """Test behavior when FTS index doesn't exist or is corrupted."""
        # Create indexed file without creating FTS index
        indexed_file = IndexedFile(
            doc_id="no_fts_test",
            path="test/no_fts.txt",
            file_hash="no_fts_hash",
            size_bytes=100,
            mtime_epoch=1234567890,
            is_indexed=True,
            is_text=True
        )
        test_db.add(indexed_file)
        test_db.commit()

        # Create chunk but don't trigger FTS population
        # (Simulating FTS index corruption or missing)
        test_db.execute(text("DELETE FROM chunks_fts"))  # Clear FTS index
        test_db.commit()

        search_service = SearchService()

        # TODO: Test search against empty FTS index
        # results = search_service.search_fulltext(test_db, query="test")
        # Should handle gracefully, possibly returning empty results


class TestSearchHighlighting:
    """Test search result highlighting functionality."""

    def test_snippet_generation(self, test_db, sample_indexed_content):
        """Test generation of highlighted snippets in search results."""
        created_files, created_chunks = sample_indexed_content

        search_service = SearchService()

        # TODO: Test search with highlighting
        # results = search_service.search_fulltext(test_db, query="machine learning", highlight=True)

        # Verify highlighted snippets are included
        # for result in results:
        #     assert "highlighted_text" in result, "Should include highlighted snippet"
        #     highlighted = result["highlighted_text"]
        #     assert "<mark>" in highlighted or "[HIGHLIGHT]" in highlighted, "Should contain highlight markers"

    def test_custom_highlight_markers(self, test_db, sample_indexed_content):
        """Test custom highlight markers in snippets."""
        created_files, created_chunks = sample_indexed_content

        search_service = SearchService()

        # TODO: Test custom highlight markers
        # results = search_service.search_fulltext(
        #     test_db,
        #     query="machine",
        #     highlight=True,
        #     highlight_start="<em>",
        #     highlight_end="</em>"
        # )

        # Verify custom markers are used
        # for result in results:
        #     highlighted = result.get("highlighted_text", "")
        #     if highlighted:
        #         assert "<em>" in highlighted, "Should use custom start marker"
        #         assert "</em>" in highlighted, "Should use custom end marker"