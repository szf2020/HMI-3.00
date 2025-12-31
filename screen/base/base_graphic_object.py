# screen\base\base_graphic_object.py
from PySide6.QtWidgets import QGraphicsRectItem, QGraphicsEllipseItem, QGraphicsItem, QGraphicsPathItem
from PySide6.QtCore import QRectF, QPointF, Qt
from PySide6.QtGui import QPainterPath, QPen, QBrush
from debug_utils import get_logger

logger = get_logger(__name__)


class HiddenQGraphicsRectItem(QGraphicsRectItem):
    """
    A QGraphicsRectItem that doesn't paint itself.
    Used as a composed item to provide geometry management without visual rendering.
    """
    def paint(self, painter, option, widget=None):
        # Don't paint anything - parent will handle all rendering
        pass


class BaseGraphicObject(QGraphicsItem):
    """
    Abstract base class for all drawable objects on the canvas.
    It defines a common interface for geometric transformations.
    """

    def __init__(self, item, view_service=None, view=None, parent=None):
        super().__init__(parent)
        self.item = item
        self.item.setParentItem(self)
        self.view_service = view_service
        self.view = view
        # Flag to disable snap offset during transform handler operations
        self._transform_in_progress = False

    def boundingRect(self):
        return self.item.boundingRect()

    def paint(self, painter, option, widget):
        # The painting is delegated to the composed item.
        # This allows us to use standard QGraphics*Item painting behavior.
        pass

    def set_geometry(self, rect: QRectF):
        """
        Sets the geometry of the object. This must be implemented by subclasses.
        This is the key method for the TransformHandler to be generic.
        """
        raise NotImplementedError("This method should be implemented by subclasses.")

    def set_transform_in_progress(self, in_progress):
        """Flag to disable snap logic during handler-driven transforms."""
        self._transform_in_progress = in_progress

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange and self.scene():
            new_pos = value
            
            # Skip snap logic if transform is being driven by the handler
            if self._transform_in_progress:
                new_pos.setX(round(new_pos.x()))
                new_pos.setY(round(new_pos.y()))
                return new_pos
            
            if self.view_service and self.view_service.snap_enabled:
                if self.view_service.snapping_mode == 'grid':
                    grid_size = self.view_service.grid_size
                    new_pos.setX(round(new_pos.x() / grid_size) * grid_size)
                    new_pos.setY(round(new_pos.y() / grid_size) * grid_size)
                    return new_pos
                elif self.view_service.snapping_mode == 'object':
                    try:
                        # Magnetic snapping: attempt to align edges/centers to nearby objects
                        threshold = float(self.view_service.grid_size)

                        # Compute candidate moving rect at the new position
                        br = self.boundingRect()
                        m_left = new_pos.x() + br.left()
                        m_right = new_pos.x() + br.right()
                        m_top = new_pos.y() + br.top()
                        m_bottom = new_pos.y() + br.bottom()
                        m_v_center = new_pos.y() + br.center().y()
                        m_h_center = new_pos.x() + br.center().x()

                        best_dx = 0.0
                        best_dy = 0.0
                        best_dist_x = threshold
                        best_dist_y = threshold

                        static_items = [
                            it for it in self.scene().items()
                            if isinstance(it, BaseGraphicObject) and it is not self
                            and it.isVisible() and it.data(Qt.ItemDataRole.UserRole) is not None
                        ]

                        for static in static_items:
                            srect = static.sceneBoundingRect()
                            s_left, s_right = srect.left(), srect.right()
                            s_top, s_bottom = srect.top(), srect.bottom()
                            s_v_center = srect.center().y()
                            s_h_center = srect.center().x()

                            snap_pairs_x = [
                                (m_left, s_left), (m_left, s_right), (m_left, s_h_center),
                                (m_right, s_left), (m_right, s_right), (m_right, s_h_center),
                                (m_h_center, s_left), (m_h_center, s_right), (m_h_center, s_h_center)
                            ]
                            for m_edge, s_edge in snap_pairs_x:
                                dist = s_edge - m_edge
                                if abs(dist) < abs(best_dist_x):
                                    best_dist_x = abs(dist)
                                    best_dx = dist

                            snap_pairs_y = [
                                (m_top, s_top), (m_top, s_bottom), (m_top, s_v_center),
                                (m_bottom, s_top), (m_bottom, s_bottom), (m_bottom, s_v_center),
                                (m_v_center, s_top), (m_v_center, s_bottom), (m_v_center, s_v_center)
                            ]
                            for m_edge, s_edge in snap_pairs_y:
                                dist = s_edge - m_edge
                                if abs(dist) < abs(best_dist_y):
                                    best_dist_y = abs(dist)
                                    best_dy = dist

                        # Prefer the closest axis only
                        if abs(best_dx) > 0 and abs(best_dx) <= threshold and (abs(best_dx) < abs(best_dy) or abs(best_dy) > threshold):
                            new_pos.setX(round(new_pos.x() + best_dx))
                        if abs(best_dy) > 0 and abs(best_dy) <= threshold and (abs(best_dy) < abs(best_dx) or abs(best_dx) > threshold):
                            new_pos.setY(round(new_pos.y() + best_dy))

                        return new_pos
                    except Exception:
                        pass

            # Fallback: round to integer positions to avoid fractional coords
            new_pos.setX(round(new_pos.x()))
            new_pos.setY(round(new_pos.y()))
            return new_pos

        return super().itemChange(change, value)


class RectangleObject(BaseGraphicObject):
    """
    A concrete implementation for a rectangle object.
    Supports individual corner radius for rounded corners.
    """
    def __init__(self, rect: QRectF, view_service=None, view=None, parent=None):
        # Use HiddenQGraphicsRectItem that doesn't paint itself
        hidden_rect = HiddenQGraphicsRectItem(rect)
        super().__init__(hidden_rect, view_service, view, parent)
        # Corner radii: [top_left, top_right, bottom_right, bottom_left]
        self._corner_radii = [0.0, 0.0, 0.0, 0.0]
        self._rounded_enabled = False

    @property
    def rect_item(self) -> QGraphicsRectItem:
        return self.item

    @property
    def corner_radii(self):
        """Get corner radii [top_left, top_right, bottom_right, bottom_left]."""
        return self._corner_radii.copy()
    
    @corner_radii.setter
    def corner_radii(self, radii):
        """Set corner radii [top_left, top_right, bottom_right, bottom_left]."""
        if len(radii) == 4:
            self._corner_radii = list(radii)
            self.update()
    
    @property
    def rounded_enabled(self):
        """Check if rounded corners are enabled."""
        return self._rounded_enabled
    
    @rounded_enabled.setter
    def rounded_enabled(self, enabled):
        """Enable or disable rounded corners."""
        self._rounded_enabled = enabled
        # Invalidate cached path when mode changes
        if hasattr(self, '_cached_path_key'):
            self._cached_path_key = None
        self.update()
    
    def set_corner_radius(self, corner_index, radius):
        """Set radius for a specific corner (0=TL, 1=TR, 2=BR, 3=BL)."""
        if 0 <= corner_index < 4:
            # Clamp radius to half the smallest dimension
            rect = self.rect_item.rect()
            max_radius = min(rect.width(), rect.height()) / 2.0
            self._corner_radii[corner_index] = max(0, min(radius, max_radius))
            self.update()
    
    def set_all_corner_radii(self, radius):
        """Set the same radius for all corners."""
        rect = self.rect_item.rect()
        max_radius = min(rect.width(), rect.height()) / 2.0
        clamped = max(0, min(radius, max_radius))
        self._corner_radii = [clamped, clamped, clamped, clamped]
        self.update()
    
    def has_rounded_corners(self):
        """Check if any corner has a non-zero radius."""
        return self._rounded_enabled and any(r > 0 for r in self._corner_radii)

    def set_geometry(self, rect: QRectF):
        """
        Sets the geometry of the underlying QGraphicsRectItem.
        Invalidates rounded path cache when geometry changes.
        """
        try:
            self.prepareGeometryChange()
            self.rect_item.setRect(rect)
            # Adjust corner radii if they exceed the new dimensions
            max_radius = min(rect.width(), rect.height()) / 2.0
            self._corner_radii = [min(r, max_radius) for r in self._corner_radii]
            # Invalidate cached path since geometry changed
            if hasattr(self, '_cached_path_key'):
                self._cached_path_key = None
        except Exception as e:
            logger.error(f"CRITICAL: Error in RectangleObject.set_geometry: {e}", exc_info=True)

    def _create_rounded_path(self):
        """Create a QPainterPath with individual corner radii. Cached to avoid recalculation."""
        # Cache key: combination of rect and radii
        if not hasattr(self, '_cached_rounded_path'):
            self._cached_rounded_path = None
            self._cached_path_key = None
        
        rect = self.rect_item.rect()
        radii_tuple = tuple(self._corner_radii)
        path_key = (round(rect.width(), 2), round(rect.height(), 2), radii_tuple)
        
        # Return cached path if geometry hasn't changed
        if self._cached_path_key == path_key and self._cached_rounded_path is not None:
            return self._cached_rounded_path
        
        path = QPainterPath()
        
        tl, tr, br, bl = self._corner_radii
        
        # Start from top-left, after the corner arc
        path.moveTo(rect.left() + tl, rect.top())
        
        # Top edge to top-right corner
        path.lineTo(rect.right() - tr, rect.top())
        
        # Top-right corner arc
        if tr > 0:
            path.arcTo(rect.right() - 2*tr, rect.top(), 2*tr, 2*tr, 90, -90)
        else:
            path.lineTo(rect.right(), rect.top())
        
        # Right edge to bottom-right corner
        path.lineTo(rect.right(), rect.bottom() - br)
        
        # Bottom-right corner arc
        if br > 0:
            path.arcTo(rect.right() - 2*br, rect.bottom() - 2*br, 2*br, 2*br, 0, -90)
        else:
            path.lineTo(rect.right(), rect.bottom())
        
        # Bottom edge to bottom-left corner
        path.lineTo(rect.left() + bl, rect.bottom())
        
        # Bottom-left corner arc
        if bl > 0:
            path.arcTo(rect.left(), rect.bottom() - 2*bl, 2*bl, 2*bl, -90, -90)
        else:
            path.lineTo(rect.left(), rect.bottom())
        
        # Left edge to top-left corner
        path.lineTo(rect.left(), rect.top() + tl)
        
        # Top-left corner arc
        if tl > 0:
            path.arcTo(rect.left(), rect.top(), 2*tl, 2*tl, 180, -90)
        else:
            path.lineTo(rect.left(), rect.top())
        
        path.closeSubpath()
        
        # Cache the path
        self._cached_rounded_path = path
        self._cached_path_key = path_key
        
        return path

    def paint(self, painter, option, widget):
        # Always draw the shape ourselves to have full control
        # Get the current pen and brush from the composed item
        pen = self.item.pen()
        brush = self.item.brush()
        
        # If rounded corners are enabled and have non-zero radii, draw custom path
        if self.has_rounded_corners():
            painter.save()
            painter.setPen(pen)
            painter.setBrush(brush)
            path = self._create_rounded_path()
            painter.drawPath(path)
            painter.restore()
        else:
            # For normal rectangles, draw a regular rect
            painter.save()
            painter.setPen(pen)
            painter.setBrush(brush)
            rect = self.rect_item.rect()
            painter.drawRect(rect)
            painter.restore()


class EllipseObject(BaseGraphicObject):
    """
    A concrete implementation for an ellipse object.
    """
    def __init__(self, rect: QRectF, view_service=None, view=None, parent=None):
        # We create a QGraphicsEllipseItem and compose it.
        super().__init__(QGraphicsEllipseItem(rect), view_service, view, parent)

    @property
    def ellipse_item(self) -> QGraphicsEllipseItem:
        return self.item

    def set_geometry(self, rect: QRectF):
        """
        Sets the geometry of the underlying QGraphicsEllipseItem.
        """
        try:
            self.prepareGeometryChange()
            self.ellipse_item.setRect(rect)
        except Exception as e:
            logger.error(f"CRITICAL: Error in EllipseObject.set_geometry: {e}", exc_info=True)

    
    def paint(self, painter, option, widget):
        # We need to explicitly call the composed item's paint method
        # if we want it to be rendered.
        self.item.paint(painter, option, widget)