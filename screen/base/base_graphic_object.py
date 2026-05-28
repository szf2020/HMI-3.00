# screen\base\base_graphic_object.py
from PySide6.QtWidgets import QGraphicsRectItem, QGraphicsEllipseItem, QGraphicsItem, QGraphicsPathItem
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QPainterPath, QPen, QBrush
from debug_utils import get_logger
from screen.base.serializable_graphic_mixin import SerializableGraphicMixin

logger = get_logger(__name__)


class HiddenQGraphicsRectItem(QGraphicsRectItem):
    """
    A QGraphicsRectItem that doesn't paint itself.
    Used as a composed item to provide geometry management without visual rendering.
    """
    def paint(self, painter, option, widget=None):
        # Don't paint anything - parent will handle all rendering
        pass


class BaseGraphicObject(QGraphicsItem, SerializableGraphicMixin):
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
        
        # Make this item hit-testable based on its children's shapes
        # This is critical for composed items where the parent is a container
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemContainsChildrenInShape, True)

        self.ensure_object_id()

    def _item_type(self):
        return self.__class__.__name__.replace("Object", "").lower()

    def to_json_dict(self) -> dict:
        raise NotImplementedError("to_json_dict must be implemented by subclasses.")

    def apply_json_dict(self, data: dict) -> None:
        raise NotImplementedError("apply_json_dict must be implemented by subclasses.")

    @classmethod
    def from_json_dict(cls, data, scene_context) -> "BaseGraphicObject":
        raise NotImplementedError("from_json_dict must be implemented by subclasses.")

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

    def get_clamped_corner_radii(self, radii):
        """Clamp corner radii against current rect dimensions."""
        if not isinstance(radii, (list, tuple)) or len(radii) != 4:
            return self._corner_radii.copy()

        rect = self.rect_item.rect()
        max_radius = min(rect.width(), rect.height()) / 2.0
        return [max(0.0, min(float(radius), max_radius)) for radius in radii]
    
    @corner_radii.setter
    def corner_radii(self, radii):
        """Set corner radii [top_left, top_right, bottom_right, bottom_left]."""
        if len(radii) == 4:
            self._corner_radii = self.get_clamped_corner_radii(radii)
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


    def to_json_dict(self) -> dict:
        self.ensure_object_id()
        rect = self.rect_item.rect()
        data = self.data(Qt.ItemDataRole.UserRole) or {}
        pen = self.item.pen()
        brush = self.item.brush()
        styling = {
            "fill_type": "solid",
            "fill_color": brush.color().name(),
            "outline_color": pen.color().name(),
            "outline_width": pen.widthF(),
            "opacity": self.opacity(),
            "alignment": data.get("alignment"),
            "font": data.get("font"),
            "rounded_enabled": self.rounded_enabled,
            "corner_radii": self.corner_radii,
        }
        return self.canonical_document(
            object_id=data.get("object_id"),
            object_type="rectangle",
            geometry={"x": self.x(), "y": self.y(), "width": rect.width(), "height": rect.height(), "rotation": self.rotation()},
            styling=styling,
            data_links=data.get("data_links") or {"tags": [], "comments": []},
            z_index=self.zValue(),
            locked=not bool(self.flags() & QGraphicsItem.GraphicsItemFlag.ItemIsMovable),
            visible=self.isVisible(),
            custom_props=data.get("custom_props") or {},
        )

    def apply_json_dict(self, data: dict) -> None:
        geometry = data.get("geometry", {})
        styling = data.get("styling", {})
        self.set_geometry(QRectF(0, 0, geometry.get("width", 0), geometry.get("height", 0)))
        self.setPos(geometry.get("x", 0), geometry.get("y", 0))
        self.setRotation(geometry.get("rotation", 0))
        pen = self.item.pen()
        brush = self.item.brush()
        if styling.get("outline_color"):
            from PySide6.QtGui import QColor
            pen.setColor(QColor(styling.get("outline_color")))
        if styling.get("outline_width") is not None:
            pen.setWidthF(float(styling.get("outline_width")))
        if styling.get("fill_color"):
            from PySide6.QtGui import QColor
            brush.setColor(QColor(styling.get("fill_color")))
        self.item.setPen(pen)
        self.item.setBrush(brush)
        if styling.get("opacity") is not None:
            self.setOpacity(float(styling.get("opacity")))
        self.rounded_enabled = bool(styling.get("rounded_enabled", False))
        self.corner_radii = styling.get("corner_radii", [0.0, 0.0, 0.0, 0.0])
        payload = self.data(Qt.ItemDataRole.UserRole) or {}
        payload.update(data)
        self.setData(Qt.ItemDataRole.UserRole, payload)
        self.ensure_object_id()

    @classmethod
    def from_json_dict(cls, data, scene_context) -> "RectangleObject":
        geom = data.get("geometry", {})
        item = cls(QRectF(0, 0, geom.get("width", 0), geom.get("height", 0)), scene_context.view_service, scene_context)
        item.apply_json_dict(data)
        return item


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

    
    def to_json_dict(self) -> dict:
        self.ensure_object_id()
        rect = self.ellipse_item.rect()
        data = self.data(Qt.ItemDataRole.UserRole) or {}
        pen = self.item.pen()
        brush = self.item.brush()
        styling = {
            "fill_type": "solid",
            "fill_color": brush.color().name(),
            "outline_color": pen.color().name(),
            "outline_width": pen.widthF(),
            "opacity": self.opacity(),
            "alignment": data.get("alignment"),
            "font": data.get("font"),
        }
        return self.canonical_document(
            object_id=data.get("object_id"),
            object_type="ellipse",
            geometry={"x": self.x(), "y": self.y(), "width": rect.width(), "height": rect.height(), "rotation": self.rotation()},
            styling=styling,
            data_links=data.get("data_links") or {"tags": [], "comments": []},
            z_index=self.zValue(),
            locked=not bool(self.flags() & QGraphicsItem.GraphicsItemFlag.ItemIsMovable),
            visible=self.isVisible(),
            custom_props=data.get("custom_props") or {},
        )

    def apply_json_dict(self, data: dict) -> None:
        geometry = data.get("geometry", {})
        styling = data.get("styling", {})
        self.set_geometry(QRectF(0, 0, geometry.get("width", 0), geometry.get("height", 0)))
        self.setPos(geometry.get("x", 0), geometry.get("y", 0))
        self.setRotation(geometry.get("rotation", 0))
        pen = self.item.pen()
        brush = self.item.brush()
        if styling.get("outline_color"):
            from PySide6.QtGui import QColor
            pen.setColor(QColor(styling.get("outline_color")))
        if styling.get("outline_width") is not None:
            pen.setWidthF(float(styling.get("outline_width")))
        if styling.get("fill_color"):
            from PySide6.QtGui import QColor
            brush.setColor(QColor(styling.get("fill_color")))
        self.item.setPen(pen)
        self.item.setBrush(brush)
        if styling.get("opacity") is not None:
            self.setOpacity(float(styling.get("opacity")))
        payload = self.data(Qt.ItemDataRole.UserRole) or {}
        payload.update(data)
        self.setData(Qt.ItemDataRole.UserRole, payload)
        self.ensure_object_id()

    @classmethod
    def from_json_dict(cls, data, scene_context) -> "EllipseObject":
        geom = data.get("geometry", {})
        item = cls(QRectF(0, 0, geom.get("width", 0), geom.get("height", 0)), scene_context.view_service, scene_context)
        item.apply_json_dict(data)
        return item

    def paint(self, painter, option, widget):
        self.item.paint(painter, option, widget)
