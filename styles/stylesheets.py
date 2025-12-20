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
            background-color: transparent;
            color: {c.TEXT_PRIMARY};
        }}
        QTreeWidget::item:hover {{
            background-color: {c.COLOR_HOVER};
            color: {c.TEXT_PRIMARY};
        }}
    """


def get_project_tree_stylesheet(expand_icon_path: str = "", collapse_icon_path: str = "", 
                                  vline_path: str = "", branch_more_path: str = "", 
                                  branch_end_path: str = "") -> str:
    """
    Generate advanced stylesheet for project tree widgets with branch lines.
    
    Args:
        expand_icon_path: Path to expand icon (plus/add icon)
        collapse_icon_path: Path to collapse icon (minus/subtract icon)
        vline_path: Path to vertical line SVG
        branch_more_path: Path to T-junction branch SVG
        branch_end_path: Path to L-corner branch SVG
        
    Returns:
        QSS stylesheet string for advanced tree widgets with hierarchy lines
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
            show-decoration-selected: 1;
        }}
        QTreeWidget::item {{
            padding: 4px 2px;
            margin-left: 0px;
            color: {c.TEXT_PRIMARY};
            min-height: 20px;
        }}
        QTreeWidget::item:selected {{
            background-color: transparent;
            color: {c.TEXT_PRIMARY};
        }}
        QTreeWidget::item:hover {{
            background-color: {c.COLOR_HOVER};
            color: {c.TEXT_PRIMARY};
        }}

        
        /* Default branch styling */
        QTreeWidget::branch {{
            width: 12px;
            height: 12px;
            padding-top: 7px;
            padding-left: 0px;
            padding-right: 2px;
            padding-bottom: 7px;
            background-color: transparent;
        }}
        
        /* Branch with expand button (collapsed with children) */
        QTreeWidget::branch:has-children:!has-siblings:closed {{
            image: url("{expand_icon_path}");
            border-image: url("{branch_end_path}") 0;
        }}
        QTreeWidget::branch:closed:has-children:has-siblings {{
            image: url("{expand_icon_path}");
            border-image: url("{branch_more_path}") 0;
        }}
        
        /* Branch with collapse button (expanded with children) */
        QTreeWidget::branch:open:has-children:!has-siblings {{
            image: url("{collapse_icon_path}");
            border-image: url("{branch_end_path}") 0;
        }}
        QTreeWidget::branch:open:has-children:has-siblings {{
            image: url("{collapse_icon_path}");
            border-image: url("{branch_more_path}") 0;
        }}
        
        /* Vertical line for siblings (items that have more siblings below) - full height centered */
        QTreeWidget::branch:has-siblings:!adjoins-item {{
            border-image: url("{vline_path}") 0;
        }}
        
        /* T-junction: vertical line + horizontal line for items with siblings below */
        QTreeWidget::branch:has-siblings:adjoins-item {{
            border-image: url("{branch_more_path}") 0;
        }}
        
        /* L-corner for last item in a group (no siblings below) */
        QTreeWidget::branch:!has-siblings:adjoins-item {{
            border-image: url("{branch_end_path}") 0;
        }}
        
        QHeaderView::section {{
            background-color: {c.BG_DARK_QUATERNARY};
            color: {c.TEXT_PRIMARY};
            padding: 3px;
            border: 1px solid {c.BORDER_HEADER};
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
        QToolButton {{
            border-radius: 3px;
            padding: 3px;
        }}
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
        QToolButton:hover {{
            background-color: {c.COLOR_HOVER};
        }}
        QToolButton:checked, QToolButton:pressed {{
            background-color: #707070;
            border: 1px solid {c.BORDER_LIGHT};
        }}
        QToolButton:checked:hover {{
            background-color: #808080;
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
            background-color: transparent;
            color: {c.TEXT_PRIMARY};
        }}
        QListWidget::item:hover {{
            background-color: {c.COLOR_HOVER};
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
# TOOLBAR STYLESHEET
# ============================================================================

def get_toolbar_stylesheet() -> str:
    """
    Generate stylesheet for toolbars.
    
    Returns:
        QSS stylesheet string for toolbars
    """
    return f"""
        QToolBar {{
            background-color: {c.BG_DARK_SECONDARY};
            border: 1px solid {c.BORDER_DARK};
            spacing: 3px;
            padding: 2px;
        }}
        QToolBar::separator {{
            background-color: {c.BORDER_DARK};
            width: 1px;
            margin: 4px;
        }}
            QToolBar QSpinBox, QToolBar QComboBox {{
            min-height: 24px;
        }}
    """


# ============================================================================
# MENU AND MENU BAR STYLESHEETS
# ============================================================================

def get_menu_stylesheet() -> str:
    """
    Generate stylesheet for menus and menu bars.
    
    Returns:
        QSS stylesheet string for menus
    """
    return f"""
        QMenuBar {{
            background-color: {c.BG_DARK_SECONDARY};
            color: {c.TEXT_PRIMARY};
        }}
        QMenuBar::item:selected {{
            background-color: {c.COLOR_HOVER};
        }}
        QMenu {{
            background-color: {c.BG_DARK_SECONDARY};
            color: {c.TEXT_PRIMARY};
            border: 1px solid {c.BORDER_DARK};
        }}
        QMenu::item:selected {{
            background-color: {c.COLOR_HOVER};
            color: {c.TEXT_PRIMARY};
        }}
        QComboBox QAbstractItemView {{
            background-color: {c.BG_DARK_SECONDARY};
            color: {c.TEXT_PRIMARY};
            selection-background-color: {c.COLOR_HOVER};
            selection-color: {c.TEXT_PRIMARY};
            outline: none;
        }}
        QPushButton:hover {{
            background-color: {c.COLOR_HOVER};
        }}
    """


# ============================================================================
# EXPORT ALL STYLESHEETS AS DICTIONARY
# ============================================================================

STYLESHEETS = {
    "tree_widget": get_tree_widget_stylesheet,
    "project_tree": get_project_tree_stylesheet,
    "status_bar": get_status_bar_stylesheet,
    "tool_button": get_tool_button_stylesheet,
    "formula_hint": get_formula_hint_stylesheet,
    "completer_popup": get_completer_popup_stylesheet,
    "gradient": get_gradient_qss,
    "color_button": get_color_button_stylesheet,
    "pattern_widget": get_pattern_widget_stylesheet,
    "error_text": get_error_text_stylesheet,
    "normal_text": get_normal_text_stylesheet,
    "menu": get_menu_stylesheet,
    "toolbar": get_toolbar_stylesheet,
}
