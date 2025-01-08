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
from PyQt5.QtCore import Qt, QUrl, QAbstractTableModel
from PyQt5.QtWidgets import (
    QApplication,
    QMenuBar,
    QAbstractItemView,
    QMainWindow,
    QTableView,
    QWidget,
    QAction,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QInputDialog,
    QLabel,
    QStyleFactory,
    QPushButton, 
    QDialog,
    QMessageBox,
    QHeaderView,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QCheckBox,
    QListWidget,
    QSplitter,
    QMenu,
    QDialogButtonBox,  # Add this import
    QTextEdit  # Add this import
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
    color: #000000;
    gridline-color: #cccccc;
    font-size: 14px;
}
QTableWidget::item {
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
    font-size: 14px;
}
QListWidget {
    background-color: #ffffff;
    color: #000000;
}
QListWidget::item:selected {
    background-color: #0078d7;
    color: #ffffff;
}
QCheckBox {
    color: #000000;
    font-size: 14px;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 1px solid #cccccc;
    border-radius: 3px;
    background: #ffffff;
}
QCheckBox::indicator:checked {
    background: #0078d7;
    border-color: #0078d7;
}
"""

# Define the QSS for the toggle switch
TOGGLE_SWITCH_QSS = """
QCheckBox::indicator {
    width: 40px;
    height: 20px;
}
QCheckBox::indicator:unchecked {
    image: url(:/images/toggle_off.png);
}
QCheckBox::indicator:checked {
    image: url(:/images/toggle_on.png);
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
QTableWidget, QTableView {
    background-color: #2b2b2b;
    color: #ffffff;
    gridline-color: #374151;
    font-size: 14px;
}
QTableWidget::item, QTableView::item {
    color: #ffffff;
}
QTableWidget::item:selected, QTableView::item:selected {
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
    font-size: 14px;
}
QListWidget {
    background-color: #2b2b2b;
    color: #ffffff;
}
QListWidget::item:selected {
    background-color: #555555;
    color: #ffffff;
}
QHeaderView::section {
    background-color: #374151;
    color: #ffffff;
    font-weight: bold;
    border: 1px solid #444444;
}
QCheckBox {
    color: #dddddd;
    font-size: 14px;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 1px solid #666666;
    border-radius: 3px;
    background: #3b3b3b;
}
QCheckBox::indicator:checked {
    background: #0078d7;
    border-color: #0078d7;
}
"""

###############################################################################
###############################################################################

def get_app_folder():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))

def get_database_path():
    return os.path.join(get_app_folder(), "commander.db")

def init_database():
    """
    Initialize the in-memory database by copying schema and data from the persistent database.
    """
    global conn_disk, conn_memory
    conn_disk = sqlite3.connect(get_database_path())  # Persistent database on disk
    conn_memory = sqlite3.connect(":memory:")         # In-memory database

    cursor_disk = conn_disk.cursor()
    cursor_memory = conn_memory.cursor()

    # Copy schema and data
    for line in conn_disk.iterdump():
        try:
            cursor_memory.execute(line)
        except sqlite3.Error as e:
            print(f"Error executing line: {line}")
            print(f"SQLite error: {e}")

    conn_memory.commit()

def flush_memory_to_disk():
    """
    Flush changes from the in-memory database back to the persistent disk database.
    """
    global conn_disk, conn_memory
    cursor_disk = conn_disk.cursor()

    # Clear existing data from disk tables
    tables_to_clear = ["settings", "shortcuts", "categories", "tags", "shortcut_tags", "preferences"]
    for table in tables_to_clear:
        cursor_disk.execute(f"DELETE FROM {table};")

    # Dump in-memory data back to disk
    for line in conn_memory.iterdump():
        # Skip problematic statements
        if any(
            line.startswith(keyword)
            for keyword in ("CREATE TABLE", "CREATE INDEX", "CREATE UNIQUE INDEX", "BEGIN TRANSACTION", "COMMIT")
        ):
            continue
        try:
            cursor_disk.execute(line)
        except sqlite3.IntegrityError as e:
            print(f"Integrity error executing line: {line}")
            print(f"SQLite error: {e}")
        except sqlite3.Error as e:
            print(f"Error executing line: {line}")
            print(f"SQLite error: {e}")

    # Commit changes to the disk database
    conn_disk.commit()
    print("Flushed in-memory changes to disk.")

###############################################################################
# Theme toggle switch
###############################################################################
class ShortcutTableModel(QAbstractTableModel):
    def __init__(self, shortcuts, parent=None):
        super().__init__(parent)
        self.shortcuts = shortcuts  # List of shortcut dictionaries

    def rowCount(self, parent=None):
        return len(self.shortcuts)

    def columnCount(self, parent=None):
        return 4  # Name, Command, Tags, Category

    def data(self, index, role):
        if not index.isValid():
            return None

        shortcut = self.shortcuts[index.row()]
        if role == Qt.DisplayRole:
            if index.column() == 0:  # Name
                return shortcut.get("name", "")
            elif index.column() == 1:  # Command
                return shortcut.get("command", "")
            elif index.column() == 2:  # Tags
                return ", ".join(shortcut.get("tags", []))
            elif index.column() == 3:  # Category
                return shortcut.get("category", "")

        return None

    def headerData(self, section, orientation, role):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            headers = ["Name", "Command", "Tags", "Category"]
            return headers[section]
        return None

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
        self.setFixedSize(40, 20)  # Ensure the toggle switch has a fixed size

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
        
        # Initialize database first
        init_database()
        
        # Basic setup
        self.shortcuts_data = []
        self.displayed_pairs = []
        self.current_theme = "light"
        self.selected_category = None
        self.current_sort_method = "newest"
        self.confirmation_pending = False
        self.log_text = ""

        # Window setup with dynamic sizing
        self.setWindowTitle("Commander")
        screen = QApplication.primaryScreen().availableGeometry()
        
        # Store screen dimensions for later use
        self.screen_width = screen.width()
        self.screen_height = screen.height()
        
        # Set minimum size to 40% of screen
        self.setMinimumSize(
            int(self.screen_width * 0.4),
            int(self.screen_height * 0.4)
        )
        
        # Set default size to 80% (used when window is restored)
        self.default_width = int(self.screen_width * 0.8)
        self.default_height = int(self.screen_height * 0.8)
        
        # Start maximized
        self.setWindowState(Qt.WindowMaximized)

        # Load data and preferences
        self.load_shortcuts()
        self.load_theme_preference()
        self.load_sorting_preference()

        # Initialize UI
        self.initUI()
        self.apply_theme(self.current_theme)

        # Set initial data
        self.displayed_pairs = [(s, i) for i, s in enumerate(self.shortcuts_data)]
        
        # Apply saved sort method
        print(f"Initializing with sort method: {self.current_sort_method}")
        self.sort_table(self.current_sort_method)

        # Set default column widths
        self.set_default_column_widths()

        # Initialize execute button
        self.execute_button.setStyleSheet("background-color: red; color: white;")

        # Add minimum column widths
        self.min_column_widths = {
            0: 100,  # Name minimum width
            1: 150,  # Command minimum width
            2: 80,   # Tags minimum width
            3: 80    # Category minimum width
        }
        
        # Set smaller minimum window width
        self.setMinimumWidth(500)  # Allow window to be shrunk more

    def set_default_column_widths(self):
        """
        Set default column widths for the table.
        """
        total_width = self.table.viewport().width()
        self.table.setColumnWidth(0, int(total_width * 0.2))  # Name
        self.table.setColumnWidth(1, int(total_width * 0.4))  # Command
        self.table.setColumnWidth(2, int(total_width * 0.2))  # Tags
        self.table.setColumnWidth(3, int(total_width * 0.2))  # Category

    def resizeEvent(self, event):
        """
        Enhanced resize event handler with better font scaling
        """
        # Calculate base font size based on window width
        base_width = 1000  # Reference width
        current_width = self.width()
        base_font_size = 12
        
        # Scale font size between 8 and 14 based on window width
        scaled_font_size = max(8, min(14, int(base_font_size * (current_width / base_width))))
        
        # Apply scaled styling with adjusted padding
        self.setStyleSheet(f"""
            QTableView {{
                font-size: {scaled_font_size}px;
            }}
            QPushButton {{
                font-size: {scaled_font_size}px;
                padding: {max(2, scaled_font_size//3)}px {max(4, scaled_font_size//2)}px;
            }}
            QLabel {{
                font-size: {scaled_font_size}px;
            }}
            QLineEdit {{
                font-size: {scaled_font_size}px;
                padding: {max(2, scaled_font_size//4)}px;
            }}
            QListWidget {{
                font-size: {scaled_font_size}px;
            }}
            QHeaderView::section {{
                font-size: {scaled_font_size}px;
                padding: {max(2, scaled_font_size//4)}px;
            }}
        """)
        
        # Adjust layout proportions
        self.adjust_column_widths()
        super().resizeEvent(event)

    def adjust_column_widths(self):
        """
        Enhanced column width adjustment with better responsive behavior
        """
        if not hasattr(self, 'table'):
            return
            
        total_width = self.table.viewport().width()
        
        # Base proportions for when we have enough space
        base_proportions = {
            0: 0.25,  # Name column - 25%
            1: 0.35,  # Command column - 35%
            2: 0.20,  # Tags column - 20%
            3: 0.20   # Category column - 20%
        }

        # Calculate minimum total width needed
        min_total = sum(self.min_column_widths.values())
        
        if total_width <= min_total:
            # When space is too tight, use minimum widths
            for col, min_width in self.min_column_widths.items():
                self.table.setColumnWidth(col, min_width)
        else:
            # Distribute extra space proportionally
            extra_space = total_width - min_total
            for col, proportion in base_proportions.items():
                min_width = self.min_column_widths[col]
                extra = int(extra_space * proportion)
                self.table.setColumnWidth(col, min_width + extra)

        # Configure header behavior
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setStretchLastSection(False)
        
        # Enable horizontal scrolling if needed
        self.table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

    def changeEvent(self, event):
        """
        Handle window state changes (maximize/restore)
        """
        if event.type() == event.WindowStateChange:
            if self.windowState() & Qt.WindowMaximized:
                # Window was maximized
                self.adjust_column_widths()
            elif event.oldState() & Qt.WindowMaximized:
                # Window was restored
                self.adjust_column_widths()
        super().changeEvent(event)

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

        theme_menu = view_menu.addMenu("Theme")
        light_theme_action = QAction("Light Mode", self)
        light_theme_action.triggered.connect(lambda: self.apply_theme("light"))
        theme_menu.addAction(light_theme_action)

        dark_theme_action = QAction("Dark Mode", self)
        dark_theme_action.triggered.connect(lambda: self.apply_theme("dark"))
        theme_menu.addAction(dark_theme_action)

        # Help menu
        help_menu = menubar.addMenu("Help")

        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about_dialog)

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
        
        if not method:
            method = "newest"
            
        self.current_sort_method = method
        self.save_sorting_preference(method)

        # Ensure we have pairs to sort
        if not self.displayed_pairs:
            self.displayed_pairs = [(s, i) for i, s in enumerate(self.shortcuts_data)]

        def safe_get(data, key, default):
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

        # Store the sorted pairs and update the table
        self.displayed_pairs = sorted_pairs
        self.populate_table(sorted_pairs)
        print(f"Table sorted by {method}")

    def save_sorting_preference(self, method):
        """
        Save the current sorting preference to the in-memory database.
        """
        self.current_sort_method = method  # Update the tracking variable
        cursor = conn_memory.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO settings (key, value) VALUES ('sort_preference', ?)
        """, (method,))
        conn_memory.commit()

    def load_sorting_preference(self):
        """
        Load the saved sorting preference from the in-memory database.
        """
        cursor = conn_memory.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = 'sort_preference'")
        result = cursor.fetchone()
        self.current_sort_method = result[0] if result else "newest"  # Default to "newest"

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
        selected_indexes = self.table.selectionModel().selectedRows()
        if not selected_indexes:
            QMessageBox.warning(self, "No Selection", "Please select a shortcut to execute.")
            return

        # Get the selected row and its command
        row = selected_indexes[0].row()
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
            self.run_selected_command()

    def copy_selected_command(self):
        """
        Copies the command of the selected row to the clipboard.
        """
        selected_indexes = self.table.selectionModel().selectedRows()
        if not selected_indexes:
            QMessageBox.warning(self, "No Selection", "Please select a shortcut to copy.")
            return

        # Get the selected row and its command
        row = selected_indexes[0].row()
        command = self.model.data(self.model.index(row, 1), Qt.DisplayRole)

        if not command:
            QMessageBox.warning(self, "No Command", "The selected shortcut has no command to copy.")
            return

        clipboard = QApplication.clipboard()
        clipboard.setText(command)
        self.info_label.setText("Command copied to clipboard.")

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
        if (cat_text == "(All Categories)"):
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

        right_panel.addLayout(search_layout)

        # ========== Table ==========
        self.table = QTableView(self)
        self.model = ShortcutTableModel(self.shortcuts_data, self)
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.resizeColumnsToContents()
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setStretchLastSection(True)

        # Connect selection changes
        self.table.selectionModel().selectionChanged.connect(self.on_table_select)
        self.init_table_context_menu()

        right_panel.addWidget(self.table)

        # ========== CRUD + Bottom Layout ==========
        crud_layout = QHBoxLayout()

        # Add Shortcut Button
        self.add_button = QPushButton("Add Shortcut")
        self.add_button.clicked.connect(self.on_add_shortcut)
        self.add_button.setMaximumWidth(150)
        crud_layout.addWidget(self.add_button)

        # Edit Shortcut Button
        self.edit_button = QPushButton("Edit Shortcut")
        self.edit_button.clicked.connect(self.on_edit_shortcut)
        self.edit_button.setEnabled(False)
        self.edit_button.setMaximumWidth(150)
        crud_layout.addWidget(self.edit_button)

        # Delete Shortcut Button
        self.delete_button = QPushButton("Delete Shortcut")
        self.delete_button.clicked.connect(self.on_delete_shortcut)
        self.delete_button.setEnabled(False)
        self.delete_button.setMaximumWidth(150)
        crud_layout.addWidget(self.delete_button)

        right_panel.addLayout(crud_layout)

        # Info Label and Execute Button
        bottom_layout = QHBoxLayout()
        self.execute_button = QPushButton("Execute")
        self.execute_button.setEnabled(False)
        self.execute_button.setMaximumWidth(200)
        self.execute_button.clicked.connect(self.on_execute_clicked)

        self.log_button = QPushButton("Execution Log")  # Add log button
        self.log_button.setMaximumWidth(200)
        self.log_button.clicked.connect(self.show_log_dialog)

        bottom_layout.addWidget(self.execute_button)
        bottom_layout.addWidget(self.log_button)  # Add log button to layout

        right_panel.addLayout(bottom_layout)

        # New Info Label below all buttons
        self.info_label = QLabel("")
        self.info_label.setAlignment(Qt.AlignCenter)
        self.info_label.setStyleSheet(
            "color: #333333;" if self.current_theme == "light" else "color: #dddddd;"
        )
        right_panel.addWidget(self.info_label)

        # Wrap the right panel in a widget
        right_panel_widget = QWidget()
        right_panel_widget.setLayout(right_panel)

        # Add the right panel widget to the splitter
        splitter.addWidget(right_panel_widget)

        splitter.setStretchFactor(0, 1)  # Sidebar expands less
        splitter.setStretchFactor(1, 4)  # Table expands more
        splitter.setSizes([50, 800])  # Initial sizes (sidebar, table)

        # Add the splitter to the main layout
        main_layout.addWidget(splitter)

        # Update categories and table
        self.update_category_sidebar()
        self.refresh_table()

    def show_log_dialog(self):
        """
        Show a dialog with the log text.
        """
        dialog = QDialog(self)
        dialog.setWindowTitle("Log")
        layout = QVBoxLayout(dialog)

        log_text_edit = QTextEdit(dialog)
        log_text_edit.setReadOnly(True)
        log_text_edit.setPlainText(self.log_text)
        layout.addWidget(log_text_edit)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok, dialog)
        button_box.accepted.connect(dialog.accept)
        layout.addWidget(button_box)

        dialog.exec_()

    def update_log(self, message):
        """
        Update the log text with a new message.
        """
        self.log_text += message + "\n"

    def update_info_label(self, message):
        """
        Updates the info label with the given message and logs it.
        """
        self.info_label.setText(message)
        self.update_log(message)

    ###########################################################################
    # THEME LOGIC
    ###########################################################################
    def apply_theme(self, theme_name):
        """
        Applies the specified theme stylesheet to the QApplication.
        """
        self.current_theme = theme_name
        if theme_name == "dark":
            QApplication.instance().setStyleSheet(DARK_STYLESHEET)
            if hasattr(self, 'info_label'):
                self.info_label.setStyleSheet("color: #dddddd;")
        else:
            QApplication.instance().setStyleSheet(LIGHT_STYLESHEET)
            if hasattr(self, 'info_label'):
                self.info_label.setStyleSheet("color: #333333;")

        self.save_theme_preference()  # Save the updated theme preference
        print(f"Applied theme: {theme_name}")  # Debug output

    def save_theme_preference(self):
        """
        Save the current theme preference to the in-memory database.
        """
        cursor = conn_memory.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO settings (key, value) VALUES ('theme', ?)
        """, (self.current_theme,))
        conn_memory.commit()
        print(f"Theme '{self.current_theme}' saved to database.")  # Debug output


    def load_theme_preference(self):
        """
        Load the saved theme preference from the in-memory database.
        """
        cursor = conn_memory.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = 'theme'")
        result = cursor.fetchone()

        if result:
            self.current_theme = result[0]
            print(f"Loaded theme: {self.current_theme}")  # Debug output
        else:
            self.current_theme = "light"  # Default to light theme
            print("No theme found in database; defaulting to 'light'.")

        self.apply_theme(self.current_theme)

    ###########################################################################
    # LOADING / SAVING
    ###########################################################################
    def load_shortcuts(self):
        """
        Load shortcuts from the in-memory SQLite database.
        """
        cursor = conn_memory.cursor()

        # Clear existing shortcuts data
        self.shortcuts_data = []

        cursor.execute("""
            SELECT s.id, s.name, s.command, s.description, c.name AS category,
                s.updated_at, s.usage_count, s.use_powershell
            FROM shortcuts s
            LEFT JOIN categories c ON s.category_id = c.id
            ORDER BY s.updated_at DESC
        """)

        self.shortcuts_data = [
            {
                "id": row[0],
                "name": row[1],
                "command": row[2],
                "description": row[3] or "No description available",
                "category": row[4] or "",
                "updated_at": row[5] or "",
                "usage_count": int(row[6]) if row[6] else 0,
                "use_powershell": bool(row[7]) if row[7] is not None else False,
            }
            for row in cursor.fetchall()
        ]

        print(f"Loaded shortcuts: {self.shortcuts_data}")  # Debug output

    def save_shortcuts(self):
        """
        Save all shortcuts to the in-memory SQLite database.
        """
        cursor = conn_memory.cursor()

        # Save shortcuts in a batch transaction
        with conn_memory:
            for shortcut in self.shortcuts_data:
                cursor.execute("""
                    INSERT OR REPLACE INTO shortcuts (id, name, command, description, category_id, usage_count, use_powershell, updated_at)
                    VALUES (?, ?, ?, ?, (SELECT id FROM categories WHERE name = ?), ?, ?, ?)
                """, (
                    shortcut.get("id"),
                    shortcut["name"],
                    shortcut["command"],
                    shortcut["description"],
                    shortcut["category"],
                    shortcut["usage_count"],
                    shortcut["use_powershell"],
                    shortcut["updated_at"],
                ))
                print(f"Shortcut saved: {shortcut['name']}")  # Debug output

    ###########################################################################
    # TABLE LOGIC
    ###########################################################################
    def populate_table(self, pairs, page=1, page_size=100):
        """
        Updates the model with a subset of the given pairs for lazy loading.
        Implements pagination.
        """
        self.current_page = page  # Track the current page
        self.page_size = page_size  # Items per page
        self.total_items = len(pairs)  # Total number of pairs
        self.total_pages = (self.total_items + page_size - 1) // page_size  # Calculate total pages

        # Determine the range of items to display
        start_index = (page - 1) * page_size
        end_index = min(start_index + page_size, self.total_items)
        displayed_pairs = pairs[start_index:end_index]

        # Update the model with the displayed data
        self.model.shortcuts = [pair[0] for pair in displayed_pairs]
        self.model.layoutChanged.emit()  # Notify the view that the data has changed

        # Update navigation info
        self.info_label.setText(
            f"Showing {start_index + 1}-{end_index} of {self.total_items} items (Page {page}/{self.total_pages})"
        )

    ###########################################################################
    # SEARCH LOGIC
    ###########################################################################
    def refresh_table(self):
        """
        Refresh the table while keeping the current sorting and category filters.
        """
        self.load_shortcuts()  # Reload data from the database
        self.sort_table(self.current_sort_method)  # Reapply sorting
        self.filter_table()  # Reapply filters if any
        print(f"Refreshed table with {len(self.shortcuts_data)} shortcuts.")  # Debug output

    def filter_table(self):
        """
        Filters the table based on search text or selected category.
        Ensures the search resets and reevaluates with each text update.
        """
        # Retrieve the filter text
        filter_text = self.search_bar.text().lower().strip()
        pairs = []

        # Reset to all items in the current category (or all if none selected)
        for i, shortcut in enumerate(self.shortcuts_data):
            # Filter by selected category first
            if self.selected_category:
                if shortcut.get("category", "") != self.selected_category:
                    continue

            # Apply search filter if there's text
            if filter_text:
                combined_text = " ".join([
                    shortcut.get("name", ""),
                    shortcut.get("command", ""),
                    " ".join(shortcut.get("tags", [])),
                    shortcut.get("category", "")
                ]).lower()
                if filter_text not in combined_text:
                    continue

            pairs.append((shortcut, i))

        # Store the filtered pairs
        self.displayed_pairs = pairs

        # Populate the table with the filtered results
        self.populate_table(pairs)

        # Update the info label with filter context
        filter_info = []
        if self.selected_category:
            filter_info.append(f"Category: {self.selected_category}")
        if filter_text:
            filter_info.append(f"Search: '{filter_text}'")
        
        status = f"Showing {len(pairs)} items"
        if filter_info:
            status += f" ({' | '.join(filter_info)})"
        self.info_label.setText(status)

    def update_info_label(self):
        """
        Updates the info label with the current table status.
        """
        total_items = len(self.displayed_pairs)
        self.info_label.setText(f"Showing {total_items} items")

    ###########################################################################
    # TABLE SELECTION (Enabling Execute, Edit, Delete)
    ###########################################################################
    def on_table_select(self, selected, deselected):
        """
        Handles table row selection.
        Updates the info_label with the selected shortcut details.
        """
        indexes = self.table.selectionModel().selectedRows()
        if indexes:
            row = indexes[0].row()
            if row < len(self.displayed_pairs):
                shortcut = self.displayed_pairs[row][0]
                name = shortcut.get("name", "")
                command = shortcut.get("command", "")
                
                # Build status message with context
                status = f"Selected: {name} | Command: {command}"
                
                # Add category/search context if filtered
                filter_info = []
                if self.selected_category:
                    filter_info.append(f"Category: {self.selected_category}")
                if self.search_bar.text().strip():
                    filter_info.append(f"Search: '{self.search_bar.text().strip()}'")
                
                if filter_info:
                    status += f" ({' | '.join(filter_info)})"
                
                self.info_label.setText(status)
                
                # Enable buttons for selected rows
                self.execute_button.setEnabled(True)
                self.edit_button.setEnabled(True)
                self.delete_button.setEnabled(True)
        else:
            # If no selection, show only filter context
            filter_info = []
            if self.selected_category:
                filter_info.append(f"Category: {self.selected_category}")
            if self.search_bar.text().strip():
                filter_info.append(f"Search: '{self.search_bar.text().strip()}'")
            
            status = f"Showing {len(self.displayed_pairs)} items"
            if filter_info:
                status += f" ({' | '.join(filter_info)})"
            
            self.info_label.setText(status)
            self.execute_button.setEnabled(False)
            self.edit_button.setEnabled(False)
            self.delete_button.setEnabled(False)

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

    def run_selected_command(self):
        """
        Executes the command of the selected row in the table.
        """
        # Get selected rows from the selection model
        selected_indexes = self.table.selectionModel().selectedRows()
        if not selected_indexes:
            print("No item selected.")
            self.info_label.setText("No item selected.")
            return

        # Get the first selected row
        row = selected_indexes[0].row()
        shortcut = self.model.shortcuts[row]  # Retrieve the shortcut from the model

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
            placeholder_values = self.prompt_for_variables(placeholders, command)
            if not placeholder_values:  # Handle missing input
                self.info_label.setText("Execution canceled. Missing values for placeholders.")
                print("Command canceled due to missing values for placeholders.")
                return
            # Replace the placeholders with the user-provided values
            for ph, val in placeholder_values.items():
                command = command.replace(f"{{{ph}}}", val)

        # Re-validate command to check for unresolved placeholders
        if "{" in command or "}" in command:
            self.info_label.setText("Invalid command: Unresolved placeholders remain.")
            print("Invalid or unresolved placeholders remain in command:", command)
            return

        # Prepend the appropriate executor based on the file type
        if command.endswith(".bat"):
            if shortcut.get("use_powershell", False):
                command = f"powershell -NoExit -Command \"& '{command}'\""
            else:
                command = f"cmd.exe /c \"{command}\""
        elif command.endswith(".ps1"):
            command = f"powershell -ExecutionPolicy Bypass -NoExit -File \"{command}\""
        elif command.endswith(".exe"):
            command = f"\"{command}\""  # Enclose in quotes for safety

        # Execute based on terminal preference
        if shortcut.get("use_powershell", False):
            interactive_command = f"start powershell -NoExit -Command \"{command}\""
        else:
            interactive_command = f"start cmd /k {command}"  # Use /k to keep the window open
        print(f"Final interactive command: {interactive_command}")

        # Run the command as a detached subprocess
        try:
            subprocess.Popen(
                interactive_command,
                shell=True,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                close_fds=True,
                creationflags=subprocess.DETACHED_PROCESS if os.name == 'nt' else 0  # Windows-specific detachment
            )
            print(f"Executing: {interactive_command}")
            self.update_log(f"Executed: {command}")  # Log the execution
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

        # Update the model data for the specific row
        shortcut["usage_count"] += 1
        shortcut["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.update_shortcut_row(shortcut, row)  # Optimized row update

    def prompt_for_variables(self, placeholders, command):
        """
        Prompts the user for input to replace multiple placeholders.
        """
        dialog = QDialog(self)
        dialog.setWindowTitle("Input Required")
        layout = QVBoxLayout(dialog)

        command_layout = QHBoxLayout()
        command_parts = re.split(r"({.*?})", command)
        input_fields = {}

        for part in command_parts:
            if part.startswith("{") and part.endswith("}"):
                placeholder = part[1:-1]
                input_field = QLineEdit(dialog)
                input_field.setPlaceholderText(placeholder)  # Set ghost text
                input_fields[placeholder] = input_field
                command_layout.addWidget(input_field)
            else:
                command_layout.addWidget(QLabel(part, dialog))

        layout.addLayout(command_layout)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, dialog)
        layout.addWidget(button_box)

        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)

        if dialog.exec_() == QDialog.Accepted:
            return {ph: input_fields[ph].text().strip() for ph in input_fields}
        return None

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
    def update_shortcut_row(self, shortcut, row_index):
        """
        Updates a single shortcut row in the model.
        """
        self.model.shortcuts[row_index] = shortcut  # Update the shortcut data in the model
        self.model.dataChanged.emit(  # Notify the view to update the specific row
            self.model.index(row_index, 0),  # Start index (first column of the row)
            self.model.index(row_index, self.model.columnCount() - 1)  # End index (last column of the row)
        )
        
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
            if (placeholder_label == "time"):
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

            cursor = conn_memory.cursor()

            # Ensure the category exists or create it
            cursor.execute("""
                INSERT OR IGNORE INTO categories (name) VALUES (?)
            """, (new_data["category"],))
            cursor.execute("""
                SELECT id FROM categories WHERE name = ?
            """, (new_data["category"],))
            category_id = cursor.fetchone()[0]

            # Insert the new shortcut
            cursor.execute("""
                INSERT INTO shortcuts (name, command, description, category_id, use_powershell)
                VALUES (?, ?, ?, ?, ?)
            """, (new_data["name"], new_data["command"], new_data["description"], 
                category_id, new_data["use_powershell"]))
            shortcut_id = cursor.lastrowid

            # Batch insert tags
            tags = [(tag,) for tag in new_data["tags"]]
            cursor.executemany("INSERT OR IGNORE INTO tags (name) VALUES (?)", tags)

            # Fetch tag IDs
            cursor.execute("SELECT id, name FROM tags WHERE name IN ({})".format(
                ",".join("?" for _ in new_data["tags"])
            ), new_data["tags"])
            tag_ids = [row[0] for row in cursor.fetchall()]

            # Batch insert shortcut-tags
            shortcut_tags = [(shortcut_id, tag_id) for tag_id in tag_ids]
            cursor.executemany("""
                INSERT INTO shortcut_tags (shortcut_id, tag_id)
                VALUES (?, ?)
            """, shortcut_tags)

            conn_memory.commit()

            # Refresh the UI
            self.load_shortcuts()
            self.update_category_sidebar()
            self.refresh_table()

    def on_edit_shortcut(self):
        selected_indexes = self.table.selectionModel().selectedRows()
        if not selected_indexes:
            return

        table_row = selected_indexes[0].row()
        shortcut, original_index = self.displayed_pairs[table_row]

        dialog = ShortcutDialog(self, shortcut_data=shortcut)

        if dialog.exec_() == QDialog.Accepted:
            updated_data = dialog.get_data()

            cursor = conn_memory.cursor()

            # Ensure the category exists or create it
            cursor.execute("""
                INSERT OR IGNORE INTO categories (name) VALUES (?)
            """, (updated_data["category"],))
            cursor.execute("""
                SELECT id FROM categories WHERE name = ?
            """, (updated_data["category"],))
            category_id = cursor.fetchone()[0]

            # Update the shortcut
            cursor.execute("""
                UPDATE shortcuts
                SET name = ?, command = ?, description = ?, category_id = ?, use_powershell = ?
                WHERE id = ?
            """, (updated_data["name"], updated_data["command"], updated_data["description"], 
                category_id, updated_data["use_powershell"], shortcut["id"]))

            # Update tags
            cursor.execute("DELETE FROM shortcut_tags WHERE shortcut_id = ?", (shortcut["id"],))
            for tag in updated_data["tags"]:
                cursor.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (tag,))
                cursor.execute("""
                    INSERT INTO shortcut_tags (shortcut_id, tag_id)
                    SELECT ?, id FROM tags WHERE name = ?
                """, (shortcut["id"], tag))

            conn_memory.commit()
            print(f"Shortcut updated: {updated_data['name']}")  # Debug output

            # Refresh the UI
            self.remove_unused_categories()  # Remove unused categories
            self.load_shortcuts()
            self.update_category_sidebar()
            self.refresh_table()

    def on_delete_shortcut(self):
        selected_indexes = self.table.selectionModel().selectedRows()
        if not selected_indexes:
            return

        table_row = selected_indexes[0].row()
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
            cursor = conn_memory.cursor()

            # Delete the shortcut and its relationships
            cursor.execute("DELETE FROM shortcut_tags WHERE shortcut_id = ?", (shortcut["id"],))
            cursor.execute("DELETE FROM shortcuts WHERE id = ?", (shortcut["id"],))

            conn_memory.commit()
            print(f"Shortcut deleted: {shortcut_name}")  # Debug output

            # Refresh the UI
            self.remove_unused_categories()  # Remove unused categories
            self.load_shortcuts()
            self.update_category_sidebar()
            self.refresh_table()

    def remove_unused_categories(self):
        """
        Remove categories that are no longer associated with any shortcuts.
        """
        print("remove_unused_categories called.")  # Debug log

        cursor = conn_memory.cursor()

        # Check for unused categories
        cursor.execute("""
            SELECT id, name
            FROM categories
            WHERE id NOT IN (
                SELECT DISTINCT category_id
                FROM shortcuts
                WHERE category_id IS NOT NULL
            )
        """)
        unused_categories = cursor.fetchall()
        print(f"Unused categories found: {unused_categories}")  # Debug log

        # Delete unused categories
        cursor.execute("""
            DELETE FROM categories
            WHERE id NOT IN (
                SELECT DISTINCT category_id
                FROM shortcuts
                WHERE category_id IS NOT NULL
            )
        """)

        conn_memory.commit()
        print("Unused categories removed.")  # Debug log

    def update_category_sidebar(self):
        """
        Clear and repopulate the category_list QListWidget.
        Includes an '(All Categories)' item to reset filter.
        """
        self.category_list.clear()

        cursor = conn_memory.cursor()
        cursor.execute("""
            SELECT name
            FROM categories
            WHERE name IS NOT NULL AND TRIM(name) != ''
            ORDER BY name
        """)
        categories = [row[0] for row in cursor.fetchall()]

        # Add an item to show all categories
        self.category_list.addItem("(All Categories)")

        # Add the individual categories
        for cat in categories:
            self.category_list.addItem(cat)

        # Enable context menu on category_list
        self.category_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.category_list.customContextMenuRequested.connect(self.show_category_context_menu)

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

        # Add PowerShell toggle after category and apply current theme
        self.powershell_toggle = QCheckBox("Use PowerShell instead of CMD")
        if isinstance(parent, Commander):  # Check if parent is Commander
            if parent.current_theme == "dark":
                self.setStyleSheet(DARK_STYLESHEET)
            else:
                self.setStyleSheet(LIGHT_STYLESHEET)
        layout.addRow("Terminal:", self.powershell_toggle)

        # If editing, populate fields
        if self.edit_mode and shortcut_data is not None:
            self.name_edit.setText(shortcut_data.get("name", ""))
            self.command_edit.setText(shortcut_data.get("command", ""))
            self.description_edit.setText(shortcut_data.get("description", ""))
            tag_list = shortcut_data.get("tags", [])
            self.tags_edit.setText(", ".join(tag_list))
            self.category_edit.setText(shortcut_data.get("category", ""))
            self.powershell_toggle.setChecked(bool(shortcut_data.get("use_powershell", False)))

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
            "category": category,
            "use_powershell": self.powershell_toggle.isChecked()
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
            "use_powershell": self.powershell_toggle.isChecked()
        }

def main():
    try:
        app = QApplication(sys.argv)
        app.setStyle(QStyleFactory.create("Fusion"))

        # Initialize in-memory database
        init_database()

        # Set up the main application window
        window = Commander()
        window.show()

        # Run the application
        exit_code = app.exec_()

        # Flush changes to disk on exit
        flush_memory_to_disk()

        # Clean up database connections
        conn_memory.close()
        conn_disk.close()

        sys.exit(exit_code)
    except Exception as e:
        traceback.print_exc()
        sys.exit(1)
if __name__ == "__main__":
    main()