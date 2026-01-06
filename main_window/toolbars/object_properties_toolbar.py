# main_window\toolbars\object_properties_toolbar.py
"""
Object Properties Toolbar
=========================
A floating toolbar for displaying and editing selected object's 
position, size, and rotation angle with live updates.
Supports undo/redo for all property changes.
"""

from PySide6.QtWidgets import (
    QToolBar, QWidget, QHBoxLayout, QLabel, QDoubleSpinBox, 
    QCheckBox, QFrame
)
from PySide6.QtCore import Qt, Signal, QSize, QPointF, QRectF
from ..services.icon_service import IconService
from screen.base.canvas_base_screen import CanvasBaseScreen
from screen.base.base_graphic_object import BaseGraphicObject
from services.undo_commands import TransformItemsCommand, MoveItemsCommand
from styles import stylesheets


class ObjectPropertiesToolbar(QToolBar):
    """
    Toolbar for displaying and editing selected object properties.
    Shows X, Y position, Width, Height, and Angle.
    All values are editable and provide live updates to the canvas.
    Supports undo/redo for all changes.
    """
    
    # Signals emitted when user edits values
    position_edited = Signal(float, float)  # x, y
    size_edited = Signal(float, float)  # width, height
    angle_edited = Signal(float)  # angle
    
    def __init__(self, main_window):
        super().__init__("Object Properties", main_window)
        self.main_window = main_window
        self._syncing = False  # Prevent feedback loops during sync
        self._last_width = 100
        self._last_height = 100
        
        # Track initial state for undo
        self._editing_item = None
        self._edit_initial_state = None
        
        self._setup_ui()
        
        # Apply consistent styling
        self.setStyleSheet(stylesheets.get_object_properties_toolbar_stylesheet())
        
    def _setup_ui(self):
        """Setup the toolbar UI components."""
        # Icon size consistent with other toolbars (24x24)
        icon_size = QSize(24, 24)
        
        # Position Section
        pos_widget = QWidget()
        pos_layout = QHBoxLayout(pos_widget)
        pos_layout.setContentsMargins(4, 0, 4, 0)
        pos_layout.setSpacing(4)
        
        # X Position
        x_icon = QLabel()
        x_icon.setPixmap(IconService.get_icon('object-pos').pixmap(icon_size))
        pos_layout.addWidget(x_icon)
        
        x_label = QLabel("X:")
        x_label.setStyleSheet("font-weight: bold;")
        pos_layout.addWidget(x_label)
        
        self.x_spin = QDoubleSpinBox()
        self.x_spin.setRange(-99999.0, 99999.0)
        self.x_spin.setValue(0)
        self.x_spin.setDecimals(0)
        self.x_spin.setFixedWidth(75)
        self.x_spin.setToolTip("X Position (Left)")
        self.x_spin.valueChanged.connect(self._on_position_changed)
        pos_layout.addWidget(self.x_spin)
        
        # Y Position
        y_label = QLabel("Y:")
        y_label.setStyleSheet("font-weight: bold;")
        pos_layout.addWidget(y_label)
        
        self.y_spin = QDoubleSpinBox()
        self.y_spin.setRange(-99999.0, 99999.0)
        self.y_spin.setValue(0)
        self.y_spin.setDecimals(0)
        self.y_spin.setFixedWidth(75)
        self.y_spin.setToolTip("Y Position (Top)")
        self.y_spin.valueChanged.connect(self._on_position_changed)
        pos_layout.addWidget(self.y_spin)
        
        self.addWidget(pos_widget)
        self._add_separator()
        
        # Size Section
        size_widget = QWidget()
        size_layout = QHBoxLayout(size_widget)
        size_layout.setContentsMargins(4, 0, 4, 0)
        size_layout.setSpacing(4)
        
        # Width
        w_icon = QLabel()
        w_icon.setPixmap(IconService.get_icon('object-size').pixmap(icon_size))
        size_layout.addWidget(w_icon)
        
        w_label = QLabel("W:")
        w_label.setStyleSheet("font-weight: bold;")
        size_layout.addWidget(w_label)
        
        self.width_spin = QDoubleSpinBox()
        self.width_spin.setRange(1, 99999.0)
        self.width_spin.setValue(100)
        self.width_spin.setDecimals(0)
        self.width_spin.setFixedWidth(75)
        self.width_spin.setToolTip("Width")
        self.width_spin.valueChanged.connect(self._on_size_changed)
        size_layout.addWidget(self.width_spin)
        
        # Height
        h_label = QLabel("H:")
        h_label.setStyleSheet("font-weight: bold;")
        size_layout.addWidget(h_label)
        
        self.height_spin = QDoubleSpinBox()
        self.height_spin.setRange(1, 99999.0)
        self.height_spin.setValue(100)
        self.height_spin.setDecimals(0)
        self.height_spin.setFixedWidth(75)
        self.height_spin.setToolTip("Height")
        self.height_spin.valueChanged.connect(self._on_size_changed)
        size_layout.addWidget(self.height_spin)
        
        # Lock Aspect Ratio
        self.lock_aspect = QCheckBox()
        self.lock_aspect.setToolTip("Lock Aspect Ratio")
        self.lock_aspect.setIcon(IconService.get_icon('lock'))
        self.lock_aspect.setIconSize(icon_size)
        size_layout.addWidget(self.lock_aspect)
        
        self.addWidget(size_widget)
        self._add_separator()
        
        # Angle Section
        angle_widget = QWidget()
        angle_layout = QHBoxLayout(angle_widget)
        angle_layout.setContentsMargins(4, 0, 4, 0)
        angle_layout.setSpacing(4)
        
        angle_icon = QLabel()
        angle_icon.setPixmap(IconService.get_icon('rotate-right').pixmap(icon_size))
        angle_layout.addWidget(angle_icon)
        
        angle_label = QLabel("∠:")
        angle_label.setStyleSheet("font-weight: bold;")
        angle_layout.addWidget(angle_label)
        
        self.angle_spin = QDoubleSpinBox()
        self.angle_spin.setRange(-360.0, 360.0)
        self.angle_spin.setValue(0)
        self.angle_spin.setSuffix("°")
        self.angle_spin.setDecimals(1)
        self.angle_spin.setFixedWidth(75)
        self.angle_spin.setToolTip("Rotation Angle")
        self.angle_spin.valueChanged.connect(self._on_angle_changed)
        angle_layout.addWidget(self.angle_spin)
        
        self.addWidget(angle_widget)
        
        # Initially disable all inputs (no selection)
        self._set_enabled(False)
        
    def _add_separator(self):
        """Add a visual separator."""
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.VLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        self.addWidget(separator)
        
    def _set_enabled(self, enabled):
        """Enable or disable all input widgets."""
        self.x_spin.setEnabled(enabled)
        self.y_spin.setEnabled(enabled)
        self.width_spin.setEnabled(enabled)
        self.height_spin.setEnabled(enabled)
        self.angle_spin.setEnabled(enabled)
        self.lock_aspect.setEnabled(enabled)
        
    def _on_position_changed(self, value):
        """Handle position spinbox changes."""
        if self._syncing:
            return
        
        x = self.x_spin.value()
        y = self.y_spin.value()
        
        # Apply to active canvas selection
        self._apply_position_to_selection(x, y)
        self.position_edited.emit(x, y)
        
    def _on_size_changed(self, value):
        """Handle size spinbox changes with aspect ratio lock support."""
        if self._syncing:
            return
        
        width = self.width_spin.value()
        height = self.height_spin.value()
        
        # Handle aspect ratio lock
        if self.lock_aspect.isChecked():
            sender = self.sender()
            if sender == self.width_spin and self._last_width > 0:
                ratio = self._last_height / self._last_width
                self._syncing = True
                self.height_spin.setValue(width * ratio)
                self._syncing = False
                height = self.height_spin.value()
            elif sender == self.height_spin and self._last_height > 0:
                ratio = self._last_width / self._last_height
                self._syncing = True
                self.width_spin.setValue(height * ratio)
                self._syncing = False
                width = self.width_spin.value()
        
        self._last_width = width
        self._last_height = height
        
        # Apply to active canvas selection
        self._apply_size_to_selection(width, height)
        self.size_edited.emit(width, height)
        
    def _on_angle_changed(self, value):
        """Handle angle spinbox changes."""
        if self._syncing:
            return
        
        # Apply to active canvas selection
        self._apply_angle_to_selection(value)
        self.angle_edited.emit(value)
    
    def _capture_item_state(self, item):
        """Capture current state of an item for undo."""
        state = {
            'pos': QPointF(item.pos()),
            'rect': QRectF(item.boundingRect()),
            'rotation': item.rotation(),
            'transform_origin': QPointF(item.transformOriginPoint())
        }
        if hasattr(item, 'corner_radii'):
            state['corner_radii'] = item.corner_radii.copy()
        return state
        
    def _apply_position_to_selection(self, x, y):
        """Apply position changes to the selected object(s) with undo support."""
        active_screen = self.main_window.get_active_screen_widget()
        if not isinstance(active_screen, CanvasBaseScreen):
            return
        
        selected_items = active_screen.scene.selectedItems()
        valid_items = [item for item in selected_items if isinstance(item, BaseGraphicObject)]
        
        if len(valid_items) == 1:
            item = valid_items[0]
            
            # Capture old state
            old_pos = QPointF(item.pos())
            new_pos = QPointF(x, y)
            
            # Only push command if position actually changed
            if old_pos != new_pos:
                # Use MoveItemsCommand for position changes
                command = MoveItemsCommand([item], [old_pos], [new_pos], "Move Item")
                active_screen.undo_stack.push(command)
            
            active_screen.scene.update()
            active_screen.save_items()
            # Update transform handler if exists
            if active_screen.transform_handler:
                active_screen.transform_handler.update_geometry()
                
    def _apply_size_to_selection(self, width, height):
        """Apply size changes to the selected object(s) with undo support."""
        active_screen = self.main_window.get_active_screen_widget()
        if not isinstance(active_screen, CanvasBaseScreen):
            return
        
        selected_items = active_screen.scene.selectedItems()
        valid_items = [item for item in selected_items if isinstance(item, BaseGraphicObject)]
        
        if len(valid_items) == 1:
            item = valid_items[0]
            
            # Capture old state
            old_state = self._capture_item_state(item)
            
            # Apply the size change
            current_rect = item.boundingRect()
            new_rect = QRectF(current_rect.x(), current_rect.y(), width, height)
            item.set_geometry(new_rect)
            
            # Capture new state
            new_state = self._capture_item_state(item)
            
            # Only push command if state actually changed
            if old_state != new_state:
                command = TransformItemsCommand([item], [old_state], [new_state], "Resize Item")
                active_screen.undo_stack.push(command)
            
            active_screen.scene.update()
            active_screen.save_items()
            # Update transform handler if exists
            if active_screen.transform_handler:
                active_screen.transform_handler.update_geometry()
                
    def _apply_angle_to_selection(self, angle):
        """Apply rotation angle to the selected object(s) with undo support."""
        active_screen = self.main_window.get_active_screen_widget()
        if not isinstance(active_screen, CanvasBaseScreen):
            return
        
        selected_items = active_screen.scene.selectedItems()
        valid_items = [item for item in selected_items if isinstance(item, BaseGraphicObject)]
        
        if len(valid_items) == 1:
            item = valid_items[0]
            
            # Capture old state
            old_state = self._capture_item_state(item)
            
            # Apply the rotation
            rect = item.boundingRect()
            center = rect.center()
            item.setTransformOriginPoint(center)
            item.setRotation(angle)
            
            # Capture new state
            new_state = self._capture_item_state(item)
            
            # Only push command if state actually changed
            if old_state != new_state:
                command = TransformItemsCommand([item], [old_state], [new_state], "Rotate Item")
                active_screen.undo_stack.push(command)
            
            active_screen.scene.update()
            active_screen.save_items()
            # Update transform handler if exists
            if active_screen.transform_handler:
                active_screen.transform_handler.update_geometry()
    
    def sync_from_selection(self, selected_items, deselected_items=None):
        """
        Sync toolbar values from selected canvas items.
        Called when canvas selection changes.
        """
        valid_items = [item for item in selected_items if isinstance(item, BaseGraphicObject)]
        
        if len(valid_items) == 0:
            # No selection - disable and reset
            self._syncing = True
            self.x_spin.setValue(0)
            self.y_spin.setValue(0)
            self.width_spin.setValue(100)
            self.height_spin.setValue(100)
            self.angle_spin.setValue(0)
            self._syncing = False
            self._set_enabled(False)
            return
        
        if len(valid_items) == 1:
            # Single selection - show and enable all properties
            item = valid_items[0]
            self._syncing = True
            
            # Position
            pos = item.pos()
            self.x_spin.setValue(pos.x())
            self.y_spin.setValue(pos.y())
            
            # Size
            rect = item.boundingRect()
            width = rect.width()
            height = rect.height()
            self.width_spin.setValue(width)
            self.height_spin.setValue(height)
            self._last_width = width
            self._last_height = height
            
            # Angle
            self.angle_spin.setValue(item.rotation())
            
            self._syncing = False
            self._set_enabled(True)
        else:
            # Multiple selection - show bounding box info, limited editing
            self._syncing = True
            
            # Calculate combined bounding rect
            min_x = min(item.pos().x() for item in valid_items)
            min_y = min(item.pos().y() for item in valid_items)
            max_x = max(item.pos().x() + item.boundingRect().width() for item in valid_items)
            max_y = max(item.pos().y() + item.boundingRect().height() for item in valid_items)
            
            self.x_spin.setValue(min_x)
            self.y_spin.setValue(min_y)
            self.width_spin.setValue(max_x - min_x)
            self.height_spin.setValue(max_y - min_y)
            self.angle_spin.setValue(0)  # Mixed angles - show 0
            
            self._syncing = False
            
            # Enable position for group move, disable size/angle for multiple
            self.x_spin.setEnabled(True)
            self.y_spin.setEnabled(True)
            self.width_spin.setEnabled(False)
            self.height_spin.setEnabled(False)
            self.angle_spin.setEnabled(False)
            self.lock_aspect.setEnabled(False)
    
    def update_from_canvas(self):
        """
        Update toolbar values from current canvas selection.
        Called during object manipulation (drag, resize, etc.)
        """
        active_screen = self.main_window.get_active_screen_widget()
        if not isinstance(active_screen, CanvasBaseScreen):
            return
        
        selected_items = active_screen.scene.selectedItems()
        self.sync_from_selection(selected_items)
    
    def on_object_data_changed(self, data):
        """
        Handle live updates during object manipulation (resize, move, rotate).
        Called when object_data_changed signal is emitted.
        
        Args:
            data: Dict with 'position' (x, y), 'size' (w, h), and 'rotation' (angle) or None values
        """
        if self._syncing:
            return
        
        self._syncing = True
        
        position = data.get('position')
        size = data.get('size')
        rotation = data.get('rotation')
        
        if position is not None:
            x, y = position
            self.x_spin.setValue(x)
            self.y_spin.setValue(y)
        
        if size is not None:
            w, h = size
            self.width_spin.setValue(w)
            self.height_spin.setValue(h)
            self._last_width = w
            self._last_height = h
        
        if rotation is not None:
            self.angle_spin.setValue(rotation)
        
        self._syncing = False
