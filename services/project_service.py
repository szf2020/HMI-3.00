import json
import logging
from dataclasses import dataclass
from pathlib import Path

from services.storage_manager import StorageManager

logger = logging.getLogger(__name__)


@dataclass
class ProjectMetadata:
    project_id: str
    project_path: Path
    source_path: Path | None = None


class ProjectService:
    """A service class to manage project-related data and operations."""

    def __init__(self):
        self.storage = StorageManager()
        self.project_data = self.get_default_project_data()
        self.file_path = None
        self.project_metadata: ProjectMetadata | None = None
        self.is_saved = True

    def get_default_project_data(self):
        return {
            "screens": [],
            "comments": {},
            "tag_lists": {},
            "screen_design_template": {
                "width": 1920,
                "height": 1080,
                "type": "color",
                "color": "#FFFFFF",
            },
        }

    def new_project(self):
        project_ref = self.storage.create_project("project")
        self.project_data = self.get_default_project_data()
        self.project_metadata = ProjectMetadata(project_ref.project_id, project_ref.project_path)
        self.file_path = str(project_ref.project_path)
        self.is_saved = False

    def _load_folder_project(self, project_dir: Path):
        settings = self.storage.load_settings(project_dir)
        tags = self.storage.load_tags(project_dir)
        comments = self.storage.load_comments(project_dir)

        screens = []
        for screen_id in self.storage.list_screens(project_dir):
            screen_payload = self.storage.load_screen(project_dir, screen_id)
            if screen_payload:
                screens.append(screen_payload)

        self.project_data = self.get_default_project_data()
        self.project_data["screens"] = screens
        self.project_data["screen_design_template"] = settings.get(
            "screen_design_template", self.get_default_project_data()["screen_design_template"]
        )
        self.project_data["tag_lists"] = tags.get("tag_lists", {})
        self.project_data["comments"] = comments.get("comments", {})

        self.project_metadata = ProjectMetadata(project_dir.name.split("_")[-1], project_dir, project_dir)
        self.file_path = str(project_dir)

    def _migrate_legacy_hmi(self, file_path: Path):
        with file_path.open("r", encoding="utf-8") as file:
            data = json.load(file)

        project_data = data.get("project_data", self.get_default_project_data())
        name = file_path.stem
        project_ref = self.storage.create_project(name)

        self.storage.save_settings(project_ref.project_path, {
            "screen_design_template": project_data.get(
                "screen_design_template", self.get_default_project_data()["screen_design_template"]
            )
        })
        self.storage.save_tags(project_ref.project_path, {"tag_lists": project_data.get("tag_lists", {})})
        self.storage.save_comments(project_ref.project_path, {"comments": project_data.get("comments", {})})

        for idx, screen in enumerate(project_data.get("screens", [])):
            screen_id = str(screen.get("id") or screen.get("name") or f"screen_{idx + 1}")
            self.storage.save_screen(project_ref.project_path, screen_id, screen)

        self.project_data = project_data
        if "screen_design_template" not in self.project_data:
            self.project_data["screen_design_template"] = self.get_default_project_data()["screen_design_template"]
        if "comments" not in self.project_data:
            self.project_data["comments"] = {}
        if "tag_lists" not in self.project_data:
            self.project_data["tag_lists"] = {}

        self.project_metadata = ProjectMetadata(project_ref.project_id, project_ref.project_path, file_path)
        self.file_path = str(file_path)

    def load_project(self, file_path):
        try:
            path = Path(file_path)
            if not path.exists():
                raise FileNotFoundError(f"Project file not found: {file_path}")

            if path.is_dir():
                self._load_folder_project(path)
            else:
                self._migrate_legacy_hmi(path)

            self.is_saved = True
            logger.info("Project loaded successfully: %s", file_path)
            return True, "Project loaded successfully"
        except FileNotFoundError as exc:
            logger.error("FileNotFoundError: %s", exc)
            return False, str(exc)
        except json.JSONDecodeError as exc:
            logger.error("Invalid JSON format: %s", exc)
            return False, f"Invalid project file format: {str(exc)}"
        except Exception as exc:
            logger.error("Error loading project: %s", exc, exc_info=True)
            return False, f"Error loading project: {str(exc)}"

    def save_project(self, file_path=None):
        try:
            if file_path:
                self.file_path = file_path

            if not self.project_metadata:
                project_ref = self.storage.create_project(Path(self.file_path).stem if self.file_path else "project")
                self.project_metadata = ProjectMetadata(project_ref.project_id, project_ref.project_path)

            project_path = self.project_metadata.project_path
            self.storage.save_settings(project_path, {
                "screen_design_template": self.project_data.get(
                    "screen_design_template", self.get_default_project_data()["screen_design_template"]
                )
            })
            self.storage.save_tags(project_path, {"tag_lists": self.project_data.get("tag_lists", {})})
            self.storage.save_comments(project_path, {"comments": self.project_data.get("comments", {})})

            existing = set(self.storage.list_screens(project_path))
            current = set()
            for idx, screen in enumerate(self.project_data.get("screens", [])):
                screen_id = str(screen.get("id") or screen.get("name") or f"screen_{idx + 1}")
                current.add(screen_id)
                self.storage.save_screen(project_path, screen_id, screen)

            for deleted in existing - current:
                self.storage.delete_screen(project_path, deleted)

            self.is_saved = True
            logger.info("Project saved successfully: %s", project_path)
            return True, "Project saved successfully"
        except Exception as exc:
            logger.error("Error saving project: %s", exc, exc_info=True)
            return False, f"Error saving project: {str(exc)}"

    def mark_as_unsaved(self):
        if self.is_saved:
            self.is_saved = False

    def get_screen_design_template(self):
        return self.project_data.get("screen_design_template", self.get_default_project_data()["screen_design_template"])

    def set_screen_design_template(self, template_data):
        self.project_data["screen_design_template"] = template_data
        self.mark_as_unsaved()
