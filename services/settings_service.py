# services\settings_service.py"
import json
import os
from PySide6.QtCore import QSettings

class SettingsService:
    """
    Manages loading and saving of application settings from a JSON file.
    This service helps in persisting UI states like window size, position,
    and the state of dock widgets and toolbars across sessions.
    """
    def __init__(self, file_path='settings.json'):
        """
        Initializes the SettingsService.

        Args:
            file_path (str): The path to the settings file.
        """
        self.file_path = file_path
        self.settings = self.load_settings()

    def load_settings(self):
        """
        Loads the settings from the JSON file. If the file doesn't exist,
        it returns a default dictionary.
        """
        if not os.path.exists(self.file_path):
            return self._get_default_settings()
        try:
            with open(self.file_path, 'r') as f:
                settings = json.load(f)
                # Ensure visibility keys exist for backward compatibility
                if "toolbars_visibility" not in settings:
                    settings["toolbars_visibility"] = {}
                if "docks_visibility" not in settings:
                    settings["docks_visibility"] = {}
                # Ensure view_settings key exists
                if "view_settings" not in settings:
                    settings["view_settings"] = self._get_default_settings()["view_settings"]
                return settings
        except (json.JSONDecodeError, FileNotFoundError):
            return self._get_default_settings()

    def _get_default_settings(self):
        """Returns the default settings structure."""
        return {
            "main_window": {
                "geometry": None,
                "state": None
            },
            "toolbars_visibility": {},
            "docks_visibility": {},
            "view_settings": {
                "object_snap": True,
                "snap_distance": "10",
                "state_number": 0,
                "display_items": {
                    "select_mode": True,
                    "tag": False,
                    "object_id": False,
                    "transform_line": True,
                    "click_area": False
                }
            }
        }

    def save_settings(self, main_window):
        """
        Saves the current state of the main window and visibility of UI elements
        to the JSON file.

        Args:
            main_window (QMainWindow): The main window instance to save settings from.
        """
        self.settings['main_window']['geometry'] = main_window.saveGeometry().data().hex()
        self.settings['main_window']['state'] = main_window.saveState().data().hex()
        
        # Save visibility of toolbars and docks
        self.settings['toolbars_visibility'] = {
            name: toolbar.isVisible() for name, toolbar in main_window.toolbars.items()
        }
        self.settings['docks_visibility'] = {
            name: dock.isVisible() for name, dock in main_window.dock_factory.docks.items()
        }
        
        # Save view settings
        view_toolbar = main_window.toolbars.get("View")
        if view_toolbar:
            self.settings['view_settings'] = {
                "object_snap": view_toolbar.object_snap_checkbox.isChecked(),
                "snap_distance": view_toolbar.snap_combo.currentText(),
                "state_number": view_toolbar.current_state,
                "display_items": {
                    "select_mode": main_window.view_menu.select_mode_action.isChecked(),
                    "tag": main_window.view_menu.tag_action.isChecked(),
                    "object_id": main_window.view_menu.object_id_action.isChecked(),
                    "transform_line": main_window.view_menu.transform_line_action.isChecked(),
                    "click_area": main_window.view_menu.click_area_action.isChecked()
                }
            }
        
        with open(self.file_path, 'w') as f:
            json.dump(self.settings, f, indent=4)

    def get_main_window_settings(self):
        """
        Returns the settings for the main window.
        """
        return self.settings.get('main_window', {})

    def get_toolbars_visibility(self):
        """Returns the visibility settings for toolbars."""
        return self.settings.get('toolbars_visibility', {})

    def get_docks_visibility(self):
        """Returns the visibility settings for dock widgets."""
        return self.settings.get('docks_visibility', {})

    def get_view_settings(self):
        """Returns the view settings."""
        return self.settings.get('view_settings', self._get_default_settings()['view_settings'])

