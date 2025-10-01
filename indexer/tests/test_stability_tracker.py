from pathlib import Path
import sys
import importlib
import importlib.util
import sysconfig

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.resolve()))
sys.path.insert(0, str((ROOT / "app").resolve()))
sys.path.insert(0, str((ROOT / "../backend").resolve()))
sys.path.insert(0, str((ROOT / "../backend/app").resolve()))


def _get_stability_tracker():
    queue_backup = sys.modules.get("queue")
    stdlib_queue_path = Path(sysconfig.get_path("stdlib")) / "queue.py"
    std_queue = None
    if stdlib_queue_path.exists():
        spec = importlib.util.spec_from_file_location("queue", stdlib_queue_path)
        std_queue = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(std_queue)
    else:
        std_queue = importlib.import_module("queue")
    sys.modules["queue"] = std_queue

    indexer_app_pkg = importlib.import_module("indexer.app")
    if "app" not in sys.modules:
        sys.modules["app"] = indexer_app_pkg
    if "app.queue" not in sys.modules:
        sys.modules["app.queue"] = importlib.import_module("indexer.app.queue")

    try:
        watcher_module = importlib.import_module("indexer.app.watcher")
        watcher_module = importlib.reload(watcher_module)
        return watcher_module.FileStabilityTracker
    finally:
        if queue_backup is not None:
            sys.modules["queue"] = queue_backup
        else:
            sys.modules.pop("queue", None)


def test_add_file_preserves_progress_when_stat_unchanged(tmp_path):
    FileStabilityTracker = _get_stability_tracker()
    tracker = FileStabilityTracker(stability_checks=3, debounce_seconds=0)
    file_path = tmp_path / "sample.txt"
    file_path.write_text("hello")

    tracker.add_file(str(file_path))
    pending = tracker.pending_files[str(file_path)]
    pending["checks_passed"] = 2
    original_last_check = pending["last_check"]
    original_mtime = pending["mtime"]
    original_size = pending["size"]

    tracker.add_file(str(file_path))

    updated = tracker.pending_files[str(file_path)]
    assert updated["checks_passed"] == 2
    assert updated["mtime"] == original_mtime
    assert updated["size"] == original_size
    assert updated["last_check"] >= original_last_check

    file_path.write_text("hello world")

    tracker.add_file(str(file_path))
    changed = tracker.pending_files[str(file_path)]
    assert changed["checks_passed"] == 0
    assert changed["mtime"] != original_mtime or changed["size"] != original_size
