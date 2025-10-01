# Ticket 021: Dual Pipeline Conflict - Old and New Indexing Systems Running Simultaneously

**Type:** BUG
**Priority:** CRITICAL
**Component:** Indexer Service
**Created:** 2025-01-30
**Status:** Resolved (2025-09-30)

# MCP KnowledgeExplorer — Indexing Pipeline Report (Ticket 021)

Author: Senior Dev & Project Architect
Audience: Backend, Indexer, and Frontend teams
Scope: Collapse two-tier reindex into a **single, deterministic Hard Reindex**, fix pipeline contradictions, and align monitoring & tests.

---

> **2025-09-30 Update:** Implemented hard-reset pruning of missing files, automatic Phase 4B job reuse, and an FTS rebuild procedure. Force Reindex now enqueues only core stage jobs with fresh batch IDs, and the dashboard reflects the new counts after an indexer restart or `/control/resume`.

## 1) Problem (short)

The Indexer dashboard shows **378 Text Extract / 0 Chunk / 336 FTS**. That state is impossible if all numbers belong to the same run. It comes from:

* **Force Reindex (hard)** currently **enqueues legacy parent jobs** (`index_file` / `reindex_file`) that spawn the real stage jobs indirectly.
* The dashboard **filters** to the stage jobs (`TEXT_EXTRACT`, `CHUNK`, `FTS_INDEX`) and excludes parents, so counts look inconsistent.
* The **reset** used by Force Reindex does **not** always clear all artifacts (e.g., per-file hashes, FTS tables), so FTS can advance using stale chunks.
* Monitoring is **not batch-scoped**, mixing old and new activity.

We also maintain two reindex modes (soft/hard) that create confusion. You want to **remove the two-tier reindex** and **keep only Hard Reindex**.

---

## 2) Analysis (what’s really happening)

* **Pipeline architecture:**

  * *Parents (legacy coordinators):* `index_file`, `reindex_file` (good for incremental/daily ops).
  * *Core stages:* `TEXT_EXTRACT → CHUNK → FTS_INDEX` (the real work).
* **Force Reindex today:** enqueues **parent jobs** for all files. Parents then spawn core stages with inconsistent batch attribution and heuristics designed for incremental runs.
* **Effects:**

  1. **Batch ambiguity** → UI shows paradox (FTS progressing with CHUNK=0).
  2. **Reset gaps** → stale data reused by FTS.
  3. **Retries & back-pressure** harder to reason about.
  4. **Monitoring** doesn’t make parent→child lineage or batch scope explicit.

**Decision:** Keep parents for incremental file-watcher flows, **do not** use them for reindex. Remove “soft reindex”; **retain only Hard Reindex** that goes **directly** to the core stages.

---

## 3) Solution Overview

A **single, deterministic Hard Reindex** that:

1. **Pauses** workers/watchers (maintenance mode).
2. **Resets** the index state cleanly (chunks, FTS, jobs, per-file metadata).
3. **Enqueues only core stage jobs directly** for the selected scope with a **new `batch_id`**:
   `TEXT_EXTRACT(file_id, batch_id=B)` → `CHUNK` → `FTS_INDEX`.
4. **FTS** either **truncates/rebuilds** or **consumes only chunks from `batch_id=B`**.
5. **Dashboard** becomes **batch-aware**, surfaces legacy jobs explicitly (if present historically), and prevents paradoxical states.

You asked to **remove the two-tier reindex**: we’ll **delete/disable soft reindex** and **rename the button to “Rebuild Index (Hard)”**.

---

## 4) Implementation Plan — **Test-First**, Step-by-Step

> For every step: write tests first, then implement until tests pass.

### Step A — Canonicalize the Reindex Entry Point (Force Reindex = core stages only)

**Goal:** Hard Reindex enqueues **only** `TEXT_EXTRACT` jobs for the selected scope; no parent jobs are created.

**Define tests first**

* `test_force_reindex_enqueues_core_jobs_only()`
  *Given* N files, *when* POST `/admin/reindex/rebuild` is called, *then* `index_jobs` contains only `TEXT_EXTRACT` (no `index_file`/`reindex_file`) with a **new `batch_id`**.
* `test_child_jobs_carry_batch_id()`
  *When* workers run, *then* the generated `CHUNK` and `FTS_INDEX` jobs inherit the same `batch_id`.
* `test_no_parent_jobs_in_batch()`
  Assert zero legacy parent jobs for that `batch_id`.

**Implementation**

* Backend `ReindexService.rebuild(scope)`:

  * enumerate target files
  * enqueue `TEXT_EXTRACT(file_id, batch_id=B)` for each
* **Remove** “soft reindex” API/UI.
* Keep parents for incremental watcher flow; **do not** call them here.

**Acceptance**

* SQL on `index_jobs` shows only `TEXT_EXTRACT/CHUNK/FTS_INDEX` for that batch.

---

### Step B — True Clean Reset + Maintenance Mode

**Goal:** Atomic, programmatic reset; watchers/workers paused; no stale artifacts remain.

**Define tests first**

* `test_full_reset_clears_all_index_state()`
  After `POST /admin/reindex/full-reset-now`:

  * `document_chunks`, FTS tables, `index_jobs` → empty
  * `indexed_files.extracted_text_hash`, `embedding_vector`, `last_indexed_at` → `NULL`
* `test_maintenance_mode_blocks_processing()`
  Jobs do not start while maintenance flag is ON; resume when OFF.

**Implementation**

* New endpoint: `POST /admin/reindex/full-reset-now`

  * set `maintenance_mode=ON`
  * in a transaction: clear `document_chunks`, FTS virtual/index tables (recreate if needed), `index_jobs`, batch tables/flags; `UPDATE indexed_files SET extracted_text_hash=NULL, embedding_vector=NULL, last_indexed_at=NULL`
  * set `maintenance_mode=OFF`
* Ensure **all workers/watchers** check `maintenance_mode` before pulling work.

**Acceptance**

* Tables verified clean via SQL; no job begins during reset.

---

### Step C — FTS Batch Safety

**Goal:** FTS reads only from current batch or is fully rebuilt.

**Define tests first**

* `test_fts_truncate_then_rebuild()` (if choosing truncate)
  *Given* prior data, after reset+rebuild, searches return only content from current batch.
* `test_fts_filters_by_batch_id()` (if choosing filter)
  FTS INDEX consumer ignores chunks not in `batch_id=B`.

**Implementation (pick one)**

1. **Truncate & rebuild**: recreate FTS virtual tables before enqueueing.
2. **Batch filter**: FTS consumer queries only `document_chunks where batch_id=B`.

**Acceptance**

* No mixing of results across batches.

---

### Step D — Monitoring & Dashboard (batch-aware, consistent)

**Goal:** No paradox; make scope explicit; show legacy presence clearly.

**Define tests first (UI/integration)**

* `test_pipeline_tiles_are_batch_scoped()`
  With `batch=B`, CHUNK count reflects actual CHUNK jobs for B.
* `test_consistency_rule_fts_leq_chunk()`
  UI flags if FTS > CHUNK for the selected batch.
* `test_legacy_banner_visibility()`
  If legacy jobs exist anywhere, a banner appears explaining filtering.

**Implementation**

* Add **Batch Selector** (default = current batch).
* Pipeline tiles show `TEXT_EXTRACT/CHUNK/FTS_INDEX` **for selected batch only**.
* **Consistency rule**: flag if FTS completed > files-with-chunks.
* **Legacy banner**: “Legacy jobs detected; pipeline metrics show core-stage jobs only.”
* Bottom actions operate **on current batch**: *Retry failed*, *Clear failed history*, *View logs*.

**Acceptance**

* The “0 CHUNK / many FTS” paradox cannot appear for the selected batch unless there’s a real data error (which is then flagged).

---

### Step E — Observability & Guardrails

**Goal:** Clear lineage, clean retries, safe startup.

**Define tests first**

* `test_chunk_stage_emits_structured_logs()`
  Logs include `file_id`, `batch_id`, `text_bytes`, `chunks_created`.
* `test_startup_guard_unknown_job_types()`
  Startup fails fast if unknown job types are present post-migration.
* `test_retry_semantics_by_stage_and_batch()`
  Retrying failed CHUNK jobs re-enqueues only those CHUNK jobs within batch B.

**Implementation**

* Structured logs/metrics at CHUNK and FTS stages.
* Startup validator for allowed job types.
* Retry endpoints operate by `batch_id` and `stage`.

**Acceptance**

* Clean, auditable lineage and targeted retries.

---

## 5) Data & API Changes (concise)

* **Jobs table:** ensure `batch_id` present & required for core stages.
* **Endpoints:**

  * `POST /admin/reindex/rebuild` → enumerates files, enqueues `TEXT_EXTRACT(..., batch_id=B)`.
  * `POST /admin/reindex/full-reset-now` → maintenance, reset, (optionally) auto-rebuild.
* **Remove** “soft reindex” API & UI.
* **Dashboard:** add Batch Selector and consistency checks.

---

## 6) Post-Deploy Validation Checklist

1. Trigger **Full Reset** → verify tables are empty / metadata NULL.
2. Run **Rebuild Index** → SQL:

```sql
SELECT job_type, COUNT(*) FROM index_jobs WHERE batch_id=:B GROUP BY job_type;
```

Expect only `TEXT_EXTRACT/CHUNK/FTS_INDEX`.
3) Watch dashboard (batch=B) → `TEXT_EXTRACT → CHUNK → FTS_INDEX` progress aligns; no paradox flags.
4) Spot check searches → only current batch content returned.
5) Retry a few failed CHUNK jobs → they re-run in batch B and succeed.

---

## 7) Risks & Mitigations

* **Watcher interference** → Enforce maintenance flag in all workers/watchers.
* **FTS residuals** → Prefer truncate/recreate on rebuild or strict batch filter.
* **Hidden legacy usage** → UI banner + startup guard on job types.
* **Load spikes on rebuild** → use queue throttling and clear worker concurrency settings.

---

## 8) What we are **removing** / **keeping**

* **Removed:** “Soft Reindex” path (two-tier reindex).
* **Kept:** Parent jobs for **incremental watcher** workflows, but **never** used by Rebuild Index.

---

### One-line summary for the team

> **Rebuild Index = pause → clean reset → enqueue only core stages with a batch_id → FTS builds from that batch → dashboard shows batch-scoped progress with consistency checks. No soft reindex.**

If you want, I can also draft the exact endpoint contracts, migration DDL, and minimal diffs for `ReindexService` in a follow-up.
