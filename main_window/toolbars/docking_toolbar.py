# main_window\toolbars\docking_toolbar.py
from PySide6.QtWidgets import QToolBar, QCheckBox
from PySide6.QtGui import QAction
from ..services.icon_service import IconService

class DockingToolbar(QToolBar):
    """
    A floating toolbar to control the visibility of docking windows.
    Its state is synchronized with the View > Docking Window menu via a
    central controller in the MainWindow.
    """
    def __init__(self, main_window, view_menu):
        super().__init__("Window Display", main_window)
        self.main_window = main_window
        self.view_menu = view_menu

        # This list should match the one in view_menu.py for consistency
        docking_items = [
            ("Project Tree", IconService.get_icon('dock-project-tree')),
            ("Screen Tree", IconService.get_icon('dock-screen-tree')),
            ("System Tree", IconService.get_icon('dock-system-tree')),
            ("Layers", IconService.get_icon('dock-layers')),
            ("Tag Search", IconService.get_icon('dock-tag-search')),
            ("Data Browser", IconService.get_icon('dock-data-browser')),
            ("Property Tree", IconService.get_icon('dock-property-tree')),
            ("IP Address", IconService.get_icon('dock-ip-address')),
            ("Library", IconService.get_icon('dock-library')),
            ("Controller List", IconService.get_icon('dock-controller-list')),
            ("Data View", IconService.get_icon('dock-data-view')),
            ("Screen Image List", IconService.get_icon('dock-screen-image-list')),
        ]
        
        for text, icon in docking_items:
            dock_name = text.lower().replace(' ', '_')
            
            # Create a new, checkable action for the toolbar
            toolbar_action = QAction(icon, text, self)
            toolbar_action.setCheckable(True)
            toolbar_action.setToolTip(f"Show/Hide {text}")
            # Set a unique object name to find it later
            toolbar_action.setObjectName(f"toggle_{dock_name}")

            self.addAction(toolbar_action)
