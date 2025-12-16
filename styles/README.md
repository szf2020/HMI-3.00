# Styles Package Documentation

## Overview

The `styles` package centralizes all styling, theming, and visual design constants for the HMI Designer Application. This ensures consistency across the entire codebase and makes it easy to update the entire application's theme by changing values in one place.

## Structure

```
styles/
├── __init__.py           # Package initialization and exports
├── colors.py             # Color theme constants
├── fonts.py              # Font theme and typography constants
└── stylesheets.py        # QSS stylesheet generators
```

## Modules

### 1. `colors.py` - Color Theme

Defines all colors used throughout the application organized by category:

#### Dark Theme Colors
- `BG_DARK_PRIMARY` - Main dark background (#2b2b2b)
- `BG_DARK_SECONDARY` - Secondary dark background (#252525)
- `BG_DARK_TERTIARY` - Tertiary dark background (#3d3d3d)
- `BG_DARK_QUATERNARY` - Header background (#353535)

#### Text Colors
- `TEXT_PRIMARY` - Primary text color (white)
- `TEXT_SECONDARY` - Secondary text color (light grey)
- `TEXT_DARK` - Dark text for light backgrounds

#### Accent Colors (Google Material Design)
- `ACCENT_GREEN` - Primary accent (#34a853)
- `ACCENT_GREEN_DARK` - Dark green for borders (#2e7d32)
- `ACCENT_YELLOW` - Yellow accent (#fbbc05)
- `ACCENT_YELLOW_DARK` - Dark yellow (#f9ab00)

#### Interactive Colors
- `COLOR_SELECTED` - Tree item selected state (dark blue)
- `COLOR_SELECTED_ALT` - Alternative selected color (lighter blue)
- `COLOR_HOVER` - Hover effect color
- `COLOR_SELECTION_HIGHLIGHT` - Selection highlight color

#### Border and Grid Colors
- `BORDER_DARK` - Dark border (#444444)
- `BORDER_MEDIUM` - Medium border (#555555)
- `BORDER_LIGHT` - Light border (#666666)
- `GRID_LINE` - Grid line color

#### Reference/Formula Colors
- `COLOR_REF_BLUE` - Reference blue
- `COLOR_REF_RED` - Reference red
- `COLOR_REF_GREEN` - Reference green
- `COLOR_REF_PURPLE` - Reference purple

#### Drawing and Graphic Colors
- `COLOR_SELECTION_BOX_BORDER` - Selection box border (cyan)
- `COLOR_TRANSFORM_BORDER` - Transform handle border
- `COLOR_TRANSFORM_INDIVIDUAL` - Individual transform color (magenta)

#### Utility Functions
- `get_text_color(bg_color_hex)` - Automatically determine appropriate text color based on background brightness

### 2. `fonts.py` - Typography

Defines all font-related constants:

#### Font Families
- `FONT_FAMILY_DEFAULT` - Default font (Arial)
- `FONT_FAMILY_MONOSPACE` - Monospace font (Courier New)
- `FONT_FAMILY_SYSTEM` - System font (Segoe UI)

#### Font Sizes
- `FONT_SIZE_SMALL` - 8pt (hints, status)
- `FONT_SIZE_NORMAL` - 10pt (default)
- `FONT_SIZE_MEDIUM` - 11pt
- `FONT_SIZE_LARGE` - 12pt (headers)
- `FONT_SIZE_XLARGE` - 14pt (titles)
- `FONT_SIZE_XXLARGE` - 16pt (dialog titles)

#### Font Weights
- `FONT_WEIGHT_NORMAL` - Normal weight
- `FONT_WEIGHT_MEDIUM` - Medium weight
- `FONT_WEIGHT_BOLD` - Bold weight
- `FONT_WEIGHT_BLACK` - Black weight

#### Predefined Font Objects
- `FONT_DEFAULT`, `FONT_SMALL`, `FONT_LARGE`, `FONT_LARGE_BOLD`, etc.
- `FONT_MONOSPACE` - Monospace font object

#### Utility Functions
- `create_font(size, weight, family, italic)` - Create custom font objects

### 3. `stylesheets.py` - QSS Stylesheet Generators

Contains functions that generate QSS stylesheets using variables from `colors.py`:

#### Stylesheet Generators
- `get_tree_widget_stylesheet()` - Standard tree widget styles
- `get_project_tree_stylesheet(expand_icon_path, collapse_icon_path)` - Advanced tree with icons
- `get_status_bar_stylesheet()` - Status bar styles
- `get_tool_button_stylesheet()` - Tool button on/off states
- `get_formula_hint_stylesheet()` - Formula hint popup
- `get_completer_popup_stylesheet()` - Autocomplete popup

#### Color Helpers
- `get_spreadsheet_cell_color(is_selected, is_header)` - Cell background colors
- `get_spreadsheet_border_color()` - Cell border color
- `get_gradient_qss(color1, color2)` - Linear gradient QSS
- `get_color_button_stylesheet(color_hex, is_selected)` - Color picker button
- `get_pattern_widget_stylesheet(color_hex)` - Pattern widget
- `get_error_text_stylesheet()` - Error text styling
- `get_normal_text_stylesheet()` - Normal text styling

## Usage Examples

### Importing and Using Colors

```python
from styles import colors

# Use in stylesheets
widget.setStyleSheet(f"background-color: {colors.BG_DARK_PRIMARY};")

# Use in QColor constructors
selection_color = QColor(colors.COLOR_SELECTED)

# Use color constants directly
pen = QPen(QColor(colors.ACCENT_GREEN), 2)
```

### Using Fonts

```python
from styles import fonts

# Use predefined fonts
widget.setFont(fonts.FONT_LARGE_BOLD)

# Or create custom fonts
custom_font = fonts.create_font(
    size=14,
    weight=fonts.FONT_WEIGHT_BOLD,
    family=fonts.FONT_FAMILY_DEFAULT,
    italic=False
)
widget.setFont(custom_font)
```

### Using Stylesheets

```python
from styles import stylesheets

# Apply predefined stylesheets
tree_widget.setStyleSheet(stylesheets.get_tree_widget_stylesheet())

status_bar.setStyleSheet(stylesheets.get_status_bar_stylesheet())

# Or use stylesheet generators with parameters
formula_popup.setStyleSheet(stylesheets.get_formula_hint_stylesheet())

# Access stylesheet dictionary
all_stylesheets = stylesheets.STYLESHEETS
```

## Theming

To change the entire application theme:

1. **Global color scheme**: Edit `colors.py` to change all color constants
2. **Typography**: Edit `fonts.py` to change font sizes and families
3. **Specific components**: Update stylesheet generators in `stylesheets.py`

### Example: Creating a Light Theme

Duplicate `colors.py` to `colors_light.py` and modify all color values:

```python
# colors_light.py
BG_DARK_PRIMARY = "#ffffff"
TEXT_PRIMARY = "#000000"
ACCENT_GREEN = "#00aa00"
# ... etc
```

Then import from your theme file:

```python
# In your application
from styles import colors_light as colors
```

## Best Practices

1. **Always use style constants** instead of hardcoding colors and fonts
2. **Use color variables** even when defining new color schemes
3. **Use stylesheet generators** for complex QSS styles
4. **Group related styles** together in the same file
5. **Document color purpose** (e.g., "for selection state", "for borders")
6. **Test theme changes** to ensure consistency across all components

## Migration Guide

### Before (Hardcoded Colors)
```python
widget.setStyleSheet("background-color: #2b2b2b; color: #ffffff;")
pen = QPen(QColor("#00FFFF"), 2)
```

### After (Using Style Constants)
```python
from styles import colors, stylesheets

widget.setStyleSheet(stylesheets.get_tree_widget_stylesheet())
pen = QPen(QColor(colors.COLOR_TRANSFORM_BORDER), 2)
```

## Files Updated with Centralized Styles

- `main_window/main_window.py`
- `main_window/widgets/tree.py`
- `main_window/widgets/pattern_widget.py`
- `main_window/widgets/gradient_widget.py`
- `main_window/widgets/color_selector.py`
- `main_window/toolbars/transform_handler.py`
- `main_window/toolbars/drawing_tools/rectangle_tool.py`
- `main_window/toolbars/drawing_tools/ellipse_tool.py`
- `project/comment/comment_table.py`
- `project/comment/virtual_spreadsheet.py`
- `screen/base/canvas_base_screen.py`

## Future Enhancements

- [ ] Create dark/light theme preset files
- [ ] Add dynamic theme switching at runtime
- [ ] Create theme editor GUI
- [ ] Add theme export/import functionality
- [ ] Support for custom color profiles per user
