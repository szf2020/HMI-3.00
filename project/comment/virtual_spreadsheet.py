# project\comment\virtual_spreadsheet.py
"""
Advanced Virtual Viewport Spreadsheet Implementation
Efficiently handles 10,000+ rows/columns with intelligent rendering.
Only visible cells are rendered, background operations are async.
"""

import collections
import re
import threading
from typing import Dict, List, Tuple, Set, Any
from dataclasses import dataclass
from PySide6.QtWidgets import (
    QAbstractScrollArea, QAbstractItemView, QHeaderView, QMenu, 
    QMessageBox, QApplication, QLabel, QLineEdit, QWidget, QVBoxLayout
)
from PySide6.QtCore import (
    Qt, QRect, QSize, QPoint, Signal, QTimer, QMutex, 
    QThread, Slot, QEvent
)
from PySide6.QtGui import (
    QPainter, QPen, QColor, QBrush, QFont, QIcon, QCursor, QUndoStack, QUndoCommand
)
from styles import colors
from .comment_utils import FormulaParser, FUNCTION_HINTS, adjust_formula_references, col_str_to_int, col_int_to_str


@dataclass
class CellData:
    """Represents a single cell with its properties."""
    value: str = ''
    font: Dict[str, bool] = None
    text_color: str = None
    bg_color: str = None
    
    def __post_init__(self):
        if self.font is None:
            self.font = {'bold': False, 'italic': False, 'underline': False}
    
    def to_dict(self):
        return {
            'value': self.value,
            'font': self.font.copy(),
            'text_color': self.text_color,
            'bg_color': self.bg_color
        }
    
    @staticmethod
    def from_dict(data):
        if isinstance(data, dict):
            return CellData(
                value=str(data.get('value', '')),
                font=data.get('font', {'bold': False, 'italic': False, 'underline': False}).copy(),
                text_color=data.get('text_color'),
                bg_color=data.get('bg_color')
            )
        return CellData()


class LazyDataStore:
    """Efficient data storage with lazy loading and memory management."""
    
    def __init__(self, initial_rows=100, initial_cols=10):
        self._data: Dict[Tuple[int, int], CellData] = {}
        self.row_count = initial_rows
        self.col_count = initial_cols
        self._lock = QMutex()
        self._dirty_cells: Set[Tuple[int, int]] = set()
        self._cached_rows: Dict[int, List[CellData]] = {}
    
    def get_cell(self, row: int, col: int) -> CellData:
        """Get cell data with lazy initialization."""
        if not (0 <= row < self.row_count and 0 <= col < self.col_count):
            return CellData()
        
        key = (row, col)
        if key not in self._data:
            self._data[key] = CellData()
        return self._data[key]
    
    def set_cell(self, row: int, col: int, data: CellData):
        """Set cell data and mark as dirty."""
        if 0 <= row < self.row_count and 0 <= col < self.col_count:
            self._lock.lock()
            try:
                self._data[(row, col)] = data
                self._dirty_cells.add((row, col))
                # Invalidate cached row
                if row in self._cached_rows:
                    del self._cached_rows[row]
            finally:
                self._lock.unlock()
    
    def get_row(self, row: int) -> List[CellData]:
        """Get entire row (cached)."""
        if row not in self._cached_rows:
            self._cached_rows[row] = [self.get_cell(row, c) for c in range(self.col_count)]
        return self._cached_rows[row]
    
    def get_visible_range(self, start_row: int, end_row: int, start_col: int, end_col: int) -> Dict:
        """Get only visible cells efficiently."""
        visible = {}
        for row in range(max(0, start_row), min(self.row_count, end_row + 1)):
            for col in range(max(0, start_col), min(self.col_count, end_col + 1)):
                key = (row, col)
                if key in self._data:
                    visible[key] = self._data[key]
        return visible
    
    def insert_row(self, index: int, count: int = 1):
        """Insert rows efficiently by shifting data."""
        self._lock.lock()
        try:
            # Create new keys for rows from end to insertion point
            new_data = {}
            for (row, col), cell in list(self._data.items()):
                if row >= index:
                    new_data[(row + count, col)] = cell
                else:
                    new_data[(row, col)] = cell
            self._data = new_data
            self.row_count += count
            self._cached_rows.clear()
        finally:
            self._lock.unlock()
    
    def insert_column(self, index: int, count: int = 1):
        """Insert columns efficiently by shifting data."""
        self._lock.lock()
        try:
            new_data = {}
            for (row, col), cell in list(self._data.items()):
                if col >= index:
                    new_data[(row, col + count)] = cell
                else:
                    new_data[(row, col)] = cell
            self._data = new_data
            self.col_count += count
            self._cached_rows.clear()
        finally:
            self._lock.unlock()
    
    def remove_row(self, index: int) -> List[CellData]:
        """Remove row and return data for undo."""
        self._lock.lock()
        try:
            saved = self.get_row(index)
            new_data = {}
            for (row, col), cell in list(self._data.items()):
                if row == index:
                    continue
                elif row > index:
                    new_data[(row - 1, col)] = cell
                else:
                    new_data[(row, col)] = cell
            self._data = new_data
            self.row_count = max(0, self.row_count - 1)
            self._cached_rows.clear()
            return saved
        finally:
            self._lock.unlock()
    
    def remove_column(self, index: int) -> List[CellData]:
        """Remove column and return data for undo."""
        self._lock.lock()
        try:
            saved = [self.get_cell(r, index) for r in range(self.row_count)]
            new_data = {}
            for (row, col), cell in list(self._data.items()):
                if col == index:
                    continue
                elif col > index:
                    new_data[(row, col - 1)] = cell
                else:
                    new_data[(row, col)] = cell
            self._data = new_data
            self.col_count = max(0, self.col_count - 1)
            self._cached_rows.clear()
            return saved
        finally:
            self._lock.unlock()
    
    def get_all_data(self) -> List[List[Dict]]:
        """Export all data (for saving)."""
        result = []
        for row in range(self.row_count):
            row_data = []
            for col in range(self.col_count):
                cell = self.get_cell(row, col)
                row_data.append(cell.to_dict())
            result.append(row_data)
        return result
    
    def load_all_data(self, data: List[List[Dict]]):
        """Import all data (for loading)."""
        self._lock.lock()
        try:
            self._data.clear()
            self._cached_rows.clear()
            for row, row_data in enumerate(data):
                for col, cell_data in enumerate(row_data):
                    if cell_data and cell_data.get('value'):
                        self._data[(row, col)] = CellData.from_dict(cell_data)
            self.row_count = len(data)
            self.col_count = len(data[0]) if data else 0
        finally:
            self._lock.unlock()


class BackgroundCalculationThread(QThread):
    """Background thread for formula evaluation and saving."""
    
    progress = Signal(str)
    finished_calculation = Signal()
    
    def __init__(self, spreadsheet, cells_to_evaluate):
        super().__init__()
        self.spreadsheet = spreadsheet
        self.cells_to_evaluate = cells_to_evaluate
    
    def run(self):
        """Run formula evaluation in background."""
        total = len(self.cells_to_evaluate)
        for idx, (row, col) in enumerate(self.cells_to_evaluate):
            if idx % 100 == 0:
                self.progress.emit(f"Evaluating: {idx}/{total}")
            try:
                self.spreadsheet._evaluate_cell_internal(row, col)
            except Exception:
                pass
        self.finished_calculation.emit()


class VirtualSpreadsheet(QAbstractScrollArea):
    """
    High-performance virtual viewport spreadsheet.
    Only renders visible rows/columns. Perfect for 10,000+ rows.
    """
    
    currentCellChanged = Signal(int, int, int, int)  # newRow, newCol, oldRow, oldCol
    cellClicked = Signal(int, int)
    
    def __init__(self, parent=None, comment_service=None, comment_number=None):
        super().__init__(parent)
        self.comment_service = comment_service
        self.comment_number = comment_number
        
        # Data storage
        self.data_store = LazyDataStore()
        
        # Rendering
        self.cell_width = 100
        self.cell_height = 24
        self.header_height = 24
        self.header_width = 50
        self.viewport_width = 0
        self.viewport_height = 0
        
        # Selection
        self.selected_ranges = []
        self.current_row = 0
        self.current_col = 0
        self.hover_row = -1
        self.hover_col = -1
        self.selection_mode = QAbstractItemView.SelectionMode.ExtendedSelection
        
        # Performance
        self.undo_stack = QUndoStack(self)
        self._updates_deferred = False
        self._render_timer = QTimer()
        self._render_timer.setSingleShot(True)
        self._render_timer.timeout.connect(self.viewport().update)
        
        # Dependency tracking
        self.dependents = collections.defaultdict(set)
        self.precedents = collections.defaultdict(set)
        
        # Background calculation
        self._calc_thread = None
        self._pending_saves = []
        
        # Setup UI
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.viewport().setMouseTracking(True)
        
        # Connect scrollbar signals
        self.verticalScrollBar().valueChanged.connect(self._on_scroll)
        self.horizontalScrollBar().valueChanged.connect(self._on_scroll)
        
        # Load data
        self.load_data_from_service()
        
        # Setup delayed save
        self._save_timer = QTimer()
        self._save_timer.setSingleShot(True)
        self._save_timer.timeout.connect(self._execute_pending_saves)
        self._save_timer.setInterval(2000)  # Save after 2s of inactivity
    
    def rowCount(self) -> int:
        """Return number of rows."""
        return self.data_store.row_count
    
    def columnCount(self) -> int:
        """Return number of columns."""
        return self.data_store.col_count
    
    def setRowCount(self, count: int):
        """Resize to specified row count."""
        if count > self.data_store.row_count:
            self.data_store.insert_row(self.data_store.row_count, count - self.data_store.row_count)
        elif count < self.data_store.row_count:
            while self.data_store.row_count > count:
                self.data_store.remove_row(self.data_store.row_count - 1)
        self.viewport().update()
    
    def setColumnCount(self, count: int):
        """Resize to specified column count."""
        if count > self.data_store.col_count:
            self.data_store.insert_column(self.data_store.col_count, count - self.data_store.col_count)
        elif count < self.data_store.col_count:
            while self.data_store.col_count > count:
                self.data_store.remove_column(self.data_store.col_count - 1)
        self.viewport().update()
    
    def item(self, row: int, col: int):
        """Get item (compatibility with QTableWidget)."""
        return self.data_store.get_cell(row, col)
    
    def setItem(self, row: int, col: int, data: 'CellData'):
        """Set item data."""
        self.data_store.set_cell(row, col, data)
        self._schedule_save()
    
    def _get_visible_range(self) -> Tuple[int, int, int, int]:
        """Calculate visible row and column range."""
        v_scroll = self.verticalScrollBar().value()
        h_scroll = self.horizontalScrollBar().value()
        
        start_row = max(0, v_scroll // self.cell_height)
        end_row = min(self.data_store.row_count - 1, 
                     (v_scroll + self.viewport().height()) // self.cell_height + 1)
        
        start_col = max(0, h_scroll // self.cell_width)
        end_col = min(self.data_store.col_count - 1,
                     (h_scroll + self.viewport().width()) // self.cell_width + 1)
        
        return start_row, end_row, start_col, end_col
    
    def resizeEvent(self, event):
        """Handle viewport resize."""
        super().resizeEvent(event)
        self.viewport_width = self.viewport().width()
        self.viewport_height = self.viewport().height()
        self._update_scrollbars()
    
    def _update_scrollbars(self):
        """Update scrollbar ranges."""
        total_height = self.data_store.row_count * self.cell_height
        total_width = self.data_store.col_count * self.cell_width
        
        self.verticalScrollBar().setRange(0, max(0, total_height - self.viewport_height))
        self.horizontalScrollBar().setRange(0, max(0, total_width - self.viewport_width))
        
        self.verticalScrollBar().setPageStep(self.viewport_height)
        self.horizontalScrollBar().setPageStep(self.viewport_width)
    
    def _on_scroll(self):
        """Handle scroll events - only re-render visible area."""
        self._render_timer.stop()
        self._render_timer.start(16)  # Throttle to ~60 FPS
    
    def paintEvent(self, event):
        """Render only visible cells."""
        painter = QPainter(self.viewport())
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Fill background
        painter.fillRect(self.viewport().rect(), QColor(colors.BG_SPREADSHEET))
        
        v_scroll = self.verticalScrollBar().value()
        h_scroll = self.horizontalScrollBar().value()
        
        start_row, end_row, start_col, end_col = self._get_visible_range()
        
        # Render headers and cells
        self._render_headers(painter, h_scroll, start_col, end_col)
        self._render_cells(painter, v_scroll, h_scroll, start_row, end_row, start_col, end_col)
    
    def _render_headers(self, painter, h_scroll, start_col, end_col):
        """Render column headers."""
        painter.fillRect(0, 0, self.viewport().width(), self.header_height, QColor(colors.BG_DARK_QUATERNARY))
        painter.setPen(QPen(QColor(colors.BORDER_MEDIUM)))
        
        # Render column headers
        for col in range(start_col, end_col + 1):
            x = col * self.cell_width - h_scroll
            painter.drawLine(x + self.cell_width, 0, x + self.cell_width, self.header_height)
            
            col_label = col_int_to_str(col)
            painter.setPen(QPen(QColor(colors.COLOR_HEADER_TEXT)))
            painter.drawText(x + 5, 0, self.cell_width - 10, self.header_height, 
                           Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter, col_label)
            painter.setPen(QPen(QColor(colors.BORDER_MEDIUM)))
    
    def _render_cells(self, painter, v_scroll, h_scroll, start_row, end_row, start_col, end_col):
        """Render visible cells efficiently."""
        # Render row headers and cells together
        for row in range(start_row, end_row + 1):
            y = row * self.cell_height - v_scroll
            
            # Render row header
            painter.fillRect(-h_scroll, y, self.header_width, self.cell_height, QColor(colors.BG_DARK_QUATERNARY))
            painter.setPen(QPen(QColor(colors.BORDER_MEDIUM)))
            painter.drawLine(-h_scroll, y + self.cell_height, self.viewport().width(), y + self.cell_height)
            painter.setPen(QPen(QColor(colors.TEXT_SECONDARY)))
            painter.drawText(-h_scroll + 5, y, self.header_width - 10, self.cell_height,
                           Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter, str(row + 1))
            
            # Render cells
            for col in range(start_col, end_col + 1):
                x = col * self.cell_width - h_scroll
                cell = self.data_store.get_cell(row, col)
                self._render_cell(painter, x, y, cell, row, col)
    
    def _render_cell(self, painter, x, y, cell: CellData, row: int, col: int):
        """Render a single cell."""
        # Cell background
        bg_color = QColor(cell.bg_color) if cell.bg_color else QColor(colors.BG_SPREADSHEET)
        
        # Hover effect
        if row == self.hover_row and col == self.hover_col:
            bg_color = QColor(colors.COLOR_HOVER)
            
        painter.fillRect(x, y, self.cell_width, self.cell_height, bg_color)
        
        # Cell border
        painter.setPen(QPen(QColor(colors.BORDER_MEDIUM)))
        painter.drawLine(x + self.cell_width, y, x + self.cell_width, y + self.cell_height)
        
        # Selection highlight
        if self._is_cell_selected(row, col):
            # Make selection background transparent as requested
            # painter.fillRect(x, y, self.cell_width - 1, self.cell_height - 1, QColor(colors.COLOR_SELECTION_HIGHLIGHT_ALT))
            
            # Make selection border transparent as requested
            painter.setPen(QPen(Qt.GlobalColor.transparent, 2))
            painter.drawRect(x, y, self.cell_width - 1, self.cell_height - 1)
        
        # Cell text
        font = QFont()
        if cell.font:
            font.setBold(cell.font.get('bold', False))
            font.setItalic(cell.font.get('italic', False))
            font.setUnderline(cell.font.get('underline', False))
        painter.setFont(font)
        
        text_color = QColor(cell.text_color) if cell.text_color else QColor(colors.TEXT_SECONDARY)
        painter.setPen(QPen(text_color))
        painter.drawText(x + 3, y, self.cell_width - 6, self.cell_height,
                        Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, str(cell.value))
    
    def _is_cell_selected(self, row: int, col: int) -> bool:
        """Check if cell is selected."""
        for r_start, r_end, c_start, c_end in self.selected_ranges:
            if r_start <= row <= r_end and c_start <= col <= c_end:
                return True
        return row == self.current_row and col == self.current_col
    
    def mousePressEvent(self, event):
        """Handle mouse clicks."""
        v_scroll = self.verticalScrollBar().value()
        h_scroll = self.horizontalScrollBar().value()
        
        col = (event.position().x() + h_scroll) // self.cell_width
        row = (event.position().y() + v_scroll) // self.cell_height
        
        if row < 0 or col < 0:
            return
        
        self.current_row = row
        self.current_col = col
        self.cellClicked.emit(row, col)
        self.viewport().update()
    
    def mouseMoveEvent(self, event):
        """Handle mouse move for selection and hover."""
        v_scroll = self.verticalScrollBar().value()
        h_scroll = self.horizontalScrollBar().value()
        
        col = int((event.position().x() + h_scroll) // self.cell_width)
        row = int((event.position().y() + v_scroll) // self.cell_height)
        
        # Update hover state
        if row != self.hover_row or col != self.hover_col:
            self.hover_row = row
            self.hover_col = col
            self.viewport().update()
            
        if event.buttons() & Qt.MouseButton.LeftButton:
            if row >= 0 and col >= 0:
                self.current_row = row
                self.current_col = col
                self.viewport().update()
    
    def leaveEvent(self, event):
        """Clear hover state when mouse leaves."""
        self.hover_row = -1
        self.hover_col = -1
        self.viewport().update()
        super().leaveEvent(event)
    
    def wheelEvent(self, event):
        """Handle mouse wheel scrolling."""
        delta = event.angleDelta().y()
        current_value = self.verticalScrollBar().value()
        new_value = current_value - delta
        self.verticalScrollBar().setValue(new_value)
    
    def load_data_from_service(self):
        """Load data from comment service."""
        if not self.comment_service:
            return
        
        table_data = self.comment_service.get_table_data(self.comment_number)
        if table_data:
            self.data_store.load_all_data(table_data)
            self._update_scrollbars()
            self.viewport().update()
            self._schedule_evaluation()
    
    def _schedule_evaluation(self):
        """Schedule background formula evaluation."""
        cells_with_formulas = []
        for row in range(min(1000, self.data_store.row_count)):  # Start with first 1000
            for col in range(self.data_store.col_count):
                cell = self.data_store.get_cell(row, col)
                if cell.value.startswith('='):
                    cells_with_formulas.append((row, col))
        
        if cells_with_formulas:
            self._calc_thread = BackgroundCalculationThread(self, cells_with_formulas)
            self._calc_thread.finished_calculation.connect(self.viewport().update)
            self._calc_thread.start()
    
    def _evaluate_cell_internal(self, row: int, col: int):
        """Evaluate single cell (thread-safe)."""
        cell = self.data_store.get_cell(row, col)
        if not cell.value.startswith('='):
            return
        
        try:
            parser = FormulaParser(self, (row, col))
            result = parser.evaluate(cell.value[1:])
            
            # Format result
            if isinstance(result, bool):
                display_value = str(result).upper()
            elif isinstance(result, float) and result.is_integer():
                display_value = str(int(result))
            else:
                display_value = f"{result:.2f}" if isinstance(result, float) else str(result)
            
            cell.value = display_value
        except Exception:
            cell.value = "#ERROR"
    
    def _schedule_save(self):
        """Defer saving to batch multiple operations."""
        self._save_timer.stop()
        self._save_timer.start()
    
    def _execute_pending_saves(self):
        """Save all pending changes to service."""
        if self.comment_service:
            data = self.data_store.get_all_data()
            self.comment_service.update_table_data(self.comment_number, data)
    
    def set_updates_deferred(self, state: bool):
        """Control batch updates."""
        self._updates_deferred = state
        if not state:
            self.viewport().update()
            self._schedule_save()
            self._schedule_evaluation()
    
    def add_row(self):
        """Add row efficiently."""
        self.data_store.insert_row(self.data_store.row_count, 1)
        self._update_scrollbars()
        self._schedule_save()
        self.viewport().update()
    
    def add_column(self):
        """Add column efficiently."""
        if self.data_store.col_count >= 30:
            QMessageBox.warning(self, "Limit", "Max 30 columns allowed.")
            return
        
        self.data_store.insert_column(self.data_store.col_count, 1)
        self._update_scrollbars()
        self._schedule_save()
        self.viewport().update()
    
    def remove_row(self, index: int = None):
        """Remove row(s) with efficient batch operation."""
        rows_to_remove = set()
        
        if index is not None and isinstance(index, int):
            rows_to_remove.add(index)
        else:
            rows_to_remove.add(self.current_row)
        
        if not rows_to_remove:
            return
        
        self.set_updates_deferred(True)
        try:
            for row in sorted(rows_to_remove, reverse=True):
                if row < self.data_store.row_count:
                    self.data_store.remove_row(row)
        finally:
            self.set_updates_deferred(False)
        
        self._update_scrollbars()
        self.viewport().update()
    
    def remove_column(self, index: int = None):
        """Remove column(s) with efficient batch operation."""
        cols_to_remove = set()
        
        if index is not None and isinstance(index, int):
            cols_to_remove.add(index)
        else:
            cols_to_remove.add(self.current_col)
        
        if not cols_to_remove:
            return
        
        self.set_updates_deferred(True)
        try:
            for col in sorted(cols_to_remove, reverse=True):
                if col < self.data_store.col_count:
                    self.data_store.remove_column(col)
        finally:
            self.set_updates_deferred(False)
        
        self._update_scrollbars()
        self.viewport().update()
