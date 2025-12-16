"""
Centralized color theme for the HMI Designer Application.
All color values are defined here to ensure consistency across the entire application.
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
COLOR_SELECTED = "#0d47a1"        # Tree item selected (dark blue)
COLOR_SELECTED_ALT = "#2a82da"    # Alternative selected color (lighter blue)
COLOR_SELECTION_HIGHLIGHT = "#42B8E6"  # Selection highlight
COLOR_SELECTION_HIGHLIGHT_ALT = "rgba(42, 130, 218, 128)"  # Selection with transparency

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
COLOR_GRID_BACKGROUND = "#lightgrey"        # Canvas grid background
COLOR_GRID = "#darkgray"                    # Grid color

# Canvas drawing defaults
COLOR_DEFAULT_SHAPE_FILL = "rgba(200, 200, 200, 100)"  # Semi-transparent grey
COLOR_DEFAULT_SHAPE_BORDER = "#000000"      # Black border for shapes

# ============================================================================
# FOCUS/DEBUG COLORS
# ============================================================================

COLOR_ERROR = "#FF0000"           # Error state
COLOR_WARNING = "#FFA500"         # Warning state
COLOR_SUCCESS = "#00AA00"         # Success state
COLOR_DEBUG_BORDER = "#0078D7"    # Debug/focus border (Microsoft Blue)

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
