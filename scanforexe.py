import os
import csv
import sys

def find_files(drive_letter: str, extensions: list):
    """
    Given a single-letter drive identifier (e.g. 'C'),
    recursively search the drive for files whose extensions
    match any in 'extensions' (list of strings),
    and return a list of (filename, fullpath) tuples.
    """
    # Construct the drive path, e.g. "C:\\"
    drive_path = f"{drive_letter}:\\"
    
    found_files = []

    # Recursively walk through the drive
    for root, dirs, files in os.walk(drive_path):
        for file in files:
            # Check if file ends with any of the given extensions
            # (case-insensitive)
            lower_file = file.lower()
            if any(lower_file.endswith(ext) for ext in extensions):
                full_path = os.path.join(root, file)
                found_files.append((file, full_path))
    
    return found_files

def output_as_csv(files_list):
    """
    Output the file list as CSV to stdout.
    Columns: FileName, FullPath
    """
    writer = csv.writer(sys.stdout, lineterminator='\n')
    
    # Write header
    writer.writerow(["FileName", "FullPath"])
    
    # Write rows
    for filename, full_path in files_list:
        writer.writerow([filename, full_path])

def main():
    # Ask for drive letter input
    drive_letter = input("Enter the drive letter (e.g. C): ").strip().upper()

    # Validate input is a single character
    if len(drive_letter) != 1 or not drive_letter.isalpha():
        print("Please enter a valid single-letter drive (e.g. C).")
        return

    # Define the file extensions we want to search for
    wanted_extensions = [".exe", ".ps1", ".bat"]

    # Find all files with the wanted extensions
    files_list = find_files(drive_letter, wanted_extensions)

    # Output results in CSV format
    output_as_csv(files_list)

if __name__ == "__main__":
    main()
