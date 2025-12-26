# main_window\toolbars\alignment_toolbar.py
from PySide6.QtWidgets import QToolBar

class AlignmentToolbar(QToolBar):
    def __init__(self, main_window, edit_menu):
        super().__init__("Alignment", main_window)
        self.main_window = main_window
        
        # Alignment actions
        self.addAction(edit_menu.align_left_action)
        self.addAction(edit_menu.align_center_action)
        self.addAction(edit_menu.align_right_action)
        self.addSeparator()
        self.addAction(edit_menu.align_top_action)
        self.addAction(edit_menu.align_middle_action)
        self.addAction(edit_menu.align_bottom_action)
        self.addSeparator()
        self.addAction(edit_menu.dist_horz_action)
        self.addAction(edit_menu.dist_vert_action)
        self.addSeparator()
        
        # Stacking Order actions
        self.addAction(edit_menu.move_to_front_action)
        self.addAction(edit_menu.move_front_layer_action)
        self.addAction(edit_menu.move_back_layer_action)
        self.addAction(edit_menu.move_to_back_action)
        self.addSeparator()
        
        # Flip and Rotate actions
        self.addAction(edit_menu.flip_horz_action)
        self.addAction(edit_menu.flip_vert_action)
        self.addAction(edit_menu.rotate_left_action)
        self.addAction(edit_menu.rotate_right_action)
