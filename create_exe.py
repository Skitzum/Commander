import os
import subprocess

def create_exe(main_script, database_file, output_dir="dist"):
    """
    Creates a standalone executable for the given Python script and database file using PyInstaller.

    :param main_script: Path to the main Python script (e.g., main.py).
    :param database_file: Path to the SQLite database file (e.g., commander.db).
    :param output_dir: Directory where the executable will be placed.
    """
    if not os.path.exists(main_script):
        print(f"Error: {main_script} does not exist.")
        return

    if not os.path.exists(database_file):
        print(f"Error: {database_file} does not exist.")
        return

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Prepare the PyInstaller command
    pyinstaller_command = [
        "pyinstaller",
        "--onefile",
        f"--add-data={database_file};.",  # Include database file
        "--name=CommanderApp",  # Name of the executable
        f"--distpath={output_dir}",  # Output directory
        main_script
    ]

    # Run PyInstaller command
    try:
        print("Building the executable...")
        subprocess.run(pyinstaller_command, check=True)
        print(f"Executable created successfully in {output_dir}.")
    except subprocess.CalledProcessError as e:
        print(f"Error during build process: {e}")

if __name__ == "__main__":
    # Paths to the main script and database
    main_script_path = "main.py"
    database_file_path = "commander.db"

    # Call the function to create the executable
    create_exe(main_script_path, database_file_path)
