# main_window\widgets\pattern_widget.py
import sys
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QGroupBox, QPushButton, QLabel, QFrame
)
from PySide6.QtGui import QColor, QPainter, QBrush, QPen
from PySide6.QtCore import Signal, Qt
from styles import colors

from .color_selector import ColorSelector

class ColorPickerButton(QPushButton):
    """A button that displays a color and opens a color picker when clicked."""
    color_changed = Signal(QColor)

    def __init__(self, color='white', parent=None):
        super().__init__(parent)
        self._color = QColor(color)
        self.setFixedSize(120, 24)
        self._update_style()
        self.clicked.connect(self._open_color_picker)

    def color(self):
        """Returns the current QColor of the button."""
        return self._color

    def set_color(self, color):
        """Sets the button's color and emits a signal if it changes."""
        if self._color != color:
            self._color = color
            self._update_style()
            self.color_changed.emit(self._color)

    def _update_style(self):
        border_color = colors.BORDER_MEDIUM
        self.setStyleSheet(f"background-color: {self._color.name()}; border: 1px solid {border_color};")

    def _open_color_picker(self):
        """Opens the color selector dialog to choose a new color."""
        new_color = ColorSelector.getColor(self._color, self)
        if new_color.isValid():
            self.set_color(new_color)


class PatternPreviewWidget(QWidget):
    """A widget to display a single fill pattern."""
    clicked = Signal()

    def __init__(self, pattern, fg_color, bg_color, parent=None):
        super().__init__(parent)
        self.setFixedSize(40, 40)
        self.pattern = pattern
        self.fg_color = fg_color
        self.bg_color = bg_color
        self.is_selected = False

    def set_selected(self, selected):
        self.is_selected = selected
        self.update()

    def set_colors(self, fg_color, bg_color):
        self.fg_color = fg_color
        self.bg_color = bg_color
        self.update()
        
    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        brush = QBrush(self.fg_color, self.pattern)
        painter.fillRect(self.rect(), self.bg_color)
        painter.fillRect(self.rect(), brush)

        if self.is_selected:
            pen = QPen(QColor(colors.COLOR_FOCUS_HIGHLIGHT), 2)
            painter.setPen(pen)
        else:
            painter.setPen(QColor("grey"))
            
        painter.drawRect(self.rect().adjusted(1, 1, -1, -1))

class PatternWidget(QWidget):
    """A widget for selecting colors and a fill pattern."""
    def __init__(self, initial_pattern=None, parent=None):
        super().__init__(parent)
        main_layout = QVBoxLayout(self)
        self.selected_pattern_preview = None
        
        # Color selection
        color_group = QGroupBox("Color")
        color_layout = QGridLayout()
        color_group.setLayout(color_layout)
        self.fg_color_button = ColorPickerButton(QColor("black"))
        self.bg_color_button = ColorPickerButton(QColor("white"))
        color_layout.addWidget(QLabel("Foreground Color"), 0, 0)
        color_layout.addWidget(self.fg_color_button, 0, 1)
        color_layout.addWidget(QLabel("Background Color"), 1, 0)
        color_layout.addWidget(self.bg_color_button, 1, 1)
        main_layout.addWidget(color_group)

        # Pattern selection
        pattern_group = QGroupBox("Pattern")
        self.pattern_grid = QGridLayout()
        pattern_group.setLayout(self.pattern_grid)
        self.pattern_grid.setSpacing(5)

        if initial_pattern:
            self.fg_color_button.set_color(initial_pattern["fg_color"])
            self.bg_color_button.set_color(initial_pattern["bg_color"])

        patterns = [
            Qt.BrushStyle.SolidPattern, Qt.BrushStyle.Dense1Pattern, Qt.BrushStyle.Dense2Pattern,
            Qt.BrushStyle.Dense3Pattern, Qt.BrushStyle.Dense4Pattern, Qt.BrushStyle.Dense5Pattern,
            Qt.BrushStyle.Dense6Pattern, Qt.BrushStyle.Dense7Pattern, Qt.BrushStyle.HorPattern,
            Qt.BrushStyle.VerPattern, Qt.BrushStyle.CrossPattern, Qt.BrushStyle.BDiagPattern,
            Qt.BrushStyle.FDiagPattern, Qt.BrushStyle.DiagCrossPattern
        ]
        
        self.pattern_previews = []
        for i, pattern in enumerate(patterns):
            row, col = divmod(i, 6)
            preview = PatternPreviewWidget(pattern, self.fg_color_button.color(), self.bg_color_button.color())
            preview.clicked.connect(self.select_pattern_slot)
            self.pattern_grid.addWidget(preview, row, col)
            self.pattern_previews.append(preview)

        if initial_pattern:
            initial_pattern_style = initial_pattern["pattern"]
            for preview in self.pattern_previews:
                if preview.pattern == initial_pattern_style:
                    self.select_pattern(preview)
                    break
        else:
            if self.pattern_previews:
                self.select_pattern(self.pattern_previews[0])

        main_layout.addWidget(pattern_group)

        # Connections
        self.fg_color_button.color_changed.connect(self.update_pattern_colors)
        self.bg_color_button.color_changed.connect(self.update_pattern_colors)

    def select_pattern_slot(self):
        clicked_preview = self.sender()
        self.select_pattern(clicked_preview)

    def select_pattern(self, preview_to_select):
        if self.selected_pattern_preview:
            self.selected_pattern_preview.set_selected(False)
        self.selected_pattern_preview = preview_to_select
        if self.selected_pattern_preview:
            self.selected_pattern_preview.set_selected(True)

    def update_pattern_colors(self):
        fg_color = self.fg_color_button.color()
        bg_color = self.bg_color_button.color()
        for preview in self.pattern_previews:
            preview.set_colors(fg_color, bg_color)
