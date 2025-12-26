# screen\base\canvas_base_screen.py
from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsWidget, QLabel, QGraphicsItem, QGraphicsSimpleTextItem
from PySide6.QtGui import QPainter, QColor, QBrush, QLinearGradient, QPixmap, QPen, QFont, QUndoStack
from PySide6.QtCore import Qt, QRectF, Signal, QPointF, QLineF
from styles import colors

from screen.base.base_graphic_object import RectangleObject, EllipseObject, BaseGraphicObject
from services.edit_service import EditService, ClipboardDataType
from services.undo_commands import (
    AddItemCommand, RemoveItemCommand, MoveItemsCommand, 
    PasteItemsCommand, DuplicateItemsCommand, ZOrderCommand
)
from debug_utils import get_logger
import uuid
import copy
from main_window.toolbars.transform_handler import TransformHandler, AverageTransformHandler

logger = get_logger(__name__)


class CanvasWidget(QGraphicsWidget):
    """
    A QGraphicsWidget that represents the actual content of the screen.
    This widget handles the drawing of the background and any content on the screen.
    """
    def __init__(self, screen_data, project_service, view_service):
        super().__init__()
        self.screen_data = screen_data
        self.project_service = project_service
        self.view_service = view_service
        self.snap_lines = []
        
        width, height = self._get_dimensions()
        self.setGeometry(0, 0, width, height)
        self.update_background()

    def _get_dimensions(self):
        """Determines the correct dimensions for the screen canvas."""
        # Priority 1: Individual screen design settings for base screens
        if self.screen_data.get("type") == "base" and self.screen_data.get("design"):
            design = self.screen_data["design"]
            if "width" in design and "height" in design:
                return design["width"], design["height"]
        
        # Priority 2: Project-wide screen design template for base screens
        if self.screen_data.get("type") == "base" and self.project_service:
            template = self.project_service.get_screen_design_template()
            if template and "width" in template and "height" in template:
                return template["width"], template["height"]
        
        # Priority 3: Fallback to data stored on the screen itself (e.g., for window screens)
        if "width" in self.screen_data and "height" in self.screen_data:
            return self.screen_data["width"], self.screen_data["height"]
            
        # Final fallback
        return 1920, 1080

    def update_background(self):
        """Updates the background based on the screen's design data."""
        self.update()  # Trigger a repaint

    def paint(self, painter, option, widget=None):
        """Paint the background and content of the screen."""
        # Determine which design data to use for the background
        design_data = self.screen_data.get("design")
        if not design_data and self.project_service and self.screen_data.get("type") == "base":
             # If no individual design on a base screen, use the project template for background
             design_data = self.project_service.get_screen_design_template()

        rect = self.boundingRect()

        # Default background
        painter.fillRect(rect, QColor(colors.COLOR_GRID_BACKGROUND))

        if design_data:
            style_type = design_data.get("type")
            
            if style_type == "color":
                color = QColor(design_data.get("color", colors.COLOR_DEFAULT_SHAPE_FILL_LIGHT))
                painter.fillRect(rect, color)
            
            elif style_type == "gradient":
                grad_data = design_data.get("gradient")
                if grad_data:
                    gradient = QLinearGradient(0, 0, rect.width(), rect.height())
                    gradient.setColorAt(0, QColor(grad_data['color1']))
                    gradient.setColorAt(1, QColor(grad_data['color2']))
                    painter.fillRect(rect, QBrush(gradient))

            elif style_type == "pattern":
                patt_data = design_data.get("pattern")
                if patt_data:
                    fg_color = QColor(patt_data["fg_color"])
                    bg_color = QColor(patt_data["bg_color"])
                    painter.fillRect(rect, bg_color)
                    brush = QBrush(fg_color, patt_data["pattern"])
                    painter.fillRect(rect, brush)
            
            elif style_type == "image":
                path = design_data.get("image_path")
                if path:
                    pixmap = QPixmap(path)
                    if not pixmap.isNull():
                        scaled_pixmap = pixmap.scaled(rect.size().toSize(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                        x = rect.x() + (rect.width() - scaled_pixmap.width()) / 2
                        y = rect.y() + (rect.height() - scaled_pixmap.height()) / 2
                        painter.drawPixmap(int(x), int(y), scaled_pixmap)

        if self.view_service.snapping_mode == 'grid':
            self.draw_grid(painter)
        elif self.view_service.snapping_mode == 'object':
            self.draw_snap_lines(painter)

    def draw_grid(self, painter):
        """Draws a grid on the canvas if snapping is enabled."""
        if not self.view_service.snap_enabled:
            return

        grid_size = self.view_service.grid_size
        if grid_size <= 1:  # Don't draw if grid is too small
            return

        rect = self.boundingRect()
        width = rect.width()
        height = rect.height()

        grid_color = QColor(Qt.GlobalColor.darkGray)
        grid_color.setAlpha(50)
        pen = QPen(grid_color, 0.5)
        painter.setPen(pen)

        # Draw vertical lines
        x = float(grid_size)
        while x < width:
            painter.drawLine(int(x), 0, int(x), int(height))
            x += grid_size

        # Draw horizontal lines
        y = float(grid_size)
        while y < height:
            painter.drawLine(0, int(y), int(width), int(y))
            y += grid_size

    def draw_snap_lines(self, painter):
        """Draws the currently active snap lines."""
        pen = QPen(Qt.GlobalColor.red, 1, Qt.PenStyle.DashLine)
        painter.setPen(pen)
        for line in self.snap_lines:
            painter.drawLine(line)

            
class CanvasBaseScreen(QGraphicsView):
    """
    A QGraphicsView that acts as a container for a screen, providing zoom, pan, and drawing functionality.
    """
    zoom_changed = Signal(float)
    mouse_moved = Signal(QPointF)
    tool_reset = Signal() # Signal emitted when tool is reset to select mode via ESC
    object_data_changed = Signal(dict)  # Emits dict with {'position': (x, y), 'size': (w, h)} when object is moved/resized
    graphics_item_added = Signal(object, dict)  # Emitted when a graphics item is added (item, data_dict)
    graphics_item_removed = Signal(object)  # Emitted when a graphics item is removed
    canvas_selection_changed = Signal(list, list)  # Emitted when canvas items selected/deselected (selected_items, deselected_items)

    def __init__(self, screen_data, project_service, view_service, parent=None):
        super().__init__(parent)
        self.screen_data = screen_data
        self.project_service = project_service
        self.view_service = view_service
        self.zoom_factor = 1.0
        self._initial_fit_done = False
        self.current_tool = None # The active drawing/editing tool
        self.transform_handler = None # The resizing/rotating handler
        self.snapping_threshold = 5
        self._previous_selection = set()  # Track previous selection for deselection detection

        # Visibility Flags
        self.show_tags = True
        self.show_object_id = True
        self.show_transform_lines = True
        self.show_click_area = True # Click area is essentially the bounding rect visual

        # Initialize undo stack and edit service
        self.edit_service = EditService()
        self.undo_stack = QUndoStack(self)
        
        # Generate unique ID for this canvas's undo stack
        screen_type = screen_data.get('type', 'base')
        screen_number = screen_data.get('number', 0)
        self._stack_id = f"canvas_{screen_type}_{screen_number}"
        
        # Register with EditService
        self.edit_service.register_undo_stack(self._stack_id, self.undo_stack)

        # Create a scene and the canvas widget
        self.scene = QGraphicsScene(self)
        self.scene.selectionChanged.connect(self.on_selection_changed)
        
        self.canvas_widget = CanvasWidget(self.screen_data, self.project_service, self.view_service)
        self.scene.addItem(self.canvas_widget)
        self.setScene(self.scene)
        
        # Configure the view
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag) # Default drag mode
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setMouseTracking(True)
        
        # Transform interaction state
        self._resizing_handle = None
        
        # Connect to view service for live updates
        self.view_service.snap_changed.connect(lambda: self.canvas_widget.update())
        self.view_service.grid_size_changed.connect(lambda: self.canvas_widget.update())
        self.view_service.snapping_mode_changed.connect(lambda: self.canvas_widget.update())

        # Restore items from screen data
        self._restore_items()

    def _restore_items(self):
        """Restores graphical items from the screen data."""
        if 'items' in self.screen_data:
            for item_data in self.screen_data['items']:
                # Pass is_restoring=True to prevent signal emission during restore
                self.create_graphic_item_from_data(item_data, is_restoring=True)

    def save_items(self):
        """Saves current graphical items to screen data."""
        logger.debug("Saving items to screen data.")
        items_list = []
        try:
            for item in self.scene.items():
                if not isinstance(item, BaseGraphicObject):
                    continue

                item_data = item.data(Qt.ItemDataRole.UserRole)
                if item_data:
                    rect = item.boundingRect()
                    item_data['rect'] = [rect.x(), rect.y(), rect.width(), rect.height()]
                    item_data['pos'] = [item.pos().x(), item.pos().y()]
                    items_list.append(item_data)

            self.screen_data['items'] = items_list
            logger.debug(f"Saved {len(items_list)} items.")
            self.project_service.mark_as_unsaved()
        except Exception as e:
            logger.error(f"CRITICAL: Error saving items: {e}", exc_info=True)

    def create_graphic_item_from_data(self, data, is_restoring=False):
        """Factory method to recreate an item from its dictionary representation.
        
        Args:
            data: Dictionary with item properties (type, rect, pos, etc.)
            is_restoring: If True, don't emit graphics_item_added signal (used when loading saved items)
        """
        item_type = data.get('type')
        item = None
        
        rect_data = data['rect']
        rect = QRectF(rect_data[0], rect_data[1], rect_data[2], rect_data[3])
        
        if item_type == 'rectangle':
            item = RectangleObject(rect, self.view_service, self)
        elif item_type == 'ellipse':
            item = EllipseObject(rect, self.view_service, self)
        
        if item:
            pos_data = data.get('pos', [0, 0])
            item.setPos(pos_data[0], pos_data[1])
            
            # Common properties
            item.setFlags(
                QGraphicsItem.GraphicsItemFlag.ItemIsMovable |
                QGraphicsItem.GraphicsItemFlag.ItemIsSelectable |
                QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
            )
            item.setData(Qt.ItemDataRole.UserRole, data)
            
            # You might want to store/load style from `data` here
            # For now, using default style
            pen = QPen(QColor("black"), 2)
            brush = QBrush(QColor(200, 200, 200, 100))
            
            # Access the composed item to set style
            if hasattr(item, 'item'):
                item.item.setPen(pen)
                item.item.setBrush(brush)
            
            self.scene.addItem(item)
            self._add_overlays(item, data)
            
            # Only emit signal for newly created items, not restored ones
            if not is_restoring:
                self.graphics_item_added.emit(item, data)
            
        return item

    def delete_graphic_object(self, item):
        """Deletes a graphic object from the scene."""
        if isinstance(item, BaseGraphicObject) and item.scene():
            # Remove from previous selection tracking
            self._previous_selection.discard(item)
            # Emit removal signal and remove from scene
            self.graphics_item_removed.emit(item)
            self.scene.removeItem(item)
            self.clear_transform_handler()
            self.save_items()

    def duplicate_graphic_object(self, item):
        """Duplicates a graphic object on the canvas."""
        if not isinstance(item, BaseGraphicObject):
            return None
        
        item_data = item.data(Qt.ItemDataRole.UserRole)
        if not item_data:
            return None
        
        import copy
        new_data = copy.deepcopy(item_data)
        new_data['id'] = self._generate_next_id()
        
        # Offset the position slightly so the duplicate is visible
        pos = new_data.get('pos', [0, 0])
        new_data['pos'] = [pos[0] + 20, pos[1] + 20]
        
        new_item = self.create_graphic_item_from_data(new_data)
        self.save_items()
        return new_item

    def _generate_next_id(self):
        """Generates the next sequential numeric ID for an object."""
        max_id = 0
        for item in self.scene.items():
            if not isinstance(item, BaseGraphicObject):
                continue
                
            item_data = item.data(Qt.ItemDataRole.UserRole)
            if item_data and 'id' in item_data:
                try:
                    current_id = int(str(item_data['id']))
                    if current_id > max_id:
                        max_id = current_id
                except ValueError:
                    pass
        return max_id + 1

    def add_new_item(self, item_type, rect, pos):
        """Registers a newly drawn item using the factory logic with undo support."""
        new_id = self._generate_next_id()
        width = rect.width()
        height = rect.height()
        
        scene_top_left = rect.topLeft()
        
        data = {
            'id': new_id,
            'type': item_type,
            'rect': [0, 0, width, height],
            'pos': [scene_top_left.x(), scene_top_left.y()],
            'tag': ''
        }
        
        # Use AddItemCommand for undo support
        command = AddItemCommand(self, data, f"Add {item_type}")
        self.undo_stack.push(command)

    def _add_overlays(self, item, data):
        """Adds text labels for ID and Tag."""
        id_text = QGraphicsSimpleTextItem(f"ID: {data['id']}", item)
        id_text.setBrush(QBrush(Qt.GlobalColor.red))
        font = QFont()
        font.setBold(True)
        id_text.setFont(font)
        id_text.setPos(5, 0) 
        id_text.setVisible(self.show_object_id)
        id_text.setData(Qt.ItemDataRole.UserRole + 1, "overlay_id")

        if data.get('tag'):
            tag_text = QGraphicsSimpleTextItem(f"Tag: {data['tag']}", item)
            tag_text.setBrush(QBrush(Qt.GlobalColor.blue))
            tag_text.setFont(font)
            tag_text.setPos(0, -30) 
            tag_text.setVisible(self.show_tags)
            tag_text.setData(Qt.ItemDataRole.UserRole + 1, "overlay_tag")

    def toggle_overlays(self, overlay_type, visible):
        """Toggles visibility of specific overlays."""
        if overlay_type == 'tag':
            self.show_tags = visible
        elif overlay_type == 'id':
            self.show_object_id = visible
        elif overlay_type == 'transform':
            self.show_transform_lines = visible
            if self.transform_handler:
                self.transform_handler.setVisible(visible)
        elif overlay_type == 'click_area':
            self.show_click_area = visible
        
        for item in self.scene.items():
            if item.parentItem():
                tag = item.data(Qt.ItemDataRole.UserRole + 1)
                if tag == "overlay_id":
                    item.setVisible(self.show_object_id)
                elif tag == "overlay_tag":
                    item.setVisible(self.show_tags)

    def set_tool(self, tool):
        """Sets the active tool. None for selection mode."""
        self.current_tool = tool
        if self.current_tool:
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
            self.setCursor(Qt.CursorShape.CrossCursor)
            self.clear_transform_handler()
            self.scene.clearSelection()
        else:
            self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self.on_selection_changed()

    def clear_transform_handler(self):
        """Removes the current transform handler."""
        logger.debug("clear_transform_handler")
        if self.transform_handler:
            self.transform_handler.cleanup()
            self.transform_handler = None

    def on_selection_changed(self):
        """Handle selection changes to update the transform handler."""
        logger.debug("Selection changed.")
        if self.current_tool:
            logger.debug("In drawing mode, ignoring selection change.")
            return

        try:
            selected_items = self.scene.selectedItems()
            logger.debug(f"{len(selected_items)} items selected.")
            self.clear_transform_handler()
            
            # Update status bar with selected object info
            self._update_selected_object_info()


            # Filter and validate items
            valid_items = []
            for item in selected_items:
                try:
                    if isinstance(item, BaseGraphicObject) and item.scene():
                        valid_items.append(item)
                except Exception as e:
                    logger.debug(f"Error validating selected item: {e}")
            
            logger.debug(f"{len(valid_items)} valid items found.")

            if self.show_transform_lines and valid_items:
                    try:
                        if len(valid_items) == 1:
                            logger.debug("Creating TransformHandler for single item.")
                            self.transform_handler = TransformHandler(valid_items[0], self.scene, self.view_service)
                        elif len(valid_items) > 1:
                            logger.debug("Creating AverageTransformHandler for multiple items.")
                            self.transform_handler = AverageTransformHandler(valid_items, self.scene, self.view_service)
                    except Exception as e:
                        logger.error(f"CRITICAL: Error creating transform handler: {e}", exc_info=True)
                        self.transform_handler = None
            
            # Calculate deselected items by comparing with previous selection
            current_selection_set = set(valid_items)
            deselected_items = list(self._previous_selection - current_selection_set)
            newly_selected_items = list(current_selection_set - self._previous_selection)
            
            # Update previous selection for next change
            self._previous_selection = current_selection_set
            
            # Emit with actual deselected items
            self.canvas_selection_changed.emit(valid_items, deselected_items)
        except Exception as e:
            logger.error(f"CRITICAL: Error in on_selection_changed: {e}", exc_info=True)

    def _update_selected_object_info(self):
        """Emits object data changed signal with current selected object's position, size, and rotation."""
        selected_items = self.scene.selectedItems()
        valid_items = [item for item in selected_items if isinstance(item, BaseGraphicObject)]
        
        if len(valid_items) == 1:
            item = valid_items[0]
            pos = item.pos()
            rect = item.boundingRect()
            self.object_data_changed.emit({
                'position': (int(pos.x()), int(pos.y())),
                'size': (int(rect.width()), int(rect.height())),
                'rotation': item.rotation()
            })
        elif len(valid_items) == 0:
            # No selection - emit empty data
            self.object_data_changed.emit({
                'position': None,
                'size': None,
                'rotation': None
            })
        # For multiple items, we don't show position/size (ambiguous)

    def mousePressEvent(self, event):
        """Handle mouse press events."""
        scene_pos = self.mapToScene(event.pos())
        logger.debug(f"Mouse press at scene pos: {scene_pos}")
        
        if self.transform_handler and not self.current_tool:
            try:
                # Use view-based hit testing (event.pos()) for accuracy with items that ignore transformations.
                # This ensures handles (which have ItemIgnoresTransformations set) are detected correctly
                # regardless of zoom level, preventing "click-through" to objects or background.
                items_at_pos = self.items(event.pos())
                handle_name = self.transform_handler.get_handle_from_items(items_at_pos)
                
                if handle_name:
                    logger.debug(f"Activating resize handle: {handle_name}")
                    self._resizing_handle = handle_name
                    self.transform_handler.handle_mouse_press(handle_name, event.pos(), scene_pos)
                    self.setDragMode(QGraphicsView.DragMode.NoDrag)
                    event.accept()
                    return
            except Exception as e:
                logger.error(f"CRITICAL: Error in mousePressEvent with transform_handler: {e}", exc_info=True)

        if self.current_tool:
            if event.button() == Qt.MouseButton.LeftButton:
                logger.debug(f"Passing mouse press to tool: {self.current_tool.__class__.__name__}")
                self.current_tool.mouse_press(scene_pos)
                event.accept()
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Handle mouse move events."""
        scene_pos = self.mapToScene(event.pos())
        self.mouse_moved.emit(scene_pos)

        # Handle resizing via transform handler
        if self._resizing_handle and self.transform_handler:
            try:
                logger.debug(f"Passing mouse move to transform handler. Handle: {self._resizing_handle}")
                self.transform_handler.handle_mouse_move(scene_pos, event.modifiers())
                self.update_snap_lines(self.transform_handler.get_items())
                # Update status bar with current size/position during resize
                self._update_selected_object_info()

            except Exception as e:
                logger.error(f"CRITICAL: Error during handle mouse move: {e}", exc_info=True)
            event.accept()
            return

        # Handle object dragging
        if event.buttons() & Qt.MouseButton.LeftButton and self.scene.selectedItems():
            moving_items = self.scene.selectedItems()
            if moving_items:
                self.update_snap_lines(moving_items)
                # Update status bar with current position during drag
                self._update_selected_object_info()


        if self.current_tool:
            self.current_tool.mouse_move(scene_pos, event.modifiers())
            event.accept()
            return

        super().mouseMoveEvent(event)
        
        if self.transform_handler and not self._resizing_handle and not self.current_tool:
            try:
                self.transform_handler.update_geometry()
            except Exception as e:
                logger.debug(f"Error updating transform handler geometry: {e}")

    def mouseReleaseEvent(self, event):
        """Handle mouse release events."""
        scene_pos = self.mapToScene(event.pos())
        logger.debug(f"Mouse release at scene pos: {scene_pos}")
        self.clear_snap_lines()

        if self._resizing_handle:
            logger.debug(f"Finished resizing handle: {self._resizing_handle}")
            self._resizing_handle = None
            if not self.current_tool:
                self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
            self.save_items()
            # Update status bar with final size/position after resize
            self._update_selected_object_info()
            event.accept()
            return

        if self.current_tool:
            if event.button() == Qt.MouseButton.LeftButton:
                logger.debug(f"Passing mouse release to tool: {self.current_tool.__class__.__name__}")
                self.current_tool.mouse_release(scene_pos)
                
                temp_item = self.current_tool.current_item
                if temp_item:
                    rect = temp_item.rect().normalized()
                    pos = temp_item.pos()
                    item_type = temp_item.data(0)
                    
                    self.scene.removeItem(temp_item)
                    
                    if item_type:
                        self.add_new_item(item_type, rect, pos)
                
                event.accept()
            return

        super().mouseReleaseEvent(event)
        
        # Always save after a potential modification
        logger.debug("Saving items after mouse release.")
        self.save_items()
        if self.transform_handler:
            self.transform_handler.update_geometry()
            
    def update_snap_lines(self, moving_items):
        """Calculates and displays snap lines by comparing moving items to static items."""
        if not self.view_service.snap_enabled or self.view_service.snapping_mode != 'object':
            return
    
        self.canvas_widget.snap_lines = []
        
        # Bounding rect of all moving items
        moving_rect = self.get_items_bounding_rect(moving_items)
        if moving_rect.isEmpty():
            return
    
        static_items = [item for item in self.scene.items() if isinstance(item, BaseGraphicObject) and item not in moving_items]
    
        # --- Snapping logic ---
        snap_offset_x, snap_offset_y = self.calculate_snap_offsets(moving_rect, static_items)
    
        # Apply the snap offset to all moving items
        if snap_offset_x != 0 or snap_offset_y != 0:
            for item in moving_items:
                item.moveBy(snap_offset_x, snap_offset_y)

        self.canvas_widget.update()


    def calculate_snap_offsets(self, moving_rect, static_items):
        """
        Calculates the required x and y offsets to snap the moving_rect to the nearest static item.
        """
        snap_offset_x, snap_offset_y = 0, 0
        min_dist_x, min_dist_y = self.snapping_threshold, self.snapping_threshold
    
        m_left, m_right = moving_rect.left(), moving_rect.right()
        m_top, m_bottom = moving_rect.top(), moving_rect.bottom()
        m_v_center, m_h_center = moving_rect.center().y(), moving_rect.center().x()
    
        for static_item in static_items:
            static_rect = static_item.sceneBoundingRect()
    
            s_left, s_right = static_rect.left(), static_rect.right()
            s_top, s_bottom = static_rect.top(), static_rect.bottom()
            s_v_center, s_h_center = static_rect.center().y(), static_rect.center().x()
    
            # --- Vertical Snapping (X-axis) ---
            snap_pairs_x = [
                (m_left, s_left), (m_left, s_right), (m_left, s_h_center),
                (m_right, s_left), (m_right, s_right), (m_right, s_h_center),
                (m_h_center, s_left), (m_h_center, s_right), (m_h_center, s_h_center)
            ]
            for m_edge, s_edge in snap_pairs_x:
                dist = s_edge - m_edge
                if abs(dist) < min_dist_x:
                    min_dist_x = abs(dist)
                    snap_offset_x = dist
                    self.canvas_widget.snap_lines.append(QLineF(s_edge, self.canvas_widget.boundingRect().top(), s_edge, self.canvas_widget.boundingRect().bottom()))

            # --- Horizontal Snapping (Y-axis) ---
            snap_pairs_y = [
                (m_top, s_top), (m_top, s_bottom), (m_top, s_v_center),
                (m_bottom, s_top), (m_bottom, s_bottom), (m_bottom, s_v_center),
                (m_v_center, s_top), (m_v_center, s_bottom), (m_v_center, s_v_center)
            ]
            for m_edge, s_edge in snap_pairs_y:
                dist = s_edge - m_edge
                if abs(dist) < min_dist_y:
                    min_dist_y = abs(dist)
                    snap_offset_y = dist
                    self.canvas_widget.snap_lines.append(QLineF(self.canvas_widget.boundingRect().left(), s_edge, self.canvas_widget.boundingRect().right(), s_edge))

        # If a snap occurred, we only want the closest one, not both X and Y.
        if abs(snap_offset_x) < abs(snap_offset_y) and abs(snap_offset_x) > 0:
            snap_offset_y = 0
        elif abs(snap_offset_y) < abs(snap_offset_x) and abs(snap_offset_y) > 0:
            snap_offset_x = 0
            
        return snap_offset_x, snap_offset_y


    def get_items_bounding_rect(self, items):
        """Returns the total bounding rect for a list of items."""
        if not items:
            return QRectF()
        
        total_rect = items[0].sceneBoundingRect()
        for i in range(1, len(items)):
            total_rect = total_rect.united(items[i].sceneBoundingRect())
        return total_rect

    def clear_snap_lines(self):
        """Clears any visible snap lines."""
        if self.canvas_widget.snap_lines:
            self.canvas_widget.snap_lines = []
            self.canvas_widget.update()

    def showEvent(self, event):
        """Handle the event when the view is shown, to perform initial fit."""
        if not self._initial_fit_done:
            self.fit_screen()
            self._initial_fit_done = True
        super().showEvent(event)

    def wheelEvent(self, event):
        """Handle mouse wheel events for zooming."""
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                self.zoom_in()
            else:
                self.zoom_out()
            event.accept()
        else:
            super().wheelEvent(event)

    def keyPressEvent(self, event):
        """Handle key press events for zooming and panning."""
        if event.key() == Qt.Key.Key_Escape:
            if self.current_tool:
                self.set_tool(None)
                self.tool_reset.emit()
            event.accept()
            return

        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            if event.key() == Qt.Key.Key_Plus or event.key() == Qt.Key.Key_Equal:
                self.zoom_in()
                event.accept()
            elif event.key() == Qt.Key.Key_Minus:
                self.zoom_out()
                event.accept()
            elif event.key() == Qt.Key.Key_0:
                self.fit_screen()
                event.accept()
            else:
                super().keyPressEvent(event)
        elif event.key() == Qt.Key.Key_Space:
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            event.accept()
        elif event.key() == Qt.Key.Key_Delete:
            # Use the centralized delete method with undo support
            self.delete()
            event.accept()
        else:
            super().keyPressEvent(event)
            
    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key.Key_Space:
            if not self.current_tool:
                self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
            else:
                self.setDragMode(QGraphicsView.DragMode.NoDrag)
        else:
            super().keyReleaseEvent(event)

    def zoom(self, factor):
        """Apply a zoom factor to the view, respecting min/max limits."""
        new_zoom_factor = self.zoom_factor * factor
        
        if 0.1 <= new_zoom_factor <= 10.0:
            self.zoom_factor = new_zoom_factor
            self.resetTransform()
            self.scale(self.zoom_factor, self.zoom_factor)
            self.zoom_changed.emit(self.zoom_factor)

    def zoom_in(self):
        """Zoom in by a predefined factor."""
        self.zoom(1.1)

    def zoom_out(self):
        """Zoom out by a predefined factor."""
        self.zoom(0.9)
        
    def set_zoom_level(self, level_str):
        """Set zoom to a specific percentage (e.g., "100%"), respecting limits."""
        try:
            level = float(level_str.strip('%')) / 100.0
            clamped_level = max(0.1, min(level, 10.0))
            
            if self.zoom_factor != clamped_level:
                self.zoom_factor = clamped_level
                self.resetTransform()
                self.scale(self.zoom_factor, self.zoom_factor)
                self.zoom_changed.emit(self.zoom_factor)

        except ValueError as e:
            logger.error(f"Value error in zoom calculation: {e}")
        except ZeroDivisionError as e:
            logger.error(f"Division by zero in zoom calculation: {e}")

    def fit_screen(self):
        """Fit the entire screen content within the view."""
        self.fitInView(self.canvas_widget.boundingRect(), Qt.AspectRatioMode.KeepAspectRatio)
        self.zoom_factor = self.transform().m11()
        self.zoom_changed.emit(self.zoom_factor)

    # ========== Edit Operations (Cut/Copy/Paste/Delete/Undo/Redo) ==========

    def cut(self):
        """Cut selected items to clipboard."""
        selected_items = [item for item in self.scene.selectedItems() 
                         if isinstance(item, BaseGraphicObject)]
        if not selected_items:
            logger.debug("Cut: No items selected")
            return
        
        # Copy items data to clipboard
        items_data = []
        for item in selected_items:
            item_data = item.data(Qt.ItemDataRole.UserRole)
            if item_data:
                data_copy = copy.deepcopy(item_data)
                data_copy['pos'] = [item.pos().x(), item.pos().y()]
                rect = item.boundingRect()
                data_copy['rect'] = [rect.x(), rect.y(), rect.width(), rect.height()]
                items_data.append(data_copy)
        
        # Store in clipboard with cut flag
        self.edit_service.set_clipboard(items_data, ClipboardDataType.CANVAS_ITEMS, is_cut=True)
        
        # Delete items using undo command
        command = RemoveItemCommand(self, selected_items, "Cut Items")
        self.undo_stack.push(command)
        
        logger.debug(f"Cut {len(selected_items)} items")

    def copy(self):
        """Copy selected items to clipboard."""
        selected_items = [item for item in self.scene.selectedItems() 
                         if isinstance(item, BaseGraphicObject)]
        if not selected_items:
            logger.debug("Copy: No items selected")
            return
        
        # Copy items data to clipboard
        items_data = []
        for item in selected_items:
            item_data = item.data(Qt.ItemDataRole.UserRole)
            if item_data:
                data_copy = copy.deepcopy(item_data)
                data_copy['pos'] = [item.pos().x(), item.pos().y()]
                rect = item.boundingRect()
                data_copy['rect'] = [rect.x(), rect.y(), rect.width(), rect.height()]
                items_data.append(data_copy)
        
        # Store in clipboard (not a cut operation)
        self.edit_service.set_clipboard(items_data, ClipboardDataType.CANVAS_ITEMS, is_cut=False)
        
        logger.debug(f"Copied {len(selected_items)} items")

    def paste(self):
        """Paste items from clipboard."""
        clipboard_data, data_type, is_cut = self.edit_service.get_clipboard()
        
        if data_type != ClipboardDataType.CANVAS_ITEMS or not clipboard_data:
            logger.debug("Paste: No canvas items in clipboard")
            return
        
        # Use paste command for undo support
        command = PasteItemsCommand(self, clipboard_data, QPointF(20, 20), "Paste Items")
        self.undo_stack.push(command)
        
        # If this was a cut operation, mark it as completed so subsequent pastes don't re-delete
        if is_cut:
            self.edit_service.mark_cut_completed()
        
        logger.debug(f"Pasted {len(clipboard_data)} items")

    def delete(self):
        """Delete selected items."""
        selected_items = [item for item in self.scene.selectedItems() 
                         if isinstance(item, BaseGraphicObject)]
        if not selected_items:
            logger.debug("Delete: No items selected")
            return
        
        # Use remove command for undo support
        command = RemoveItemCommand(self, selected_items, "Delete Items")
        self.undo_stack.push(command)
        
        logger.debug(f"Deleted {len(selected_items)} items")

    def duplicate(self):
        """Duplicate selected items with offset."""
        selected_items = [item for item in self.scene.selectedItems() 
                         if isinstance(item, BaseGraphicObject)]
        if not selected_items:
            logger.debug("Duplicate: No items selected")
            return
        
        # Use duplicate command for undo support
        command = DuplicateItemsCommand(self, selected_items, QPointF(20, 20), "Duplicate Items")
        self.undo_stack.push(command)
        
        logger.debug(f"Duplicated {len(selected_items)} items")

    def selectAll(self):
        """Select all graphic items on the canvas."""
        for item in self.scene.items():
            if isinstance(item, BaseGraphicObject):
                item.setSelected(True)
        logger.debug("Selected all items")

    def undo(self):
        """Undo the last action."""
        if self.undo_stack.canUndo():
            self.undo_stack.undo()
            logger.debug(f"Undo: {self.undo_stack.undoText()}")

    def redo(self):
        """Redo the last undone action."""
        if self.undo_stack.canRedo():
            self.undo_stack.redo()
            logger.debug(f"Redo: {self.undo_stack.redoText()}")

    def can_undo(self):
        """Returns True if undo is available."""
        return self.undo_stack.canUndo()

    def can_redo(self):
        """Returns True if redo is available."""
        return self.undo_stack.canRedo()

    # ========== Stacking Order Operations ==========

    def move_front_layer(self):
        """Move selected items one layer up (increase z-value)."""
        selected_items = [item for item in self.scene.selectedItems() 
                         if isinstance(item, BaseGraphicObject)]
        if not selected_items:
            return
        
        old_z_values = [item.zValue() for item in selected_items]
        new_z_values = [z + 1 for z in old_z_values]
        
        command = ZOrderCommand(selected_items, old_z_values, new_z_values, "Move Front Layer")
        self.undo_stack.push(command)
        self.save_items()

    def move_back_layer(self):
        """Move selected items one layer down (decrease z-value)."""
        selected_items = [item for item in self.scene.selectedItems() 
                         if isinstance(item, BaseGraphicObject)]
        if not selected_items:
            return
        
        old_z_values = [item.zValue() for item in selected_items]
        new_z_values = [z - 1 for z in old_z_values]
        
        command = ZOrderCommand(selected_items, old_z_values, new_z_values, "Move Back Layer")
        self.undo_stack.push(command)
        self.save_items()

    def move_to_front(self):
        """Move selected items to the front (highest z-value)."""
        selected_items = [item for item in self.scene.selectedItems() 
                         if isinstance(item, BaseGraphicObject)]
        if not selected_items:
            return
        
        # Find the highest z-value among all items
        max_z = 0
        for item in self.scene.items():
            if isinstance(item, BaseGraphicObject):
                max_z = max(max_z, item.zValue())
        
        old_z_values = [item.zValue() for item in selected_items]
        new_z_values = [max_z + 1 + i for i in range(len(selected_items))]
        
        command = ZOrderCommand(selected_items, old_z_values, new_z_values, "Move to Front")
        self.undo_stack.push(command)
        self.save_items()

    def move_to_back(self):
        """Move selected items to the back (lowest z-value)."""
        selected_items = [item for item in self.scene.selectedItems() 
                         if isinstance(item, BaseGraphicObject)]
        if not selected_items:
            return
        
        # Find the lowest z-value among all items
        min_z = 0
        for item in self.scene.items():
            if isinstance(item, BaseGraphicObject):
                min_z = min(min_z, item.zValue())
        
        old_z_values = [item.zValue() for item in selected_items]
        new_z_values = [min_z - len(selected_items) + i for i in range(len(selected_items))]
        
        command = ZOrderCommand(selected_items, old_z_values, new_z_values, "Move to Back")
        self.undo_stack.push(command)
        self.save_items()

    # ========== Alignment Operations ==========

    def align_items(self, alignment):
        """
        Align selected items based on alignment type.
        
        Args:
            alignment: 'left', 'center', 'right', 'top', 'middle', 'bottom'
        """
        selected_items = [item for item in self.scene.selectedItems() 
                         if isinstance(item, BaseGraphicObject)]
        if len(selected_items) < 2:
            return  # Need at least 2 items to align
        
        # Get bounding rects
        rects = [item.sceneBoundingRect() for item in selected_items]
        
        # Calculate alignment target based on first selected item (anchor)
        anchor_rect = rects[0]
        
        old_positions = [item.pos() for item in selected_items]
        new_positions = []
        
        for item, rect in zip(selected_items, rects):
            new_pos = item.pos()
            
            if alignment == 'left':
                new_pos.setX(new_pos.x() + (anchor_rect.left() - rect.left()))
            elif alignment == 'center':
                new_pos.setX(new_pos.x() + (anchor_rect.center().x() - rect.center().x()))
            elif alignment == 'right':
                new_pos.setX(new_pos.x() + (anchor_rect.right() - rect.right()))
            elif alignment == 'top':
                new_pos.setY(new_pos.y() + (anchor_rect.top() - rect.top()))
            elif alignment == 'middle':
                new_pos.setY(new_pos.y() + (anchor_rect.center().y() - rect.center().y()))
            elif alignment == 'bottom':
                new_pos.setY(new_pos.y() + (anchor_rect.bottom() - rect.bottom()))
            
            new_positions.append(new_pos)
        
        # Create move command for undo support
        command = MoveItemsCommand(selected_items, old_positions, new_positions, f"Align {alignment}")
        self.undo_stack.push(command)
        self.save_items()

    def distribute_items(self, direction):
        """
        Distribute selected items evenly.
        
        Args:
            direction: 'horizontal' or 'vertical'
        """
        selected_items = [item for item in self.scene.selectedItems() 
                         if isinstance(item, BaseGraphicObject)]
        if len(selected_items) < 3:
            return  # Need at least 3 items to distribute
        
        rects = [(item, item.sceneBoundingRect()) for item in selected_items]
        
        if direction == 'horizontal':
            # Sort by x position
            rects.sort(key=lambda x: x[1].left())
            
            # Calculate total spacing
            first_left = rects[0][1].left()
            last_right = rects[-1][1].right()
            total_width = sum(r[1].width() for _, r in rects)
            spacing = (last_right - first_left - total_width) / (len(rects) - 1)
            
            old_positions = [item.pos() for item, _ in rects]
            new_positions = []
            
            current_x = first_left
            for item, rect in rects:
                new_pos = item.pos()
                new_pos.setX(new_pos.x() + (current_x - rect.left()))
                new_positions.append(new_pos)
                current_x += rect.width() + spacing
        else:  # vertical
            # Sort by y position
            rects.sort(key=lambda x: x[1].top())
            
            first_top = rects[0][1].top()
            last_bottom = rects[-1][1].bottom()
            total_height = sum(r[1].height() for _, r in rects)
            spacing = (last_bottom - first_top - total_height) / (len(rects) - 1)
            
            old_positions = [item.pos() for item, _ in rects]
            new_positions = []
            
            current_y = first_top
            for item, rect in rects:
                new_pos = item.pos()
                new_pos.setY(new_pos.y() + (current_y - rect.top()))
                new_positions.append(new_pos)
                current_y += rect.height() + spacing
        
        items = [item for item, _ in rects]
        command = MoveItemsCommand(items, old_positions, new_positions, f"Distribute {direction}")
        self.undo_stack.push(command)
        self.save_items()

    # ========== Flip/Rotate Operations ==========

    def flip_items(self, direction):
        """
        Flip selected items.
        
        Args:
            direction: 'horizontal' or 'vertical'
        """
        selected_items = [item for item in self.scene.selectedItems() 
                         if isinstance(item, BaseGraphicObject)]
        if not selected_items:
            return
        
        # Get the center of all selected items
        combined_rect = selected_items[0].sceneBoundingRect()
        for item in selected_items[1:]:
            combined_rect = combined_rect.united(item.sceneBoundingRect())
        
        center = combined_rect.center()
        
        for item in selected_items:
            current_transform = item.transform()
            
            if direction == 'horizontal':
                # Flip horizontally (mirror across y-axis at center)
                item.setTransform(current_transform.scale(-1, 1))
                # Adjust position to keep item in place
                item_center = item.sceneBoundingRect().center()
                offset_x = 2 * (center.x() - item_center.x())
                item.moveBy(offset_x, 0)
            else:
                # Flip vertically (mirror across x-axis at center)
                item.setTransform(current_transform.scale(1, -1))
                item_center = item.sceneBoundingRect().center()
                offset_y = 2 * (center.y() - item_center.y())
                item.moveBy(0, offset_y)
        
        self.save_items()
        logger.debug(f"Flipped {len(selected_items)} items {direction}")

    def rotate_items(self, angle):
        """
        Rotate selected items by the specified angle.
        
        Args:
            angle: Rotation angle in degrees (positive = clockwise)
        """
        selected_items = [item for item in self.scene.selectedItems() 
                         if isinstance(item, BaseGraphicObject)]
        if not selected_items:
            return
        
        # Get the center of all selected items
        combined_rect = selected_items[0].sceneBoundingRect()
        for item in selected_items[1:]:
            combined_rect = combined_rect.united(item.sceneBoundingRect())
        
        center = combined_rect.center()
        
        for item in selected_items:
            # Get current rotation
            current_rotation = item.rotation()
            new_rotation = current_rotation + angle
            
            # Rotate around the combined center point
            item.setTransformOriginPoint(item.mapFromScene(center))
            item.setRotation(new_rotation)
        
        self.save_items()
        logger.debug(f"Rotated {len(selected_items)} items by {angle} degrees")

    # ========== Cleanup ==========

    def cleanup(self):
        """Clean up resources when the canvas is closed."""
        # Unregister undo stack from EditService
        self.edit_service.unregister_undo_stack(self._stack_id)
        logger.debug(f"Canvas {self._stack_id} cleaned up")