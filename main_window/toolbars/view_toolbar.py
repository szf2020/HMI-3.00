# main_window\toolbars\view_toolbar.py
from PySide6.QtWidgets import QToolBar, QComboBox, QToolButton, QCheckBox, QSpinBox
from PySide6.QtCore import Qt
from ..services.icon_service import IconService

class ViewToolbar(QToolBar):
    def __init__(self, main_window, view_menu, view_service):
        super().__init__("View", main_window)
        self.main_window = main_window
        self.view_menu = view_menu
        self.view_service = view_service
        self.setMovable(True)
        self.current_state = 0
        self.max_states = 64

        # --- Snap Controls ---
        self.snap_combo = QComboBox()
        self.snap_combo.setFixedWidth(70)
        self.snap_combo.addItems(["1", "2", "4", "8", "16", "32"])
        self.snap_combo.setCurrentText(str(self.view_service.grid_size))
        # Use a lambda to capture the text and convert to int for the service
        self.snap_combo.currentTextChanged.connect(
            lambda text: setattr(self.view_service, 'grid_size', int(text))
        )
        # Connect service changes back to the UI
        self.view_service.grid_size_changed.connect(
            lambda size: self.snap_combo.setCurrentText(str(size))
        )
        self.addWidget(self.snap_combo)

        self.object_snap_checkbox = QCheckBox("Object Snap")
        self.object_snap_checkbox.setChecked(self.view_service.snap_enabled)
        # UI controls update the service
        self.object_snap_checkbox.toggled.connect(
            lambda checked: setattr(self.view_service, 'snap_enabled', checked)
        )
        self.view_menu.object_snap_checkbox.toggled.connect(
            lambda checked: setattr(self.view_service, 'snap_enabled', checked)
        )
        # Service signals update the UI to keep them in sync
        self.view_service.snap_changed.connect(self.object_snap_checkbox.setChecked)
        self.view_service.snap_changed.connect(self.view_menu.object_snap_checkbox.setChecked)

        self.addWidget(self.object_snap_checkbox)
        self.addSeparator()

        # Select Mode Action
        self.addAction(view_menu.select_mode_action)
        self.addSeparator()

        # Zoom Controls
        zoom_in_icon = IconService.get_icon('zoom-in')
        zoom_out_icon = IconService.get_icon('zoom-out')
        
        self.zoom_out_button = QToolButton()
        self.zoom_out_button.setIcon(zoom_out_icon)
        self.addWidget(self.zoom_out_button)

        self.zoom_combo = QComboBox()
        self.zoom_combo.setEditable(True)
        self.zoom_combo.setFixedWidth(100)
        for action in self.view_menu.zoom_actions:
            self.zoom_combo.addItem(action.text())
        self.zoom_combo.setCurrentText("100%")
        self.addWidget(self.zoom_combo)

        self.zoom_in_button = QToolButton()
        self.zoom_in_button.setIcon(zoom_in_icon)
        self.addWidget(self.zoom_in_button)

        self.addAction(self.view_menu.fit_screen_action)
        self.addSeparator()

        # --- State Controls ---
        self.state_toggle_button = QToolButton()
        self.state_toggle_button.setCheckable(True)
        self.state_toggle_button.clicked.connect(self.toggle_state)
        self.addWidget(self.state_toggle_button)
        
        self.state_spin_box = QSpinBox()
        self.state_spin_box.setRange(0, self.max_states - 1)
        self.state_spin_box.setFixedWidth(50)
        self.state_spin_box.valueChanged.connect(self.set_state_from_spinbox)
        self.addWidget(self.state_spin_box)
        
        self.addSeparator()

        # Display Item Toggles
        self.addAction(self.view_menu.tag_action)
        self.addAction(self.view_menu.object_id_action)
        self.addAction(self.view_menu.transform_line_action)
        self.addAction(self.view_menu.click_area_action)
        
        # Connect menu actions to toolbar methods
        self.view_menu.state_on_off_action.triggered.connect(self.toggle_state)
        self.view_menu.next_state_action.triggered.connect(self.next_state)
        self.view_menu.prev_state_action.triggered.connect(self.prev_state)
        
        # Set initial UI state
        self.update_state_ui()

    def update_state_ui(self):
        """Updates all state-related UI elements to reflect the current state."""
        # Block signals on the spin box to prevent recursive calls when we set its value
        self.state_spin_box.blockSignals(True)
        self.state_spin_box.setValue(self.current_state)
        self.state_spin_box.blockSignals(False)

        # Update the toggle button and menu item based on the current state
        if self.current_state == 0:
            self.state_toggle_button.setText("OFF")
            self.state_toggle_button.setProperty("state", "off")
            self.state_toggle_button.setChecked(False)
            self.view_menu.state_on_off_action.setChecked(False)
        elif self.current_state == 1:
            self.state_toggle_button.setText("ON")
            self.state_toggle_button.setProperty("state", "on")
            self.state_toggle_button.setChecked(True)
            self.view_menu.state_on_off_action.setChecked(True)
        else:
            self.state_toggle_button.setText("OFF")
            self.state_toggle_button.setProperty("state", "off") # Or a neutral state
            self.state_toggle_button.setChecked(False)
            self.view_menu.state_on_off_action.setChecked(False)
        
        # Re-polish the widget to apply the new style
        self.style().unpolish(self.state_toggle_button)
        self.style().polish(self.state_toggle_button)


    def toggle_state(self):
        """Toggles the state between 0 (OFF) and 1 (ON)."""
        if self.current_state == 1:
            self.current_state = 0
        else:
            self.current_state = 1
        self.update_state_ui()

    def next_state(self):
        """Moves to the next state, wrapping around if necessary."""
        self.current_state = (self.current_state + 1) % self.max_states
        self.update_state_ui()

    def prev_state(self):
        """Moves to the previous state, wrapping around if necessary."""
        self.current_state = (self.current_state - 1 + self.max_states) % self.max_states
        self.update_state_ui()

    def set_state_from_spinbox(self, value):
        """Sets the state from the spin box value."""
        if 0 <= value < self.max_states:
            self.current_state = value
            self.update_state_ui()

