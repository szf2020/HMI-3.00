# main_window/toolbars/transform_handler.py
"""
Robust Transform Handler System
================================
Provides reliable transform handles for single and multiple graphics items.
Includes comprehensive error handling, state validation, and coordinate safety.
Supports rotation from corner handles with center anchor point.
"""

import math
from PySide6.QtWidgets import QGraphicsItem, QGraphicsRectItem, QGraphicsEllipseItem
from PySide6.QtCore import Qt, QRectF, QPointF, Signal
from PySide6.QtGui import QPen, QBrush, QColor, QCursor, QPixmap, QPainter
from styles import colors
from screen.base.base_graphic_object import BaseGraphicObject, RectangleObject
from debug_utils import get_logger

logger = get_logger(__name__)


def create_rotation_cursor():
    """Create a custom rotation cursor (curved arrow)."""
    pixmap = QPixmap(24, 24)
    pixmap.fill(Qt.GlobalColor.transparent)
    
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    
    # Draw rotation arc arrow
    pen = QPen(QColor(0, 0, 0), 2)
    painter.setPen(pen)
    
    # Draw arc
    from PySide6.QtCore import QRect
    rect = QRect(4, 4, 16, 16)
    painter.drawArc(rect, 45 * 16, 270 * 16)  # Start at 45°, span 270°
    
    # Draw arrow head at end of arc
    painter.drawLine(18, 8, 20, 4)
    painter.drawLine(18, 8, 14, 6)
    
    painter.end()
    
    return QCursor(pixmap, 12, 12)


class TransformHandle(QGraphicsRectItem):
    """A single handle (square) for resizing or rotating."""
    
    def __init__(self, cursor_shape, parent=None, is_rotation_handle=False):
        # Hit area: 12x12 pixel square (larger than visual for easier clicking)
        # Centered relative to its pos (-6, -6)
        super().__init__(-6, -6, 12, 12, parent)
        self.is_rotation_handle = is_rotation_handle
        
        if isinstance(cursor_shape, QCursor):
            self.setCursor(cursor_shape)
        else:
            self.setCursor(cursor_shape)
        
        # Different colors for rotation handles
        if is_rotation_handle:
            self.setBrush(QBrush(QColor(colors.COLOR_TRANSFORM_BORDER)))
            self.setPen(QPen(QColor(colors.TEXT_PRIMARY), 2))
        else:
            self.setBrush(QBrush(QColor(colors.TEXT_PRIMARY)))
            self.setPen(QPen(QColor(colors.COLOR_TRANSFORM_BORDER), 2))
        
        # Ensure handles stay consistent size regardless of zoom
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations, True)

    def paint(self, painter, option, widget=None):
        """
        Draws the visual representation of the handle.
        Rotation handles draw a circle, resize handles draw a square.
        """
        painter.setPen(self.pen())
        painter.setBrush(self.brush())
        
        if self.is_rotation_handle:
            # Visual area: 6x6 circle for rotation handles
            painter.drawEllipse(-3, -3, 6, 6)
        else:
            # Visual area: 6x6 square for resize handles
            painter.drawRect(-3, -3, 6, 6)


class CornerRadiusHandle(QGraphicsEllipseItem):
    """A small dot handle for adjusting individual corner radius."""
    
    def __init__(self, corner_index, parent=None):
        # Hit area: 10x10 pixel circle, Visual area: 6x6
        super().__init__(-5, -5, 10, 10, parent)
        self.corner_index = corner_index  # 0=TL, 1=TR, 2=BR, 3=BL
        
        # Use a distinct blue color for corner radius handles
        self.setBrush(QBrush(QColor(0, 120, 215)))  # Blue fill
        self.setPen(QPen(QColor(255, 255, 255), 1.5))  # White border
        
        self.setCursor(Qt.CursorShape.CrossCursor)
        
        # Ensure handles stay consistent size regardless of zoom
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations, True)
        
        # Initially hidden
        self.setVisible(False)

    def paint(self, painter, option, widget=None):
        """Draws the visual representation of the corner radius handle."""
        painter.setPen(self.pen())
        painter.setBrush(self.brush())
        # Visual area: 6x6 circle
        painter.drawEllipse(-3, -3, 6, 6)


class BaseTransformHandler(QGraphicsItem):
    """
    Base class for transform handlers with robust state management.
    Provides common functionality and error handling for all handlers.
    Supports rotation from corner handles with center anchor point.
    Supports corner radius adjustment for rounded rectangles.
    """

    # Offset for rotation handles from corners (in pixels)
    ROTATION_HANDLE_OFFSET = 20
    # Offset for corner radius handles (inside the corner)
    CORNER_RADIUS_HANDLE_OFFSET = 15

    def __init__(self, scene, view_service):
        super().__init__()
        self._is_resizing = False
        self._is_rotating = False
        self._is_adjusting_corner_radius = False
        self.scene_ref = scene
        self.view_service = view_service
        
        self.setZValue(9999)  # Always on top
        
        # Pen for the border line
        if not hasattr(self, 'border_pen'):
            self.border_pen = QPen(QColor(colors.COLOR_TRANSFORM_BORDER), 2, Qt.PenStyle.SolidLine)
            self.border_pen.setCosmetic(True)
        
        # State management
        self._drag_mode = None
        self._is_valid = True
        self._handles = {}
        self._rotation_handles = {}
        self._corner_radius_handles = {}
        
        # Rotation state
        self._rotation_start_angle = 0.0
        self._rotation_center = QPointF()
        self._initial_item_rotation = 0.0
        
        # Corner radius state
        self._corner_radius_mode_enabled = False
        self._initial_corner_radii = [0.0, 0.0, 0.0, 0.0]
        self._corner_drag_start_pos = QPointF()
        self._active_corner_index = -1
        
        # Create rotation cursor
        self._rotation_cursor = create_rotation_cursor()
        
        self._create_handles()
        self._create_rotation_handles()
        self._create_corner_radius_handles()
        
        # CRITICAL: Do NOT call addItem(self) here. 
        # Subclasses must call addToScene() explicitly at the end of their __init__.

    def addToScene(self):
        """Safely add the handler to the scene after full initialization."""
        if self.scene_ref:
            try:
                # Check if already in a scene to avoid duplicate additions
                if self.scene() == self.scene_ref:
                    return  # Already added, skip
                
                self.scene_ref.addItem(self)
                
                # Child items (handles parented to us) are automatically added to scene
                # No need to manually add them
                
            except Exception as e:
                logger.error(f"Error adding handler to scene: {e}")
                self.scene_ref = None

    def get_items(self):
        """Return the item(s) being transformed."""
        raise NotImplementedError

    def _create_handles(self):
        """Create transform handles."""
        cursors = {
            'tl': Qt.CursorShape.SizeFDiagCursor,
            't':  Qt.CursorShape.SizeVerCursor,
            'tr': Qt.CursorShape.SizeBDiagCursor,
            'r':  Qt.CursorShape.SizeHorCursor,
            'br': Qt.CursorShape.SizeFDiagCursor,
            'b':  Qt.CursorShape.SizeVerCursor,
            'bl': Qt.CursorShape.SizeBDiagCursor,
            'l':  Qt.CursorShape.SizeHorCursor
        }
        
        for key, cursor in cursors.items():
            try:
                self._handles[key] = TransformHandle(cursor, self)
            except Exception as e:
                logger.warning(f"Error creating handle {key}: {e}")
    
    def _create_rotation_handles(self):
        """Create rotation handles at corners with proper parenting."""
        # Rotation handles at all 4 corners
        # Parent them to the handler to avoid scene management issues
        corner_keys = ['rot_tl', 'rot_tr', 'rot_bl', 'rot_br']
        
        for key in corner_keys:
            try:
                handle = TransformHandle(
                    self._rotation_cursor, self, is_rotation_handle=True
                )
                self._rotation_handles[key] = handle
            except Exception as e:
                logger.warning(f"Error creating rotation handle {key}: {e}")
    
    def _create_corner_radius_handles(self):
        """Create corner radius handles for rounded rectangle adjustment with proper parenting."""
        # Corner radius handles: 0=TL, 1=TR, 2=BR, 3=BL
        # Parent them to the handler instead of leaving them unparented
        corner_keys = ['cr_tl', 'cr_tr', 'cr_br', 'cr_bl']
        
        for idx, key in enumerate(corner_keys):
            try:
                handle = CornerRadiusHandle(idx, self)  # Parent to handler
                self._corner_radius_handles[key] = handle
            except Exception as e:
                logger.warning(f"Error creating corner radius handle {key}: {e}")
    
    def is_valid(self):
        """Check if handler is still valid."""
        return self._is_valid
    
    def validate(self):
        """Override in subclasses to validate handler state."""
        return self._is_valid
    
    def boundingRect(self):
        """Return local bounding rect."""
        return QRectF()
    
    def paint(self, painter, option, widget=None):
        """Draw the transform visualization."""
        pass
    
    def get_handle_at(self, scene_pos):
        """
        Returns the name of the handle under the mouse using scene coordinates.
        Note: Use get_handle_from_items for more robust view-based detection.
        """
        if not self._is_valid or not self.scene_ref:
            return None
        
        try:
            items = self.scene_ref.items(
                scene_pos, 
                Qt.ItemSelectionMode.IntersectsItemShape, 
                Qt.SortOrder.DescendingOrder
            )
            return self.get_handle_from_items(items)
        except Exception as e:
            logger.debug(f"Error getting handle at position: {e}")
        
        return None

    def get_handle_from_items(self, items):
        """
        Finds a handle name from a list of QGraphicsItems.
        This is preferred for use with QGraphicsView.items(pos).
        Returns tuple (handle_name, is_rotation_handle) or (None, False).
        """
        if not self._is_valid:
            return None
        
        # Check corner radius handles first (highest priority when enabled)
        if self._corner_radius_mode_enabled:
            for item in items:
                for name, handle in self._corner_radius_handles.items():
                    if item == handle and handle.isVisible():
                        return name
        
        # Check rotation handles next (they are on top)
        for item in items:
            for name, handle in self._rotation_handles.items():
                if item == handle:
                    return name
        
        # Then check resize handles
        for item in items:
            for name, handle in self._handles.items():
                if item == handle:
                    return name
        return None
    
    def is_rotation_handle(self, handle_name):
        """Check if a handle name is a rotation handle."""
        return handle_name and handle_name.startswith('rot_')
    
    def is_corner_radius_handle(self, handle_name):
        """Check if a handle name is a corner radius handle."""
        return handle_name and handle_name.startswith('cr_')
    
    def handle_mouse_press(self, handle_name, pos, scene_pos):
        """Called when a handle is pressed."""
        self._drag_mode = handle_name
        
        if self.is_corner_radius_handle(handle_name):
            self._is_adjusting_corner_radius = True
            self._is_rotating = False
            self._is_resizing = False
            self._corner_drag_start_pos = QPointF(scene_pos)
            # Extract corner index from handle name (cr_tl=0, cr_tr=1, cr_br=2, cr_bl=3)
            corner_map = {'cr_tl': 0, 'cr_tr': 1, 'cr_br': 2, 'cr_bl': 3}
            self._active_corner_index = corner_map.get(handle_name, -1)
        elif self.is_rotation_handle(handle_name):
            self._is_rotating = True
            self._is_resizing = False
            self._is_adjusting_corner_radius = False
        else:
            self._is_resizing = True
            self._is_rotating = False
            self._is_adjusting_corner_radius = False
    
    def handle_mouse_move(self, scene_pos, modifiers=Qt.KeyboardModifier.NoModifier):
        """Logic to resize/transform based on handle movement."""
        pass

    def handle_mouse_release(self):
        """Called when the mouse is released after a transform."""
        self._is_resizing = False
        self._is_rotating = False
        self._is_adjusting_corner_radius = False
        self._active_corner_index = -1
        self._drag_mode = None

    def cleanup(self):
        """Clean up resources safely."""
        try:
            if self.scene() and self.scene_ref and self.scene() == self.scene_ref:
                # Remove self (which removes parented items automatically)
                self.scene_ref.removeItem(self)
        except Exception as e:
            logger.debug(f"Error during handler cleanup: {e}")
        finally:
            self._is_valid = False
            self._handles.clear()
            self._rotation_handles.clear()
            self._corner_radius_handles.clear()
            self.scene_ref = None
    
    def set_corner_radius_mode(self, enabled):
        """Enable or disable corner radius adjustment mode."""
        self._corner_radius_mode_enabled = enabled
        self._update_corner_radius_handles_visibility()
    
    def _update_corner_radius_handles_visibility(self):
        """Update visibility of corner radius handles based on mode and target item type."""
        # Override in subclasses to check if target item supports corner radius
        pass


class TransformHandler(BaseTransformHandler):
    """
    Manages selection handles for a single QGraphicsItem.
    """
    
    def __init__(self, target_item, scene, view_service):
        logger.debug("TransformHandler.__init__")
        self.target_item = target_item
        self._aspect_ratio = 1.0
        self._initial_rect = QRectF()
        self._initial_scene_rect = QRectF()
        self._initial_pos = QPointF()
        self._initial_rotation = 0.0
        self._initial_transform_origin = QPointF()
        self._anchor_scene_pos = QPointF()  # Anchor point in scene coordinates for resize

        # Initialize base class WITHOUT adding to scene yet
        super().__init__(scene, view_service)
        
        try:
            if self.validate():
                self.update_geometry()
                # NOW it is safe to add to scene because we are fully initialized
                self.addToScene() 
        except Exception as e:
            logger.error(f"Error initializing TransformHandler: {e}")
            self._is_valid = False

    def get_items(self):
        return [self.target_item]

    def validate(self):
        """Validate that target item still exists and is in scene."""
        try:
            if not self.target_item:
                self._is_valid = False
                return False
            
            if not self.target_item.scene():
                self._is_valid = False
                return False
            
            self._is_valid = True
            return True
        except Exception as e:
            logger.debug(f"Error validating handler: {e}")
            self._is_valid = False
            return False

    def boundingRect(self):
        """Return the bounding rect for the handler."""
        if not self.validate():
            return QRectF()
        
        try:
            return self.target_item.boundingRect()
        except Exception as e:
            logger.debug(f"Error getting target item bounding rect: {e}")
            return QRectF()

    def paint(self, painter, option, widget=None):
        """Draws the bounding box outline."""
        if not self.validate() or not painter:
            return
        
        try:
            rect = self.target_item.boundingRect()
            painter.setPen(self.border_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(rect)
        except Exception as e:
            logger.debug(f"Error painting transform handler: {e}")

    def update_geometry(self):
        """Updates the position of the handler and its handles to match the target."""
        if not self.validate():
            self.setVisible(False)
            # Hide rotation handles too
            for handle in self._rotation_handles.values():
                if handle:
                    handle.setVisible(False)
            return

        try:
            # Sync transform with target - INCLUDING transform origin point
            self.setPos(self.target_item.pos())
            self.setTransformOriginPoint(self.target_item.transformOriginPoint())
            self.setRotation(self.target_item.rotation())
            self.setTransform(self.target_item.transform())
            
            # Get local bounding rect of the target
            rect = self.target_item.boundingRect()
            
            # Update resize handle positions (in local coordinates - they are children)
            h = self._handles
            if rect.width() > 0 and rect.height() > 0:
                h['tl'].setPos(rect.topLeft())
                h['t'].setPos(QPointF(rect.center().x(), rect.top()))
                h['tr'].setPos(rect.topRight())
                h['r'].setPos(QPointF(rect.right(), rect.center().y()))
                h['br'].setPos(rect.bottomRight())
                h['b'].setPos(QPointF(rect.center().x(), rect.bottom()))
                h['bl'].setPos(rect.bottomLeft())
                h['l'].setPos(QPointF(rect.left(), rect.center().y()))
                
                # Update rotation handle positions in LOCAL coordinates of handler
                # Since handles are now parented to the handler, they move/rotate WITH it
                offset = self.ROTATION_HANDLE_OFFSET
                rh = self._rotation_handles
                
                # Get the 4 corners in LOCAL coordinates (relative to handler)
                # The handler's local coords ARE the same as the target's local coords
                # since the handler is positioned/rotated to match the target
                tl_local = rect.topLeft()
                tr_local = rect.topRight()
                bl_local = rect.bottomLeft()
                br_local = rect.bottomRight()
                
                # Calculate the direction vectors for offset (diagonal outward from center)
                center_local = rect.center()
                
                # Offset each corner diagonally away from center (in local space)
                def offset_from_center_local(corner, center, offset_dist):
                    dx = corner.x() - center.x()
                    dy = corner.y() - center.y()
                    length = math.sqrt(dx * dx + dy * dy)
                    if length > 0:
                        dx /= length
                        dy /= length
                    return QPointF(corner.x() + dx * offset_dist, corner.y() + dy * offset_dist)
                
                # Position in local coordinates - rotation automatically handled by parent
                rh['rot_tl'].setPos(offset_from_center_local(tl_local, center_local, offset))
                rh['rot_tr'].setPos(offset_from_center_local(tr_local, center_local, offset))
                rh['rot_bl'].setPos(offset_from_center_local(bl_local, center_local, offset))
                rh['rot_br'].setPos(offset_from_center_local(br_local, center_local, offset))
                
                # Make sure rotation handles are visible
                for handle in self._rotation_handles.values():
                    if handle:
                        handle.setVisible(True)
                
                # Update corner radius handle positions (inside corners)
                self._update_corner_radius_handle_positions(rect, tl_local, tr_local, br_local, bl_local)
            
            self.prepareGeometryChange()
            self.update()
        except Exception as e:
            logger.error(f"Error updating transform handler geometry: {e}")
            self._is_valid = False
    
    def _update_corner_radius_handle_positions(self, rect, tl_local, tr_local, br_local, bl_local):
        """Update positions of corner radius handles in LOCAL coordinates."""
        if not self._corner_radius_handles:
            return
        
        crh = self._corner_radius_handles
        offset = self.CORNER_RADIUS_HANDLE_OFFSET
        
        # Get current corner radii if target supports it
        corner_radii = [0, 0, 0, 0]
        if isinstance(self.target_item, RectangleObject):
            corner_radii = self.target_item.corner_radii
        
        # Position handles at each corner in LOCAL coordinates (no rotation needed - parent handles it)
        # TL corner - offset inward
        tl_offset = max(corner_radii[0], offset)
        crh['cr_tl'].setPos(tl_local.x() + tl_offset, tl_local.y() + tl_offset)
        
        # TR corner - offset inward
        tr_offset = max(corner_radii[1], offset)
        crh['cr_tr'].setPos(tr_local.x() - tr_offset, tr_local.y() + tr_offset)
        
        # BR corner - offset inward
        br_offset = max(corner_radii[2], offset)
        crh['cr_br'].setPos(br_local.x() - br_offset, br_local.y() - br_offset)
        
        # BL corner - offset inward
        bl_offset = max(corner_radii[3], offset)
        crh['cr_bl'].setPos(bl_local.x() + bl_offset, bl_local.y() - bl_offset)
    
    def _update_corner_radius_handles_visibility(self):
        """Update visibility of corner radius handles based on mode and target item type."""
        # Only show corner radius handles for RectangleObject when mode is enabled
        show_handles = (self._corner_radius_mode_enabled and 
                       isinstance(self.target_item, RectangleObject))
        
        for handle in self._corner_radius_handles.values():
            if handle:
                handle.setVisible(show_handles)
        
        # Also enable rounded mode on the item if it's a RectangleObject
        if isinstance(self.target_item, RectangleObject):
            self.target_item.rounded_enabled = self._corner_radius_mode_enabled

    def handle_mouse_press(self, handle_name, pos, scene_pos):
        """Called when a handle is pressed."""
        if not self.validate():
            return
        
        super().handle_mouse_press(handle_name, pos, scene_pos)
        
        try:
            if isinstance(self.target_item, BaseGraphicObject):
                self._initial_rect = QRectF(self.target_item.boundingRect())
                self._initial_pos = QPointF(self.target_item.pos())
                self._initial_rotation = self.target_item.rotation()
                self._initial_transform_origin = QPointF(self.target_item.transformOriginPoint())
                
                scene_rect = self.target_item.sceneBoundingRect()
                self._initial_scene_rect = QRectF(round(scene_rect.x()),
                                                  round(scene_rect.y()),
                                                  round(scene_rect.width()),
                                                  round(scene_rect.height()))
                if self._initial_rect.height() != 0:
                    self._aspect_ratio = self._initial_rect.width() / self._initial_rect.height()
                else:
                    self._aspect_ratio = 1.0
                
                # For resize, calculate anchor point (opposite corner/edge) in scene coordinates
                if not self.is_rotation_handle(handle_name):
                    rect = self._initial_rect
                    # Determine anchor point based on which handle is being dragged
                    anchor_local = QPointF()
                    if handle_name == 'tl':
                        anchor_local = rect.bottomRight()
                    elif handle_name == 'tr':
                        anchor_local = rect.bottomLeft()
                    elif handle_name == 'bl':
                        anchor_local = rect.topRight()
                    elif handle_name == 'br':
                        anchor_local = rect.topLeft()
                    elif handle_name == 't':
                        anchor_local = QPointF(rect.center().x(), rect.bottom())
                    elif handle_name == 'b':
                        anchor_local = QPointF(rect.center().x(), rect.top())
                    elif handle_name == 'l':
                        anchor_local = QPointF(rect.right(), rect.center().y())
                    elif handle_name == 'r':
                        anchor_local = QPointF(rect.left(), rect.center().y())
                    
                    # Map anchor to scene coordinates and round to prevent fractional propagation
                    anchor_scene = self.target_item.mapToScene(anchor_local)
                    self._anchor_scene_pos = QPointF(round(anchor_scene.x()), round(anchor_scene.y()))
                
                # For rotation, store initial rotation and calculate center
                if self.is_rotation_handle(handle_name):
                    self._initial_item_rotation = self.target_item.rotation()
                    # Calculate center in scene coordinates
                    rect = self.target_item.boundingRect()
                    center_local = rect.center()
                    self._rotation_center = self.target_item.mapToScene(center_local)
                    # Calculate initial angle from center to mouse
                    dx = scene_pos.x() - self._rotation_center.x()
                    dy = scene_pos.y() - self._rotation_center.y()
                    self._rotation_start_angle = math.degrees(math.atan2(dy, dx))
                
                # For corner radius, store initial corner radii
                if self.is_corner_radius_handle(handle_name):
                    if isinstance(self.target_item, RectangleObject):
                        self._initial_corner_radii = self.target_item.corner_radii.copy()
                    else:
                        self._initial_corner_radii = [0.0, 0.0, 0.0, 0.0]
                    
        except Exception as e:
            logger.warning(f"Error storing initial rect: {e}")

    def handle_mouse_move(self, scene_pos, modifiers=Qt.KeyboardModifier.NoModifier):
        """Logic to resize or rotate the target item based on the active handle."""
        if not self._drag_mode or not self.validate():
            return

        if not isinstance(self.target_item, BaseGraphicObject):
            return
        
        # Handle corner radius adjustment
        if self._is_adjusting_corner_radius:
            self._handle_corner_radius(scene_pos, modifiers)
            return
        
        # Handle rotation
        if self._is_rotating:
            self._handle_rotation(scene_pos, modifiers)
            return
            
        # Handle resize - works in local coordinates to support rotated objects
        try:
            logger.debug(f"Handling mouse move for single item. Drag mode: {self._drag_mode}, Scene pos: {scene_pos}")
            
            # Convert scene position to local coordinates using the INITIAL transform state
            # This prevents feedback loops that cause flickering
            rotation_rad = math.radians(self._initial_rotation)
            cos_r = math.cos(-rotation_rad)
            sin_r = math.sin(-rotation_rad)
            
            # Get initial transform origin in scene space
            initial_origin_scene = QPointF(
                self._initial_pos.x() + self._initial_transform_origin.x(),
                self._initial_pos.y() + self._initial_transform_origin.y()
            )
            
            # Translate scene_pos relative to the initial rotation center
            dx = scene_pos.x() - initial_origin_scene.x()
            dy = scene_pos.y() - initial_origin_scene.y()
            
            # Rotate back to local space
            local_x = dx * cos_r - dy * sin_r
            local_y = dx * sin_r + dy * cos_r
            
            # Add back the transform origin offset to get local coordinates
            local_pos = QPointF(
                local_x + self._initial_transform_origin.x(),
                local_y + self._initial_transform_origin.y()
            )
            
            # Start with the initial local rect
            new_rect = QRectF(self._initial_rect)
            
            # Update rect based on handle and mouse position in local coordinates
            if 'l' in self._drag_mode: new_rect.setLeft(local_pos.x())
            if 'r' in self._drag_mode: new_rect.setRight(local_pos.x())
            if 't' in self._drag_mode: new_rect.setTop(local_pos.y())
            if 'b' in self._drag_mode: new_rect.setBottom(local_pos.y())

            # Aspect Ratio Lock for corner drags
            maintain_aspect = (modifiers & Qt.KeyboardModifier.ShiftModifier) and \
                              (self._drag_mode in ['tl', 'tr', 'bl', 'br'])
                              
            if maintain_aspect and self._aspect_ratio > 0:
                w = new_rect.width()
                h = new_rect.height()
                
                if h != 0 and abs(w / h) > abs(self._aspect_ratio):
                    h = w / self._aspect_ratio
                    if 't' in self._drag_mode: new_rect.setTop(new_rect.bottom() - h)
                    else: new_rect.setBottom(new_rect.top() + h)
                elif h != 0:
                    w = h * self._aspect_ratio
                    if 'l' in self._drag_mode: new_rect.setLeft(new_rect.right() - w)
                    else: new_rect.setRight(new_rect.left() + w)

            final_rect = new_rect.normalized()

            # Enforce Minimum Size
            if final_rect.width() < 1: final_rect.setWidth(1)
            if final_rect.height() < 1: final_rect.setHeight(1)
            
            snapped_width = round(final_rect.width())
            snapped_height = round(final_rect.height())
            
            # Calculate the new geometry rect (normalized to start at 0,0)
            new_geometry = QRectF(0, 0, snapped_width, snapped_height)
            
            # Calculate new transform origin (center of new geometry)
            # Use integer division to avoid .5 fractional values that cause rounding inconsistencies
            new_center_x = snapped_width // 2
            new_center_y = snapped_height // 2
            new_center = QPointF(new_center_x, new_center_y)
            
            # For non-rotated objects, preserve fixed coordinates based on handle type
            # This prevents position flickering caused by rounding errors
            is_rotated = abs(self._initial_rotation) > 0.001
            
            if not is_rotated:
                # For non-rotated objects, directly calculate position based on handle
                # Right, Bottom, BottomRight: X and Y should NOT change
                # Left, BottomLeft: Y should NOT change  
                # Top, TopRight: X should NOT change
                # TopLeft: both X and Y can change
                
                initial_x = round(self._initial_pos.x())
                initial_y = round(self._initial_pos.y())
                
                if self._drag_mode in ['r', 'b', 'br']:
                    # Anchor is at top-left area, position should not change
                    new_pos_x = initial_x
                    new_pos_y = initial_y
                elif self._drag_mode == 'l':
                    # Dragging left edge: X changes, Y stays fixed
                    # New X = anchor_right - new_width
                    new_pos_x = round(self._anchor_scene_pos.x()) - snapped_width
                    new_pos_y = initial_y
                elif self._drag_mode == 'bl':
                    # Dragging bottom-left: X changes, Y stays fixed
                    new_pos_x = round(self._anchor_scene_pos.x()) - snapped_width
                    new_pos_y = initial_y
                elif self._drag_mode == 't':
                    # Dragging top edge: Y changes, X stays fixed
                    new_pos_x = initial_x
                    new_pos_y = round(self._anchor_scene_pos.y()) - snapped_height
                elif self._drag_mode == 'tr':
                    # Dragging top-right: Y changes, X stays fixed
                    new_pos_x = initial_x
                    new_pos_y = round(self._anchor_scene_pos.y()) - snapped_height
                elif self._drag_mode == 'tl':
                    # Dragging top-left: both X and Y change
                    new_pos_x = round(self._anchor_scene_pos.x()) - snapped_width
                    new_pos_y = round(self._anchor_scene_pos.y()) - snapped_height
                else:
                    new_pos_x = initial_x
                    new_pos_y = initial_y
            else:
                # For rotated objects, use the full anchor-based calculation
                # Determine anchor point in the NEW local rect based on handle
                new_anchor_local = QPointF()
                if self._drag_mode == 'tl':
                    new_anchor_local = new_geometry.bottomRight()
                elif self._drag_mode == 'tr':
                    new_anchor_local = new_geometry.bottomLeft()
                elif self._drag_mode == 'bl':
                    new_anchor_local = new_geometry.topRight()
                elif self._drag_mode == 'br':
                    new_anchor_local = new_geometry.topLeft()
                elif self._drag_mode == 't':
                    new_anchor_local = QPointF(new_center_x, new_geometry.bottom())
                elif self._drag_mode == 'b':
                    new_anchor_local = QPointF(new_center_x, new_geometry.top())
                elif self._drag_mode == 'l':
                    new_anchor_local = QPointF(new_geometry.right(), new_center_y)
                elif self._drag_mode == 'r':
                    new_anchor_local = QPointF(new_geometry.left(), new_center_y)
                
                # Calculate position so anchor stays fixed in scene
                # Vector from new center to anchor in local space
                anchor_from_center_x = new_anchor_local.x() - new_center_x
                anchor_from_center_y = new_anchor_local.y() - new_center_y
                
                # Rotate this vector to scene space (positive rotation)
                cos_r_pos = math.cos(rotation_rad)
                sin_r_pos = math.sin(rotation_rad)
                rotated_anchor_x = anchor_from_center_x * cos_r_pos - anchor_from_center_y * sin_r_pos
                rotated_anchor_y = anchor_from_center_x * sin_r_pos + anchor_from_center_y * cos_r_pos
                
                # The anchor in scene = pos + new_center + rotated_anchor_offset
                # So: pos = anchor_scene - new_center - rotated_anchor_offset
                new_pos_x = self._anchor_scene_pos.x() - new_center_x - rotated_anchor_x
                new_pos_y = self._anchor_scene_pos.y() - new_center_y - rotated_anchor_y
            
            # Apply all changes with batching to prevent intermediate snap intercepts
            self.prepareGeometryChange()
            try:
                self.target_item.set_transform_in_progress(True)
                self.target_item.set_geometry(new_geometry)
                self.target_item.setTransformOriginPoint(new_center)
                self.target_item.setPos(round(new_pos_x), round(new_pos_y))
            finally:
                self.target_item.set_transform_in_progress(False)
            
            self.update_geometry()
            logger.debug("Successfully handled mouse move for single item.")

        except Exception as e:
            logger.error(f"CRITICAL: Exception in TransformHandler.handle_mouse_move: {e}", exc_info=True)

    def _handle_corner_radius(self, scene_pos, modifiers=Qt.KeyboardModifier.NoModifier):
        """Handle corner radius adjustment for rounded rectangles."""
        try:
            if not isinstance(self.target_item, RectangleObject):
                return
            
            # Get the rect and corner positions
            rect = self.target_item.boundingRect()
            
            # Get corner position in scene coordinates
            corner_map = {
                0: rect.topLeft(),      # TL
                1: rect.topRight(),     # TR
                2: rect.bottomRight(),  # BR
                3: rect.bottomLeft()    # BL
            }
            
            if self._active_corner_index < 0 or self._active_corner_index > 3:
                return
            
            corner_local = corner_map[self._active_corner_index]
            corner_scene = self.target_item.mapToScene(corner_local)
            
            # Calculate distance from corner to current mouse position
            dx = scene_pos.x() - corner_scene.x()
            dy = scene_pos.y() - corner_scene.y()
            
            # Account for object rotation by rotating the drag vector back to local space
            rotation_angle = self.target_item.rotation() if isinstance(self.target_item, BaseGraphicObject) else 0
            rotation_rad = math.radians(rotation_angle)
            cos_r = math.cos(-rotation_rad)  # Negative to rotate back
            sin_r = math.sin(-rotation_rad)
            
            # Rotate the drag vector to local coordinates
            dx_local = dx * cos_r - dy * sin_r
            dy_local = dx * sin_r + dy * cos_r
            
            # Direction multipliers based on corner (in local space)
            # TL: inward is +x, +y  |  TR: inward is -x, +y
            # BR: inward is -x, -y  |  BL: inward is +x, -y
            dir_mult = {
                0: (1, 1),    # TL
                1: (-1, 1),   # TR
                2: (-1, -1),  # BR
                3: (1, -1)    # BL
            }
            
            mult_x, mult_y = dir_mult[self._active_corner_index]
            
            # Calculate the inward distance (positive when dragging inside)
            inward_x = dx_local * mult_x
            inward_y = dy_local * mult_y
            
            # Use the minimum of x and y as the radius (to keep it symmetric per corner)
            radius = max(0, min(inward_x, inward_y))
            
            # Clamp to half the smallest dimension
            max_radius = min(rect.width(), rect.height()) / 2.0
            radius = min(radius, max_radius)
            
            # Apply to corner(s) based on Shift modifier
            if modifiers & Qt.KeyboardModifier.ShiftModifier:
                # Shift held: apply same radius to all corners
                self.target_item.set_all_corner_radii(radius)
            else:
                # No Shift: only adjust the active corner
                self.target_item.set_corner_radius(self._active_corner_index, radius)
            
            # Update handler geometry to reposition handles
            self.update_geometry()
            
            logger.debug(f"Corner radius applied: corner={self._active_corner_index}, radius={radius}")
            
        except Exception as e:
            logger.error(f"Error handling corner radius: {e}", exc_info=True)
            
        except Exception as e:
            logger.error(f"Error handling corner radius: {e}", exc_info=True)

    def _handle_rotation(self, scene_pos, modifiers=Qt.KeyboardModifier.NoModifier):
        """Handle rotation of the target item around its center."""
        try:
            # Calculate current angle from center to mouse position
            dx = scene_pos.x() - self._rotation_center.x()
            dy = scene_pos.y() - self._rotation_center.y()
            current_angle = math.degrees(math.atan2(dy, dx))
            
            # Calculate rotation delta
            angle_delta = current_angle - self._rotation_start_angle
            
            # Calculate new rotation angle
            new_rotation = self._initial_item_rotation + angle_delta
            
            # Snap to 15° increments when Shift is held
            if modifiers & Qt.KeyboardModifier.ShiftModifier:
                new_rotation = round(new_rotation / 15) * 15
            
            # Normalize angle to -360 to 360 range
            while new_rotation > 360:
                new_rotation -= 360
            while new_rotation < -360:
                new_rotation += 360
            
            # Set transform origin to center and apply rotation
            rect = self.target_item.boundingRect()
            center = rect.center()
            self.target_item.setTransformOriginPoint(center)
            self.target_item.setRotation(new_rotation)
            
            # Update handler geometry
            self.update_geometry()
            
            logger.debug(f"Rotation applied: {new_rotation}°")
            
        except Exception as e:
            logger.error(f"Error handling rotation: {e}", exc_info=True)

    def get_current_rotation(self):
        """Get the current rotation angle of the target item."""
        if self.validate() and self.target_item:
            return self.target_item.rotation()
        return 0.0


class AverageTransformHandler(BaseTransformHandler):
    """
    Manages selection handles for multiple QGraphicsItems.
    """
    
    def __init__(self, target_items, scene, view_service):
        logger.debug("AverageTransformHandler.__init__")
        self.target_items = list(target_items) if target_items else []
        self._initial_rects = {}
        self._initial_positions = {}
        self._initial_avg_rect = QRectF()
        self._average_rect = QRectF()
        
        self.border_pen = QPen(QColor(colors.COLOR_TRANSFORM_BORDER), 2, Qt.PenStyle.SolidLine)
        self.border_pen.setCosmetic(True)
        
        super().__init__(scene, view_service)
        
        try:
            if self.validate():
                self.update_geometry()
                # NOW it is safe to add to scene
                self.addToScene()
        except Exception as e:
            logger.error(f"Error initializing AverageTransformHandler: {e}")
            self._is_valid = False

    def get_items(self):
        return self.target_items

    def validate(self):
        """Validate that all target items still exist and are in scene."""
        try:
            if not self.target_items:
                self._is_valid = False
                return False
            
            valid_count = 0
            for item in self.target_items:
                try:
                    if item and item.scene():
                        valid_count += 1
                except Exception as e:
                    logger.debug(f"Item validation error: {e}")
            
            if valid_count == 0:
                self._is_valid = False
                return False
            
            self._is_valid = True
            return True
        except Exception as e:
            logger.debug(f"Error validating average handler: {e}")
            self._is_valid = False
            return False

    def _calculate_average_rect(self):
        """Calculate the average bounding rectangle from all selected items."""
        if not self.validate():
            return QRectF()
        
        try:
            min_x = float('inf')
            min_y = float('inf')
            max_x = float('-inf')
            max_y = float('-inf')
            
            has_valid_item = False
            for item in self.target_items:
                try:
                    if not item or not item.scene(): continue
                    
                    scene_rect = item.sceneBoundingRect()
                    if scene_rect.isNull() or scene_rect.width() < 1 or scene_rect.height() < 1:
                        continue
                    
                    min_x = min(min_x, scene_rect.left())
                    min_y = min(min_y, scene_rect.top())
                    max_x = max(max_x, scene_rect.right())
                    max_y = max(max_y, scene_rect.bottom())
                    has_valid_item = True
                except Exception as e:
                    logger.debug(f"Error getting item bounding rect: {e}")
                    continue
            
            if not has_valid_item or min_x == float('inf') or max_x == float('-inf'):
                return QRectF()
            
            width = max_x - min_x
            height = max_y - min_y
            
            if width < 1 or height < 1:
                return QRectF()
            
            return QRectF(min_x, min_y, width, height)
        except Exception as e:
            logger.error(f"Error calculating average rect: {e}")
            return QRectF()

    def boundingRect(self):
        """Return the bounding rect for the handler."""
        if self._average_rect.isNull():
            return QRectF()
        return QRectF(0, 0, self._average_rect.width(), self._average_rect.height())

    def paint(self, painter, option, widget=None):
        if not self.validate() or self._average_rect.isNull() or not painter:
            return
        try:
            # Draw individual highlights for selected items
            # Use a dashed magenta line for individual items to distinguish them
            painter.save()
            individual_pen = QPen(QColor(colors.COLOR_TRANSFORM_INDIVIDUAL), 2, Qt.PenStyle.DashLine)
            individual_pen.setCosmetic(True)
            painter.setPen(individual_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)

            handler_pos = self.pos()

            for item in self.target_items:
                try:
                    if item and item.scene():
                        # Get item's rect in scene coordinates
                        scene_rect = item.sceneBoundingRect()
                        
                        # Calculate position relative to this handler
                        local_x = scene_rect.x() - handler_pos.x()
                        local_y = scene_rect.y() - handler_pos.y()
                        
                        painter.drawRect(QRectF(local_x, local_y, scene_rect.width(), scene_rect.height()))
                except Exception as e:
                    logger.debug(f"Error drawing individual selection: {e}")
            
            painter.restore()

            # Draw the main group bounding box (Green)
            painter.setPen(self.border_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            local_rect = QRectF(0, 0, self._average_rect.width(), self._average_rect.height())
            painter.drawRect(local_rect)
        except Exception as e:
            logger.debug(f"Error painting average transform handler: {e}")

    def update_geometry(self):
        if not self.validate():
            self.setVisible(False)
            # Hide rotation handles too
            for handle in self._rotation_handles.values():
                if handle:
                    handle.setVisible(False)
            return

        try:
            new_rect = self._calculate_average_rect()
            if new_rect.isNull():
                self.setVisible(False)
                # Hide rotation handles
                for handle in self._rotation_handles.values():
                    if handle:
                        handle.setVisible(False)
                return
            
            self.prepareGeometryChange()
            self._average_rect = new_rect
            
            self.setVisible(True)
            self.setPos(self._average_rect.topLeft())
            
            h = self._handles
            if self._average_rect.width() > 0 and self._average_rect.height() > 0:
                local_rect = QRectF(0, 0, self._average_rect.width(), self._average_rect.height())
                h['tl'].setPos(local_rect.topLeft())
                h['t'].setPos(QPointF(local_rect.center().x(), local_rect.top()))
                h['tr'].setPos(local_rect.topRight())
                h['r'].setPos(QPointF(local_rect.right(), local_rect.center().y()))
                h['br'].setPos(local_rect.bottomRight())
                h['b'].setPos(QPointF(local_rect.center().x(), local_rect.bottom()))
                h['bl'].setPos(local_rect.bottomLeft())
                h['l'].setPos(QPointF(local_rect.left(), local_rect.center().y()))
                
                # Update rotation handle positions in LOCAL coordinates
                # For AverageTransformHandler, the handler is not rotated
                # So local coords = relative to handler position
                offset = self.ROTATION_HANDLE_OFFSET
                rh = self._rotation_handles
                
                # Position rotation handles at corners with diagonal offset (in local space)
                local_rect = QRectF(0, 0, self._average_rect.width(), self._average_rect.height())
                center_local = local_rect.center()
                
                # Offset outward from center for each corner
                def offset_from_center(corner, center, offset_dist):
                    dx = corner.x() - center.x()
                    dy = corner.y() - center.y()
                    length = math.sqrt(dx * dx + dy * dy)
                    if length > 0:
                        dx /= length
                        dy /= length
                    return QPointF(corner.x() + dx * offset_dist, corner.y() + dy * offset_dist)
                
                rh['rot_tl'].setPos(offset_from_center(local_rect.topLeft(), center_local, offset))
                rh['rot_tr'].setPos(offset_from_center(local_rect.topRight(), center_local, offset))
                rh['rot_bl'].setPos(offset_from_center(local_rect.bottomLeft(), center_local, offset))
                rh['rot_br'].setPos(offset_from_center(local_rect.bottomRight(), center_local, offset))
                
                # Make sure rotation handles are visible
                for handle in self._rotation_handles.values():
                    if handle:
                        handle.setVisible(True)
            
            self.update()
        except Exception as e:
            logger.error(f"Error updating average transform handler geometry: {e}")
            self._is_valid = False

    def handle_mouse_press(self, handle_name, pos, scene_pos):
        if not self.validate(): return
        super().handle_mouse_press(handle_name, pos, scene_pos)
        
        try:
            self._initial_rects = {}
            self._initial_positions = {}
            self._initial_rotations = {}
            
            for item in self.target_items:
                try:
                    if isinstance(item, BaseGraphicObject) and item.scene():
                        item_id = id(item)
                        self._initial_rects[item_id] = (QRectF(item.boundingRect()), item)
                        self._initial_positions[item_id] = (QPointF(round(item.pos().x()), round(item.pos().y())), item)
                        self._initial_rotations[item_id] = (item.rotation(), item)
                except Exception as e:
                    logger.debug(f"Error storing item state: {e}")
            
            if self._initial_rects:
                avg_rect = self._calculate_average_rect()
                if not avg_rect.isNull():
                    self._initial_avg_rect = QRectF(round(avg_rect.x()), round(avg_rect.y()), round(avg_rect.width()), round(avg_rect.height()))
                    
                    # For rotation, store center of average rect
                    if self.is_rotation_handle(handle_name):
                        self._rotation_center = avg_rect.center()
                        # Calculate initial angle from center to mouse
                        dx = scene_pos.x() - self._rotation_center.x()
                        dy = scene_pos.y() - self._rotation_center.y()
                        self._rotation_start_angle = math.degrees(math.atan2(dy, dx))
                        
        except Exception as e:
            logger.warning(f"Error in handle_mouse_press: {e}")

    def handle_mouse_move(self, scene_pos, modifiers=Qt.KeyboardModifier.NoModifier):
        if not self._drag_mode or not self.validate(): return
        if self._initial_avg_rect.isNull(): return
        
        # Handle rotation
        if self._is_rotating:
            self._handle_rotation(scene_pos, modifiers)
            return
        
        try:
            new_rect = QRectF(self._initial_avg_rect)
            # Round scene position to prevent fractional accumulation
            snapped_pos = QPointF(round(scene_pos.x()), round(scene_pos.y()))
            
            if 'r' in str(self._drag_mode): new_rect.setRight(snapped_pos.x())
            if 'l' in str(self._drag_mode): new_rect.setLeft(snapped_pos.x())
            if 'b' in str(self._drag_mode): new_rect.setBottom(snapped_pos.y())
            if 't' in str(self._drag_mode): new_rect.setTop(snapped_pos.y())
            
            new_rect = new_rect.normalized()
            
            old_width = self._initial_avg_rect.width()
            old_height = self._initial_avg_rect.height()
            new_width = round(new_rect.width())
            new_height = round(new_rect.height())
            
            if old_width < 1 or old_height < 1 or new_width < 1 or new_height < 1:
                return
            
            scale_x = new_width / old_width
            scale_y = new_height / old_height
            
            # Determine which coordinates should be preserved based on handle type
            # This prevents position flickering caused by rounding errors
            drag_mode = str(self._drag_mode)
            preserve_x = drag_mode in ['r', 'b', 'br', 't', 'tr']  # X should not change
            preserve_y = drag_mode in ['r', 'b', 'br', 'l', 'bl']  # Y should not change
            
            # Calculate new rect position based on handle
            # For r, b, br: top-left stays fixed
            # For l, bl: top-right stays fixed (X changes)
            # For t, tr: bottom-left stays fixed (Y changes)
            # For tl: bottom-right stays fixed (both change)
            new_rect_left = round(self._initial_avg_rect.left()) if preserve_x else round(new_rect.left())
            new_rect_top = round(self._initial_avg_rect.top()) if preserve_y else round(new_rect.top())
            
            # Batch transform operations to prevent snap intercepts
            for item in self.target_items:
                if isinstance(item, BaseGraphicObject) and item.scene():
                    item.set_transform_in_progress(True)
            
            try:
                for item_id, (initial_rect, item) in self._initial_rects.items():
                    try:
                        if isinstance(item, BaseGraphicObject) and item.scene():
                            scaled_width = round(initial_rect.width() * scale_x)
                            scaled_height = round(initial_rect.height() * scale_y)
                            
                            if scaled_width < 1 or scaled_height < 1: continue
                            
                            new_item_rect = QRectF(0, 0, scaled_width, scaled_height)
                            item.set_geometry(new_item_rect)
                            
                            # Set transform origin to integer center
                            new_center_x = scaled_width // 2
                            new_center_y = scaled_height // 2
                            item.setTransformOriginPoint(QPointF(new_center_x, new_center_y))
                            
                            initial_pos, _ = self._initial_positions.get(item_id, (QPointF(0, 0), None))
                            
                            # Calculate position based on whether coordinates should be preserved
                            if preserve_x and preserve_y:
                                # Both X and Y preserved (r, b, br handles)
                                # Position stays relative to initial avg rect top-left
                                offset_x = initial_pos.x() - self._initial_avg_rect.left()
                                offset_y = initial_pos.y() - self._initial_avg_rect.top()
                                new_x = new_rect_left + offset_x * scale_x
                                new_y = new_rect_top + offset_y * scale_y
                            elif preserve_y:
                                # Only Y preserved (l, bl handles)
                                offset_x = initial_pos.x() - self._initial_avg_rect.left()
                                offset_y = initial_pos.y() - self._initial_avg_rect.top()
                                new_x = new_rect_left + offset_x * scale_x
                                new_y = new_rect_top + offset_y * scale_y
                            elif preserve_x:
                                # Only X preserved (t, tr handles)
                                offset_x = initial_pos.x() - self._initial_avg_rect.left()
                                offset_y = initial_pos.y() - self._initial_avg_rect.top()
                                new_x = new_rect_left + offset_x * scale_x
                                new_y = new_rect_top + offset_y * scale_y
                            else:
                                # Neither preserved (tl handle)
                                offset_x = initial_pos.x() - self._initial_avg_rect.left()
                                offset_y = initial_pos.y() - self._initial_avg_rect.top()
                                new_x = new_rect_left + offset_x * scale_x
                                new_y = new_rect_top + offset_y * scale_y
                            
                            item.setPos(round(new_x), round(new_y))
                    except Exception as e:
                        logger.debug(f"Error transforming item: {e}")
            finally:
                # Clear the batching flag
                for item in self.target_items:
                    if isinstance(item, BaseGraphicObject) and item.scene():
                        item.set_transform_in_progress(False)
            
            self.update_geometry()
        except Exception as e:
            logger.error(f"CRITICAL: Exception in AverageTransformHandler.handle_mouse_move: {e}", exc_info=True)

    def _handle_rotation(self, scene_pos, modifiers=Qt.KeyboardModifier.NoModifier):
        """Handle rotation of multiple items around their combined center."""
        try:
            # Calculate current angle from center to mouse position
            dx = scene_pos.x() - self._rotation_center.x()
            dy = scene_pos.y() - self._rotation_center.y()
            current_angle = math.degrees(math.atan2(dy, dx))
            
            # Calculate rotation delta
            angle_delta = current_angle - self._rotation_start_angle
            
            # Snap to 15° increments when Shift is held
            if modifiers & Qt.KeyboardModifier.ShiftModifier:
                angle_delta = round(angle_delta / 15) * 15
            
            # Batch transform operations to prevent snap intercepts during rotation
            for item in self.target_items:
                if isinstance(item, BaseGraphicObject) and item.scene():
                    item.set_transform_in_progress(True)
            
            try:
                # Apply rotation to each item
                for item_id, (initial_rotation, item) in self._initial_rotations.items():
                    try:
                        if isinstance(item, BaseGraphicObject) and item.scene():
                            # Get initial position
                            initial_pos, _ = self._initial_positions.get(item_id, (QPointF(0, 0), None))
                            
                            # Calculate new rotation
                            new_rotation = initial_rotation + angle_delta
                            
                            # Normalize angle
                            while new_rotation > 360:
                                new_rotation -= 360
                            while new_rotation < -360:
                                new_rotation += 360
                            
                            # Calculate item center in scene coordinates
                            initial_rect, _ = self._initial_rects.get(item_id, (QRectF(), None))
                            item_center = QPointF(
                                initial_pos.x() + initial_rect.width() / 2,
                                initial_pos.y() + initial_rect.height() / 2
                            )
                            
                            # Rotate item position around the group center
                            angle_rad = math.radians(angle_delta)
                            cos_a = math.cos(angle_rad)
                            sin_a = math.sin(angle_rad)
                            
                            # Translate to origin (center), rotate, translate back
                            rel_x = item_center.x() - self._rotation_center.x()
                            rel_y = item_center.y() - self._rotation_center.y()
                            
                            new_center_x = self._rotation_center.x() + (rel_x * cos_a - rel_y * sin_a)
                            new_center_y = self._rotation_center.y() + (rel_x * sin_a + rel_y * cos_a)
                            
                            # Calculate new position (top-left corner)
                            new_x = new_center_x - initial_rect.width() / 2
                            new_y = new_center_y - initial_rect.height() / 2
                            
                            # Apply position and rotation in batch
                            item.setPos(round(new_x), round(new_y))
                            
                            # Set transform origin to center and apply rotation
                            rect = item.boundingRect()
                            center = rect.center()
                            item.setTransformOriginPoint(center)
                            item.setRotation(new_rotation)
                            
                    except Exception as e:
                        logger.debug(f"Error rotating item: {e}")
            finally:
                # Clear the batching flag for all items
                for item in self.target_items:
                    if isinstance(item, BaseGraphicObject) and item.scene():
                        item.set_transform_in_progress(False)
            
            self.update_geometry()
            logger.debug(f"Group rotation applied: {angle_delta}°")
            
        except Exception as e:
            logger.error(f"Error handling group rotation: {e}", exc_info=True)

    def get_current_rotation(self):
        """Get the average current rotation angle of the target items."""
        if not self.validate() or not self.target_items:
            return 0.0
        
        total_rotation = 0.0
        count = 0
        for item in self.target_items:
            if isinstance(item, BaseGraphicObject) and item.scene():
                total_rotation += item.rotation()
                count += 1
        
        return total_rotation / count if count > 0 else 0.0

    def cleanup(self):
        try:
            if self.target_items: self.target_items.clear()
            if self._initial_rects: self._initial_rects.clear()
            if self._initial_positions: self._initial_positions.clear()
            if hasattr(self, '_initial_rotations') and self._initial_rotations:
                self._initial_rotations.clear()
        except Exception as e:
            logger.debug(f"Error during average handler cleanup: {e}")
        finally:
            super().cleanup()