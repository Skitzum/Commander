
Commander is a **Python + PyQt** application that manages a collection of handy shortcuts—each shortcut can be:

- A simple **CMD** command (e.g., `ping google.com`)
- A **PowerShell** command or script (e.g., `.ps1` files)
- An **.exe** or **.bat** program
- Commands with **placeholders** (like `{host}`) that prompt the user at runtime

It provides:

- A **table** with name, command, tags, and category.
- **Light/Dark** theme toggle switch.
- **Search** bar for filtering by text in name/command/tags/category.
- A **category sidebar** for advanced filtering.
- **Two-step execution** (Execute → Confirm) to avoid accidental runs.
- Add/Edit/Delete for new shortcuts (persisted in a JSON file).
- Support for **multiline PowerShell** scripts via external `.ps1` or an embedded approach.

---

## Features

1. **Searchable Table**
    
    - Real-time filter by name, command, tags, or category.
    - Category sidebar to quickly navigate or show `(All Categories)`.
2. **Light/Dark Mode**
    
    - A toggle switch in the search bar area.
    - Setting saved to JSON so it’s remembered next time.
3. **Two-Step Confirmation**
    
    - Prevents accidental command execution by requiring “Execute” → “Confirm.”
4. **Add/Edit/Delete Shortcuts**
    
    - Add new shortcuts with a **ShortcutDialog** (input name, command, description, tags, category, etc.).
    - Option to mark “Requires user input?” for placeholder substitution.
    - Link `.exe`, `.bat`, `.ps1`, or embed multiline code.
5. **Placeholder Logic**
    
    - If `requires_input` is set, Commander scans the command for tokens like `{host}`.
    - Prompts the user for each placeholder at runtime.
    - Substitutes them before execution.
6. **Automatic Shell Detection**
    
    - If the command ends with `.exe`, Commander runs it directly.
    - If `.ps1`, it uses PowerShell.
    - Otherwise, defaults to `cmd /k`.
7. **Easy Portability**
    
    - All data stored in `shortcuts.json` in the same folder.
    - Just drop the folder on a flash drive—Commander references relative paths if you choose.

---

## Installation & Requirements

1. **Python 3.7+** (recommended)
2. **PyQt5** (For the GUI).
3. **Windows** environment for best results (Currently all commands are Windows specific).

Install dependencies:

bash

Copy code

`pip install pyqt5`

---

## Running Commander

1. **Clone** or **copy** the Commander files (including `main.py`, `shortcuts.json`, etc.) to a folder.
2. **Open** a terminal or command prompt in that folder.
3. **Launch**:
    
    bash
    
    Copy code
    
=======
    
4. The Commander window appears. You’ll see:
    - A **search bar** (with a theme toggle switch).
    - A **category sidebar** (left).
    - A **table** listing your shortcuts (right).
    - Bottom buttons for adding/editing/deleting.
    - An “Execute” button.

---

## Adding a Shortcut

1. **Click** “Add Shortcut.”
2. Fill in:
    - **Name**: A label (e.g., “Ping Google”).
    - **Command**: The command or path (e.g., “ping google.com” or `E:\HwInfo\HwInfo64.exe`).
    - **Description**: Optional brief text.
    - **Tags**: Comma-separated tags (e.g., `network, ping`).
    - **Category**: For grouping (e.g., `Networking`).
    - **Requires user input?**: If you have placeholders like `{host}` in Command, check this box.
3. **Press OK**. The new shortcut is saved to JSON and appears in the table.

---

## Editing or Deleting a Shortcut

1. **Select** the row in the table.
2. **Edit Shortcut** or **Delete Shortcut**:
    - **Edit** opens the same dialog, pre-filled. Change fields, then OK.
    - **Delete** asks “Are you sure?”
3. Changes are saved automatically to `shortcuts.json`.

---

## Running a Shortcut

1. **Select** the row you want.
2. Click **Execute**.
3. Button changes to **Confirm**. Click again → the command runs.
4. If it’s a `.exe`, it launches. If `.ps1`, it uses PowerShell. Otherwise, default to `cmd /k`.
5. If the command has placeholders like `{host}`, you’ll be prompted for each placeholder first.

---

## Handling Multiline PowerShell

**Recommended**: Put your multiline script in a `.ps1` file. Then your “Command” might be:

arduino

Copy code

`powershell.exe -NoExit -File "E:\Commander\Scripts\FindRecentFiles.ps1"`

_(Or you can embed multiline code directly in the Command field and write it to a temp file on-the-fly, but that requires more code changes. See the documentation for details.)_

---

## Building an Executable (Optional)

If you want a **single-file `.exe`**:

1. Install [**PyInstaller**](https://www.pyinstaller.org/):
    
    bash
    
    Copy code
    
    `pip install pyinstaller`
    
2. In your folder, run:
    
    bash
    
    Copy code
    
    `pyinstaller --onefile main.py`
    
3. It creates `dist/main.exe`. Put `shortcuts.json` (and any `.ps1` scripts you need) **beside** that `.exe`.

---

## Troubleshooting

- **Placeholder logic** not working? Make sure you don’t **overwrite** the local `command` variable after replacements, or skip the `requires_input` check.
- **Not picking up `.exe`**? Double-check your extension logic or see if the path is spelled correctly.
- **No shortcuts** appear? Possibly your `shortcuts.json` is empty or in a different folder. Add debug prints or check the console for file paths.

---

## Contributing

Feel free to open a PR or share improvements:

- More advanced search or category logic.
- Additional shells (e.g. WSL?).
- Integration with external tools or an embedded console approach.
- Much more robust handling for .exe creation with better instructions
- Groups that can run multiple commands at a time
- Need more ideas for great commands to add to default JSON
- Resizing columns correctly so long commands don't take up the whole window

---

## License

Commander is licensed under the MIT License. You can freely modify and distribute it.
