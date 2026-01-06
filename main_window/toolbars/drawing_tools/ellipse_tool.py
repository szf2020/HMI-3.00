# main_window\toolbars\drawing_tools\ellipse_tool.py
from PySide6.QtWidgets import QGraphicsEllipseItem
from PySide6.QtGui import QPen, QColor, QBrush
from PySide6.QtCore import Qt, QRectF
from styles import colors

class EllipseTool:
    """
    Tool for drawing ellipses on the canvas.
    """
    def __init__(self, canvas_screen):
        self.canvas = canvas_screen
        self.scene = canvas_screen.scene
        self.current_item = None
        self.start_pos = None

    def mouse_press(self, scene_pos):
        """Starts drawing an ellipse."""
        self.start_pos = scene_pos
        self.current_item = QGraphicsEllipseItem(QRectF(self.start_pos, self.start_pos))
        self.current_item.setData(0, "ellipse")  # Set object type for factory

        # Set default styles
        self.current_item.setPen(QPen(QColor(colors.COLOR_DEFAULT_SHAPE_BORDER), 2))
        self.current_item.setBrush(QBrush(QColor(colors.COLOR_DEFAULT_SHAPE_FILL)))

        # Add flags
        self.current_item.setFlags(
            QGraphicsEllipseItem.GraphicsItemFlag.ItemIsMovable |
            QGraphicsEllipseItem.GraphicsItemFlag.ItemIsSelectable |
            QGraphicsEllipseItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )

        self.scene.addItem(self.current_item)

    def mouse_move(self, scene_pos, modifiers=Qt.KeyboardModifier.NoModifier):
        """Updates the ellipse size while dragging."""
        if self.current_item and self.start_pos:
            width = scene_pos.x() - self.start_pos.x()
            height = scene_pos.y() - self.start_pos.y()

            if modifiers & Qt.KeyboardModifier.ShiftModifier:
                side_length = max(abs(width), abs(height))
                width = side_length if width >= 0 else -side_length
                height = side_length if height >= 0 else -side_length

            new_rect = QRectF(self.start_pos.x(), self.start_pos.y(), width, height).normalized()
            self.current_item.setRect(new_rect)

    def mouse_release(self, scene_pos):
        """Finishes the drawing operation."""
        if self.current_item:
            if self.current_item.rect().width() < 5 or self.current_item.rect().height() < 5:
                self.scene.removeItem(self.current_item)
            else:
                self.current_item.setSelected(True)

            # The item is finalized in canvas_base_screen
            # self.current_item = None
            self.start_pos = None
