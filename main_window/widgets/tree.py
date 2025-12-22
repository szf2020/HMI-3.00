# main_window\widgets\tree.py
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem, QAbstractItemView
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtCore import Qt
from pathlib import Path
from typing import Optional
from styles import stylesheets

class CustomTreeWidget(QTreeWidget):
    """
    A custom QTreeWidget with custom expand/collapse icons from icon-park-solid.
    Includes visual indicators for parent-child relationships, multi-column support,
    and enhanced selection/styling capabilities matching tag table functionality.
    """
    def __init__(self, parent=None):
        """
        Initializes the CustomTreeWidget with custom icons and styling.
        """
        super().__init__(parent)
        self.setHeaderHidden(True)
        
        # Get the resource path for icons
        self.icon_path = Path(__file__).parent.parent / "resources" / "icons"
        
        # Load expand/collapse icons with proper path formatting
        expand_icon_path = str(self.icon_path / "icon-park-solid-add.svg").replace("\\", "/")
        collapse_icon_path = str(self.icon_path / "icon-park-solid-subtract.svg").replace("\\", "/")
        
        # Load branch line SVG icons
        vline_path = str(self.icon_path / "branch-vline.svg").replace("\\", "/")
        branch_more_path = str(self.icon_path / "branch-more.svg").replace("\\", "/")
        branch_end_path = str(self.icon_path / "branch-end.svg").replace("\\", "/")
        
        # Configure selection mode and row appearance
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setAlternatingRowColors(False)  # Disable for cleaner branch lines
        self.setRootIsDecorated(True)
        
        # Set indentation for proper branch line display
        self.setIndentation(24)  # Proper spacing for branch lines
        
        # Enable uniform row heights for consistent line drawing
        self.setUniformRowHeights(True)
        
        # Set custom stylesheet with branch styling using icon paths
        # Store paths for later use by subclasses
        self._expand_icon_path = expand_icon_path
        self._collapse_icon_path = collapse_icon_path
        self._vline_path = vline_path
        self._branch_more_path = branch_more_path
        self._branch_end_path = branch_end_path
        
        # Apply default stylesheet (can be overridden by subclasses)
        self._apply_default_stylesheet(expand_icon_path, collapse_icon_path, 
                                        vline_path, branch_more_path, branch_end_path)
        
        # Connect itemExpanded and itemCollapsed signals
        self.itemExpanded.connect(self._on_item_expanded)
        self.itemCollapsed.connect(self._on_item_collapsed)
        
        # Setup context menu support
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._on_context_menu)
    
    def mousePressEvent(self, event):
        """
        Override mouse press event to prevent selection when clicking on branch lines.
        """
        if event.button() == Qt.MouseButton.LeftButton:
            index = self.indexAt(event.pos())
            if index.isValid() and index.column() == 0:
                # Get the visual rectangle of the item (content area)
                rect = self.visualRect(index)
                # If the click is to the left of the content area, it's in the branch area
                if event.pos().x() < rect.left():
                    # Toggle expansion if it's a parent item
                    if self.model().hasChildren(index):
                        self.setExpanded(index, not self.isExpanded(index))
                    # Return without calling super() to prevent selection
                    return
        
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        """
        Override mouse double click event to prevent selection/actions when clicking on branch lines.
        """
        if event.button() == Qt.MouseButton.LeftButton:
            index = self.indexAt(event.pos())
            if index.isValid() and index.column() == 0:
                rect = self.visualRect(index)
                if event.pos().x() < rect.left():
                    # Return without calling super() to prevent selection and itemDoubleClicked signal
                    return
        
        super().mouseDoubleClickEvent(event)

    def _apply_default_stylesheet(self, expand_icon_path, collapse_icon_path,
                                   vline_path="", branch_more_path="", branch_end_path=""):
        """Apply the default stylesheet. Can be overridden by subclasses."""
        stylesheet = stylesheets.get_project_tree_stylesheet(
            expand_icon_path, collapse_icon_path, vline_path, branch_more_path, branch_end_path)
        self.setStyleSheet(stylesheet)
    
    def _on_context_menu(self, position):
        """Handle context menu request. Override in subclasses for custom menus."""
        pass
    
    def setup_columns(self, column_count: int, headers: list):
        """
        Setup multiple columns with headers.
        
        Args:
            column_count: Number of columns
            headers: List of header labels
        """
        self.setColumnCount(column_count)
        self.setHeaderLabels(headers)
        self.setHeaderHidden(False)
    
    def get_column_count(self) -> int:
        """Get the number of columns in the tree."""
        return self.columnCount()
    
    def set_selection_mode(self, mode=QAbstractItemView.SelectionMode.ExtendedSelection):
        """
        Set the selection mode for the tree.
        
        Args:
            mode: Selection mode (default: ExtendedSelection for multi-select)
        """
        self.setSelectionMode(mode)
    
    def enable_alternating_rows(self, enable: bool = True):
        """
        Enable or disable alternating row colors.
        
        Args:
            enable: Whether to show alternating row colors
        """
        self.setAlternatingRowColors(enable)
    
    def enable_root_decoration(self, enable: bool = True):
        """
        Enable or disable root item decoration.
        
        Args:
            enable: Whether to show root item decoration
        """
        self.setRootIsDecorated(enable)
    
    def _load_icon(self, icon_name: str) -> QIcon:
        """
        Load an icon from the resources folder.
        
        Args:
            icon_name: Name of the icon file (e.g., 'icon-park-solid-add.svg')
            
        Returns:
            QIcon object, or empty icon if not found
        """
        icon_path = self.icon_path / icon_name
        if icon_path.exists():
            return QIcon(str(icon_path))
        else:
            print(f"Warning: Icon not found at {icon_path}")
            return QIcon()
    
    def add_item(self, parent: Optional[QTreeWidgetItem], text: str, icon: Optional[QIcon] = None, is_parent: bool = False) -> QTreeWidgetItem:
        """
        Add an item to the tree with proper parent-child hierarchy indication.
        
        Args:
            parent: Parent QTreeWidgetItem or None for root items
            text: Text label for the item
            icon: Optional QIcon for the item
            is_parent: Whether this item can have children (affects icon display)
            
        Returns:
            The created QTreeWidgetItem
        """
        item = QTreeWidgetItem()
        item.setText(0, text)
        
        # Set icon if provided
        if icon:
            item.setIcon(0, icon)
        
        # Mark as parent if needed
        item.setData(0, Qt.ItemDataRole.UserRole, is_parent)
        
        # Add to parent or root
        if parent:
            parent.addChild(item)
        else:
            self.addTopLevelItem(item)
        
        return item
    
    def add_multi_column_item(self, parent: Optional[QTreeWidgetItem], texts: list, icon: Optional[QIcon] = None) -> QTreeWidgetItem:
        """
        Add an item with multiple columns.
        
        Args:
            parent: Parent QTreeWidgetItem or None for root items
            texts: List of text values for each column
            icon: Optional QIcon for the first column
            
        Returns:
            The created QTreeWidgetItem
        """
        item = QTreeWidgetItem()
        
        # Set text for all columns
        for col_idx, text in enumerate(texts):
            item.setText(col_idx, str(text))
        
        # Set icon if provided
        if icon:
            item.setIcon(0, icon)
        
        # Add to parent or root
        if parent:
            parent.addChild(item)
        else:
            self.addTopLevelItem(item)
        
        return item
    
    def _on_item_expanded(self, item: QTreeWidgetItem):
        """Handle item expansion - show collapse icon."""
        # Update the visual indication for expanded state
        item.setData(0, Qt.ItemDataRole.UserRole + 1, True)  # Mark as expanded
    
    def _on_item_collapsed(self, item: QTreeWidgetItem):
        """Handle item collapse - show expand icon."""
        # Update the visual indication for collapsed state
        item.setData(0, Qt.ItemDataRole.UserRole + 1, False)  # Mark as collapsed
    
    def set_item_parent_child_indicators(self, item: QTreeWidgetItem, show_hierarchy: bool = True):
        """
        Set visual indicators showing parent-child relationships.
        
        Args:
            item: The QTreeWidgetItem to update
            show_hierarchy: Whether to show parent-child relationship indicators
        """
        if show_hierarchy:
            # If item has children, it's a parent
            if item.childCount() > 0:
                # Prepend indicator to show this is a parent
                original_text = item.text(0)

            else:
                # This is a child/leaf item
                original_text = item.text(0)


