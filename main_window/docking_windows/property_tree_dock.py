# main_window\docking_windows\property_tree_dock.py
"""
Property Tree Dock - A comprehensive property editor for selected graphic objects.
Provides Style and Text tabs for manipulating object properties.
"""
from PySide6.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QTabWidget, QLabel, QPushButton, QCheckBox, QComboBox, QSpinBox,
    QDoubleSpinBox, QSlider, QFrame, QGroupBox, QFontComboBox,
    QToolButton, QSizePolicy, QScrollArea, QButtonGroup, QMenu,
    QWidgetAction, QDialog, QDialogButtonBox, QFileDialog
)
from PySide6.QtCore import Qt, Signal, QSize, QPoint
from PySide6.QtGui import (
    QColor, QPen, QBrush, QFont, QIcon, QPainter, QLinearGradient,
    QPixmap, QAction
)
from ..widgets.color_selector import ColorSelector, ColorButton
from ..widgets.gradient_widget import GradientWidget
from ..widgets.pattern_widget import PatternWidget
from ..services.icon_service import IconService
from screen.base.base_graphic_object import BaseGraphicObject
from services.undo_commands import PropertyChangeCommand
from styles import colors


class QuickColorButton(QPushButton):
    """Small color button for quick color selection in the style presets row."""
    color_clicked = Signal(QColor)
    
    def __init__(self, color, parent=None):
        super().__init__(parent)
        self._color = QColor(color) if isinstance(color, str) else color
        self.setFixedSize(26, 26)
        self._update_style()
        self.clicked.connect(lambda: self.color_clicked.emit(self._color))
    
    def color(self):
        return self._color
    
    def setColor(self, color):
        self._color = QColor(color) if isinstance(color, str) else color
        self._update_style()
    
    def _update_style(self):
        self.setStyleSheet(
            f"background-color: {self._color.name()}; "
            f"border: 1px solid {colors.BORDER_MEDIUM}; "
            f"border-radius: 2px;"
        )


class ColorPickerButton(QPushButton):
    """A button that displays a color and opens a color picker dialog."""
    color_changed = Signal(QColor)
    
    def __init__(self, color=QColor("white"), parent=None):
        super().__init__(parent)
        self._color = QColor(color) if isinstance(color, str) else color
        self.setFixedSize(28, 20)
        self._update_style()
        self.clicked.connect(self._open_picker)
    
    def color(self):
        return self._color
    
    def setColor(self, color):
        new_color = QColor(color) if isinstance(color, str) else color
        if self._color != new_color:
            self._color = new_color
            self._update_style()
    
    def _update_style(self):
        self.setStyleSheet(
            f"background-color: {self._color.name()}; "
            f"border: 1px solid {colors.BORDER_MEDIUM};"
        )
    
    def _open_picker(self):
        new_color = ColorSelector.getColor(self._color, self)
        if new_color.isValid():
            self._color = new_color
            self._update_style()
            self.color_changed.emit(self._color)


class FillPreviewButton(QPushButton):
    """A button that shows a preview of the current fill style and opens fill options."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(28, 20)
        self._fill_type = "Color"  # Color, Gradient, Pattern, Image
        self._color = QColor("white")
        self._gradient_data = None
        self._pattern_data = None
        self._image_path = None
        self._update_style()
    
    def set_fill_color(self, color):
        self._fill_type = "Color"
        self._color = QColor(color) if isinstance(color, str) else color
        self._update_style()
    
    def set_fill_gradient(self, gradient_data):
        self._fill_type = "Gradient"
        self._gradient_data = gradient_data
        self._update_style()
    
    def set_fill_pattern(self, pattern_data):
        self._fill_type = "Pattern"
        self._pattern_data = pattern_data
        self._update_style()
    
    def set_fill_image(self, image_path):
        self._fill_type = "Image"
        self._image_path = image_path
        self._update_style()
    
    def get_brush(self):
        """Returns the QBrush based on current fill settings."""
        if self._fill_type == "Color":
            return QBrush(self._color)
        elif self._fill_type == "Gradient" and self._gradient_data:
            gradient = QLinearGradient()
            gradient.setColorAt(0, self._gradient_data.get("color1", QColor("white")))
            gradient.setColorAt(1, self._gradient_data.get("color2", QColor("black")))
            return QBrush(gradient)
        elif self._fill_type == "Pattern" and self._pattern_data:
            brush = QBrush(self._pattern_data.get("fg_color", QColor("black")), 
                          self._pattern_data.get("pattern", Qt.BrushStyle.SolidPattern))
            return brush
        return QBrush(self._color)
    
    def _update_style(self):
        if self._fill_type == "Color":
            self.setStyleSheet(
                f"background-color: {self._color.name()}; "
                f"border: 1px solid {colors.BORDER_MEDIUM};"
            )
        elif self._fill_type == "Gradient" and self._gradient_data:
            c1 = self._gradient_data.get("color1", QColor("white")).name()
            c2 = self._gradient_data.get("color2", QColor("black")).name()
            self.setStyleSheet(
                f"background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {c1}, stop:1 {c2}); "
                f"border: 1px solid {colors.BORDER_MEDIUM};"
            )
        elif self._fill_type == "Pattern":
            self.setStyleSheet(
                f"background-color: {colors.BG_DARK_TERTIARY}; "
                f"border: 1px solid {colors.BORDER_MEDIUM};"
            )
            self.setText("▦")
        elif self._fill_type == "Image":
            self.setStyleSheet(
                f"background-color: {colors.BG_DARK_TERTIARY}; "
                f"border: 1px solid {colors.BORDER_MEDIUM};"
            )
            self.setText("🖼")
        
        if self._fill_type in ["Color", "Gradient"]:
            self.setText("")


class FillTypeSelector(QWidget):
    """Widget that provides a dropdown with fill type options that open specific dialogs."""
    
    fill_changed = Signal(QBrush)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._fill_type = "Color"
        self._color = QColor("white")
        self._gradient_data = {"color1": QColor("#D0CECE"), "color2": QColor("#596978"), "stops": "Horizontal"}
        self._pattern_data = {"fg_color": QColor("black"), "bg_color": QColor("white"), "pattern": Qt.BrushStyle.SolidPattern}
        self._image_path = None
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        # Fill type dropdown
        self.fill_type_combo = QComboBox()
        self.fill_type_combo.addItems(["Color", "Gradient", "Pattern", "Image"])
        self.fill_type_combo.setFixedWidth(75)
        self.fill_type_combo.currentTextChanged.connect(self._on_fill_type_selected)
        layout.addWidget(self.fill_type_combo)
        
        # Preview/Edit button
        self.preview_btn = FillPreviewButton()
        self.preview_btn.clicked.connect(self._open_fill_editor)
        layout.addWidget(self.preview_btn)
    
    def _on_fill_type_selected(self, fill_type):
        """Handle fill type selection from dropdown."""
        self._fill_type = fill_type
        self._update_preview()
        # Automatically open the editor for the selected type
        self._open_fill_editor()
    
    def _open_fill_editor(self):
        """Open the appropriate editor dialog based on current fill type."""
        if self._fill_type == "Color":
            self._open_color_dialog()
        elif self._fill_type == "Gradient":
            self._open_gradient_dialog()
        elif self._fill_type == "Pattern":
            self._open_pattern_dialog()
        elif self._fill_type == "Image":
            self._open_image_dialog()
    
    def _open_color_dialog(self):
        """Open color picker dialog."""
        new_color = ColorSelector.getColor(self._color, self)
        if new_color.isValid():
            self._color = new_color
            self.preview_btn.set_fill_color(self._color)
            self._emit_fill()
    
    def _open_gradient_dialog(self):
        """Open gradient editor dialog."""
        dialog = QDialog(self.window())
        dialog.setWindowTitle("Gradient Fill")
        dialog.setMinimumSize(450, 350)
        
        layout = QVBoxLayout(dialog)
        
        gradient_widget = GradientWidget(self._gradient_data)
        layout.addWidget(gradient_widget)
        
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Get gradient data from the SELECTED preview variation
            selected_preview = gradient_widget.selected_preview
            if selected_preview:
                self._gradient_data = {
                    "color1": selected_preview.color1,
                    "color2": selected_preview.color2,
                    "stops": selected_preview.stops
                }
            else:
                # Fallback to radio button selection if no preview selected
                self._gradient_data = {
                    "color1": gradient_widget.color1_button.color(),
                    "color2": gradient_widget.color2_button.color(),
                    "stops": self._get_gradient_stops(gradient_widget)
                }
            self.preview_btn.set_fill_gradient(self._gradient_data)
            self._emit_fill()
    
    def _get_gradient_stops(self, widget):
        """Get the gradient direction from widget."""
        if widget.radio_horizontal.isChecked():
            return "Horizontal"
        elif widget.radio_vertical.isChecked():
            return "Vertical"
        elif widget.radio_up_diagonal.isChecked():
            return "Up Diagonal"
        elif widget.radio_down_diagonal.isChecked():
            return "Down Diagonal"
        return "Horizontal"
    
    def _open_pattern_dialog(self):
        """Open pattern editor dialog."""
        dialog = QDialog(self.window())
        dialog.setWindowTitle("Pattern Fill")
        dialog.setMinimumSize(350, 300)
        
        layout = QVBoxLayout(dialog)
        
        pattern_widget = PatternWidget(self._pattern_data)
        layout.addWidget(pattern_widget)
        
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Get selected pattern data
            selected_preview = pattern_widget.selected_pattern_preview
            self._pattern_data = {
                "fg_color": pattern_widget.fg_color_button.color(),
                "bg_color": pattern_widget.bg_color_button.color(),
                "pattern": selected_preview.pattern if selected_preview else Qt.BrushStyle.SolidPattern
            }
            self.preview_btn.set_fill_pattern(self._pattern_data)
            self._emit_fill()
    
    def _open_image_dialog(self):
        """Open image file dialog."""
        file_path, _ = QFileDialog.getOpenFileName(
            self.window(),
            "Select Fill Image",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.gif);;All Files (*)"
        )
        if file_path:
            self._image_path = file_path
            self.preview_btn.set_fill_image(self._image_path)
            self._emit_fill()
    
    def _update_preview(self):
        """Update the preview button based on current fill type."""
        if self._fill_type == "Color":
            self.preview_btn.set_fill_color(self._color)
        elif self._fill_type == "Gradient":
            self.preview_btn.set_fill_gradient(self._gradient_data)
        elif self._fill_type == "Pattern":
            self.preview_btn.set_fill_pattern(self._pattern_data)
        elif self._fill_type == "Image":
            self.preview_btn.set_fill_image(self._image_path)
    
    def _emit_fill(self):
        """Emit the current fill brush."""
        brush = self.get_brush()
        self.fill_changed.emit(brush)
    
    def get_brush(self):
        """Get the current fill as a QBrush."""
        if self._fill_type == "Color":
            return QBrush(self._color)
        elif self._fill_type == "Gradient" and self._gradient_data:
            stops = self._gradient_data.get("stops", "Horizontal")
            
            # Create gradient based on direction
            # Use ObjectBoundingMode coordinates (0-1 range) so gradient scales with object
            if stops == "Horizontal":
                gradient = QLinearGradient(0, 0.5, 1, 0.5)
            elif stops == "Vertical":
                gradient = QLinearGradient(0.5, 0, 0.5, 1)
            elif stops == "Up Diagonal":
                gradient = QLinearGradient(0, 1, 1, 0)
            elif stops == "Down Diagonal":
                gradient = QLinearGradient(0, 0, 1, 1)
            else:
                gradient = QLinearGradient(0, 0.5, 1, 0.5)
            
            # Set coordinate mode to ObjectBoundingMode so gradient scales with object
            gradient.setCoordinateMode(QLinearGradient.CoordinateMode.ObjectBoundingMode)
            gradient.setColorAt(0, self._gradient_data.get("color1", QColor("white")))
            gradient.setColorAt(1, self._gradient_data.get("color2", QColor("black")))
            return QBrush(gradient)
        elif self._fill_type == "Pattern" and self._pattern_data:
            brush = QBrush(self._pattern_data.get("fg_color", QColor("black")), 
                          self._pattern_data.get("pattern", Qt.BrushStyle.SolidPattern))
            return brush
        elif self._fill_type == "Image" and self._image_path:
            pixmap = QPixmap(self._image_path)
            if not pixmap.isNull():
                return QBrush(pixmap)
        return QBrush(self._color)
    
    def set_from_brush(self, brush):
        """Set the fill type selector from an existing brush."""
        style = brush.style()
        if style == Qt.BrushStyle.NoBrush:
            return
        elif style == Qt.BrushStyle.SolidPattern:
            self._fill_type = "Color"
            self._color = brush.color()
            self.fill_type_combo.setCurrentText("Color")
        elif style == Qt.BrushStyle.LinearGradientPattern:
            self._fill_type = "Gradient"
            self.fill_type_combo.setCurrentText("Gradient")
        elif style == Qt.BrushStyle.TexturePattern:
            self._fill_type = "Image"
            self.fill_type_combo.setCurrentText("Image")
        else:
            # Assume pattern
            self._fill_type = "Pattern"
            self._pattern_data["pattern"] = style
            self._pattern_data["fg_color"] = brush.color()
            self.fill_type_combo.setCurrentText("Pattern")
        self._update_preview()


class StyleTab(QWidget):
    """Style tab for fill, gradient, line, and effects properties."""
    
    # Signals for property changes
    fill_changed = Signal(QBrush)
    line_changed = Signal(QPen)
    opacity_changed = Signal(float)
    rounded_changed = Signal(bool)
    shadow_changed = Signal(bool)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._syncing = False
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        # Quick color presets row
        presets_layout = QHBoxLayout()
        presets_layout.setSpacing(2)
        
        self.preset_colors = [
            "#FFFFFF", "#FFD754", "#6AC2FD", "#9752FF",
            "#65FF65", "#FF6262", "#FFEE55", "#6161FF"
        ]
        self.preset_buttons = []
        for color in self.preset_colors:
            btn = QuickColorButton(color)
            btn.color_clicked.connect(self._on_preset_color_clicked)
            self.preset_buttons.append(btn)
            presets_layout.addWidget(btn)
        
        # Navigation arrows for more presets
        nav_btn = QToolButton()
        nav_btn.setArrowType(Qt.ArrowType.RightArrow)
        nav_btn.setFixedSize(20, 26)
        presets_layout.addWidget(nav_btn)
        presets_layout.addStretch()
        
        layout.addLayout(presets_layout)
        
        # === Fill Section ===
        fill_layout = QHBoxLayout()
        self.fill_checkbox = QCheckBox("Fill  ")
        self.fill_checkbox.setChecked(True)
        self.fill_checkbox.stateChanged.connect(self._on_fill_checkbox_changed)
        fill_layout.addWidget(self.fill_checkbox)
        
        # Fill type selector with integrated dropdown and preview
        self.fill_selector = FillTypeSelector()
        self.fill_selector.fill_changed.connect(self._on_fill_selector_changed)
        fill_layout.addWidget(self.fill_selector)
        
        # Eyedropper button
        self.eyedropper_btn = QToolButton()
        self.eyedropper_btn.setIcon(IconService.get_icon('edit-tool-eyedropper'))
        fill_layout.addWidget(self.eyedropper_btn)
        fill_layout.addStretch()
        
        layout.addLayout(fill_layout)
        
        # === Line Section (all controls in single row) ===
        line_layout = QHBoxLayout()
        line_layout.setSpacing(8)
        
        self.line_checkbox = QCheckBox("Line")
        self.line_checkbox.setChecked(True)
        self.line_checkbox.stateChanged.connect(self._on_line_changed)
        line_layout.addWidget(self.line_checkbox)
        
        # Line style dropdown
        self.line_style_combo = QComboBox()
        self.line_style_combo.addItems(["Solid", "Dash", "Dot", "DashDot", "DashDotDot"])
        self.line_style_combo.setFixedWidth(75)
        self.line_style_combo.currentTextChanged.connect(self._on_line_style_changed)
        line_layout.addWidget(self.line_style_combo)
        
        # Line color button
        self.line_color_btn = ColorPickerButton(QColor("black"))
        self.line_color_btn.color_changed.connect(self._on_line_color_changed)
        line_layout.addWidget(self.line_color_btn)
        
        # Line width spinbox
        self.line_width_spin = QDoubleSpinBox()
        self.line_width_spin.setRange(0.0, 50.0)
        self.line_width_spin.setValue(0.3)
        self.line_width_spin.setSingleStep(0.1)
        self.line_width_spin.setSuffix(" mm")
        self.line_width_spin.setFixedWidth(70)
        self.line_width_spin.valueChanged.connect(self._on_line_width_changed)
        line_layout.addWidget(self.line_width_spin)
        
        line_layout.addStretch()
        layout.addLayout(line_layout)
        
        # === Opacity Section ===
        opacity_layout = QHBoxLayout()
        opacity_layout.addWidget(QLabel("Opacity  "))
        self.opacity_spin = QSpinBox()
        self.opacity_spin.setRange(0, 100)
        self.opacity_spin.setValue(100)
        self.opacity_spin.setSuffix(" %")
        self.opacity_spin.setFixedWidth(60)
        self.opacity_spin.valueChanged.connect(self._on_opacity_changed)
        opacity_layout.addWidget(self.opacity_spin)
        
        # Opacity slider
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(0, 100)
        self.opacity_slider.setValue(100)
        self.opacity_slider.setFixedWidth(120)
        self.opacity_slider.valueChanged.connect(self._on_opacity_slider_changed)
        self.opacity_spin.valueChanged.connect(self.opacity_slider.setValue)
        opacity_layout.addWidget(self.opacity_slider)
        
        opacity_layout.addStretch()
        layout.addLayout(opacity_layout)
        
        # === Effects Section ===
        effects_layout = QHBoxLayout()
        effects_layout.setSpacing(8)
        
        self.rounded_checkbox = QCheckBox("Rounded")
        self.rounded_checkbox.stateChanged.connect(self._on_rounded_checkbox_changed)
        effects_layout.addWidget(self.rounded_checkbox)
        
        self.shadow_checkbox = QCheckBox("Shadow")
        self.shadow_checkbox.stateChanged.connect(lambda s: self.shadow_changed.emit(s == Qt.CheckState.Checked.value))
        effects_layout.addWidget(self.shadow_checkbox)
        
        effects_layout.addStretch()
        layout.addLayout(effects_layout)
        layout.addStretch()
    
    def _on_rounded_checkbox_changed(self, state):
        """Handle rounded checkbox change - only emit if not syncing."""
        if not self._syncing:
            self.rounded_changed.emit(state == Qt.CheckState.Checked.value)
    
    def _on_preset_color_clicked(self, color):
        """Handle quick color preset selection."""
        self.fill_selector._color = color
        self.fill_selector._fill_type = "Color"
        self.fill_selector.fill_type_combo.setCurrentText("Color")
        self.fill_selector._update_preview()
        self._emit_fill_brush()
    
    def _on_fill_checkbox_changed(self, state):
        """Handle fill checkbox change."""
        self._emit_fill_brush()
    
    def _on_fill_selector_changed(self, brush):
        """Handle fill selector change."""
        if not self._syncing:
            self.fill_changed.emit(brush)
    
    def _emit_fill_brush(self):
        """Emit the fill brush based on current settings."""
        if self._syncing:
            return
        if self.fill_checkbox.isChecked():
            brush = self.fill_selector.get_brush()
        else:
            brush = QBrush(Qt.BrushStyle.NoBrush)
        self.fill_changed.emit(brush)
    
    def _on_line_changed(self, state):
        """Handle line checkbox change."""
        self._emit_line_pen()
    
    def _on_line_color_changed(self, color):
        """Handle line color change."""
        self._emit_line_pen()
    
    def _on_line_style_changed(self, style):
        """Handle line style change."""
        self._emit_line_pen()
    
    def _on_line_width_changed(self, width):
        """Handle line width change."""
        self._emit_line_pen()
    
    def _emit_line_pen(self):
        """Emit the line pen based on current settings."""
        if self._syncing:
            return
        if self.line_checkbox.isChecked():
            pen = QPen(self.line_color_btn.color())
            pen.setWidthF(self.line_width_spin.value())
            
            style_map = {
                "Solid": Qt.PenStyle.SolidLine,
                "Dash": Qt.PenStyle.DashLine,
                "Dot": Qt.PenStyle.DotLine,
                "DashDot": Qt.PenStyle.DashDotLine,
                "DashDotDot": Qt.PenStyle.DashDotDotLine
            }
            pen.setStyle(style_map.get(self.line_style_combo.currentText(), Qt.PenStyle.SolidLine))
        else:
            pen = QPen(Qt.PenStyle.NoPen)
        self.line_changed.emit(pen)
    
    def _on_opacity_changed(self, value):
        """Handle opacity change."""
        if not self._syncing:
            self.opacity_changed.emit(value / 100.0)
    
    def _on_opacity_slider_changed(self, value):
        """Handle opacity slider change - sync to spinbox."""
        if self.opacity_spin.value() != value:
            self.opacity_spin.setValue(value)
    
    def set_opacity_ui(self, value):
        """Set opacity UI without triggering signals (for external sync).
        
        Args:
            value: Opacity value (0-100 as integer percentage)
        """
        self._syncing = True
        try:
            self.opacity_spin.setValue(value)
            self.opacity_slider.setValue(value)
        finally:
            self._syncing = False
    
    def update_from_item(self, item):
        """Update UI from a selected item's properties."""
        self._syncing = True
        try:
            if item and hasattr(item, 'item'):
                inner = item.item
                
                # Update fill
                brush = inner.brush()
                has_fill = brush.style() != Qt.BrushStyle.NoBrush
                self.fill_checkbox.setChecked(has_fill)
                if has_fill:
                    self.fill_selector.set_from_brush(brush)
                
                # Update line
                pen = inner.pen()
                has_line = pen.style() != Qt.PenStyle.NoPen
                self.line_checkbox.setChecked(has_line)
                if has_line:
                    self.line_color_btn.setColor(pen.color())
                    self.line_width_spin.setValue(pen.widthF())
                    
                    style_map = {
                        Qt.PenStyle.SolidLine: "Solid",
                        Qt.PenStyle.DashLine: "Dash",
                        Qt.PenStyle.DotLine: "Dot",
                        Qt.PenStyle.DashDotLine: "DashDot",
                        Qt.PenStyle.DashDotDotLine: "DashDotDot"
                    }
                    self.line_style_combo.setCurrentText(style_map.get(pen.style(), "Solid"))
                
                # Update opacity
                opacity = item.opacity()
                self.opacity_spin.setValue(int(opacity * 100))
                
                # Update rounded checkbox (for RectangleObject)
                if hasattr(item, 'rounded_enabled'):
                    self.rounded_checkbox.setChecked(item.rounded_enabled)
                else:
                    self.rounded_checkbox.setChecked(False)
        finally:
            self._syncing = False


class TextTab(QWidget):
    """Text tab for font and text formatting properties."""
    
    # Signals
    font_changed = Signal(QFont)
    font_color_changed = Signal(QColor)
    alignment_changed = Signal(Qt.AlignmentFlag)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._syncing = False
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        
        # === Font Section ===
        layout.addWidget(QLabel("Font"))
        
        font_layout = QHBoxLayout()
        self.font_combo = QFontComboBox()
        self.font_combo.setCurrentFont(QFont("Helvetica"))
        self.font_combo.currentFontChanged.connect(self._on_font_changed)
        font_layout.addWidget(self.font_combo)
        layout.addLayout(font_layout)
        
        # Font style buttons and size
        style_layout = QHBoxLayout()
        
        self.bold_btn = QToolButton()
        self.bold_btn.setText("B")
        self.bold_btn.setCheckable(True)
        self.bold_btn.setFixedSize(24, 24)
        self.bold_btn.setStyleSheet("font-weight: bold;")
        self.bold_btn.toggled.connect(self._on_font_changed)
        style_layout.addWidget(self.bold_btn)
        
        self.italic_btn = QToolButton()
        self.italic_btn.setText("I")
        self.italic_btn.setCheckable(True)
        self.italic_btn.setFixedSize(24, 24)
        self.italic_btn.setStyleSheet("font-style: italic;")
        self.italic_btn.toggled.connect(self._on_font_changed)
        style_layout.addWidget(self.italic_btn)
        
        self.underline_btn = QToolButton()
        self.underline_btn.setText("U")
        self.underline_btn.setCheckable(True)
        self.underline_btn.setFixedSize(24, 24)
        self.underline_btn.setStyleSheet("text-decoration: underline;")
        self.underline_btn.toggled.connect(self._on_font_changed)
        style_layout.addWidget(self.underline_btn)
        
        self.strikethrough_btn = QToolButton()
        self.strikethrough_btn.setText("S")
        self.strikethrough_btn.setCheckable(True)
        self.strikethrough_btn.setFixedSize(24, 24)
        self.strikethrough_btn.setStyleSheet("text-decoration: line-through;")
        self.strikethrough_btn.toggled.connect(self._on_font_changed)
        style_layout.addWidget(self.strikethrough_btn)
        
        style_layout.addStretch()
        
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(6, 144)
        self.font_size_spin.setValue(12)
        self.font_size_spin.setSuffix(" px")
        self.font_size_spin.setFixedWidth(60)
        self.font_size_spin.valueChanged.connect(self._on_font_changed)
        style_layout.addWidget(self.font_size_spin)
        
        layout.addLayout(style_layout)
        
        # Alignment buttons
        align_layout = QHBoxLayout()
        
        self.align_left_btn = QToolButton()
        self.align_left_btn.setIcon(IconService.get_icon('align-horizontal-left'))
        self.align_left_btn.setCheckable(True)
        self.align_left_btn.setFixedSize(24, 24)
        align_layout.addWidget(self.align_left_btn)
        
        self.align_center_btn = QToolButton()
        self.align_center_btn.setIcon(IconService.get_icon('align-horizontal-center'))
        self.align_center_btn.setCheckable(True)
        self.align_center_btn.setFixedSize(24, 24)
        align_layout.addWidget(self.align_center_btn)
        
        self.align_right_btn = QToolButton()
        self.align_right_btn.setIcon(IconService.get_icon('align-horizontal-right'))
        self.align_right_btn.setCheckable(True)
        self.align_right_btn.setFixedSize(24, 24)
        align_layout.addWidget(self.align_right_btn)
        
        # Make alignment buttons exclusive
        self.align_group = QButtonGroup(self)
        self.align_group.addButton(self.align_left_btn)
        self.align_group.addButton(self.align_center_btn)
        self.align_group.addButton(self.align_right_btn)
        self.align_left_btn.setChecked(True)
        
        align_layout.addSpacing(10)
        
        self.align_top_btn = QToolButton()
        self.align_top_btn.setIcon(IconService.get_icon('align-vertical-top'))
        self.align_top_btn.setCheckable(True)
        self.align_top_btn.setFixedSize(24, 24)
        align_layout.addWidget(self.align_top_btn)
        
        self.align_vcenter_btn = QToolButton()
        self.align_vcenter_btn.setIcon(IconService.get_icon('align-vertical-center'))
        self.align_vcenter_btn.setCheckable(True)
        self.align_vcenter_btn.setFixedSize(24, 24)
        align_layout.addWidget(self.align_vcenter_btn)
        
        self.align_bottom_btn = QToolButton()
        self.align_bottom_btn.setIcon(IconService.get_icon('align-vertical-bottom'))
        self.align_bottom_btn.setCheckable(True)
        self.align_bottom_btn.setFixedSize(24, 24)
        align_layout.addWidget(self.align_bottom_btn)
        
        # Make vertical alignment buttons exclusive
        self.valign_group = QButtonGroup(self)
        self.valign_group.addButton(self.align_top_btn)
        self.valign_group.addButton(self.align_vcenter_btn)
        self.valign_group.addButton(self.align_bottom_btn)
        self.align_vcenter_btn.setChecked(True)
        
        align_layout.addStretch()
        layout.addLayout(align_layout)
        
        # Position dropdown
        pos_layout = QHBoxLayout()
        pos_layout.addWidget(QLabel("Position"))
        self.position_combo = QComboBox()
        self.position_combo.addItems(["Center", "Top", "Bottom", "Left", "Right"])
        self.position_combo.setFixedWidth(80)
        pos_layout.addWidget(self.position_combo)
        pos_layout.addStretch()
        layout.addLayout(pos_layout)
        
        # Writing Direction
        dir_layout = QHBoxLayout()
        dir_layout.addWidget(QLabel("Writing Direction"))
        self.direction_combo = QComboBox()
        self.direction_combo.addItems(["Automatic", "Left to Right", "Right to Left"])
        self.direction_combo.setFixedWidth(100)
        dir_layout.addWidget(self.direction_combo)
        dir_layout.addStretch()
        layout.addLayout(dir_layout)
        
        # === Color Options ===
        # Font Color
        font_color_layout = QHBoxLayout()
        self.font_color_checkbox = QCheckBox("Font Color")
        self.font_color_checkbox.setChecked(True)
        font_color_layout.addWidget(self.font_color_checkbox)
        self.font_color_btn = ColorPickerButton(QColor("black"))
        self.font_color_btn.color_changed.connect(self._on_font_color_changed)
        font_color_layout.addWidget(self.font_color_btn)
        font_color_layout.addStretch()
        layout.addLayout(font_color_layout)
        
        # Background Color
        bg_color_layout = QHBoxLayout()
        self.bg_color_checkbox = QCheckBox("Background Color")
        bg_color_layout.addWidget(self.bg_color_checkbox)
        self.bg_color_btn = ColorPickerButton(QColor("white"))
        bg_color_layout.addWidget(self.bg_color_btn)
        bg_color_layout.addStretch()
        layout.addLayout(bg_color_layout)
        
        # Border Color
        border_color_layout = QHBoxLayout()
        self.border_color_checkbox = QCheckBox("Border Color")
        border_color_layout.addWidget(self.border_color_checkbox)
        self.border_color_btn = ColorPickerButton(QColor("black"))
        border_color_layout.addWidget(self.border_color_btn)
        border_color_layout.addStretch()
        layout.addLayout(border_color_layout)
        
        # Shadow
        shadow_layout = QHBoxLayout()
        self.text_shadow_checkbox = QCheckBox("Shadow")
        shadow_layout.addWidget(self.text_shadow_checkbox)
        shadow_layout.addStretch()
        layout.addLayout(shadow_layout)
        
        # === Text Options ===
        self.word_wrap_checkbox = QCheckBox("Word Wrap")
        self.word_wrap_checkbox.setChecked(True)
        layout.addWidget(self.word_wrap_checkbox)
        
        self.formatted_text_checkbox = QCheckBox("Formatted Text")
        self.formatted_text_checkbox.setChecked(True)
        layout.addWidget(self.formatted_text_checkbox)
        
        # === Opacity ===
        opacity_layout = QHBoxLayout()
        opacity_layout.addWidget(QLabel("Opacity"))
        self.text_opacity_spin = QSpinBox()
        self.text_opacity_spin.setRange(0, 100)
        self.text_opacity_spin.setValue(100)
        self.text_opacity_spin.setSuffix(" %")
        self.text_opacity_spin.setFixedWidth(60)
        opacity_layout.addWidget(self.text_opacity_spin)
        opacity_layout.addStretch()
        layout.addLayout(opacity_layout)
        
        # === Spacing ===
        spacing_layout = QHBoxLayout()
        spacing_layout.addWidget(QLabel("Spacing"))
        self.h_spacing_spin = QDoubleSpinBox()
        self.h_spacing_spin.setRange(0.0, 100.0)
        self.h_spacing_spin.setValue(0)
        self.h_spacing_spin.setSuffix(" mm")
        self.h_spacing_spin.setFixedWidth(65)
        spacing_layout.addWidget(self.h_spacing_spin)
        
        self.v_spacing_spin = QDoubleSpinBox()
        self.v_spacing_spin.setRange(0.0, 100.0)
        self.v_spacing_spin.setValue(0.5)
        self.v_spacing_spin.setSuffix(" mm")
        self.v_spacing_spin.setFixedWidth(65)
        spacing_layout.addWidget(self.v_spacing_spin)
        spacing_layout.addStretch()
        layout.addLayout(spacing_layout)
        
        # Margin labels
        margin_labels = QHBoxLayout()
        margin_labels.addSpacing(50)
        margin_labels.addWidget(QLabel("Top"))
        margin_labels.addSpacing(40)
        margin_labels.addWidget(QLabel("Global"))
        margin_labels.addStretch()
        layout.addLayout(margin_labels)
        
        # Margins row 1 (top)
        margins_top = QHBoxLayout()
        self.margin_top_spin = QDoubleSpinBox()
        self.margin_top_spin.setRange(0.0, 100.0)
        self.margin_top_spin.setValue(0)
        self.margin_top_spin.setSuffix(" mm")
        self.margin_top_spin.setFixedWidth(65)
        margins_top.addWidget(self.margin_top_spin)
        
        self.margin_top2_spin = QDoubleSpinBox()
        self.margin_top2_spin.setRange(0.0, 100.0)
        self.margin_top2_spin.setValue(0)
        self.margin_top2_spin.setSuffix(" mm")
        self.margin_top2_spin.setFixedWidth(65)
        margins_top.addWidget(self.margin_top2_spin)
        margins_top.addStretch()
        layout.addLayout(margins_top)
        
        # Margins row 2 (left/bottom/right)
        margins_bottom = QHBoxLayout()
        self.margin_left_spin = QDoubleSpinBox()
        self.margin_left_spin.setRange(0.0, 100.0)
        self.margin_left_spin.setValue(0)
        self.margin_left_spin.setSuffix(" mm")
        self.margin_left_spin.setFixedWidth(65)
        margins_bottom.addWidget(self.margin_left_spin)
        
        self.margin_bottom_spin = QDoubleSpinBox()
        self.margin_bottom_spin.setRange(0.0, 100.0)
        self.margin_bottom_spin.setValue(0)
        self.margin_bottom_spin.setSuffix(" mm")
        self.margin_bottom_spin.setFixedWidth(65)
        margins_bottom.addWidget(self.margin_bottom_spin)
        
        self.margin_right_spin = QDoubleSpinBox()
        self.margin_right_spin.setRange(0.0, 100.0)
        self.margin_right_spin.setValue(0)
        self.margin_right_spin.setSuffix(" mm")
        self.margin_right_spin.setFixedWidth(65)
        margins_bottom.addWidget(self.margin_right_spin)
        margins_bottom.addStretch()
        layout.addLayout(margins_bottom)
        
        # Margin labels (Left/Bottom/Right)
        margin_labels2 = QHBoxLayout()
        margin_labels2.addWidget(QLabel("Left"))
        margin_labels2.addSpacing(35)
        margin_labels2.addWidget(QLabel("Bottom"))
        margin_labels2.addSpacing(25)
        margin_labels2.addWidget(QLabel("Right"))
        margin_labels2.addStretch()
        layout.addLayout(margin_labels2)
        
        # Clear Formatting button
        self.clear_format_btn = QPushButton("Clear Formatting")
        self.clear_format_btn.clicked.connect(self._on_clear_formatting)
        layout.addWidget(self.clear_format_btn)
        
        layout.addStretch()
    
    def _on_font_changed(self, *args):
        """Emit font changed signal."""
        if self._syncing:
            return
        font = self.font_combo.currentFont()
        font.setPointSize(self.font_size_spin.value())
        font.setBold(self.bold_btn.isChecked())
        font.setItalic(self.italic_btn.isChecked())
        font.setUnderline(self.underline_btn.isChecked())
        font.setStrikeOut(self.strikethrough_btn.isChecked())
        self.font_changed.emit(font)
    
    def _on_font_color_changed(self, color):
        """Emit font color changed signal."""
        if not self._syncing:
            self.font_color_changed.emit(color)
    
    def _on_clear_formatting(self):
        """Reset text formatting to defaults."""
        self._syncing = True
        try:
            self.font_combo.setCurrentFont(QFont("Helvetica"))
            self.font_size_spin.setValue(12)
            self.bold_btn.setChecked(False)
            self.italic_btn.setChecked(False)
            self.underline_btn.setChecked(False)
            self.strikethrough_btn.setChecked(False)
            self.font_color_btn.setColor(QColor("black"))
        finally:
            self._syncing = False
        self._on_font_changed()
    
    def update_from_item(self, item):
        """Update UI from item properties (placeholder for text items)."""
        pass


class PropertyTreeDock(QDockWidget):
    """
    Dockable window to display and edit properties of selected objects.
    Provides Style and Text tabs for property editing.
    """
    def __init__(self, main_window):
        """
        Initializes the Property Tree dock widget.

        Args:
            main_window (QMainWindow): The main window instance.
        """
        super().__init__("Property Tree", main_window)
        self.main_window = main_window
        self.setObjectName("property_tree")
        
        # Track current state
        self.current_canvas = None
        self.selected_items = []
        self._syncing = False
        
        # Create main widget with tabs
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        
        # Create tabs
        self.style_tab = StyleTab()
        self.text_tab = TextTab()
        
        self.tab_widget.addTab(self.style_tab, "Style")
        self.tab_widget.addTab(self.text_tab, "Text")
        
        main_layout.addWidget(self.tab_widget)
        self.setWidget(main_widget)
        
        # Connect tab signals to property update methods
        self._connect_signals()
        
        # Initial state: disable until selection
        self._set_enabled(False)
    
    def _connect_signals(self):
        """Connect tab signals to canvas property updates."""
        # Style tab signals
        self.style_tab.fill_changed.connect(self._on_fill_changed)
        self.style_tab.line_changed.connect(self._on_line_changed)
        self.style_tab.opacity_changed.connect(self._on_opacity_changed)
        self.style_tab.rounded_changed.connect(self._on_rounded_changed)
    
    def _set_enabled(self, enabled):
        """Enable or disable the property controls."""
        self.style_tab.setEnabled(enabled)
        self.text_tab.setEnabled(enabled)
    
    def set_current_canvas(self, canvas):
        """Set the current canvas to work with."""
        self.current_canvas = canvas
        if canvas:
            # Update from current selection
            selected = [item for item in canvas.scene.selectedItems() 
                       if isinstance(item, BaseGraphicObject)]
            self._update_from_selection(selected)
    
    def on_selection_changed(self, selected_items, deselected_items):
        """Handle canvas selection change signal."""
        if self._syncing:
            return
        
        # Filter to only BaseGraphicObject items
        valid_items = [item for item in selected_items if isinstance(item, BaseGraphicObject)]
        self.selected_items = valid_items
        self._update_from_selection(valid_items)
    
    def _update_from_selection(self, items):
        """Update all tabs from the selected items."""
        self._syncing = True
        try:
            if not items:
                self._set_enabled(False)
                return
            
            self._set_enabled(True)
            
            # For single selection, update from that item
            if len(items) == 1:
                item = items[0]
                self.style_tab.update_from_item(item)
                self.text_tab.update_from_item(item)
                
                # Sync corner radius mode with transform handler
                self._sync_corner_radius_mode(item)
            else:
                # For multiple selection, could show common properties
                # For now, just use the first item
                self.style_tab.update_from_item(items[0])
                self.text_tab.update_from_item(items[0])
        finally:
            self._syncing = False
    
    def _sync_corner_radius_mode(self, item):
        """Sync corner radius mode between item and transform handler."""
        if self.current_canvas and hasattr(self.current_canvas, 'transform_handler'):
            handler = self.current_canvas.transform_handler
            if handler and hasattr(item, 'rounded_enabled'):
                handler.set_corner_radius_mode(item.rounded_enabled)
    
    # === Property Change Handlers ===
    
    def _on_fill_changed(self, brush):
        """Apply fill brush change to selected items."""
        if self._syncing or not self.selected_items:
            return
        for item in self.selected_items:
            if hasattr(item, 'item'):
                old_brush = item.item.brush()
                if self.current_canvas and hasattr(self.current_canvas, 'undo_stack'):
                    cmd = PropertyChangeCommand(item, 'brush', old_brush, brush, "Change Fill")
                    self.current_canvas.undo_stack.push(cmd)
                else:
                    item.item.setBrush(brush)
    
    def _on_line_changed(self, pen):
        """Apply line pen change to selected items."""
        if self._syncing or not self.selected_items:
            return
        for item in self.selected_items:
            if hasattr(item, 'item'):
                old_pen = item.item.pen()
                if self.current_canvas and hasattr(self.current_canvas, 'undo_stack'):
                    cmd = PropertyChangeCommand(item, 'pen', old_pen, pen, "Change Line")
                    self.current_canvas.undo_stack.push(cmd)
                else:
                    item.item.setPen(pen)
    
    def _on_opacity_changed(self, opacity):
        """Apply opacity change to selected items."""
        if self._syncing or not self.selected_items:
            return
        for item in self.selected_items:
            old_opacity = item.opacity()
            if self.current_canvas and hasattr(self.current_canvas, 'undo_stack'):
                cmd = PropertyChangeCommand(item, 'opacity', old_opacity, opacity, "Change Opacity")
                self.current_canvas.undo_stack.push(cmd)
            else:
                item.setOpacity(opacity)
    
    def _on_rounded_changed(self, enabled):
        """Handle rounded corners checkbox change."""
        if self._syncing or not self.selected_items:
            return
        
        # Import here to avoid circular imports
        from screen.base.base_graphic_object import RectangleObject
        
        # Enable/disable rounded mode on selected items
        for item in self.selected_items:
            if isinstance(item, RectangleObject):
                item.rounded_enabled = enabled
        
        # Update transform handler to show/hide corner radius handles
        if self.current_canvas and hasattr(self.current_canvas, 'transform_handler'):
            handler = self.current_canvas.transform_handler
            if handler:
                handler.set_corner_radius_mode(enabled)
                handler.update_geometry()
    
    def set_opacity_from_layers(self, value):
        """Update opacity UI from layers dock (0-100 integer value).
        
        Args:
            value: Opacity value (0-100 as integer percentage)
        """
        self.style_tab.set_opacity_ui(value)
    
    def get_style_tab_opacity_signal(self):
        """Get the style tab's opacity_changed signal for external connections."""
        return self.style_tab.opacity_changed
