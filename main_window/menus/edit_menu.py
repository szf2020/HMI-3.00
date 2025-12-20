# main_window\menus\edit_menu.py
from PySide6.QtGui import QAction
from ..services.icon_service import IconService

class EditMenu:
    """
    Creates the 'Edit' menu and its actions.
    """
    def __init__(self, main_window, menu_bar):
        self.main_window = main_window
        edit_menu = menu_bar.addMenu("&Edit")

        # Icons
        undo_icon = IconService.get_icon('edit-undo')
        redo_icon = IconService.get_icon('edit-redo')
        cut_icon = IconService.get_icon('edit-cut')
        copy_icon = IconService.get_icon('edit-copy')
        paste_icon = IconService.get_icon('edit-paste')
        duplicate_icon = IconService.get_icon('edit-duplicate')
        delete_icon = IconService.get_icon('edit-delete')
        consecutive_copy_icon = IconService.get_icon('edit-consecutive-copy')
        select_all_icon = IconService.get_icon('edit-select-all')
        
        # Actions
        self.undo_action = QAction(undo_icon,"Undo", self.main_window)
        self.redo_action = QAction(redo_icon,"Redo", self.main_window)
        self.cut_action = QAction(cut_icon,"Cut", self.main_window)
        self.copy_action = QAction(copy_icon,"Copy", self.main_window)
        self.paste_action = QAction(paste_icon,"Paste", self.main_window)
        self.duplicate_action = QAction(duplicate_icon,"Duplicate", self.main_window)
        self.consecutive_copy_action = QAction(consecutive_copy_icon, "Consecutive Copy", self.main_window)
        self.select_all_action = QAction(select_all_icon, "Select All", self.main_window)
        self.delete_action = QAction(delete_icon,"Delete", self.main_window)
        
        self.undo_action.setShortcut("Ctrl+Z")
        self.redo_action.setShortcut("Ctrl+Y")
        self.cut_action.setShortcut("Ctrl+X")
        self.copy_action.setShortcut("Ctrl+C")
        self.paste_action.setShortcut("Ctrl+V")
        self.duplicate_action.setShortcut("Ctrl+D")
        self.consecutive_copy_action.setShortcut("Ctrl+Shift+C")
        self.select_all_action.setShortcut("Ctrl+A")
        self.delete_action.setShortcut("Del")

        # Add actions to the Edit menu
        edit_menu.addAction(self.cut_action)
        edit_menu.addAction(self.copy_action)
        edit_menu.addAction(self.paste_action)
        edit_menu.addSeparator()
        edit_menu.addAction(self.undo_action)
        edit_menu.addAction(self.redo_action)
        edit_menu.addSeparator()
        edit_menu.addAction(self.duplicate_action)
        edit_menu.addAction(self.consecutive_copy_action)
        edit_menu.addSeparator()
        edit_menu.addAction(self.select_all_action)
        edit_menu.addAction(self.delete_action)
        edit_menu.addSeparator()

        # Stacking Order Submenu
        stacking_order_icon = IconService.get_icon('stacking-order')
        stacking_order_menu = edit_menu.addMenu(stacking_order_icon, "Stacking Order")
        move_front_layer_icon = IconService.get_icon('move-front-layer')
        move_back_layer_icon = IconService.get_icon('move-back-layer')
        move_to_front_icon = IconService.get_icon('move-to-front')
        move_to_back_icon = IconService.get_icon('move-to-back')
        self.move_front_layer_action = QAction(move_front_layer_icon, "Move Front Layer", self.main_window)
        stacking_order_menu.addAction(self.move_front_layer_action)
        self.move_back_layer_action = QAction(move_back_layer_icon, "Move Back Layer", self.main_window)
        stacking_order_menu.addAction(self.move_back_layer_action)
        self.move_to_front_action = QAction(move_to_front_icon, "Move to Front", self.main_window)
        stacking_order_menu.addAction(self.move_to_front_action)
        self.move_to_back_action = QAction(move_to_back_icon, "Move to Back", self.main_window)
        stacking_order_menu.addAction(self.move_to_back_action)

        # Align Submenu
        align_icon = IconService.get_icon('align-center')
        align_menu = edit_menu.addMenu(align_icon, "Align")
        align_left_icon = IconService.get_icon('align-left')
        align_center_icon = IconService.get_icon('align-horizontal-center')
        align_right_icon = IconService.get_icon('align-right')
        align_top_icon = IconService.get_icon('align-top')
        align_middle_icon = IconService.get_icon('align-middle')
        align_bottom_icon = IconService.get_icon('align-bottom')
        dist_horz_icon = IconService.get_icon('distribute-horizontal')
        dist_vert_icon = IconService.get_icon('distribute-vertical')
        self.align_left_action = QAction(align_left_icon, "Left", self.main_window)
        align_menu.addAction(self.align_left_action)
        self.align_center_action = QAction(align_center_icon, "Center", self.main_window)
        align_menu.addAction(self.align_center_action)
        self.align_right_action = QAction(align_right_icon, "Right", self.main_window)
        align_menu.addAction(self.align_right_action)
        align_menu.addSeparator()
        self.align_top_action = QAction(align_top_icon, "Top", self.main_window)
        align_menu.addAction(self.align_top_action)
        self.align_middle_action = QAction(align_middle_icon, "Middle", self.main_window)
        align_menu.addAction(self.align_middle_action)
        self.align_bottom_action = QAction(align_bottom_icon, "Bottom", self.main_window)
        align_menu.addAction(self.align_bottom_action)
        align_menu.addSeparator()
        self.dist_horz_action = QAction(dist_horz_icon, "Distribute Horizontal", self.main_window)
        align_menu.addAction(self.dist_horz_action)
        self.dist_vert_action = QAction(dist_vert_icon, "Distribute Vertical", self.main_window)
        align_menu.addAction(self.dist_vert_action)

        # Wrap Action
        wrap_icon = IconService.get_icon('wrap')
        self.wrap_action = QAction(wrap_icon, "Wrap", self.main_window)
        edit_menu.addAction(self.wrap_action)
        
        # Flip Submenu
        flip_icon = IconService.get_icon('flip')
        flip_menu = edit_menu.addMenu(flip_icon, "Flip")
        flip_vert_icon = IconService.get_icon('flip-vertical')
        flip_horz_icon = IconService.get_icon('flip-horizontal')
        rotate_left_icon = IconService.get_icon('rotate-left')
        rotate_right_icon = IconService.get_icon('rotate-right')
        self.flip_vert_action = QAction(flip_vert_icon, "Vertical", self.main_window)
        flip_menu.addAction(self.flip_vert_action)
        self.flip_horz_action = QAction(flip_horz_icon, "Horizontal", self.main_window)
        flip_menu.addAction(self.flip_horz_action)
        self.rotate_left_action = QAction(rotate_left_icon, "Left", self.main_window)
        flip_menu.addAction(self.rotate_left_action)
        self.rotate_right_action = QAction(rotate_right_icon, "Right", self.main_window)
        flip_menu.addAction(self.rotate_right_action)