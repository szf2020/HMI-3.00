# main_window\menus\view_menu.py
from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QCheckBox, QWidgetAction
from ..services.icon_service import IconService

class ViewMenu:
    """
    Creates the 'View' menu and its actions.
    """
    def __init__(self, main_window, menu_bar):
        self.main_window = main_window
        view_menu = menu_bar.addMenu("&View")
        
        preview_icon = IconService.get_icon('view-preview')
        
        self.preview_action = QAction(preview_icon,"Preview", self.main_window)
        view_menu.addAction(self.preview_action)

        # State No. Submenu
        state_number_icon = IconService.get_icon('view-state-number')
        state_no_menu = view_menu.addMenu(state_number_icon, "State No.")
        self.state_on_off_action = QAction("State On/Off", self.main_window)
        self.state_on_off_action.setCheckable(True)
        self.state_on_off_action.setChecked(True)
        state_no_menu.addAction(self.state_on_off_action)
        self.next_state_action = QAction(IconService.get_icon('view-next-state'), "Next State", self.main_window)
        state_no_menu.addAction(self.next_state_action)
        self.prev_state_action = QAction(IconService.get_icon('view-prev-state'), "Previous State", self.main_window)
        state_no_menu.addAction(self.prev_state_action)

        # Tool Bar Submenu
        tool_bar_icon = IconService.get_icon('view-tool-bar')
        self.tool_bar_menu = view_menu.addMenu(tool_bar_icon, "Tool Bar")
        toolbar_items = [
            ("Window Display", IconService.get_icon('view-window-display')),
            ("View", IconService.get_icon('view-view')),
            ("Screen", IconService.get_icon('view-screen')),
            ("Edit", IconService.get_icon('view-edit')),
            ("Alignment", IconService.get_icon('view-alignment')),
            ("Figure", IconService.get_icon('view-figure')),
            ("Object", IconService.get_icon('view-object')),
            ("Debug", IconService.get_icon('view-debug')),
        ]
        self._create_checkable_actions(self.tool_bar_menu, toolbar_items)


        # Docking Window Submenu
        docking_window_icon = IconService.get_icon('view-docking-window')
        self.docking_window_menu = view_menu.addMenu(docking_window_icon, "Docking Window")
        docking_items = [
            ("Project Tree", IconService.get_icon('dock-project-tree')),
            ("Screen Tree", IconService.get_icon('dock-screen-tree')),
            ("System Tree", IconService.get_icon('dock-system-tree')),
            ("Tag Search", IconService.get_icon('dock-tag-search')),
            ("Data Browser", IconService.get_icon('dock-data-browser')),
            ("Property Tree", IconService.get_icon('dock-property-tree')),
            ("IP Address", IconService.get_icon('dock-ip-address')),
            ("Library", IconService.get_icon('dock-library')),
            ("Controller List", IconService.get_icon('dock-controller-list')),
            ("Data View", IconService.get_icon('dock-data-view')),
            ("Screen Image List", IconService.get_icon('dock-screen-image-list')),
        ]
        self._create_checkable_actions(self.docking_window_menu, docking_items)


        # Display Item Submenu
        display_item_icon = IconService.get_icon('view-display-item')
        display_item_menu = view_menu.addMenu(display_item_icon, "Display Item")
        self.tag_action = QAction(IconService.get_icon('view-tag'), "Tag", self.main_window)
        self.tag_action.setCheckable(True)
        display_item_menu.addAction(self.tag_action)
        self.object_id_action = QAction(IconService.get_icon('view-object-id'), "Object ID", self.main_window)
        self.object_id_action.setCheckable(True)
        display_item_menu.addAction(self.object_id_action)
        self.transform_line_action = QAction(IconService.get_icon('view-transform-line'), "Transform Line", self.main_window)
        self.transform_line_action.setCheckable(True)
        display_item_menu.addAction(self.transform_line_action)
        self.click_area_action = QAction(IconService.get_icon('view-click-area'), "Click Area", self.main_window)
        self.click_area_action.setCheckable(True)
        display_item_menu.addAction(self.click_area_action)
        
        # Object Snap Action
        object_snap_icon = IconService.get_icon('view-object-snap')
        object_snap_widget_action = QWidgetAction(self.main_window)
        object_snap_widget = QWidget()
        object_snap_layout = QHBoxLayout(object_snap_widget)
        object_snap_layout.setContentsMargins(4, 4, 4, 4)
        object_snap_layout.setSpacing(10)

        object_snap_icon_label = QLabel()
        object_snap_icon_label.setPixmap(object_snap_icon.pixmap(16, 16))
        object_snap_text_label = QLabel("Object Snap")
        self.object_snap_checkbox = QCheckBox()
        self.object_snap_checkbox.setChecked(True)

        object_snap_layout.addWidget(object_snap_icon_label)
        object_snap_layout.addWidget(object_snap_text_label)
        object_snap_layout.addStretch()
        object_snap_layout.addWidget(self.object_snap_checkbox)

        object_snap_widget_action.setDefaultWidget(object_snap_widget)
        view_menu.addAction(object_snap_widget_action)

        # Zoom Submenu
        zoom_icon = IconService.get_icon('view-zoom')
        self.zoom_menu = view_menu.addMenu(zoom_icon, "Zoom")
        self.fit_screen_action = QAction(IconService.get_icon('view-fit-screen'), "Fit Screen", self.main_window)
        self.zoom_menu.addAction(self.fit_screen_action)
        self.zoom_menu.addSeparator()
        
        self.zoom_action_group = QActionGroup(self.main_window)
        self.zoom_action_group.setExclusive(True)
        
        zoom_levels = ["20%", "50%", "75%", "100%", "125%", "150%", "200%", "250%", "300%", "400%", "500%", "600%", "700%", "800%", "900%", "1000%"]
        self.zoom_actions = []
        for level in zoom_levels:
            action = QAction(level, self.main_window)
            action.setCheckable(True)
            if level == "100%":
                action.setChecked(True)
            self.zoom_menu.addAction(action)
            self.zoom_action_group.addAction(action)
            self.zoom_actions.append(action)

    def _create_checkable_actions(self, menu, items):
        """
        Generic helper function to create and add checkable widget actions to a menu.
        
        Args:
            menu (QMenu): The parent menu to which actions will be added.
            items (list of tuples): A list where each tuple contains (text, icon).
        """
        for text, icon in items:
            widget_action = QWidgetAction(self.main_window)
            widget_action.setText(text)
            
            widget = QWidget()
            layout = QHBoxLayout(widget)
            layout.setContentsMargins(4, 4, 4, 4)
            layout.setSpacing(10)

            check_box = QCheckBox()
            check_box.setChecked(True)
            
            icon_label = QLabel()
            if icon:
                icon_label.setPixmap(icon.pixmap(16, 16))
            
            text_label = QLabel(text)

            layout.addWidget(check_box)
            layout.addWidget(icon_label)
            layout.addWidget(text_label)
            layout.addStretch()

            widget_action.setDefaultWidget(widget)
            menu.addAction(widget_action)
