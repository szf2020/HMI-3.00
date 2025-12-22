# main_window\widgets\gradient_widget.py
import sys
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QGroupBox, QRadioButton, QPushButton, QLabel, QButtonGroup
)
from PySide6.QtGui import QColor, QPainter, QLinearGradient, QBrush, QPen
from PySide6.QtCore import Signal, QPointF, Qt
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

class GradientPreviewWidget(QWidget):
    """A widget to display a single gradient preview."""
    clicked = Signal()

    def __init__(self, color1, color2, stops, parent=None):
        super().__init__(parent)
        self.setFixedSize(100, 100)
        self.color1 = color1
        self.color2 = color2
        self.stops = stops
        self.is_selected = False

    def set_selected(self, selected):
        self.is_selected = selected
        self.update()

    def set_gradient(self, color1, color2, stops):
        self.color1 = color1
        self.color2 = color2
        self.stops = stops
        self.update()

    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect()
        
        gradient = QLinearGradient()
        if self.stops == "Horizontal":
            gradient.setStart(QPointF(rect.left(), rect.center().y()))
            gradient.setFinalStop(QPointF(rect.right(), rect.center().y()))
        elif self.stops == "Vertical":
            gradient.setStart(QPointF(rect.center().x(), rect.top()))
            gradient.setFinalStop(QPointF(rect.center().x(), rect.bottom()))
        elif self.stops == "Up Diagonal":
            gradient.setStart(QPointF(rect.bottomLeft()))
            gradient.setFinalStop(QPointF(rect.topRight()))
        elif self.stops == "Down Diagonal":
            gradient.setStart(QPointF(rect.topLeft()))
            gradient.setFinalStop(QPointF(rect.bottomRight()))

        gradient.setColorAt(0, self.color1)
        gradient.setColorAt(1, self.color2)
        
        painter.fillRect(rect, QBrush(gradient))
        
        if self.is_selected:
            pen = QPen(QColor(colors.COLOR_FOCUS_HIGHLIGHT), 2)
            painter.setPen(pen)
        else:
            painter.setPen(QColor(colors.BORDER_MEDIUM))
            
        painter.drawRect(rect.adjusted(1, 1, -1, -1))

class GradientWidget(QWidget):
    """A widget for selecting and previewing gradient colors."""
    def __init__(self, initial_gradient=None, parent=None):
        super().__init__(parent)
        main_layout = QVBoxLayout(self)
        self.selected_preview = None

        # Color Selection
        color_group = QGroupBox("Color")
        color_layout = QGridLayout()
        color_group.setLayout(color_layout)
        self.color1_button = ColorPickerButton(QColor("#D0CECE"))
        self.color2_button = ColorPickerButton(QColor("#596978"))
        color_layout.addWidget(QLabel("Color1"), 0, 0)
        color_layout.addWidget(self.color1_button, 0, 1)
        color_layout.addWidget(QLabel("Color2"), 1, 0)
        color_layout.addWidget(self.color2_button, 1, 1)
        main_layout.addWidget(color_group)

        # Gradation Type and Variation
        bottom_layout = QHBoxLayout()
        gradation_group = QGroupBox("Gradation Type")
        gradation_layout = QVBoxLayout(gradation_group)
        self.radio_horizontal = QRadioButton("Horizontal")
        self.radio_vertical = QRadioButton("Vertical")
        self.radio_up_diagonal = QRadioButton("Up Diagonal")
        self.radio_down_diagonal = QRadioButton("Down Diagonal")
        
        self.gradation_type_group = QButtonGroup(self)
        self.gradation_type_group.addButton(self.radio_horizontal)
        self.gradation_type_group.addButton(self.radio_vertical)
        self.gradation_type_group.addButton(self.radio_up_diagonal)
        self.gradation_type_group.addButton(self.radio_down_diagonal)

        gradation_layout.addWidget(self.radio_horizontal)
        gradation_layout.addWidget(self.radio_vertical)
        gradation_layout.addWidget(self.radio_up_diagonal)
        gradation_layout.addWidget(self.radio_down_diagonal)
        bottom_layout.addWidget(gradation_group)
        
        variation_group = QGroupBox("Variation")
        variation_layout = QGridLayout()
        variation_group.setLayout(variation_layout)
        
        c1 = self.color1_button.color()
        c2 = self.color2_button.color()
        self.preview1 = GradientPreviewWidget(c1, c2, "Horizontal")
        self.preview2 = GradientPreviewWidget(c1, c2, "Vertical")
        self.preview3 = GradientPreviewWidget(c1, c2, "Up Diagonal")
        self.preview4 = GradientPreviewWidget(c1, c2, "Down Diagonal")
        
        self.previews = [self.preview1, self.preview2, self.preview3, self.preview4]

        variation_layout.addWidget(self.preview1, 0, 0)
        variation_layout.addWidget(self.preview2, 0, 1)
        variation_layout.addWidget(self.preview3, 1, 0)
        variation_layout.addWidget(self.preview4, 1, 1)
        bottom_layout.addWidget(variation_group)
        
        main_layout.addLayout(bottom_layout)

        # Set initial state if provided
        if initial_gradient:
            self.color1_button.set_color(initial_gradient["color1"])
            self.color2_button.set_color(initial_gradient["color2"])

            stops = initial_gradient.get("stops", "Horizontal")
            if stops == "Horizontal":
                self.radio_horizontal.setChecked(True)
            elif stops == "Vertical":
                self.radio_vertical.setChecked(True)
            elif stops == "Up Diagonal":
                self.radio_up_diagonal.setChecked(True)
            elif stops == "Down Diagonal":
                self.radio_down_diagonal.setChecked(True)
        else:
            self.radio_horizontal.setChecked(True)

        # Connections
        self.color1_button.color_changed.connect(self.update_previews)
        self.color2_button.color_changed.connect(self.update_previews)
        self.radio_horizontal.toggled.connect(self.on_gradation_type_changed)
        self.radio_vertical.toggled.connect(self.on_gradation_type_changed)
        self.radio_up_diagonal.toggled.connect(self.on_gradation_type_changed)
        self.radio_down_diagonal.toggled.connect(self.on_gradation_type_changed)

        for preview in self.previews:
            preview.clicked.connect(self.select_preview_slot)
            
        self.select_preview(self.preview1)
        self.update_previews()

    def select_preview_slot(self):
        """Slot to handle a preview click."""
        clicked_preview = self.sender()
        self.select_preview(clicked_preview)

    def select_preview(self, preview_to_select):
        """Handles the selection of a gradient preview widget."""
        if self.selected_preview:
            self.selected_preview.set_selected(False)
        
        self.selected_preview = preview_to_select
        if self.selected_preview:
            self.selected_preview.set_selected(True)

    def on_gradation_type_changed(self, checked):
        if checked:
            self.update_previews()

    def update_previews(self):
        """Updates all gradient previews based on current selections."""
        c1 = self.color1_button.color()
        c2 = self.color2_button.color()

        if self.radio_horizontal.isChecked():
            self.preview1.set_gradient(c1, c2, "Horizontal")
            self.preview2.set_gradient(c2, c1, "Horizontal")
            self.preview3.set_gradient(c1, c2, "Down Diagonal")
            self.preview4.set_gradient(c2, c1, "Down Diagonal")
        elif self.radio_vertical.isChecked():
            self.preview1.set_gradient(c1, c2, "Vertical")
            self.preview2.set_gradient(c2, c1, "Vertical")
            self.preview3.set_gradient(c1, c2, "Up Diagonal")
            self.preview4.set_gradient(c2, c1, "Up Diagonal")
        elif self.radio_up_diagonal.isChecked():
            self.preview1.set_gradient(c1, c2, "Up Diagonal")
            self.preview2.set_gradient(c2, c1, "Up Diagonal")
            self.preview3.set_gradient(c1, c2, "Vertical")
            self.preview4.set_gradient(c2, c1, "Vertical")
        elif self.radio_down_diagonal.isChecked():
            self.preview1.set_gradient(c1, c2, "Down Diagonal")
            self.preview2.set_gradient(c2, c1, "Down Diagonal")
            self.preview3.set_gradient(c1, c2, "Horizontal")
            self.preview4.set_gradient(c2, c1, "Horizontal")
