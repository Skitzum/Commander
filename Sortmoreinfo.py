import json

def remove_entries_with_phrase(file_path, phrase):
    try:
        # Load the JSON file
        with open(file_path, 'r') as file:
            data = json.load(file)
        
        # Remove entries containing the specified phrase
        filtered_data = [entry for entry in data if phrase not in json.dumps(entry, ensure_ascii=False)]
        
        # Save the filtered data back to the JSON file
        with open(file_path, 'w') as file:
            json.dump(filtered_data, file, indent=4)
        
        print(f"Entries containing '{phrase}' have been removed. The updated JSON file has been saved.")
    except Exception as e:
        print(f"An error occurred: {e}")

# Replace 'Tools USB.json' with the actual path to your JSON file
remove_entries_with_phrase('Tools USB.json', "More info needed")
