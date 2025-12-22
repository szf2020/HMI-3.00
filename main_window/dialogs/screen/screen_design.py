# main_window\dialogs\screen\screen_design.py
import sys
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QDialogButtonBox,
    QRadioButton, QButtonGroup, QStackedWidget, QWidget, QGroupBox,
    QPushButton, QFileDialog, QLineEdit, QFormLayout, QSpinBox
)
from PySide6.QtGui import (
    QColor, QPixmap, QIcon, QPainter, QLinearGradient, QBrush
)
from PySide6.QtCore import Qt, QEvent, QPointF, QSize
from styles import colors

# Import the refactored widgets
from ...widgets.color_selector import ColorSelector
from ...widgets.gradient_widget import GradientWidget
from ...widgets.pattern_widget import PatternWidget

class ScreenDesignDialog(QDialog):
    """
    A dialog window for creating and configuring a screen design template,
    allowing users to choose between solid colors, gradients, patterns, or images for the fill.
    """
    def __init__(self, parent=None, initial_data=None):
        super().__init__(parent)
        self.setWindowTitle("Screen Design Template")
        
        # Initialize properties to hold the selected fill style
        self.selected_color = QColor("#FFFFFF")
        self.selected_gradient = None
        self.selected_pattern = None
        self.selected_image = None

        main_layout = QVBoxLayout(self)

        # --- Screen Size GroupBox ---
        screen_size_group_box = QGroupBox("Screen Size")
        screen_size_layout = QFormLayout(screen_size_group_box)
        self.width_spinbox = QSpinBox()
        self.width_spinbox.setRange(1, 8000)
        self.width_spinbox.setValue(1920)
        self.height_spinbox = QSpinBox()
        self.height_spinbox.setRange(1, 8000)
        self.height_spinbox.setValue(1080)
        screen_size_layout.addRow("Width:", self.width_spinbox)
        screen_size_layout.addRow("Height:", self.height_spinbox)
        
        # --- Radio buttons for fill style ---
        fill_group_box = QGroupBox("Fill Style")
        fill_layout = QHBoxLayout()
        self.fill_color_radio = QRadioButton("Fill Colour")
        self.gradient_color_radio = QRadioButton("Gradient Colour")
        self.fill_pattern_radio = QRadioButton("Fill Pattern")
        self.fill_image_radio = QRadioButton("Fill Image")
        
        fill_layout.addWidget(self.fill_color_radio)
        fill_layout.addWidget(self.gradient_color_radio)
        fill_layout.addWidget(self.fill_pattern_radio)
        fill_layout.addWidget(self.fill_image_radio)
        fill_group_box.setLayout(fill_layout)
        
        self.radio_button_group = QButtonGroup()
        self.radio_button_group.addButton(self.fill_color_radio, 0)
        self.radio_button_group.addButton(self.gradient_color_radio, 1)
        self.radio_button_group.addButton(self.fill_pattern_radio, 2)
        self.radio_button_group.addButton(self.fill_image_radio, 3)
        self.fill_color_radio.setChecked(True)

        # --- Stacked widget for options based on radio selection ---
        self.stack = QStackedWidget()
        self.stack.addWidget(self._create_fill_color_widget())
        self.stack.addWidget(self._create_gradient_color_widget())
        self.stack.addWidget(self._create_pattern_widget())
        self.stack.addWidget(self._create_image_widget())
        
        self.radio_button_group.idClicked.connect(self.stack.setCurrentIndex)

        # --- OK and Cancel buttons ---
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        
        main_layout.addWidget(screen_size_group_box)
        main_layout.addWidget(fill_group_box)
        main_layout.addWidget(self.stack)
        main_layout.addWidget(buttons)

        self.resize(550, 500)

        if initial_data:
            self.load_design_details(initial_data)

    def _create_fill_color_widget(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        self.color_preview_button = QPushButton()
        self.color_preview_button.setFixedHeight(40)
        self.set_color_preview(self.selected_color)
        self.color_preview_button.clicked.connect(self._open_color_selector_dialog)
        layout.addWidget(self.color_preview_button)
        layout.addStretch()
        return widget

    def set_color_preview(self, color):
        self.selected_color = color
        text_color = "black" if color.lightnessF() > 0.5 else "white"
        hex_code = color.name(QColor.NameFormat.HexRgb).upper()
        self.color_preview_button.setText(f"{hex_code}\nClick to change")
        self.color_preview_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {color.name()};
                color: {text_color};
                border: 1px solid {colors.BORDER_MEDIUM};
                border-radius: 4px;
                text-align: center;
                padding: 5px;
            }}
            QPushButton:hover {{
                background-color: {colors.COLOR_HOVER};
                border: 2px solid transparent;
                border: 2px solid transparent;
                border: 2px solid transparent;
            }}
        """ )

    def _open_color_selector_dialog(self):
        color = ColorSelector.getColor(self.selected_color, self)
        if color.isValid():
            self.set_color_preview(color)

    def _create_gradient_color_widget(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        self.gradient_preview_button = QPushButton("Click to select gradient")
        self.gradient_preview_button.setFixedHeight(40)
        self.gradient_preview_button.clicked.connect(self._open_gradient_selector_dialog)
        layout.addWidget(self.gradient_preview_button)
        layout.addStretch()
        return widget

    def _update_gradient_preview_button(self):
        """Updates the preview button to reflect the selected gradient."""
        if not self.selected_gradient:
            self.gradient_preview_button.setText("Click to select gradient")
            self.gradient_preview_button.setStyleSheet("")
            return

        color1 = self.selected_gradient["color1"]
        color2 = self.selected_gradient["color2"]
        stops = self.selected_gradient["stops"]
        
        color1_hex = color1.name()
        color2_hex = color2.name()
        
        if stops == "Horizontal":
            gradient_stops = "x1: 0, y1: 0, x2: 1, y2: 0"
        elif stops == "Vertical":
            gradient_stops = "x1: 0, y1: 0, x2: 0, y2: 1"
        elif stops == "Up Diagonal":
            gradient_stops = "x1: 0, y1: 1, x2: 1, y2: 0"
        else: # Down Diagonal
            gradient_stops = "x1: 0, y1: 0, x2: 1, y2: 1"

        self.gradient_preview_button.setText("")
        self.gradient_preview_button.setStyleSheet(f"""
            QPushButton {{
                background-color: qlineargradient({gradient_stops}, stop: 0 {color1_hex}, stop: 1 {color2_hex});
                border: 1px solid {colors.BORDER_MEDIUM};
                border-radius: 4px;
            }}
            QPushButton:hover {{
                border: 2px solid {colors.COLOR_HOVER_FOCUS};
            }}
        """)

    def _open_gradient_selector_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Select Gradient")
        layout = QVBoxLayout(dialog)
        gradient_widget = GradientWidget(self.selected_gradient)
        layout.addWidget(gradient_widget)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec():
            preview = gradient_widget.selected_preview
            if preview:
                self.selected_gradient = {
                    "color1": preview.color1,
                    "color2": preview.color2,
                    "stops": preview.stops
                }
                self._update_gradient_preview_button()

    def _create_pattern_widget(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        self.pattern_preview_button = QPushButton("Click to select pattern")
        self.pattern_preview_button.setFixedHeight(40)
        self.pattern_preview_button.clicked.connect(self._open_pattern_selector_dialog)
        layout.addWidget(self.pattern_preview_button)
        layout.addStretch()
        return widget

    def _update_pattern_preview_button(self):
        """Updates the preview button icon to reflect the selected pattern."""
        if not self.selected_pattern:
            self.pattern_preview_button.setText("Click to select pattern")
            self.pattern_preview_button.setIcon(QIcon())
            self.pattern_preview_button.setStyleSheet("")
            return
            
        pattern_style = self.selected_pattern["pattern"]
        fg_color = self.selected_pattern["fg_color"]
        bg_color = self.selected_pattern["bg_color"]
        
        icon_pixmap = QPixmap(150, 32)
        icon_pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(icon_pixmap)
        pattern_brush = QBrush(fg_color, pattern_style)
        
        painter.fillRect(icon_pixmap.rect(), bg_color)
        painter.fillRect(icon_pixmap.rect(), pattern_brush)
        painter.end()
        
        self.pattern_preview_button.setText("")
        self.pattern_preview_button.setIcon(QIcon(icon_pixmap))
        self.pattern_preview_button.setIconSize(icon_pixmap.size())
        
        self.pattern_preview_button.setStyleSheet(f"""
            QPushButton {{
                border: 1px solid {colors.BORDER_MEDIUM};
                border-radius: 4px;
            }}
            QPushButton:hover {{
                border: 2px solid {colors.COLOR_HOVER_FOCUS};
            }}
        """ )

    def _open_pattern_selector_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Select Pattern")
        layout = QVBoxLayout(dialog)
        pattern_widget = PatternWidget(self.selected_pattern)
        layout.addWidget(pattern_widget)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec():
            preview = pattern_widget.selected_pattern_preview
            if preview:
                self.selected_pattern = {
                    "pattern": preview.pattern,
                    "fg_color": preview.fg_color,
                    "bg_color": preview.bg_color
                }
                self._update_pattern_preview_button()

    def _create_image_widget(self):
        widget = QWidget()
        main_layout = QVBoxLayout(widget)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Horizontal layout for the file path and browse button
        hbox = QHBoxLayout()
        
        # Label to show the file path
        self.image_path_label = QLineEdit()
        self.image_path_label.setPlaceholderText("No image selected")
        self.image_path_label.setReadOnly(True) # Make it non-editable
        
        # Browse button
        browse_button = QPushButton("Browse...")
        browse_button.clicked.connect(self.open_image_dialog)
        
        # Add widgets to the horizontal layout
        hbox.addWidget(self.image_path_label)
        hbox.addWidget(browse_button)
        
        # Add the horizontal layout to the main vertical layout
        main_layout.addLayout(hbox)
        
        main_layout.addStretch() # Pushes the hbox to the top

        return widget

    def open_image_dialog(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Select an Image", "", 
            "Image Files (*.png *.jpg *.jpeg *.bmp *.svg)"
        )
        if file_name:
            self.selected_image = file_name
            self.image_path_label.setText(file_name)
    
    def load_design_details(self, data):
        """Loads an existing design configuration into the dialog."""
        style_type = data.get("type")
        
        self.width_spinbox.setValue(data.get("width", 1920))
        self.height_spinbox.setValue(data.get("height", 1080))

        if style_type == "color":
            color_str = data.get("color", "#FFFFFFFF")
            self.selected_color = QColor(color_str)
            self.fill_color_radio.setChecked(True)
            self.set_color_preview(self.selected_color)
        
        elif style_type == "gradient":
            self.selected_gradient = data.get("gradient")
            if self.selected_gradient:
                # Convert color strings back to QColor objects
                self.selected_gradient["color1"] = QColor(self.selected_gradient["color1"])
                self.selected_gradient["color2"] = QColor(self.selected_gradient["color2"])
                self.gradient_color_radio.setChecked(True)
                self._update_gradient_preview_button()
        
        elif style_type == "pattern":
            self.selected_pattern = data.get("pattern")
            if self.selected_pattern:
                # Convert color strings back to QColor objects
                self.selected_pattern["fg_color"] = QColor(self.selected_pattern["fg_color"])
                self.selected_pattern["bg_color"] = QColor(self.selected_pattern["bg_color"])
                self.fill_pattern_radio.setChecked(True)
                self._update_pattern_preview_button()
        
        elif style_type == "image":
            self.selected_image = data.get("image_path")
            if self.selected_image:
                self.fill_image_radio.setChecked(True)
                self.image_path_label.setText(self.selected_image)

    def get_design_details(self):
        """
        Gathers the selected design details and returns them in a dictionary.
        Colors are stored as hex strings to ensure they are serializable.
        """
        details = {
            "width": self.width_spinbox.value(),
            "height": self.height_spinbox.value()
        }
        selected_id = self.radio_button_group.checkedId()
        
        if selected_id == 0:  # Fill Colour
            details["type"] = "color"
            details["color"] = self.selected_color.name(QColor.NameFormat.HexArgb)
        
        elif selected_id == 1:  # Gradient Colour
            if self.selected_gradient:
                grad_data = self.selected_gradient.copy()
                grad_data["color1"] = grad_data["color1"].name(QColor.NameFormat.HexArgb)
                grad_data["color2"] = grad_data["color2"].name(QColor.NameFormat.HexArgb)
                details["type"] = "gradient"
                details["gradient"] = grad_data
        
        elif selected_id == 2:  # Fill Pattern
            if self.selected_pattern:
                patt_data = self.selected_pattern.copy()
                patt_data["fg_color"] = patt_data["fg_color"].name(QColor.NameFormat.HexArgb)
                patt_data["bg_color"] = patt_data["bg_color"].name(QColor.NameFormat.HexArgb)
                details["type"] = "pattern"
                details["pattern"] = patt_data
        
        elif selected_id == 3:  # Fill Image
            if self.selected_image:
                details["type"] = "image"
                details["image_path"] = self.selected_image
        
        if "type" not in details:
            # Default to color if nothing else is valid
            details["type"] = "color"
            details["color"] = self.selected_color.name(QColor.NameFormat.HexArgb)

        return details
