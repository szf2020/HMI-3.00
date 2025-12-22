"""
Centralized color theme for the HMI Designer Application.
All color values are defined here to ensure consistency across the entire application.

This module provides a Material Design-inspired dark theme with carefully chosen contrast
ratios for optimal accessibility and visual hierarchy. Colors are organized by category
for easy maintenance and extension.

Color Categories:
- DARK THEME: Primary backgrounds and surfaces (BG_DARK_*)
- TEXT COLORS: Typography colors for different emphasis levels (TEXT_*)
- ACCENT COLORS: Interactive and highlight colors (ACCENT_*, HOVER, SELECTED)
- INTERACTIVE: States for user interactions (HOVER, SELECTED, SELECTION_HIGHLIGHT)
- BORDERS: Divider and border colors (BORDER_*)
- REFERENCE/FORMULA: Tag-specific colors for visual identification (BLUE, RED, GREEN, PURPLE)
- DRAWING: Graphics and canvas colors (COLOR_SELECTION_*, COLOR_TRANSFORM_*, COLOR_GRID_*)
- PATTERNS: Default colors for patterns and gradients
- STATUS: Error, warning, and success indicators

Usage:
  from styles.colors import TEXT_PRIMARY, BG_DARK_PRIMARY, ACCENT_GREEN
  
  # Use in stylesheets
  stylesheet = f"QLabel {{ color: {TEXT_PRIMARY}; background-color: {BG_DARK_PRIMARY}; }}"
  
  # Use with fonts
  color = get_contrasting_text_color(BG_DARK_PRIMARY)  # Returns white or black

Unused Colors (Reserved for Future Features):
  - BG_DARK_SECONDARY, ACCENT_YELLOW_DARK: For alternative backgrounds/themes
  - ACCENT_BLUE, ACCENT_BLUE_DARK: For primary action colors
  - SELECTION_HIGHLIGHT_ALT: Alternate selection highlight for multi-select states
  - Additional color slots available for theme extensions
"""

# ============================================================================
# DARK THEME COLORS (Main UI Background)
# ============================================================================

# Primary dark backgrounds
BG_DARK_PRIMARY = "#2b2b2b"       # Main dark background for tree widgets, docks
BG_DARK_SECONDARY = "#252525"     # Secondary dark background
BG_DARK_TERTIARY = "#3d3d3d"      # Tertiary dark background
BG_DARK_QUATERNARY = "#353535"    # Header background

# Status bar and special backgrounds
BG_STATUS_BAR = "#2c3e50"         # Status bar dark blue-grey
BG_SPREADSHEET = "#191919"        # Spreadsheet/table background
BG_SPREADSHEET_CELL = "#1a1a1a"   # Spreadsheet cell background

# ============================================================================
# TEXT AND FOREGROUND COLORS
# ============================================================================

TEXT_PRIMARY = "#ffffff"          # Primary text color (white)
TEXT_SECONDARY = "#c8c8c8"        # Secondary text color (light grey)
TEXT_DARK = "#000000"             # Dark text color for light backgrounds

# ============================================================================
# ACCENT AND HIGHLIGHT COLORS
# ============================================================================

# Google Material Colors
ACCENT_GREEN = "#34a853"          # Google Green - primary accent
ACCENT_GREEN_DARK = "#2e7d32"     # Darker green for borders
ACCENT_YELLOW = "#fbbc05"         # Google Yellow
ACCENT_YELLOW_DARK = "#f9ab00"    # Darker yellow

# Interactive colors
COLOR_SELECTED = "rgba(84, 184, 255, 100)"        # Tree item selected (blue)
COLOR_SELECTED_ALT = "rgba(84, 184, 255, 150)"    # Alternative selected color
COLOR_HOVER = "#505050"           # Hover color (gray)
COLOR_SELECTION_HIGHLIGHT = "rgba(84, 184, 255, 100)"  # Selection highlight
COLOR_SELECTION_HIGHLIGHT_ALT = "rgba(84, 184, 255, 150)"  # Selection with transparency

# Focus and selection state colors
COLOR_FOCUS_HIGHLIGHT = "#0078D7"  # Focus/selection highlight (VS Code blue)
COLOR_HOVER_FOCUS = "#5B9BD5"     # Hover focus state (Excel-style blue)
COLOR_SELECTION_FILL = "#228B22"  # Selection fill color (forest green)
COLOR_HEADER_TEXT = "#BFBFBF"     # Header text color (light grey)

# ============================================================================
# BORDER AND SEPARATOR COLORS
# ============================================================================

BORDER_DARK = "#444444"           # Dark border color
BORDER_MEDIUM = "#555555"         # Medium border color
BORDER_LIGHT = "#666666"          # Light border color
BORDER_HEADER = "#555555"         # Header border
GRID_LINE = "#252525"             # Grid line color
GRID_LINE_DARK = "#2b2b2b"        # Dark grid line

# ============================================================================
# REFERENCE/FORMULA COLORS
# ============================================================================

COLOR_REF_BLUE = "#54B8FF"        # Reference color blue
COLOR_REF_RED = "#FF3C3C"         # Reference color red
COLOR_REF_GREEN = "#39FF92"       # Reference color green
COLOR_REF_PURPLE = "#BE6AFF"      # Reference color purple

# ============================================================================
# DRAWING AND GRAPHIC COLORS
# ============================================================================

COLOR_SELECTION_BOX_BORDER = "#00FFFF"      # Cyan selection box border
COLOR_SELECTION_BOX_FILL = "rgba(255, 255, 255, 0.5)"  # White semi-transparent fill
COLOR_TRANSFORM_BORDER = "#00FFFF"          # Transform handler cyan border
COLOR_TRANSFORM_INDIVIDUAL = "#FF4FF0"      # Individual transform magenta border
COLOR_GRID_BACKGROUND = "#d3d3d3"           # Canvas grid background (light grey)
COLOR_GRID = "#a9a9a9"                      # Grid color (dark grey)

# Canvas drawing defaults
COLOR_DEFAULT_SHAPE_FILL = "rgba(200, 200, 200, 100)"  # Semi-transparent grey
COLOR_DEFAULT_SHAPE_FILL_LIGHT = "#F15B5B"  # Light red default shape fill
COLOR_DEFAULT_SHAPE_BORDER = "#000000"      # Black border for shapes

# ============================================================================
# FOCUS/DEBUG COLORS
# ============================================================================

COLOR_ERROR = "#FF0000"           # Error state
COLOR_WARNING = "#FFA500"         # Warning state
COLOR_SUCCESS = "#00AA00"         # Success state
COLOR_DEBUG_BORDER = "transparent"    # Debug/focus border (transparent)

# ============================================================================
# PATTERN AND GRADIENT COLORS
# ============================================================================

PATTERN_FG_DEFAULT = "#000000"    # Pattern foreground default (black)
PATTERN_BG_DEFAULT = "#ffffff"    # Pattern background default (white)
GRADIENT_COLOR_1_DEFAULT = "#D0CECE"  # Gradient color 1 default (light grey)
GRADIENT_COLOR_2_DEFAULT = "#596978"  # Gradient color 2 default (slate grey)

# ============================================================================
# UTILITY COLOR FUNCTIONS
# ============================================================================

def get_text_color(bg_color_hex: str) -> str:
    """
    Determine appropriate text color (white or black) based on background brightness.
    
    Args:
        bg_color_hex: Background color in hex format (e.g., "#ffffff")
        
    Returns:
        Text color hex string (white or black)
    """
    from PySide6.QtGui import QColor
    
    try:
        color = QColor(bg_color_hex)
        # If background is light, use dark text; if dark, use light text
        return TEXT_PRIMARY if color.lightnessF() < 0.5 else TEXT_DARK
    except:
        return TEXT_PRIMARY
