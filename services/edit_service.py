# services\edit_service.py
"""
Centralized Edit Service for managing clipboard operations and undo/redo functionality.
This service acts as the single source of truth for all edit operations across the application.
"""
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QUndoGroup, QUndoStack
from PySide6.QtCore import QObject, Signal
from enum import Enum, auto
import copy

from debug_utils import get_logger

logger = get_logger(__name__)


class ClipboardDataType(Enum):
    """Enum to identify the type of data stored in the clipboard."""
    NONE = auto()
    CANVAS_ITEMS = auto()       # Graphic objects from canvas
    TABLE_CELLS = auto()        # Cells from spreadsheet/tag table
    TREE_SCREENS = auto()       # Screen nodes from screen tree
    TREE_PROJECT_ITEMS = auto() # Tags/comments from project tree
    TEXT = auto()               # Plain text


class EditService(QObject):
    """
    A centralized service class to manage clipboard operations (cut, copy, paste)
    and undo/redo functionality across all application widgets.
    
    Features:
    - Singleton pattern for global access
    - QUndoGroup for managing multiple QUndoStack instances (one per document/widget)
    - Typed clipboard storage with discriminators
    - Unified edit operation dispatcher
    
    Signals:
        clipboard_changed: Emitted when clipboard content changes
        can_undo_changed: Emitted when undo availability changes
        can_redo_changed: Emitted when redo availability changes
    """
    _instance = None
    
    # Signals
    clipboard_changed = Signal(ClipboardDataType)
    can_undo_changed = Signal(bool)
    can_redo_changed = Signal(bool)
    undo_text_changed = Signal(str)
    redo_text_changed = Signal(str)

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EditService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initializes the EditService."""
        if self._initialized:
            return
            
        # Initialize QObject parent
        super().__init__()
        self._initialized = True
        
        # System clipboard for text
        self.system_clipboard = QApplication.clipboard()
        
        # Custom clipboard for application-specific data
        self._clipboard_data = None
        self._clipboard_type = ClipboardDataType.NONE
        self._is_cut_operation = False  # Track if clipboard data is from a cut operation
        
        # QUndoGroup to manage multiple undo stacks
        self.undo_group = QUndoGroup(self)
        
        # Map of widget/document IDs to their undo stacks
        self._undo_stacks = {}
        
        # Connect undo group signals
        self.undo_group.canUndoChanged.connect(self._on_can_undo_changed)
        self.undo_group.canRedoChanged.connect(self._on_can_redo_changed)
        self.undo_group.undoTextChanged.connect(self._on_undo_text_changed)
        self.undo_group.redoTextChanged.connect(self._on_redo_text_changed)
        
        logger.debug("EditService initialized")

    # ========== Clipboard Operations ==========
    
    def set_clipboard(self, data, data_type, is_cut=False):
        """
        Sets data to the internal clipboard with type information.
        
        Args:
            data: The data to store (will be deep copied)
            data_type: ClipboardDataType indicating the kind of data
            is_cut: True if this is a cut operation (original should be deleted on paste)
        """
        self._clipboard_data = copy.deepcopy(data)
        self._clipboard_type = data_type
        self._is_cut_operation = is_cut
        self.clipboard_changed.emit(data_type)
        logger.debug(f"Clipboard set: type={data_type.name}, is_cut={is_cut}")
    
    def get_clipboard(self):
        """
        Gets data from the internal clipboard.
        
        Returns:
            tuple: (data, ClipboardDataType, is_cut_operation)
        """
        return (copy.deepcopy(self._clipboard_data), self._clipboard_type, self._is_cut_operation)
    
    def get_clipboard_type(self):
        """Returns the type of data currently in the clipboard."""
        return self._clipboard_type
    
    def has_clipboard_data(self, data_type=None):
        """
        Checks if there is data in the clipboard.
        
        Args:
            data_type: Optional. If specified, checks for specific type of data.
        
        Returns:
            bool: True if clipboard has matching data
        """
        if data_type is None:
            return self._clipboard_type != ClipboardDataType.NONE
        return self._clipboard_type == data_type
    
    def clear_clipboard(self):
        """Clears the internal clipboard."""
        self._clipboard_data = None
        self._clipboard_type = ClipboardDataType.NONE
        self._is_cut_operation = False
        self.clipboard_changed.emit(ClipboardDataType.NONE)
        logger.debug("Clipboard cleared")
    
    def mark_cut_completed(self):
        """
        Marks that a cut operation has been completed (items were deleted after paste).
        After this, subsequent pastes won't trigger deletion.
        """
        self._is_cut_operation = False

    # ========== Undo Stack Management ==========
    
    def register_undo_stack(self, stack_id, undo_stack):
        """
        Registers a QUndoStack with the service.
        
        Args:
            stack_id: Unique identifier for the stack (e.g., widget ID, document path)
            undo_stack: QUndoStack instance to register
        """
        if stack_id in self._undo_stacks:
            logger.warning(f"Undo stack '{stack_id}' already registered, replacing")
            self.unregister_undo_stack(stack_id)
        
        self._undo_stacks[stack_id] = undo_stack
        self.undo_group.addStack(undo_stack)
        logger.debug(f"Registered undo stack: {stack_id}")
    
    def unregister_undo_stack(self, stack_id):
        """
        Unregisters a QUndoStack from the service.
        
        Args:
            stack_id: Identifier of the stack to remove
        """
        if stack_id in self._undo_stacks:
            stack = self._undo_stacks.pop(stack_id)
            self.undo_group.removeStack(stack)
            logger.debug(f"Unregistered undo stack: {stack_id}")
    
    def get_undo_stack(self, stack_id):
        """
        Gets a registered undo stack by ID.
        
        Args:
            stack_id: Identifier of the stack
            
        Returns:
            QUndoStack or None if not found
        """
        return self._undo_stacks.get(stack_id)
    
    def set_active_stack(self, stack_id):
        """
        Sets the active undo stack in the group.
        
        Args:
            stack_id: Identifier of the stack to make active
        """
        stack = self._undo_stacks.get(stack_id)
        if stack:
            self.undo_group.setActiveStack(stack)
            logger.debug(f"Active undo stack set to: {stack_id}")
        else:
            # If no stack found, set to None (no active stack)
            self.undo_group.setActiveStack(None)
    
    def get_active_stack(self):
        """Returns the currently active QUndoStack."""
        return self.undo_group.activeStack()
    
    def create_undo_stack(self, stack_id, parent=None):
        """
        Creates and registers a new QUndoStack.
        
        Args:
            stack_id: Unique identifier for the stack
            parent: Optional parent QObject
            
        Returns:
            QUndoStack: The created stack
        """
        stack = QUndoStack(parent)
        self.register_undo_stack(stack_id, stack)
        return stack

    # ========== Undo/Redo Operations ==========
    
    def undo(self):
        """Performs undo on the active stack."""
        if self.undo_group.canUndo():
            self.undo_group.undo()
            logger.debug("Undo performed")
    
    def redo(self):
        """Performs redo on the active stack."""
        if self.undo_group.canRedo():
            self.undo_group.redo()
            logger.debug("Redo performed")
    
    def can_undo(self):
        """Returns True if undo is available on the active stack."""
        return self.undo_group.canUndo()
    
    def can_redo(self):
        """Returns True if redo is available on the active stack."""
        return self.undo_group.canRedo()
    
    def get_undo_text(self):
        """Returns the text description of the next undo action."""
        return self.undo_group.undoText()
    
    def get_redo_text(self):
        """Returns the text description of the next redo action."""
        return self.undo_group.redoText()
    
    def push_command(self, command, stack_id=None):
        """
        Pushes an undo command to a stack.
        
        Args:
            command: QUndoCommand to push
            stack_id: Optional stack ID. If None, uses active stack.
        """
        if stack_id:
            stack = self._undo_stacks.get(stack_id)
            if stack:
                stack.push(command)
        else:
            stack = self.undo_group.activeStack()
            if stack:
                stack.push(command)

    # ========== Signal Handlers ==========
    
    def _on_can_undo_changed(self, can_undo):
        """Relays can undo changed signal."""
        self.can_undo_changed.emit(can_undo)
    
    def _on_can_redo_changed(self, can_redo):
        """Relays can redo changed signal."""
        self.can_redo_changed.emit(can_redo)
    
    def _on_undo_text_changed(self, text):
        """Relays undo text changed signal."""
        self.undo_text_changed.emit(text)
    
    def _on_redo_text_changed(self, text):
        """Relays redo text changed signal."""
        self.redo_text_changed.emit(text)

    # ========== Edit Operation Dispatcher ==========
    
    def execute_edit_operation(self, operation, widget):
        """
        Central dispatcher for edit operations.
        Routes the operation to the appropriate widget method.
        
        Args:
            operation: String name of operation ('cut', 'copy', 'paste', 'delete', 
                      'undo', 'redo', 'select_all', 'duplicate')
            widget: The target widget to perform the operation on
            
        Returns:
            bool: True if operation was executed, False otherwise
        """
        if widget is None:
            logger.warning(f"No widget provided for operation: {operation}")
            return False
        
        operation_map = {
            'cut': 'cut',
            'copy': 'copy',
            'paste': 'paste',
            'delete': 'delete',
            'undo': 'undo',
            'redo': 'redo',
            'select_all': 'selectAll',
            'duplicate': 'duplicate',
        }
        
        method_name = operation_map.get(operation)
        if not method_name:
            logger.warning(f"Unknown operation: {operation}")
            return False
        
        if hasattr(widget, method_name):
            try:
                getattr(widget, method_name)()
                logger.debug(f"Executed {operation} on {widget.__class__.__name__}")
                return True
            except Exception as e:
                logger.error(f"Error executing {operation}: {e}", exc_info=True)
                return False
        else:
            logger.debug(f"Widget {widget.__class__.__name__} does not support {operation}")
            return False
