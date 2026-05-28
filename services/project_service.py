# services\project_service.py
import json
import os
import logging
import tempfile
import shutil
from PySide6.QtWidgets import QMessageBox

logger = logging.getLogger(__name__)

class ProjectService:
    """
    A service class to manage project-related data and operations.
    """
    def __init__(self):
        self.project_data = self.get_default_project_data()
        self.file_path = None
        self.is_saved = True

    def get_default_project_data(self):
        """Returns the default structure for a new project."""
        return {
            'screens': [],
            'comments': {},
            'screen_design_template': {
                "width": 1920,
                "height": 1080,
                "type": "color",
                "color": "#FFFFFF"
            }
        }

    def new_project(self):
        """Resets the project to a new, unsaved state."""
        self.project_data = self.get_default_project_data()
        self.file_path = None
        self.is_saved = False

    def load_project(self, file_path):
        """Loads a project from a file."""
        try:
            if not os.path.exists(file_path):
                logger.error(f"Project file not found: {file_path}")
                raise FileNotFoundError(f"Project file not found: {file_path}")

            with open(file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)

            self.file_path = file_path
            self.project_data = data.get('project_data', self.get_default_project_data())
            # Ensure screen_design_template exists for older projects
            if 'screen_design_template' not in self.project_data:
                self.project_data['screen_design_template'] = self.get_default_project_data()['screen_design_template']
            if 'comments' not in self.project_data:
                self.project_data['comments'] = {}
            self.is_saved = True

            logger.info(f"Project loaded successfully: {file_path}")
            return True, "Project loaded successfully"

        except FileNotFoundError as e:
            logger.error(f"FileNotFoundError: {e}")
            return False, str(e)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON format: {e}")
            return False, f"Invalid project file format: {str(e)}"
        except Exception as e:
            logger.error(f"Error loading project: {e}", exc_info=True)
            return False, f"Error loading project: {str(e)}"

    def save_project(self, file_path=None):
        """Saves the project to a file with atomic write and backup."""
        try:
            if file_path:
                self.file_path = file_path

            if not self.file_path:
                return False, "No file path specified"

            # Ensure directory exists
            os.makedirs(os.path.dirname(self.file_path), exist_ok=True)

            # Prepare data to save
            data_to_save = {
                'project_data': self.project_data,
                'file_path': self.file_path,
                'version': '1.0'
            }

            # Write to temporary file first (atomic write)
            temp_dir = os.path.dirname(self.file_path)
            with tempfile.NamedTemporaryFile(
                mode='w', 
                delete=False, 
                suffix='.json',
                dir=temp_dir,
                encoding='utf-8'
            ) as tmp_file:
                json.dump(data_to_save, tmp_file, indent=2, ensure_ascii=False)
                tmp_path = tmp_file.name

            # Create backup of existing file if it exists
            if os.path.exists(self.file_path):
                backup_path = self.file_path + '.backup'
                try:
                    shutil.copy2(self.file_path, backup_path)
                    logger.info(f"Backup created: {backup_path}")
                except Exception as e:
                    logger.warning(f"Failed to create backup: {e}")

            # Atomic move (replace original with temp file)
            shutil.move(tmp_path, self.file_path)

            self.is_saved = True
            logger.info(f"Project saved successfully: {self.file_path}")
            return True, "Project saved successfully"

        except PermissionError:
            logger.error(f"Permission denied saving to {self.file_path}")
            return False, "Permission denied. Cannot save to this location."
        except OSError as e:
            logger.error(f"File system error during save: {e}")
            return False, f"File system error: {str(e)}"
        except Exception as e:
            logger.error(f"Error saving project: {e}", exc_info=True)
            return False, f"Error saving project: {str(e)}"

    def mark_as_unsaved(self):
        """Marks the current project as having unsaved changes."""
        if self.is_saved:
            self.is_saved = False
            # self.main_window.update_window_title() # This should be handled by the main window

    def get_screen_design_template(self):
        """Returns the project-wide screen design template."""
        return self.project_data.get('screen_design_template', self.get_default_project_data()['screen_design_template'])

    def set_screen_design_template(self, template_data):
        """Sets the project-wide screen design template."""
        self.project_data['screen_design_template'] = template_data
        self.mark_as_unsaved()
