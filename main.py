import sys
import os
import subprocess
import ctypes
import re
import shlex
import traceback
import sqlite3
from datetime import datetime

from PyQt5.QtGui import QDesktopServices
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtWidgets import (
    QApplication,
    QMenuBar,
    QMainWindow,
    QWidget,
    QAction,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QInputDialog,
    QTableWidget,
    QTableWidgetItem,
    QLabel,
    QStyleFactory,
    QPushButton, 
    QDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QTextEdit,
    QHeaderView,
    QComboBox,
    QPushButton,
    QFileDialog,
    QFormLayout,
    QCheckBox,
    QListWidget,
    QSplitter,
    QMenu,
)

###############################################################################
# Define the Light/Dark stylesheets
###############################################################################
LIGHT_STYLESHEET = """
QMainWindow {
    background-color: #f0f0f0;
}
QLabel {
    font-size: 14px;
    color: #000000;
}
QLineEdit {
    font-size: 14px;
    padding: 4px;
    background-color: #ffffff;
    color: #000000;
}
QTableWidget {
    background-color: #ffffff;
    gridline-color: #cccccc;
    font-size: 14px;
    color: #000000;
}
QTableWidget::item:selected {
    background-color: #0078d7;
    color: #ffffff;
}
QPushButton {
    font-size: 14px;
    padding: 6px 12px;
    color: #000000;
    background-color: #e6e6e6;
    border: 1px solid #cccccc;
    border-radius: 5px;
}
QPushButton:disabled {
    background-color: #f0f0f0;
    border: 1px inset #cccccc;
    color: #a0a0a0;
}
QPushButton:hover:!disabled {
    background-color: #d9d9d9;
}
QToolTip {
    background-color: #222222;
    color: #ffffff;
    border: 1px solid #aaaaaa;
    padding: 5px;
    font-size: 12px;
}
QListWidget {
    background-color: #ffffff;
    color: #000000;
}
QListWidget::item:selected {
    background-color: #0078d7;
    color: #ffffff;
}
"""

DARK_STYLESHEET = """
QMainWindow {
    background-color: #2b2b2b;
}
QDialog {
    background-color: #2b2b2b;
}
QLabel {
    font-size: 14px;
    color: #dddddd;
}
QLineEdit {
    font-size: 14px;
    padding: 4px;
    background-color: #3b3b3b;
    color: #ffffff;
}
QTableWidget {
    background-color: #3b3b3b;
    color: #ffffff;
    gridline-color: #555555;
    font-size: 14px;
}
QTableWidget::item:selected {
    background-color: #0078d7;
    color: #ffffff;
}
QPushButton {
    font-size: 14px;
    padding: 6px 12px;
    color: #ffffff;
    background-color: #444444;
    border: 1px solid #666666;
    border-radius: 5px;
}
QPushButton:disabled {
    background-color: #333333;
    border: 1px inset #222222;
    color: #666666;
}
QPushButton:hover:!disabled {
    background-color: #555555;
}
QToolTip {
    background-color: #222222;
    color: #ffffff;
    border: 1px solid #aaaaaa;
    padding: 5px;
    font-size: 12px;
}
QListWidget {
    background-color: #3b3b3b;
    color: #ffffff;
}
QListWidget::item:selected {
    background-color: #555555;
    color: #ffffff;
}
"""

###############################################################################
# Define a small toggle switch (styled QCheckBox) to switch between light/dark
###############################################################################

TOGGLE_SWITCH_QSS = """
QCheckBox {
    spacing: 0px;
}
QCheckBox::indicator {
    width: 50px;
    height: 25px;
    border-radius: 12px;
}
QCheckBox::indicator:unchecked {
    background-color: qlineargradient(
        spread:pad, x1:0, y1:0, x2:1, y2:0, 
        stop:0 black, stop:0.5 black, stop:0.5 white, stop:1 white
    );
}
QCheckBox::indicator:checked {
    background-color: qlineargradient(
        spread:pad, x1:0, y1:0, x2:1, y2:0, 
        stop:0 white, stop:0.5 white, stop:0.5 black, stop:1 black
    );
}
QCheckBox::indicator:unchecked:hover {
    background-color: qlineargradient(
        spread:pad, x1:0, y1:0, x2:1, y2:0, 
        stop:0 #333333, stop:0.5 #333333, stop:0.5 #dddddd, stop:1 #dddddd
    );
}
QCheckBox::indicator:checked:hover {
    background-color: qlineargradient(
        spread:pad, x1:0, y1:0, x2:1, y2:0, 
        stop:0 #dddddd, stop:0.5 #dddddd, stop:0.5 #333333, stop:1 #333333
    );
}
"""

###############################################################################
# Set path
###############################################################################

def get_app_folder():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))

def get_database_path():
    return os.path.join(get_app_folder(), "commander.db")

###############################################################################
# Theme toggle switch
###############################################################################

class ThemeToggleSwitch(QCheckBox):
    """
    A QCheckBox styled as a small toggle switch.
    We'll rely on toggled(bool) to know if it's ON (dark) or OFF (light).
    """
    def __init__(self, parent=None, checked=False):
        super().__init__(parent)
        self.setChecked(checked)
        self.setText("")  # No label text
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(TOGGLE_SWITCH_QSS)

    def on_link_file(self):
        """
        Let the user pick a .bat or .ps1 file and store that path in self.command_edit.
        """
        file_filter = "Scripts (*.bat *.ps1);;All Files (*)"
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Script", "", file_filter)
        if file_path:
            self.command_edit.setText(file_path)

    def on_ok_clicked(self):
        """
        Gather all data, store in self.result_data, and accept the dialog.
        """
        name = self.name_edit.text().strip()
        command = self.command_edit.text().strip()
        description = self.description_edit.text().strip()
        tags_str = self.tags_edit.text().strip()
        category = self.category_edit.text().strip()

        # Convert tags to a list
        if tags_str:
            tags_list = [tag.strip() for tag in tags_str.split(",")]
        else:
            tags_list = []

        self.result_data = {
            "name": name,
            "command": command,
            "description": description,
            "tags": tags_list,
            "category": category
        }
        self.accept()
    
    def get_data(self):
        """
        Returns the final data from the dialog as a dict.
        """
        return self.result_data
    
###############################################################################
# Standard Windows Admin-check logic (if you're still using admin re-launch)
###############################################################################

def is_user_admin():
    """
    Returns True if the current Python process is running with admin privileges (Windows).
    """
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def relaunch_as_admin():
    """
    Relaunches the current script with admin rights via ShellExecuteW.
    Returns True if relaunch was attempted, False if already admin or any error occurred.
    """
    if is_user_admin():
        return False  # already admin

    try:
        # Re-run the script with 'runas' param
        params = " ".join(sys.argv[1:])  # pass existing command line args if needed
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, sys.argv[0] + " " + params, None, 1)
        return True
    except Exception as e:
        #print("Failed to elevate:", e)
        return False
    
###############################################################################
# Commander Class
###############################################################################

class Commander(QMainWindow):
    def __init__(self):
        super().__init__()
        self.shortcuts_data = []

        # This new list will store (shortcut, original_index) for the currently displayed table rows
        self.displayed_pairs = []

        # Set a default theme before initializing the UI
        self.current_theme = "light"  # Default to light theme

        # Track which category is selected (None => show all)
        self.selected_category = None

        self.current_sort_method = "newest"  # Default sorting method

        # Window Title & Initial Size
        self.setWindowTitle("Commander")
        self.setMaximumSize(1920, 1080)  # Prevent extreme stretching
        self.setMinimumSize(800, 400)
        self.resize(1000, 600)

        # Keep track of two-step confirm state
        self.confirmation_pending = False

        self.load_shortcuts()  # Load shortcuts and settings

        self.initUI()  # Initialize the UI components, including self.table

        self.apply_theme(self.current_theme)  # Apply the loaded theme after UI initialization

        # Initially show all shortcuts
        self.displayed_pairs = [(s, i) for i, s in enumerate(self.shortcuts_data)]
        self.sort_table(self.current_sort_method)  # Sort table after initializing UI
        self.populate_table(self.displayed_pairs)  # Populate the table

    def resizeEvent(self, event):
        font_size = max(12, self.width() // 100)  # Scale font size
        self.setStyleSheet(f"""
            QTableWidget {{
                font-size: {font_size}px;
            }}
            QPushButton {{
                font-size: {font_size}px;
            }}
        """)
        super().resizeEvent(event)

    def init_menu(self):
        # Create menu bar
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("File")

        new_action = QAction("Add Shortcut", self)
        new_action.triggered.connect(self.on_add_shortcut)
        file_menu.addAction(new_action)

        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Edit menu
        edit_menu = menubar.addMenu("Edit")

        add_category_action = QAction("Add Category", self)
        edit_menu.addAction(add_category_action)

        remove_unused_action = QAction("Remove Unused Categories", self)
        remove_unused_action.triggered.connect(self.remove_unused_categories)
        edit_menu.addAction(remove_unused_action)

        preferences_menu = edit_menu.addMenu("Preferences")

        sort_newest_action = QAction("Sort by Newest", self)
        sort_newest_action.triggered.connect(lambda: self.sort_table("newest"))
        preferences_menu.addAction(sort_newest_action)

        sort_alpha_action = QAction("Sort Alphabetically", self)
        sort_alpha_action.triggered.connect(lambda: self.sort_table("alphabetically"))
        preferences_menu.addAction(sort_alpha_action)

        sort_used_action = QAction("Sort by Most Used", self)
        sort_used_action.triggered.connect(lambda: self.sort_table("most_used"))
        preferences_menu.addAction(sort_used_action)

        # View menu
        view_menu = menubar.addMenu("View")

        refresh_action = QAction("Refresh", self)
        refresh_action.triggered.connect(self.refresh_table)  # Fix: Use self.refresh_table instead of self.filter_table
        view_menu.addAction(refresh_action)

        toggle_theme_action = QAction("Toggle Dark Mode", self)
        toggle_theme_action.triggered.connect(lambda: self.theme_toggle_switch.toggle())
        view_menu.addAction(toggle_theme_action)

        # Help menu
        help_menu = menubar.addMenu("Help")

        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)

        documentation_action = QAction("Documentation", self)
        documentation_action.triggered.connect(self.open_documentation)
        help_menu.addAction(documentation_action)


    def open_documentation(self):
        """
        Open the README.md file located in the same directory as the script.
        """
        readme_path = os.path.join(get_app_folder(), "README.md")
        if os.path.exists(readme_path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(readme_path))
        else:
            QMessageBox.warning(
                self,
                "Documentation Not Found",
                "The README.md file could not be found in the application directory.",
                QMessageBox.Ok
            )
            
    def show_about_dialog(self):
        QMessageBox.information(
            self,
            "About Commander",
            "Commander Application\nVersion 1.0\nA handy tool for managing shortcuts.",
            QMessageBox.Ok
        )
    def sort_table(self, method):
        """
        Sorts the table based on the selected method.
        """
        print(f"Sorting table using method: {method}")
        self.current_sort_method = method  # Track the current sorting method
        self.save_sorting_preference(method)  # Persist the user's preference

        def safe_get(data, key, default):
            """
            Safely retrieves the value of a key from a dictionary, or returns a default.
            """
            return data.get(key, default)

        # Sort based on the chosen method
        if method == "newest":
            sorted_pairs = sorted(
                self.displayed_pairs,
                key=lambda x: safe_get(x[0], "updated_at", ""),
                reverse=True
            )
        elif method == "alphabetically":
            sorted_pairs = sorted(
                self.displayed_pairs,
                key=lambda x: safe_get(x[0], "name", "").lower()
            )
        elif method == "most_used":
            sorted_pairs = sorted(
                self.displayed_pairs,
                key=lambda x: safe_get(x[0], "usage_count", 0),
                reverse=True
            )
        else:
            print(f"Unknown sorting method: {method}")
            return

        # Debug: Check sorted pairs
        print(f"Sorted pairs: {sorted_pairs}")

        self.populate_table(sorted_pairs)

    def init_table_context_menu(self):
        """
        Initializes the context menu for the table with right-click options.
        """
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_table_context_menu)

    def show_table_context_menu(self, position):
        """
        Displays the context menu at the given position.
        """
        menu = QMenu(self)

        # Add actions to the context menu
        execute_action = menu.addAction("Execute")
        copy_command_action = menu.addAction("Copy Command")
        refresh_action = menu.addAction("Refresh")
        add_action = menu.addAction("Add")
        edit_action = menu.addAction("Edit")
        delete_action = menu.addAction("Delete")

        # Map actions to their respective handlers
        execute_action.triggered.connect(self.confirm_and_execute)
        copy_command_action.triggered.connect(self.copy_selected_command)
        refresh_action.triggered.connect(self.refresh_table)
        add_action.triggered.connect(self.on_add_shortcut)
        edit_action.triggered.connect(self.on_edit_shortcut)
        delete_action.triggered.connect(self.on_delete_shortcut)

        # Show the context menu
        menu.exec_(self.table.viewport().mapToGlobal(position))

    def confirm_and_execute(self):
        """
        Pops up a confirmation dialog and executes the selected command if confirmed.
        """
        selected_items = self.table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "No Selection", "Please select a shortcut to execute.")
            return

        # Get the selected row and its command
        row = selected_items[0].row()
        shortcut, original_index = self.displayed_pairs[row]
        command = shortcut.get("command", "").strip()

        if not command:
            QMessageBox.warning(self, "No Command", "The selected shortcut has no command to execute.")
            return

        # Show confirmation dialog
        reply = QMessageBox.question(
            self,
            "Confirm Execution",
            f"Are you sure you want to execute the command:\n\n{command}",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.run_selected_command(row)

    def save_sorting_preference(self, method):
        """
        Save the current sorting preference to the database.
        """
        self.current_sort_method = method  # Update the tracking variable

        conn = sqlite3.connect(get_database_path())
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO settings (key, value) VALUES ('sort_preference', ?)
        """, (method,))
        conn.commit()
        conn.close()
    ###########################################################################
    # SIDEBAR / CATEGORY
    ###########################################################################
    def remove_unused_categories(self):
        """
        Remove categories that are no longer associated with any shortcuts.
        """
        conn = sqlite3.connect(get_database_path())
        cursor = conn.cursor()

        # Delete unused categories
        cursor.execute("""
            DELETE FROM categories
            WHERE id NOT IN (SELECT DISTINCT category_id FROM shortcuts)
        """)

        conn.commit()
        conn.close()

    def update_category_list(self):
        """
        Gather unique category names from the database.
        """
        conn = sqlite3.connect(get_database_path())
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM categories ORDER BY name")
        self.available_categories = [row[0] for row in cursor.fetchall()]
        conn.close()

    def update_category_sidebar(self):
        """
        Clear and repopulate the category_list QListWidget.
        Includes an '(All Categories)' item to reset filter.
        """
        self.category_list.clear()
        
        # Fetch updated categories from the database
        conn = sqlite3.connect(get_database_path())
        cursor = conn.cursor()
        cursor.execute("""
            SELECT name
            FROM categories
            WHERE name IS NOT NULL AND TRIM(name) != ''
            ORDER BY name
        """)
        categories = [row[0] for row in cursor.fetchall()]
        conn.close()

        # Add an item to show all categories
        self.category_list.addItem("(All Categories)")

        # Add the individual categories
        for cat in categories:
            self.category_list.addItem(cat)

        # Enable context menu on category_list
        self.category_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.category_list.customContextMenuRequested.connect(self.show_category_context_menu)

    def show_category_context_menu(self, position):
        """
        Show a context menu for the category sidebar.
        """
        # Get the selected item
        selected_item = self.category_list.itemAt(position)
        if not selected_item:
            return

        # Prevent context menu for "(All Categories)"
        if selected_item.text() == "(All Categories)":
            return

        # Create the context menu
        menu = QMenu(self)
        delete_action = menu.addAction("Delete Category")
        edit_action = menu.addAction("Edit Category")

        # Execute the menu
        action = menu.exec_(self.category_list.viewport().mapToGlobal(position))

        # Handle the action
        if action == delete_action:
            self.delete_category(selected_item.text())
        elif action == edit_action:
            self.edit_category(selected_item.text())
    def delete_category(self, category_name):
        """
        Delete a category from the database.
        """
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete the category '{category_name}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            conn = sqlite3.connect(get_database_path())
            cursor = conn.cursor()

            # Delete the category
            cursor.execute("DELETE FROM categories WHERE name = ?", (category_name,))

            conn.commit()
            conn.close()

            # Refresh the sidebar
            self.update_category_sidebar()
            self.refresh_table()
    def edit_category(self, old_category_name):
        """
        Edit a category's name in the database.
        """
        new_category_name, ok = QInputDialog.getText(
            self,
            "Edit Category",
            "Enter new category name:",
            QLineEdit.Normal,
            old_category_name
        )

        if ok and new_category_name.strip():
            conn = sqlite3.connect(get_database_path())
            cursor = conn.cursor()

            # Update the category name
            cursor.execute("""
                UPDATE categories
                SET name = ?
                WHERE name = ?
            """, (new_category_name.strip(), old_category_name))

            conn.commit()
            conn.close()

            # Refresh the sidebar
            self.update_category_sidebar()
            self.refresh_table()

    def on_category_selected(self, item):
        """
        Called when the user clicks a category in the sidebar.
        If '(All Categories)', reset self.selected_category to None.
        Otherwise, set self.selected_category to the category text.
        Then call filter_table().
        """
        cat_text = item.text()
        if cat_text == "(All Categories)":
            self.selected_category = None
        else:
            self.selected_category = cat_text

        self.filter_table()

    ###########################################################################
    # UI SETUP
    ###########################################################################
    def initUI(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.init_menu()
        # Create the main horizontal layout
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)  # Add margins
        main_layout.setSpacing(10)  # Add spacing between components

        central_widget.setLayout(main_layout)
        
        # Create the splitter
        splitter = QSplitter(Qt.Horizontal)

        # 1) Left Sidebar: Category List
        self.category_list = QListWidget()
        self.category_list.itemClicked.connect(self.on_category_selected)
        # We'll call update_category_sidebar() after load_shortcuts to fill it

        splitter.addWidget(self.category_list)  # Add the category list to the splitter

        # 2) Right Panel
        right_panel = QVBoxLayout()

        # ========== Search Row ==========
        search_layout = QHBoxLayout()
        search_label = QLabel("Search:")
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search Current Category...")
        self.search_bar.setClearButtonEnabled(True)
        self.search_bar.textChanged.connect(self.filter_table)

        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_bar)

        # Add the toggle switch to the same row
        self.theme_toggle_switch = ThemeToggleSwitch(checked=(self.current_theme == "dark"))
        self.theme_toggle_switch.toggled.connect(self.on_theme_switch_toggled)
        search_layout.addWidget(self.theme_toggle_switch)

        right_panel.addLayout(search_layout)

        # ========== Table ==========
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Name", "Command", "Tags", "Category"])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.cellClicked.connect(self.on_table_select)
        self.init_table_context_menu()
        self.table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #666666;
                gridline-color: #444444;
                background-color: #3b3b3b;
                alternate-background-color: #2b2b2b;
            }
            QHeaderView::section {
                background-color: #555555;
                color: #ffffff;
                font-weight: bold;
                border: 1px solid #444444;
            }
            QTableWidget::item:selected {
                background-color: #0078d7;
                color: #ffffff;
            }
        """)
        right_panel.addWidget(self.table)
        

        # ========== CRUD + Bottom Layout ==========
        bottom_layout = QHBoxLayout()

        # Execute Button
        self.execute_button = QPushButton("Execute")
        self.execute_button.setEnabled(False)
        self.execute_button.clicked.connect(self.on_execute_clicked)

        # CRUD Buttons (Add, Edit, Delete)
        crud_layout = QHBoxLayout()

        self.add_button = QPushButton("Add Shortcut")
        self.add_button.clicked.connect(self.on_add_shortcut)
        crud_layout.addWidget(self.add_button)

        self.edit_button = QPushButton("Edit Shortcut")
        self.edit_button.clicked.connect(self.on_edit_shortcut)
        self.edit_button.setEnabled(False)
        crud_layout.addWidget(self.edit_button)

        self.delete_button = QPushButton("Delete Shortcut")
        self.delete_button.clicked.connect(self.on_delete_shortcut)
        self.delete_button.setEnabled(False)
        crud_layout.addWidget(self.delete_button)
        self.add_button.setMaximumWidth(150)
        self.edit_button.setMaximumWidth(150)
        self.delete_button.setMaximumWidth(150)
        self.execute_button.setMaximumWidth(200)

        right_panel.addLayout(crud_layout)

        # Info Label
        self.info_label = QLabel("")
        self.info_label.setStyleSheet(
            "color: #333333;" if self.current_theme == "light" else "color: #dddddd;"
        )

        bottom_layout.addWidget(self.execute_button)
        bottom_layout.addWidget(self.info_label)

        right_panel.addLayout(bottom_layout)

        # Wrap the right panel layout in a QWidget
        right_panel_widget = QWidget()
        right_panel_widget.setLayout(right_panel)

        # Add the right panel widget to the splitter
        splitter.addWidget(right_panel_widget)

        splitter.setStretchFactor(0, 1)  # Sidebar expands less
        splitter.setStretchFactor(1, 4)  # Table expands more
        splitter.setSizes([200, 800])  # Initial sizes (sidebar, table)


        # Set default sizes (adjust as needed for your desired ratio)
        splitter.setSizes([150, 400])  # Left panel starts with 1/3 width, right panel 2/3
        
        # Add the splitter to the main layout
        main_layout.addWidget(splitter)

        # Finally, update the category sidebar to show all categories
        self.update_category_sidebar()
        self.refresh_table()  # Ensures table is populated and sorted initially


    ###########################################################################
    # THEME LOGIC
    ###########################################################################
    def apply_theme(self, theme_name):
        """Applies the specified theme stylesheet to the QApplication."""
        if theme_name == "dark":
            QApplication.instance().setStyleSheet(DARK_STYLESHEET)
            if hasattr(self, 'info_label'):
                self.info_label.setStyleSheet("color: #dddddd;")  # Light text for dark background
        else:
            QApplication.instance().setStyleSheet(LIGHT_STYLESHEET)
            if hasattr(self, 'info_label'):
                self.info_label.setStyleSheet("color: #333333;")  # Dark text for light background

    def on_theme_switch_toggled(self, checked):
        """
        If 'checked' is True => 'dark' mode; otherwise => 'light'.
        """
        self.current_theme = "dark" if checked else "light"
        #print(f"Theme toggled. New theme: {self.current_theme}")
        self.apply_theme(self.current_theme)
        self.save_theme_preference()  # Save the new preference

    def save_theme_preference(self):
        """
        Save the current theme preference to the database.
        """
        conn = sqlite3.connect(get_database_path())
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO settings (key, value) VALUES ('theme', ?)
        """, (self.current_theme,))
        conn.commit()
        conn.close()
        #print(f"Theme preference saved: {self.current_theme}")

    ###########################################################################
    # LOADING / SAVING
    ###########################################################################
    def load_shortcuts(self):
        conn = sqlite3.connect(get_database_path())
        cursor = conn.cursor()

        # Query shortcuts with categories and tags
        cursor.execute("""
            SELECT s.id, s.name, s.command, s.description,
                c.name AS category, GROUP_CONCAT(t.name) AS tags,
                s.updated_at, s.usage_count
            FROM shortcuts s
            LEFT JOIN categories c ON s.category_id = c.id
            LEFT JOIN shortcut_tags st ON s.id = st.shortcut_id
            LEFT JOIN tags t ON st.tag_id = t.id
            GROUP BY s.id
        """)
        self.shortcuts_data = [
            {
                "id": row[0],
                "name": row[1],
                "command": row[2],
                "description": row[3],
                "requires_input": bool(re.search(r"{(.*?)}", row[2])),  # Auto-detect placeholders
                "category": row[4] or "",
                "tags": row[5].split(",") if row[5] else [],
                "updated_at": row[6] or "",
                "usage_count": int(row[7]) if row[7] else 0
            }
            for row in cursor.fetchall()
        ]

        # Load settings
        cursor.execute("SELECT key, value FROM settings")
        self.settings_data = {row[0]: row[1] for row in cursor.fetchall()}
        self.current_theme = self.settings_data.get("theme", "light")
        self.current_sort_method = self.settings_data.get("sort_preference", "newest")
        conn.close()

        #print(f"Shortcuts loaded: {self.shortcuts_data}")
        #print(f"Settings loaded: {self.settings_data}")

    def save_shortcuts(self):
        """
        Save shortcuts to the SQLite database.
        """
        conn = sqlite3.connect(os.path.join(get_app_folder(), "commander.db"))
        cursor = conn.cursor()

        # Save shortcuts
        for shortcut in self.shortcuts_data:
            cursor.execute("""
                INSERT OR REPLACE INTO shortcuts (id, name, command, description, category_id)
                VALUES (?, ?, ?, ?, (SELECT id FROM categories WHERE name = ?))
            """, (shortcut.get("id"), shortcut["name"], shortcut["command"], shortcut["description"],
                shortcut["category"]))

            # Update tags for the shortcut
            cursor.execute("DELETE FROM shortcut_tags WHERE shortcut_id = ?", (shortcut.get("id"),))
            for tag in shortcut["tags"]:
                cursor.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (tag,))
                cursor.execute("""
                    INSERT INTO shortcut_tags (shortcut_id, tag_id)
                    SELECT ?, id FROM tags WHERE name = ?
                """, (shortcut.get("id"), tag))

        # Save settings
        for key, value in self.settings_data.items():
            cursor.execute("""
                INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)
            """, (key, value))

        conn.commit()
        conn.close()

    ###########################################################################
    # TABLE LOGIC
    ###########################################################################
    def populate_table(self, pairs):
        """
        Populates the table with the given pairs (sorted shortcuts).
        Each pair is a tuple of (shortcut, original_index).
        """
        self.displayed_pairs = pairs  # Store for later reference
        self.table.setRowCount(len(pairs))  # Adjust table row count

        for row_idx, (shortcut, _) in enumerate(pairs):
            # Extract shortcut attributes
            name = shortcut.get("name", "")
            command = shortcut.get("command", "")
            description = shortcut.get("description", "") or "No description available"  # Tooltip
            tags = ", ".join(shortcut.get("tags", []))
            category = shortcut.get("category", "")

            # Create table items
            item_name = QTableWidgetItem(name)
            item_command = QTableWidgetItem(command)
            item_tags = QTableWidgetItem(tags)
            item_category = QTableWidgetItem(category)

            # Add tooltips
            item_name.setToolTip(description)
            item_command.setToolTip(description)
            item_tags.setToolTip(description)
            item_category.setToolTip(description)

            # Populate the table row
            self.table.setItem(row_idx, 0, item_name)
            self.table.setItem(row_idx, 1, item_command)
            self.table.setItem(row_idx, 2, item_tags)
            self.table.setItem(row_idx, 3, item_category)

        # Adjust column widths for readability
        self.table.setColumnWidth(0, 150)  # Name
        self.table.setColumnWidth(1, 200)  # Command
        self.table.setColumnWidth(2, 150)  # Tags
        self.table.setColumnWidth(3, 150)  # Category

        # Ensure headers resize properly
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)  # Name
        header.setSectionResizeMode(1, QHeaderView.Stretch)  # Command
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Tags
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Category

        

    ###########################################################################
    # SEARCH LOGIC
    ###########################################################################
    def refresh_table(self):
        """
        Refreshes the table while keeping the current sorting and category filters.
        """
        print(f"Refreshing table with current sort method: {self.current_sort_method}")

        # Reload shortcuts and categories
        self.load_shortcuts()
        self.update_category_sidebar()

        # Apply the current sorting method
        if hasattr(self, 'current_sort_method') and self.current_sort_method:
            self.sort_table(self.current_sort_method)
        else:
            print("Invalid or missing sort method. Defaulting to 'newest'.")
            self.sort_table("newest")

        # Reapply the current filter (if any)
        print("Reapplying filters after sorting.")
        self.filter_table()

    def filter_table(self):
        """
        Filters the table based on search text or selected category.
        """
        filter_text = self.search_bar.text().lower().strip()
        pairs = []

        for shortcut, original_index in self.displayed_pairs:  # Use displayed_pairs for filtering
            # Filter by selected category
            if self.selected_category:
                if shortcut.get("category", "") != self.selected_category:
                    continue

            # Filter by search text
            if filter_text:
                combined_text = " ".join([
                    shortcut.get("name", ""),
                    shortcut.get("command", ""),
                    " ".join(shortcut.get("tags", [])),
                    shortcut.get("category", "")
                ]).lower()
                if filter_text not in combined_text:
                    continue

            pairs.append((shortcut, original_index))

        # Debug: Check filtered data
        print(f"Filtered {len(pairs)} items. First item: {pairs[0][0].get('name', '') if pairs else 'None'}")

        self.populate_table(pairs)

    ###########################################################################
    # TABLE SELECTION (Enabling Execute, Edit, Delete)
    ###########################################################################
    def on_table_select(self, row, column):
        self.execute_button.setEnabled(True)
        self.execute_button.setText("Execute")
        self.confirmation_pending = False

        # Make it red
        self.execute_button.setStyleSheet("background-color: red; color: white;")

        self.edit_button.setEnabled(True)
        self.delete_button.setEnabled(True)

        item_name = self.table.item(row, 0).text()
        item_command = self.table.item(row, 1).text()
        self.info_label.setText(f"Selected: {item_name} | Command: {item_command}")
    def copy_selected_command(self):
        """
        Copies the command of the selected row to the clipboard.
        """
        selected_items = self.table.selectedItems()
        if selected_items:
            command = selected_items[1].text()  # Assuming column 1 is the "Command" column
            clipboard = QApplication.clipboard()
            clipboard.setText(command)
            self.info_label.setText("Command copied to clipboard.")
        else:
            self.info_label.setText("No item selected to copy.")

    ###########################################################################
    # TWO-STEP EXECUTION
    ###########################################################################
    def on_execute_clicked(self):
        if not self.confirmation_pending:
            self.execute_button.setText("Confirm")
            self.confirmation_pending = True
            # Turn green
            self.execute_button.setStyleSheet("background-color: green; color: white;")
        else:
            self.run_selected_command()
            self.execute_button.setText("Execute")
            self.confirmation_pending = False
            self.execute_button.setStyleSheet("background-color: red; color: white;")

    def run_selected_command(self, row=None):
        """
        Executes the command of the selected row, either from a button or a right-click context menu.
        """
        if row is None:  # If no row is passed, use the currently selected item
            selected_items = self.table.selectedItems()
            if not selected_items:
                print("No item selected.")
                self.info_label.setText("No item selected.")
                return

            row = selected_items[0].row()

        # Safeguard: Verify row alignment with displayed_pairs
        if row >= len(self.displayed_pairs):
            print("Invalid row selection. Out of range.")
            self.info_label.setText("Invalid selection.")
            return

        shortcut, original_index = self.displayed_pairs[row]

        # Validate command
        command = shortcut.get("command", "").strip()
        if not command:
            self.info_label.setText("No command to execute.")
            print("No command provided.")
            return

        # Detect and handle placeholders
        placeholders = re.findall(r"{(.*?)}", command)
        if placeholders:
            print(f"Detected placeholders: {placeholders}")
            for ph in placeholders:
                val = self.prompt_for_variable(ph)
                if not val:  # Handle missing input
                    self.info_label.setText(f"Execution canceled. Missing value for {ph}.")
                    print(f"Command canceled due to missing value for placeholder: {ph}")
                    return
                # Replace the placeholder with the user-provided value
                command = command.replace(f"{{{ph}}}", val)

        # Re-validate command to check for unresolved placeholders
        if "{" in command or "}" in command:
            self.info_label.setText("Invalid command: Unresolved placeholders remain.")
            print("Invalid or unresolved placeholders remain in command:", command)
            return

        # Prepend the appropriate executor based on the file type
        if command.endswith(".bat"):
            command = f"cmd.exe /c \"{command}\""
        elif command.endswith(".ps1"):
            command = f"powershell -ExecutionPolicy Bypass -File \"{command}\""
        elif command.endswith(".exe"):
            command = f"\"{command}\""  # Enclose in quotes for safety

        # Execute the command interactively
        interactive_command = f"start cmd /k {command}"  # Use /k to keep the window open
        print(f"Final interactive command: {interactive_command}")

        try:
            subprocess.Popen(interactive_command, shell=True)
            print(f"Executing: {interactive_command}")
        except Exception as e:
            print(f"Error executing command: {e}")
            self.info_label.setText(f"Error executing: {e}")
            return

        # Update usage count and timestamp in the database
        conn = sqlite3.connect(get_database_path())
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE shortcuts
            SET usage_count = usage_count + 1,
                updated_at = ?
            WHERE id = ?
        """, (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), shortcut["id"]))
        conn.commit()
        conn.close()

        # Update the in-memory shortcut data
        shortcut["usage_count"] += 1
        shortcut["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.update_table_row(row, shortcut)

        # Automatically sort the table after updates
        self.sort_table(self.current_sort_method)

    def update_shortcut_usage(self, shortcut, row):
        # Update database
        conn = sqlite3.connect(get_database_path())
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE shortcuts
            SET usage_count = usage_count + 1,
                updated_at = ?
            WHERE id = ?
        """, (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), shortcut["id"]))
        conn.commit()
        conn.close()

        # Update shortcut in memory
        shortcut["usage_count"] += 1
        shortcut["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.update_table_row(row, shortcut)
        self.sort_table(self.current_sort_method)
        
    def update_table_row(self, row, shortcut):
        """
        Update a single table row with the latest shortcut data.
        """
        self.table.item(row, 0).setText(shortcut.get("name", ""))
        self.table.item(row, 1).setText(shortcut.get("command", ""))
        self.table.item(row, 2).setText(", ".join(shortcut.get("tags", [])))
        self.table.item(row, 3).setText(shortcut.get("category", ""))
        self.table.resizeColumnsToContents()

    def prompt_for_variable(self, placeholder_label: str = "value"):
        """
        Prompts the user for input to replace a placeholder.
        """
        text, ok = QInputDialog.getText(
            self,
            "Input Required",
            f"Enter {placeholder_label}:",
            QLineEdit.Normal
        )
        if ok and text.strip():
            # Validate numeric input for specific placeholders
            if placeholder_label == "time":
                if not text.strip().isdigit():
                    QMessageBox.warning(
                        self,
                        "Invalid Input",
                        "Please enter a valid numeric value for time.",
                        QMessageBox.Ok
                    )
                    return None
            return text.strip()
        return None

    ###########################################################################
    # ADD / EDIT / DELETE SHORTCUTS
    ###########################################################################
    
    def on_add_shortcut(self):
        dialog = ShortcutDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            new_data = dialog.get_data()

            conn = sqlite3.connect(get_database_path())
            cursor = conn.cursor()

            # Ensure the category exists or create it
            cursor.execute("""
                INSERT OR IGNORE INTO categories (name) VALUES (?)
            """, (new_data["category"],))
            cursor.execute("""
                SELECT id FROM categories WHERE name = ?
            """, (new_data["category"],))
            category_id = cursor.fetchone()[0]

            # Insert the new shortcut, auto-detect if placeholders exist
            requires_input = bool(re.search(r"{(.*?)}", new_data["command"]))  # Detect placeholders dynamically
            cursor.execute("""
                INSERT INTO shortcuts (name, command, description, category_id)
                VALUES (?, ?, ?, ?)
            """, (new_data["name"], new_data["command"], new_data["description"], category_id))

            # Insert tags and link them to the shortcut
            shortcut_id = cursor.lastrowid
            for tag in new_data["tags"]:
                cursor.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (tag,))
                cursor.execute("""
                    INSERT INTO shortcut_tags (shortcut_id, tag_id)
                    SELECT ?, id FROM tags WHERE name = ?
                """, (shortcut_id, tag))

            conn.commit()
            conn.close()

            # Refresh the UI
            self.load_shortcuts()
            self.update_category_sidebar()
            self.refresh_table()

    def on_edit_shortcut(self):
        selected_items = self.table.selectedItems()
        if not selected_items:
            return

        table_row = selected_items[0].row()
        shortcut, original_index = self.displayed_pairs[table_row]
        dialog = ShortcutDialog(self, shortcut_data=shortcut)

        if dialog.exec_() == QDialog.Accepted:
            updated_data = dialog.get_data()

            conn = sqlite3.connect(get_database_path())
            cursor = conn.cursor()

            # Ensure the category exists or create it
            cursor.execute("""
                INSERT OR IGNORE INTO categories (name) VALUES (?)
            """, (updated_data["category"],))
            cursor.execute("""
                SELECT id FROM categories WHERE name = ?
            """, (updated_data["category"],))
            category_id = cursor.fetchone()[0]

            # Update the shortcut, auto-detect if placeholders exist
            requires_input = bool(re.search(r"{(.*?)}", updated_data["command"]))  # Detect placeholders dynamically
            cursor.execute("""
                UPDATE shortcuts
                SET name = ?, command = ?, description = ?, category_id = ?
                WHERE id = ?
            """, (updated_data["name"], updated_data["command"], updated_data["description"], category_id, shortcut["id"]))

            # Update tags for the shortcut
            cursor.execute("DELETE FROM shortcut_tags WHERE shortcut_id = ?", (shortcut["id"],))
            for tag in updated_data["tags"]:
                cursor.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (tag,))
                cursor.execute("""
                    INSERT INTO shortcut_tags (shortcut_id, tag_id)
                    SELECT ?, id FROM tags WHERE name = ?
                """, (shortcut["id"], tag))

            conn.commit()
            conn.close()

            # Refresh the UI
            self.remove_unused_categories()  # Remove unused categories
            self.load_shortcuts()
            self.update_category_sidebar()
            self.filter_table()

    def on_delete_shortcut(self):
        selected_items = self.table.selectedItems()
        if not selected_items:
            return

        table_row = selected_items[0].row()
        shortcut, original_index = self.displayed_pairs[table_row]
        shortcut_name = shortcut["name"]

        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete '{shortcut_name}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            conn = sqlite3.connect(get_database_path())
            cursor = conn.cursor()

            # Delete the shortcut and its relationships
            cursor.execute("DELETE FROM shortcut_tags WHERE shortcut_id = ?", (shortcut["id"],))
            cursor.execute("DELETE FROM shortcuts WHERE id = ?", (shortcut["id"],))

            conn.commit()
            conn.close()

            # Remove unused categories and refresh the GUI
            self.remove_unused_categories()  # Call the method here
            self.load_shortcuts()
            self.update_category_sidebar()
            self.filter_table()

    def remove_unused_tags(self):
        """
        Remove tags that are not associated with any shortcuts.
        """
        conn = sqlite3.connect(get_database_path())
        cursor = conn.cursor()

        # Delete unused tags
        cursor.execute("""
            DELETE FROM tags
            WHERE id NOT IN (SELECT DISTINCT tag_id FROM shortcut_tags)
        """)

        conn.commit()
        conn.close()

###############################################################################
# Shortcut editing
###############################################################################

class ShortcutDialog(QDialog):
    def __init__(self, parent=None, shortcut_data=None):
        super().__init__(parent)
        self.setWindowTitle("Shortcut")

        self.result_data = {}
        self.edit_mode = (shortcut_data is not None)

        layout = QFormLayout()
        self.setLayout(layout)

        # Name
        self.name_edit = QLineEdit()
        layout.addRow(QLabel("Name:"), self.name_edit)

        # Command
        self.command_edit = QLineEdit()
        layout.addRow(QLabel("Command (use {placeholder} if needed):"), self.command_edit)

        # Description
        self.description_edit = QLineEdit()
        layout.addRow(QLabel("Description:"), self.description_edit)

        # Tags
        self.tags_edit = QLineEdit()
        layout.addRow(QLabel("Tags (comma-separated):"), self.tags_edit)

        # Category
        self.category_edit = QLineEdit()
        layout.addRow(QLabel("Category:"), self.category_edit)

        # Link script button if desired
        self.link_file_button = QPushButton("Link .exe, .bat, or .ps1")
        self.link_file_button.clicked.connect(self.on_link_file)
        layout.addRow(QLabel("(Optional) Link Script:"), self.link_file_button)

        # If editing, populate fields
        if self.edit_mode and shortcut_data is not None:
            self.name_edit.setText(shortcut_data.get("name", ""))
            self.command_edit.setText(shortcut_data.get("command", ""))
            self.description_edit.setText(shortcut_data.get("description", ""))
            tag_list = shortcut_data.get("tags", [])
            self.tags_edit.setText(", ".join(tag_list))
            self.category_edit.setText(shortcut_data.get("category", ""))

        # OK / Cancel
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.on_ok_clicked)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        layout.addRow(self.ok_button, self.cancel_button)

    def on_link_file(self):
        file_filter = "Executables / Scripts (*.exe *.bat *.ps1);;All Files (*)"
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Executable or Script", "", file_filter)
        if file_path:
            self.command_edit.setText(file_path)

    def on_ok_clicked(self):
        name = self.name_edit.text().strip()
        command = self.command_edit.text().strip()
        description = self.description_edit.text().strip()
        tags_str = self.tags_edit.text().strip()
        category = self.category_edit.text().strip()

        # Convert comma-separated tags to a list
        tags_list = [tag.strip() for tag in tags_str.split(",")] if tags_str else []

        # No need for requires_input; it will be determined dynamically later
        self.result_data = {
            "name": name,
            "command": command,
            "description": description,
            "tags": tags_list,
            "category": category
        }
        self.accept()

    def get_data(self):
        """
        Returns the final data from the dialog as a dict.
        """
        name = self.name_edit.text().strip()
        command = self.command_edit.text().strip()
        description = self.description_edit.text().strip()
        tags_str = self.tags_edit.text().strip()
        category = self.category_edit.text().strip()

        # Convert comma-separated tags to a list
        tags_list = [tag.strip() for tag in tags_str.split(",")] if tags_str else []

        return {
            "name": name,
            "command": command,
            "description": description,
            "tags": tags_list,
            "category": category,
        }

def main():
    try:
        app = QApplication(sys.argv)
        app.setStyle(QStyleFactory.create("Fusion"))
        app.setStyleSheet("""
            QMainWindow {
                background-color: #f0f0f0;
            }
            QLabel {
                font-size: 14px;
            }
            QLineEdit {
                font-size: 14px;
                padding: 4px;
            }
            QTableWidget {
                background-color: #ffffff;
                gridline-color: #cccccc;
                font-size: 14px;
            }
            QTableWidget::item:selected {
                background-color: #0078d7;
                color: #ffffff;
            }
            QPushButton {
                font-size: 14px;
                padding: 6px 12px;
            }
            QToolTip {
                background-color: #222222;
                color: #ffffff;
                border: 1px solid #aaaaaa;
                padding: 5px;
                font-size: 12px;
            }
        """)

        window = Commander()
        window.show()
        sys.exit(app.exec_())
    except Exception as e:
        traceback.print_exc()  # Log full traceback
       #print(f"Unhandled exception: {e}")
if __name__ == "__main__":
    main()