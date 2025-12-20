# main_window\services\icon_service.py
from PySide6.QtGui import QIcon
import os
import logging

logger = logging.getLogger(__name__)

class IconService:
    """
    A centralized service for managing and retrieving icons for the application.
    It uses a predefined dictionary to map icon names to their file paths,
    making it easier to manage and update icons.
    """
    ICON_DIR = os.path.join(os.path.dirname(__file__), "..", "resources", "icons")

    ICONS = {
        # Modern Icon
        "HMI-Designer-icon": "HMI-Designer-icon.svg",
        
        # File Menu Icons
        "file-new": "file-new.svg",
        "folder-open": "folder-open.svg",
        "file-save": "file-save.svg",
        "file-save-as": "file-save-as.svg",
        "run": "run.svg",
        "window-close": "window-close.svg",
        "windows-close": "windows-close.svg",
        "exit": "exit.svg",
        "mouse-cursor": "mouse-cursor.svg",
        
        # Edit Menu Icons
        "edit-undo": "edit-undo.svg",
        "edit-redo": "edit-redo.svg",
        "edit-cut": "edit-cut.svg",
        "edit-copy": "edit-copy.svg",
        "edit-paste": "edit-paste.svg",
        "edit-duplicate": "edit-duplicate.svg",
        "edit-delete": "edit-delete.svg",
        "edit-consecutive-copy": "edit-consecutive-copy.svg",
        "edit-select-all": "edit-select-all.svg",
        "stacking-order": "stacking-order.svg",
        "move-front-layer": "move-front-layer.svg",
        "move-back-layer": "move-back-layer.svg",
        "move-to-front": "move-to-front.svg",
        "move-to-back": "move-to-back.svg",
        "align-center": "align-center.svg",
        "align-left": "align-left.svg",
        "align-horizontal-center": "align-horizontal-center.svg",
        "align-right": "align-right.svg",
        "align-top": "align-top.svg",
        "align-middle": "align-middle.svg",
        "align-bottom": "align-bottom.svg",
        "distribute-horizontal": "distribute-horizontal.svg",
        "distribute-vertical": "distribute-vertical.svg",
        "wrap": "wrap.svg",
        "flip": "flip.svg",
        "flip-vertical": "flip-vertical.svg",
        "flip-horizontal": "flip-horizontal.svg",
        "rotate-left": "rotate-left.svg",
        "rotate-right": "rotate-right.svg",
        
        # Search/Replace Menu Icons
        "search-tag": "search-tag.svg",
        "search-tag-list": "search-tag-list.svg",
        "search-text-list": "search-text-list.svg",
        "search-data-browser": "search-data-browser.svg",
        "search-ip-address-list": "search-ip-address-list.svg",
        "search-batch-edit": "search-batch-edit.svg",
        "search-batch-edit-tags": "search-batch-edit-tags.svg",
        "search-batch-edit-color": "search-batch-edit-color.svg",
        "search-batch-edit-shape": "search-batch-edit-shape.svg",
        "search-batch-edit-text": "search-batch-edit-text.svg",
        
        # View Menu Icons
        "view-preview": "view-preview.svg",
        "view-state-number": "view-state-number.svg",
        "view-next-state": "view-next-state.svg",
        "view-prev-state": "view-prev-state.svg",
        "view-tool-bar": "view-tool-bar.svg",
        "view-window-display": "view-window-display.svg",
        "view-view": "view-view.svg",
        "view-screen": "view-screen.svg",
        "view-edit": "view-edit.svg",
        "view-alignment": "view-alignment.svg",
        "view-figure": "view-figure.svg",
        "view-object": "view-object.svg",
        "view-debug": "view-debug.svg",
        "view-docking-window": "view-docking-window.svg",
        "dock-project-tree": "dock-project-tree.svg",
        "dock-screen-tree": "dock-screen-tree.svg",
        "dock-system-tree": "dock-system-tree.svg",
        "dock-tag-search": "dock-tag-search.svg",
        "dock-data-browser": "dock-data-browser.svg",
        "dock-property-tree": "dock-property-tree.svg",
        "dock-ip-address": "dock-ip-address.svg",
        "dock-library": "dock-library.svg",
        "dock-controller-list": "dock-controller-list.svg",
        "dock-data-view": "dock-data-view.svg",
        "dock-screen-image-list": "dock-screen-image-list.svg",
        "view-display-item": "view-display-item.svg",
        "view-tag": "view-tag.svg",
        "view-object-id": "view-object-id.svg",
        "view-transform-line": "view-transform-line.svg",
        "object-pos": "object-pos.svg",
        "object-size": "object-size.svg",
        "view-click-area": "view-click-area.svg",
        "view-object-snap": "view-object-snap.svg",
        "view-zoom": "view-zoom.svg",
        "view-fit-screen": "view-fit-screen.svg",
        "zoom-in": "zoom-in.svg",
        "zoom-out": "zoom-out.svg",
        
        # Screen Menu Icons
        "screen-new": "screen-new.svg",
        "screen-base": "screen-base.svg",
        "screen-window": "screen-window.svg",
        "screen-template": "screen-template.svg",
        "screen-widgets" : "screen-widgets.svg",
        "screen-report": "screen-report.svg",
        "screen-open": "screen-open.svg",
        "screen-close": "screen-close.svg",
        "screen-close-all": "screen-close-all.svg",
        "screen-design": "screen-design.svg",
        "screen-property": "screen-property.svg",
        
        "screen-base-white": "screen-base-white.svg",
        "screen-window-white": "screen-window-white.svg",
        "screen-template-white": "screen-template-white.svg",
        "screen-widgets-white": "screen-widgets-white.svg",
        
        # Common Menu Icons
        "common-environment": "common-environment.svg",
        "common-screen-switching": "common-screen-switching.svg",
        "common-dialog-window": "common-dialog-window.svg",
        "common-system-information": "common-system-information.svg",
        "common-security": "common-security.svg",
        "common-ethernet": "common-ethernet.svg",
        "common-controller-setting": "common-controller-setting.svg",
        "common-peripheral-device": "common-peripheral-device.svg",
        "common-barcode": "common-barcode.svg",
        "common-rfid": "common-rfid.svg",
        "common-servo": "common-servo.svg",
        "common-robot": "common-robot.svg",
        "common-camera": "common-camera.svg",
        "common-tags": "common-tags.svg",
        "common-folder-open": "common-folder-open.svg",
        "common-new": "common-new.svg",
        "common-add": "common-add.svg",
        "common-edit": "common-edit.svg",
        "common-remove": "common-remove.svg",
        "common-import": "common-import.svg",
        "common-export": "common-export.svg",
        "common-comment": "common-comment.svg",
        "common-add-column": "common-add-column.svg",
        "common-add-row": "common-add-row.svg",
        "common-remove-column": "common-remove-column.svg",
        "common-remove-row": "common-remove-row.svg",
        "common-find": "common-find.svg",
        "common-style": "common-style.svg",
        "common-bold": "common-bold.svg",
        "common-italic": "common-italic.svg",
        "common-underline": "common-underline.svg",
        "common-fill": "common-fill.svg",
        "common-alarm": "common-alarm.svg",
        "common-user-alarm": "common-user-alarm.svg",
        "common-system-alarm": "common-system-alarm.svg",
        "common-popup-alarm": "common-popup-alarm.svg",
        "common-logging": "common-logging.svg",
        "common-script": "common-script.svg",
        "common-tags-data-transfer": "common-tags-data-transfer.svg",
        "common-trigger-action": "common-trigger-action.svg",
        "common-time-action": "common-time-action.svg",

        # Figure Menu Icons
        "figure-text": "figure-text.svg",
        "figure-line": "figure-line.svg",
        "figure-polyline": "figure-polyline.svg",
        "figure-rectangle": "figure-rectangle.svg",
        "figure-polygon": "figure-polygon.svg",
        "figure-circle": "figure-circle.svg",
        "figure-arc": "figure-arc.svg",
        "figure-sector": "figure-sector.svg",
        "figure-table": "figure-table.svg",
        "figure-scale": "figure-scale.svg",
        "figure-image": "figure-image.svg",
        "figure-dxf": "figure-dxf.svg",
        
        # Object Menu Icons
        "object-button": "object-button.svg",
        "object-push-button-sq": "object-push-button-sq.svg",
        "object-push-button-ci": "object-push-button-ci.svg",
        "object-toggle-button": "object-toggle-button.svg",
        "object-checkbox": "object-checkbox.svg",
        "object-radio-button": "object-radio-button.svg",
        "object-selector-switch": "object-selector-switch.svg",
        "object-lamp": "object-lamp.svg",
        "object-bit-lamp": "object-bit-lamp.svg",
        "object-word-lamp": "object-word-lamp.svg",
        "object-border-lamp": "object-border-lamp.svg",
        "object-numerical": "object-numerical.svg",
        "object-calculator": "object-calculator.svg",
        "object-spin-box": "object-spin-box.svg",
        "object-text-display": "object-text-display.svg",
        "object-datetime": "object-datetime.svg",
        "object-date-display": "object-date-display.svg",
        "object-time-display": "object-time-display.svg",
        "object-datetime-display": "object-datetime-display.svg",
        "object-datetime-picker": "object-datetime-picker.svg",
        "object-comment": "object-comment.svg",
        "object-bit-comment": "object-bit-comment.svg",
        "object-word-comment": "object-word-comment.svg",
        "object-simple-comment": "object-simple-comment.svg",
        "object-view-box": "object-view-box.svg",
        "object-combo-box": "object-combo-box.svg",
        "object-check-list-box": "object-check-list-box.svg",
        "object-side-menu-bar": "object-side-menu-bar.svg",
        "object-group-box": "object-group-box.svg",
        "object-data-grid": "object-data-grid.svg",
        "object-list-box": "object-list-box.svg",
        "object-splitter-panel": "object-splitter-panel.svg",
        "object-status-bar": "object-status-bar.svg",
        "object-tab-view": "object-tab-view.svg",
        "object-tree-view": "object-tree-view.svg",
        "object-scroll-bar": "object-scroll-bar.svg",
        "object-image": "object-image.svg",
        "object-video": "object-video.svg",
        "object-animation": "object-animation.svg",
        "object-progress-bar": "object-progress-bar.svg",
        "object-tower-light": "object-tower-light.svg",
        "object-gear": "object-gear.svg",
        "object-robot": "object-robot.svg",
        "object-conveyor": "object-conveyor.svg",
        "object-fan": "object-fan.svg",
        "object-printer": "object-printer.svg",
        "object-historical-data": "object-historical-data.svg",
        "object-alarm": "object-alarm.svg",
        "object-simple-alarm": "object-simple-alarm.svg",
        "object-user-alarm": "object-user-alarm.svg",
        "object-system-alarm": "object-system-alarm.svg",
        "object-recipe": "object-recipe.svg",
        "object-graph": "object-graph.svg",
        "object-line-graph": "object-line-graph.svg",
        "object-trend-graph": "object-trend-graph.svg",
        "object-bar-graph": "object-bar-graph.svg",
        "object-pie-graph": "object-pie-graph.svg",
        "object-scatter-graph": "object-scatter-graph.svg",
        "object-combo-graph": "object-combo-graph.svg",
        "object-graphical-meter": "object-graphical-meter.svg",
        "object-sector-meter": "object-sector-meter.svg",
        "object-semi-circle-meter": "object-semi-circle-meter.svg",
        "object-bar-meter": "object-bar-meter.svg",
        "object-slider": "object-slider.svg",
        "object-document": "object-document.svg",
        "object-web-browser": "object-web-browser.svg",
        "icon-park-solid-add": "icon-park-solid-add.svg",
        "icon-park-solid-subtract": "icon-park-solid-subtract.svg",
        
        # Layer Icons
        "layer-visible": "layer-visible.svg",
        "layer-hidden": "layer-hidden.svg",
        "layer-locked": "layer-locked.svg",
        "layer-unlocked": "layer-unlocked.svg",
        "layer-group": "layer-group.svg",
        "layer-item": "layer-item.svg",
        "dock-layers": "dock-layers.svg",

    }

    @staticmethod
    def get_icon(name: str) -> QIcon:
        """
        Loads an icon from the resources/icons directory using a predefined dictionary.

        Args:
            name: The logical name of the icon to load.

        Returns:
            A QIcon object. Returns an empty QIcon if the name is not found.
        """
        filename = IconService.ICONS.get(name)
        if not filename:
            logger.warning(f"Icon '{name}' not found in the icon dictionary.")
            return QIcon()
            
        path = os.path.join(IconService.ICON_DIR, filename)
        if not os.path.exists(path):
            logger.warning(f"Icon file '{filename}' for '{name}' not found at '{path}'")
            return QIcon()
            
        return QIcon(path)
