"""
Centralized stylesheet generator for the HMI Designer Application.
All QSS/CSS style strings are generated using theme variables.
"""

from styles import colors as c


# ============================================================================
# TREE WIDGET STYLESHEETS
# ============================================================================

def get_tree_widget_stylesheet() -> str:
    """
    Generate stylesheet for tree widgets used in docking windows.
    
    Returns:
        QSS stylesheet string for tree widgets
    """
    return f"""
        QTreeWidget {{
            background-color: {c.BG_DARK_PRIMARY};
            color: {c.TEXT_PRIMARY};
            border: 1px solid {c.BORDER_DARK};
        }}
        QTreeWidget::item:selected {{
            background-color: {c.COLOR_SELECTED_ALT};
            color: {c.TEXT_PRIMARY};
        }}
    """


def get_project_tree_stylesheet(expand_icon_path: str = "", collapse_icon_path: str = "") -> str:
    """
    Generate advanced stylesheet for project tree widgets.
    
    Args:
        expand_icon_path: Path to expand icon
        collapse_icon_path: Path to collapse icon
        
    Returns:
        QSS stylesheet string for advanced tree widgets
    """
    return f"""
        QTreeWidget {{
            border: none;
            background-color: {c.BG_DARK_SECONDARY};
            alternate-background-color: {c.BG_DARK_SECONDARY};
            color: {c.TEXT_PRIMARY};
            gridline-color: {c.BG_DARK_SECONDARY};
            outline: none;
            margin-left: 0px;
        }}
        QTreeWidget::item {{
            padding: 4px 2px;
            border-left: 2px solid {c.ACCENT_GREEN};
            margin-left: 0px;
            color: {c.TEXT_PRIMARY};
        }}
        QTreeWidget::item:selected {{
            background-color: {c.COLOR_SELECTED_ALT};
            border-left: 2px solid {c.ACCENT_GREEN};
            color: {c.TEXT_PRIMARY};
        }}
        QTreeWidget::branch:has-children:closed {{
            image: url("{expand_icon_path}");
            background-color: transparent;
            width: 20px;
            height: 20px;
        }}
        QTreeWidget::branch:has-children:open {{
            image: url("{collapse_icon_path}");
            background-color: transparent;
            width: 20px;
            height: 20px;
        }}
        QTreeWidget::branch:has-siblings {{
            border-image: none;
        }}
        QTreeWidget::branch {{
            background-color: transparent;
            margin-right: 4px;
            margin-left: 4px;
            margin-top: 4px;
            margin-bottom: 4px;
        }}
        QHeaderView::section {{
            background-color: {c.BG_DARK_QUATERNARY};
            color: {c.TEXT_PRIMARY};
            padding: 3px;
            border: 1px solid {c.BORDER_HEADER};
        }}
    """


def get_layers_tree_stylesheet(expand_icon_path: str = "", collapse_icon_path: str = "") -> str:
    """
    Generate stylesheet for layers tree widget with enhanced spacing and icon sizing.
    
    Args:
        expand_icon_path: Path to expand icon
        collapse_icon_path: Path to collapse icon
        
    Returns:
        QSS stylesheet string for layers tree widget
    """
    return f"""
        QTreeWidget {{
            border: none;
            background-color: {c.BG_DARK_SECONDARY};
            alternate-background-color: {c.BG_DARK_SECONDARY};
            color: {c.TEXT_PRIMARY};
            gridline-color: {c.BG_DARK_SECONDARY};
            outline: none;
            margin-left: 0px;
        }}
        QTreeWidget::item {{
            padding: 4px 2px;
            border-left: 2px solid {c.ACCENT_GREEN};
            margin-left: 0px;
            color: {c.TEXT_PRIMARY};
        }}
        QTreeWidget::item:selected {{
            background-color: {c.COLOR_SELECTED_ALT};
            border-left: 2px solid {c.ACCENT_GREEN};
            color: {c.TEXT_PRIMARY};
        }}
        QTreeWidget::branch:has-children:closed {{
            image: url("{expand_icon_path}");
            background-color: transparent;
            width: 24px;
            height: 24px;
        }}
        QTreeWidget::branch:has-children:open {{
            image: url("{collapse_icon_path}");
            background-color: transparent;
            width: 24px;
            height: 24px;
        }}
        QTreeWidget::branch:has-siblings {{
            border-image: none;
        }}
        QTreeWidget::branch {{
            background-color: transparent;
            margin-right: 6px;
            margin-left: 4px;
            margin-top: 6px;
            margin-bottom: 6px;
        }}
    """


# ============================================================================
# STATUS BAR STYLESHEETS
# ============================================================================

def get_status_bar_stylesheet() -> str:
    """
    Generate stylesheet for status bar.
    
    Returns:
        QSS stylesheet string for status bar
    """
    return f"""
        QStatusBar {{
            background-color: {c.BG_STATUS_BAR};
            color: {c.TEXT_PRIMARY};
        }}
        QStatusBar::item {{
            border: none;
        }}
        QLabel {{
            color: {c.TEXT_PRIMARY};
            padding-left: 2px;
            padding-right: 2px;
        }}
    """


# ============================================================================
# BUTTON AND TOOLBAR STYLESHEETS
# ============================================================================

def get_tool_button_stylesheet() -> str:
    """
    Generate stylesheet for tool buttons (on/off states).
    
    Returns:
        QSS stylesheet string for tool buttons
    """
    return f"""
        QToolButton[state="on"] {{
            background-color: {c.ACCENT_GREEN};
            color: {c.TEXT_PRIMARY};
            border: 1px solid {c.ACCENT_GREEN_DARK};
        }}
        QToolButton[state="off"] {{
            background-color: {c.ACCENT_YELLOW};
            color: black;
            border: 1px solid {c.ACCENT_YELLOW_DARK};
        }}
    """


# ============================================================================
# DIALOG AND POPUP STYLESHEETS
# ============================================================================

def get_formula_hint_stylesheet() -> str:
    """
    Generate stylesheet for formula hint popups.
    
    Returns:
        QSS stylesheet string for formula hints
    """
    return f"""
        background-color: {c.BG_DARK_QUATERNARY};
        border: 1px solid {c.BORDER_MEDIUM};
        padding: 4px;
        font-size: {9}pt;
        color: {c.TEXT_PRIMARY};
    """


def get_completer_popup_stylesheet() -> str:
    """
    Generate stylesheet for autocomplete/completer popups.
    
    Returns:
        QSS stylesheet string for completer popups
    """
    return f"""
        QListWidget {{
            background-color: {c.BG_SPREADSHEET};
            border: 1px solid {c.BORDER_MEDIUM};
        }}
        QListWidget::item {{
            color: {c.TEXT_PRIMARY};
        }}
        QListWidget::item:selected {{
            background-color: {c.COLOR_SELECTED_ALT};
            color: {c.TEXT_PRIMARY};
        }}
    """


# ============================================================================
# SPREADSHEET/TABLE STYLESHEETS (Dynamic Generation)
# ============================================================================

def get_spreadsheet_cell_color(is_selected: bool = False, is_header: bool = False) -> str:
    """
    Get background color for spreadsheet cells.
    
    Args:
        is_selected: Whether the cell is selected
        is_header: Whether the cell is a header cell
        
    Returns:
        Color hex string
    """
    if is_header:
        return c.BG_DARK_QUATERNARY
    elif is_selected:
        return c.COLOR_SELECTION_HIGHLIGHT_ALT
    else:
        return c.BG_SPREADSHEET


def get_spreadsheet_border_color() -> str:
    """Get border color for spreadsheet cells."""
    return c.BORDER_MEDIUM


# ============================================================================
# GRADIENT STYLESHEET HELPERS
# ============================================================================

def get_gradient_qss(color1: str, color2: str) -> str:
    """
    Generate QSS for a linear gradient.
    
    Args:
        color1: First gradient color (hex)
        color2: Second gradient color (hex)
        
    Returns:
        QSS string with gradient definition
    """
    return f"qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {color1}, stop:1 {color2})"


# ============================================================================
# COLOR PICKER AND WIDGET STYLESHEETS
# ============================================================================

def get_color_button_stylesheet(color_hex: str, is_selected: bool = False) -> str:
    """
    Generate stylesheet for color picker buttons.
    
    Args:
        color_hex: Button background color (hex)
        is_selected: Whether the button is selected/focused
        
    Returns:
        QSS stylesheet string for color button
    """
    border_color = c.COLOR_DEBUG_BORDER if is_selected else c.BORDER_MEDIUM
    border_width = "2px" if is_selected else "1px"
    text_color = c.get_text_color(color_hex)
    
    return f"""
        background-color: {color_hex};
        color: {text_color};
        border: {border_width} solid {border_color};
        padding: 2px;
        border-radius: 2px;
    """


# ============================================================================
# PATTERN WIDGET STYLESHEET
# ============================================================================

def get_pattern_widget_stylesheet(color_hex = None) -> str:
    """
    Generate stylesheet for pattern widgets.
    
    Args:
        color_hex: Override background color (hex)
        
    Returns:
        QSS stylesheet string for pattern widget
    """
    bg_color = color_hex if color_hex else c.TEXT_PRIMARY
    border_color = c.BORDER_MEDIUM
    
    return f"""
        background-color: {bg_color};
        border: 1px solid {border_color};
    """


# ============================================================================
# VALIDATION/ERROR STYLESHEETS
# ============================================================================

def get_error_text_stylesheet() -> str:
    """Generate stylesheet for error text."""
    return f"color: {c.COLOR_ERROR};"


def get_normal_text_stylesheet() -> str:
    """Generate stylesheet for normal text."""
    return f"color: {c.TEXT_PRIMARY};"


# ============================================================================
# EXPORT ALL STYLESHEETS AS DICTIONARY
# ============================================================================

STYLESHEETS = {
    "tree_widget": get_tree_widget_stylesheet,
    "project_tree": get_project_tree_stylesheet,
    "layers_tree": get_layers_tree_stylesheet,
    "status_bar": get_status_bar_stylesheet,
    "tool_button": get_tool_button_stylesheet,
    "formula_hint": get_formula_hint_stylesheet,
    "completer_popup": get_completer_popup_stylesheet,
    "gradient": get_gradient_qss,
    "color_button": get_color_button_stylesheet,
    "pattern_widget": get_pattern_widget_stylesheet,
    "error_text": get_error_text_stylesheet,
    "normal_text": get_normal_text_stylesheet,
}
