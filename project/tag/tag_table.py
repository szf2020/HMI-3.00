# project\tag\tag_table.py
import re
import copy
import json
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem, QHeaderView,
    QToolBar, QComboBox, QMessageBox, QStyledItemDelegate, QCheckBox,
    QAbstractItemView, QLineEdit, QApplication, QSizePolicy,
    QDateEdit, QTimeEdit, QDateTimeEdit, QTreeWidgetItemIterator, QProgressDialog,
    QMenu
)
from PySide6.QtCore import Qt, QMimeData, QDate, QTime, QDateTime
from PySide6.QtGui import QAction, QUndoStack, QUndoCommand, QKeySequence, QColor, QBrush
from main_window.services.icon_service import IconService
from main_window.widgets.tree import CustomTreeWidget

# Import optimization utilities
try:
    from .optimized_tag_operations import OptimizedTagDeletion, OptimizedTagAddition
except ImportError:
    OptimizedTagDeletion = None
    OptimizedTagAddition = None

# Define validation ranges for data types
DATA_TYPE_RANGES = {
    "Bit": (0, 1),
    "Sign Int8": (-128, 127),
    "Sign Int16": (-32768, 32767),
    "Sign Int32": (-2147483648, 2147483647),
    "Unsign Int8": (0, 255),
    "Unsign Int16": (0, 65535),
    "Unsign Int32": (0, 4294967295),
}

# --- Undo Commands ---

class TagChangeCommand(QUndoCommand):
    """Command for changing a single cell's value."""
    def __init__(self, table, row, col, old_val, new_val, child_key=None, text="Edit Tag"):
        super().__init__(text)
        self.table = table
        self.row = row
        self.col = col
        self.old_val = old_val
        self.new_val = new_val
        self.child_key = child_key

    def redo(self):
        self.table.block_signals(True)
        self.table._set_cell_value(self.row, self.col, self.new_val, self.child_key)
        self.table.block_signals(False)
        self.table.save_data()

    def undo(self):
        self.table.block_signals(True)
        self.table._set_cell_value(self.row, self.col, self.old_val, self.child_key)
        self.table.block_signals(False)
        self.table.save_data()

class TagAddCommand(QUndoCommand):
    """Command for adding a new tag."""
    def __init__(self, table, row_index, tag_data, text="Add Tag"):
        super().__init__(text)
        self.table = table
        self.row_index = row_index
        self.tag_data = tag_data

    def redo(self):
        self.table.block_signals(True)
        self.table._insert_tag_item(self.row_index, self.tag_data)
        self.table.block_signals(False)
        self.table.save_data()

    def undo(self):
        self.table.block_signals(True)
        self.table.table.takeTopLevelItem(self.row_index)
        self.table.block_signals(False)
        self.table.save_data()

class TagRemoveCommand(QUndoCommand):
    """Command for removing tags with optimized batch processing for large deletions."""
    def __init__(self, table, rows_data, text="Remove Tag"):
        super().__init__(text)
        self.table = table
        # rows_data is a list of tuples: (row_index, tag_data_dict)
        # Sort by row index descending to handle removals correctly
        self.rows_data = sorted(rows_data, key=lambda x: x[0], reverse=True)
        self.is_batch = len(rows_data) > 10  # Flag for batch operations

    def redo(self):
        self.table.block_signals(True)
        
        # Use optimized batch deletion if available and needed
        if self.is_batch and OptimizedTagDeletion:
            try:
                rows_to_delete = [row for row, _ in self.rows_data]
                OptimizedTagDeletion.delete_multiple_tags_optimized(
                    self.table, rows_to_delete, parent_widget=self.table
                )
            except Exception:
                # Fallback to standard deletion if optimization fails
                for row, _ in self.rows_data:
                    self.table.table.takeTopLevelItem(row)
        else:
            # Standard deletion for small operations
            for row, _ in self.rows_data:
                self.table.table.takeTopLevelItem(row)
        
        self.table.block_signals(False)
        self.table.save_data()

    def undo(self):
        self.table.block_signals(True)
        
        # Re-insert in reverse order of removal (ascending index)
        if self.is_batch:
            # Batch re-insertion with deferred updates
            for row, data in reversed(self.rows_data):
                self.table._insert_tag_item(row, data)
        else:
            # Standard re-insertion for small operations
            for row, data in reversed(self.rows_data):
                self.table._insert_tag_item(row, data)
        
        self.table.block_signals(False)
        self.table.save_data()

class TagCutCommand(QUndoCommand):
    """Command for cutting (removing) tags."""
    def __init__(self, table, rows_data, text="Cut Tags"):
        super().__init__(text)
        self.table = table
        self.rows_data = sorted(rows_data, key=lambda x: x[0], reverse=True)

    def redo(self):
        self.table.block_signals(True)
        for row, _ in self.rows_data:
            self.table.table.takeTopLevelItem(row)
        self.table.block_signals(False)
        self.table.save_data()

    def undo(self):
        self.table.block_signals(True)
        for row, data in reversed(self.rows_data):
            self.table._insert_tag_item(row, data)
        self.table.block_signals(False)
        self.table.save_data()

class TagPasteCommand(QUndoCommand):
    """Command for pasting tags."""
    def __init__(self, table, row_index, tags_data, text="Paste Tags"):
        super().__init__(text)
        self.table = table
        self.row_index = row_index
        self.tags_data = tags_data

    def redo(self):
        self.table.block_signals(True)
        for idx, tag_data in enumerate(self.tags_data):
            self.table._insert_tag_item(self.row_index + idx, tag_data)
        self.table.block_signals(False)
        self.table.save_data()

    def undo(self):
        self.table.block_signals(True)
        for i in range(len(self.tags_data)):
            self.table.table.takeTopLevelItem(self.row_index)
        self.table.block_signals(False)
        self.table.save_data()


# --- Delegates ---

class ArrayElementsDelegate(QStyledItemDelegate):
    """Delegate to validate Array Elements input format (e.g., 10, 10x10, 10x10x10)."""
    def __init__(self, tag_table, parent=None):
        super().__init__(parent)
        self.tag_table = tag_table

    def createEditor(self, parent, option, index):
        # Disable editing for child items
        if index.parent().isValid():
            return None
        editor = QLineEdit(parent)
        return editor

    def setEditorData(self, editor, index):
        editor.setText(str(index.model().data(index, Qt.ItemDataRole.EditRole)))

    def setModelData(self, editor, model, index):
        text = editor.text().strip().lower()
        old_val = str(index.model().data(index, Qt.ItemDataRole.EditRole))
        
        # Regex to match N, NxM, or NxMxK where N,M,K are positive integers
        if not re.match(r'^[1-9]\d*(?:x[1-9]\d*){0,2}$', text):
             QMessageBox.warning(self.tag_table, "Invalid Format", 
                                 "Invalid array format.\n"
                                 "Accepted formats:\n"
                                 "- 1D: '10'\n"
                                 "- 2D: '10x10'\n"
                                 "- 3D: '10x10x10'")
             return

        if text != old_val:
            item = self.tag_table.table.itemFromIndex(index)
            if not item or item.parent(): 
                return

            root = self.tag_table.table.invisibleRootItem()
            top_level_index = root.indexOfChild(item)
            
            command = TagChangeCommand(self.tag_table, top_level_index, index.column(), old_val, text, text="Edit Array Elements")
            self.tag_table.undo_stack.push(command)

class DataTypeDelegate(QStyledItemDelegate):
    def __init__(self, tag_table, parent=None):
        super().__init__(parent)
        self.tag_table = tag_table
        self.data_types = [
            "Bit", "Sign Int8", "Sign Int16", "Sign Int32",
            "Unsign Int8", "Unsign Int16", "Unsign Int32",
            "Real", "Time", "Date", "Date Time",
            "String", "Timer", "Counter"
        ]

    def createEditor(self, parent, option, index):
        # Disable editing for child items - they inherit type
        if index.parent().isValid():
            return None
        editor = QComboBox(parent)
        editor.addItems(self.data_types)
        return editor

    def setEditorData(self, editor, index):
        value = index.model().data(index, Qt.ItemDataRole.EditRole)
        if value in self.data_types:
            editor.setCurrentText(value)
        editor.showPopup()

    def setModelData(self, editor, model, index):
        new_val = editor.currentText()
        old_val = index.model().data(index, Qt.ItemDataRole.EditRole)
        
        if new_val != old_val:
            item = self.tag_table.table.itemFromIndex(index)
            if not item or item.parent(): return
            root = self.tag_table.table.invisibleRootItem()
            row = root.indexOfChild(item)

            # Determine the default initial value based on the new datatype
            default_init_val = TagTable._get_default_value_for_type(new_val)

            self.tag_table.undo_stack.beginMacro("Change Data Type")
            cmd_type = TagChangeCommand(self.tag_table, row, index.column(), old_val, new_val, text="Change Data Type")
            self.tag_table.undo_stack.push(cmd_type)

            # Reset Initial Value to appropriate default based on datatype
            init_val_col = 2
            old_init_val = item.text(init_val_col)
            cmd_reset = TagChangeCommand(self.tag_table, row, init_val_col, old_init_val, default_init_val, text="Reset Initial Value")
            self.tag_table.undo_stack.push(cmd_reset)

            self.tag_table.undo_stack.endMacro()
    
    def _get_default_value_for_type(self, data_type):
        """Returns the default initial value based on the datatype."""
        return TagTable._get_default_value_for_type(data_type)

class TagNameDelegate(QStyledItemDelegate):
    def __init__(self, tag_table, parent=None):
        super().__init__(parent)
        self.tag_table = tag_table

    def createEditor(self, parent, option, index):
        # Disable editing for child items
        if index.parent().isValid():
            return None
        return QLineEdit(parent)

    def setEditorData(self, editor, index):
        editor.setText(index.model().data(index, Qt.ItemDataRole.EditRole))

    def setModelData(self, editor, model, index):
        new_name = editor.text().strip()
        old_name = index.model().data(index, Qt.ItemDataRole.EditRole)
        
        if new_name == old_name: return

        item = self.tag_table.table.itemFromIndex(index)
        if not item or item.parent(): return
        root = self.tag_table.table.invisibleRootItem()
        row = root.indexOfChild(item)

        # Check duplicates
        for i in range(root.childCount()):
            if i == row: continue
            other_item = root.child(i)
            if other_item.text(0).lower() == new_name.lower():
                QMessageBox.warning(self.tag_table, "Duplicate Name", f"The tag name '{new_name}' already exists.")
                return 

        command = TagChangeCommand(self.tag_table, row, index.column(), old_name, new_name, text="Rename Tag")
        self.tag_table.undo_stack.push(command)

class InitialValueDelegate(QStyledItemDelegate):
    def __init__(self, tag_table, parent=None):
        super().__init__(parent)
        self.tag_table = tag_table

    def createEditor(self, parent, option, index):
        item = self.tag_table.table.itemFromIndex(index)
        # Inherit type from parent if it's a child item
        type_item = item
        while type_item.parent():
            type_item = type_item.parent()
        
        data_type = type_item.text(1)

        # For the main tag item of an array OR any intermediate parent (like Tag[0]), disable direct editing
        # It should only be editable via child leaf updates
        if item.childCount() > 0:
             return None

        if data_type == "Date":
            editor = QDateEdit(parent)
            editor.setDisplayFormat("dd-MM-yyyy")
            editor.setCalendarPopup(True)
            return editor
        elif data_type == "Time":
            editor = QTimeEdit(parent)
            editor.setDisplayFormat("HH:mm:ss")
            return editor
        elif data_type == "Date Time":
            editor = QDateTimeEdit(parent)
            editor.setDisplayFormat("dd-MM-yyyy HH:mm:ss")
            editor.setCalendarPopup(True)
            return editor

        return QLineEdit(parent)

    def setEditorData(self, editor, index):
        value_str = str(index.model().data(index, Qt.ItemDataRole.EditRole))
        if isinstance(editor, QDateEdit):
            qdate = QDate.fromString(value_str, "dd-MM-yyyy")
            editor.setDate(qdate if qdate.isValid() else QDate.currentDate())
        elif isinstance(editor, QTimeEdit):
            qtime = QTime.fromString(value_str, "HH:mm:ss")
            editor.setTime(qtime if qtime.isValid() else QTime.currentTime())
        elif isinstance(editor, QDateTimeEdit):
            qdt = QDateTime.fromString(value_str, "dd-MM-yyyy HH:mm:ss")
            editor.setDateTime(qdt if qdt.isValid() else QDateTime.currentDateTime())
        elif isinstance(editor, QLineEdit):
            editor.setText(value_str)

    def setModelData(self, editor, model, index):
        old_val_str = str(index.model().data(index, Qt.ItemDataRole.EditRole))
        new_val_str = ""

        if isinstance(editor, QDateEdit): new_val_str = editor.date().toString("dd-MM-yyyy")
        elif isinstance(editor, QTimeEdit): new_val_str = editor.time().toString("HH:mm:ss")
        elif isinstance(editor, QDateTimeEdit): new_val_str = editor.dateTime().toString("dd-MM-yyyy HH:mm:ss")
        elif isinstance(editor, QLineEdit):
            new_val_str = editor.text().strip()
            
            # --- VALIDATION START ---
            # Retrieve the data type for the current row (or its parent)
            item = self.tag_table.table.itemFromIndex(index)
            type_item = item
            while type_item.parent():
                type_item = type_item.parent()
            data_type = type_item.text(1)  # Data Type is in column 1

            if data_type in DATA_TYPE_RANGES:
                min_val, max_val = DATA_TYPE_RANGES[data_type]
                try:
                    val = int(new_val_str)
                    if not (min_val <= val <= max_val):
                        QMessageBox.warning(self.tag_table, "Invalid Value", f"Value must be between {min_val} and {max_val} for {data_type}.")
                        return # Reject change
                except ValueError:
                    QMessageBox.warning(self.tag_table, "Invalid Value", f"Invalid integer format for {data_type}.")
                    return # Reject change
            elif data_type == "Real":
                try:
                    float(new_val_str)
                except ValueError:
                    QMessageBox.warning(self.tag_table, "Invalid Value", "Invalid format for Real (float).")
                    return # Reject change
            # --- VALIDATION END ---

        if new_val_str != old_val_str:
            item = self.tag_table.table.itemFromIndex(index)
            # Find top level index
            top_item = item
            while top_item.parent(): top_item = top_item.parent()
            root = self.tag_table.table.invisibleRootItem()
            row = root.indexOfChild(top_item)
            
            # Determine if we are editing a child
            child_key = None
            if item.parent():
                child_key = item.data(0, Qt.ItemDataRole.UserRole) # Use stored index path as key

            command = TagChangeCommand(self.tag_table, row, index.column(), old_val_str, new_val_str, child_key, text="Edit Initial Value")
            self.tag_table.undo_stack.push(command)

class GenericDelegate(QStyledItemDelegate):
    def __init__(self, tag_table, parent=None):
        super().__init__(parent)
        self.tag_table = tag_table
        
    def createEditor(self, parent, option, index):
        return QLineEdit(parent)

    def setEditorData(self, editor, index):
        editor.setText(str(index.model().data(index, Qt.ItemDataRole.EditRole)))

    def setModelData(self, editor, model, index):
        new_val = editor.text()
        old_val = str(index.model().data(index, Qt.ItemDataRole.EditRole))
        
        if new_val != old_val:
            item = self.tag_table.table.itemFromIndex(index)
            
            top_item = item
            while top_item.parent(): top_item = top_item.parent()
            root = self.tag_table.table.invisibleRootItem()
            row = root.indexOfChild(top_item)
            
            child_key = None
            if item.parent():
                child_key = item.data(0, Qt.ItemDataRole.UserRole)

            command = TagChangeCommand(self.tag_table, row, index.column(), old_val, new_val, child_key, text="Edit Cell")
            self.tag_table.undo_stack.push(command)

# --- Custom Tree Widget ---

class TagTreeWidget(CustomTreeWidget):
    """A QTreeWidget customized for the tag table."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderHidden(False)
        self.tag_table = None  # Will be set by TagTable
        
        # Apply tag-specific stylesheet that includes header styling
        self._apply_tag_stylesheet()
    
    def _apply_tag_stylesheet(self):
        """Apply stylesheet specific to tag table with branch icons and header styling."""
        # Tag table uses the default stylesheet from CustomTreeWidget parent class
        # No additional styling needed - inherits from _apply_default_stylesheet
        pass
        
    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        index = self.indexAt(event.position().toPoint())
        if index.isValid():
            # Edit on single click if it's the Data Type column
            # Only if it's a top-level item (parent is invalid)
            if index.column() == 1 and not index.parent().isValid():
                self.edit(index)

    def contextMenuEvent(self, event):
        """Show context menu on right-click."""
        if self.tag_table:
            self.tag_table.show_context_menu(event.globalPos())
        else:
            super().contextMenuEvent(event)

# --- Main Widget ---

class TagTable(QWidget):
    def __init__(self, tag_data, main_window, parent=None):
        super().__init__(parent)
        self.tag_data = tag_data
        self.main_window = main_window
        self.undo_stack = QUndoStack(self)
        self.undo_stack.setUndoLimit(100)  # Limit to 100 operations to prevent unbounded growth
        
        if 'tags' not in self.tag_data:
            self.tag_data['tags'] = []

        self.setup_ui()
        self.load_data()

    @staticmethod
    def _get_default_value_for_type(data_type):
        """Returns the default initial value based on the datatype."""
        if data_type == "Date":
            return QDate.currentDate().toString("dd-MM-yyyy")
        elif data_type == "Time":
            return QTime.currentTime().toString("HH:mm:ss")
        elif data_type == "Date Time":
            return QDateTime.currentDateTime().toString("dd-MM-yyyy HH:mm:ss")
        elif data_type == "Timer":
            return "00:00:00.000"
        elif data_type == "String":
            return ""
        else:
            # For Bit, Int, Real, Counter, etc.
            return "0"

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # --- Toolbar ---
        self.toolbar = QToolBar("Tag Toolbar")
        self.toolbar.setIconSize(self.main_window.iconSize())
        
        self.add_action = QAction(IconService.get_icon('common-add-row'), "Add Tag", self)
        self.add_action.triggered.connect(self.add_tag)
        self.add_action.setShortcut(QKeySequence("Ctrl+N"))
        self.toolbar.addAction(self.add_action)

        self.remove_action = QAction(IconService.get_icon('common-remove-row'), "Remove Tag", self)
        self.remove_action.triggered.connect(self.remove_tag)
        self.toolbar.addAction(self.remove_action)
        
        empty = QWidget()
        empty.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.toolbar.addWidget(empty)

        layout.addWidget(self.toolbar)

        # --- Tree Widget ---
        self.table = TagTreeWidget()
        self.table.tag_table = self  # Set reference for context menu
        self.table.setColumnCount(6)
        self.table.setHeaderLabels([
            "Tag Name", "Data Type", "Initial Value", 
            "Array Elements", "Constant", "Comment"
        ])
        
        # Delegates
        self.table.setItemDelegateForColumn(0, TagNameDelegate(self, self.table))
        self.table.setItemDelegateForColumn(1, DataTypeDelegate(self, self.table))
        self.table.setItemDelegateForColumn(2, InitialValueDelegate(self, self.table))
        self.table.setItemDelegateForColumn(3, ArrayElementsDelegate(self, self.table))
        self.table.setItemDelegateForColumn(5, GenericDelegate(self, self.table))
        
        header = self.table.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(1, 120)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(2, 140)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(3, 100)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(4, 70)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setAlternatingRowColors(False)
        self.table.setRootIsDecorated(True)
        
        self.table.itemChanged.connect(self.on_item_changed)
        layout.addWidget(self.table)
        
        # Initialize clipboard for copy/paste
        self.clipboard_data = None
        
        # Setup keyboard shortcuts
        self.setup_keyboard_shortcuts()

    def block_signals(self, block):
        self.table.blockSignals(block)

    def load_data(self):
        self.block_signals(True)
        self.table.clear()
        tags = self.tag_data.get('tags', [])
        for tag in tags:
            self._insert_tag_item(self.table.topLevelItemCount(), tag)
        self.block_signals(False)

    def _insert_tag_item(self, index, tag_dict):
        item = QTreeWidgetItem()
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
        
        item.setText(0, tag_dict.get('name', 'Tag'))
        item.setText(1, tag_dict.get('type', 'Bit'))
        item.setText(2, tag_dict.get('initial_value', '0'))
        item.setText(3, tag_dict.get('array_elements', '1'))
        
        item.setCheckState(4, Qt.CheckState.Checked if tag_dict.get('constant', False) else Qt.CheckState.Unchecked)
        item.setText(5, tag_dict.get('comment', ''))
        
        # Store child values in UserRole of column 1 if needed, or rely on tag_dict passed here
        item.setData(0, Qt.ItemDataRole.UserRole, tag_dict)

        self.table.insertTopLevelItem(index, item)
        
        # Generate children if it's an array
        self._update_array_children(item, tag_dict.get('child_values', {}))

    def _update_array_children(self, parent_item, child_values=None):
        """Regenerates child items based on Array Elements dimension string."""
        # Clear existing children
        parent_item.takeChildren()
        
        if child_values is None:
            # Try to fetch from item data
            tag_data = parent_item.data(0, Qt.ItemDataRole.UserRole) or {}
            child_values = tag_data.get('child_values', {})

        dim_str = parent_item.text(3)
        dims = self._parse_array_dimensions(dim_str)
        
        total_elements = 1
        for d in dims: total_elements *= d
        
        # Only add children if we have an array > 1
        if total_elements > 1:
            base_name = parent_item.text(0)
            self._add_array_nodes(parent_item, dims, [], child_values, base_name)
            parent_item.setExpanded(True)
            self._update_parent_array_display(parent_item, dims)

    def _parse_array_dimensions(self, dim_str):
        """Parses '10', '10x10' etc. Returns empty list for invalid dimensions."""
        if not dim_str: return []
        try:
            parts = re.split(r'[xX]', str(dim_str))
            # Filter for valid digits and convert to int, exclude 0 and empty strings
            dims = []
            for p in parts:
                if p.isdigit():
                    val = int(p)
                    if val > 0:  # Only accept positive integers
                        dims.append(val)
                    else:
                        return []  # Invalid: 0 or negative dimension
                else:
                    return []  # Invalid: non-digit part
            return dims
        except ValueError:
            return []

    def _add_array_nodes(self, parent_item, dims, current_indices=[], child_values={}, base_name=""):
        depth = len(current_indices)
        if depth >= len(dims): return

        count = dims[depth]
        if count > 100:
            child = QTreeWidgetItem(parent_item)
            child.setText(0, f"Array too large ({count} items)")
            return

        for i in range(count):
            child = QTreeWidgetItem(parent_item)
            indices = current_indices + [i]
            
            # Generate key for this node, e.g. "0" or "0-1"
            key = "-".join(map(str, indices))
            
            # Generate full name: Tag[0][1]
            indices_str = "".join([f"[{idx}]" for idx in indices])
            child.setText(0, f"{base_name}{indices_str}")
            
            # Enable editing for specific columns by delegates, but set flag here
            child.setFlags(child.flags() | Qt.ItemFlag.ItemIsEditable)
            
            # Use stored child data if available, else inherit/default
            c_data = child_values.get(key, {})
            
            # Column 1: Type (Inherit from parent, read-only via delegate)
            child.setText(1, parent_item.text(1)) 
            
            # Column 2: Initial Value (Editable)
            # Use datatype-specific default if no child data exists
            parent_type = parent_item.text(1)
            default_val = TagTable._get_default_value_for_type(parent_type)
            
            # Use existing value from child data if present
            val_to_set = c_data.get('initial_value', default_val)
            child.setText(2, val_to_set)
            
            # Column 3: Array Elements (Empty for children)
            child.setText(3, "")
            
            # Column 4: Constant (Inherit or specific? Usually inherit structure)
            child.setCheckState(4, Qt.CheckState.Unchecked) # Disable checkbox logic for kids or inherit?
            
            # Column 5: Comment (Editable)
            child.setText(5, c_data.get('comment', ''))
            
            # Store the key in UserRole so we know which child this is later
            child.setData(0, Qt.ItemDataRole.UserRole, key)

            if depth + 1 < len(dims):
                self._add_array_nodes(child, dims, indices, child_values, base_name)
            else:
                # Leaf node logic if needed
                pass 
                
    def _update_parent_array_display(self, parent_item, dims=None):
        """
        Updates the parent item's initial value column to show nested list structure.
        E.g. [1, 2, 3] or [[1, 2], [3, 4]]
        """
        if dims is None:
            pass

        # We need to construct the nested list string recursively
        def build_nested_string(item):
            # If item is a leaf (no children), return its value
            if item.childCount() == 0:
                val = item.text(2)
                return val
            
            # If item has children, it's a list container
            elements = []
            for i in range(item.childCount()):
                child = item.child(i)
                # Skip placeholder if exists
                if child.text(0).startswith("Array too large"):
                    continue
                elements.append(build_nested_string(child))
            
            return "[" + ", ".join(elements) + "]"

        
        if parent_item.childCount() > 0:
            display_str = build_nested_string(parent_item)
            # Truncate if too long?
            if len(display_str) > 200:
                 display_str = display_str[:197] + "..."
            parent_item.setText(2, display_str)
            
            # Recursively update children that are containers (intermediate nodes)
            for i in range(parent_item.childCount()):
                child = parent_item.child(i)
                if child.childCount() > 0:
                    self._update_parent_array_display(child)

    def _get_row_data(self, row):
        item = self.table.topLevelItem(row)
        if not item:
            return {
                'name': '',
                'type': 'Bit',
                'initial_value': '0',
                'array_elements': '1',
                'constant': False,
                'comment': '',
                'child_values': {}
            }
        
        # Collect child data
        child_values = {}
        # Helper to recurse
        def collect_children(p_item):
            for i in range(p_item.childCount()):
                child = p_item.child(i)
                key = child.data(0, Qt.ItemDataRole.UserRole)
                if key: # It's a valid data node
                    # Only save if different from default to save space? 
                    # Or always save to be safe. Let's save.
                    child_values[key] = {
                        'initial_value': child.text(2),
                        'comment': child.text(5)
                    }
                collect_children(child)
        
        collect_children(item)

        return {
            'name': item.text(0),
            'type': item.text(1),
            'initial_value': item.text(2), # This might be the array string now
            'array_elements': item.text(3),
            'constant': item.checkState(4) == Qt.CheckState.Checked,
            'comment': item.text(5),
            'child_values': child_values
        }

    def _set_cell_value(self, row, col, value, child_key=None):
        item = self.table.topLevelItem(row)
        if not item: return
        
        target_item = item
        
        if child_key:
            # Find the child item
            found = False
            def find_child_recursive(parent):
                for i in range(parent.childCount()):
                    child = parent.child(i)
                    if child.data(0, Qt.ItemDataRole.UserRole) == child_key:
                        return child
                    found_in_child = find_child_recursive(child)
                    if found_in_child:
                        return found_in_child
                return None
            
            target_item = find_child_recursive(item)
            if not target_item: return

        if col == 4:
            target_item.setCheckState(4, Qt.CheckState.Checked if value else Qt.CheckState.Unchecked)
        else:
            target_item.setText(col, str(value))
            
        # Logic updates
        if child_key:
            # If a child's value changed, update the parent array display string
            if col == 2:
                self.table.blockSignals(True)
                curr = target_item.parent()
                while curr:
                    self._update_parent_array_display(curr)
                    curr = curr.parent()
                self.table.blockSignals(False)

        if not child_key:
            # If Name changed (col 0), update children names
            if col == 0:
                self.table.blockSignals(True)
                new_name = str(value)
                def update_names_recursive(parent_node):
                    for i in range(parent_node.childCount()):
                        c = parent_node.child(i)
                        key = c.data(0, Qt.ItemDataRole.UserRole)
                        if key:
                            indices_str = "".join([f"[{k}]" for k in key.split('-')])
                            c.setText(0, f"{new_name}{indices_str}")
                        update_names_recursive(c)
                update_names_recursive(item)
                self.table.blockSignals(False)

            # If Array Elements changed (col 3), update children structure
            if col == 3:
                self.table.blockSignals(True)
                self._update_array_children(item)
                self.table.blockSignals(False)
            
            # If Data Type changed (col 1), propagate to children and reset values
            if col == 1:
                self.table.blockSignals(True)
                
                # Get the appropriate default value based on new datatype
                default_val = TagTable._get_default_value_for_type(str(value))
                
                def update_type_recursive(parent):
                    for i in range(parent.childCount()):
                        child = parent.child(i)
                        child.setText(1, str(value))
                        # Reset initial value to datatype-specific default
                        child.setText(2, default_val)
                        update_type_recursive(child)
                update_type_recursive(item)
                
                # Update parent array display string since all children are now set to default
                self._update_parent_array_display(item)
                self.table.blockSignals(False)

    def on_item_changed(self, item, column):
        if self.table.signalsBlocked(): return
        
        # Only handle top-level items for structural saving via this signal
        # Child edits are handled via delegates/commands
        if item.parent(): return 

        # If Array Elements changed, update structure
        if column == 3:
            self.table.blockSignals(True)
            self._update_array_children(item)
            self.table.blockSignals(False)

        self.save_data()

    def _add_tag_from_data(self, tag_data):
        """
        Add a tag directly from a data dictionary.
        Used by OptimizedTagAddition for batch operations.
        
        Args:
            tag_data: Dictionary containing tag properties
        """
        row = self.table.topLevelItemCount()
        self._insert_tag_item(row, tag_data)

    def add_tag(self):
        row = self.table.topLevelItemCount()
        
        base_name = "Tag"
        count = 1
        new_name = f"{base_name}_{count}"
        
        # Check existing names
        existing_names = set()
        for i in range(row):
            existing_names.add(self.table.topLevelItem(i).text(0))
            
        while new_name in existing_names:
            count += 1
            new_name = f"{base_name}_{count}"

        new_tag = {
            'name': new_name,
            'type': 'Bit',
            'initial_value': '0',
            'array_elements': '1',
            'constant': False,
            'comment': '',
            'child_values': {}
        }
        
        command = TagAddCommand(self, row, new_tag)
        self.undo_stack.push(command)

    def remove_tag(self):
        # Get selected top level items
        selected_items = self.table.selectedItems()
        rows_to_remove = set()
        
        root = self.table.invisibleRootItem()
        for item in selected_items:
            # Standard behavior: remove the tag definition.
            top_item = item
            while top_item.parent(): top_item = top_item.parent()
            
            row = root.indexOfChild(top_item)
            if row != -1:
                rows_to_remove.add(row)

        if not rows_to_remove and self.table.currentItem():
             item = self.table.currentItem()
             top_item = item
             while top_item.parent(): top_item = top_item.parent()
             row = root.indexOfChild(top_item)
             if row != -1: rows_to_remove.add(row)

        if not rows_to_remove: return

        # Optimize for large deletions using batch processing
        if OptimizedTagDeletion and len(rows_to_remove) > 10:
            rows_data = []
            for r in sorted(rows_to_remove):
                rows_data.append((r, self._get_row_data(r)))
            
            command = TagRemoveCommand(self, rows_data)
            self.undo_stack.push(command)
        else:
            # Standard deletion for small operations
            rows_data = []
            for r in rows_to_remove:
                rows_data.append((r, self._get_row_data(r)))

            command = TagRemoveCommand(self, rows_data)
            self.undo_stack.push(command)
        
    def delete(self):
        self.remove_tag()

    def undo(self):
        self.undo_stack.undo()

    def redo(self):
        self.undo_stack.redo()

    def setup_keyboard_shortcuts(self):
        """Setup keyboard shortcuts for various operations.
        Note: Cut, Copy, Paste, Undo, Redo are already handled by Edit Menu.
        Only register Insert shortcut here.
        """
        # Insert: Ctrl+I
        insert_action = QAction(self)
        insert_action.setShortcut(QKeySequence("Ctrl+I"))
        insert_action.triggered.connect(self.add_tag)
        self.addAction(insert_action)

    def show_context_menu(self, position):
        """Display context menu with cut, copy, paste, delete, insert options."""
        menu = QMenu(self)
        
        # Cut
        cut_action = menu.addAction("Cut")
        cut_action.triggered.connect(self.cut)
        
        # Copy
        copy_action = menu.addAction("Copy")
        copy_action.triggered.connect(self.copy)
        
        # Paste
        paste_action = menu.addAction("Paste")
        paste_action.triggered.connect(self.paste)
        paste_action.setEnabled(self.clipboard_data is not None)
        
        menu.addSeparator()
        
        # Delete
        delete_action = menu.addAction("Delete")
        delete_action.triggered.connect(self.delete)
        
        # Insert
        insert_action = menu.addAction("Insert")
        insert_action.triggered.connect(self.add_tag)
        
        menu.exec(position)

    def copy(self):
        """Copy selected tags to clipboard."""
        selected_items = self.table.selectedItems()
        rows_to_copy = set()
        
        root = self.table.invisibleRootItem()
        for item in selected_items:
            top_item = item
            while top_item.parent():
                top_item = top_item.parent()
            
            row = root.indexOfChild(top_item)
            if row != -1:
                rows_to_copy.add(row)
        
        if not rows_to_copy and self.table.currentItem():
            item = self.table.currentItem()
            top_item = item
            while top_item.parent():
                top_item = top_item.parent()
            row = root.indexOfChild(top_item)
            if row != -1:
                rows_to_copy.add(row)
        
        if rows_to_copy:
            self.clipboard_data = []
            for r in sorted(rows_to_copy):
                self.clipboard_data.append(self._get_row_data(r))
            QMessageBox.information(self, "Copy", f"Copied {len(rows_to_copy)} tag(s) to clipboard.")
        else:
            QMessageBox.warning(self, "Copy", "No tags selected to copy.")

    def cut(self):
        """Cut selected tags (copy and delete)."""
        self.copy()
        if self.clipboard_data:
            self.remove_tag()

    def paste(self):
        """Paste tags from clipboard."""
        if not self.clipboard_data:
            QMessageBox.warning(self, "Paste", "Clipboard is empty. No tags to paste.")
            return
        
        # Ensure unique tag names
        existing_names = set()
        for i in range(self.table.topLevelItemCount()):
            item = self.table.topLevelItem(i)
            if item:
                existing_names.add(item.text(0))
        
        # Paste at the end or at current row position
        insert_row = self.table.topLevelItemCount()
        current_item = self.table.currentItem()
        if current_item:
            root = self.table.invisibleRootItem()
            top_item = current_item
            while top_item.parent():
                top_item = top_item.parent()
            insert_row = root.indexOfChild(top_item) + 1
        
        # Make copies with unique names
        tags_to_paste = []
        for tag_data in self.clipboard_data:
            new_tag = copy.deepcopy(tag_data)
            base_name = new_tag['name']
            count = 1
            new_name = f"{base_name}_copy"
            
            while new_name in existing_names:
                count += 1
                new_name = f"{base_name}_copy_{count}"
            
            new_tag['name'] = new_name
            existing_names.add(new_name)
            tags_to_paste.append(new_tag)
        
        # Create paste command
        command = TagPasteCommand(self, insert_row, tags_to_paste)
        self.undo_stack.push(command)
        
        QMessageBox.information(self, "Paste", f"Pasted {len(tags_to_paste)} tag(s).")


    def save_data(self):
        tags = []
        for row in range(self.table.topLevelItemCount()):
            tags.append(self._get_row_data(row))
        
        self.tag_data['tags'] = tags
        
        # Check if project_service exists and is not None
        if hasattr(self.main_window, 'project_service') and self.main_window.project_service is not None:
            tag_number = str(self.tag_data.get('number'))
            if tag_number:
                if 'tag_lists' not in self.main_window.project_service.project_data:
                    self.main_window.project_service.project_data['tag_lists'] = {}
                
                self.main_window.project_service.project_data['tag_lists'][tag_number] = self.tag_data
                self.main_window.project_service.mark_as_unsaved()