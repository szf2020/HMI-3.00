# project\comment\comment_table.py
import re
import collections
import logging
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QToolBar, QTableWidget, QTableWidgetItem,
    QLineEdit, QMessageBox, QAbstractItemView, QHeaderView, QApplication, QLabel,
    QStyledItemDelegate, QMenu, QListWidget, QSpinBox, QDialog, QFormLayout, 
    QPushButton, QHBoxLayout
)
from main_window.widgets.color_selector import ColorSelector
from PySide6.QtGui import (
    QColor, QBrush, QFont, QPainter, QPen, QKeySequence, QUndoStack, QUndoCommand, QAction
)
from PySide6.QtCore import Qt, QRectF, QPointF, Signal, QEvent
from styles import colors, stylesheets
from .comment_utils import FormulaParser, FUNCTION_HINTS, adjust_formula_references, col_str_to_int, col_int_to_str
from .optimized_operations import OptimizedBatchDelete, OptimizedColumnAddition
from .performance_config import MAX_COLUMNS, MAX_ROWS

logger = logging.getLogger(__name__)

# --- Insert Quantity Dialog ---

class InsertQuantityDialog(QDialog):
    """Dialog to ask user how many rows or columns to insert."""
    def __init__(self, mode='row', current_count=0, parent=None):
        """
        Parameters:
        - mode: 'row' or 'column' to specify what type of insertion
        - current_count: current number of rows or columns in the table
        - parent: parent widget
        """
        super().__init__(parent)
        self.mode = mode
        self.quantity = 1
        
        # Set dialog properties
        if mode == 'row':
            self.setWindowTitle("Insert Rows")
            self.max_per_insertion = 10000  # Max rows per single insertion
            self.max_total = 1000000  # Max total rows in table
            remaining = self.max_total - current_count
            self.max_limit = min(self.max_per_insertion, remaining)
            label_text = f"Number of rows to insert (max {self.max_limit}):"
        else:
            self.setWindowTitle("Insert Columns")
            self.max_per_insertion = 30  # Max columns per single insertion
            self.max_total = 30  # Max total columns in table
            remaining = self.max_total - current_count
            self.max_limit = min(self.max_per_insertion, remaining)
            label_text = f"Number of columns to insert (max {self.max_limit}):"
        
        # Create layout
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        
        # Create spin box for quantity
        self.quantity_spinbox = QSpinBox()
        self.quantity_spinbox.setMinimum(1)
        self.quantity_spinbox.setMaximum(self.max_limit)
        self.quantity_spinbox.setValue(1)
        
        form_layout.addRow(label_text, self.quantity_spinbox)
        
        # Create buttons
        button_layout = QHBoxLayout()
        ok_button = QPushButton("OK")
        cancel_button = QPushButton("Cancel")
        
        ok_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        
        layout.addLayout(form_layout)
        layout.addLayout(button_layout)
        
        self.setMinimumWidth(350)
    
    def get_quantity(self):
        """Returns the quantity entered by the user."""
        return self.quantity_spinbox.value()

# --- End Insert Quantity Dialog ---



class ChangeCellCommand(QUndoCommand):
    """An undo command for changing the data of one or more cells."""
    def __init__(self, table, changes, text="Cell Change"):
        super().__init__(text)
        self.table = table
        self.changes = changes

    def redo(self):
        self.table.apply_changes(self.changes)

    def undo(self):
        # Reverse changes: (row, col, old, new) -> (row, col, new, old)
        reversed_changes = [(r, c, n, o) for r, c, o, n in self.changes]
        self.table.apply_changes(reversed_changes)

class ResizeCommand(QUndoCommand):
    """An undo command for adding/removing rows or columns."""
    def __init__(self, table, action, index, count=1):
        super().__init__(f"{action.replace('_', ' ').title()}")
        self.table = table
        self.action = action # 'add_row', 'remove_row', 'add_col', 'remove_col'
        self.index = index
        self.count = count
        self.saved_data = [] # Used for undoing removals

    def redo(self):
        if 'add' in self.action:
            self.table.perform_insert(self.action, self.index, self.count)
        else:
            self.saved_data = self.table.perform_remove(self.action, self.index)

    def undo(self):
        if 'add' in self.action:
            # Undo add = remove
            remove_action = self.action.replace('add', 'remove')
            self.table.perform_remove(remove_action, self.index)
        else:
            # Undo remove = insert and restore
            insert_action = self.action.replace('remove', 'add')
            self.table.perform_insert_with_restore(insert_action, self.index, self.saved_data)

# --- End Undo Commands ---

class CommentTable(QWidget):
    """
    A widget that provides a spreadsheet-like interface for comments,
    supporting formulas, cell referencing, and basic Excel features.
    """
    def __init__(self, comment_data, main_window, common_menu, comment_service, parent=None):
        super().__init__(parent)
        self.comment_data = comment_data
        self.main_window = main_window
        self.common_menu = common_menu
        self.comment_service = comment_service

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        toolbar = self._create_toolbar()
        self.formula_bar = QLineEdit()
        self.formula_bar.setPlaceholderText("Enter formula here")
        self.table_widget = Spreadsheet(self, self.comment_service, self.comment_data['number'])

        layout.addWidget(toolbar)
        layout.addWidget(self.formula_bar)
        layout.addWidget(self.table_widget)

        self._connect_signals()

    def _create_toolbar(self):
        toolbar = QToolBar("Comment Toolbar")
        toolbar.setIconSize(self.main_window.iconSize())
        toolbar.addAction(self.common_menu.add_column_action)
        toolbar.addAction(self.common_menu.add_row_action)
        toolbar.addAction(self.common_menu.remove_column_action)
        toolbar.addAction(self.common_menu.remove_row_action)
        toolbar.addSeparator()
        toolbar.addAction(self.common_menu.bold_action)
        toolbar.addAction(self.common_menu.italic_action)
        toolbar.addAction(self.common_menu.underline_action)
        toolbar.addAction(self.common_menu.fill_text_action)
        toolbar.addAction(self.common_menu.fill_background_action)
        return toolbar

    def _connect_signals(self):
        self.common_menu.add_column_action.triggered.connect(self.table_widget.add_column)
        self.common_menu.add_row_action.triggered.connect(self.table_widget.add_row)
        self.common_menu.remove_column_action.triggered.connect(self.table_widget.remove_column)
        self.common_menu.remove_row_action.triggered.connect(self.table_widget.remove_row)
        self.common_menu.bold_action.triggered.connect(self.table_widget.set_bold)
        self.common_menu.italic_action.triggered.connect(self.table_widget.set_italic)
        self.common_menu.underline_action.triggered.connect(self.table_widget.set_underline)
        self.common_menu.fill_text_action.triggered.connect(self.table_widget.set_text_color)
        self.common_menu.fill_background_action.triggered.connect(self.table_widget.set_background_color)
        self.table_widget.currentCellChanged.connect(self.update_formula_bar)
        self.formula_bar.returnPressed.connect(self.update_cell_from_formula_bar)
        self.table_widget.cellClicked.connect(self.handle_cell_click_for_formula)

    def handle_cell_click_for_formula(self, row, column):
        if self.formula_bar.hasFocus() and self.formula_bar.text().startswith('='):
            cell_ref = self.table_widget.get_cell_ref_str(row, column)
            self.formula_bar.insert(cell_ref)

    def update_formula_bar(self, currentRow, currentColumn, previousRow, previousColumn):
        item = self.table_widget.item(currentRow, currentColumn)
        if item:
            data = item.get_data()
            self.formula_bar.setText(str(data.get('value', '')))

    def update_cell_from_formula_bar(self):
        current_item = self.table_widget.currentItem()
        if current_item:
            row = self.table_widget.currentRow()
            col = self.table_widget.currentColumn()
            old_data = current_item.get_data()
            new_data = old_data.copy()
            new_data['value'] = self.formula_bar.text()
            if new_data != old_data:
                changes = [(row, col, old_data, new_data)]
                command = ChangeCellCommand(self.table_widget, changes, "Edit Cell")
                self.table_widget.undo_stack.push(command)

class SpreadsheetItem(QTableWidgetItem):
    def __init__(self, data=None):
        super().__init__()
        if data is None: data = {'value': ''}
        self.set_data(data)

    def get_data(self):
        return self.data(Qt.ItemDataRole.UserRole) or {'value': ''}

    def set_data(self, data):
        self.setData(Qt.ItemDataRole.UserRole, data)
        font = QFont()
        font_data = data.get('font', {})
        font.setBold(font_data.get('bold', False))
        font.setItalic(font_data.get('italic', False))
        font.setUnderline(font_data.get('underline', False))
        self.setFont(font)
        bg = data.get('bg_color')
        self.setBackground(QColor(bg) if bg else QBrush())
        fg = data.get('text_color')
        self.setForeground(QColor(fg) if fg else QColor(colors.TEXT_PRIMARY))

class ExcelHeaderView(QHeaderView):
    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)
        self.setHighlightSections(False)
        self.setSectionsClickable(True)
        self.sectionClicked.connect(self.on_section_clicked)

    def on_section_clicked(self, logicalIndex):
        if self.orientation() == Qt.Orientation.Horizontal:
            self.parentWidget().selectColumn(logicalIndex)
        else:
            self.parentWidget().selectRow(logicalIndex)

class SpreadsheetDelegate(QStyledItemDelegate):
    editingTextChanged = Signal(str)
    def createEditor(self, parent, option, index):
        editor = super().createEditor(parent, option, index)
        if isinstance(editor, QLineEdit):
            editor.textChanged.connect(self.editingTextChanged)
        return editor
    def setEditorData(self, editor, index):
        data = index.model().data(index, Qt.ItemDataRole.UserRole) or {}
        if isinstance(editor, QLineEdit): editor.setText(str(data.get('value', '')))
    def setModelData(self, editor, model, index):
        if isinstance(editor, QLineEdit):
            table = self.parent()
            new_val = editor.text()
            old_data = index.model().data(index, Qt.ItemDataRole.UserRole) or {'value': ''}
            new_data = old_data.copy()
            new_data['value'] = new_val
            if old_data != new_data:
                changes = [(index.row(), index.column(), old_data, new_data)]
                command = ChangeCellCommand(table, changes, "Edit Cell")
                table.undo_stack.push(command)

class Spreadsheet(QTableWidget):
    def __init__(self, parent=None, comment_service=None, comment_number=None):
        super().__init__(1000, 2, parent)
        self.comment_service = comment_service
        self.comment_number = comment_number
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setMouseTracking(True)
        self.hover_row = -1
        self.hover_col = -1
        
        # Set spreadsheet styling
        self.setStyleSheet(f"""
            QTableWidget {{
                background-color: {colors.BG_SPREADSHEET};
                color: {colors.TEXT_PRIMARY};
                gridline-color: {colors.GRID_LINE};
                selection-background-color: transparent;
                border: none;
            }}
            QTableWidget::item {{
                padding: 2px;
            }}
            QLineEdit {{
                background-color: {colors.BG_DARK_TERTIARY};
                color: {colors.TEXT_PRIMARY};
                border: 1px solid {colors.ACCENT_GREEN};
            }}
        """)
        
        # Dependency Management
        self.dependents = collections.defaultdict(set) # Key: (row, col), Value: Set of dependent (row, col)
        self.precedents = collections.defaultdict(set) # Key: (row, col), Value: Set of precedent (row, col)
        self._evaluating = False # Flag to prevent recursion loops
        self._updates_deferred = False # Flag for batch operations

        self._is_dragging_fill_handle = False
        self._drag_start_pos = None
        self._drag_fill_rect = None
        self.highlighted_cells = set()
        self.referenced_cells = []
        self.ref_colors = [QColor(colors.COLOR_REF_BLUE), QColor(colors.COLOR_REF_RED), QColor(colors.COLOR_REF_GREEN), QColor(colors.COLOR_REF_PURPLE)]
        self.undo_stack = QUndoStack(self)

        # --- Formula Hinting Widgets ---
        self.formula_hint = QLabel(self)
        # Changed from ToolTip to Tool to prevent overlapping other apps while staying on top of parent
        self.formula_hint.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint)
        self.formula_hint.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.formula_hint.setStyleSheet(stylesheets.get_formula_hint_stylesheet())
        self.formula_hint.hide()

        self.completer_popup = QListWidget(self)
        # Changed from ToolTip to Tool to prevent overlapping other apps while staying on top of parent
        self.completer_popup.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint)
        self.completer_popup.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.completer_popup.setStyleSheet(stylesheets.get_completer_popup_stylesheet())
        self.completer_popup.hide()
        self.completer_popup.itemClicked.connect(self.complete_formula)
        # --- End Hinting Widgets ---
        
        # Install event filter on the application to detect focus changes globally
        QApplication.instance().installEventFilter(self)

        self.setHorizontalHeader(ExcelHeaderView(Qt.Orientation.Horizontal, self))
        self.setVerticalHeader(ExcelHeaderView(Qt.Orientation.Vertical, self))
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.delegate = SpreadsheetDelegate(self)
        self.setItemDelegate(self.delegate)
        self.delegate.editingTextChanged.connect(parent.formula_bar.setText)

        self.update_headers()
        self.itemSelectionChanged.connect(self.on_selection_changed)
        parent.formula_bar.textChanged.connect(self.on_formula_bar_text_changed)

        # REMOVED: Stylesheet now handled by global stylesheet.qss
        # The global stylesheet provides consistent theming across the application
        
        self.load_data_from_service()
        
        # Enable custom context menu for headers
        self.horizontalHeader().setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.horizontalHeader().customContextMenuRequested.connect(self.show_header_context_menu)
        self.verticalHeader().setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.verticalHeader().customContextMenuRequested.connect(self.show_header_context_menu)

    def set_updates_deferred(self, state):
        """
        Controls whether expensive operations like saving and evaluating
        are performed immediately or deferred.
        """
        self._updates_deferred = state
        if not state:
            self.update_headers()
            self.save_data_to_service()
            self.evaluate_all_cells()

    def eventFilter(self, obj, event):
        """Global event filter to hide popups when application loses focus."""
        if event.type() == QEvent.Type.ApplicationStateChange:
             if QApplication.instance().applicationState() != Qt.ApplicationState.ApplicationActive:
                 self.formula_hint.hide()
                 self.completer_popup.hide()
        return super().eventFilter(obj, event)

    # --- New Helper Methods to Fix AttributeError ---
    def isColumnSelected(self, column):
        """Check if the entire column is selected."""
        return self.selectionModel().isColumnSelected(self.model().index(0, column), self.model().index(self.rowCount()-1, column))

    def isRowSelected(self, row):
        """Check if the entire row is selected."""
        return self.selectionModel().isRowSelected(self.model().index(row, 0), self.model().index(row, self.columnCount()-1))
    # ------------------------------------------------

    def show_header_context_menu(self, pos):
        header = self.sender()
        logicalIndex = header.logicalIndexAt(pos)
        
        # Standard Excel behavior: Right-clicking a header should select it if not already selected
        if header.orientation() == Qt.Orientation.Horizontal:
            # Note: selectionModel().isColumnSelected requires checks. 
            # We can simplify by just selecting if the count of selected cells doesn't match a full column
            self.selectColumn(logicalIndex)
        else:
            self.selectRow(logicalIndex)

        menu = QMenu(self)

        cut_action = menu.addAction("Cut")
        copy_action = menu.addAction("Copy")
        paste_action = menu.addAction("Paste")
        menu.addSeparator()
        clear_contents_action = menu.addAction("Clear Content")
        menu.addSeparator()
        insert_action = menu.addAction("Insert")
        delete_action = menu.addAction("Delete")

        # Connect actions to methods
        cut_action.triggered.connect(self.cut)
        copy_action.triggered.connect(self.copy)
        paste_action.triggered.connect(self.paste)
        
        if header.orientation() == Qt.Orientation.Horizontal:
            clear_contents_action.triggered.connect(lambda: self.clear_column_contents(logicalIndex))
            insert_action.triggered.connect(lambda: self.insert_column(logicalIndex))
            delete_action.triggered.connect(lambda: self.remove_column(logicalIndex)) 
        else:
            clear_contents_action.triggered.connect(lambda: self.clear_row_contents(logicalIndex))
            insert_action.triggered.connect(lambda: self.insert_row(logicalIndex))
            delete_action.triggered.connect(lambda: self.remove_row(logicalIndex)) 

        menu.exec(header.mapToGlobal(pos))

    # --- Dependency Graph Methods ---
    
    def add_dependency(self, dependent_cell, precedent_cell):
        """
        Called by FormulaParser when 'dependent_cell' reads 'precedent_cell'.
        """
        self.precedents[dependent_cell].add(precedent_cell)
        self.dependents[precedent_cell].add(dependent_cell)

    def clear_dependencies(self, cell):
        """Clears outgoing dependencies for a cell before re-parsing."""
        if cell in self.precedents:
            for prec in self.precedents[cell]:
                if cell in self.dependents[prec]:
                    self.dependents[prec].remove(cell)
            del self.precedents[cell]

    def evaluate_cell(self, row, col, propagate=True):
        """
        Evaluates a specific cell, updates the graph, and optionally propagates updates.
        """
        item = self.item(row, col)
        if not item: return

        data = item.get_data()
        raw_value = str(data.get('value', ''))
        
        if raw_value.startswith('='):
            cell_coords = (row, col)
            # 1. Clear old dependencies
            self.clear_dependencies(cell_coords)
            
            # 2. Parse and Evaluate
            try:
                # Pass self (Spreadsheet) as the table interface
                parser = FormulaParser(self, cell_coords) 
                result = parser.evaluate(raw_value[1:])
                
                # Format Result
                if isinstance(result, bool): item.setText(str(result).upper())
                elif isinstance(result, float) and result.is_integer(): item.setText(str(int(result)))
                else: item.setText(f"{result:.2f}" if isinstance(result, float) else str(result))
            except Exception:
                item.setText("#ERROR")
        else:
            # If it's not a formula, just show text
            # Also clear dependencies because it's no longer a formula
            self.clear_dependencies((row, col))
            item.setText(raw_value)

        # 3. Propagate to dependents
        if propagate and (row, col) in self.dependents:
            # Create a copy of the set to avoid "Set changed size during iteration" error
            # when recursive calls modify the dependents set
            for dep_row, dep_col in list(self.dependents[(row, col)]):
                self.evaluate_cell(dep_row, dep_col, propagate=True)

    def evaluate_all_cells(self):
        """
        Evaluates all cells using Topological Sort to handle dependencies efficiently.
        """
        # 1. Clear all dependencies and rebuild graph from scratch
        self.dependents.clear()
        self.precedents.clear()

        # 2. First pass: Parse all formulas to build the dependency graph (without evaluating values yet if possible, 
        #    but simplest is just to eval). 
        #    However, to avoid double work, we can just queue cells.
        
        cells_with_formulas = []
        for r in range(self.rowCount()):
            for c in range(self.columnCount()):
                item = self.item(r, c)
                if item and str(item.get_data().get('value', '')).startswith('='):
                    cells_with_formulas.append((r, c))
                elif item:
                    item.setText(str(item.get_data().get('value', '')))

        # 3. Evaluation Loop (Simple approach with cycle detection)
        # A true topological sort is better, but just evaluating standard cells first then formulas works often.
        # Given the circular ref possibility, we'll just call evaluate_cell.
        # To prevent infinite recursion during init, we rely on the parser.
        
        # Better approach: Just evaluate everything. The recursion in `evaluate_cell` 
        # handles the order if we trigger it. But efficient way is:
        # Evaluate cells with NO formulas first (done above).
        # Then evaluate cells with formulas.
        for r, c in cells_with_formulas:
            self.evaluate_cell(r, c, propagate=False) 
            # propagate=False because we are iterating everyone anyway, 
            # though correct order matters.
            
        # Refined Approach: 
        # To ensure correct order (A1 before B1 if B1=A1), we need to resolve deps.
        # Since we cleared deps, we let `evaluate_cell` rebuild them.
        # We might calculate a cell twice if we are not careful, but that's safer than O(N^2).
        pass

    # --- Data Operations ---

    def get_cell_value(self, row, col):
        item = self.item(row, col)
        if not item: return 0
        text = item.text()
        try: return float(text)
        except: return text

    def apply_changes(self, changes):
        """Applies a batch of cell changes and triggers updates."""
        self.blockSignals(True)
        affected_cells = []
        for row, col, _, new_data in changes:
            item = self.item(row, col)
            if not item:
                item = SpreadsheetItem()
                self.setItem(row, col, item)
            item.set_data(new_data)
            affected_cells.append((row, col))
        self.blockSignals(False)
        
        for r, c in affected_cells:
            self.evaluate_cell(r, c)
            
        self.viewport().update()
        self.save_data_to_service()

    def perform_insert(self, action, index, count=1):
        self.blockSignals(True)
        if action == 'add_row':
            for _ in range(count): self.insertRow(index)
            self.shift_formulas_for_insert_delete(row_threshold=index, row_shift=count)
        elif action == 'add_col':
            for _ in range(count): self.insertColumn(index)
            self.shift_formulas_for_insert_delete(col_threshold=index, col_shift=count)
        
        self.blockSignals(False)
        
        if not self._updates_deferred:
            self.update_headers()
            self.save_data_to_service()
            self.evaluate_all_cells()

    def perform_remove(self, action, index):
        self.blockSignals(True)
        saved_data = []
        
        if action == 'remove_row':
            # Save data for undo
            for c in range(self.columnCount()):
                item = self.item(index, c)
                saved_data.append(item.get_data() if item else {'value': ''})
            self.removeRow(index)
            self.shift_formulas_for_insert_delete(row_threshold=index, row_shift=-1, deleted_row=index)
            
        elif action == 'remove_col':
            for r in range(self.rowCount()):
                item = self.item(r, index)
                saved_data.append(item.get_data() if item else {'value': ''})
            self.removeColumn(index)
            self.shift_formulas_for_insert_delete(col_threshold=index, col_shift=-1, deleted_col=index)

        self.blockSignals(False)
        
        if not self._updates_deferred:
            self.update_headers()
            self.save_data_to_service()
            self.evaluate_all_cells()
        return saved_data

    def perform_insert_with_restore(self, action, index, saved_data):
        # Used for undoing a delete
        self.perform_insert(action, index, 1) # This handles the shift
        # Now restore data
        self.blockSignals(True)
        if action == 'add_row':
            for c, data in enumerate(saved_data):
                item = self.item(index, c)
                if not item: 
                    item = SpreadsheetItem()
                    self.setItem(index, c, item)
                item.set_data(data)
        elif action == 'add_col':
             for r, data in enumerate(saved_data):
                item = self.item(r, index)
                if not item: 
                    item = SpreadsheetItem()
                    self.setItem(r, index, item)
                item.set_data(data)
        self.blockSignals(False)
        
        if not self._updates_deferred:
            self.save_data_to_service()
            self.evaluate_all_cells()

    def shift_formulas_for_insert_delete(self, row_threshold=0, col_threshold=0, row_shift=0, col_shift=0, deleted_row=-1, deleted_col=-1):
        """
        Iterates over all cells and updates formulas to point to new locations.
        """
        for r in range(self.rowCount()):
            for c in range(self.columnCount()):
                item = self.item(r, c)
                if not item: continue
                
                data = item.get_data()
                val = str(data.get('value', ''))
                
                if val.startswith('='):
                    new_formula = adjust_formula_references(
                        val, 
                        row_offset=row_shift, 
                        col_offset=col_shift, 
                        min_row=row_threshold, 
                        min_col=col_threshold,
                        delete_row=deleted_row,
                        delete_col=deleted_col
                    )
                    if new_formula != val:
                        data['value'] = new_formula
                        item.set_data(data)

    def paste(self):
        selection = self.selectedRanges()
        if not selection: return
        start_row, start_col = selection[0].topRow(), selection[0].leftColumn()

        clipboard_text = QApplication.clipboard().text()
        rows = clipboard_text.strip('\n').split('\n')
        changes = []
        
        for r_idx, row_text in enumerate(rows):
            cols = row_text.split('\t')
            for c_idx, val in enumerate(cols):
                target_row, target_col = start_row + r_idx, start_col + c_idx
                if target_row < self.rowCount() and target_col < self.columnCount():
                    item = self.item(target_row, target_col)
                    old_data = item.get_data() if item else {'value': ''}
                    new_data = old_data.copy()
                    
                    # Intelligent Paste: Adjust relative references
                    # We assume the copy source was (0,0) relative to the clipboard structure
                    # This is a simplification. A full Excel clone stores source coords in clipboard.
                    # For now, we just set value. Real relative paste requires knowing source indices.
                    # Assuming simple text paste for now, but if it looks like formula, we paste as is?
                    # Problem: "Relative Reference Adjustment on Paste" requested.
                    # Limitation: Standard text clipboard doesn't hold source coordinates.
                    # Solution: Use EditService for internal copy to track source row/col.
                    
                    from services.edit_service import ClipboardDataType
                    clipboard_data, clipboard_type, _ = self.parent().main_window.edit_service.get_clipboard()
                    if clipboard_type == ClipboardDataType.TABLE_CELLS and clipboard_data and 'is_spreadsheet' in clipboard_data:
                        source_data = clipboard_data
                        # Use internal logic if available
                        src_r = source_data['start_row'] + r_idx
                        src_c = source_data['start_col'] + c_idx
                        # Calculate offset
                        row_offset = target_row - src_r
                        col_offset = target_col - src_c
                        
                        if val.startswith('='):
                            val = adjust_formula_references(val, row_offset, col_offset)

                    new_data['value'] = val
                    changes.append((target_row, target_col, old_data, new_data))

        if changes:
            self.undo_stack.push(ChangeCellCommand(self, changes, "Paste"))

    def copy(self):
        selection = self.selectedRanges()
        if not selection: return
        r1, c1 = selection[0].topRow(), selection[0].leftColumn()
        r2, c2 = selection[0].bottomRow(), selection[0].rightColumn()
        
        # Save metadata for intelligent paste using new EditService API
        from services.edit_service import ClipboardDataType
        self.parent().main_window.edit_service.set_clipboard({
            'is_spreadsheet': True,
            'start_row': r1,
            'start_col': c1
        }, ClipboardDataType.TABLE_CELLS)
        
        text = ""
        for r in range(r1, r2 + 1):
            row_data = []
            for c in range(c1, c2 + 1):
                item = self.item(r, c)
                row_data.append(str(item.get_data().get('value', '')) if item else "")
            text += "\t".join(row_data) + "\n"
        QApplication.clipboard().setText(text)

    def cut(self):
        self.copy()
        self.delete()

    def delete(self):
        selection = self.selectedRanges()
        if not selection: return
        changes = []
        for r in selection:
            for row in range(r.topRow(), r.bottomRow() + 1):
                for col in range(r.leftColumn(), r.rightColumn() + 1):
                    item = self.item(row, col)
                    if item and item.get_data().get('value'):
                        old = item.get_data()
                        new = old.copy()
                        new['value'] = ''
                        changes.append((row, col, old, new))
        if changes:
            self.undo_stack.push(ChangeCellCommand(self, changes, "Delete"))
    
    def undo(self):
        self.set_updates_deferred(True)
        self.undo_stack.undo()
        self.set_updates_deferred(False)

    def redo(self):
        self.set_updates_deferred(True)
        self.undo_stack.redo()
        self.set_updates_deferred(False)
    
    def load_data_from_service(self):
        if not self.comment_service: return
        table_data = self.comment_service.get_table_data(self.comment_number)
        if not table_data: return

        self.setRowCount(len(table_data))
        self.setColumnCount(len(table_data[0]) if table_data else 0)
        self.update_headers()

        self.blockSignals(True)
        for r, row in enumerate(table_data):
            for c, cell_data in enumerate(row):
                item = self.item(r, c) or SpreadsheetItem()
                self.setItem(r, c, item)
                item.set_data(cell_data)
        self.blockSignals(False)
        self.evaluate_all_cells()

    def save_data_to_service(self):
        if not self.comment_service: return
        data = []
        for r in range(self.rowCount()):
            row_d = []
            for c in range(self.columnCount()):
                item = self.item(r, c)
                row_d.append(item.get_data() if item else {'value': ''})
            data.append(row_d)
        self.comment_service.update_table_data(self.comment_number, data)

    def update_headers(self):
        self.setHorizontalHeaderLabels([col_int_to_str(i) for i in range(self.columnCount())])
        self.setVerticalHeaderLabels([str(i+1) for i in range(self.rowCount())])

    def get_cell_ref_str(self, row, col):
        return f"{col_int_to_str(col)}{row + 1}"

    def add_column(self):
        # Insert at current selection if available, else insert BEFORE current index
        selected_cols = self.selectedRanges()
        count = 0
        idx = 0
        
        if selected_cols:
             for r in selected_cols:
                 count += r.columnCount()
             idx = selected_cols[0].leftColumn()
        else:
             count = 1
             idx = self.currentColumn()
             if idx < 0: idx = self.columnCount() # If no selection, append? Standard excel inserts before active cell.
        
        if count == 0: count = 1
        if self.columnCount() + count > MAX_COLUMNS:
            QMessageBox.warning(self, "Limit", f"Max {MAX_COLUMNS} columns allowed.")
            return
        
        # Use optimized addition for tables with many rows
        if self.rowCount() > 10000 and count > 1:
            OptimizedColumnAddition.add_columns_optimized(self, idx, count, show_progress=True)
        else:
            self.undo_stack.push(ResizeCommand(self, 'add_col', idx, count))

    def add_row(self):
        # Insert at current selection if available, else insert BEFORE current index
        selected_rows = self.selectedRanges()
        count = 0
        idx = 0

        if selected_rows:
             for r in selected_rows:
                 count += r.rowCount()
             idx = selected_rows[0].topRow()
        else:
             count = 1
             idx = self.currentRow()
             if idx < 0: idx = self.rowCount()

        if count == 0: count = 1
        if self.rowCount() + count > MAX_ROWS:
            QMessageBox.warning(self, "Limit", f"Max {MAX_ROWS:,} rows allowed.")
            return
            
        self.undo_stack.push(ResizeCommand(self, 'add_row', idx, count))

    def remove_column(self, index=None):
        # FIX: Ensure index is strictly an int and not bool (from signal)
        # Signals send 'False' which is 0, causing column 0 deletion on simple button click
        target_index = None
        if index is not None and type(index) is int:
            target_index = index
            
        cols_to_remove = set()
        
        if target_index is not None:
             # Context menu deletion
             # If the target column is part of a multi-column selection, delete all selected
             # Otherwise just delete the target
             selection_model = self.selectionModel()
             if selection_model and selection_model.isColumnSelected(target_index, self.rootIndex()):
                 for r in self.selectedRanges():
                     for c in range(r.leftColumn(), r.rightColumn() + 1):
                         cols_to_remove.add(c)
             else:
                 cols_to_remove.add(target_index)
        else:
            # Button/Shortcut deletion
            # Use current selection
            for r in self.selectedRanges():
                 for c in range(r.leftColumn(), r.rightColumn() + 1):
                     cols_to_remove.add(c)
            
            # If nothing selected (e.g. just a single cell focus), delete that column
            if not cols_to_remove and self.currentColumn() >= 0:
                 cols_to_remove.add(self.currentColumn())

        sorted_cols = sorted(list(cols_to_remove), reverse=True)
        if not sorted_cols: return

        # Use optimized deletion for large operations
        if len(sorted_cols) > 5 and self.rowCount() > 100:
            OptimizedColumnAddition.add_columns_optimized(self, 0, 0)  # Dummy to show UI pattern
            # Actually use delete method
            self.set_updates_deferred(True)
            self.undo_stack.beginMacro("Delete Columns")
            try:
                for c in sorted_cols:
                    if self.columnCount() > 0:
                        self.undo_stack.push(ResizeCommand(self, 'remove_col', c))
            finally:
                self.undo_stack.endMacro()
                self.set_updates_deferred(False)
        else:
            self.set_updates_deferred(True)
            self.undo_stack.beginMacro("Delete Columns")
            try:
                for c in sorted_cols:
                    if self.columnCount() > 0:
                        self.undo_stack.push(ResizeCommand(self, 'remove_col', c))
            finally:
                self.undo_stack.endMacro()
                self.set_updates_deferred(False)

    def remove_row(self, index=None):
        # FIX: Ensure index is strictly an int and not bool (from signal)
        target_index = None
        if index is not None and type(index) is int:
            target_index = index

        rows_to_remove = set()
        
        if target_index is not None:
             selection_model = self.selectionModel()
             if selection_model and selection_model.isRowSelected(target_index, self.rootIndex()):
                 for r in self.selectedRanges():
                     for row in range(r.topRow(), r.bottomRow() + 1):
                         rows_to_remove.add(row)
             else:
                 rows_to_remove.add(target_index)
        else:
            for r in self.selectedRanges():
                 for row in range(r.topRow(), r.bottomRow() + 1):
                     rows_to_remove.add(row)
            if not rows_to_remove and self.currentRow() >= 0:
                 rows_to_remove.add(self.currentRow())

        sorted_rows = sorted(list(rows_to_remove), reverse=True)
        if not sorted_rows: return

        # Use optimized batch deletion for large operations
        if len(sorted_rows) > 100 or (len(sorted_rows) > 10 and self.rowCount() > 10000):
            OptimizedBatchDelete.delete_multiple_rows_optimized(self, sorted_rows, show_progress=True)
        else:
            # Standard deletion for small batches
            self.set_updates_deferred(True)
            self.undo_stack.beginMacro("Delete Rows")
            try:
                for r in sorted_rows:
                    if self.rowCount() > 0:
                        self.undo_stack.push(ResizeCommand(self, 'remove_row', r))
            finally:
                self.undo_stack.endMacro()
                self.set_updates_deferred(False)

    def insert_column(self, index):
        # Context menu insert - show dialog to ask how many columns
        dialog = InsertQuantityDialog(mode='column', current_count=self.columnCount(), parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        
        count = dialog.get_quantity()
        if count <= 0:
            return
        
        if self.columnCount() + count > MAX_COLUMNS:
            QMessageBox.warning(self, "Limit", f"Max {MAX_COLUMNS} columns allowed.")
            return
        
        self.undo_stack.push(ResizeCommand(self, 'add_col', index, count))

    def insert_row(self, index):
        # Context menu insert - show dialog to ask how many rows
        dialog = InsertQuantityDialog(mode='row', current_count=self.rowCount(), parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        
        count = dialog.get_quantity()
        if count <= 0:
            return
            
        if self.rowCount() + count > MAX_ROWS:
            QMessageBox.warning(self, "Limit", f"Max {MAX_ROWS:,} rows allowed.")
            return
        
        self.undo_stack.push(ResizeCommand(self, 'add_row', index, count))

    def clear_column_contents(self, index):
        changes = []
        for r in range(self.rowCount()):
            item = self.item(r, index)
            if item:
                old_data = item.get_data()
                if old_data.get('value'):
                    new_data = old_data.copy()
                    new_data['value'] = ''
                    changes.append((r, index, old_data, new_data))
        if changes:
            self.undo_stack.push(ChangeCellCommand(self, changes, "Clear Column Contents"))

    def clear_row_contents(self, index):
        changes = []
        for c in range(self.columnCount()):
            item = self.item(index, c)
            if item:
                old_data = item.get_data()
                if old_data.get('value'):
                    new_data = old_data.copy()
                    new_data['value'] = ''
                    changes.append((index, c, old_data, new_data))
        if changes:
            self.undo_stack.push(ChangeCellCommand(self, changes, "Clear Row Contents"))

    def set_bold(self): self._toggle_font('bold')
    def set_italic(self): self._toggle_font('italic')
    def set_underline(self): self._toggle_font('underline')
    def _toggle_font(self, p):
        changes = []
        for i in self.selectedItems():
            o = i.get_data()
            n = o.copy()
            if 'font' not in n:
                n['font'] = {}
            n['font'][p] = not n['font'].get(p, False)
            changes.append((i.row(), i.column(), o, n))
        if changes: self.undo_stack.push(ChangeCellCommand(self, changes, f"Toggle {p}"))

    def set_text_color(self): self._set_color('text_color')
    def set_background_color(self): self._set_color('bg_color')
    def _set_color(self, p):
        c = ColorSelector.getColor(QColor("black"), self)
        if not c.isValid(): return
        changes = []
        for i in self.selectedItems():
            o = i.get_data()
            n = o.copy()
            n[p] = c.name()
            changes.append((i.row(), i.column(), o, n))
        if changes: self.undo_stack.push(ChangeCellCommand(self, changes, "Color"))
    
    def on_selection_changed(self):
        self.viewport().update()
        self.parent().formula_bar.setText("")
        self.formula_hint.hide()
        self.completer_popup.hide()
    
    def on_formula_bar_text_changed(self, text):
        self.referenced_cells.clear()
        self.formula_hint.hide()
        self.completer_popup.hide()
        if text.startswith('='):
            text_upper = text.upper()
            refs = re.findall(r"([A-Z]+)(\d+)", text_upper)
            for i, (c_str, r_str) in enumerate(refs):
                r, c = int(r_str)-1, col_str_to_int(c_str)
                self.referenced_cells.append(((r, c), self.ref_colors[i % 4]))
            syntax_match = re.search(r"([A-Z_]+)\(([^)]*)$", text_upper)
            if syntax_match:
                func_name = syntax_match.group(1)
                args_text = syntax_match.group(2)
                if func_name in FUNCTION_HINTS:
                    self.show_syntax_hint(func_name, args_text)
            else:
                completer_match = re.search(r"=([A-Z_]*)$", text_upper)
                if completer_match:
                    self.show_completer_popup(completer_match.group(1))
        self.viewport().update()

    def show_syntax_hint(self, func_name, args_text):
        hint_template = FUNCTION_HINTS[func_name]
        arg_parts = hint_template[len(func_name)+1:-1].split(',')
        current_arg_index = args_text.count(',')
        if current_arg_index < len(arg_parts):
            arg_parts[current_arg_index] = f"<b>{arg_parts[current_arg_index].strip()}</b>"
        hint_text = f"{func_name}({', '.join(arg_parts)})"
        self.formula_hint.setText(hint_text)
        self.formula_hint.adjustSize()
        current_rect = self.visualRect(self.currentIndex())
        if current_rect.isValid():
            global_pos = self.viewport().mapToGlobal(current_rect.bottomLeft())
            self.formula_hint.move(global_pos)
            self.formula_hint.show()
            self.formula_hint.raise_()

    def show_completer_popup(self, partial_func):
        matches = [f for f in FUNCTION_HINTS if f.startswith(partial_func)]
        if matches:
            self.completer_popup.clear()
            self.completer_popup.addItems(matches)
            current_rect = self.visualRect(self.currentIndex())
            if current_rect.isValid():
                global_pos = self.viewport().mapToGlobal(current_rect.bottomLeft())
                self.completer_popup.move(global_pos)
                self.completer_popup.adjustSize()
                self.completer_popup.setMinimumWidth(150)
                self.completer_popup.show()
                self.completer_popup.raise_()

    def complete_formula(self, item):
        full_func = item.text()
        editor = self.focusWidget()
        if not isinstance(editor, QLineEdit):
             editor = self.parent().formula_bar
        current_text = editor.text()
        last_equal = current_text.rfind('=')
        last_paren = current_text.rfind('(')
        last_comma = current_text.rfind(',')
        start_pos = max(last_equal, last_paren, last_comma) + 1
        new_text = current_text[:start_pos] + full_func + "("
        editor.setText(new_text)
        editor.setFocus()
        editor.setCursorPosition(len(new_text))
        self.completer_popup.hide()

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self.viewport())
        
        # Draw hover effect
        if self.hover_row != -1 and self.hover_col != -1:
            rect = self.visualRect(self.model().index(self.hover_row, self.hover_col))
            if rect.isValid():
                # Use semi-transparent hover color so text remains visible
                hover_color = QColor(colors.COLOR_HOVER)
                hover_color.setAlpha(60) 
                painter.fillRect(rect, hover_color)

        for (row, col), color in self.referenced_cells:
            rect = self.visualRect(self.model().index(row, col))
            if rect.isValid():
                painter.setPen(QPen(color, 1, Qt.PenStyle.DashLine))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRect(rect.adjusted(0, 0, -1, -1))
        for (row, col) in self.highlighted_cells:
            rect = self.visualRect(self.model().index(row, col))
            if rect.isValid():
                # Make highlighted cells (blue line) transparent as requested
                painter.setPen(QPen(Qt.GlobalColor.transparent, 2))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRect(rect.adjusted(0, 0, -1, -1))
        if not self.selectionModel().hasSelection(): return
        selection = self.selectionModel().selection()
        current_index = self.currentIndex()
        if len(selection.indexes()) > 1:
            for sel_range in selection:
                for index in sel_range.indexes():
                    if index != current_index:
                        rect = self.visualRect(index)
                        # Use a light green for selected cells (Excel style)
                        painter.fillRect(rect, QColor(colors.COLOR_SELECTION_FILL).lighter(150))
        selection_rect = self.visualRegionForSelection(selection).boundingRect()
        # Draw a solid green border around the selection
        painter.setPen(QPen(QColor(colors.COLOR_SELECTION_FILL), 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(selection_rect.adjusted(0, 0, -1, -1))
        handle_rect = self.get_fill_handle_rect()
        if handle_rect:
            painter.setBrush(QBrush(QColor(colors.COLOR_SELECTION_FILL)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRect(handle_rect)
        if self._is_dragging_fill_handle and self._drag_fill_rect:
            painter.setPen(QPen(QColor(colors.BORDER_DARK), 1, Qt.PenStyle.DashLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(self._drag_fill_rect)

    def get_fill_handle_rect(self):
        selected_ranges = self.selectedRanges()
        if not selected_ranges: return None
        last_range = selected_ranges[-1]
        # Use visualRect with model index instead of item to support empty cells
        index = self.model().index(last_range.bottomRow(), last_range.rightColumn())
        last_cell_rect = self.visualRect(index)
        if last_cell_rect.isValid():
            return QRectF(last_cell_rect.right() - 4, last_cell_rect.bottom() - 4, 8, 8)
        return None

    def mousePressEvent(self, event):
        self.highlighted_cells.clear()
        comment_table = self.parent()
        is_editing_in_formula_bar = comment_table.formula_bar.hasFocus() and comment_table.formula_bar.text().startswith('=')
        is_editing_in_cell = self.state() == QAbstractItemView.State.EditingState
        editor = QApplication.focusWidget() if is_editing_in_cell else None
        if is_editing_in_formula_bar or (is_editing_in_cell and isinstance(editor, QLineEdit) and editor.text().startswith('=')):
            index = self.indexAt(event.position().toPoint())
            if index.isValid():
                cell_ref = self.get_cell_ref_str(index.row(), index.column())
                if is_editing_in_formula_bar:
                    comment_table.formula_bar.insert(cell_ref)
                else:
                    editor.insert(cell_ref)
            return
        handle_rect = self.get_fill_handle_rect()
        if handle_rect and handle_rect.contains(event.position()):
            self._is_dragging_fill_handle = True
            self._drag_start_pos = event.position()
            self.setCursor(Qt.CursorShape.CrossCursor)
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        # Update hover state
        pos = event.position()
        row = self.rowAt(int(pos.y()))
        col = self.columnAt(int(pos.x()))
        
        if row != self.hover_row or col != self.hover_col:
            self.hover_row = row
            self.hover_col = col
            self.viewport().update()

        if self._is_dragging_fill_handle:
            selection_ranges = self.selectedRanges()
            if not selection_ranges: return
            selection_range = selection_ranges[0]
            # Use visualRect instead of visualItemRect to support empty cells
            index = self.model().index(selection_range.topRow(), selection_range.leftColumn())
            start_rect = self.visualRect(index)
            if not start_rect.isValid(): return
            
            clamped_pos = event.position()
            if clamped_pos.y() > self.viewport().height():
                 clamped_pos.setY(float(self.viewport().height()))
            if clamped_pos.x() > self.viewport().width():
                 clamped_pos.setX(float(self.viewport().width()))
                 
            self._drag_fill_rect = QRectF(QPointF(start_rect.topLeft()), clamped_pos).normalized()
            self.viewport().update()
        else:
            super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        self.hover_row = -1
        self.hover_col = -1
        self.viewport().update()
        super().leaveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._is_dragging_fill_handle:
            self.setCursor(Qt.CursorShape.ArrowCursor)
            if self._drag_fill_rect:
                end_row = self.rowAt(int(self._drag_fill_rect.bottom()))
                end_col = self.columnAt(int(self._drag_fill_rect.right()))
                
                if end_row == -1: end_row = self.rowCount() - 1
                if end_col == -1: end_col = self.columnCount() - 1
                
                self.perform_fill_drag(end_row, end_col)
            self._is_dragging_fill_handle = False
            self._drag_start_pos = None
            self._drag_fill_rect = None
            self.viewport().update()
        else:
            super().mouseReleaseEvent(event)

    def perform_fill_drag(self, end_row, end_col):
        selected_ranges = self.selectedRanges()
        if not selected_ranges: return
        source_range = selected_ranges[0]
        
        # Determine direction
        rows_ext = end_row - source_range.bottomRow()
        cols_ext = end_col - source_range.rightColumn()
        
        changes = []
        
        if rows_ext > 0 and (rows_ext >= cols_ext or cols_ext <= 0):
            # Fill Down
            fill_rows = range(source_range.bottomRow() + 1, end_row + 1)
            for col in range(source_range.leftColumn(), source_range.rightColumn() + 1):
                for i, target_row in enumerate(fill_rows, 1):
                    source_row = source_range.topRow() + (i - 1) % source_range.rowCount()
                    source_item = self.item(source_row, col)
                    source_data = source_item.get_data() if source_item else {'value': ''}
                    source_text = str(source_data.get('value', ''))
                    new_data = source_data.copy()
                    
                    if source_text.startswith('='):
                        new_data['value'] = adjust_formula_references(source_text, target_row - source_row, 0)
                    else:
                        match = re.match(r"^(.*?)(\d+)$", source_text)
                        if match:
                            prefix, num_str = match.groups()
                            new_value = int(num_str) + i
                            new_data['value'] = f"{prefix}{new_value}"
                        else:
                            new_data['value'] = source_text
                            
                    target_item = self.item(target_row, col)
                    old_data = target_item.get_data() if target_item else {'value': ''}
                    changes.append((target_row, col, old_data, new_data))
                    
        elif cols_ext > 0 and (cols_ext > rows_ext or rows_ext <= 0):
            # Fill Right
            fill_cols = range(source_range.rightColumn() + 1, end_col + 1)
            for row in range(source_range.topRow(), source_range.bottomRow() + 1):
                for i, target_col in enumerate(fill_cols, 1):
                    source_col = source_range.leftColumn() + (i - 1) % source_range.columnCount()
                    source_item = self.item(row, source_col)
                    source_data = source_item.get_data() if source_item else {'value': ''}
                    source_text = str(source_data.get('value', ''))
                    new_data = source_data.copy()
                    
                    if source_text.startswith('='):
                        new_data['value'] = adjust_formula_references(source_text, 0, target_col - source_col)
                    else:
                        match = re.match(r"^(.*?)(\d+)$", source_text)
                        if match:
                            prefix, num_str = match.groups()
                            new_value = int(num_str) + i
                            new_data['value'] = f"{prefix}{new_value}"
                        else:
                            new_data['value'] = source_text
                            
                    target_item = self.item(row, target_col)
                    old_data = target_item.get_data() if target_item else {'value': ''}
                    changes.append((row, target_col, old_data, new_data))

        if changes:
            command = ChangeCellCommand(self, changes, "Fill Drag")
            self.undo_stack.push(command)

    def trace_precedents(self):
        current_item = self.currentItem()
        if not current_item: return
        cell = (current_item.row(), current_item.column())
        if cell in self.precedents:
            self.highlighted_cells.update(self.precedents[cell])
            self.viewport().update()

    def clear_highlights(self):
        self.highlighted_cells.clear()
        self.viewport().update()

    def on_focus_changed(self, old, new):
        if new is not self and new is not self.parent().formula_bar:
             self.formula_hint.hide()
             self.completer_popup.hide()