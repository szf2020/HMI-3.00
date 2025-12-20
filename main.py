# main.py
import sys
from PySide6.QtWidgets import QApplication, QStyleFactory
from PySide6.QtGui import QIcon, QPalette, QColor
from PySide6.QtCore import Qt
from main_window.main_window import MainWindow
from services.settings_service import SettingsService
from main_window.services.icon_service import IconService
from debug_utils import setup_logging

def main():
    """
    The main function to launch the application.
    """
    # Set up logging
    setup_logging(debug_mode=True)

    # Create an instance of QApplication
    app = QApplication(sys.argv)
    
    # Set the application icon
    app.setWindowIcon(IconService.get_icon("HMI-Designer-icon"))

    # Set the application style to Fusion
    app.setStyle(QStyleFactory.create('Fusion'))

    # Create and set a dark palette for a consistent dark theme
    dark_palette = QPalette()
    dark_palette.setColor(QPalette.ColorRole.Window, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
    dark_palette.setColor(QPalette.ColorRole.Base, QColor(25, 25, 25))
    dark_palette.setColor(QPalette.ColorRole.AlternateBase, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.ColorRole.ToolTipBase, Qt.GlobalColor.black)
    dark_palette.setColor(QPalette.ColorRole.ToolTipText, Qt.GlobalColor.white)
    dark_palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
    dark_palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
    dark_palette.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
    dark_palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.ColorRole.Highlight, Qt.GlobalColor.transparent)
    dark_palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.white)
    app.setPalette(dark_palette)

    # Load and apply centralized stylesheets
    from styles import stylesheets
    global_stylesheet = (
        stylesheets.get_tool_button_stylesheet() + 
        stylesheets.get_menu_stylesheet() + 
        stylesheets.get_toolbar_stylesheet()
    )
    app.setStyleSheet(global_stylesheet)
    
    # Initialize the settings service
    settings_service = SettingsService('settings.json')
    
    # Create an instance of our MainWindow
    window = MainWindow(settings_service)

    # Show the window
    window.show()

    # Start the application's event loop
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
