# main_window\docking_windows\project_tree_dock.py
import copy
import json
import csv
from PySide6.QtWidgets import QDockWidget, QTreeWidgetItem, QMenu, QDialog, QMessageBox, QFileDialog
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence
from ..widgets.tree import CustomTreeWidget
from ..services.icon_service import IconService
from ..dialogs.project_tree.project_information_dialog import ProjectInformationDialog
from ..dialogs.project_tree.tag_dialog import TagDialog
from ..dialogs.project_tree.comment_dialog import CommentDialog
from ..dialogs.project_tree.alarm_dialog import AlarmDialog
from ..dialogs.project_tree.logging_dialog import LoggingDialog
from ..dialogs.project_tree.recipe_dialog import RecipeDialog
from ..dialogs.project_tree.script_dialog import ScriptDialog
from ..dialogs.project_tree.device_data_transfer_dialog import DeviceDataTransferDialog
from ..dialogs.project_tree.trigger_action_dialog import TriggerActionDialog
from ..dialogs.project_tree.time_action_dialog import TimeActionDialog
from ..dialogs.project_tree.image_dialog import ImageDialog
from ..dialogs.project_tree.animation_dialog import AnimationDialog
from project.comment.comment_table import CommentTable
from project.tag.tag_table import TagTable


class ProjectTreeDock(QDockWidget):
    """
    Dockable window to display the project file structure.
    """
    def __init__(self, main_window, comment_service):
        """
        Initializes the Project Tree dock widget.

        Args:
            main_window (QMainWindow): The main window instance.
            comment_service (CommentService): The service for managing comment data.
        """
        super().__init__("Project Tree", main_window)
        self.main_window = main_window
        self.comment_service = comment_service
        self.setObjectName("project_tree")
        self._clipboard = None

        self.tree_widget = CustomTreeWidget()
        self.setWidget(self.tree_widget)
        
        self._populate_tree()

        self.tree_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree_widget.customContextMenuRequested.connect(self.show_context_menu)
        self.tree_widget.itemDoubleClicked.connect(self.handle_double_click)

    def keyPressEvent(self, event):
        """Handle key press events for cut, copy, paste, and delete."""
        selected_items = self.tree_widget.selectedItems()
        if not selected_items:
            super().keyPressEvent(event)
            return

        item = selected_items[0]
        
        if event.matches(QKeySequence.StandardKey.Copy):
            self.copy_item(item)
            event.accept()
        elif event.matches(QKeySequence.StandardKey.Cut):
            self.cut_item(item)
            event.accept()
        elif event.matches(QKeySequence.StandardKey.Paste):
            self.paste_item(item)
            event.accept()
        elif event.key() == Qt.Key.Key_Delete:
             self.delete_item(item)
             event.accept()
        else:
            super().keyPressEvent(event)

    def _populate_tree(self):
        """
        Populates the tree with project items.
        """
        self.system_item = self._add_item("System", "dock-system-tree")
        self.screen_item = self._add_item("Screen", "dock-screen-tree")
        self.project_info_item = self._add_item("Project Information", "common-system-information")
        self.tag_item = self._add_item("Tag", "common-tags")
        self.comment_item = self._add_item("Comment", "common-comment")
        self.alarm_item = self._add_item("Alarm", "common-alarm")
        self.logging_item = self._add_item("Logging", "common-logging")
        self.recipe_item = self._add_item("Recipe", "object-recipe")
        self.script_item = self._add_item("Script", "common-script")
        self.device_data_transfer_item = self._add_item("Device Data Transfer", "common-tags-data-transfer")
        self.trigger_action_item = self._add_item("Trigger Action", "common-trigger-action")
        self.time_action_item = self._add_item("Time Action", "common-time-action")
        self.image_item = self._add_item("Image", "figure-image")
        self.animation_item = self._add_item("Animation", "object-animation")

    def _add_item(self, name, icon_name):
        item = QTreeWidgetItem(self.tree_widget, [name])
        item.setIcon(0, IconService.get_icon(icon_name))
        return item

    def clear_project_items(self):
        """Clears all dynamic items from the project tree (e.g., tags, comments)."""
        for i in range(self.comment_item.childCount() -1, -1, -1):
            self.comment_item.removeChild(self.comment_item.child(i))
        for i in range(self.tag_item.childCount() -1, -1, -1):
            self.tag_item.removeChild(self.tag_item.child(i))

    def load_project_data(self, project_data):
        """Loads data from the project into the tree view."""
        self.clear_project_items()
        
        # Load Comments
        comments_data = project_data.get('comments', {})
        for number_str, comment_obj in comments_data.items():
            metadata = comment_obj.get('metadata')
            if metadata:
                comment_text = f"{metadata['number']} - {metadata['name']}"
                new_item = QTreeWidgetItem(self.comment_item, [comment_text])
                new_item.setData(0, Qt.ItemDataRole.UserRole, metadata)
                new_item.setIcon(0, IconService.get_icon('common-comment'))
        
        # Load Tags
        tags_data = project_data.get('tag_lists', {})
        for number_str, tag_obj in tags_data.items():
             tag_text = f"{tag_obj['number']} - {tag_obj['name']}"
             new_item = QTreeWidgetItem(self.tag_item, [tag_text])
             new_item.setData(0, Qt.ItemDataRole.UserRole, tag_obj)
             new_item.setIcon(0, IconService.get_icon('common-tags'))
        
        self.comment_item.setExpanded(True)
        self.tag_item.setExpanded(True)

    def handle_double_click(self, item, column):
        """
        Handles double-click events on tree items.
        """
        if item == self.system_item:
            self.main_window.set_dock_widget_visibility("system_tree", True)
        elif item == self.screen_item:
            self.main_window.set_dock_widget_visibility("screen_tree", True)
        elif item == self.project_info_item:
            dialog = ProjectInformationDialog(self)
            dialog.exec()
        elif item.parent() == self.comment_item:
            self.open_comment(item)
        elif item.parent() == self.tag_item:
            self.open_tag(item)


    def show_context_menu(self, position):
        """
        Shows a context menu when an item is right-clicked.
        """
        item = self.tree_widget.itemAt(position)
        if not item:
            return

        menu = QMenu()
        parent = item.parent()

        if item == self.tag_item:
            action = menu.addAction("Add New Tag List")
            action.triggered.connect(self.add_new_tag)
            menu.addSeparator()
            paste_action = menu.addAction(IconService.get_icon('edit-paste'), "Paste")
            paste_action.setEnabled(self._clipboard is not None and self._clipboard.get('type') == 'tag')
            paste_action.triggered.connect(lambda: self.paste_item(item))
            import_action = menu.addAction(IconService.get_icon('common-import'), "Import")
            import_action.triggered.connect(self.import_tags)
        elif parent == self.tag_item:
            open_action = menu.addAction(IconService.get_icon('screen-open'), "Open")
            open_action.triggered.connect(lambda: self.open_tag(item))
            menu.addSeparator()
            cut_action = menu.addAction(IconService.get_icon('edit-cut'), "Cut")
            cut_action.triggered.connect(lambda: self.cut_item(item))
            copy_action = menu.addAction(IconService.get_icon('edit-copy'), "Copy")
            copy_action.triggered.connect(lambda: self.copy_item(item))
            paste_action = menu.addAction(IconService.get_icon('edit-paste'), "Paste")
            paste_action.setEnabled(self._clipboard is not None and self._clipboard.get('type') == 'tag')
            paste_action.triggered.connect(lambda: self.paste_item(item))
            menu.addSeparator()
            properties_action = menu.addAction(IconService.get_icon('screen-property'), "Properties")
            properties_action.triggered.connect(lambda: self.show_tag_properties(item))
            menu.addSeparator()
            delete_action = menu.addAction(IconService.get_icon('edit-delete'), "Delete")
            delete_action.triggered.connect(lambda: self.delete_item(item))
        elif item == self.comment_item:
            action = menu.addAction("Add New Comment")
            action.triggered.connect(self.add_new_comment)
            menu.addSeparator()
            paste_action = menu.addAction(IconService.get_icon('edit-paste'), "Paste")
            paste_action.setEnabled(self._clipboard is not None and self._clipboard.get('type') == 'comment')
            paste_action.triggered.connect(lambda: self.paste_item(item))
            import_action = menu.addAction(IconService.get_icon('common-import'), "Import")
            import_action.triggered.connect(self.import_comments)
        elif parent == self.comment_item:
            open_action = menu.addAction(IconService.get_icon('screen-open'), "Open")
            open_action.triggered.connect(lambda: self.open_comment(item))
            menu.addSeparator()
            cut_action = menu.addAction(IconService.get_icon('edit-cut'), "Cut")
            cut_action.triggered.connect(lambda: self.cut_item(item))
            copy_action = menu.addAction(IconService.get_icon('edit-copy'), "Copy")
            copy_action.triggered.connect(lambda: self.copy_item(item))
            paste_action = menu.addAction(IconService.get_icon('edit-paste'), "Paste")
            paste_action.setEnabled(self._clipboard is not None and self._clipboard.get('type') == 'comment')
            paste_action.triggered.connect(lambda: self.paste_item(item))
            menu.addSeparator()
            properties_action = menu.addAction(IconService.get_icon('screen-property'), "Properties")
            properties_action.triggered.connect(lambda: self.show_comment_properties(item))
            menu.addSeparator()
            delete_action = menu.addAction(IconService.get_icon('edit-delete'), "Delete")
            delete_action.triggered.connect(lambda: self.delete_item(item))
        elif item == self.alarm_item:
            action = menu.addAction("Add New Alarm List")
            action.triggered.connect(lambda: self.open_dialog(AlarmDialog))
        elif item == self.logging_item:
            action = menu.addAction("Add New Logging List")
            action.triggered.connect(lambda: self.open_dialog(LoggingDialog))
        elif item == self.recipe_item:
            action = menu.addAction("Add New Recipe List")
            action.triggered.connect(lambda: self.open_dialog(RecipeDialog))
        elif item == self.script_item:
            action = menu.addAction("Add New Script List")
            action.triggered.connect(lambda: self.open_dialog(ScriptDialog))
        elif item == self.device_data_transfer_item:
            action = menu.addAction("Add New Device Data Transfer List")
            action.triggered.connect(lambda: self.open_dialog(DeviceDataTransferDialog))
        elif item == self.trigger_action_item:
            action = menu.addAction("Add New Trigger Action List")
            action.triggered.connect(lambda: self.open_dialog(TriggerActionDialog))
        elif item == self.time_action_item:
            action = menu.addAction("Add New Time Action List")
            action.triggered.connect(lambda: self.open_dialog(TimeActionDialog))
        elif item == self.image_item:
            action = menu.addAction("Add New Image List")
            action.triggered.connect(lambda: self.open_dialog(ImageDialog))
        elif item == self.animation_item:
            action = menu.addAction("Add New Animation List")
            action.triggered.connect(lambda: self.open_dialog(AnimationDialog))

        if not menu.isEmpty():
            menu.exec(self.tree_widget.viewport().mapToGlobal(position))
            
    def get_existing_comment_numbers(self):
        numbers = []
        for i in range(self.comment_item.childCount()):
            child = self.comment_item.child(i)
            data = child.data(0, Qt.ItemDataRole.UserRole)
            if data and 'number' in data:
                numbers.append(data['number'])
        return numbers

    def add_new_comment(self):
        existing_numbers = self.get_existing_comment_numbers()
        dialog = CommentDialog(self, existing_comment_numbers=existing_numbers)
        if dialog.exec():
            comment_data = dialog.get_comment_data()
            if comment_data:
                # Add to service first
                self.comment_service.add_comment(comment_data)
                self.main_window.project_modified()

                # Add item to tree
                comment_text = f"{comment_data['number']} - {comment_data['name']}"
                new_item = QTreeWidgetItem(self.comment_item, [comment_text])
                new_item.setData(0, Qt.ItemDataRole.UserRole, comment_data)
                new_item.setIcon(0, IconService.get_icon('common-comment'))
                self.comment_item.setExpanded(True)
                
                # Open tab in main window
                self.main_window.open_comment_table(comment_data)

    def get_existing_tag_numbers(self):
        numbers = []
        for i in range(self.tag_item.childCount()):
            child = self.tag_item.child(i)
            data = child.data(0, Qt.ItemDataRole.UserRole)
            if data and 'number' in data:
                numbers.append(data['number'])
        return numbers

    def add_new_tag(self):
        existing_numbers = self.get_existing_tag_numbers()
        dialog = TagDialog(self, existing_tag_numbers=existing_numbers)
        if dialog.exec():
            tag_data = dialog.get_tag_data()
            if tag_data:
                # Save to Project Service
                if 'tag_lists' not in self.main_window.project_service.project_data:
                    self.main_window.project_service.project_data['tag_lists'] = {}
                
                self.main_window.project_service.project_data['tag_lists'][str(tag_data['number'])] = tag_data
                self.main_window.project_modified()
                
                # Add item to tree
                tag_text = f"{tag_data['number']} - {tag_data['name']}"
                new_item = QTreeWidgetItem(self.tag_item, [tag_text])
                new_item.setData(0, Qt.ItemDataRole.UserRole, tag_data)
                new_item.setIcon(0, IconService.get_icon('common-tags'))
                self.tag_item.setExpanded(True)
                
                # Open tab in main window
                self.main_window.open_tag_table(tag_data)
            
    def open_tag(self, item):
        # Fetch ID from the tree item (this part should be stable)
        item_data = item.data(0, Qt.ItemDataRole.UserRole)
        if not item_data: return
        
        tag_number = str(item_data.get('number'))
        
        # Fetch the LATEST data from ProjectService, not the potentially stale tree item data
        project_data = self.main_window.project_service.project_data
        if 'tag_lists' in project_data and tag_number in project_data['tag_lists']:
            fresh_data = project_data['tag_lists'][tag_number]
            self.main_window.open_tag_table(fresh_data)
        else:
            # Fallback in case of sync issue
            self.main_window.open_tag_table(item_data)

    def open_comment(self, item):
        comment_data = item.data(0, Qt.ItemDataRole.UserRole)
        if comment_data:
            self.main_window.open_comment_table(comment_data)

    def cut_item(self, item):
        self.copy_item(item)
        self.delete_item(item, confirm=False)

    def copy_item(self, item):
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return

        parent = item.parent()
        item_type = None
        if parent == self.tag_item:
            item_type = 'tag'
        elif parent == self.comment_item:
            item_type = 'comment'

        if item_type:
            self._clipboard = copy.deepcopy(data)
            self._clipboard['type'] = item_type
            # For comments, also copy the table data
            if item_type == 'comment':
                comment_number = data.get('number')
                if comment_number is not None:
                    table_data = self.comment_service.get_table_data(comment_number)
                    self._clipboard['table_data'] = copy.deepcopy(table_data)

    def paste_item(self, item):
        if not self._clipboard:
            return

        clipboard_type = self._clipboard.get('type')
        pasted_data = copy.deepcopy(self._clipboard)
        del pasted_data['type']

        if clipboard_type == 'tag':
            existing_numbers = self.get_existing_tag_numbers()
            new_number = pasted_data['number']
            while new_number in existing_numbers:
                new_number += 1
            pasted_data['number'] = new_number
            pasted_data['name'] += " (copy)"
            
            # Save to Project Service
            if 'tag_lists' not in self.main_window.project_service.project_data:
                 self.main_window.project_service.project_data['tag_lists'] = {}
            self.main_window.project_service.project_data['tag_lists'][str(new_number)] = pasted_data
            self.main_window.project_modified()

            tag_text = f"{pasted_data['number']} - {pasted_data['name']}"
            new_item = QTreeWidgetItem(self.tag_item, [tag_text])
            new_item.setData(0, Qt.ItemDataRole.UserRole, pasted_data)
            new_item.setIcon(0, IconService.get_icon('common-tags'))
            self.tag_item.setExpanded(True)

        elif clipboard_type == 'comment':
            existing_numbers = self.get_existing_comment_numbers()
            new_number = pasted_data['number']
            while new_number in existing_numbers:
                new_number += 1
            pasted_data['number'] = new_number
            pasted_data['name'] += " (copy)"

            # Add the comment with metadata first
            self.comment_service.add_comment(pasted_data)
            # If table_data was copied, update it for the new comment
            if 'table_data' in self._clipboard:
                self.comment_service.update_table_data(new_number, self._clipboard['table_data'])
            self.main_window.project_modified()

            comment_text = f"{pasted_data['number']} - {pasted_data['name']}"
            new_item = QTreeWidgetItem(self.comment_item, [comment_text])
            new_item.setData(0, Qt.ItemDataRole.UserRole, pasted_data)
            new_item.setIcon(0, IconService.get_icon('common-comment'))
            self.comment_item.setExpanded(True)

    def show_tag_properties(self, item):
        tag_data = item.data(0, Qt.ItemDataRole.UserRole)
        if not tag_data:
            return

        existing_numbers = self.get_existing_tag_numbers()
        current_number = tag_data.get("number")
        editable_numbers = [num for num in existing_numbers if num != current_number]
        
        dialog = TagDialog(self, existing_tag_numbers=editable_numbers, initial_data=tag_data)

        if dialog.exec():
            updated_data = dialog.get_tag_data()
            # Preserve existing tags rows
            updated_data['tags'] = tag_data.get('tags', [])
            updated_data['number'] = current_number # Keep original number
            
            # Update Service
            self.main_window.project_service.project_data['tag_lists'][str(current_number)] = updated_data
            self.main_window.project_modified()

            item.setData(0, Qt.ItemDataRole.UserRole, updated_data)
            item.setText(0, f"{updated_data['number']} - {updated_data['name']}")
            
            self.main_window.close_tag_tab_by_number(current_number)
            self.main_window.open_tag_table(updated_data)

    def show_comment_properties(self, item):
        comment_data = item.data(0, Qt.ItemDataRole.UserRole)
        if not comment_data:
            return

        existing_numbers = self.get_existing_comment_numbers()
        current_number = comment_data.get("number")
        editable_numbers = [num for num in existing_numbers if num != current_number]
        
        dialog = CommentDialog(self, existing_comment_numbers=editable_numbers, initial_data=comment_data)

        if dialog.exec():
            updated_data = dialog.get_comment_data()
            updated_data['number'] = current_number # Keep original number
            item.setData(0, Qt.ItemDataRole.UserRole, updated_data)
            item.setText(0, f"{updated_data['number']} - {updated_data['name']}")
            
            self.comment_service.update_comment_metadata(updated_data)
            self.main_window.project_modified()
            
            self.main_window.close_comment_tab_by_number(current_number)
            self.main_window.open_comment_table(updated_data)

    def delete_item(self, item, confirm=True):
        if not item or not item.parent():
            return

        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return

        reply = QMessageBox.StandardButton.Yes
        if confirm:
            reply = QMessageBox.question(self, "Delete Item", 
                                         f"Are you sure you want to delete '{data.get('name')}'?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            item_number = data.get('number')
            parent = item.parent()

            parent.removeChild(item)
            
            if parent == self.tag_item:
                self.main_window.close_tag_tab_by_number(item_number)
                # Remove from Project Service
                if 'tag_lists' in self.main_window.project_service.project_data:
                     if str(item_number) in self.main_window.project_service.project_data['tag_lists']:
                         del self.main_window.project_service.project_data['tag_lists'][str(item_number)]
                         self.main_window.project_modified()

            elif parent == self.comment_item:
                self.main_window.close_comment_tab_by_number(item_number)
                self.comment_service.remove_comment(item_number)
                self.main_window.project_modified()
            
    def open_dialog(self, dialog_class):
        dialog = dialog_class(self)
        dialog.exec()

    def paste_tag(self):
        # Placeholder for future implementation
        print("Paste Tag action triggered.")

    def import_tags(self):
        """Import tags from a JSON or CSV file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Import Tags", "", 
            "Tag Files (*.json *.csv);;JSON Files (*.json);;CSV Files (*.csv);;All Files (*)"
        )
        if not file_path:
            return
        
        try:
            if file_path.endswith('.json'):
                with open(file_path, 'r', encoding='utf-8') as f:
                    imported_data = json.load(f)
                    if isinstance(imported_data, list):
                        tags_list = imported_data
                    elif isinstance(imported_data, dict) and 'tags' in imported_data:
                        tags_list = imported_data['tags']
                    else:
                        tags_list = [imported_data]
            elif file_path.endswith('.csv'):
                tags_list = []
                with open(file_path, 'r', encoding='utf-8', newline='') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        # Convert number to int if present
                        if 'number' in row:
                            row['number'] = int(row['number'])
                        tags_list.append(row)
            else:
                QMessageBox.warning(self, "Import Error", "Unsupported file format.")
                return
            
            existing_numbers = self.get_existing_tag_numbers()
            imported_count = 0
            
            for tag_data in tags_list:
                # Skip if number already exists, or assign new number
                if 'number' not in tag_data or tag_data['number'] in existing_numbers:
                    tag_data['number'] = max(existing_numbers + [0]) + 1
                
                existing_numbers.append(tag_data['number'])
                
                # Ensure required fields
                if 'name' not in tag_data:
                    tag_data['name'] = f"Tag_{tag_data['number']}"
                
                # Save to Project Service
                if 'tag_lists' not in self.main_window.project_service.project_data:
                    self.main_window.project_service.project_data['tag_lists'] = {}
                
                self.main_window.project_service.project_data['tag_lists'][str(tag_data['number'])] = tag_data
                
                # Add item to tree
                tag_text = f"{tag_data['number']} - {tag_data['name']}"
                new_item = QTreeWidgetItem(self.tag_item, [tag_text])
                new_item.setData(0, Qt.ItemDataRole.UserRole, tag_data)
                new_item.setIcon(0, IconService.get_icon('common-tags'))
                imported_count += 1
            
            self.tag_item.setExpanded(True)
            self.main_window.project_modified()
            QMessageBox.information(self, "Import Complete", f"Successfully imported {imported_count} tag(s).")
            
        except Exception as e:
            QMessageBox.warning(self, "Import Error", f"Failed to import tags: {str(e)}")

    def export_tags(self):
        """Export tags to a JSON or CSV file."""
        file_path, selected_filter = QFileDialog.getSaveFileName(
            self, "Export Tags", "", 
            "JSON Files (*.json);;CSV Files (*.csv);;All Files (*)"
        )
        if not file_path:
            return
        
        try:
            # Collect all tags
            tags_list = []
            for i in range(self.tag_item.childCount()):
                child = self.tag_item.child(i)
                tag_data = child.data(0, Qt.ItemDataRole.UserRole)
                if tag_data:
                    tags_list.append(tag_data)
            
            if not tags_list:
                QMessageBox.warning(self, "Export Error", "No tags to export.")
                return
            
            if file_path.endswith('.csv') or 'CSV' in selected_filter:
                if not file_path.endswith('.csv'):
                    file_path += '.csv'
                # Get all unique keys for CSV header
                all_keys = set()
                for tag in tags_list:
                    all_keys.update(tag.keys())
                all_keys = sorted(list(all_keys))
                
                with open(file_path, 'w', encoding='utf-8', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=all_keys)
                    writer.writeheader()
                    writer.writerows(tags_list)
            else:
                if not file_path.endswith('.json'):
                    file_path += '.json'
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump({'tags': tags_list}, f, indent=2, ensure_ascii=False)
            
            QMessageBox.information(self, "Export Complete", f"Successfully exported {len(tags_list)} tag(s).")
            
        except Exception as e:
            QMessageBox.warning(self, "Export Error", f"Failed to export tags: {str(e)}")

    def paste_comment(self):
        # Placeholder for future implementation
        print("Paste Comment action triggered.")

    def import_comments(self):
        """Import comments from a JSON file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Import Comments", "", 
            "JSON Files (*.json);;All Files (*)"
        )
        if not file_path:
            return
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                imported_data = json.load(f)
                if isinstance(imported_data, list):
                    comments_list = imported_data
                elif isinstance(imported_data, dict) and 'comments' in imported_data:
                    comments_list = imported_data['comments']
                else:
                    comments_list = [imported_data]
            
            existing_numbers = self.get_existing_comment_numbers()
            imported_count = 0
            
            for comment_data in comments_list:
                # Skip if number already exists, or assign new number
                if 'number' not in comment_data or comment_data['number'] in existing_numbers:
                    comment_data['number'] = max(existing_numbers + [0]) + 1
                
                existing_numbers.append(comment_data['number'])
                
                # Ensure required fields
                if 'name' not in comment_data:
                    comment_data['name'] = f"Comment_{comment_data['number']}"
                
                # Add to comment service
                self.comment_service.add_comment(comment_data)
                
                # If table_data was included, update it
                if 'table_data' in comment_data:
                    self.comment_service.update_table_data(comment_data['number'], comment_data['table_data'])
                
                # Add item to tree
                comment_text = f"{comment_data['number']} - {comment_data['name']}"
                new_item = QTreeWidgetItem(self.comment_item, [comment_text])
                new_item.setData(0, Qt.ItemDataRole.UserRole, comment_data)
                new_item.setIcon(0, IconService.get_icon('common-comment'))
                imported_count += 1
            
            self.comment_item.setExpanded(True)
            self.main_window.project_modified()
            QMessageBox.information(self, "Import Complete", f"Successfully imported {imported_count} comment(s).")
            
        except Exception as e:
            QMessageBox.warning(self, "Import Error", f"Failed to import comments: {str(e)}")

    def export_comments(self):
        """Export comments to a JSON file."""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Comments", "", 
            "JSON Files (*.json);;All Files (*)"
        )
        if not file_path:
            return
        
        try:
            # Collect all comments with their table data
            comments_list = []
            for i in range(self.comment_item.childCount()):
                child = self.comment_item.child(i)
                comment_data = child.data(0, Qt.ItemDataRole.UserRole)
                if comment_data:
                    export_data = copy.deepcopy(comment_data)
                    # Include table data from service
                    table_data = self.comment_service.get_table_data(comment_data.get('number'))
                    if table_data:
                        export_data['table_data'] = table_data
                    comments_list.append(export_data)
            
            if not comments_list:
                QMessageBox.warning(self, "Export Error", "No comments to export.")
                return
            
            if not file_path.endswith('.json'):
                file_path += '.json'
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump({'comments': comments_list}, f, indent=2, ensure_ascii=False)
            
            QMessageBox.information(self, "Export Complete", f"Successfully exported {len(comments_list)} comment(s).")
            
        except Exception as e:
            QMessageBox.warning(self, "Export Error", f"Failed to export comments: {str(e)}")