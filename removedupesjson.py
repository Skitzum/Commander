import json

def remove_duplicates(file_path):
    try:
        # Load the JSON file
        with open(file_path, 'r') as file:
            data = json.load(file)
        
        # Remove duplicate entries
        seen_entries = set()
        unique_data = []
        for entry in data:
            # Convert the entry to a JSON string to ensure uniqueness
            entry_str = json.dumps(entry, sort_keys=True)
            if entry_str not in seen_entries:
                seen_entries.add(entry_str)
                unique_data.append(entry)
        
        # Save the unique data back to the JSON file
        with open(file_path, 'w') as file:
            json.dump(unique_data, file, indent=4)
        
        print("Duplicate entries have been removed. The updated JSON file has been saved.")
    except Exception as e:
        print(f"An error occurred: {e}")

# Replace 'Tools USB.json' with the actual path to your JSON file
remove_duplicates('Tools USB.json')
