BEGIN TRANSACTION;
PRAGMA writable_schema=ON;
INSERT INTO sqlite_master(type,name,tbl_name,rootpage,sql)VALUES('table','chunks_fts','chunks_fts',0,'CREATE VIRTUAL TABLE chunks_fts USING fts5(
                    text,
                    content=''document_chunks'',
                    content_rowid=''id'',
                    tokenize = ''trigram''
                )');
INSERT INTO "chunks_fts" VALUES('This is a test document for Phase 4B full-text search. It contains keywords like ''machine learning'', ''artificial intelligence'', and ''data processing''. The search functionality should be able to find this content using FTS5 trigram tokenizer.');
INSERT INTO "chunks_fts" VALUES('This is a test document for Phase 4B full-text search. It contains keywords like ''machine learning'', ''artificial intelligence'', and ''data processing''. The search functionality should be able to find this content using FTS5 trigram tokenizer.

Updated to trigger file watcher event detection.');
INSERT INTO "chunks_fts" VALUES('{"name":"demo","ts":12345}');
