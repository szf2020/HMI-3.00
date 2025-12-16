# main_window\docking_windows\layers_dock.py
"""
Photoshop-style Layers docking window for HMI Designer.
Features include:
- Show/Hide layers
- Lock/Unlock layers
- Drag and drop layers
- Group/Ungroup layers
- Rename layers
- Delete layers
- Layer opacity control
- Layer blending modes
- Search/Filter layers
"""

from PySide6.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QMenu, QMessageBox, QLineEdit, QLabel, QSlider, QComboBox, QSpinBox,
    QHeaderView, QAbstractItemView, QStyleOptionViewItem
)
from PySide6.QtCore import (
    Qt, Signal, QTimer, QMimeData, QByteArray, QDataStream, QIODevice, QSize, QRect
)
from PySide6.QtGui import (
    QIcon, QPixmap, QDrag, QPalette, QColor, QFont, QKeySequence, QCursor
)
from PySide6.QtSvg import QSvgRenderer
from pathlib import Path
from ..services.icon_service import IconService
from ..widgets.tree import CustomTreeWidget
from styles import stylesheets
import uuid
import json
from debug_utils import get_logger

logger = get_logger(__name__)


class LayerItem:
    """Represents a layer in the hierarchy."""
    
    def __init__(self, name, layer_id=None, is_group=False, parent=None):
        self.name = name
        self.layer_id = layer_id or str(uuid.uuid4())
        self.is_group = is_group
        self.parent = parent
        self.children = []
        self.visible = True
        self.locked = False
        self.opacity = 100
        self.graphics_item = None  # Reference to QGraphicsItem
        
    def add_child(self, item):
        """Add a child layer."""
        item.parent = self
        self.children.append(item)
        
    def remove_child(self, item):
        """Remove a child layer."""
        if item in self.children:
            self.children.remove(item)
            item.parent = None
            
    def to_dict(self):
        """Convert layer to dictionary for serialization."""
        return {
            'name': self.name,
            'layer_id': self.layer_id,
            'is_group': self.is_group,
            'visible': self.visible,
            'locked': self.locked,
            'opacity': self.opacity,
            'children': [child.to_dict() for child in self.children]
        }
    
    @staticmethod
    def from_dict(data, parent=None):
        """Create layer from dictionary."""
        item = LayerItem(data['name'], data['layer_id'], data['is_group'], parent)
        item.visible = data.get('visible', True)
        item.locked = data.get('locked', False)
        item.opacity = data.get('opacity', 100)
        for child_data in data.get('children', []):
            item.add_child(LayerItem.from_dict(child_data, item))
        return item


class LayerTreeWidget(CustomTreeWidget):
    """Custom tree widget for layers with drag-drop support."""
    
    layers_changed = Signal()
    layer_visibility_changed = Signal(str, bool)  # layer_id, visible
    layer_locked_changed = Signal(str, bool)  # layer_id, locked
    layer_opacity_changed = Signal(str, int)  # layer_id, opacity
    layer_selected = Signal(str)  # layer_id
    layer_renamed = Signal(str, str)  # layer_id, new_name
    layer_deleted = Signal(str)  # layer_id
    layers_reordered = Signal()
    layer_moved_to_group = Signal(str, str)  # layer_id, group_id
    layer_moved_out_group = Signal(str)  # layer_id
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setIndentation(24)  # Increased from 12 for better spacing
        self.setColumnCount(3)
        self.setHeaderLabels(['Layer', 'Vis', 'Lock'])
        
        # Hide header
        self.header().hide()
        
        header = self.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        
        self.setUniformRowHeights(True)
        self._user_selection_active = False
        self._dragged_layer = None  # Track dragged layer for custom drop handling
        
        # Apply enhanced stylesheet for layers tree
        self._apply_layers_stylesheet()
        
        self.itemSelectionChanged.connect(self._on_item_selection_changed)
        self.itemChanged.connect(self._on_item_changed)
    
    def _apply_layers_stylesheet(self):
        """Apply enhanced stylesheet for layers tree with larger icons and spacing."""
        from styles import stylesheets
        from pathlib import Path
        
        # Get icon paths
        icon_path = Path(__file__).parent.parent / 'resources' / 'icons'
        expand_icon = str(icon_path / 'icon-park-solid-add.svg').replace('\\', '/')
        collapse_icon = str(icon_path / 'icon-park-solid-subtract.svg').replace('\\', '/')
        
        # Get stylesheet from centralized styles module
        stylesheet = stylesheets.get_layers_tree_stylesheet(expand_icon, collapse_icon)
        self.setStyleSheet(stylesheet)
    
    def _on_item_selection_changed(self):
        """Emit signal when layer is selected."""
        if not self._consume_user_selection():
            return

        selected_items = self.selectedItems()
        if selected_items:
            layer_item = self._layer_from_tree_item(selected_items[0])
            if layer_item:
                self.layer_selected.emit(layer_item.layer_id)
    
    def _on_item_changed(self, tree_item, column):
        """Handle when tree item is edited (renamed)."""
        if column == 0:  # Name column
            layer_item = self._layer_from_tree_item(tree_item)
            if layer_item:
                new_name = tree_item.text(0)
                self.layer_renamed.emit(layer_item.layer_id, new_name)
    
    def dropEvent(self, event):
        """Handle drop event for reordering layers."""
        # Get the dragged items
        dragged_items = self.selectedItems()
        if not dragged_items:
            super().dropEvent(event)
            return
        
        dragged_layer = self._layer_from_tree_item(dragged_items[0])
        if not dragged_layer:
            super().dropEvent(event)
            return
        
        # Get drop target item
        drop_item = self.itemAt(event.pos())
        drop_handled = False
        
        if drop_item:
            drop_layer = self._layer_from_tree_item(drop_item)
            
            # Case 1: Dropping on a group - move layer into group
            if drop_layer and drop_layer.is_group and dragged_layer != drop_layer:
                self._move_layer_to_group(dragged_layer, drop_layer)
                drop_handled = True
            
            # Case 2: Dropping on a regular layer - reorder within same parent
            elif drop_layer and drop_layer.parent and dragged_layer != drop_layer:
                # Check if we're moving a layer out of a group
                if dragged_layer.parent != drop_layer.parent:
                    # Check if drop target is child of dragged layer (moving out)
                    if self._is_ancestor(dragged_layer, drop_layer):
                        # Moving out of group
                        self._move_layer_out_of_group(dragged_layer, drop_layer.parent)
                    else:
                        # Regular reorder
                        self._reorder_layer_in_parent(dragged_layer, drop_layer)
                else:
                    # Same parent, just reorder
                    self._reorder_layer_in_parent(dragged_layer, drop_layer)
                
                drop_handled = True
        
        if drop_handled:
            # Rebuild tree to reflect changes
            if hasattr(self, 'layers_dock') and self.layers_dock:
                self.layers_dock._rebuild_tree()
            event.accept()
        else:
            # Default behavior for root level
            super().dropEvent(event)
        
        self.layers_reordered.emit()
    
    def _is_ancestor(self, potential_ancestor, item):
        """Check if potential_ancestor is an ancestor of item."""
        current = item.parent
        while current:
            if current == potential_ancestor:
                return True
            current = current.parent
        return False
        
    def _move_layer_to_group(self, layer, group):
        """Move a layer into a group."""
        if layer.parent:
            layer.parent.remove_child(layer)
        group.add_child(layer)
        self.layer_moved_to_group.emit(layer.layer_id, group.layer_id)
    
    def _move_layer_out_of_group(self, layer, target_parent):
        """Move a layer out of its group to a target parent."""
        old_parent = layer.parent
        
        if old_parent:
            old_parent.remove_child(layer)
        
        # Add to target parent
        if target_parent:
            target_parent.add_child(layer)
        
        self.layer_moved_out_group.emit(layer.layer_id)
        
        # Check if old parent group is now empty and remove it if so
        if old_parent and old_parent.is_group and len(old_parent.children) == 0:
            grandparent = old_parent.parent or self.root_layer
            if old_parent in grandparent.children:
                grandparent.remove_child(old_parent)
            
            if old_parent.layer_id in self.layer_map:
                del self.layer_map[old_parent.layer_id]
    
    def _reorder_layer_in_parent(self, layer, target_layer):
        """Reorder a layer within the same parent."""
        parent = target_layer.parent or layer.parent
        if not parent:
            return
        
        # Remove from current position
        if layer.parent:
            layer.parent.remove_child(layer)
        
        # Find target position in parent's children
        target_index = parent.children.index(target_layer)
        parent.children.insert(target_index, layer)
        layer.parent = parent
        
    def dragEnterEvent(self, event):
        """Handle drag enter event."""
        if event.mimeData().hasFormat("application/x-layer"):
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)
            
    def dragMoveEvent(self, event):
        """Handle drag move event - show drop indicators."""
        if event.mimeData().hasFormat("application/x-layer"):
            item = self.itemAt(event.pos())
            if item:
                drop_layer = self._layer_from_tree_item(item)
                # Highlight group targets in different color
                if drop_layer and drop_layer.is_group:
                    event.acceptProposedAction()
                    return
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def _layer_from_tree_item(self, tree_item) -> LayerItem | None:
        """Return the layer object mapped to a tree item (if available)."""
        if tree_item is None:
            return None
        layer_id = tree_item.data(0, Qt.ItemDataRole.UserRole)
        if not layer_id:
            return None
        return self.layer_map.get(layer_id)

    def mousePressEvent(self, event):
        """Track mouse-initiated selection so we can gate hover selection."""
        self._mark_user_selection()
        super().mousePressEvent(event)
        QTimer.singleShot(0, self._clear_user_selection_if_stale)

    def keyPressEvent(self, event):
        """Mind keyboard navigation as a deliberate selection trigger."""
        self._mark_user_selection()
        super().keyPressEvent(event)
        QTimer.singleShot(0, self._clear_user_selection_if_stale)

    def _mark_user_selection(self):
        """Indicate the next selection change should be treated as user-driven."""
        self._user_selection_active = True

    def _clear_user_selection_if_stale(self):
        """If a selection change never fired, reset the user flag."""
        if self._user_selection_active:
            self._user_selection_active = False

    def _consume_user_selection(self) -> bool:
        """Return True once when a user selection arrives."""
        if not self._user_selection_active:
            return False
        self._user_selection_active = False
        return True
    
    def _rebuild_tree_from_root(self):
        """Rebuild tree widget from layer_map - called after drop operations."""
        # This method will be called by LayersDock after tree modifications
        pass


class LayersDock(QDockWidget):
    """
    Photoshop-style layers docking window.
    Manages layers with full hierarchy support.
    """
    
    def __init__(self, main_window):
        super().__init__("Layers", main_window)
        self.main_window = main_window
        self.setObjectName("layers_dock")
        
        # Layer storage
        self.root_layer = LayerItem("Root", "root", True)
        self.layer_map = {}  # Map of layer_id to LayerItem
        self.graphics_items_map = {}  # Map of QGraphicsItem to LayerItem
        
        # Create main widget
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_widget.setLayout(main_layout)
        
        # Top bar with opacity slider and action buttons
        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(4, 4, 4, 4)
        
        opacity_label = QLabel("Opacity:")
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setMinimum(0)
        self.opacity_slider.setMaximum(100)
        self.opacity_slider.setValue(100)
        self.opacity_slider.setMaximumWidth(80)
        self.opacity_value = QSpinBox()
        self.opacity_value.setMinimum(0)
        self.opacity_value.setMaximum(100)
        self.opacity_value.setValue(100)
        self.opacity_value.setMaximumWidth(40)
        
        self.opacity_slider.valueChanged.connect(self._on_opacity_slider_changed)
        self.opacity_value.valueChanged.connect(self._on_opacity_value_changed)
        
        top_layout.addWidget(opacity_label)
        top_layout.addWidget(self.opacity_slider)
        top_layout.addWidget(self.opacity_value)
        top_layout.addStretch()
        
        # Delete and Duplicate buttons on the right (icon only)
        self.delete_btn = self._create_icon_button("🗑", "Delete", self._delete_layer)
        self.duplicate_btn = self._create_icon_button("📋", "Duplicate", self._duplicate_layer)
        
        top_layout.addWidget(self.delete_btn)
        top_layout.addWidget(self.duplicate_btn)
        main_layout.addLayout(top_layout)
        
        # Layers tree widget
        self.tree_widget = LayerTreeWidget()
        self.tree_widget.layer_map = self.layer_map
        self.tree_widget.layers_dock = self  # Reference back to LayersDock for callbacks
        main_layout.addWidget(self.tree_widget)
        
        self.setWidget(main_widget)
        
        # Connect signals
        self._setup_signals()
        
    def _create_button(self, text, callback):
        """Helper to create styled button."""
        from PySide6.QtWidgets import QPushButton
        btn = QPushButton(text)
        btn.clicked.connect(callback)
        btn.setMaximumHeight(24)
        return btn
    
    def _create_icon_button(self, icon_text, tooltip, callback):
        """Helper to create icon-only button."""
        from PySide6.QtWidgets import QPushButton
        btn = QPushButton(icon_text)
        btn.clicked.connect(callback)
        btn.setMaximumHeight(24)
        btn.setMaximumWidth(32)
        btn.setToolTip(tooltip)
        return btn
    
    def _setup_signals(self):
        """Connect tree widget signals."""
        self.tree_widget.layer_visibility_changed.connect(self._on_visibility_changed)
        self.tree_widget.layer_locked_changed.connect(self._on_locked_changed)
        self.tree_widget.layer_opacity_changed.connect(self._on_opacity_changed)
        self.tree_widget.layer_selected.connect(self._on_layer_selected)
        self.tree_widget.layer_renamed.connect(self._on_layer_renamed)
        self.tree_widget.layer_deleted.connect(self._on_layer_deleted)
        self.tree_widget.layers_reordered.connect(self._on_layers_reordered)
        self.tree_widget.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.tree_widget.customContextMenuRequested.connect(self._show_context_menu)
        self.tree_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
    
    def add_graphics_item(self, graphics_item, item_data=None, name=None):
        """
        Auto-register a graphics item from screen.
        
        This is called automatically when objects are created on the screen.
        Users cannot manually create layers; they are created automatically.
        
        Args:
            graphics_item: QGraphicsItem to add (from canvas)
            item_data: Optional data dict with item info (id, type, etc.)
            name: Optional name for the layer (defaults to auto-generated from item ID)
        """
        # Generate a meaningful name from item data
        if not name:
            if item_data:
                item_id = item_data.get('id', 'Unknown')
                item_type = item_data.get('type', 'Object').title()
                name = f"{item_type} {item_id}"
            else:
                name = type(graphics_item).__name__
        
        layer = LayerItem(name)
        layer.graphics_item = graphics_item
        self.root_layer.add_child(layer)
        self.layer_map[layer.layer_id] = layer
        self.graphics_items_map[id(graphics_item)] = layer
        
        self._add_tree_item(layer)
        self.tree_widget.layers_changed.emit()
        logger.debug(f"Auto-registered layer: {name} (ID: {layer.layer_id})")
        
    def remove_graphics_item(self, graphics_item):
        """Remove a graphics item from layers."""
        item_id = id(graphics_item)
        if item_id in self.graphics_items_map:
            layer = self.graphics_items_map[item_id]
            self._remove_tree_item(layer)
            del self.graphics_items_map[item_id]
            del self.layer_map[layer.layer_id]
            self.tree_widget.layers_changed.emit()
    
    def _add_tree_item(self, layer_item, parent_tree_item=None):
        """Add a layer to the tree widget."""
        if parent_tree_item is None:
            parent_tree_item = self.tree_widget.invisibleRootItem()
        
        tree_item = QTreeWidgetItem(parent_tree_item)
        tree_item.setText(0, layer_item.name)
        tree_item.setData(0, Qt.ItemDataRole.UserRole, layer_item.layer_id)
        
        # Set icons
        if layer_item.is_group:
            tree_item.setIcon(0, IconService.get_icon("folder") or self._create_default_icon("📁"))
        
        # Add visibility toggle
        vis_widget = self._create_visibility_widget(layer_item)
        self.tree_widget.setItemWidget(tree_item, 1, vis_widget)
        
        # Add lock toggle
        lock_widget = self._create_lock_widget(layer_item)
        self.tree_widget.setItemWidget(tree_item, 2, lock_widget)
        
        # Add children
        for child in layer_item.children:
            self._add_tree_item(child, tree_item)
    
    def _remove_tree_item(self, layer_item):
        """Remove a layer from the tree widget."""
        # Find and remove the tree item
        for i in range(self.tree_widget.topLevelItemCount()):
            item = self.tree_widget.topLevelItem(i)
            if self._find_and_remove_tree_item(item, layer_item):
                return
    
    def _find_and_remove_tree_item(self, tree_item, layer_item):
        """Recursively find and remove tree item."""
        item_data = self._layer_from_tree_item(tree_item)
        if item_data == layer_item:
            parent = tree_item.parent()
            if parent:
                parent.removeChild(tree_item)
            else:
                self.tree_widget.invisibleRootItem().removeChild(tree_item)
            return True
        
        for i in range(tree_item.childCount()):
            if self._find_and_remove_tree_item(tree_item.child(i), layer_item):
                return True
        
        return False
    
    def _create_visibility_widget(self, layer_item):
        """Create visibility toggle widget."""
        from PySide6.QtWidgets import QPushButton
        btn = QPushButton()
        btn.setMaximumWidth(24)
        btn.setMaximumHeight(24)
        btn.setFlat(True)
        self._update_visibility_button(btn, layer_item.visible)
        
        def toggle():
            layer_item.visible = not layer_item.visible
            self._update_visibility_button(btn, layer_item.visible)
            self.tree_widget.layer_visibility_changed.emit(layer_item.layer_id, layer_item.visible)
            
            # If this is a group, cascade visibility to all children
            if layer_item.is_group:
                self._set_group_visibility_cascade(layer_item, layer_item.visible)
            
            if layer_item.graphics_item:
                layer_item.graphics_item.show() if layer_item.visible else layer_item.graphics_item.hide()
        
        btn.clicked.connect(toggle)
        return btn
    
    def _set_group_visibility_cascade(self, group_item, visible):
        """Recursively set visibility for all children in a group."""
        for child in group_item.children:
            child.visible = visible
            # Update UI for child
            tree_item = self._find_tree_item_for_layer(child)
            if tree_item:
                vis_widget = self.tree_widget.itemWidget(tree_item, 1)
                if vis_widget:
                    self._update_visibility_button(vis_widget, visible)
            
            if child.graphics_item:
                child.graphics_item.show() if visible else child.graphics_item.hide()
            
            # Recursively apply to nested groups
            if child.is_group:
                self._set_group_visibility_cascade(child, visible)
    
    def _update_visibility_button(self, btn, visible):
        """Update visibility button appearance."""
        if visible:
            btn.setText("👁")
            btn.setToolTip("Hide layer")
        else:
            btn.setText("🚫")
            btn.setToolTip("Show layer")
    
    def _create_lock_widget(self, layer_item):
        """Create lock toggle widget."""
        from PySide6.QtWidgets import QPushButton
        btn = QPushButton()
        btn.setMaximumWidth(24)
        btn.setMaximumHeight(24)
        btn.setFlat(True)
        self._update_lock_button(btn, layer_item.locked)
        
        def toggle():
            from PySide6.QtWidgets import QGraphicsItem
            layer_item.locked = not layer_item.locked
            self._update_lock_button(btn, layer_item.locked)
            self.tree_widget.layer_locked_changed.emit(layer_item.layer_id, layer_item.locked)
            
            # If this is a group, cascade lock to all children
            if layer_item.is_group:
                self._set_group_lock_cascade(layer_item, layer_item.locked)
            
            if layer_item.graphics_item:
                layer_item.graphics_item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, not layer_item.locked)
                layer_item.graphics_item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, not layer_item.locked)
        
        btn.clicked.connect(toggle)
        return btn
    
    def _set_group_lock_cascade(self, group_item, locked):
        """Recursively set lock state for all children in a group."""
        for child in group_item.children:
            child.locked = locked
            # Update UI for child
            tree_item = self._find_tree_item_for_layer(child)
            if tree_item:
                lock_widget = self.tree_widget.itemWidget(tree_item, 2)
                if lock_widget:
                    self._update_lock_button(lock_widget, locked)
            
            if child.graphics_item:
                from PySide6.QtWidgets import QGraphicsItem
                child.graphics_item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, not locked)
                child.graphics_item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, not locked)
            
            # Recursively apply to nested groups
            if child.is_group:
                self._set_group_lock_cascade(child, locked)
    
    def _update_lock_button(self, btn, locked):
        """Update lock button appearance."""
        if locked:
            btn.setText("🔒")
            btn.setToolTip("Unlock layer")
        else:
            btn.setText("🔓")
            btn.setToolTip("Lock layer")
    
    def _create_default_icon(self, text):
        """Create a simple text-based icon."""
        pixmap = QPixmap(16, 16)
        pixmap.fill(Qt.GlobalColor.transparent)
        return QIcon(pixmap)
    
    def _add_layer(self):
        """Add a new layer."""
        selected_items = self.tree_widget.selectedItems()
        parent_layer = self.root_layer
        parent_tree_item = self.tree_widget.invisibleRootItem()
        
        if selected_items:
            parent_tree_item = selected_items[0]
            parent_layer_data = self._layer_from_tree_item(parent_tree_item)
            if parent_layer_data:
                parent_layer = parent_layer_data if parent_layer_data.is_group else parent_layer_data.parent or self.root_layer
        
        new_layer = LayerItem(f"Layer {len(self.layer_map) + 1}")
        parent_layer.add_child(new_layer)
        self.layer_map[new_layer.layer_id] = new_layer
        
        self._add_tree_item(new_layer, parent_tree_item)
        self.tree_widget.layers_changed.emit()
    
    def _add_group(self):
        """Add a new group. If items selected, move them into the group."""
        selected_items = self.tree_widget.selectedItems()
        
        # Determine parent for new group
        parent_layer = self.root_layer
        parent_tree_item = self.tree_widget.invisibleRootItem()
        
        if selected_items:
            # Get parent of first selected item
            first_item = selected_items[0]
            parent_tree_item_candidate = first_item.parent()
            if parent_tree_item_candidate:
                parent_tree_item = parent_tree_item_candidate
                parent_layer_data = self._layer_from_tree_item(parent_tree_item_candidate)
                if parent_layer_data:
                    parent_layer = parent_layer_data
            else:
                parent_layer = self.root_layer
        
        new_group = LayerItem(f"Group {len(self.layer_map) + 1}", is_group=True)
        parent_layer.add_child(new_group)
        self.layer_map[new_group.layer_id] = new_group
        
        # If items were selected, move them into the group
        if selected_items:
            selected_layers = []
            for tree_item in selected_items:
                layer_item = self._layer_from_tree_item(tree_item)
                if layer_item:
                    selected_layers.append(layer_item)
            
            # Move selected layers into the group
            for layer_item in selected_layers:
                if layer_item.parent:
                    layer_item.parent.remove_child(layer_item)
                new_group.add_child(layer_item)
        
        # Rebuild tree
        self.tree_widget.clear()
        for child in self.root_layer.children:
            self._add_tree_item(child)
        
        self.tree_widget.layers_changed.emit()
    
    def _delete_layer(self):
        """Delete selected layer."""
        selected_items = self.tree_widget.selectedItems()
        if not selected_items:
            return
        
        tree_item = selected_items[0]
        layer_item = self._layer_from_tree_item(tree_item)
        
        if layer_item and layer_item.layer_id != "root":
            if layer_item.parent:
                layer_item.parent.remove_child(layer_item)
            
            if layer_item.layer_id in self.layer_map:
                del self.layer_map[layer_item.layer_id]
            
            # Safely remove graphics item from scene
            if layer_item.graphics_item:
                try:
                    scene = layer_item.graphics_item.scene()
                    if scene:
                        # Check if item actually belongs to this scene
                        if layer_item.graphics_item in scene.items():
                            scene.removeItem(layer_item.graphics_item)
                except (RuntimeError, AttributeError):
                    # Item may have already been deleted or scene is invalid
                    pass
                
                if id(layer_item.graphics_item) in self.graphics_items_map:
                    del self.graphics_items_map[id(layer_item.graphics_item)]
            
            parent = tree_item.parent()
            if parent:
                parent.removeChild(tree_item)
            else:
                self.tree_widget.invisibleRootItem().removeChild(tree_item)
            
            self.tree_widget.layers_changed.emit()
            self.tree_widget.layer_deleted.emit(layer_item.layer_id)
    
    def _duplicate_layer(self):
        """Duplicate selected layer AND its graphics item on canvas."""
        selected_items = self.tree_widget.selectedItems()
        if not selected_items:
            return
        
        tree_item = selected_items[0]
        layer_item = self._layer_from_tree_item(tree_item)
        
        if not layer_item:
            return
        
        def duplicate_recursive(source_layer, get_canvas):
            new_layer = LayerItem(
                f"{source_layer.name} copy",
                is_group=source_layer.is_group
            )
            new_layer.visible = source_layer.visible
            new_layer.locked = source_layer.locked
            new_layer.opacity = source_layer.opacity
            
            # If source layer has graphics item, duplicate it on canvas
            if source_layer.graphics_item and not source_layer.is_group:
                canvas = get_canvas()
                if canvas:
                    # Get the original item's data
                    item_data = source_layer.graphics_item.data(Qt.ItemDataRole.UserRole)
                    if item_data:
                        # Create a copy with new ID
                        new_item_data = item_data.copy()
                        new_item_data['id'] = canvas._generate_next_id()
                        
                        # Create the graphics item with new ID
                        # IMPORTANT: Pass is_restoring=True to prevent double layer creation
                        # (we handle layer creation manually here in _duplicate_layer)
                        new_graphics_item = canvas.create_graphic_item_from_data(new_item_data, is_restoring=True)
                        if new_graphics_item:
                            new_layer.graphics_item = new_graphics_item
                            # Map graphics item to layer
                            self.graphics_items_map[id(new_graphics_item)] = new_layer
                            canvas.save_items()
            
            for child in source_layer.children:
                new_layer.add_child(duplicate_recursive(child, get_canvas))
            
            return new_layer
        
        # Get the canvas from the graphics item's scene
        canvas = None
        if layer_item.graphics_item:
            scene = layer_item.graphics_item.scene()
            if scene and hasattr(scene, 'views'):
                views = list(scene.views())
                if views:
                    canvas = views[0]
        
        dup_layer = duplicate_recursive(layer_item, lambda: canvas)
        parent = layer_item.parent or self.root_layer
        parent.add_child(dup_layer)
        self.layer_map[dup_layer.layer_id] = dup_layer
        
        parent_tree_item = tree_item.parent() or self.tree_widget.invisibleRootItem()
        self._add_tree_item(dup_layer, parent_tree_item)
        self.tree_widget.layers_changed.emit()
    
    def _filter_layers(self, text):
        """Filter layers by search text."""
        self._filter_tree_items(self.tree_widget.invisibleRootItem(), text.lower())
    
    def _filter_tree_items(self, parent_item, search_text):
        """Recursively filter tree items."""
        for i in range(parent_item.childCount()):
            tree_item = parent_item.child(i)
            layer_item = self._layer_from_tree_item(tree_item)
            
            if layer_item:
                matches = search_text in layer_item.name.lower()
                tree_item.setHidden(not matches)
            
            self._filter_tree_items(tree_item, search_text)
    
    def _on_visibility_changed(self, layer_id, visible):
        """Handle visibility change."""
        if layer_id in self.layer_map:
            self.layer_map[layer_id].visible = visible
    
    def _on_locked_changed(self, layer_id, locked):
        """Handle lock change."""
        if layer_id in self.layer_map:
            self.layer_map[layer_id].locked = locked
    
    def _on_opacity_changed(self, layer_id, opacity):
        """Handle opacity change."""
        if layer_id in self.layer_map:
            self.layer_map[layer_id].opacity = opacity

    def _layer_from_tree_item(self, tree_item):
        """Proxy helper so LayersDock can reuse the tree's lookup."""
        if not hasattr(self.tree_widget, "_layer_from_tree_item"):
            return None
        return self.tree_widget._layer_from_tree_item(tree_item)
    
    def _on_layer_selected(self, layer_id):
        """Handle layer selection - select corresponding graphics item and update opacity control."""
        if layer_id in self.layer_map:
            layer_item = self.layer_map[layer_id]
            # Update opacity slider and spinbox to show selected layer's opacity
            self.opacity_slider.blockSignals(True)
            self.opacity_value.blockSignals(True)
            self.opacity_slider.setValue(layer_item.opacity)
            self.opacity_value.setValue(layer_item.opacity)
            self.opacity_slider.blockSignals(False)
            self.opacity_value.blockSignals(False)
            
            if layer_item.graphics_item and not layer_item.locked:
                scene = layer_item.graphics_item.scene()
                if scene:
                    # Allow multiple selection with Ctrl key
                    # Check if Ctrl is held
                    from PySide6.QtWidgets import QApplication
                    modifiers = QApplication.keyboardModifiers()
                    if modifiers != Qt.KeyboardModifier.ControlModifier:
                        scene.clearSelection()
                    layer_item.graphics_item.setSelected(True)
    
    def sync_canvas_selection(self, selected_items, deselected_items):
        """Sync canvas selection to layers dock - called when canvas items are selected."""
        # Block signals temporarily to avoid loop
        self.tree_widget.blockSignals(True)
        self.tree_widget.clearSelection()
        
        # Select corresponding layers
        for item in selected_items:
            item_id = id(item)
            if item_id in self.graphics_items_map:
                layer = self.graphics_items_map[item_id]
                # Find tree item for this layer
                tree_item = self._find_tree_item_for_layer(layer)
                if tree_item:
                    tree_item.setSelected(True)
        
        self.tree_widget.blockSignals(False)
    
    def _on_layer_renamed(self, layer_id, new_name):
        """Handle layer rename."""
        if layer_id in self.layer_map:
            self.layer_map[layer_id].name = new_name
    
    def _on_layer_deleted(self, layer_id):
        """Handle layer deletion."""
        self.tree_widget.layers_changed.emit()
    
    def _on_layers_reordered(self):
        """Handle layer reordering - update z-order on canvas."""
        # This handler is called when layers are reordered via drag-drop
        # Update z-order of graphics items based on tree position if needed
        pass
    
    def _find_tree_item_for_layer(self, layer_item):
        """Recursively find tree item for a given layer item."""
        for i in range(self.tree_widget.topLevelItemCount()):
            tree_item = self._find_tree_item_recursive(self.tree_widget.topLevelItem(i), layer_item)
            if tree_item:
                return tree_item
        return None
    
    def _find_tree_item_recursive(self, tree_item, layer_item):
        """Recursively search for tree item matching layer."""
        item_data = self._layer_from_tree_item(tree_item)
        if item_data == layer_item:
            return tree_item
        
        for i in range(tree_item.childCount()):
            result = self._find_tree_item_recursive(tree_item.child(i), layer_item)
            if result:
                return result
        
        return None

    def _on_item_double_clicked(self, tree_item, column):
        """Handle double-click to rename."""
        layer_item = self._layer_from_tree_item(tree_item)
        if column == 0 and layer_item:
            # Enable editing for this item
            tree_item.setFlags(tree_item.flags() | Qt.ItemFlag.ItemIsEditable)
            self.tree_widget.editItem(tree_item, column)
    
    def _on_opacity_slider_changed(self, value):
        """Handle opacity slider change."""
        self.opacity_value.blockSignals(True)
        self.opacity_value.setValue(value)
        self.opacity_value.blockSignals(False)
        self._apply_opacity_to_selected(value)
    
    def _on_opacity_value_changed(self, value):
        """Handle opacity spinbox change."""
        self.opacity_slider.blockSignals(True)
        self.opacity_slider.setValue(value)
        self.opacity_slider.blockSignals(False)
        self._apply_opacity_to_selected(value)
    
    def _apply_opacity_to_selected(self, opacity):
        """Apply opacity to selected layer."""
        selected_items = self.tree_widget.selectedItems()
        if selected_items:
            tree_item = selected_items[0]
            layer_item = self._layer_from_tree_item(tree_item)
            if layer_item:
                layer_item.opacity = opacity
                # Update label
                opacity_label = self.tree_widget.itemWidget(tree_item, 3)
                if opacity_label:
                    from PySide6.QtWidgets import QLabel
                    if isinstance(opacity_label, QLabel):
                        opacity_label.setText(f"{opacity}%")
                
                if layer_item.graphics_item:
                    layer_item.graphics_item.setOpacity(opacity / 100.0)
                
                self.tree_widget.layer_opacity_changed.emit(layer_item.layer_id, opacity)
    
    def _show_context_menu(self, position):
        """Show context menu for layer operations."""
        selected_items = self.tree_widget.selectedItems()
        
        menu = QMenu()
        menu.addAction("New Layer", self._add_layer)
        menu.addAction("New Group", self._add_group)
        
        if selected_items:
            menu.addSeparator()
            menu.addAction("Rename", self._rename_layer)
            menu.addAction("Duplicate", self._duplicate_layer)
            menu.addAction("Delete", self._delete_layer)
            menu.addSeparator()
            
            layer_item = self._layer_from_tree_item(selected_items[0])
            if layer_item and layer_item.children:
                menu.addAction("Ungroup", self._ungroup_layer)
            
            menu.addSeparator()
            menu.addAction("Move Up", self._move_layer_up)
            menu.addAction("Move Down", self._move_layer_down)
            menu.addSeparator()
            menu.addAction("Hide Others", self._hide_others)
            menu.addAction("Show All", self._show_all)
            menu.addAction("Lock Others", self._lock_others)
            menu.addAction("Unlock All", self._unlock_all)
        
        menu.exec(self.tree_widget.mapToGlobal(position))
    
    def _rename_layer(self):
        """Rename selected layer."""
        selected_items = self.tree_widget.selectedItems()
        if selected_items:
            tree_item = selected_items[0]
            tree_item.setFlags(tree_item.flags() | Qt.ItemFlag.ItemIsEditable)
            self.tree_widget.editItem(tree_item, 0)
    
    def _ungroup_layer(self):
        """Ungroup a group layer."""
        selected_items = self.tree_widget.selectedItems()
        if not selected_items:
            return
        
        tree_item = selected_items[0]
        layer_item = self._layer_from_tree_item(tree_item)
        
        if layer_item and layer_item.is_group:
            parent = layer_item.parent or self.root_layer
            parent_tree_item = tree_item.parent() or self.tree_widget.invisibleRootItem()
            
            # Move children to parent
            for child in list(layer_item.children):
                layer_item.remove_child(child)
                parent.add_child(child)
                self._add_tree_item(child, parent_tree_item)
            
            # Remove group
            self._remove_tree_item(layer_item)
            if layer_item.layer_id in self.layer_map:
                del self.layer_map[layer_item.layer_id]
            
            self.tree_widget.layers_changed.emit()
    
    def _move_layer_up(self):
        """Move selected layer up within its parent."""
        selected_items = self.tree_widget.selectedItems()
        if not selected_items:
            return
        
        tree_item = selected_items[0]
        layer_item = self._layer_from_tree_item(tree_item)
        
        if not layer_item or layer_item.layer_id == "root":
            return
        
        parent = layer_item.parent or self.root_layer
        current_index = parent.children.index(layer_item)
        
        # Can't move up if already at top
        if current_index <= 0:
            return
        
        # Swap with previous
        parent.children[current_index], parent.children[current_index - 1] = \
            parent.children[current_index - 1], parent.children[current_index]
        
        # Rebuild tree to reflect changes
        self._rebuild_tree()
        self.tree_widget.layers_reordered.emit()
    
    def _move_layer_down(self):
        """Move selected layer down within its parent."""
        selected_items = self.tree_widget.selectedItems()
        if not selected_items:
            return
        
        tree_item = selected_items[0]
        layer_item = self._layer_from_tree_item(tree_item)
        
        if not layer_item or layer_item.layer_id == "root":
            return
        
        parent = layer_item.parent or self.root_layer
        current_index = parent.children.index(layer_item)
        
        # Can't move down if already at bottom
        if current_index >= len(parent.children) - 1:
            return
        
        # Swap with next
        parent.children[current_index], parent.children[current_index + 1] = \
            parent.children[current_index + 1], parent.children[current_index]
        
        # Rebuild tree to reflect changes
        self._rebuild_tree()
        self.tree_widget.layers_reordered.emit()
    
    def _rebuild_tree(self):
        """Rebuild the tree widget from the layer hierarchy."""
        self.tree_widget.clear()
        for child in self.root_layer.children:
            self._add_tree_item(child)
    
    def _hide_others(self):
        """Hide all layers except selected."""
        selected_items = self.tree_widget.selectedItems()
        if not selected_items:
            return
        
        selected_layer = self._layer_from_tree_item(selected_items[0])
        
        def hide_all_except(layer_item):
            if layer_item != selected_layer:
                layer_item.visible = False
                if layer_item.graphics_item:
                    layer_item.graphics_item.hide()
            
            for child in layer_item.children:
                hide_all_except(child)
        
        hide_all_except(self.root_layer)
        self.tree_widget.layers_changed.emit()
    
    def _show_all(self):
        """Show all layers."""
        def show_all(layer_item):
            layer_item.visible = True
            if layer_item.graphics_item:
                layer_item.graphics_item.show()
            
            for child in layer_item.children:
                show_all(child)
        
        show_all(self.root_layer)
        self.tree_widget.layers_changed.emit()
    
    def _lock_others(self):
        """Lock all layers except selected."""
        selected_items = self.tree_widget.selectedItems()
        if not selected_items:
            return
        
        selected_layer = self._layer_from_tree_item(selected_items[0])
        
        def lock_all_except(layer_item):
            if layer_item != selected_layer:
                layer_item.locked = True
                if layer_item.graphics_item:
                    layer_item.graphics_item.setFlag(layer_item.graphics_item.ItemIsMovable, False)
                    layer_item.graphics_item.setFlag(layer_item.graphics_item.ItemIsSelectable, False)
            
            for child in layer_item.children:
                lock_all_except(child)
        
        lock_all_except(self.root_layer)
        self.tree_widget.layers_changed.emit()
    
    def _unlock_all(self):
        """Unlock all layers."""
        def unlock_all(layer_item):
            layer_item.locked = False
            if layer_item.graphics_item:
                layer_item.graphics_item.setFlag(layer_item.graphics_item.ItemIsMovable, True)
                layer_item.graphics_item.setFlag(layer_item.graphics_item.ItemIsSelectable, True)
            
            for child in layer_item.children:
                unlock_all(child)
        
        unlock_all(self.root_layer)
        self.tree_widget.layers_changed.emit()
    
    def keyPressEvent(self, event):
        """Handle keyboard shortcuts."""
        if event.key() == Qt.Key.Key_Delete:
            self._delete_layer()
            event.accept()
        elif event.matches(QKeySequence.StandardKey.Paste):
            self._duplicate_layer()
            event.accept()
        elif event.key() == Qt.Key.Key_F2 or (event.modifiers() == Qt.KeyboardModifier.ControlModifier and event.key() == Qt.Key.Key_R):
            self._rename_layer()
            event.accept()
        else:
            super().keyPressEvent(event)
    
    def get_layer_hierarchy(self):
        """Get layer hierarchy as dictionary."""
        return self.root_layer.to_dict()
    
    def set_layer_hierarchy(self, data):
        """Set layer hierarchy from dictionary."""
        self.tree_widget.clear()
        self.root_layer = LayerItem.from_dict(data)
        self.layer_map.clear()
        
        def populate_map(layer_item):
            self.layer_map[layer_item.layer_id] = layer_item
            for child in layer_item.children:
                populate_map(child)
        
        populate_map(self.root_layer)
        
        for child in self.root_layer.children:
            self._add_tree_item(child)
        
        self.tree_widget.layers_changed.emit()
    
    def sync_with_scene(self, scene):
        """
        Sync layers panel with graphics scene items.
        
        Args:
            scene: QGraphicsScene to sync with
        """
        if not scene:
            return
        
        # Clear existing layers (except root)
        self.root_layer.children.clear()
        self.layer_map.clear()
        self.graphics_items_map.clear()
        self.tree_widget.clear()
        
        # Add all scene items
        for item in scene.items():
            if item.parentItem() is None:  # Top-level items only
                layer = LayerItem(type(item).__name__)
                layer.graphics_item = item
                self.root_layer.add_child(layer)
                self.layer_map[layer.layer_id] = layer
                self.graphics_items_map[id(item)] = layer
                self._add_tree_item(layer)
        
        self.tree_widget.layers_changed.emit()
