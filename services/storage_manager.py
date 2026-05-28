import json
import logging
import os
import re
import tempfile
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class ProjectRef:
    project_id: str
    project_name: str
    project_path: Path


class StorageManager:
    def __init__(self, base_dir: Optional[Path] = None):
        if base_dir is None:
            home_dir = Path.home()
            if str(home_dir) == "." or not home_dir.exists():
                home_dir = Path.cwd()
            base_dir = home_dir / ".hmi_designer" / "json_data"
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _default_settings(self) -> dict[str, Any]:
        return {
            "screen_design_template": {
                "width": 1920,
                "height": 1080,
                "type": "color",
                "color": "#FFFFFF",
            }
        }

    def _default_tags(self) -> dict[str, Any]:
        return {"tag_lists": {}}

    def _default_comments(self) -> dict[str, Any]:
        return {"comments": {}}

    def _default_action_history(self) -> dict[str, Any]:
        return {"undo": [], "redo": []}

    def _sanitize_project_name(self, project_name: str | None) -> str:
        raw = (project_name or "project").strip().lower()
        value = re.sub(r"[^a-z0-9_-]+", "_", raw).strip("_-")
        return value or "project"

    def create_project(self, project_name: str | None) -> ProjectRef:
        safe_name = self._sanitize_project_name(project_name)
        project_id = uuid.uuid4().hex[:8]
        project_path = self.base_dir / f"{safe_name}_{project_id}"
        project_path.mkdir(parents=True, exist_ok=False)
        (project_path / "screens").mkdir(exist_ok=True)

        self._save_json_atomic(project_path / "settings.json", self._default_settings())
        self._save_json_atomic(project_path / "tags.json", self._default_tags())
        self._save_json_atomic(project_path / "comments.json", self._default_comments())
        self._save_json_atomic(project_path / "action_history.json", self._default_action_history())

        return ProjectRef(project_id=project_id, project_name=safe_name, project_path=project_path)

    def _load_json(self, path: Path, default: Any) -> Any:
        if not path.exists():
            return default
        try:
            with self._acquire_lock(path):
                with path.open("r", encoding="utf-8") as fh:
                    return json.load(fh)
        except Exception as exc:
            logger.warning("Failed to load JSON from %s: %s", path, exc)
            return default

    def _save_json_atomic(self, path: Path, payload: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._acquire_lock(path):
            fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as tmp_file:
                    json.dump(payload, tmp_file, indent=2, ensure_ascii=False)
                    tmp_file.flush()
                    os.fsync(tmp_file.fileno())
                os.replace(tmp_name, path)
            finally:
                if os.path.exists(tmp_name):
                    os.unlink(tmp_name)

    @contextmanager
    def _acquire_lock(self, path: Path, timeout: float = 3.0, interval: float = 0.05):
        lock_path = path.with_suffix(path.suffix + ".lock")
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        lock_file = lock_path.open("a+b")
        start = time.time()
        locked = False
        try:
            while True:
                try:
                    if os.name == "nt":
                        import msvcrt

                        msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
                    else:
                        import fcntl

                        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    locked = True
                    break
                except Exception:
                    if (time.time() - start) >= timeout:
                        break
                    time.sleep(interval)
            yield
        finally:
            if locked:
                try:
                    if os.name == "nt":
                        import msvcrt

                        msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
                    else:
                        import fcntl

                        fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
                except Exception:
                    pass
            lock_file.close()

    def load_settings(self, project_path: Path) -> dict[str, Any]:
        return self._load_json(project_path / "settings.json", self._default_settings())

    def save_settings(self, project_path: Path, payload: dict[str, Any]) -> None:
        self._save_json_atomic(project_path / "settings.json", payload)

    def load_tags(self, project_path: Path) -> dict[str, Any]:
        return self._load_json(project_path / "tags.json", self._default_tags())

    def save_tags(self, project_path: Path, payload: dict[str, Any]) -> None:
        self._save_json_atomic(project_path / "tags.json", payload)

    def load_comments(self, project_path: Path) -> dict[str, Any]:
        return self._load_json(project_path / "comments.json", self._default_comments())

    def save_comments(self, project_path: Path, payload: dict[str, Any]) -> None:
        self._save_json_atomic(project_path / "comments.json", payload)

    def list_screens(self, project_path: Path) -> list[str]:
        screens_dir = project_path / "screens"
        if not screens_dir.exists():
            return []
        return sorted(p.stem for p in screens_dir.glob("*.json"))

    def load_screen(self, project_path: Path, screen_id: str) -> dict[str, Any]:
        return self._load_json(project_path / "screens" / f"{screen_id}.json", {})

    def save_screen(self, project_path: Path, screen_id: str, data: dict[str, Any]) -> None:
        self._save_json_atomic(project_path / "screens" / f"{screen_id}.json", data)

    def delete_screen(self, project_path: Path, screen_id: str) -> None:
        target = project_path / "screens" / f"{screen_id}.json"
        if target.exists():
            target.unlink()
