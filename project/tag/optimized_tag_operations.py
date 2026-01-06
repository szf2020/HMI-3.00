# project\tag\optimized_tag_operations.py
"""
Optimized tag table operations for large-scale batch processing.
Provides batching, progress tracking, and UI responsiveness for tag deletion and addition.
"""

import time
from PySide6.QtWidgets import QProgressDialog, QApplication
from PySide6.QtCore import Qt


class OptimizedTagDeletion:
    """Handles optimized batch deletion of tags with progress feedback."""
    
    # Configuration - matches PerformanceConfig for consistency
    BATCH_CHUNK_SIZE = 100
    MIN_ITEMS_FOR_PROGRESS = 10
    
    @staticmethod
    def delete_multiple_tags_optimized(tag_table, rows_to_delete, parent_widget=None):
        """
        Delete multiple tags in optimized batches with progress feedback.
        
        Args:
            tag_table: The TagTable widget instance
            rows_to_delete: List of row indices to delete (will be sorted descending)
            parent_widget: Parent widget for progress dialog
            
        Returns:
            bool: True if deletion completed successfully, False if cancelled
        """
        if not rows_to_delete:
            return True
        
        # Sort in reverse order to maintain correct indices during deletion
        sorted_rows = sorted(rows_to_delete, reverse=True)
        total_rows = len(sorted_rows)
        
        # Show progress dialog for large deletions
        show_progress = total_rows >= OptimizedTagDeletion.MIN_ITEMS_FOR_PROGRESS
        progress = None
        
        try:
            if show_progress:
                progress = QProgressDialog(
                    "Deleting tags...", "Cancel", 0, total_rows,
                    parent_widget or tag_table
                )
                progress.setWindowModality(Qt.WindowModality.WindowModal)
                progress.setMinimumDuration(500)
            
            # Block tree signals to prevent re-rendering during deletion
            tag_table.table.blockSignals(True)
            
            # Process deletions in chunks
            start_time = time.time()
            deleted_count = 0
            
            for i, row in enumerate(sorted_rows):
                # Update progress
                if progress:
                    if progress.wasCanceled():
                        tag_table.table.blockSignals(False)
                        tag_table.table.update()
                        return False
                    
                    progress.setValue(i)
                    QApplication.processEvents()
                
                # Delete the item
                root = tag_table.table.invisibleRootItem()
                if 0 <= row < root.childCount():
                    item = root.takeChild(row)
                    if item:
                        deleted_count += 1
                
                # Process events periodically to keep UI responsive
                if (i + 1) % OptimizedTagDeletion.BATCH_CHUNK_SIZE == 0:
                    QApplication.processEvents()
            
            # Re-enable signals and trigger final update
            tag_table.table.blockSignals(False)
            tag_table.table.update()
            
            # Trigger save after deletion
            tag_table.save_data()
            
            elapsed = time.time() - start_time
            
            if progress:
                progress.setValue(total_rows)
                progress.close()
            
            return True
            
        except Exception as e:
            if progress:
                progress.close()
            tag_table.table.blockSignals(False)
            tag_table.table.update()
            raise e


class OptimizedTagAddition:
    """Handles optimized batch addition of tags with progress feedback."""
    
    # Configuration
    BATCH_CHUNK_SIZE = 100
    MIN_ITEMS_FOR_PROGRESS = 20
    
    @staticmethod
    def add_multiple_tags_optimized(tag_table, tags_data, parent_widget=None):
        """
        Add multiple tags in optimized batches with progress feedback.
        
        Args:
            tag_table: The TagTable widget instance
            tags_data: List of tag data dictionaries to add
            parent_widget: Parent widget for progress dialog
            
        Returns:
            bool: True if addition completed successfully, False if cancelled
        """
        if not tags_data:
            return True
        
        total_tags = len(tags_data)
        
        # Show progress dialog for large additions
        show_progress = total_tags >= OptimizedTagAddition.MIN_ITEMS_FOR_PROGRESS
        progress = None
        
        try:
            if show_progress:
                progress = QProgressDialog(
                    "Adding tags...", "Cancel", 0, total_tags,
                    parent_widget or tag_table
                )
                progress.setWindowModality(Qt.WindowModality.WindowModal)
                progress.setMinimumDuration(500)
            
            # Block signals during batch addition
            tag_table.table.blockSignals(True)
            
            added_count = 0
            start_time = time.time()
            
            for i, tag_data in enumerate(tags_data):
                # Update progress
                if progress:
                    if progress.wasCanceled():
                        tag_table.table.blockSignals(False)
                        tag_table.table.update()
                        return False
                    
                    progress.setValue(i)
                    QApplication.processEvents()
                
                # Add the tag using the standard method
                tag_table._add_tag_from_data(tag_data)
                added_count += 1
                
                # Process events periodically to keep UI responsive
                if (i + 1) % OptimizedTagAddition.BATCH_CHUNK_SIZE == 0:
                    QApplication.processEvents()
            
            # Re-enable signals and trigger final update
            tag_table.table.blockSignals(False)
            tag_table.table.update()
            
            # Trigger save after addition
            tag_table.save_data()
            
            elapsed = time.time() - start_time
            
            if progress:
                progress.setValue(total_tags)
                progress.close()
            
            return True
            
        except Exception as e:
            if progress:
                progress.close()
            tag_table.table.blockSignals(False)
            tag_table.table.update()
            raise e
