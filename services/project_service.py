import json
import os
import logging
import tempfile
import shutil
import uuid
import re
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class ProjectService:
    """Manages legacy .hmi project data and a robust JSON storage workspace."""

    def __init__(self):
        self.project_data = self.get_default_project_data()
        self.file_path = None
        self.is_saved = True
        self.project_id = None
        self.project_root = None
        self._workspace_root = self._default_workspace_root()
        self.main_window = None
        self.tag_service = None
        self.comment_service = None

    def _default_workspace_root(self) -> Path:
        return Path.cwd() / 'json_data'

    def _sanitize_name(self, value: str) -> str:
        cleaned = re.sub(r'[^a-zA-Z0-9_-]+', '_', (value or '').strip())
        return cleaned[:64].strip('_') or 'project'

    def _atomic_json_write(self, path: Path, payload: Dict[str, Any]):
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json', dir=path.parent, encoding='utf-8') as tmp:
            json.dump(payload, tmp, indent=2, ensure_ascii=False)
            temp_path = Path(tmp.name)
        os.replace(temp_path, path)

    def _read_json(self, path: Path, default: Any):
        if not path.exists():
            return default
        with path.open('r', encoding='utf-8') as handle:
            return json.load(handle)

    def get_default_project_data(self):
        return {
            'screens': [],
            'comments': {},
            'tags': {},
            'screen_design_template': {
                "width": 1920,
                "height": 1080,
                "type": "color",
                "color": "#FFFFFF"
            }
        }

    def new_project(self, project_name: str = 'Untitled Project'):
        self.project_data = self.get_default_project_data()
        self.file_path = None
        self.is_saved = False
        self.project_id = str(uuid.uuid4())
        safe_name = self._sanitize_name(project_name)
        self.project_root = self._workspace_root / f"{safe_name}_{self.project_id[:8]}"
        self.initialize_storage(project_name=project_name)

    def initialize_storage(self, project_name: str = 'Untitled Project'):
        if not self.project_root:
            self.project_id = self.project_id or str(uuid.uuid4())
            safe_name = self._sanitize_name(project_name)
            self.project_root = self._workspace_root / f"{safe_name}_{self.project_id[:8]}"

        (self.project_root / 'screens').mkdir(parents=True, exist_ok=True)
        (self.project_root / 'tags').mkdir(parents=True, exist_ok=True)
        (self.project_root / 'comments').mkdir(parents=True, exist_ok=True)
        default_settings = {
            'project_name': project_name,
            'project_id': self.project_id,
            'resolution': {
                'width': self.project_data['screen_design_template']['width'],
                'height': self.project_data['screen_design_template']['height'],
            },
            'author': '',
            'global_config': {}
        }
        if not (self.project_root / 'settings.json').exists():
            self._atomic_json_write(self.project_root / 'settings.json', default_settings)
        if not (self.project_root / 'action_history.json').exists():
            self._atomic_json_write(self.project_root / 'action_history.json', {'undo': [], 'redo': []})
        if not (self.project_root / 'clipboard.json').exists():
            self._atomic_json_write(self.project_root / 'clipboard.json', {'items': []})

    def _screen_file(self, screen_name: str) -> Path:
        safe = self._sanitize_name(screen_name)
        return self.project_root / 'screens' / f'{safe}.json'

    def save_screen_state(self, screen_name: str, screen_payload: Dict[str, Any]):
        if not self.project_root:
            self.initialize_storage()
        self._atomic_json_write(self._screen_file(screen_name), screen_payload)

    def load_screen_state(self, screen_name: str) -> Dict[str, Any]:
        if not self.project_root:
            return {}
        return self._read_json(self._screen_file(screen_name), {})

    def register_services(self, tag_service=None, comment_service=None):
        """Attach data services so entity changes can be synced immediately."""
        if tag_service is not None:
            self.tag_service = tag_service
            if hasattr(tag_service, 'set_project_service'):
                tag_service.set_project_service(self)
        if comment_service is not None:
            self.comment_service = comment_service
            if hasattr(comment_service, 'set_project_service'):
                comment_service.set_project_service(self)

    def _tag_file(self, tag_number) -> Path:
        return self.project_root / 'tags' / f'tag_{tag_number}.json'

    def _comment_file(self, comment_number) -> Path:
        return self.project_root / 'comments' / f'comment_{comment_number}.json'

    def sync_tag(self, tag_number, tag_payload):
        """Immediately write one tag payload to project_root/tags/tag_<number>.json."""
        if tag_number is None:
            return
        if not self.project_root:
            self.initialize_storage()
        number_str = str(tag_number)
        self.project_data.setdefault('tags', {})[number_str] = tag_payload
        # Keep legacy consumers in sync while the app migrates to TagService.
        self.project_data.setdefault('tag_lists', {})[number_str] = tag_payload
        self._atomic_json_write(self._tag_file(number_str), {'tag': tag_payload})

    def delete_tag(self, tag_number):
        """Immediately delete project_root/tags/tag_<number>.json and in-memory references."""
        if tag_number is None:
            return
        if not self.project_root:
            self.initialize_storage()
        number_str = str(tag_number)
        self.project_data.setdefault('tags', {}).pop(number_str, None)
        self.project_data.setdefault('tag_lists', {}).pop(number_str, None)
        self._tag_file(number_str).unlink(missing_ok=True)

    def sync_comment(self, comment_number, comment_payload):
        """Immediately write one comment payload to project_root/comments/comment_<number>.json."""
        if comment_number is None:
            return
        if not self.project_root:
            self.initialize_storage()
        number_str = str(comment_number)
        self.project_data.setdefault('comments', {})[number_str] = comment_payload
        self._atomic_json_write(self._comment_file(number_str), {'comment': comment_payload})

    def delete_comment(self, comment_number):
        """Immediately delete project_root/comments/comment_<number>.json and in-memory references."""
        if comment_number is None:
            return
        if not self.project_root:
            self.initialize_storage()
        number_str = str(comment_number)
        self.project_data.setdefault('comments', {}).pop(number_str, None)
        self._comment_file(number_str).unlink(missing_ok=True)

    def save_structured_project_state(self):
        if not self.project_root:
            self.initialize_storage()
        tags_dir = self.project_root / 'tags'
        comments_dir = self.project_root / 'comments'
        tags_dir.mkdir(parents=True, exist_ok=True)
        comments_dir.mkdir(parents=True, exist_ok=True)

        tag_service = self.tag_service or getattr(getattr(self, 'main_window', None), 'tag_service', None)
        comment_service = self.comment_service or getattr(getattr(self, 'main_window', None), 'comment_service', None)
        if tag_service is not None:
            self.project_data['tags'] = tag_service.get_all_data()
            self.project_data['tag_lists'] = self.project_data['tags']
        if comment_service is not None:
            self.project_data['comments'] = comment_service.get_all_data()

        tags_data = self.project_data.get('tags') or self.project_data.get('tag_lists', {}) or {}
        comments_data = self.project_data.get('comments', {}) or {}

        existing_tag_files = set(tags_dir.glob('tag_*.json'))
        active_tag_files = set()
        for tag_number, tag_payload in tags_data.items():
            tag_path = tags_dir / f'tag_{tag_number}.json'
            active_tag_files.add(tag_path)
            self._atomic_json_write(tag_path, {'tag': tag_payload})
        for stale_file in existing_tag_files - active_tag_files:
            stale_file.unlink(missing_ok=True)

        existing_comment_files = set(comments_dir.glob('comment_*.json'))
        active_comment_files = set()
        for comment_number, comment_payload in comments_data.items():
            comment_path = comments_dir / f'comment_{comment_number}.json'
            active_comment_files.add(comment_path)
            self._atomic_json_write(comment_path, {'comment': comment_payload})
        for stale_file in existing_comment_files - active_comment_files:
            stale_file.unlink(missing_ok=True)

    def _load_entities_from_directory(self, directory: Path, prefix: str, key: str) -> Dict[str, Any]:
        loaded_data: Dict[str, Any] = {}
        if not directory.exists():
            return loaded_data
        for path in sorted(directory.glob(f'{prefix}_*.json')):
            suffix = path.stem.replace(f'{prefix}_', '', 1)
            if not suffix:
                continue
            payload = self._read_json(path, {})
            if isinstance(payload, dict) and key in payload:
                loaded_data[str(suffix)] = payload[key]
            else:
                loaded_data[str(suffix)] = payload
        return loaded_data

    def append_action_history(self, command_name: str, before: Optional[Dict[str, Any]], after: Optional[Dict[str, Any]]):
        if not self.project_root:
            return
        history_path = self.project_root / 'action_history.json'
        history = self._read_json(history_path, {'undo': [], 'redo': []})
        history['undo'].append({'action': command_name, 'before': before, 'after': after})
        history['redo'] = []
        self._atomic_json_write(history_path, history)

    def update_clipboard_buffer(self, items):
        if not self.project_root:
            return
        self._atomic_json_write(self.project_root / 'clipboard.json', {'items': items})

    def load_project(self, file_path):
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Project file not found: {file_path}")
            with open(file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
            self.file_path = file_path
            self.project_data = data.get('project_data', self.get_default_project_data())
            if 'screen_design_template' not in self.project_data:
                self.project_data['screen_design_template'] = self.get_default_project_data()['screen_design_template']
            if 'comments' not in self.project_data:
                self.project_data['comments'] = {}
            if 'tags' not in self.project_data:
                self.project_data['tags'] = {}
            self.project_id = data.get('project_id', str(uuid.uuid4()))
            project_name = Path(file_path).stem
            self.project_root = self._workspace_root / f"{self._sanitize_name(project_name)}_{self.project_id[:8]}"
            self.initialize_storage(project_name=project_name)
            loaded_tags = self._load_entities_from_directory(self.project_root / 'tags', 'tag', 'tag')
            loaded_comments = self._load_entities_from_directory(self.project_root / 'comments', 'comment', 'comment')
            if loaded_tags:
                self.project_data['tags'] = loaded_tags
            else:
                self.project_data['tags'] = self.project_data.get('tags') or self.project_data.get('tag_lists', {}) or {}
            self.project_data['tag_lists'] = self.project_data['tags']
            if loaded_comments:
                self.project_data['comments'] = loaded_comments
            self.is_saved = True
            return True, "Project loaded successfully"
        except FileNotFoundError as e:
            return False, str(e)
        except json.JSONDecodeError as e:
            return False, f"Invalid project file format: {str(e)}"
        except Exception as e:
            logger.error(f"Error loading project: {e}", exc_info=True)
            return False, f"Error loading project: {str(e)}"

    def save_project(self, file_path=None):
        try:
            if file_path:
                self.file_path = file_path
            if not self.file_path:
                return False, "No file path specified"
            os.makedirs(os.path.dirname(self.file_path), exist_ok=True)

            tag_service = self.tag_service or getattr(getattr(self, 'main_window', None), 'tag_service', None)
            comment_service = self.comment_service or getattr(getattr(self, 'main_window', None), 'comment_service', None)
            if tag_service is not None:
                self.project_data['tags'] = tag_service.get_all_data()
            if comment_service is not None:
                self.project_data['comments'] = comment_service.get_all_data()

            self.save_structured_project_state()
            data_to_save = {
                'project_data': self.project_data,
                'file_path': self.file_path,
                'project_id': self.project_id,
                'version': '2.0'
            }
            temp_dir = os.path.dirname(self.file_path)
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json', dir=temp_dir, encoding='utf-8') as tmp_file:
                json.dump(data_to_save, tmp_file, indent=2, ensure_ascii=False)
                tmp_path = tmp_file.name
            if os.path.exists(self.file_path):
                try:
                    shutil.copy2(self.file_path, self.file_path + '.backup')
                except Exception:
                    pass
            shutil.move(tmp_path, self.file_path)
            self.is_saved = True
            return True, "Project saved successfully"
        except PermissionError:
            return False, "Permission denied. Cannot save to this location."
        except OSError as e:
            return False, f"File system error: {str(e)}"
        except Exception as e:
            logger.error(f"Error saving project: {e}", exc_info=True)
            return False, f"Error saving project: {str(e)}"

    def mark_as_unsaved(self):
        self.is_saved = False

    def get_screen_design_template(self):
        return self.project_data.get('screen_design_template', self.get_default_project_data()['screen_design_template'])

    def set_screen_design_template(self, template_data):
        self.project_data['screen_design_template'] = template_data
        self.mark_as_unsaved()
