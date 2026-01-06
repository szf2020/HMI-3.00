# services\undo_commands.py
"""
Centralized Undo Command classes for the HMI Designer application.
These commands implement the Command pattern using Qt's QUndoCommand base class.
"""
from PySide6.QtWidgets import QGraphicsItem
from PySide6.QtGui import QUndoCommand, QPen, QBrush, QColor, QTransform
from PySide6.QtCore import QPointF, QRectF, Qt
import copy


class TransformItemsCommand(QUndoCommand):
    """
    Command for transforming graphic items (move, resize, rotate).
    Captures complete state before and after transformation.
    Supports single and multiple items.
    """
    def __init__(self, items, old_states, new_states, description="Transform Items"):
        super().__init__(description)
        self.items = items if isinstance(items, list) else [items]
        # Each state is a dict: {'pos': QPointF, 'rect': QRectF, 'rotation': float, 'transform_origin': QPointF, 'corner_radii': list}
        self.old_states = old_states if isinstance(old_states, list) else [old_states]
        self.new_states = new_states if isinstance(new_states, list) else [new_states]
        self._first_redo = True
        
    def redo(self):
        """Apply new transform states."""
        # Skip first redo since transformation was already applied during mouse interaction
        if self._first_redo:
            self._first_redo = False
            return
        self._apply_states(self.new_states)
        
    def undo(self):
        """Restore old transform states."""
        self._apply_states(self.old_states)
    
    def _apply_states(self, states):
        """Apply a list of states to items."""
        for item, state in zip(self.items, states):
            if not state or not item.scene():
                continue
            
            # Apply geometry (rect) first - this may affect size-dependent properties
            if 'rect' in state and hasattr(item, 'set_geometry'):
                item.set_geometry(state['rect'])
            
            # Apply transform origin before rotation (rotation uses this point)
            if 'transform_origin' in state:
                item.setTransformOriginPoint(state['transform_origin'])
            
            # Apply rotation after transform origin is set
            if 'rotation' in state:
                item.setRotation(state['rotation'])
            
            # Apply position after geometry and rotation are set
            if 'pos' in state:
                item.setPos(state['pos'])
            
            # Apply full transform (for flip operations)
            if 'transform' in state:
                item.setTransform(state['transform'])
            
            # Apply corner radii for rectangles
            if 'corner_radii' in state and hasattr(item, 'corner_radii'):
                item.corner_radii = state['corner_radii'].copy()
                if hasattr(item, 'update_path'):
                    item.update_path()
            
            # Ensure item redraws
            item.update()
    
    def id(self):
        """Return -1 to prevent merging of transform commands."""
        # Each transform should be tracked separately for proper undo/redo
        return -1
    
    def mergeWith(self, other):
        """Disabled - each transform should be a separate undo entry."""
        return False


class CornerRadiusCommand(QUndoCommand):
    """
    Command for changing corner radius of rounded rectangles.
    """
    def __init__(self, item, old_radii, new_radii, description="Change Corner Radius"):
        super().__init__(description)
        self.item = item
        self.old_radii = old_radii.copy() if old_radii else [0.0, 0.0, 0.0, 0.0]
        self.new_radii = new_radii.copy() if new_radii else [0.0, 0.0, 0.0, 0.0]
        self._first_redo = True
        
    def redo(self):
        """Apply new corner radii."""
        if self._first_redo:
            self._first_redo = False
            return
        self._apply_radii(self.new_radii)
        
    def undo(self):
        """Restore old corner radii."""
        self._apply_radii(self.old_radii)
    
    def _apply_radii(self, radii):
        """Apply corner radii to item."""
        if not self.item.scene() or not hasattr(self.item, 'corner_radii'):
            return
        self.item.corner_radii = radii.copy()
        if hasattr(self.item, 'update_path'):
            self.item.update_path()
        self.item.update()
    
    def id(self):
        """Return command ID for merging."""
        return 1002
    
    def mergeWith(self, other):
        """Merge consecutive corner radius commands."""
        if not isinstance(other, CornerRadiusCommand):
            return False
        if id(self.item) != id(other.item):
            return False
        self.new_radii = other.new_radii
        return True


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
        self._first_redo = True
        
    def redo(self):
        """Move items to new positions."""
        # Skip first redo since the move already happened during drag
        if self._first_redo:
            self._first_redo = False
            return
        for item, new_pos in zip(self.items, self.new_positions):
            if item.scene():
                item.setPos(new_pos)
        
    def undo(self):
        """Move items back to old positions."""
        for item, old_pos in zip(self.items, self.old_positions):
            if item.scene():
                item.setPos(old_pos)
    
    def id(self):
        """Return -1 to prevent merging of move commands."""
        # Return -1 so each move is tracked separately
        return -1


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
        self.original_items_data = copy.deepcopy(items_data)  # Keep original unmodified
        self.offset = offset or QPointF(20, 20)
        self.created_items = []
        self.assigned_ids = []  # Store assigned IDs for consistent redo
        self._first_redo = True
        
    def redo(self):
        """Paste items to canvas."""
        self.created_items = []
        
        for i, orig_data in enumerate(self.original_items_data):
            # Create a copy for this operation
            item_data = copy.deepcopy(orig_data)
            
            # Generate or reuse ID
            if self._first_redo:
                new_id = self.canvas._generate_next_id()
                self.assigned_ids.append(new_id)
            else:
                new_id = self.assigned_ids[i] if i < len(self.assigned_ids) else self.canvas._generate_next_id()
            
            item_data['id'] = new_id
            
            # Apply offset to position (from original position)
            orig_pos = orig_data.get('pos', [0, 0])
            item_data['pos'] = [orig_pos[0] + self.offset.x(), orig_pos[1] + self.offset.y()]
            
            item = self.canvas.create_graphic_item_from_data(item_data)
            if item:
                self.created_items.append(item)
                
        self._first_redo = False
        
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
        # Store original data for items to duplicate
        self.original_items_data = []
        for item in items:
            item_data = item.data(Qt.ItemDataRole.UserRole)
            if item_data:
                data_copy = copy.deepcopy(item_data)
                data_copy['pos'] = [item.pos().x(), item.pos().y()]
                rect = item.boundingRect()
                data_copy['rect'] = [rect.x(), rect.y(), rect.width(), rect.height()]
                self.original_items_data.append(data_copy)
        self.created_items = []
        self.assigned_ids = []  # Store assigned IDs for consistent redo
        self._first_redo = True
        
    def redo(self):
        """Create duplicates."""
        self.created_items = []
        
        for i, orig_data in enumerate(self.original_items_data):
            # Create a copy for this operation
            item_data = copy.deepcopy(orig_data)
            
            # Generate or reuse ID
            if self._first_redo:
                new_id = self.canvas._generate_next_id()
                self.assigned_ids.append(new_id)
            else:
                new_id = self.assigned_ids[i] if i < len(self.assigned_ids) else self.canvas._generate_next_id()
            
            item_data['id'] = new_id
            
            # Apply offset (from original position)
            orig_pos = orig_data.get('pos', [0, 0])
            item_data['pos'] = [orig_pos[0] + self.offset.x(), orig_pos[1] + self.offset.y()]
            
            item = self.canvas.create_graphic_item_from_data(item_data)
            if item:
                self.created_items.append(item)
        
        self._first_redo = False
                
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
