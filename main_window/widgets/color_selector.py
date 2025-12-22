# main_window\widgets\color_selector.py
import sys
from PySide6.QtWidgets import (
    QApplication, QDialog, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QDialogButtonBox, QLineEdit, QSlider, QFrame, QComboBox, QTabWidget,
    QGroupBox
)
from PySide6.QtGui import QColor, QPainter, QLinearGradient, QPen, QBrush, QFont, QFontMetrics
from PySide6.QtCore import Qt, Signal, QPointF, QRectF
from styles import colors
import math
import random

def calculate_harmonies(base_color):
    """Calculates various color harmonies based on a base color."""
    h, s, v, base_alpha = base_color.getHsvF()
    h = h * 360

    def create_color(new_hue, new_s, new_v):
        # Clamp values to the valid [0.0, 1.0] range to prevent floating point errors
        safe_hue = max(0.0, min(1.0, new_hue))
        safe_s = max(0.0, min(1.0, new_s))
        safe_v = max(0.0, min(1.0, new_v))
        
        color = QColor.fromHsvF(safe_hue, safe_s, safe_v)
        color.setAlphaF(base_alpha)
        return color

    harmonies = {
        "Complementary": [create_color(((h + 180) % 360) / 360.0, s, v)],
        "Analogous": [
            create_color(((h - 30 + 360) % 360) / 360.0, s, v),
            base_color,
            create_color(((h + 30) % 360) / 360.0, s, v)
        ],
        "Triadic": [
            create_color(((h + 120) % 360) / 360.0, s, v),
            create_color(((h + 240) % 360) / 360.0, s, v)
        ],
        "Split Complementary": [
            create_color(((h + 150) % 360) / 360.0, s, v),
            create_color(((h + 210) % 360) / 360.0, s, v)
        ],
        "Double Split Complementary": [
             create_color(((h + 30) % 360) / 360.0, s, v),
             create_color(((h + 180) % 360) / 360.0, s, v),
             create_color(((h + 210) % 360) / 360.0, s, v),
        ]
    }
    # Add the base color to each harmony list
    for key in harmonies:
        if base_color not in harmonies[key]:
            harmonies[key].insert(0, base_color)
            
    return harmonies


class ColorSquare(QWidget):
    """A widget to select saturation and value from a square."""
    color_changed = Signal(QColor)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(200, 200)
        self._hue = 0.0
        self._saturation = 1.0
        self._value = 1.0
        self._alpha = 1.0
        self._indicator_pos = QPointF(200, 0)

    def set_hue(self, hue):
        self._hue = hue
        self.update()
        self._update_from_indicator()
        
    def set_alpha(self, alpha):
        self._alpha = alpha
        self._update_from_indicator()

    def set_hsv(self, h, s, v, a):
        self._hue = h
        self._saturation = s
        self._value = v
        self._alpha = a
        self._indicator_pos = QPointF(s * self.width(), (1 - v) * self.height())
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        gradient_h = QLinearGradient(0, 0, self.width(), 0)
        gradient_h.setColorAt(0, QColor.fromHsvF(self._hue, 0, 1))
        gradient_h.setColorAt(1, QColor.fromHsvF(self._hue, 1, 1))
        painter.fillRect(self.rect(), gradient_h)

        gradient_v = QLinearGradient(0, 0, 0, self.height())
        gradient_v.setColorAt(0, QColor(0, 0, 0, 0))
        gradient_v.setColorAt(1, QColor(0, 0, 0, 255))
        painter.fillRect(self.rect(), gradient_v)

        painter.setPen(QPen(Qt.GlobalColor.white, 1.5))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(self._indicator_pos, 5, 5)
        painter.setPen(QPen(Qt.GlobalColor.black, 1.5))
        painter.drawEllipse(self._indicator_pos, 6, 6)

    def mousePressEvent(self, event):
        self._update_indicator_pos(event.position())

    def mouseMoveEvent(self, event):
        self._update_indicator_pos(event.position())

    def _update_indicator_pos(self, pos):
        x = max(0, min(pos.x(), self.width()))
        y = max(0, min(pos.y(), self.height()))
        self._indicator_pos = QPointF(x, y)
        self.update()
        self._update_from_indicator()

    def _update_from_indicator(self):
        self._saturation = self._indicator_pos.x() / self.width()
        self._value = 1 - (self._indicator_pos.y() / self.height())
        color = QColor.fromHsvF(self._hue, self._saturation, self._value)
        color.setAlphaF(self._alpha)
        self.color_changed.emit(color)

class HueSlider(QWidget):
    """A slider for selecting the hue."""
    hue_changed = Signal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(20)
        self.setMaximumHeight(20)
        self._hue = 0.0
        self._indicator_x = 0

    def set_hue(self, hue):
        self._hue = hue
        self._indicator_x = hue * self.width()
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        gradient = QLinearGradient(0, 0, self.width(), 0)
        for i in range(361):
            gradient.setColorAt(i/360.0, QColor.fromHsvF(i/360.0, 1, 1))
        painter.fillRect(self.rect(), gradient)

        painter.setPen(QPen(Qt.GlobalColor.black, 2))
        painter.setBrush(Qt.GlobalColor.white)
        indicator_rect = QRectF(self._indicator_x - 3, 0, 6, self.height())
        painter.drawRect(indicator_rect)

    def mousePressEvent(self, event):
        self._update_hue(event.position().x())

    def mouseMoveEvent(self, event):
        self._update_hue(event.position().x())

    def _update_hue(self, x):
        self._indicator_x = max(0, min(x, self.width()))
        self._hue = self._indicator_x / self.width()
        self.update()
        self.hue_changed.emit(self._hue)

class AlphaSlider(QWidget):
    """A slider for selecting the alpha/transparency."""
    alpha_changed = Signal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(20)
        self.setMaximumHeight(20)
        self._alpha = 1.0
        self._color = QColor("black")
        self._indicator_x = self.width()

    def set_color(self, color):
        self._color = QColor(color)
        self.update()

    def set_alpha(self, alpha):
        self._alpha = alpha
        self._indicator_x = alpha * self.width()
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        tile_size = 8
        for i in range(math.ceil(self.width() / tile_size)):
            for j in range(math.ceil(self.height() / tile_size)):
                if (i + j) % 2 == 0:
                    painter.fillRect(i * tile_size, j * tile_size, tile_size, tile_size, Qt.GlobalColor.lightGray)
                else:
                    painter.fillRect(i * tile_size, j * tile_size, tile_size, tile_size, Qt.GlobalColor.white)
        
        gradient = QLinearGradient(0, 0, self.width(), 0)
        start_color = QColor(self._color)
        start_color.setAlpha(0)
        end_color = QColor(self._color)
        end_color.setAlpha(255)
        gradient.setColorAt(0, start_color)
        gradient.setColorAt(1, end_color)
        painter.fillRect(self.rect(), gradient)

        painter.setPen(QPen(Qt.GlobalColor.black, 2))
        painter.setBrush(Qt.GlobalColor.white)
        indicator_rect = QRectF(self._indicator_x - 3, 0, 6, self.height())
        painter.drawRect(indicator_rect)

    def mousePressEvent(self, event):
        self._update_alpha(event.position().x())

    def mouseMoveEvent(self, event):
        self._update_alpha(event.position().x())

    def _update_alpha(self, x):
        self._indicator_x = max(0, min(x, self.width()))
        self._alpha = self._indicator_x / self.width()
        self.update()
        self.alpha_changed.emit(self._alpha)

class PaletteWidget(QWidget):
    """Widget to display a color palette."""
    color_clicked = Signal(QColor)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

    def update_palette(self, colors):
        while self.layout.count():
            child = self.layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        for color in colors:
            btn = QPushButton(color.name(QColor.NameFormat.HexArgb).upper())
            btn.setMinimumHeight(50)
            btn.setStyleSheet(f"background-color: {color.name()}; color: {self._get_text_color(color).name()}; border: none;")
            btn.clicked.connect(lambda _, c=color: self.color_clicked.emit(c))
            self.layout.addWidget(btn)
        self.layout.addStretch()

    def _get_text_color(self, bg_color):
        return QColor("white") if bg_color.lightnessF() < 0.5 else QColor("black")

class ColorButton(QPushButton):
    """A button that displays a color and emits a signal when clicked."""
    color_clicked = Signal(QColor)

    def __init__(self, color, parent=None):
        super().__init__(parent)
        if isinstance(color, str):
            self._color = QColor(color)
        else:
            self._color = color
        
        self.setFixedSize(24, 24)
        self._is_selected = False
        self._update_style()
        self.clicked.connect(self._emit_color)

    def color(self):
        """Returns the QColor of the button."""
        return self._color

    def setColor(self, color):
        """Sets a new color for the button and updates its appearance."""
        if isinstance(color, str):
            self._color = QColor(color)
        else:
            self._color = color
        self._update_style()
    
    def set_selected(self, selected):
        """Sets the visual selection state of the button."""
        if self._is_selected != selected:
            self._is_selected = selected
            self._update_style()

    def _update_style(self):
        """Updates the stylesheet based on the color and selection state."""
        from styles import colors
        if self._is_selected:
            # A prominent blue border for selection
            style = f"background-color: {self._color.name()}; border: 2px solid {colors.COLOR_FOCUS_HIGHLIGHT}; border-radius: 2px;"
        else:
            style = f"background-color: {self._color.name()}; border: 1px solid lightgrey;"
        self.setStyleSheet(style)

    def _emit_color(self):
        self.color_clicked.emit(self._color)

class ColorSelector(QDialog):
    """A modern dialog for selecting a color, inspired by the screenshot."""
    color_selected = Signal(QColor)

    def __init__(self, initial_color=QColor("white"), parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Color")
        self.setFixedSize(600, 480)
        
        self.swatch_buttons = [] # To keep track of swatch buttons
        self._color = initial_color

        main_layout = QVBoxLayout(self)
        
        # --- Tab Widget for different selection modes ---
        tab_widget = QTabWidget()
        custom_color_tab = self._create_custom_color_tab()
        swatches_tab = self._create_swatches_tab()
        
        tab_widget.addTab(custom_color_tab, "Custom Color")
        tab_widget.addTab(swatches_tab, "Swatches")

        # --- Dialog Buttons ---
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        no_fill_button = buttons.addButton("No Fill", QDialogButtonBox.ButtonRole.ActionRole)
        no_fill_button.clicked.connect(self._select_no_fill)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        main_layout.addWidget(tab_widget)
        main_layout.addWidget(buttons)

        self.update_ui_from_color(self._color)

        # --- Signal Connections ---
        self.color_square.color_changed.connect(self.update_ui_from_color)
        self.hue_slider.hue_changed.connect(self.update_from_hue_slider)
        self.alpha_slider.alpha_changed.connect(self.update_from_alpha_slider)
        self.hex_input_line.textChanged.connect(self.update_from_hex)
        self.hex_display.textChanged.connect(self.update_from_hex)
        self.harmony_combo.currentTextChanged.connect(lambda: self.update_ui_from_color(self._color))
        self.palette_widget.color_clicked.connect(self.update_ui_from_color)

    def _create_custom_color_tab(self):
        """Creates the widget for the 'Custom Color' tab."""
        custom_tab_widget = QWidget()
        main_layout = QVBoxLayout(custom_tab_widget)

        top_bar = QHBoxLayout()
        self.hex_display = QLineEdit()
        self.rgba_display = QLabel()
        h,s,l,a = self._color.getHslF()
        self.hsl_display = QLabel(f"HSL {int(h*360)}, {int(s*100)}, {int(l*100)}")
        top_bar.addWidget(QLabel("Hex"))
        top_bar.addWidget(self.hex_display)
        top_bar.addWidget(self.rgba_display)
        top_bar.addWidget(self.hsl_display)
        top_bar.addStretch()

        content_layout = QHBoxLayout()
        
        picker_layout = QVBoxLayout()
        self.color_square = ColorSquare()
        self.hue_slider = HueSlider()
        self.alpha_slider = AlphaSlider()
        
        color_input_layout = QHBoxLayout()
        self.preview = QWidget()
        self.preview.setFixedSize(40, 40)
        self.preview.setAutoFillBackground(True)
        self.hex_input_line = QLineEdit()
        color_input_layout.addWidget(self.preview)
        color_input_layout.addWidget(self.hex_input_line)

        picker_layout.addWidget(self.color_square)
        picker_layout.addWidget(self.hue_slider)
        picker_layout.addWidget(self.alpha_slider)
        picker_layout.addLayout(color_input_layout)

        palette_container = QWidget()
        palette_main_layout = QVBoxLayout(palette_container)
        
        palette_header = QHBoxLayout()
        self.harmony_combo = QComboBox()
        self.harmony_combo.addItems(calculate_harmonies(QColor("red")).keys())
        palette_header.addWidget(self.harmony_combo)
        palette_header.addStretch()

        self.palette_widget = PaletteWidget()

        palette_main_layout.addLayout(palette_header)
        palette_main_layout.addWidget(self.palette_widget)

        content_layout.addLayout(picker_layout, 2)
        content_layout.addWidget(palette_container, 1)

        main_layout.addLayout(top_bar)
        main_layout.addLayout(content_layout)
        
        return custom_tab_widget

    def _create_swatches_tab(self):
        """Creates the widget for the 'Swatches' tab."""
        swatch_widget = QWidget()
        layout = QVBoxLayout(swatch_widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        layout.addWidget(QLabel("Theme Colors"))
        layout.addLayout(self._create_theme_colors_grid())

        layout.addWidget(QLabel("Standard Colors"))
        layout.addLayout(self._create_standard_colors_row())
        
        layout.addStretch()
        return swatch_widget

    def _create_color_button(self, color):
        """Factory method for creating and connecting a ColorButton for swatches."""
        button = ColorButton(color)
        button.color_clicked.connect(self.update_ui_from_color)
        self.swatch_buttons.append(button)
        return button

    def _generate_shades(self, base_hex):
        """Generates a list of 5 shades for a given base color."""
        shades = []
        base_color = QColor(base_hex)
        
        for i in range(1, 6):
            if base_hex == "#FFFFFF":
                lightness = 255 - (i * 25)
                shades.append(QColor(lightness, lightness, lightness))
            elif base_hex == "#000000":
                lightness = i * 25
                shades.append(QColor(lightness, lightness, lightness))
            else:
                h, s, l, a = base_color.getHslF()
                lightness_factor = 1 - (i * 0.15)
                new_l = max(0, l * lightness_factor)
                shades.append(QColor.fromHslF(h, s, new_l, a))
        return shades

    def _create_theme_colors_grid(self):
        """Creates the grid layout for theme colors and their shades."""
        grid = QGridLayout()
        grid.setSpacing(2)
        
        base_colors = [
            "#FFFFFF", "#000000", "#E7E6E6", "#44546A",
            "#5B9BD5", "#ED7D31", "#A5A5A5", "#FFC000",
            "#4472C4", "#70AD47"
        ]

        for col, base_hex in enumerate(base_colors):
            grid.addWidget(self._create_color_button(base_hex), 0, col)
            for row, shade_color in enumerate(self._generate_shades(base_hex), 1):
                grid.addWidget(self._create_color_button(shade_color), row, col)
        return grid

    def _create_standard_colors_row(self):
        """Creates the horizontal layout for standard colors."""
        layout = QHBoxLayout()
        layout.setSpacing(2)
        
        colors = [
            "#C00000", "#FF0000", "#FFC000", "#FFFF00",
            "#92D050", "#00B050", "#00B0F0", "#0070C0",
            "#002060", "#7030A0"
        ]

        for color_hex in colors:
            layout.addWidget(self._create_color_button(color_hex))
        layout.addStretch()
        return layout

    def currentColor(self):
        return self._color

    def block_all_signals(self, block):
        for widget in [self.color_square, self.hue_slider, self.alpha_slider, self.hex_input_line, self.hex_display, self.harmony_combo, self.palette_widget]:
            widget.blockSignals(block)

    def update_ui_from_color(self, color):
        self.block_all_signals(True)
        self._color = color
        
        # Update selection state for swatch buttons
        for button in self.swatch_buttons:
            button.set_selected(button.color() == self._color)
        
        palette = self.preview.palette()
        palette.setColor(self.preview.backgroundRole(), color)
        self.preview.setPalette(palette)
        
        h, s, v, a = color.getHsvF()
        self.color_square.set_hsv(h, s, v, a)
        self.hue_slider.set_hue(h)
        self.alpha_slider.set_color(color)
        self.alpha_slider.set_alpha(a)
        
        hex_name = color.name(QColor.NameFormat.HexArgb).upper()
        self.hex_input_line.setText(hex_name)
        self.hex_display.setText(hex_name)
        self.rgba_display.setText(f"RGBA {color.red()}, {color.green()}, {color.blue()}, {color.alpha()}")
        h,s,l,a = color.getHslF()
        self.hsl_display.setText(f"HSL {int(h*360)}, {int(s*100)}, {int(l*100)}")

        harmonies = calculate_harmonies(color)
        selected_harmony = self.harmony_combo.currentText()
        self.palette_widget.update_palette(harmonies[selected_harmony])

        self.block_all_signals(False)
        
    def update_from_hue_slider(self, hue):
        self.color_square.set_hue(hue)

    def update_from_alpha_slider(self, alpha):
        self.color_square.set_alpha(alpha)

    def update_from_hex(self, text):
        if QColor.isValidColor(text) and (len(text) == 7 or len(text) == 9):
            new_color = QColor(text)
            if self._color != new_color:
                self.update_ui_from_color(new_color)

    def _select_no_fill(self):
        self._color = QColor("transparent")
        self.accept()
        
    def accept(self):
        self.color_selected.emit(self._color)
        super().accept()
        
    @staticmethod
    def getColor(initial=QColor("white"), parent=None):
        # Traverse up the widget hierarchy to find the top-level window (the true parent)
        # This prevents the dialog from inheriting stylesheets from intermediate widgets like QPushButtons.
        true_parent = parent
        if true_parent:
            while true_parent.parent():
                true_parent = true_parent.parent()

        dialog = ColorSelector(initial, true_parent)
        if dialog.exec():
            return dialog.currentColor()
        return QColor()  # Return invalid color if canceled, matching QColorDialog behavior

