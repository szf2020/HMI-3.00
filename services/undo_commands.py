# services\undo_commands.py
"""
Centralized Undo Command classes for the HMI Designer application.
These commands implement the Command pattern using Qt's QUndoCommand base class.
"""
from PySide6.QtWidgets import QGraphicsItem
from PySide6.QtGui import QUndoCommand, QPen, QBrush, QColor
from PySide6.QtCore import QPointF, QRectF, Qt
import copy


class AddItemCommand(QUndoCommand):
    """
    Command for adding a graphic item to the canvas.
    Undo removes the item, redo adds it back.
    """
    def __init__(self, canvas, item_data, description="Add Item"):
        super().__init__(description)
        self.canvas = canvas
        self.item_data = copy.deepcopy(item_data)
        self.item = None  # Will hold reference to created item
        
    def redo(self):
        """Add the item to the canvas."""
        self.item = self.canvas.create_graphic_item_from_data(self.item_data)
        self.canvas.save_items()
        
    def undo(self):
        """Remove the item from the canvas."""
        if self.item and self.item.scene():
            self.canvas.graphics_item_removed.emit(self.item)
            self.canvas.scene.removeItem(self.item)
            self.canvas.clear_transform_handler()
            self.canvas.save_items()
            self.item = None


class RemoveItemCommand(QUndoCommand):
    """
    Command for removing graphic items from the canvas.
    Supports removing single or multiple items.
    """
    def __init__(self, canvas, items, description="Delete Items"):
        super().__init__(description)
        self.canvas = canvas
        # Store item data for all items being removed
        self.items_data = []
        for item in items:
            item_data = item.data(Qt.ItemDataRole.UserRole)
            if item_data:
                data_copy = copy.deepcopy(item_data)
                # Store current position
                data_copy['pos'] = [item.pos().x(), item.pos().y()]
                rect = item.boundingRect()
                data_copy['rect'] = [rect.x(), rect.y(), rect.width(), rect.height()]
                self.items_data.append(data_copy)
        self.items = []  # Will hold references to recreated items
        
    def redo(self):
        """Remove all items from the canvas."""
        # Find and remove items by their ID
        for item_data in self.items_data:
            item_id = item_data.get('id')
            for item in self.canvas.scene.items():
                data = item.data(Qt.ItemDataRole.UserRole)
                if data and data.get('id') == item_id:
                    self.canvas._previous_selection.discard(item)
                    self.canvas.graphics_item_removed.emit(item)
                    self.canvas.scene.removeItem(item)
                    break
        self.canvas.clear_transform_handler()
        self.canvas.save_items()
        
    def undo(self):
        """Recreate all removed items."""
        self.items = []
        for item_data in self.items_data:
            item = self.canvas.create_graphic_item_from_data(item_data)
            if item:
                self.items.append(item)
        self.canvas.save_items()


class MoveItemsCommand(QUndoCommand):
    """
    Command for moving graphic items on the canvas.
    Supports moving single or multiple items.
    """
    def __init__(self, items, old_positions, new_positions, description="Move Items"):
        super().__init__(description)
        self.items = items
        self.old_positions = old_positions  # List of QPointF
        self.new_positions = new_positions  # List of QPointF
        
    def redo(self):
        """Move items to new positions."""
        for item, new_pos in zip(self.items, self.new_positions):
            if item.scene():
                item.setPos(new_pos)
        
    def undo(self):
        """Move items back to old positions."""
        for item, old_pos in zip(self.items, self.old_positions):
            if item.scene():
                item.setPos(old_pos)


class ResizeItemCommand(QUndoCommand):
    """
    Command for resizing a graphic item.
    """
    def __init__(self, item, old_rect, new_rect, old_pos, new_pos, description="Resize Item"):
        super().__init__(description)
        self.item = item
        self.old_rect = old_rect
        self.new_rect = new_rect
        self.old_pos = old_pos
        self.new_pos = new_pos
        
    def redo(self):
        """Apply new size."""
        if self.item.scene() and hasattr(self.item, 'setRect'):
            self.item.setRect(self.new_rect)
            self.item.setPos(self.new_pos)
        
    def undo(self):
        """Restore old size."""
        if self.item.scene() and hasattr(self.item, 'setRect'):
            self.item.setRect(self.old_rect)
            self.item.setPos(self.old_pos)


class PropertyChangeCommand(QUndoCommand):
    """
    Command for changing a property of a graphic item.
    Generic command that can handle any property change.
    """
    def __init__(self, item, property_name, old_value, new_value, description=None):
        super().__init__(description or f"Change {property_name}")
        self.item = item
        self.property_name = property_name
        self.old_value = old_value
        self.new_value = new_value
        
    def redo(self):
        """Apply new value."""
        self._apply_value(self.new_value)
        
    def undo(self):
        """Restore old value."""
        self._apply_value(self.old_value)
        
    def _apply_value(self, value):
        """Helper to apply a value to the item."""
        if not self.item.scene():
            return
            
        # Handle different property types
        if self.property_name == 'pen':
            if hasattr(self.item, 'item'):
                self.item.item.setPen(value)
        elif self.property_name == 'brush':
            if hasattr(self.item, 'item'):
                self.item.item.setBrush(value)
        elif self.property_name == 'rotation':
            self.item.setRotation(value)
        elif self.property_name == 'z_value':
            self.item.setZValue(value)
        else:
            # Try generic setter
            setter_name = f'set{self.property_name[0].upper()}{self.property_name[1:]}'
            if hasattr(self.item, setter_name):
                getattr(self.item, setter_name)(value)


class ZOrderCommand(QUndoCommand):
    """
    Command for changing the stacking order (z-value) of items.
    """
    def __init__(self, items, old_z_values, new_z_values, description="Change Stacking Order"):
        super().__init__(description)
        self.items = items
        self.old_z_values = old_z_values
        self.new_z_values = new_z_values
        
    def redo(self):
        """Apply new z-values."""
        for item, z_value in zip(self.items, self.new_z_values):
            if item.scene():
                item.setZValue(z_value)
        
    def undo(self):
        """Restore old z-values."""
        for item, z_value in zip(self.items, self.old_z_values):
            if item.scene():
                item.setZValue(z_value)


class PasteItemsCommand(QUndoCommand):
    """
    Command for pasting items from clipboard.
    Handles multiple items with position offset.
    """
    def __init__(self, canvas, items_data, offset=None, description="Paste Items"):
        super().__init__(description)
        self.canvas = canvas
        self.items_data = copy.deepcopy(items_data)
        self.offset = offset or QPointF(20, 20)
        self.created_items = []
        
    def redo(self):
        """Paste items to canvas."""
        self.created_items = []
        for item_data in self.items_data:
            # Generate new ID
            item_data['id'] = self.canvas._generate_next_id()
            
            # Apply offset to position
            pos = item_data.get('pos', [0, 0])
            item_data['pos'] = [pos[0] + self.offset.x(), pos[1] + self.offset.y()]
            
            item = self.canvas.create_graphic_item_from_data(item_data)
            if item:
                self.created_items.append(item)
                
        # Select pasted items
        self.canvas.scene.clearSelection()
        for item in self.created_items:
            item.setSelected(True)
            
        self.canvas.save_items()
        
    def undo(self):
        """Remove pasted items."""
        for item in self.created_items:
            if item and item.scene():
                self.canvas._previous_selection.discard(item)
                self.canvas.graphics_item_removed.emit(item)
                self.canvas.scene.removeItem(item)
        self.canvas.clear_transform_handler()
        self.canvas.save_items()
        self.created_items = []


class DuplicateItemsCommand(QUndoCommand):
    """
    Command for duplicating items on the canvas.
    """
    def __init__(self, canvas, items, offset=None, description="Duplicate Items"):
        super().__init__(description)
        self.canvas = canvas
        self.offset = offset or QPointF(20, 20)
        # Store data for items to duplicate
        self.items_data = []
        for item in items:
            item_data = item.data(Qt.ItemDataRole.UserRole)
            if item_data:
                data_copy = copy.deepcopy(item_data)
                data_copy['pos'] = [item.pos().x(), item.pos().y()]
                rect = item.boundingRect()
                data_copy['rect'] = [rect.x(), rect.y(), rect.width(), rect.height()]
                self.items_data.append(data_copy)
        self.created_items = []
        
    def redo(self):
        """Create duplicates."""
        self.created_items = []
        for item_data in self.items_data:
            # Generate new ID
            item_data['id'] = self.canvas._generate_next_id()
            
            # Apply offset
            pos = item_data.get('pos', [0, 0])
            item_data['pos'] = [pos[0] + self.offset.x(), pos[1] + self.offset.y()]
            
            item = self.canvas.create_graphic_item_from_data(item_data)
            if item:
                self.created_items.append(item)
                
        # Select duplicated items
        self.canvas.scene.clearSelection()
        for item in self.created_items:
            item.setSelected(True)
            
        self.canvas.save_items()
        
    def undo(self):
        """Remove duplicates."""
        for item in self.created_items:
            if item and item.scene():
                self.canvas._previous_selection.discard(item)
                self.canvas.graphics_item_removed.emit(item)
                self.canvas.scene.removeItem(item)
        self.canvas.clear_transform_handler()
        self.canvas.save_items()
        self.created_items = []
