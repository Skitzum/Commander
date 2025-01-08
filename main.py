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
from PyQt5.QtCore import Qt, QUrl, QAbstractTableModel, QThread
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
    QListWidgetItem,  # Add this import
    QSplitter,
    QMenu,
    QDialogButtonBox,
    QTextEdit
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

    # Add new tables for groups if they don't exist
    cursor_memory.execute("""
        CREATE TABLE IF NOT EXISTS groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor_memory.execute("""
        CREATE TABLE IF NOT EXISTS group_shortcuts (
            group_id INTEGER,
            shortcut_id INTEGER,
            execution_order INTEGER,
            FOREIGN KEY (group_id) REFERENCES groups(id),
            FOREIGN KEY (shortcut_id) REFERENCES shortcuts(id),
            PRIMARY KEY (group_id, shortcut_id)
        )
    """)
    
    conn_memory.commit()

def flush_memory_to_disk():
    """
    Flush changes from the in-memory database back to the persistent disk database.
    """
    global conn_disk, conn_memory
    cursor_disk = conn_disk.cursor()

    # Clear existing data from disk tables
    tables_to_clear = ["settings", "shortcuts", "categories", "tags", "shortcut_tags", "preferences", "groups", "group_shortcuts"]
    for table in tables_to_clear:
        cursor_disk.execute(f"DELETE FROM {table};")
        # Reset the autoincrement counter
        cursor_disk.execute(f"DELETE FROM sqlite_sequence WHERE name='{table}';")

    # Dump in-memory data back to disk
    for line in conn_memory.iterdump():
        # Skip problematic statements
        if any(
            line.startswith(keyword)
            for keyword in ("CREATE TABLE", "CREATE INDEX", "CREATE UNIQUE INDEX", "BEGIN TRANSACTION", "COMMIT")
        ):
            continue
        try:
            # Remove any INSERT statements that specify IDs for auto-increment tables
            if line.startswith("INSERT INTO \"groups\""):
                parts = line.split("VALUES")
                if len(parts) == 2:
                    values = eval(parts[1].rstrip(";"))
                    # Skip the ID, only insert name and created_at
                    new_line = f'INSERT INTO "groups" (name, created_at) VALUES ({repr(values[1])}, {repr(values[2])});'
                    cursor_disk.execute(new_line)
                    continue
            cursor_disk.execute(line)
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
        self.selected_group = None
        self.is_group_selection_mode = False
        self.previous_selection_mode = QAbstractItemView.SingleSelection  # Add this line

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
        # Initialize status bar after UI
        self.status_bar = self.statusBar()  # Store as instance variable
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

        # Initialize context menu for groups
        self.groups_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.groups_list.customContextMenuRequested.connect(self.show_group_context_menu)

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
        if (event.type() == event.WindowStateChange):
            if (self.windowState() & Qt.WindowMaximized):
                # Window was maximized
                self.adjust_column_widths()
            elif (event.oldState() & Qt.WindowMaximized):
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
        Enhanced context menu with dynamic group operations.
        """
        menu = QMenu(self)
        indexes = self.table.selectionModel().selectedRows()
        
        if not indexes:
            return
            
        row = indexes[0].row()
        shortcut = self.displayed_pairs[row][0]
        
        # Basic actions
        execute_action = menu.addAction("Execute")
        copy_action = menu.addAction("Copy Command")
        menu.addSeparator()
        edit_action = menu.addAction("Edit")
        delete_action = menu.addAction("Delete")
        
        # Group operations submenu
        groups_menu = None
        if self.groups_list.count() > 0:  # Only if groups exist
            menu.addSeparator()
            groups_menu = menu.addMenu("Add to Group")
            
            # Add each group as an option
            for i in range(self.groups_list.count()):
                group_item = self.groups_list.item(i)
                action = groups_menu.addAction(group_item.text())
                action.setData(group_item.data(Qt.UserRole))
                
                # If shortcut is already in this group, disable the option
                cursor = conn_memory.cursor()
                cursor.execute("""
                    SELECT 1 FROM group_shortcuts 
                    WHERE group_id = ? AND shortcut_id = ?
                """, (group_item.data(Qt.UserRole), shortcut["id"]))
                
                if cursor.fetchone():
                    action.setEnabled(False)
                    action.setText(f"{group_item.text()} (Already Added)")

        action = menu.exec_(self.table.viewport().mapToGlobal(position))
        if not action:
            return

        if action == execute_action:
            self.confirm_and_execute()
        elif action == copy_action:
            self.copy_selected_command()
        elif action == edit_action:
            self.on_edit_shortcut()
        elif action == delete_action:
            self.on_delete_shortcut()
        elif groups_menu and action.parent() == groups_menu:
            self.add_to_group(shortcut["id"], action.data())
            self.info_label.setText(f"Added shortcut to group '{action.text()}'")

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
        Also resets any group selection.
        """
        # Reset any group selection when changing categories
        self.deselect_group()  # This now properly resets everything
        
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
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # Create vertical splitter for categories and groups
        left_splitter = QSplitter(Qt.Vertical)
        
        # Add category list to top of splitter
        self.category_list = QListWidget()
        self.category_list.itemClicked.connect(self.on_category_selected)
        left_splitter.addWidget(self.category_list)
        
        # Add groups widget to bottom of splitter
        groups_widget = QWidget()
        groups_layout = QVBoxLayout(groups_widget)
        
        groups_header = QLabel("Groups")
        groups_layout.addWidget(groups_header)
        
        self.groups_list = QListWidget()
        self.groups_list.itemClicked.connect(self.on_group_selected)
        groups_layout.addWidget(self.groups_list)
        
        # Add group management buttons
        group_buttons = QHBoxLayout()
        self.add_group_btn = QPushButton("+")
        self.add_group_btn.setMaximumWidth(30)
        self.add_group_btn.clicked.connect(self.on_add_group)
        self.delete_group_btn = QPushButton("-")
        self.delete_group_btn.setMaximumWidth(30)
        self.delete_group_btn.clicked.connect(self.on_delete_group)
        self.run_group_btn = QPushButton("Run")
        self.run_group_btn.setMaximumWidth(50)
        self.run_group_btn.clicked.connect(self.on_run_group)
        
        group_buttons.addWidget(self.add_group_btn)
        group_buttons.addWidget(self.delete_group_btn)
        group_buttons.addWidget(self.run_group_btn)
        group_buttons.addStretch()
        groups_layout.addLayout(group_buttons)
        
        left_splitter.addWidget(groups_widget)
        
        # Set initial sizes (categories:groups = 60:40)
        left_splitter.setSizes([600, 400])
        
        left_layout.addWidget(left_splitter)
        splitter.addWidget(left_panel)

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

        # Add cancel button (hidden by default)
        self.cancel_group_selection_button = QPushButton("Cancel Group Selection")
        self.cancel_group_selection_button.setMaximumWidth(200)
        self.cancel_group_selection_button.clicked.connect(self.cancel_group_selection_mode)
        self.cancel_group_selection_button.hide()

        bottom_layout.addWidget(self.execute_button)
        bottom_layout.addWidget(self.cancel_group_selection_button)
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
        self.update_groups_list()
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
        if self.selected_group:
            # Re-select the current group to refresh its view
            current_group = self.groups_list.findItems(
                self.groups_list.currentItem().text(), 
                Qt.MatchExactly
            )[0]
            self.on_group_selected(current_group)
        else:
            # Normal refresh
            self.load_shortcuts()
            self.sort_table(self.current_sort_method)
            self.filter_table()
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
        if self.is_group_selection_mode:
            selected_count = len(self.table.selectionModel().selectedRows())
            self.status_bar.showMessage(
                f"Selected {selected_count} shortcut{'s' if selected_count != 1 else ''} "
                f"for group: {self.current_group_item.text()}"
            )
            
            # Highlight save button if items are selected
            if selected_count > 0:
                self.add_button.setStyleSheet("background-color: red; color: white;")
            else:
                self.add_button.setStyleSheet("")
            return

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
                
                # Add group management context menu
                menu = QMenu(self)
                if self.selected_group:
                    add_to_group = menu.addAction("Add to Group")
                    add_to_group.triggered.connect(lambda: self.add_to_group(shortcut["id"]))

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
        """
        Modified to handle both single shortcut and group execution
        """
        if self.selected_group:
            # Handle group execution
            if not self.confirmation_pending:
                self.execute_button.setText("Confirm Run Group")
                self.confirmation_pending = True
                self.execute_button.setStyleSheet("background-color: green; color: white;")
            else:
                self.on_run_group()
                self.execute_button.setText("Run Group")
                self.confirmation_pending = False
                self.execute_button.setStyleSheet("background-color: red; color: white;")
        else:
            # Handle single shortcut execution
            if not self.confirmation_pending:
                self.execute_button.setText("Confirm")
                self.confirmation_pending = True
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
        placeholders = re.findall(r"{{(.*?)}}", command)
        if placeholders:
            print(f"Detected placeholders: {placeholders}")
            placeholder_values = self.prompt_for_variables(placeholders, command)
            if not placeholder_values:  # Handle missing input
                self.info_label.setText("Execution canceled. Missing values for placeholders.")
                print("Command canceled due to missing values for placeholders.")
                return
            # Replace the placeholders with the user-provided values
            for ph, val in placeholder_values.items():
                command = command.replace(f"{{{{{ph}}}}}", val)

        # Re-validate command to check for unresolved placeholders
        if "{{" in command or "}}" in command:
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
        command_parts = re.split(r"({{.*?}})", command)
        input_fields = {}

        for part in command_parts:
            if part.startswith("{{") and part.endswith("}}"):
                placeholder = part[2:-2]
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

    def on_add_group(self):
        name, ok = QInputDialog.getText(self, "New Group", "Enter group name:")
        if ok and name.strip():
            cursor = conn_memory.cursor()
            try:
                cursor.execute("INSERT INTO groups (name) VALUES (?)", (name.strip(),))
                conn_memory.commit()
                self.update_groups_list()
            except sqlite3.IntegrityError:
                QMessageBox.warning(self, "Error", "A group with that name already exists.")

    def on_delete_group(self):
        current = self.groups_list.currentItem()
        if not current:
            return
            
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Delete group '{current.text()}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            cursor = conn_memory.cursor()
            cursor.execute("DELETE FROM groups WHERE name = ?", (current.text(),))
            cursor.execute("DELETE FROM group_shortcuts WHERE group_id = ?", 
                         (current.data(Qt.UserRole),))
            conn_memory.commit()
            self.update_groups_list()

    def on_group_selected(self, item):
        """Called when a group is selected from the groups list"""
        # Reset confirmation state when changing selection
        self.confirmation_pending = False
        
        if item is None:
            self.deselect_group()
            return
            
        self.selected_group = item.data(Qt.UserRole)
        self.delete_group_btn.setEnabled(True)
        self.run_group_btn.setEnabled(True)
        
        # Update table to show group shortcuts
        cursor = conn_memory.cursor()
        # Modified query to explicitly specify columns
        cursor.execute("""
            SELECT 
                s.id,
                s.name,
                s.command,
                s.description,
                s.category_id,
                s.usage_count,
                s.use_powershell,
                s.updated_at
            FROM shortcuts s
            JOIN group_shortcuts gs ON s.id = gs.shortcut_id
            WHERE gs.group_id = ?
            ORDER BY gs.execution_order
        """, (self.selected_group,))
        
        # Convert to shortcut dictionaries with correct column mapping
        group_shortcuts = [
            {
                "id": row[0],
                "name": row[1],
                "command": row[2],
                "description": row[3] or "No description available",
                "category": "",  # Category will be filled later
                "usage_count": int(row[5]) if row[5] is not None else 0,  # Fixed column index
                "use_powershell": bool(row[6]) if row[6] is not None else False,
                "updated_at": row[7] or ""  # Fixed column index
            }
            for row in cursor.fetchall()
        ]
        
        # Update displayed pairs and model
        self.displayed_pairs = [(s, i) for i, s in enumerate(group_shortcuts)]
        self.model.shortcuts = group_shortcuts
        self.model.layoutChanged.emit()
        
        # Update status and button text
        self.info_label.setText(f"Showing {len(group_shortcuts)} shortcuts in group '{item.text()}'")
        self.execute_button.setText("Run Group")
        self.execute_button.setEnabled(len(group_shortcuts) > 0)
    def deselect_group(self):
        """Deselect the current group and reset to normal view."""
        self.selected_group = None
        self.groups_list.clearSelection()
        self.execute_button.setText("Execute")
        self.execute_button.setEnabled(False)
        self.confirmation_pending = False
        
        # Reset button states
        self.delete_group_btn.setEnabled(False)
        self.run_group_btn.setEnabled(False)
        
        # Refresh table to show all shortcuts
        self.load_shortcuts()
        self.sort_table(self.current_sort_method)
        self.filter_table()

    def update_groups_list(self):
        """Refresh the groups list widget"""
        self.groups_list.clear()
        cursor = conn_memory.cursor()
        cursor.execute("SELECT id, name FROM groups ORDER BY name")
        for group_id, name in cursor.fetchall():
            item = QListWidgetItem(name)  # Use QListWidgetItem directly
            item.setData(Qt.UserRole, group_id)
            self.groups_list.addItem(item)

    def on_run_group(self):
        """
        Execute all shortcuts in the selected group in order.
        """
        if not self.selected_group:
            return
            
        cursor = conn_memory.cursor()
        cursor.execute("""
            SELECT s.* FROM shortcuts s
            JOIN group_shortcuts gs ON s.id = gs.shortcut_id
            WHERE gs.group_id = ?
            ORDER BY gs.execution_order
        """, (self.selected_group,))
        
        shortcuts = cursor.fetchall()
        
        if not shortcuts:
            QMessageBox.information(self, "Run Group", "No shortcuts in this group.")
            return

        preview = "\n".join([f"• {row[1]}: {row[2]}" for row in shortcuts])
        reply = QMessageBox.question(
            self,
            "Confirm Group Execution",
            f"Execute these {len(shortcuts)} shortcuts?\n\n{preview}",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            success_count = 0
            for shortcut in shortcuts:
                QApplication.processEvents()  # Keep UI responsive
                if self.execute_shortcut(shortcut):
                    success_count += 1
                QThread.msleep(500)  # Reduced delay between executions
                
            self.info_label.setText(
                f"Group execution complete: {success_count}/{len(shortcuts)} successful"
            )

    def add_to_group(self, shortcut_id, group_id):
        """
        Add a shortcut to a group with smart ordering
        """
        cursor = conn_memory.cursor()
        
        # Get the next execution order number
        cursor.execute("""
            SELECT COALESCE(MAX(execution_order), -1) + 1
            FROM group_shortcuts
            WHERE group_id = ?
        """, (group_id,))
        
        next_order = cursor.fetchone()[0]
        
        # Add the shortcut to the group if not already present
        cursor.execute("""
            INSERT OR IGNORE INTO group_shortcuts (group_id, shortcut_id, execution_order)
            VALUES (?, ?, ?)
        """, (group_id, shortcut_id, next_order))
        
        conn_memory.commit()
        
        # If the group is currently selected, refresh its view
        if self.selected_group == group_id:
            self.on_group_selected(self.groups_list.currentItem())

    def show_group_context_menu(self, position):
        """Show context menu for groups list with enhanced options."""
        group_item = self.groups_list.itemAt(position)
        if not group_item:
            return
            
        menu = QMenu(self)
        edit_shortcuts = menu.addAction("Edit Shortcuts")
        manage_order = menu.addAction("Manage Order")
        menu.addSeparator()
        rename_action = menu.addAction("Rename Group")
        clear_action = menu.addAction("Clear Shortcuts")
        menu.addSeparator()
        unselect_action = menu.addAction("Unselect Group")  # Add unselect option
        delete_action = menu.addAction("Delete Group")
        
        action = menu.exec_(self.groups_list.viewport().mapToGlobal(position))
        if not action:
            return
            
        if action == edit_shortcuts:
            self.enter_group_selection_mode(group_item)
        elif action == manage_order:
            self.show_manage_shortcuts_dialog(group_item)
        elif action == rename_action:
            self.rename_group(group_item)
        elif action == clear_action:
            self.clear_group_shortcuts(group_item)
        elif action == unselect_action:
            self.deselect_group()
        elif action == delete_action:
            self.on_delete_group()

    def enter_group_selection_mode(self, group_item):
        """Enter mode for selecting shortcuts for a group."""
        self.is_group_selection_mode = True
        self.current_group_item = group_item
        self.previous_selection_mode = self.table.selectionMode()  # Store current mode
        self.table.setSelectionMode(QAbstractItemView.MultiSelection)
        
        # Get existing shortcuts in group
        cursor = conn_memory.cursor()
        cursor.execute("""
            SELECT shortcut_id FROM group_shortcuts 
            WHERE group_id = ?
        """, (group_item.data(Qt.UserRole),))
        existing_shortcuts = {row[0] for row in cursor.fetchall()}
        
        # Pre-select existing shortcuts
        for row in range(len(self.displayed_pairs)):
            shortcut = self.displayed_pairs[row][0]
            if shortcut['id'] in existing_shortcuts:
                self.table.selectRow(row)
        
        # Update UI for selection mode
        self.status_bar.showMessage(f"Select shortcuts for group: {group_item.text()}")
        self.execute_button.hide()
        self.cancel_group_selection_button.show()
        self.add_button.setText("Save Group Selection")
        self.add_button.clicked.disconnect()
        self.add_button.clicked.connect(self.save_group_shortcuts)
        
        # Disable other buttons
        self.edit_button.setEnabled(False)
        self.delete_button.setEnabled(False)

    def clear_group_shortcuts(self, group_item):
        """Remove all shortcuts from a group."""
        reply = QMessageBox.question(
            self, 
            "Confirm Clear",
            f"Remove all shortcuts from group '{group_item.text()}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            group_id = group_item.data(Qt.UserRole)
            cursor = conn_memory.cursor()
            cursor.execute("DELETE FROM group_shortcuts WHERE group_id = ?", (group_id,))
            conn_memory.commit()
            self.info_label.setText(f"Cleared all shortcuts from group '{group_item.text()}'")

    def save_group_shortcuts(self):
        """Save the selected shortcuts to the current group."""
        if not self.is_group_selection_mode or not hasattr(self, 'current_group_item'):
            return
            
        selected_rows = self.table.selectionModel().selectedRows()
        selected_shortcuts = [self.displayed_pairs[index.row()][0]['id'] for index in selected_rows]
        
        group_id = self.current_group_item.data(Qt.UserRole)
        cursor = conn_memory.cursor()
        
        # Clear existing shortcuts
        cursor.execute("DELETE FROM group_shortcuts WHERE group_id = ?", (group_id,))
        
        # Add new shortcuts with order
        for order, shortcut_id in enumerate(selected_shortcuts):
            cursor.execute("""
                INSERT INTO group_shortcuts (group_id, shortcut_id, execution_order)
                VALUES (?, ?, ?)
            """, (group_id, shortcut_id, order))
        
        conn_memory.commit()
        
        # Exit selection mode and update UI
        self.exit_group_selection_mode()
        self.info_label.setText(f"Updated shortcuts in group '{self.current_group_item.text()}'")

    def cancel_group_selection_mode(self):
        """
        Exit group selection mode without saving changes.
        """
        self.exit_group_selection_mode()

    def exit_group_selection_mode(self):
        """
        Restore normal table mode.
        """
        if not hasattr(self, 'is_group_selection_mode'):
            return
            
        self.is_group_selection_mode = False
        
        # Set back to single selection mode if previous mode wasn't stored
        selection_mode = getattr(self, 'previous_selection_mode', QAbstractItemView.SingleSelection)
        self.table.setSelectionMode(selection_mode)
        
        self.status_bar.clearMessage()
        
        # Remove the selection info label
        if hasattr(self, 'selection_info_label'):
            self.selection_info_label.deleteLater()
            delattr(self, 'selection_info_label')
        
        self.execute_button.show()
        self.cancel_group_selection_button.hide()
        self.add_button.setText("Add Shortcut")
        self.add_button.setStyleSheet("")  # Reset button style
        self.add_button.clicked.disconnect()
        self.add_button.clicked.connect(self.on_add_shortcut)
        
        # Re-enable buttons
        self.edit_button.setEnabled(True)
        self.delete_button.setEnabled(True)
        
        # Clear selection
        self.table.clearSelection()

    def show_add_shortcuts_dialog(self, group_item):
        """
        Show dialog for adding shortcuts to a group.
        """
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Add Shortcuts to {group_item.text()}")
        layout = QVBoxLayout(dialog)

        # Create list widget for shortcuts
        shortcuts_list = QListWidget(dialog)
        shortcuts_list.setSelectionMode(QAbstractItemView.MultiSelection)

        # Populate with available shortcuts
        group_id = group_item.data(Qt.UserRole)
        cursor = conn_memory.cursor()
        
        # Get existing shortcuts in the group
        cursor.execute("""
            SELECT shortcut_id FROM group_shortcuts WHERE group_id = ?
        """, (group_id,))
        existing_shortcuts = {row[0] for row in cursor.fetchall()}

        # Get all shortcuts
        cursor.execute("SELECT id, name, command FROM shortcuts ORDER BY name")
        for row in cursor.fetchall():
            item = QListWidgetItem(f"{row[1]} ({row[2]})")
            item.setData(Qt.UserRole, row[0])
            shortcuts_list.addItem(item)
            # Pre-select if already in group
            item.setSelected(row[0] in existing_shortcuts)

        layout.addWidget(shortcuts_list)

        # Add buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)

        if dialog.exec_() == QDialog.Accepted:
            # Get selected shortcuts
            selected_ids = [item.data(Qt.UserRole) for item in shortcuts_list.selectedItems()]
            
            # Clear existing shortcuts
            cursor.execute("DELETE FROM group_shortcuts WHERE group_id = ?", (group_id,))
            
            # Add new shortcuts with order
            for order, shortcut_id in enumerate(selected_ids):
                cursor.execute("""
                    INSERT INTO group_shortcuts (group_id, shortcut_id, execution_order)
                    VALUES (?, ?, ?)
                """, (group_id, shortcut_id, order))
            
            conn_memory.commit()
            self.info_label.setText(f"Updated shortcuts in group '{group_item.text()}'")

    def show_manage_shortcuts_dialog(self, group_item):
        """
        Show dialog for managing shortcuts order in a group.
        """
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Manage Shortcuts in {group_item.text()}")
        layout = QVBoxLayout(dialog)

        # Create list widget for shortcuts
        shortcuts_list = QListWidget(dialog)
        shortcuts_list.setDragDropMode(QAbstractItemView.InternalMove)

        # Get shortcuts in order
        group_id = group_item.data(Qt.UserRole)
        cursor = conn_memory.cursor()
        cursor.execute("""
            SELECT s.id, s.name, s.command
            FROM shortcuts s
            JOIN group_shortcuts gs ON s.id = gs.shortcut_id
            WHERE gs.group_id = ?
            ORDER BY gs.execution_order
        """, (group_id,))

        # Add shortcuts to list
        for row in cursor.fetchall():
            item = QListWidgetItem(f"{row[1]} ({row[2]})")
            item.setData(Qt.UserRole, row[0])
            shortcuts_list.addItem(item)

        layout.addWidget(shortcuts_list)

        # Add buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)

        if dialog.exec_() == QDialog.Accepted:
            # Save new order
            cursor.execute("DELETE FROM group_shortcuts WHERE group_id = ?", (group_id,))
            
            for order in range(shortcuts_list.count()):
                item = shortcuts_list.item(order)
                shortcut_id = item.data(Qt.UserRole)
                cursor.execute("""
                    INSERT INTO group_shortcuts (group_id, shortcut_id, execution_order)
                    VALUES (?, ?, ?)
                """, (group_id, shortcut_id, order))
            
            conn_memory.commit()
            self.info_label.setText(f"Updated shortcuts order in group '{group_item.text()}'")

    def on_table_context_menu(self, position):
        """
        Enhanced table context menu with group operations.
        """
        menu = QMenu(self)
        
        # Get selected shortcut
        indexes = self.table.selectionModel().selectedRows()
        if indexes:
            row = indexes[0].row()
            shortcut = self.displayed_pairs[row][0]
            
            # Add basic actions
            execute_action = menu.addAction("Execute")
            copy_command_action = menu.addAction("Copy Command")
            menu.addSeparator()
            edit_action = menu.addAction("Edit")
            delete_action = menu.addAction("Delete")
            
            # Add groups submenu
            if len(self.groups_list) > 0:  # Only if groups exist
                menu.addSeparator()
                groups_menu = menu.addMenu("Add to Group")
                
                # Add each group as an action
                for i in range(self.groups_list.count()):
                    group_item = self.groups_list.item(i)
                    group_action = groups_menu.addAction(group_item.text())
                    group_action.setData(group_item.data(Qt.UserRole))

            action = menu.exec_(self.table.viewport().mapToGlobal(position))
            
            if not action:
                return
                
            if action == execute_action:
                self.confirm_and_execute()
            elif action == copy_command_action:
                self.copy_selected_command()
            elif action == edit_action:
                self.on_edit_shortcut()
            elif action == delete_action:
                self.on_delete_shortcut()
            elif action.parent() == groups_menu:
                # Add to selected group
                group_id = action.data()
                cursor = conn_memory.cursor()
                
                # Get next execution order for the group
                cursor.execute("""
                    SELECT COALESCE(MAX(execution_order), -1) + 1
                    FROM group_shortcuts
                    WHERE group_id = ?
                """, (group_id,))
                next_order = cursor.fetchone()[0]
                
                # Add shortcut to group
                cursor.execute("""
                    INSERT OR REPLACE INTO group_shortcuts (group_id, shortcut_id, execution_order)
                    VALUES (?, ?, ?)
                """, (group_id, shortcut["id"], next_order))
                
                conn_memory.commit()
                self.info_label.setText(f"Added shortcut to group '{action.text()}'")

    def execute_shortcut(self, shortcut_data):
        """
        Execute a shortcut from its raw database data.
        Used primarily for group execution.
        """
        # Extract relevant data from the database row
        shortcut = {
            "id": shortcut_data[0],
            "name": shortcut_data[1],
            "command": shortcut_data[2],
            "description": shortcut_data[3],
            "use_powershell": bool(shortcut_data[7]) if len(shortcut_data) > 7 else False
        }

        # Validate command
        command = shortcut.get("command", "").strip()
        if not command:
            self.info_label.setText(f"No command for shortcut: {shortcut.get('name')}")
            return

        # Add placeholder handling
        placeholders = re.findall(r"{{(.*?)}}", command)
        if placeholders:
            print(f"Detected placeholders: {placeholders}")
            placeholder_values = self.prompt_for_variables(placeholders, command)
            if not placeholder_values:  # Handle missing input
                self.info_label.setText(f"Execution canceled for {shortcut['name']}. Missing values for placeholders.")
                print("Command canceled due to missing values for placeholders.")
                return
            # Replace the placeholders with the user-provided values
            for ph, val in placeholder_values.items():
                command = command.replace(f"{{{{{ph}}}}}", val)

        # Re-validate command to check for unresolved placeholders
        if "{{" in command or "}}" in command:
            self.info_label.setText(f"Invalid command for {shortcut['name']}: Unresolved placeholders remain.")
            print("Invalid or unresolved placeholders remain in command:", command)
            return

        # Rest of execution logic
        # Prepare command based on file type
        if command.endswith(".bat"):
            if shortcut.get("use_powershell", False):
                command = f"powershell -NoExit -Command \"& '{command}'\""
            else:
                command = f"cmd.exe /c \"{command}\""
        elif command.endswith(".ps1"):
            command = f"powershell -ExecutionPolicy Bypass -NoExit -File \"{command}\""
        elif command.endswith(".exe"):
            command = f"\"{command}\""

        # Execute based on terminal preference
        if shortcut.get("use_powershell", False):
            interactive_command = f"start powershell -NoExit -Command \"{command}\""
        else:
            interactive_command = f"start cmd /k {command}"

        # Execute the command
        try:
            subprocess.Popen(
                interactive_command,
                shell=True,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                close_fds=True,
                creationflags=subprocess.DETACHED_PROCESS if os.name == 'nt' else 0
            )

            # Update usage count and timestamp
            cursor = conn_memory.cursor()
            cursor.execute("""
                UPDATE shortcuts 
                SET usage_count = usage_count + 1,
                    updated_at = ?
                WHERE id = ?
            """, (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), shortcut["id"]))
            conn_memory.commit()

            # Log execution
            self.update_log(f"Executed group shortcut: {shortcut['name']} - {command}")
            self.info_label.setText(f"Executed: {shortcut['name']}")

        except Exception as e:
            self.info_label.setText(f"Error executing {shortcut['name']}: {str(e)}")
            self.update_log(f"Error executing {shortcut['name']}: {str(e)}")

    def clear_group_shortcuts(self, group_item):
        """
        Remove all shortcuts from a group.
        """
        reply = QMessageBox.question(
            self, 
            "Confirm Clear",
            f"Remove all shortcuts from group '{group_item.text()}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            group_id = group_item.data(Qt.UserRole)
            cursor = conn_memory.cursor()
            cursor.execute("DELETE FROM group_shortcuts WHERE group_id = ?", (group_id,))
            conn_memory.commit()
            self.info_label.setText(f"Cleared all shortcuts from group '{group_item.text()}'")

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
        Returns the dialog data as a dictionary.
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