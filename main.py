import sys
import json
import os
import subprocess
import ctypes
import re

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
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
    QSplitter
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
        # Running in a PyInstaller bundle
        return os.path.dirname(sys.executable)
    else:
        # Running in normal Python
        return os.path.dirname(os.path.abspath(__file__))

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
        self.json_path = os.path.join(get_app_folder(), "shortcuts.json")
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

    ###########################################################################
    # SIDEBAR / CATEGORY
    ###########################################################################
    def update_category_list(self):
        """
        Gather unique category names from self.shortcuts_data.
        Store them in self.available_categories as a sorted list.
        """
        categories = set()
        for s in self.shortcuts_data:
            cat = s.get("category", "").strip()
            if cat:
                categories.add(cat)
        self.available_categories = sorted(categories)

    def update_category_sidebar(self):
        """
        Clear and repopulate the category_list QListWidget.
        Includes an '(All Categories)' item to reset filter.
        """
        self.category_list.clear()
        self.update_category_list()  # Make sure self.available_categories is up to date

        # Add an item to show all categories
        self.category_list.addItem("(All Categories)")

        # Add the individual categories
        for cat in self.available_categories:
            self.category_list.addItem(cat)

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
        Load JSON data or create default data if file not found/invalid.
        Sets self.current_theme from JSON if present.
        """
        if os.path.exists(self.json_path):
            try:
                with open(self.json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.shortcuts_data = data.get("shortcuts", [])
                self.settings_data = data.get("settings", {})
                self.current_theme = self.settings_data.get("theme", "light")

                if not self.shortcuts_data:
                    self.shortcuts_data = self.get_default_shortcuts()

            except json.JSONDecodeError:
                self.shortcuts_data = self.get_default_shortcuts()
                self.settings_data = {}
                self.current_theme = "light"
        else:
            self.shortcuts_data = self.get_default_shortcuts()
            self.settings_data = {}
            self.current_theme = "light"
            self.save_shortcuts()

        # Apply the loaded theme right away
        self.apply_theme(self.current_theme)

    def save_shortcuts(self):
        data_to_save = {
            "shortcuts": self.shortcuts_data,
            "settings": {
                "theme": self.current_theme
            }
        }
        with open(self.json_path, 'w', encoding='utf-8') as f:
            json.dump(data_to_save, f, indent=2)

    def get_default_shortcuts(self):
        return [
            {
                "name": "Ping Google",
                "command": "ping google.com",
                "description": "Pings Google to check network connectivity.",
                "tags": ["network", "ping"],
                "category": "Networking"
            },
            {
                "name": "IPConfig",
                "command": "ipconfig /all",
                "description": "Displays detailed network configuration.",
                "tags": ["network", "windows"],
                "category": "Networking"
            },
            {
                "name": "List Directory",
                "command": "dir",
                "description": "Lists files and directories in the current folder.",
                "tags": ["directory", "windows", "files"],
                "category": "File System"
            }
        ]

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
            return  # no selection

        row = selected_items[0].row()
        shortcut, original_index = self.displayed_pairs[row]

        command = shortcut.get("command", "").strip()
        requires_input = shortcut.get("requires_input", False)

        # If it has placeholders, handle them
        if requires_input:
            placeholders = re.findall(r"{(.*?)}", command)
            if placeholders:
                for ph in placeholders:
                    val = self.prompt_for_variable(ph)
                    if not val:
                        self.info_label.setText("Command cancelled or no input provided.")
                        return
                    command = command.replace(f"{{{ph}}}", val)

        # Determine if it's PowerShell, PS1, .exe, or default to cmd
        if command.lower().endswith(".exe"):
            # Just run it via subprocess
            full_cmd = [command]
        elif command.lower().startswith("powershell") or command.lower().endswith(".ps1"):
            full_cmd = ["powershell.exe", "-NoExit", "-Command", command]
        else:
            full_cmd = ["cmd.exe", "/k", command]

        try:
            subprocess.Popen(full_cmd, shell=True)
        except Exception as e:
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
        dialog = ShortcutDialog(self)  # no shortcut_data => new mode
        if dialog.exec_() == QDialog.Accepted:
            new_data = dialog.get_data()
            self.shortcuts_data.append(new_data)
            self.save_shortcuts()
            # Re-filter or show all
            current_filter = self.search_bar.text().strip()
            if current_filter:
                self.filter_table()
            else:
                pairs = [(s, i) for i, s in enumerate(self.shortcuts_data)]
                self.populate_table(pairs)
            self.info_label.setText(f"Added new shortcut: {new_data['name']}")

            # Also update the sidebar (maybe new category was added)
            self.update_category_sidebar()

    def on_edit_shortcut(self):
        selected_items = self.table.selectedItems()
        if not selected_items:
            return

        table_row = selected_items[0].row()
        if table_row < 0 or table_row >= len(self.displayed_pairs):
            return  # safety check

        shortcut, original_index = self.displayed_pairs[table_row]
        original_data = self.shortcuts_data[original_index]

        dialog = ShortcutDialog(self, shortcut_data=original_data)
        if dialog.exec_() == QDialog.Accepted:
            updated_data = dialog.get_data()
            self.shortcuts_data[original_index] = updated_data
            self.save_shortcuts()

            # Re-filter or re-show all
            current_filter = self.search_bar.text().strip()
            if current_filter:
                self.filter_table()
            else:
                pairs = [(s, i) for i, s in enumerate(self.shortcuts_data)]
                self.populate_table(pairs)

            # Also update sidebar if the category changed
            self.update_category_sidebar()

    def on_delete_shortcut(self):
        selected_items = self.table.selectedItems()
        if not selected_items:
            return

        row = selected_items[0].row()
        shortcut, original_index = self.displayed_pairs[row]
        shortcut_name = shortcut.get("name", "")

        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete '{shortcut_name}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.shortcuts_data.pop(original_index)
            self.save_shortcuts()

            current_filter = self.search_bar.text().strip()
            if current_filter:
                self.filter_table()
            else:
                pairs = [(s, i) for i, s in enumerate(self.shortcuts_data)]
                self.populate_table(pairs)

            # Also refresh sidebar in case we removed the last item of a category
            self.update_category_sidebar()

            self.info_label.setText(f"Deleted shortcut: {shortcut_name}")
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
