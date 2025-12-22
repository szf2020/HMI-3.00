# main_window\widgets\dock_title_bar.py
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QToolButton, QStyle
from PySide6.QtCore import Qt
from styles import colors as c

class DockTitleBar(QWidget):
    """
    A custom title bar for QDockWidget that includes an icon and text.
    """
    def __init__(self, dock_widget, title, icon):
        super().__init__(dock_widget)
        self.dock_widget = dock_widget
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 2, 5, 2)
        layout.setSpacing(5)
        
        # Icon
        self.icon_label = QLabel()
        if icon:
            self.icon_label.setPixmap(icon.pixmap(16, 16))
        layout.addWidget(self.icon_label)
        
        # Title
        self.title_label = QLabel(title)
        layout.addWidget(self.title_label)
        
        layout.addStretch()
        
        # Float Button
        self.float_button = QToolButton()
        self.float_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_TitleBarNormalButton))
        self.float_button.setAutoRaise(True)
        self.float_button.setToolTip("Float")
        self.float_button.clicked.connect(lambda: self.dock_widget.setFloating(not self.dock_widget.isFloating()))
        layout.addWidget(self.float_button)
        
        # Close Button
        self.close_button = QToolButton()
        self.close_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_TitleBarCloseButton))
        self.close_button.setAutoRaise(True)
        self.close_button.setToolTip("Close")
        self.close_button.clicked.connect(self.dock_widget.close)
        layout.addWidget(self.close_button)
        
        # Styling
        self.setStyleSheet(f"""
            DockTitleBar {{
                background-color: {c.BG_DARK_QUATERNARY};
                border-bottom: 1px solid {c.BORDER_DARK};
            }}
            QLabel {{
                color: {c.TEXT_PRIMARY};
                font-weight: normal;
            }}
            QToolButton {{
                background: transparent;
                border: none;
                padding: 2px;
            }}
            QToolButton:hover {{
                background-color: {c.COLOR_HOVER};
            }}
        """)

    def mousePressEvent(self, event):
        # Allow dragging the dock widget by its custom title bar
        if event.button() == Qt.MouseButton.LeftButton:
            event.ignore() # Let the dock widget handle it
        super().mousePressEvent(event)
