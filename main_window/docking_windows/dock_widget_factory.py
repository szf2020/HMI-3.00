# main_window\docking_windows\dock_widget_factory.py
# Import the dock widget classes
from .project_tree_dock import ProjectTreeDock
from .screen_tree_dock import ScreenTreeDock
from .system_tree_dock import SystemTreeDock
from .property_tree_dock import PropertyTreeDock
from .library_dock import LibraryDock
from .screen_image_list_dock import ScreenImageListDock
from .tag_search_dock import TagSearchDock
from .data_browser_dock import DataBrowserDock
from .ip_address_dock import IPAddressDock
from .controller_list_dock import ControllerListDock
from .data_view_dock import DataViewDock
from .layers_dock import LayersDock
from ..services.icon_service import IconService
from ..widgets.dock_title_bar import DockTitleBar

class DockWidgetFactory:
    """
    A factory class to create and manage all dock widgets for the main application.
    This helps in keeping the main window class clean and organizes the dockable
    windows systematically.
    """

    def __init__(self, main_window):
        """
        Initializes the factory with a reference to the main window.
        
        Args:
            main_window (QMainWindow): The main window instance to which docks will be added.
        """
        self.main_window = main_window
        self.docks = {}

    def create_all_docks(self):
        """
        Creates all the predefined dock widgets for the application by instantiating
        their respective classes.
        """
        self.docks["project_tree"] = ProjectTreeDock(self.main_window, self.main_window.comment_service)
        self.docks["screen_tree"] = ScreenTreeDock(self.main_window)
        self.docks["system_tree"] = SystemTreeDock(self.main_window)
        
        self.docks["property_tree"] = PropertyTreeDock(self.main_window)
        self.docks["library"] = LibraryDock(self.main_window)
        self.docks["screen_image_list"] = ScreenImageListDock(self.main_window)
        
        self.docks["tag_search"] = TagSearchDock(self.main_window)
        self.docks["data_browser"] = DataBrowserDock(self.main_window)
        self.docks["ip_address"] = IPAddressDock(self.main_window)
        self.docks["controller_list"] = ControllerListDock(self.main_window)
        self.docks["data_view"] = DataViewDock(self.main_window)
        self.docks["layers"] = LayersDock(self.main_window)

        # Set window icons for all docks
        dock_icons = {
            "project_tree": "dock-project-tree",
            "screen_tree": "dock-screen-tree",
            "system_tree": "dock-system-tree",
            "property_tree": "dock-property-tree",
            "library": "dock-library",
            "screen_image_list": "dock-screen-image-list",
            "tag_search": "dock-tag-search",
            "data_browser": "dock-data-browser",
            "ip_address": "dock-ip-address",
            "controller_list": "dock-controller-list",
            "data_view": "dock-data-view",
            "layers": "dock-layers"
        }
        
        for name, icon_name in dock_icons.items():
            if name in self.docks:
                dock = self.docks[name]
                icon = IconService.get_icon(icon_name)
                dock.setWindowIcon(icon)
                
                # Set custom title bar with icon
                title = dock.windowTitle()
                title_bar = DockTitleBar(dock, title, icon)
                dock.setTitleBarWidget(title_bar)

    def get_dock(self, name):
        """
        Retrieves a dock widget by its name.
        
        Args:
            name (str): The object name of the dock to retrieve.
            
        Returns:
            QDockWidget or None: The dock widget instance if found, otherwise None.
        """
        return self.docks.get(name)