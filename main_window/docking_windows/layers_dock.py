# main_window\docking_windows\layers_dock.py
from PySide6.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QHBoxLayout, QTreeWidgetItem, 
    QSlider, QSpinBox, QPushButton, QLabel, QMenu, QAbstractItemView, QGraphicsScene
)
from PySide6.QtCore import Qt, Signal, QTimer, QRectF
from PySide6.QtGui import QIcon, QPixmap, QPainter
from PySide6.QtWidgets import QGraphicsItem
from ..widgets.tree import CustomTreeWidget
from ..services.icon_service import IconService
from screen.base.base_graphic_object import BaseGraphicObject


class LayersTreeWidget(CustomTreeWidget):
    """
    Custom tree widget for the Layers panel with visibility and lock columns.
    """
    
    itemVisibilityChanged = Signal(QTreeWidgetItem, bool)
    itemLockChanged = Signal(QTreeWidgetItem, bool)
    itemNameChanged = Signal(QTreeWidgetItem, str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        # Setup columns: Tree (hidden), Visibility, Lock, Preview, Name, Object ID
        self.setup_columns(6, ["", "V", "L", "P", "Name", "Object ID"])
        self.setHeaderHidden(True)
        
        # Column widths - optimized for preview and icons
        self.setColumnWidth(0, 16)   # Tree expand/collapse (narrow for decoration only)
        self.setColumnWidth(1, 28)   # Visibility - icon only
        self.setColumnWidth(2, 28)   # Lock - icon only
        self.setColumnWidth(3, 20)   # Preview - larger for thumbnail
        self.setColumnWidth(4, 150)  # Name - compact width right after preview
        self.setColumnWidth(5, 30)  # Object ID - read-only
        
        # Enable drag and drop for reordering
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        
        # Selection mode
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        
        # Connect click to handle visibility/lock toggles
        self.itemClicked.connect(self._on_item_clicked)
        self.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.itemChanged.connect(self._on_item_changed)
        
        # Set row height for preview thumbnails
        self.setUniformRowHeights(False)
    
    def _on_item_clicked(self, item, column):
        """Handle clicks on visibility and lock columns."""
        if column == 1:
            # Toggle visibility
            is_visible = item.data(0, Qt.ItemDataRole.UserRole + 10)
            if is_visible is None:
                is_visible = True
            new_state = not is_visible
            item.setData(0, Qt.ItemDataRole.UserRole + 10, new_state)
            self._update_visibility_icon(item, new_state)
            self.itemVisibilityChanged.emit(item, new_state)
        elif column == 2:
            # Toggle lock
            is_locked = item.data(0, Qt.ItemDataRole.UserRole + 11)
            if is_locked is None:
                is_locked = False
            new_state = not is_locked
            item.setData(0, Qt.ItemDataRole.UserRole + 11, new_state)
            self._update_lock_icon(item, new_state)
            self.itemLockChanged.emit(item, new_state)
    
    def _on_item_double_clicked(self, item, column):
        """Handle double-click to edit name (column 4)."""
        if column == 4:  # Name column
            self.editItem(item, column)
    
    def _on_item_changed(self, item, column):
        """Handle item data changes."""
        if column == 4:  # Name column
            new_name = item.text(4)
            self.itemNameChanged.emit(item, new_name)
    
    def keyPressEvent(self, event):
        """Handle F2 key to edit selected item name."""
        from PySide6.QtGui import QKeySequence
        
        if event.key() == Qt.Key.Key_F2:
            # Edit name of currently selected item
            selected_items = self.selectedItems()
            if selected_items:
                item = selected_items[0]
                self.editItem(item, 4)  # Column 4 is the name column
                event.accept()
                return
        
        super().keyPressEvent(event)
    
    def _update_visibility_icon(self, item, is_visible):
        """Update the visibility icon for an item."""
        if is_visible:
            item.setIcon(1, IconService.get_icon('layer-visible'))
        else:
            item.setIcon(1, IconService.get_icon('layer-hidden'))
    
    def _update_lock_icon(self, item, is_locked):
        """Update the lock icon for an item."""
        if is_locked:
            item.setIcon(2, IconService.get_icon('layer-locked'))
        else:
            item.setIcon(2, IconService.get_icon('layer-unlocked'))
    
    def _generate_preview(self, canvas_obj, size=80):
        """
        Generate a live preview pixmap of a canvas object.
        
        Args:
            canvas_obj: The BaseGraphicObject from canvas
            size: The size of the preview (width and height)
            
        Returns:
            QPixmap with the object rendered
        """
        try:
            # Get the object's bounding rect in local coordinates
            bound_rect = canvas_obj.boundingRect()
            
            if bound_rect.isEmpty() or bound_rect.width() == 0 or bound_rect.height() == 0:
                # Return a white pixmap for empty objects
                pixmap = QPixmap(int(size), int(size))
                pixmap.fill(Qt.GlobalColor.white)
                return pixmap
            
            # Create the preview pixmap with white background
            preview_size = int(size)
            pixmap = QPixmap(preview_size, preview_size)
            pixmap.fill(Qt.GlobalColor.white)
            
            # Calculate scaling to fit the preview
            scale = min(size / bound_rect.width(), size / bound_rect.height())
            scale = min(scale, 1.0)  # Don't scale up
            
            # Create painter
            painter = QPainter(pixmap)
            if not painter.isActive():
                return pixmap
                
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
            
            try:
                # Calculate the render rectangle (the area we want to capture from the object)
                render_rect = bound_rect.adjusted(-2, -2, 2, 2)
                
                # Calculate offset to center the scaled object in the pixmap
                scaled_width = render_rect.width() * scale
                scaled_height = render_rect.height() * scale
                offset_x = (preview_size - scaled_width) / 2
                offset_y = (preview_size - scaled_height) / 2
                
                # Translate and scale for centered preview
                painter.translate(offset_x, offset_y)
                painter.scale(scale, scale)
                painter.translate(-render_rect.left(), -render_rect.top())
                
                # Paint the inner item with its visual properties (brush, pen, etc.)
                if hasattr(canvas_obj, 'item') and canvas_obj.item:
                    inner_item = canvas_obj.item
                    try:
                        # Create a basic style option for painting
                        from PySide6.QtWidgets import QStyleOptionGraphicsItem
                        option = QStyleOptionGraphicsItem()
                        if hasattr(inner_item, 'rect'):
                            option.rect = inner_item.rect()
                        else:
                            option.rect = inner_item.boundingRect()
                        option.exposedRect = option.rect
                        
                        # Paint the item
                        inner_item.paint(painter, option, None)
                    except Exception:
                        pass
            finally:
                painter.end()
            
            return pixmap
        except Exception as e:
            # Return a white pixmap on error
            try:
                pixmap = QPixmap(int(size), int(size))
                pixmap.fill(Qt.GlobalColor.white)
                return pixmap
            except:
                return QPixmap()
    
    def set_object_preview(self, item, canvas_obj):
        """
        Set the preview icon for an item from a canvas object.
        
        Args:
            item: QTreeWidgetItem
            canvas_obj: The BaseGraphicObject to preview
        """
        try:
            if canvas_obj and hasattr(canvas_obj, 'boundingRect'):
                preview_pixmap = self._generate_preview(canvas_obj, size=80)
                if not preview_pixmap.isNull():
                    item.setIcon(3, QIcon(preview_pixmap))
                    # Store reference to object for updates
                    item.setData(0, Qt.ItemDataRole.UserRole + 14, canvas_obj)
                    return
        except Exception as e:
            pass
        
        # Fallback to generic icon
        item.setIcon(3, IconService.get_icon('layer-item'))
    
    def add_layer_item(self, parent, name, preview_icon=None, is_group=False, canvas_obj=None, object_id=None):
        """
        Add a layer item to the tree.
        
        Args:
            parent: Parent item or None for top level
            name: Layer name
            preview_icon: Optional preview icon (deprecated, use canvas_obj instead)
            is_group: Whether this is a group layer
            canvas_obj: Optional canvas object for live preview
            object_id: Optional object ID to display
        """
        item = QTreeWidgetItem()
        
        # Set visibility (default: visible) - column 1
        item.setText(1, "")  # Empty text to show icon
        item.setData(0, Qt.ItemDataRole.UserRole + 10, True)
        self._update_visibility_icon(item, True)
        
        # Set lock (default: unlocked) - column 2
        item.setText(2, "")  # Empty text to show icon
        item.setData(0, Qt.ItemDataRole.UserRole + 11, False)
        self._update_lock_icon(item, False)
        
        # Set preview icon - column 3
        item.setText(3, "")  # Empty text to show icon
        if canvas_obj:
            # Use live preview from canvas object
            self.set_object_preview(item, canvas_obj)
        elif preview_icon:
            item.setIcon(3, preview_icon)
        elif is_group:
            item.setIcon(3, IconService.get_icon('layer-group'))
        else:
            item.setIcon(3, IconService.get_icon('layer-item'))
        
        # Set name in column 4 (editable)
        item.setText(4, name)
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
        
        # Set object ID in column 5 (read-only)
        if object_id:
            item.setText(5, str(object_id))
        
        # Store layer type
        item.setData(0, Qt.ItemDataRole.UserRole + 12, 'group' if is_group else 'layer')
        
        if parent:
            parent.addChild(item)
        else:
            self.addTopLevelItem(item)
        
        return item


class LayersDock(QDockWidget):
    """
    Dockable window to display and manage layers in the current screen.
    Syncs with canvas objects: selecting layers selects objects and vice versa.
    """
    
    opacityChanged = Signal(int)
    layerDeleted = Signal(QTreeWidgetItem)
    layerDuplicated = Signal(QTreeWidgetItem)
    
    def __init__(self, main_window):
        """
        Initializes the Layers dock widget.

        Args:
            main_window (QMainWindow): The main window instance.
        """
        super().__init__("Layers", main_window)
        self.main_window = main_window
        self.setObjectName("layers")
        
        # Track the current canvas and objects
        self.current_canvas = None
        self.object_to_item_map = {}  # Maps canvas objects to tree items
        self.item_to_object_map = {}  # Maps tree items to canvas objects
        self._syncing = False  # Prevent circular updates during sync
        self._updating_canvas = False  # Prevent circular updates when updating canvas
        self.previously_selected_objects = set()  # Track previous selection for deselection detection
        
        # Preview update timer
        self.preview_update_timer = QTimer()
        self.preview_update_timer.timeout.connect(self._update_previews)
        self.preview_update_timer.setInterval(500)  # Update every 500ms
        self.items_needing_preview_update = set()  # Track items that need preview updates
        
        # Create main widget
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(4)
        
        # Create top toolbar with opacity and buttons
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setContentsMargins(0, 0, 0, 0)
        toolbar_layout.setSpacing(8)
        
        # Opacity label
        opacity_label = QLabel("Opacity:")
        toolbar_layout.addWidget(opacity_label)
        
        # Opacity slider
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(0, 100)
        self.opacity_slider.setValue(100)
        self.opacity_slider.setMinimumWidth(150)
        toolbar_layout.addWidget(self.opacity_slider, 1)
        
        # Opacity spinbox
        self.opacity_spinbox = QSpinBox()
        self.opacity_spinbox.setRange(0, 100)
        self.opacity_spinbox.setValue(100)
        self.opacity_spinbox.setFixedWidth(50)
        toolbar_layout.addWidget(self.opacity_spinbox)
        
        # Spacer
        toolbar_layout.addStretch()
        
        # Delete button
        self.delete_button = QPushButton()
        self.delete_button.setIcon(IconService.get_icon('edit-delete'))
        self.delete_button.setToolTip("Delete Layer")
        self.delete_button.setFixedSize(28, 28)
        toolbar_layout.addWidget(self.delete_button)
        
        # Duplicate button
        self.duplicate_button = QPushButton()
        self.duplicate_button.setIcon(IconService.get_icon('edit-duplicate'))
        self.duplicate_button.setToolTip("Duplicate Layer")
        self.duplicate_button.setFixedSize(28, 28)
        toolbar_layout.addWidget(self.duplicate_button)
        
        main_layout.addLayout(toolbar_layout)
        
        # Create tree widget
        self.tree_widget = LayersTreeWidget()
        main_layout.addWidget(self.tree_widget)
        
        self.setWidget(main_widget)
        
        # Connect signals
        self._connect_signals()
        
        # Setup context menu
        self.tree_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree_widget.customContextMenuRequested.connect(self._show_context_menu)
    
    def _connect_signals(self):
        """Connect internal signals."""
        # Sync opacity slider and spinbox
        self.opacity_slider.valueChanged.connect(self._on_opacity_slider_changed)
        self.opacity_spinbox.valueChanged.connect(self._on_opacity_spinbox_changed)
        
        # Button actions
        self.delete_button.clicked.connect(self._delete_selected)
        self.duplicate_button.clicked.connect(self._duplicate_selected)
        
        # Selection change to update opacity
        self.tree_widget.itemSelectionChanged.connect(self._on_layers_selection_changed)
        
        # Connect visibility and lock changes to canvas updates
        self.tree_widget.itemVisibilityChanged.connect(self._on_visibility_changed)
        self.tree_widget.itemLockChanged.connect(self._on_lock_changed)
        self.tree_widget.itemNameChanged.connect(self._on_name_changed)
    
    def _on_opacity_slider_changed(self, value):
        """Handle opacity slider change."""
        self.opacity_spinbox.blockSignals(True)
        self.opacity_spinbox.setValue(value)
        self.opacity_spinbox.blockSignals(False)
        self._apply_opacity_to_selected(value)
    
    def _on_opacity_spinbox_changed(self, value):
        """Handle opacity spinbox change."""
        self.opacity_slider.blockSignals(True)
        self.opacity_slider.setValue(value)
        self.opacity_slider.blockSignals(False)
        self._apply_opacity_to_selected(value)
    
    def set_opacity_ui(self, value):
        """Set opacity UI and item data without triggering signals (for external sync).
        
        Args:
            value: Opacity value (0-100 as integer percentage)
        """
        self.opacity_slider.blockSignals(True)
        self.opacity_spinbox.blockSignals(True)
        self.opacity_slider.setValue(value)
        self.opacity_spinbox.setValue(value)
        self.opacity_slider.blockSignals(False)
        self.opacity_spinbox.blockSignals(False)
        
        # Also update the stored opacity value in selected tree items
        selected = self.tree_widget.selectedItems()
        for item in selected:
            item.setData(0, Qt.ItemDataRole.UserRole + 13, value)
    
    def _apply_opacity_to_selected(self, value):
        """Apply opacity to selected layers."""
        selected = self.tree_widget.selectedItems()
        for item in selected:
            item.setData(0, Qt.ItemDataRole.UserRole + 13, value)
        self.opacityChanged.emit(value)
    
    def _update_previews(self):
        """Update previews for items that have changed."""
        for item_id in list(self.items_needing_preview_update):
            # Find tree item by stored item id
            tree_item = self.object_to_item_map.get(item_id)
            if tree_item:
                # Get canvas object from reverse mapping
                canvas_obj = self.item_to_object_map.get(id(tree_item))
                if canvas_obj:
                    self.tree_widget.set_object_preview(tree_item, canvas_obj)
        self.items_needing_preview_update.clear()
    
    def mark_item_for_preview_update(self, item):
        """Mark an item to have its preview updated."""
        self.items_needing_preview_update.add(id(item))
        if not self.preview_update_timer.isActive():
            self.preview_update_timer.start()
    
    def refresh_preview(self, canvas_obj):
        """
        Refresh the preview of a specific canvas object.
        
        Args:
            canvas_obj: The canvas object whose preview should be refreshed
        """
        item = self.object_to_item_map.get(id(canvas_obj))
        if item:
            self.tree_widget.set_object_preview(item, canvas_obj)
    
    def _on_layers_selection_changed(self):
        """Handle layers panel selection change - sync to canvas selection."""
        if self._syncing or not self.current_canvas:
            return
        
        self._syncing = True
        try:
            selected_items = self.tree_widget.selectedItems()
            
            # Get the corresponding canvas objects
            objects_to_select = []
            for item in selected_items:
                obj = self.item_to_object_map.get(id(item))
                if obj:
                    objects_to_select.append(obj)
            
            # Clear current selection and select the new objects
            self.current_canvas.scene.clearSelection()
            for obj in objects_to_select:
                obj.setSelected(True)
            
            # Update the previously selected objects tracking to match current selection
            self.previously_selected_objects = {id(obj) for obj in objects_to_select}
            
            # Update opacity display
            if selected_items:
                opacity = selected_items[0].data(0, Qt.ItemDataRole.UserRole + 13)
                if opacity is None:
                    opacity = 100
                self.opacity_slider.blockSignals(True)
                self.opacity_spinbox.blockSignals(True)
                self.opacity_slider.setValue(opacity)
                self.opacity_spinbox.setValue(opacity)
                self.opacity_slider.blockSignals(False)
                self.opacity_spinbox.blockSignals(False)
        finally:
            self._syncing = False
    
    def _on_visibility_changed(self, item, is_visible):
        """Handle visibility change - update canvas object and propagate to group children."""
        if self._updating_canvas:
            return
        
        self._updating_canvas = True
        try:
            # Update the canvas object for this item
            canvas_obj = self.item_to_object_map.get(id(item))
            if canvas_obj:
                canvas_obj.setVisible(is_visible)
            
            # Check if this is a group and propagate to children
            is_group = item.data(0, Qt.ItemDataRole.UserRole + 12) == 'group'
            if is_group:
                self._apply_visibility_to_children(item, is_visible)
        finally:
            self._updating_canvas = False
    
    def _apply_visibility_to_children(self, group_item, is_visible):
        """Recursively apply visibility to all child items."""
        for i in range(group_item.childCount()):
            child_item = group_item.child(i)
            # Update the child's visibility state
            child_item.setData(0, Qt.ItemDataRole.UserRole + 10, is_visible)
            self.tree_widget._update_visibility_icon(child_item, is_visible)
            
            # Update canvas object
            canvas_obj = self.item_to_object_map.get(id(child_item))
            if canvas_obj:
                canvas_obj.setVisible(is_visible)
            
            # Recursively apply to nested groups
            child_is_group = child_item.data(0, Qt.ItemDataRole.UserRole + 12) == 'group'
            if child_is_group:
                self._apply_visibility_to_children(child_item, is_visible)
    
    def _on_lock_changed(self, item, is_locked):
        """Handle lock change - update canvas object flags and propagate to group children."""
        if self._updating_canvas:
            return
        
        self._updating_canvas = True
        try:
            # Update the canvas object for this item
            canvas_obj = self.item_to_object_map.get(id(item))
            if canvas_obj:
                self._set_object_locked(canvas_obj, is_locked)
            
            # Check if this is a group and propagate to children
            is_group = item.data(0, Qt.ItemDataRole.UserRole + 12) == 'group'
            if is_group:
                self._apply_lock_to_children(item, is_locked)
        finally:
            self._updating_canvas = False
    
    def _on_name_changed(self, item, new_name):
        """Handle layer name change - update canvas object name."""
        canvas_obj = self.item_to_object_map.get(id(item))
        if canvas_obj:
            # Update the canvas object's name property
            if hasattr(canvas_obj, 'name'):
                canvas_obj.name = new_name
            # Also try to update via data dictionary if available
            obj_data = canvas_obj.data(Qt.ItemDataRole.UserRole)
            if obj_data and isinstance(obj_data, dict):
                obj_data['name'] = new_name
    
    def _set_object_locked(self, canvas_obj, is_locked):
        """Set locked state on a canvas object."""
        if is_locked:
            # Remove selection, movement, and resizing capabilities
            flags = canvas_obj.flags()
            flags &= ~QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            flags &= ~QGraphicsItem.GraphicsItemFlag.ItemIsMovable
            canvas_obj.setFlags(flags)
            canvas_obj.setSelected(False)  # Deselect if currently selected
        else:
            # Restore selection, movement, and resizing capabilities
            flags = canvas_obj.flags()
            flags |= QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            flags |= QGraphicsItem.GraphicsItemFlag.ItemIsMovable
            canvas_obj.setFlags(flags)
    
    def _apply_lock_to_children(self, group_item, is_locked):
        """Recursively apply lock state to all child items."""
        for i in range(group_item.childCount()):
            child_item = group_item.child(i)
            # Update the child's lock state
            child_item.setData(0, Qt.ItemDataRole.UserRole + 11, is_locked)
            self.tree_widget._update_lock_icon(child_item, is_locked)
            
            # Update canvas object
            canvas_obj = self.item_to_object_map.get(id(child_item))
            if canvas_obj:
                self._set_object_locked(canvas_obj, is_locked)
            
            # Recursively apply to nested groups
            child_is_group = child_item.data(0, Qt.ItemDataRole.UserRole + 12) == 'group'
            if child_is_group:
                self._apply_lock_to_children(child_item, is_locked)
    
    def sync_canvas_selection(self, selected_objects, deselected_objects):
        """Sync canvas selection to layers panel. Called from canvas."""
        if self._syncing:
            return
        
        self._syncing = True
        try:
            # Convert to set for comparison (using object id)
            current_selected_ids = {id(obj) for obj in selected_objects}
            previous_selected_ids = self.previously_selected_objects
            
            # Calculate actually deselected items (were selected before, not selected now)
            actually_deselected_ids = previous_selected_ids - current_selected_ids
            
            # Deselect items that were previously selected but are no longer selected
            for obj_id in actually_deselected_ids:
                item = self.object_to_item_map.get(obj_id)
                if item:
                    item.setSelected(False)
            
            # Select items corresponding to currently selected objects
            for obj in selected_objects:
                item = self.object_to_item_map.get(id(obj))
                if item:
                    item.setSelected(True)
            
            # Update the previous selection tracking
            self.previously_selected_objects = current_selected_ids
        finally:
            self._syncing = False
    
    def _on_selection_changed(self):
        """Handle selection change to update opacity display."""
        selected = self.tree_widget.selectedItems()
        if selected:
            # Get opacity of first selected item
            opacity = selected[0].data(0, Qt.ItemDataRole.UserRole + 13)
            if opacity is None:
                opacity = 100
            self.opacity_slider.blockSignals(True)
            self.opacity_spinbox.blockSignals(True)
            self.opacity_slider.setValue(opacity)
            self.opacity_spinbox.setValue(opacity)
            self.opacity_slider.blockSignals(False)
            self.opacity_spinbox.blockSignals(False)
    
    def _delete_selected(self):
        """Delete selected layers and their corresponding canvas objects."""
        selected = self.tree_widget.selectedItems()
        for item in selected:
            # Get and delete the canvas object first
            canvas_obj = self.item_to_object_map.get(id(item))
            if canvas_obj and self.current_canvas:
                # Remove from mappings
                obj_id = id(canvas_obj)
                if obj_id in self.object_to_item_map:
                    del self.object_to_item_map[obj_id]
                if id(item) in self.item_to_object_map:
                    del self.item_to_object_map[id(item)]
                # Delete from canvas
                self.current_canvas.delete_graphic_object(canvas_obj)
            
            self.layerDeleted.emit(item)
            parent = item.parent()
            if parent:
                parent.removeChild(item)
            else:
                index = self.tree_widget.indexOfTopLevelItem(item)
                if index >= 0:
                    self.tree_widget.takeTopLevelItem(index)
    
    def _duplicate_selected(self):
        """Duplicate selected layers and their corresponding canvas objects."""
        selected = self.tree_widget.selectedItems()
        for item in selected:
            # Get and duplicate the canvas object
            canvas_obj = self.item_to_object_map.get(id(item))
            if canvas_obj and self.current_canvas:
                # Duplicate on canvas - this will emit graphics_item_added which adds to layers
                new_obj = self.current_canvas.duplicate_graphic_object(canvas_obj)
                if new_obj:
                    self.layerDuplicated.emit(item)
            else:
                # No canvas object, just duplicate the tree item
                self._duplicate_item(item)
                self.layerDuplicated.emit(item)
    
    def _duplicate_item(self, item):
        """Duplicate a single item."""
        parent = item.parent()
        new_name = item.text(3) + " Copy"
        
        # Create new item
        new_item = self.tree_widget.add_layer_item(
            parent, 
            new_name,
            is_group=item.data(0, Qt.ItemDataRole.UserRole + 12) == 'group'
        )
        
        # Copy visibility and lock states
        new_item.setData(0, Qt.ItemDataRole.UserRole + 10, item.data(0, Qt.ItemDataRole.UserRole + 10))
        new_item.setData(0, Qt.ItemDataRole.UserRole + 11, item.data(0, Qt.ItemDataRole.UserRole + 11))
        new_item.setData(0, Qt.ItemDataRole.UserRole + 13, item.data(0, Qt.ItemDataRole.UserRole + 13))
        
        # Update icons
        self.tree_widget._update_visibility_icon(new_item, item.data(0, Qt.ItemDataRole.UserRole + 10))
        self.tree_widget._update_lock_icon(new_item, item.data(0, Qt.ItemDataRole.UserRole + 11))
        
        return new_item
    
    def _show_context_menu(self, position):
        """Show context menu for layer items."""
        item = self.tree_widget.itemAt(position)
        
        menu = QMenu()
        
        if item:
            # Actions for selected item
            duplicate_action = menu.addAction(IconService.get_icon('edit-duplicate'), "Duplicate")
            duplicate_action.triggered.connect(self._duplicate_selected)
            
            delete_action = menu.addAction(IconService.get_icon('edit-delete'), "Delete")
            delete_action.triggered.connect(self._delete_selected)
            
            menu.addSeparator()
            
            # Visibility toggle
            is_visible = item.data(0, Qt.ItemDataRole.UserRole + 10)
            if is_visible is None:
                is_visible = True
            visibility_text = "Hide" if is_visible else "Show"
            visibility_action = menu.addAction(visibility_text)
            visibility_action.triggered.connect(lambda: self._toggle_visibility(item))
            
            # Lock toggle
            is_locked = item.data(0, Qt.ItemDataRole.UserRole + 11)
            if is_locked is None:
                is_locked = False
            lock_text = "Unlock" if is_locked else "Lock"
            lock_action = menu.addAction(lock_text)
            lock_action.triggered.connect(lambda: self._toggle_lock(item))
            
            menu.addSeparator()
            
            # Group/Ungroup
            if item.data(0, Qt.ItemDataRole.UserRole + 12) == 'group':
                ungroup_action = menu.addAction("Ungroup")
                ungroup_action.triggered.connect(lambda: self._ungroup_item(item))
            else:
                group_action = menu.addAction("Group Selected")
                group_action.triggered.connect(self._group_selected)
        else:
            # Actions when clicking on empty area
            group_action = menu.addAction("Group Selected")
            group_action.triggered.connect(self._group_selected)
        
        if menu.actions():
            menu.exec(self.tree_widget.viewport().mapToGlobal(position))
    
    def _toggle_visibility(self, item):
        """Toggle visibility of an item."""
        is_visible = item.data(0, Qt.ItemDataRole.UserRole + 10)
        if is_visible is None:
            is_visible = True
        new_state = not is_visible
        item.setData(0, Qt.ItemDataRole.UserRole + 10, new_state)
        self.tree_widget._update_visibility_icon(item, new_state)
        self.tree_widget.itemVisibilityChanged.emit(item, new_state)
    
    def _toggle_lock(self, item):
        """Toggle lock of an item."""
        is_locked = item.data(0, Qt.ItemDataRole.UserRole + 11)
        if is_locked is None:
            is_locked = False
        new_state = not is_locked
        item.setData(0, Qt.ItemDataRole.UserRole + 11, new_state)
        self.tree_widget._update_lock_icon(item, new_state)
        self.tree_widget.itemLockChanged.emit(item, new_state)
    
    def _group_selected(self):
        """Group selected items into a new group."""
        selected = self.tree_widget.selectedItems()
        if len(selected) < 1:
            return
        
        # Create new group
        group_item = self.tree_widget.add_layer_item(None, "Group", is_group=True)
        
        # Move selected items to group
        for item in selected:
            parent = item.parent()
            if parent:
                parent.removeChild(item)
            else:
                index = self.tree_widget.indexOfTopLevelItem(item)
                if index >= 0:
                    self.tree_widget.takeTopLevelItem(index)
            group_item.addChild(item)
        
        group_item.setExpanded(True)
    
    def _ungroup_item(self, group_item):
        """Ungroup a group item."""
        if group_item.data(0, Qt.ItemDataRole.UserRole + 12) != 'group':
            return
        
        parent = group_item.parent()
        
        # Move children out of group
        while group_item.childCount() > 0:
            child = group_item.takeChild(0)
            if parent:
                parent.addChild(child)
            else:
                index = self.tree_widget.indexOfTopLevelItem(group_item)
                self.tree_widget.insertTopLevelItem(index, child)
        
        # Remove empty group
        if parent:
            parent.removeChild(group_item)
        else:
            index = self.tree_widget.indexOfTopLevelItem(group_item)
            if index >= 0:
                self.tree_widget.takeTopLevelItem(index)
    
    def clear_layers(self):
        """Clear all layers from the tree."""
        self.tree_widget.clear()
    
    def add_layer(self, name, parent=None, is_group=False):
        """
        Add a new layer to the tree.
        
        Args:
            name: Layer name
            parent: Parent item or None for top level
            is_group: Whether this is a group layer
            
        Returns:
            The created QTreeWidgetItem
        """
        return self.tree_widget.add_layer_item(parent, name, is_group=is_group)
    
    def get_selected_layers(self):
        """Get list of selected layer items."""
        return self.tree_widget.selectedItems()
    
    def populate_from_screen(self, screen_objects):
        """
        Populate layers from screen objects.
        
        Args:
            screen_objects: List of graphic objects from the screen
        """
        self.clear_layers()
        
        # Build layer tree from screen objects
        for obj in screen_objects:
            name = getattr(obj, 'name', 'Object')
            is_group = hasattr(obj, 'childItems') and len(obj.childItems()) > 0
            obj_id = getattr(obj, 'id', id(obj))
            item = self.tree_widget.add_layer_item(None, name, is_group=is_group, canvas_obj=obj, object_id=obj_id)
            
            # Store bidirectional mapping
            self.object_to_item_map[id(obj)] = item
            self.item_to_object_map[id(item)] = obj
    
    def add_canvas_object(self, canvas_obj, obj_data):
        """
        Add a canvas object as a layer. Called when object is created.
        
        Args:
            canvas_obj: The BaseGraphicObject from canvas
            obj_data: The data dictionary of the object
        """
        # Get name from object type
        obj_type = obj_data.get('type', 'Object')
        obj_name = obj_data.get('name', f"{obj_type.capitalize()}")
        obj_id = obj_data.get('id', id(canvas_obj))
        
        # Add as a layer with live preview
        item = self.tree_widget.add_layer_item(None, obj_name, is_group=False, canvas_obj=canvas_obj, object_id=obj_id)
        
        # Store the actual canvas object's opacity in the tree item
        opacity_value = int(canvas_obj.opacity() * 100) if hasattr(canvas_obj, 'opacity') else 100
        item.setData(0, Qt.ItemDataRole.UserRole + 13, opacity_value)
        
        # Store bidirectional mapping
        self.object_to_item_map[id(canvas_obj)] = item
        self.item_to_object_map[id(item)] = canvas_obj
    
    def remove_canvas_object(self, canvas_obj):
        """Remove a canvas object from layers."""
        item = self.object_to_item_map.pop(id(canvas_obj), None)
        if item:
            # Remove from item map
            self.item_to_object_map.pop(id(item), None)
            # Remove from tree
            parent = item.parent()
            if parent:
                parent.removeChild(item)
            else:
                index = self.tree_widget.indexOfTopLevelItem(item)
                if index >= 0:
                    self.tree_widget.takeTopLevelItem(index)
    
    def set_current_canvas(self, canvas):
        """
        Set the current canvas and sync its objects to layers.
        
        Args:
            canvas: The CanvasBaseScreen object
        """
        self.current_canvas = canvas
        self.clear_layers()
        self.object_to_item_map.clear()
        self.item_to_object_map.clear()
        self.previously_selected_objects.clear()  # Reset selection tracking
        
        if canvas:
            # Add all current objects from the canvas
            for item in canvas.scene.items():
                if isinstance(item, BaseGraphicObject):
                    obj_data = item.data(Qt.ItemDataRole.UserRole)
                    if obj_data:
                        self.add_canvas_object(item, obj_data)
