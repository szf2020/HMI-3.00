# screen\base\canvas_base_screen.py
from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsWidget, QLabel, QGraphicsItem, QGraphicsSimpleTextItem
from PySide6.QtGui import QPainter, QColor, QBrush, QLinearGradient, QPixmap, QPen, QFont, QUndoStack
from PySide6.QtCore import Qt, QRectF, Signal, QPoint, QPointF, QLineF
from styles import colors

from screen.base.base_graphic_object import RectangleObject, EllipseObject, BaseGraphicObject
from services.screen_schema import build_screen_document, validate_serialized_object
from screen.context_menu import ScreenContextMenu
from services.edit_service import EditService
from services.undo_commands import (
    AddItemCommand, RemoveItemCommand, MoveItemsCommand, 
    DuplicateItemsCommand, ZOrderCommand,
    GroupItemsCommand, UngroupItemsCommand
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
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.NoAnchor)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.NoAnchor)
        self.setMouseTracking(True)
        self._last_viewport_mouse_pos = None
        self._last_paste_anchor = None
        self._paste_count = 0
        
        # Transform interaction state
        self._resizing_handle = None

        # Explicit interaction mode flags
        self._mode_drag_move = False
        self._mode_resize_handle = False
        self._mode_tool_draw = False

        # Debug tracing for press-move-release cycles
        self._interaction_sequence = 0
        self._active_interaction_id = None
        
        # Drag/move undo tracking state
        self._drag_started = False
        self._drag_initial_positions = {}  # {item_id: QPointF}
        # Controls whether drag-resize object snapping applies position delta here.
        # Keep this True when BaseGraphicObject.itemChange handles only grid snapping.
        self._apply_object_snap_delta_during_drag = True
        
        # Connect to view service for live updates
        self.view_service.snap_changed.connect(lambda: self.canvas_widget.update())
        self.view_service.grid_size_changed.connect(lambda: self.canvas_widget.update())
        self.view_service.snapping_mode_changed.connect(lambda: self.canvas_widget.update())

        # Restore items from screen data
        self._restore_items()

    def _restore_items(self):
        """Restores graphical items from the screen data."""
        objects = self.screen_data.get('objects', self.screen_data.get('items', []))
        for item_data in objects:
                # Pass is_restoring=True to prevent signal emission during restore
                self.create_graphic_item_from_data(item_data, is_restoring=True)

    def save_items(self):
        """Saves current graphical items to screen data."""
        logger.debug("Saving items to screen data.")
        serialized_objects = []
        try:
            for item in self.scene.items():
                if not isinstance(item, BaseGraphicObject):
                    continue

                item.ensure_object_id()
                payload = item.to_json_dict()
                if validate_serialized_object(payload):
                    serialized_objects.append(payload)
                else:
                    logger.error("Skipping invalid serialized object for write.")

            document = build_screen_document(
                name=self.screen_data.get('name', 'Untitled'),
                bg_color=self.screen_data.get('background_color', '#FFFFFF'),
                width=self.screen_data.get('width', 0),
                height=self.screen_data.get('height', 0),
                objects=serialized_objects,
            )
            self.screen_data['schema_version'] = document['schema_version']
            self.screen_data['metadata'] = document['metadata']
            self.screen_data['objects'] = document['objects']
            self.screen_data['items'] = document['objects']
            logger.debug(f"Saved {len(serialized_objects)} items.")
            self.project_service.mark_as_unsaved()
        except Exception as e:
            logger.error(f"CRITICAL: Error saving items: {e}", exc_info=True)

    def create_graphic_item_from_data(self, data, is_restoring=False):
        """Factory method to recreate an item from its dictionary representation.
        
        Args:
            data: Dictionary with item properties (type, rect, pos, etc.)
            is_restoring: If True, don't emit graphics_item_added signal (used when loading saved items)
        """
        item_type = data.get('object_type', data.get('type'))
        item = None
        if 'lock_aspect_ratio' not in data:
            data['lock_aspect_ratio'] = False
        
        geometry = data.get('geometry')
        if geometry:
            rect = QRectF(0, 0, geometry.get('width', 0), geometry.get('height', 0))
        else:
            rect_data = data['rect']
            rect = QRectF(rect_data[0], rect_data[1], rect_data[2], rect_data[3])
        
        if item_type == 'rectangle':
            item = RectangleObject(rect, self.view_service, self)
            # Restore corner radii if present
            corner_radii = data.get('corner_radii', [0.0, 0.0, 0.0, 0.0])
            clamped_corner_radii = item.get_clamped_corner_radii(corner_radii)
            item.corner_radii = clamped_corner_radii
            data['corner_radii'] = clamped_corner_radii
            item.rounded_enabled = data.get('rounded_enabled', False)
        elif item_type == 'ellipse':
            item = EllipseObject(rect, self.view_service, self)
        
        if item:
            if 'geometry' in data:
                item.apply_json_dict(data)
            else:
                pos_data = data.get('pos', [0, 0])
                item.setPos(pos_data[0], pos_data[1])
            
            # Common properties
            item.setFlags(
                QGraphicsItem.GraphicsItemFlag.ItemIsMovable |
                QGraphicsItem.GraphicsItemFlag.ItemIsSelectable |
                QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
            )
            item.setData(Qt.ItemDataRole.UserRole, data)
            item.ensure_object_id()
            
            # Restore pen, brush, and other visual properties from data
            # Use stored properties if available, otherwise use defaults
            if 'pen' in data and data['pen']:
                pen = self._deserialize_pen(data['pen'])
            else:
                pen = QPen(QColor("black"), 2)
            
            if 'brush' in data and data['brush']:
                brush = self._deserialize_brush(data['brush'])
            else:
                brush = QBrush(QColor(200, 200, 200, 100))
            
            # Access the composed item to set style
            if hasattr(item, 'item'):
                item.item.setPen(pen)
                item.item.setBrush(brush)
            
            # Restore opacity, rotation, and z-value
            if 'opacity' in data:
                item.setOpacity(data['opacity'])
            if 'rotation' in data:
                item.setRotation(data['rotation'])
            if 'z_value' in data:
                item.setZValue(data['z_value'])
            
            self.scene.addItem(item)
            self._add_overlays(item, data)
            
            # Only emit signal for newly created items, not restored ones
            if not is_restoring:
                self.graphics_item_added.emit(item, data)
            
        return item

    def delete_graphic_object(self, item):
        """Deletes a graphic object from the scene."""
        if isinstance(item, BaseGraphicObject) and item.scene() == self.scene:
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

    def add_new_item(self, item_type, rect, pos, preview_item=None):
        """Registers a newly drawn item using the factory logic with undo support.
        
        Args:
            item_type: Type of item ('rectangle', 'ellipse', etc.)
            rect: QRectF for the item's bounding rect
            pos: QPointF for item position
            preview_item: Optional preview item to extract state from (e.g., for corner_radii)
        """
        new_id = self._generate_next_id()
        width = rect.width()
        height = rect.height()
        
        scene_top_left = rect.topLeft()
        
        # Prepare default pen and brush
        default_pen = QPen(QColor("black"), 2)
        default_brush = QBrush(QColor(200, 200, 200, 100))
        
        data = {
            'id': new_id,
            'type': item_type,
            'rect': [0, 0, width, height],
            'pos': [scene_top_left.x(), scene_top_left.y()],
            'tag': '',
            'corner_radii': [0.0, 0.0, 0.0, 0.0],  # [TL, TR, BR, BL]
            'rounded_enabled': False,
            'lock_aspect_ratio': False,
            'pen': self._serialize_pen(default_pen),
            'brush': self._serialize_brush(default_brush),
            'opacity': 1.0,
            'rotation': 0.0,
            'z_value': 0.0
        }
        
        # Extract state from preview item if provided
        if preview_item and item_type == 'rectangle':
            # Extract corner radii and rounded state from preview
            if hasattr(preview_item, 'corner_radii'):
                data['corner_radii'] = preview_item.corner_radii.copy()
            if hasattr(preview_item, 'rounded_enabled'):
                data['rounded_enabled'] = preview_item.rounded_enabled
        
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
            # Entering drawing mode must immediately clear selection state so that
            # status widgets and listeners don't keep stale "selected object" data.
            if self._previous_selection:
                deselected_items = list(self._previous_selection)
                self._previous_selection = set()
                self.canvas_selection_changed.emit([], deselected_items)
            self.object_data_changed.emit({
                'position': None,
                'size': None,
                'rotation': None
            })
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

    def refresh_transform_handler(self):
        """Refresh the transform handler geometry to match current item positions/states."""
        if self.transform_handler:
            try:
                # Verify the handler is still valid before updating
                if not self.transform_handler.is_valid():
                    logger.debug("Transform handler is no longer valid, clearing it")
                    self.clear_transform_handler()
                    return
                    
                self.transform_handler.update_geometry()
                logger.debug("Transform handler refreshed")
            except Exception as e:
                logger.error(f"Error refreshing transform handler: {e}", exc_info=True)
                # Clear invalid handler
                try:
                    self.clear_transform_handler()
                except:
                    pass

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
                            self.transform_handler = TransformHandler(valid_items[0], self.scene, self.view_service, self)
                        elif len(valid_items) > 1:
                            logger.debug("Creating AverageTransformHandler for multiple items.")
                            self.transform_handler = AverageTransformHandler(valid_items, self.scene, self.view_service, self)
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

    def _push_move_undo_command(self):
        """Push an undo command for item move operations (drag)."""
        if not self._drag_initial_positions:
            return
        
        # Get items that were moved
        items = []
        old_positions = []
        new_positions = []
        
        for item_id, old_pos in self._drag_initial_positions.items():
            # Find the item by checking scene items
            for item in self.scene.items():
                if isinstance(item, BaseGraphicObject) and id(item) == item_id:
                    new_pos = item.pos()
                    # Only include if position actually changed
                    if old_pos != new_pos:
                        items.append(item)
                        old_positions.append(old_pos)
                        new_positions.append(QPointF(new_pos))
                    break
        
        if items and old_positions and new_positions:
            command = MoveItemsCommand(items, old_positions, new_positions, "Move Items", self)
            self.undo_stack.push(command)
            logger.debug(f"Pushed move undo command for {len(items)} items")

    def _begin_interaction_cycle(self):
        """Start a new press-move-release interaction cycle for debug tracing."""
        self._interaction_sequence += 1
        self._active_interaction_id = self._interaction_sequence
        logger.debug("Interaction[%s] begin", self._active_interaction_id)

    def _reset_drag_tracking(self):
        """Reset drag tracking state deterministically."""
        self._drag_started = False
        self._drag_initial_positions = {}

    def _reset_interaction_modes(self):
        """Reset interaction mode flags and cycle id."""
        self._mode_drag_move = False
        self._mode_resize_handle = False
        self._mode_tool_draw = False
        if self._active_interaction_id is not None:
            logger.debug("Interaction[%s] end", self._active_interaction_id)
        self._active_interaction_id = None

    def mousePressEvent(self, event):
        """Handle mouse press events."""
        self._store_viewport_mouse_pos(event.pos())
        self._begin_interaction_cycle()
        self._reset_drag_tracking()
        scene_pos = self.mapToScene(event.pos())
        logger.debug(f"Mouse press at scene pos: {scene_pos}")
        
        if self.transform_handler and not self.current_tool:
            try:
                # Validate handler is still valid before checking handles
                if not self.transform_handler.is_valid():
                    logger.debug("Transform handler became invalid, clearing")
                    self.clear_transform_handler()
                else:
                    # Use view-based hit testing (event.pos()) for accuracy with items that ignore transformations.
                    # This ensures handles (which have ItemIgnoresTransformations set) are detected correctly
                    # regardless of zoom level, preventing "click-through" to objects or background.
                    items_at_pos = self.items(event.pos())
                    handle_name = self.transform_handler.get_handle_from_items(items_at_pos)
                    
                    if handle_name:
                        logger.debug(f"Activating resize handle: {handle_name}")
                        self._resizing_handle = handle_name
                        self._mode_resize_handle = True
                        logger.debug("Interaction[%s] mode=resize handle=%s", self._active_interaction_id, handle_name)
                        self.transform_handler.handle_mouse_press(handle_name, event.pos(), scene_pos)
                        self.setDragMode(QGraphicsView.DragMode.NoDrag)
                        event.accept()
                        return
            except Exception as e:
                logger.error(f"CRITICAL: Error in mousePressEvent with transform_handler: {e}", exc_info=True)

        if self.current_tool:
            if event.button() == Qt.MouseButton.LeftButton:
                self._mode_tool_draw = True
                logger.debug("Interaction[%s] mode=tool tool=%s", self._active_interaction_id, self.current_tool.__class__.__name__)
                logger.debug(f"Passing mouse press to tool: {self.current_tool.__class__.__name__}")
                self.current_tool.mouse_press(scene_pos)
                event.accept()
            return

        # Before processing selection, capture if we're clicking on a selected item
        # (to enable drag-tracking for move operations)
        previously_selected_items = set(self.scene.selectedItems())
        
        # Get all items at click position, filtering out transform handlers
        items_at_click = self.items(event.pos())
        item_at_click = None
        for item in items_at_click:
            # Skip transform handler and other non-drawable items
            if not isinstance(item, (TransformHandler, AverageTransformHandler)):
                item_at_click = item
                break
        
        target_item_before = None
        
        # Walk up parent chain to find BaseGraphicObject at click location
        temp = item_at_click
        while temp:
            if isinstance(temp, BaseGraphicObject):
                target_item_before = temp
                break
            temp = temp.parentItem()
        
        # Check if we're clicking on an already-selected item
        clicking_on_selected = target_item_before in previously_selected_items if target_item_before else False
        
        # Call base class to handle selection
        super().mousePressEvent(event)
        
        # If we were clicking on a selected item but it got deselected by super(), reselect it
        # (This happens because itemAt() might not properly recognize composed items)
        if clicking_on_selected and target_item_before and not target_item_before.isSelected():
            target_item_before.setSelected(True)
        
        # Capture initial positions for selected items AFTER selection is updated (for undo tracking)
        if event.button() == Qt.MouseButton.LeftButton and not self.current_tool:
            selected_items = [item for item in self.scene.selectedItems() 
                            if isinstance(item, BaseGraphicObject)]
            
            # If we were clicking on a selected item, always track the full selected group.
            # Fallback to target item only if selection unexpectedly becomes empty.
            if clicking_on_selected:
                items_to_drag = selected_items
                if not items_to_drag and target_item_before:
                    items_to_drag = [target_item_before]
            else:
                items_to_drag = selected_items
            
            if items_to_drag:
                self._drag_started = True
                self._mode_drag_move = True
                logger.debug("Interaction[%s] mode=drag tracked=%s", self._active_interaction_id, len(items_to_drag))
                self._drag_initial_positions = {}
                for item in items_to_drag:
                    self._drag_initial_positions[id(item)] = QPointF(item.pos())
                tracked_ids = set(self._drag_initial_positions.keys())
                if clicking_on_selected and selected_items:
                    selected_ids = {id(item) for item in selected_items}
                    if tracked_ids != selected_ids:
                        logger.warning(
                            "Drag tracking mismatch: tracked=%s selected=%s",
                            len(tracked_ids),
                            len(selected_ids)
                        )
                logger.debug(f"Drag started, captured {len(self._drag_initial_positions)} initial positions")
            else:
                logger.debug(f"No items to drag")

    def mouseMoveEvent(self, event):
        """Handle mouse move events."""
        self._store_viewport_mouse_pos(event.pos())
        scene_pos = self.mapToScene(event.pos())
        self.mouse_moved.emit(scene_pos)

        # Handle resizing via transform handler
        if self._resizing_handle and self.transform_handler:
            try:
                # Validate handler is still valid before using it
                if not self.transform_handler.is_valid():
                    logger.debug("Transform handler became invalid during resize, clearing")
                    self._resizing_handle = None
                    self.clear_transform_handler()
                    if not self.current_tool:
                        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
                    return
                
                logger.debug("Interaction[%s] resize move handle=%s", self._active_interaction_id, self._resizing_handle)
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
            logger.debug("Interaction[%s] tool move", self._active_interaction_id)
            self.current_tool.mouse_move(scene_pos, event.modifiers())
            event.accept()
            return

        super().mouseMoveEvent(event)
        
        if self.transform_handler and not self._resizing_handle and not self.current_tool:
            try:
                if self.transform_handler.is_valid():
                    self.transform_handler.update_geometry()
            except Exception as e:
                logger.debug(f"Error updating transform handler geometry: {e}")

    def mouseReleaseEvent(self, event):
        """Handle mouse release events."""
        self._store_viewport_mouse_pos(event.pos())
        scene_pos = self.mapToScene(event.pos())
        logger.debug("Interaction[%s] release at scene pos: %s", self._active_interaction_id, scene_pos)
        self.clear_snap_lines()

        if self._resizing_handle:
            logger.debug("Interaction[%s] finished resizing handle: %s", self._active_interaction_id, self._resizing_handle)
            # The transform handler will push the undo command in handle_mouse_release
            if self.transform_handler and self.transform_handler.is_valid():
                self.transform_handler.handle_mouse_release()
            self._resizing_handle = None
            self._reset_drag_tracking()
            if not self.current_tool:
                self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
            self.save_items()
            self._update_selected_object_info()
            event.accept()
            self._reset_interaction_modes()
            return

        if self.current_tool:
            if event.button() == Qt.MouseButton.LeftButton:
                logger.debug("Interaction[%s] tool release via %s", self._active_interaction_id, self.current_tool.__class__.__name__)
                self.current_tool.mouse_release(scene_pos)

                temp_item = self.current_tool.current_item
                if temp_item and temp_item.scene() == self.scene:
                    rect = temp_item.rect().normalized()
                    pos = temp_item.pos()
                    item_type = temp_item.data(0)

                    self.scene.removeItem(temp_item)
                    self.current_tool.current_item = None

                    if item_type:
                        self.add_new_item(item_type, rect, pos, temp_item)
                elif temp_item:
                    # Preview item was removed by the tool; clear stale reference.
                    self.current_tool.current_item = None

                event.accept()
            self._reset_drag_tracking()
            self._reset_interaction_modes()
            return

        should_push_move = (
            self._mode_drag_move and
            self._drag_started and
            bool(self._drag_initial_positions) and
            not self._mode_resize_handle and
            not self._mode_tool_draw
        )

        if should_push_move:
            logger.debug("Interaction[%s] emitting move undo command", self._active_interaction_id)
            self._push_move_undo_command()
        self._reset_drag_tracking()

        super().mouseReleaseEvent(event)

        logger.debug("Saving items after mouse release.")
        self.save_items()
        if self.transform_handler and self.transform_handler.is_valid():
            self.transform_handler.update_geometry()
        self._reset_interaction_modes()

    def _resolve_base_graphic_object(self, items):
        """Resolve the nearest BaseGraphicObject from a list of hit-tested items."""
        for item in items:
            current_item = item
            while current_item:
                if isinstance(current_item, BaseGraphicObject):
                    return current_item
                current_item = current_item.parentItem()
        return None

    def contextMenuEvent(self, event):
        """Build and show the canvas context menu."""
        if self.current_tool:
            super().contextMenuEvent(event)
            return

        clicked_item = self._resolve_base_graphic_object(self.items(event.pos()))

        if clicked_item and not clicked_item.isSelected():
            modifiers = event.modifiers()
            additive_selection = bool(
                modifiers & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier)
            )
            if not additive_selection:
                self.scene.clearSelection()
            clicked_item.setSelected(True)

        context_menu = ScreenContextMenu(
            canvas=self,
            target_item=clicked_item,
            global_pos=event.globalPos(),
        )
        if context_menu.show():
            event.accept()
            return

        super().contextMenuEvent(event)
            
    def update_snap_lines(self, moving_items):
        """Compute snap guides and optionally apply the snap delta for object snapping."""
        if not self.view_service.snap_enabled or self.view_service.snapping_mode != 'object':
            return
    
        self.canvas_widget.snap_lines = []
        
        # Bounding rect of all moving items
        moving_rect = self.get_items_bounding_rect(moving_items)
        if moving_rect.isEmpty():
            return
    
        static_items = [item for item in self.scene.items() if isinstance(item, BaseGraphicObject) and item not in moving_items]
    
        # Compute guides + snap delta in one pass, then decide whether to mutate item positions.
        snap_offset_x, snap_offset_y, snap_lines = self.calculate_snap_result(moving_rect, static_items)
        self.canvas_widget.snap_lines = snap_lines
    
        # Apply the snap offset to moving items only when this screen owns object snap mutation.
        if self._apply_object_snap_delta_during_drag and (snap_offset_x != 0 or snap_offset_y != 0):
            for item in moving_items:
                item.moveBy(snap_offset_x, snap_offset_y)

        self.canvas_widget.update()


    def calculate_snap_result(self, moving_rect, static_items):
        """
        Calculates object snap result for moving_rect.

        Returns:
            tuple: (snap_offset_x, snap_offset_y, snap_lines)
        """
        snap_offset_x, snap_offset_y = 0, 0
        min_dist_x, min_dist_y = self.snapping_threshold, self.snapping_threshold
        candidate_line_x = None
        candidate_line_y = None
        canvas_bounds = self.canvas_widget.boundingRect()
    
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
                    candidate_line_x = QLineF(s_edge, canvas_bounds.top(), s_edge, canvas_bounds.bottom())

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
                    candidate_line_y = QLineF(canvas_bounds.left(), s_edge, canvas_bounds.right(), s_edge)

        # If a snap occurred, we only want the closest one, not both X and Y.
        if abs(snap_offset_x) < abs(snap_offset_y) and abs(snap_offset_x) > 0:
            snap_offset_y = 0
            candidate_line_y = None
        elif abs(snap_offset_y) < abs(snap_offset_x) and abs(snap_offset_y) > 0:
            snap_offset_x = 0
            candidate_line_x = None

        snap_lines = []
        if candidate_line_x is not None:
            snap_lines.append(candidate_line_x)
        if candidate_line_y is not None:
            snap_lines.append(candidate_line_y)
            
        return snap_offset_x, snap_offset_y, snap_lines


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
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            event_pos = self._event_viewport_pos(event)
            self._store_viewport_mouse_pos(event_pos)
            delta = event.angleDelta().y()
            if delta > 0:
                self.zoom_in(event_pos)
            else:
                self.zoom_out(event_pos)
            event.accept()
        else:
            super().wheelEvent(event)

    def keyPressEvent(self, event):
        """Handle key press events for zooming, panning, and object movement."""
        if event.key() == Qt.Key.Key_Escape:
            if self.current_tool:
                self.set_tool(None)
                self.tool_reset.emit()
            event.accept()
            return

        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
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
        # Handle arrow keys for object movement
        elif event.key() in (Qt.Key.Key_Up, Qt.Key.Key_Down, Qt.Key.Key_Left, Qt.Key.Key_Right):
            # Determine movement distance (1 pixel default, or larger with Shift)
            move_distance = 10 if event.modifiers() & Qt.KeyboardModifier.ShiftModifier else 1
            
            # Handle each arrow key direction
            if event.key() == Qt.Key.Key_Up:
                self.move_items_by_offset(0, -move_distance)
            elif event.key() == Qt.Key.Key_Down:
                self.move_items_by_offset(0, move_distance)
            elif event.key() == Qt.Key.Key_Left:
                self.move_items_by_offset(-move_distance, 0)
            elif event.key() == Qt.Key.Key_Right:
                self.move_items_by_offset(move_distance, 0)
            
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

    def _store_viewport_mouse_pos(self, pos):
        """Remember the last valid mouse position inside the viewport."""
        if pos is None:
            return

        viewport_rect = self.viewport().rect()
        if viewport_rect.contains(pos):
            self._last_viewport_mouse_pos = QPoint(pos)

    def _get_zoom_anchor_pos(self, anchor_pos=None):
        """Return a viewport position to use as the zoom anchor."""
        if anchor_pos is not None and self.viewport().rect().contains(anchor_pos):
            return QPoint(anchor_pos)
        if self._last_viewport_mouse_pos is not None:
            return QPoint(self._last_viewport_mouse_pos)
        return self.viewport().rect().center()

    def _event_viewport_pos(self, event):
        """Extract a viewport QPoint from Qt mouse and wheel events."""
        if hasattr(event, "position"):
            return event.position().toPoint()
        if hasattr(event, "pos"):
            return event.pos()
        return None

    def _apply_zoom(self, target_zoom_factor, anchor_pos=None):
        """Zoom while keeping the scene point under the anchor fixed."""
        clamped_zoom = max(0.1, min(target_zoom_factor, 10.0))
        if abs(clamped_zoom - self.zoom_factor) < 1e-9:
            return

        anchor = self._get_zoom_anchor_pos(anchor_pos)
        old_scene_anchor = self.mapToScene(anchor)
        viewport_center = self.viewport().rect().center()
        anchor_offset = QPointF(anchor) - QPointF(viewport_center)
        scale_factor = clamped_zoom / self.zoom_factor

        self.scale(scale_factor, scale_factor)
        desired_viewport_center = QPointF(self.mapFromScene(old_scene_anchor)) - anchor_offset
        self.centerOn(self.mapToScene(desired_viewport_center.toPoint()))

        self.zoom_factor = clamped_zoom
        self.zoom_changed.emit(self.zoom_factor)

    def zoom(self, factor, anchor_pos=None):
        """Apply a zoom factor to the view, respecting min/max limits."""
        self._apply_zoom(self.zoom_factor * factor, anchor_pos)

    def zoom_in(self, anchor_pos=None):
        """Zoom in by a predefined factor."""
        self.zoom(1.1, anchor_pos)

    def zoom_out(self, anchor_pos=None):
        """Zoom out by a predefined factor."""
        self.zoom(0.9, anchor_pos)
        
    def set_zoom_level(self, level_str, anchor_pos=None):
        """Set zoom to a specific percentage (e.g., "100%"), respecting limits."""
        try:
            level = float(level_str.strip('%')) / 100.0
            self._apply_zoom(level, anchor_pos)

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

    def _serialize_pen(self, pen):
        """Serialize a QPen to a dictionary."""
        return {
            'color': pen.color().name(),
            'width': pen.width(),
            'style': pen.style().value,
            'cap_style': pen.capStyle().value,
            'join_style': pen.joinStyle().value
        }
    
    def _deserialize_pen(self, pen_data):
        """Deserialize a QPen from a dictionary."""
        pen = QPen(QColor(pen_data.get('color', 'black')))
        pen.setWidth(pen_data.get('width', 2))
        pen.setStyle(Qt.PenStyle(pen_data.get('style', Qt.PenStyle.SolidLine.value)))
        pen.setCapStyle(Qt.PenCapStyle(pen_data.get('cap_style', Qt.PenCapStyle.SquareCap.value)))
        pen.setJoinStyle(Qt.PenJoinStyle(pen_data.get('join_style', Qt.PenJoinStyle.BevelJoin.value)))
        return pen
    
    def _serialize_brush(self, brush):
        """Serialize a QBrush to a dictionary."""
        return {
            'color': brush.color().name(),
            'alpha': brush.color().alpha(),
            'style': brush.style().value
        }
    
    def _deserialize_brush(self, brush_data):
        """Deserialize a QBrush from a dictionary."""
        color = QColor(brush_data.get('color', '#c8c8c8'))
        color.setAlpha(brush_data.get('alpha', 100))
        brush = QBrush(color)
        brush.setStyle(Qt.BrushStyle(brush_data.get('style', Qt.BrushStyle.SolidPattern.value)))
        return brush

    def _serialize_item_for_clipboard(self, item):
        """Serialize a scene item for clipboard operations using live geometry/state."""
        item_data = item.data(Qt.ItemDataRole.UserRole)
        if not item_data:
            return None

        data_copy = copy.deepcopy(item_data)
        data_copy['pos'] = [item.pos().x(), item.pos().y()]
        rect = item.boundingRect()
        data_copy['rect'] = [rect.x(), rect.y(), rect.width(), rect.height()]

        # Ensure rounded rectangle runtime state is copied from the live item.
        if hasattr(item, 'corner_radii'):
            clamped_corner_radii = item.get_clamped_corner_radii(item.corner_radii)
            item.corner_radii = clamped_corner_radii
            data_copy['corner_radii'] = clamped_corner_radii
        if hasattr(item, 'rounded_enabled'):
            data_copy['rounded_enabled'] = item.rounded_enabled
        
        # Serialize visual properties from the composed item
        if hasattr(item, 'item'):
            # Store pen (stroke color and width)
            pen = item.item.pen()
            data_copy['pen'] = self._serialize_pen(pen)
            
            # Store brush (fill color and transparency)
            brush = item.item.brush()
            data_copy['brush'] = self._serialize_brush(brush)
            
            # Store opacity and rotation
            data_copy['opacity'] = item.opacity()
            data_copy['rotation'] = item.rotation()
            data_copy['z_value'] = item.zValue()

        return data_copy

    def cut(self):
        """Cut selected items to clipboard."""
        selected_items = [item for item in self.scene.selectedItems() if isinstance(item, BaseGraphicObject)]
        if not selected_items:
            logger.debug("Cut: No items selected")
            return

        self.edit_service.set_active_stack(self._stack_id)
        self.edit_service.cut_objects(
            selected_items,
            delete_command_factory=lambda: RemoveItemCommand(self, selected_items, "Cut Items"),
        )
        logger.debug(f"Cut {len(selected_items)} items")

    def copy(self):
        """Copy selected items to clipboard."""
        selected_items = [item for item in self.scene.selectedItems() if isinstance(item, BaseGraphicObject)]
        if not selected_items:
            logger.debug("Copy: No items selected")
            return

        self.edit_service.copy_objects(selected_items)
        logger.debug(f"Copied {len(selected_items)} items")

    def paste(self):
        """Paste items from clipboard."""
        self.edit_service.set_active_stack(self._stack_id)
        screen_id = str(self.screen_data.get('id') or self.screen_data.get('name') or self._stack_id)

        def get_screen_state(_screen_id):
            return copy.deepcopy(self.screen_data)

        def save_screen_state(_screen_id, data):
            self.screen_data.clear()
            self.screen_data.update(copy.deepcopy(data))
            if self.project_service and self.project_service.project_metadata:
                self.project_service.storage.save_screen(self.project_service.project_metadata.project_path, _screen_id, data)

        def apply_screen_state(_screen_id, state):
            self.scene.clear()
            self.screen_data.clear()
            self.screen_data.update(copy.deepcopy(state))
            self.scene.addItem(self.canvas_widget)
            self._restore_items()
            self.save_items()

        def create_object(data):
            return self.create_graphic_item_from_data(data)

        def set_selection_focus(items):
            self.scene.clearSelection()
            for item in items:
                item.setSelected(True)
            if items:
                self.setFocus()
                self.refresh_transform_handler()

        pasted_items = self.edit_service.paste_objects(
            screen_id,
            offset=(10, 10),
            get_screen_state=get_screen_state,
            save_screen=save_screen_state,
            create_object=create_object,
            apply_screen_state=apply_screen_state,
            mark_dirty=self.project_service.mark_as_unsaved,
            set_selection_focus=set_selection_focus,
        )

        if pasted_items:
            logger.debug(f"Pasted {len(pasted_items)} items")
        else:
            logger.debug("Paste: No canvas items in clipboard")

    def _calculate_paste_position(self, clipboard_data):
        """Compute paste anchor and offset with snapping awareness."""
        base_anchor = self._resolve_paste_anchor()
        source_anchor = self._clipboard_anchor(clipboard_data)
        raw_offset = base_anchor - source_anchor
        snapped_offset = self._apply_snap_to_offset(clipboard_data, raw_offset)
        return base_anchor, snapped_offset

    def _resolve_paste_anchor(self):
        """Resolve where a new paste should land."""
        if self._last_viewport_mouse_pos is not None:
            return self.mapToScene(self._last_viewport_mouse_pos)
        if self._last_paste_anchor is not None:
            step = QPointF(20, 20)
            if self.view_service.snap_enabled and self.view_service.snapping_mode == 'grid':
                grid_size = max(1, int(self.view_service.grid_size))
                step = QPointF(grid_size, grid_size)
            return self._last_paste_anchor + step
        return QPointF(20, 20)

    def _clipboard_anchor(self, clipboard_data):
        """Use the top-left of copied items as source anchor."""
        if not clipboard_data:
            return QPointF(0, 0)
        xs = []
        ys = []
        for data in clipboard_data:
            pos = data.get('pos', [0, 0])
            xs.append(float(pos[0]))
            ys.append(float(pos[1]))
        return QPointF(min(xs), min(ys))

    def _apply_snap_to_offset(self, clipboard_data, offset):
        """Adjust offset based on snap settings."""
        if not self.view_service.snap_enabled:
            return offset
        if self.view_service.snapping_mode != 'grid':
            return offset
        grid_size = max(1, int(self.view_service.grid_size))
        source_anchor = self._clipboard_anchor(clipboard_data)
        target_anchor = source_anchor + offset
        snapped_anchor = QPointF(
            round(target_anchor.x() / grid_size) * grid_size,
            round(target_anchor.y() / grid_size) * grid_size,
        )
        return snapped_anchor - source_anchor

    def delete(self):
        """Delete selected items."""
        selected_items = [item for item in self.scene.selectedItems() 
                         if isinstance(item, BaseGraphicObject)]
        self.delete_items(selected_items, "Delete Items")

    def delete_items(self, items, command_text="Delete Items"):
        """Delete provided canvas items using undo/redo command flow."""
        selected_items = [item for item in items if isinstance(item, BaseGraphicObject)]
        if not selected_items:
            logger.debug("Delete: No items selected")
            return

        # Use remove command for undo support
        command = RemoveItemCommand(self, selected_items, command_text)
        self.undo_stack.push(command)

        logger.debug(f"Deleted {len(selected_items)} items")

    def move_items_by_offset(self, dx, dy):
        """Move selected items by the given offset with undo support."""
        selected_items = [item for item in self.scene.selectedItems() 
                         if isinstance(item, BaseGraphicObject)]
        if not selected_items:
            logger.debug("Move: No items selected")
            return
        
        # Capture current positions before moving (as list, not dict)
        old_positions = [QPointF(item.pos()) for item in selected_items]
        
        # Move items immediately
        for item in selected_items:
            new_pos = item.pos() + QPointF(dx, dy)
            item.setPos(new_pos)
        
        # Capture new positions after moving (as list, not dict)
        new_positions = [QPointF(item.pos()) for item in selected_items]
        
        # Create undo command with canvas reference
        command = MoveItemsCommand(selected_items, old_positions, new_positions, "Move Items", self)
        self.undo_stack.push(command)
        
        # Update transform handler to follow the moved items
        self.refresh_transform_handler()
        
        # Update status bar with new position
        self._update_selected_object_info()
        
        logger.debug(f"Moved {len(selected_items)} items by offset ({dx}, {dy})")

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

    def _selected_graphic_items(self):
        """Return currently selected canvas graphic objects."""
        return [
            item for item in self.scene.selectedItems()
            if isinstance(item, BaseGraphicObject)
        ]

    def group_selected_items(self):
        """
        Assign selected items to a logical group (metadata-based grouping).
        """
        selected_items = self._selected_graphic_items()
        if len(selected_items) < 2:
            logger.debug("Group: Need at least 2 selected items")
            return

        group_id = str(uuid.uuid4())
        item_ids = []
        old_group_ids = {}
        for item in selected_items:
            data = item.data(Qt.ItemDataRole.UserRole) or {}
            item_id = data.get('id')
            if item_id is None:
                continue
            item_ids.append(item_id)
            old_group_ids[item_id] = data.get('group_id')

        if len(item_ids) < 2:
            logger.debug("Group: Not enough valid items with IDs")
            return

        command = GroupItemsCommand(self, item_ids, old_group_ids, group_id, "Group Items")
        self.undo_stack.push(command)
        logger.debug(f"Grouped {len(item_ids)} items with group_id={group_id}")

    def ungroup_selected_items(self):
        """
        Clear logical group assignment from selected grouped items.
        """
        selected_items = self._selected_graphic_items()
        if not selected_items:
            logger.debug("Ungroup: No selected items")
            return

        item_ids = []
        old_group_ids = {}
        for item in selected_items:
            data = item.data(Qt.ItemDataRole.UserRole) or {}
            item_id = data.get('id')
            group_id = data.get('group_id')
            if item_id is None or not group_id:
                continue
            item_ids.append(item_id)
            old_group_ids[item_id] = group_id

        if not item_ids:
            logger.debug("Ungroup: No grouped selected items")
            return

        command = UngroupItemsCommand(self, item_ids, old_group_ids, "Ungroup Items")
        self.undo_stack.push(command)
        logger.debug(f"Ungrouped {len(item_ids)} items")

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

    def _get_deterministic_z_order(self):
        """Return all graphic items sorted by z-value with stable tie-breakers."""
        all_items = [item for item in self.scene.items() if isinstance(item, BaseGraphicObject)]
        if not all_items:
            return []

        # scene.items() returns top-most items first. For equal z-values we need
        # canonical order from back -> front, so invert the scene index.
        scene_enumeration = {id(item): idx for idx, item in enumerate(all_items)}

        def sort_key(item):
            data = item.data(Qt.ItemDataRole.UserRole) or {}
            item_id = str(data.get('id', ''))
            scene_index = scene_enumeration[id(item)]
            return (item.zValue(), -scene_index, item_id)

        return sorted(all_items, key=sort_key)

    def _get_selected_items_in_canonical_order(self, ordered_items):
        """Return selected graphic items in the same canonical order as ordered_items."""
        selected_set = {
            item for item in self.scene.selectedItems()
            if isinstance(item, BaseGraphicObject)
        }
        return [item for item in ordered_items if item in selected_set]

    def _find_next_non_selected_index(self, ordered_items, start_index, selected_set):
        """Find the next non-selected item index after start_index."""
        for idx in range(start_index + 1, len(ordered_items)):
            if ordered_items[idx] not in selected_set:
                return idx
        return None

    def _find_prev_non_selected_index(self, ordered_items, start_index, selected_set):
        """Find the previous non-selected item index before start_index."""
        for idx in range(start_index - 1, -1, -1):
            if ordered_items[idx] not in selected_set:
                return idx
        return None

    def move_front_layer(self):
        """
        Move selected items one layer up (increase z-value).

        For multi-selection, process selected items from highest layer to lowest
        (descending canonical z-order) so behavior is stable and predictable.
        """
        ordered_items = self._get_deterministic_z_order()
        selected_items = self._get_selected_items_in_canonical_order(ordered_items)
        if not selected_items:
            return

        if not ordered_items:
            return

        selected_set = set(selected_items)
        # Move higher-index selected items first so multi-selection behaves like one block.
        selected_indices = sorted(
            (idx for idx, item in enumerate(ordered_items) if item in selected_set),
            reverse=True
        )
        selected_in_move_order = [ordered_items[idx] for idx in selected_indices]

        for item in selected_in_move_order:
            current_index = ordered_items.index(item)
            neighbor_index = self._find_next_non_selected_index(ordered_items, current_index, selected_set)
            if neighbor_index is None:
                continue
            ordered_items[current_index], ordered_items[neighbor_index] = (
                ordered_items[neighbor_index],
                ordered_items[current_index]
            )

        old_z_values = [item.zValue() for item in ordered_items]
        new_z_values = [float(index) for index, _ in enumerate(ordered_items)]

        command = ZOrderCommand(ordered_items, old_z_values, new_z_values, "Move Front Layer")
        self.undo_stack.push(command)
        self.save_items()

    def move_back_layer(self):
        """
        Move selected items one layer down (decrease z-value).

        For multi-selection, process selected items from lowest layer to highest
        (ascending canonical z-order) so behavior is stable and predictable.
        """
        ordered_items = self._get_deterministic_z_order()
        selected_items = self._get_selected_items_in_canonical_order(ordered_items)
        if not selected_items:
            return

        if not ordered_items:
            return

        selected_set = set(selected_items)
        # Move lower-index selected items first so multi-selection behaves like one block.
        selected_indices = sorted(
            idx for idx, item in enumerate(ordered_items) if item in selected_set
        )
        selected_in_move_order = [ordered_items[idx] for idx in selected_indices]

        for item in selected_in_move_order:
            current_index = ordered_items.index(item)
            neighbor_index = self._find_prev_non_selected_index(ordered_items, current_index, selected_set)
            if neighbor_index is None:
                continue
            ordered_items[current_index], ordered_items[neighbor_index] = (
                ordered_items[neighbor_index],
                ordered_items[current_index]
            )

        old_z_values = [item.zValue() for item in ordered_items]
        new_z_values = [float(index) for index, _ in enumerate(ordered_items)]

        command = ZOrderCommand(ordered_items, old_z_values, new_z_values, "Move Back Layer")
        self.undo_stack.push(command)
        self.save_items()


    def move_to_front_single_layer(self):
        """UI wrapper: move selected items one layer toward the front."""
        self.move_front_layer()

    def move_to_back_single_layer(self):
        """UI wrapper: move selected items one layer toward the back."""
        self.move_back_layer()

    def move_to_front(self):
        """Move selected items to the front using canonical z-order selection."""
        ordered_items = self._get_deterministic_z_order()
        selected_items = self._get_selected_items_in_canonical_order(ordered_items)
        if not selected_items:
            return

        if not ordered_items:
            return

        old_z_values = [item.zValue() for item in ordered_items]
        non_selected = [item for item in ordered_items if item not in set(selected_items)]
        new_order = non_selected + selected_items
        new_z_map = {item: float(index) for index, item in enumerate(new_order)}
        new_z_values = [new_z_map[item] for item in ordered_items]

        command = ZOrderCommand(ordered_items, old_z_values, new_z_values, "Move to Front")
        self.undo_stack.push(command)
        self.save_items()

    def move_to_back(self):
        """Move selected items to the back using canonical z-order selection."""
        ordered_items = self._get_deterministic_z_order()
        selected_items = self._get_selected_items_in_canonical_order(ordered_items)
        if not selected_items:
            return

        if not ordered_items:
            return

        old_z_values = [item.zValue() for item in ordered_items]
        non_selected = [item for item in ordered_items if item not in set(selected_items)]
        new_order = selected_items + non_selected
        new_z_map = {item: float(index) for index, item in enumerate(new_order)}
        new_z_values = [new_z_map[item] for item in ordered_items]

        command = ZOrderCommand(ordered_items, old_z_values, new_z_values, "Move to Back")
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
        
        old_positions = [QPointF(item.pos()) for item in selected_items]
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
        command = MoveItemsCommand(selected_items, old_positions, new_positions, f"Align {alignment}", self)
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
            total_width = sum(r.width() for _, r in rects)
            spacing = (last_right - first_left - total_width) / (len(rects) - 1)
            
            old_positions = [QPointF(item.pos()) for item, _ in rects]
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
            total_height = sum(r.height() for _, r in rects)
            spacing = (last_bottom - first_top - total_height) / (len(rects) - 1)
            
            old_positions = [QPointF(item.pos()) for item, _ in rects]
            new_positions = []
            
            current_y = first_top
            for item, rect in rects:
                new_pos = item.pos()
                new_pos.setY(new_pos.y() + (current_y - rect.top()))
                new_positions.append(new_pos)
                current_y += rect.height() + spacing
        
        items = [item for item, _ in rects]
        command = MoveItemsCommand(items, old_positions, new_positions, f"Distribute {direction}", self)
        self.undo_stack.push(command)
        self.save_items()

    # ========== Flip/Rotate Operations ==========

    def flip_items(self, direction):
        """
        Flip selected items with undo support.
        
        Args:
            direction: 'horizontal' or 'vertical'
        """
        selected_items = [item for item in self.scene.selectedItems() 
                         if isinstance(item, BaseGraphicObject)]
        if not selected_items:
            return
        
        # Capture old states for undo
        old_states = []
        for item in selected_items:
            state = {
                'pos': QPointF(item.pos()),
                'rect': QRectF(item.boundingRect()),
                'rotation': item.rotation(),
                'transform_origin': QPointF(item.transformOriginPoint()),
                'transform': item.transform()  # Store full transform for flip
            }
            if hasattr(item, 'corner_radii'):
                state['corner_radii'] = item.corner_radii.copy()
            old_states.append(state)
        
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
        
        # Capture new states for undo
        new_states = []
        for item in selected_items:
            state = {
                'pos': QPointF(item.pos()),
                'rect': QRectF(item.boundingRect()),
                'rotation': item.rotation(),
                'transform_origin': QPointF(item.transformOriginPoint()),
                'transform': item.transform()
            }
            if hasattr(item, 'corner_radii'):
                state['corner_radii'] = item.corner_radii.copy()
            new_states.append(state)
        
        # Push undo command
        from services.undo_commands import TransformItemsCommand
        command = TransformItemsCommand(selected_items, old_states, new_states, f"Flip {direction.title()}", self)
        self.undo_stack.push(command)
        
        # Update transform handler to follow the flipped items
        self.refresh_transform_handler()
        
        self.save_items()
        logger.debug(f"Flipped {len(selected_items)} items {direction}")

    def rotate_items(self, angle):
        """
        Rotate selected items by the specified angle with undo support.
        
        Args:
            angle: Rotation angle in degrees (positive = clockwise)
        """
        selected_items = [item for item in self.scene.selectedItems() 
                         if isinstance(item, BaseGraphicObject)]
        if not selected_items:
            return
        
        # Capture old states for undo
        old_states = []
        for item in selected_items:
            state = {
                'pos': QPointF(item.pos()),
                'rect': QRectF(item.boundingRect()),
                'rotation': item.rotation(),
                'transform_origin': QPointF(item.transformOriginPoint())
            }
            if hasattr(item, 'corner_radii'):
                state['corner_radii'] = item.corner_radii.copy()
            old_states.append(state)
        
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
        
        # Capture new states for undo
        new_states = []
        for item in selected_items:
            state = {
                'pos': QPointF(item.pos()),
                'rect': QRectF(item.boundingRect()),
                'rotation': item.rotation(),
                'transform_origin': QPointF(item.transformOriginPoint())
            }
            if hasattr(item, 'corner_radii'):
                state['corner_radii'] = item.corner_radii.copy()
            new_states.append(state)
        
        # Push undo command
        from services.undo_commands import TransformItemsCommand
        description = f"Rotate {'+' if angle > 0 else ''}{int(angle)}°"
        command = TransformItemsCommand(selected_items, old_states, new_states, description, self)
        self.undo_stack.push(command)
        
        # Update transform handler to follow the rotated items
        self.refresh_transform_handler()
        
        self.save_items()
        logger.debug(f"Rotated {len(selected_items)} items by {angle} degrees")

    # ========== Cleanup ==========

    def cleanup(self):
        """Clean up resources when the canvas is closed."""
        # Unregister undo stack from EditService
        self.edit_service.unregister_undo_stack(self._stack_id)
        logger.debug(f"Canvas {self._stack_id} cleaned up")
