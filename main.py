import sys
import os
import subprocess
import ctypes
import re
import shlex
import sqlite3

from PyQt5.QtCore import Qt
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
    QComboBox,
    QPushButton,
    QFileDialog,
    QFormLayout,
    QCheckBox,
    QListWidget,
    QSplitter,
    QMenu
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
# Set path to Json file
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
        print("Failed to elevate:", e)
        return False
    
###############################################################################
# Commander Class
###############################################################################

class Commander(QMainWindow):
    def __init__(self, json_path="shortcuts.json"):
        super().__init__()
        self.shortcuts_data = []

        # This new list will store (shortcut, original_index) for the currently displayed table rows
        self.displayed_pairs = []

        # Set a default theme before initializing the UI
        self.current_theme = "light"  # Default to light theme

        # Track which category is selected (None => show all)
        self.selected_category = None

        # Window Title & Initial Size
        self.setWindowTitle("Commander")
        self.setMinimumSize(800, 400)
        self.resize(1000, 600)

        # Keep track of two-step confirm state
        self.confirmation_pending = False

        self.load_shortcuts()
        self.initUI()
        self.apply_theme(self.current_theme)  # Apply the loaded theme after UI initialization

        # Initially show all shortcuts
        pairs = [(s, i) for i, s in enumerate(self.shortcuts_data)]
        self.populate_table(pairs)
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
        # Connect to a function for adding categories
        edit_menu.addAction(add_category_action)

        remove_unused_action = QAction("Remove Unused Categories", self)
        remove_unused_action.triggered.connect(self.remove_unused_categories)
        edit_menu.addAction(remove_unused_action)

        preferences_action = QAction("Preferences", self)
        # Connect to a settings/preferences dialog
        edit_menu.addAction(preferences_action)

        # View menu
        view_menu = menubar.addMenu("View")

        refresh_action = QAction("Refresh", self)
        refresh_action.triggered.connect(self.filter_table)
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
        # Connect this to open a README file or link
        help_menu.addAction(documentation_action)

    def show_about_dialog(self):
        QMessageBox.information(
            self,
            "About Commander",
            "Commander Application\nVersion 1.0\nA handy tool for managing shortcuts.",
            QMessageBox.Ok
        )
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
        cursor.execute("SELECT name FROM categories ORDER BY name")
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
            self.filter_table()
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
            self.filter_table()

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

        # Set initial sizes or stretch factors
        splitter.setStretchFactor(0, 0)  # Left pane does not expand as much
        splitter.setStretchFactor(1, 1)  # Right pane expands more

        # Set default sizes (adjust as needed for your desired ratio)
        splitter.setSizes([150, 400])  # Left panel starts with 1/3 width, right panel 2/3
        
        # Add the splitter to the main layout
        main_layout.addWidget(splitter)

        # Finally, update the category sidebar to show all categories
        self.update_category_sidebar()

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
        if checked:
            self.current_theme = "dark"
        else:
            self.current_theme = "light"
        self.apply_theme(self.current_theme)
        self.save_shortcuts()

    ###########################################################################
    # LOADING / SAVING
    ###########################################################################
    def load_shortcuts(self):
        """
        Load shortcuts from SQLite database.
        """
        conn = sqlite3.connect(os.path.join(get_app_folder(), "commander.db"))
        cursor = conn.cursor()

        # Query shortcuts with their categories and tags
        cursor.execute("""
            SELECT s.id, s.name, s.command, s.description, s.requires_input,
                c.name AS category, GROUP_CONCAT(t.name) AS tags
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
                "requires_input": bool(row[4]),
                "category": row[5] or "",
                "tags": row[6].split(",") if row[6] else []
            }
            for row in cursor.fetchall()
        ]

        # Load settings (e.g., theme)
        cursor.execute("SELECT key, value FROM settings")
        self.settings_data = {row[0]: row[1] for row in cursor.fetchall()}
        self.current_theme = self.settings_data.get("theme", "light")

        conn.close()
        self.apply_theme(self.current_theme)

    def save_shortcuts(self):
        """
        Save shortcuts to the SQLite database.
        """
        conn = sqlite3.connect(os.path.join(get_app_folder(), "commander.db"))
        cursor = conn.cursor()

        # Save shortcuts
        for shortcut in self.shortcuts_data:
            cursor.execute("""
                INSERT OR REPLACE INTO shortcuts (id, name, command, description, requires_input, category_id)
                VALUES (?, ?, ?, ?, ?, (SELECT id FROM categories WHERE name = ?))
            """, (shortcut.get("id"), shortcut["name"], shortcut["command"], shortcut["description"],
                shortcut["requires_input"], shortcut["category"]))

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
        pairs is a list of (shortcut_dict, original_index).
        We'll store it in self.displayed_pairs so we know how to map
        row -> original index in self.shortcuts_data.
        """
        self.displayed_pairs = pairs  # store for later reference
        self.table.setRowCount(len(pairs))

        for row_idx, (shortcut, orig_idx) in enumerate(pairs):
            name = shortcut.get("name", "")
            command = shortcut.get("command", "")
            description = shortcut.get("description", "")
            tags = ", ".join(shortcut.get("tags", []))
            category = shortcut.get("category", "")

            item_name = QTableWidgetItem(name)
            item_command = QTableWidgetItem(command)
            item_tags = QTableWidgetItem(tags)
            item_category = QTableWidgetItem(category)

            if description:
                item_name.setToolTip(description)
                item_command.setToolTip(description)
                item_tags.setToolTip(description)
                item_category.setToolTip(description)

            self.table.setItem(row_idx, 0, item_name)
            self.table.setItem(row_idx, 1, item_command)
            self.table.setItem(row_idx, 2, item_tags)
            self.table.setItem(row_idx, 3, item_category)

        self.table.resizeColumnsToContents()

    ###########################################################################
    # SEARCH LOGIC
    ###########################################################################
    def filter_table(self):
        filter_text = self.search_bar.text().lower().strip()
        pairs = []

        for i, s in enumerate(self.shortcuts_data):
            # 1) If we have a selected_category, skip items that don't match it
            if self.selected_category:
                if s.get("category", "") != self.selected_category:
                    continue

            # 2) If we have a filter_text, skip items that don't contain it
            if filter_text:
                combined_text = " ".join([
                    s.get("name", ""),
                    s.get("command", ""),
                    " ".join(s.get("tags", [])),
                    s.get("category", "")
                ]).lower()
                if filter_text not in combined_text:
                    continue

            pairs.append((s, i))

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
        selected_items = self.table.selectedItems()
        if not selected_items:
            return  # No selection

        row = selected_items[0].row()
        shortcut, original_index = self.displayed_pairs[row]

        command = shortcut.get("command", "").strip()
        requires_input = shortcut.get("requires_input", False)

        # 1) Placeholder handling
        if requires_input:
            placeholders = re.findall(r"{(.*?)}", command)
            if placeholders:
                for ph in placeholders:
                    val = self.prompt_for_variable(ph)
                    if not val:
                        self.info_label.setText("Command cancelled or no input provided.")
                        return
                    # Replace placeholders
                    command = command.replace(f"{{{ph}}}", val)

        # 2) Parse the final command string into tokens with shlex
        try:
            tokens = shlex.split(command)
        except ValueError as e:
            # If there's a quoting error, or user typed something unparseable
            self.info_label.setText(f"Shlex parse error: {e}")
            return

        if not tokens:
            self.info_label.setText("No command tokens found.")
            return

        # For debugging: print(tokens)
        print("Parsed tokens:", tokens)

        # 3) Decide how to run
        first_token_lower = tokens[0].lower()

        # A) If first token ends with .exe, run it directly
        if first_token_lower.endswith(".exe"):
            full_cmd = tokens  # e.g. ["E:\\HwInfo64.exe", "--someArg"]
        # B) If first token is powershell.exe or second token is .ps1, run powershell
        elif first_token_lower.startswith("powershell") or (len(tokens) > 0 and tokens[0].lower().endswith(".ps1")):
            # If user typed "powershell.exe ..." => just use tokens as-is
            full_cmd = tokens
            # If you want to enforce something like "powershell.exe -NoExit", you can insert tokens here
        elif (len(tokens) > 1 and tokens[1].lower().endswith(".ps1")):
            # e.g. user typed "powershell -File something.ps1"
            full_cmd = tokens
        else:
            # C) Default: pass tokens to cmd /k
            # i.e. run cmd, /k, and then your tokens as arguments
            full_cmd = ["cmd.exe", "/k"] + tokens

        print("Final cmd to execute:", full_cmd)

        # 4) Execute
        try:
            subprocess.Popen(full_cmd, shell=False)
        except Exception as e:
            print(f"Error executing command: {full_cmd}, Error: {e}")
            self.info_label.setText(f"Error executing: {e}")

    def prompt_for_variable(self, placeholder_label: str = "value"):
        text, ok = QInputDialog.getText(
            self,
            "Input Required",
            f"Enter {placeholder_label}:",
            QLineEdit.Normal
        )
        if ok and text.strip():
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

            # Insert the new shortcut
            cursor.execute("""
                INSERT INTO shortcuts (name, command, description, requires_input, category_id)
                VALUES (?, ?, ?, ?, ?)
            """, (new_data["name"], new_data["command"], new_data["description"],
                new_data["requires_input"], category_id))
            shortcut_id = cursor.lastrowid

            # Insert tags and link them to the shortcut
            for tag in new_data["tags"]:
                cursor.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (tag,))
                cursor.execute("""
                    INSERT INTO shortcut_tags (shortcut_id, tag_id)
                    SELECT ?, id FROM tags WHERE name = ?
                """, (shortcut_id, tag))

            conn.commit()
            conn.close()

            # Refresh the GUI
            self.load_shortcuts()          # Reload shortcuts from the database
            self.update_category_sidebar() # Update categories in the sidebar
            self.filter_table()            # Refresh the table view

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

            # Update the shortcut
            cursor.execute("""
                UPDATE shortcuts
                SET name = ?, command = ?, description = ?, requires_input = ?, category_id = ?
                WHERE id = ?
            """, (updated_data["name"], updated_data["command"], updated_data["description"],
                updated_data["requires_input"], category_id, shortcut["id"]))

            # Update tags
            cursor.execute("DELETE FROM shortcut_tags WHERE shortcut_id = ?", (shortcut["id"],))
            for tag in updated_data["tags"]:
                cursor.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (tag,))
                cursor.execute("""
                    INSERT INTO shortcut_tags (shortcut_id, tag_id)
                    SELECT ?, id FROM tags WHERE name = ?
                """, (shortcut["id"], tag))

            conn.commit()
            conn.close()

            # Remove unused categories and refresh the GUI
            self.remove_unused_categories()
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

        # Requires Input? checkbox
        self.requires_input_checkbox = QCheckBox("Requires user input?")
        layout.addRow(QLabel("Input Needed:"), self.requires_input_checkbox)

        # Link script button if desired
        self.link_file_button = QPushButton("Link .exe, .bat, or .ps1")
        self.link_file_button.clicked.connect(self.on_link_file)
        layout.addRow(QLabel("Link Script:"), self.link_file_button)

        # If editing, populate fields
        if self.edit_mode and shortcut_data is not None:
            self.name_edit.setText(shortcut_data.get("name", ""))
            self.command_edit.setText(shortcut_data.get("command", ""))
            self.description_edit.setText(shortcut_data.get("description", ""))
            tag_list = shortcut_data.get("tags", [])
            self.tags_edit.setText(", ".join(tag_list))
            self.category_edit.setText(shortcut_data.get("category", ""))

            # Load the requires_input checkbox
            self.requires_input_checkbox.setChecked(shortcut_data.get("requires_input", False))

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

        requires_input = self.requires_input_checkbox.isChecked()

        self.result_data = {
            "name": name,
            "command": command,
            "description": description,
            "tags": tags_list,
            "category": category,
            "requires_input": requires_input
        }
        self.accept()

    def get_data(self):
        return self.result_data
def main():
    """
    Main entry point. Attempt to re-run as admin if not already.
    Then run the PyQt application.
    """
    # Attempt to relaunch as admin
    if relaunch_as_admin():
        # If relaunch_as_admin() returned True, we've triggered a new elevated process.
        # So this current (non-admin) process should exit.
        sys.exit(0)

    # Otherwise, continue as is (already admin or failed to elevate).
    app = QApplication(sys.argv)

    # Use a more modern built-in style
    app.setStyle(QStyleFactory.create("Fusion"))

    # A basic Fusion stylesheet
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


if __name__ == "__main__":
    main()
