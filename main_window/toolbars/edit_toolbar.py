# main_window\toolbars\edit_toolbar.py
from PySide6.QtWidgets import QToolBar

class EditToolbar(QToolBar):
    def __init__(self, main_window, edit_menu):
        super().__init__("Edit", main_window)
        self.main_window = main_window
        
        self.addAction(edit_menu.cut_action)
        self.addAction(edit_menu.copy_action)
        self.addAction(edit_menu.paste_action)
        self.addSeparator()
        self.addAction(edit_menu.undo_action)
        self.addAction(edit_menu.redo_action)
        self.addSeparator()
        self.addAction(edit_menu.delete_action)