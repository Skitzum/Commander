import json

def find_entries_with_phrase(file_path, phrase):
    try:
        # Load the JSON file
        with open(file_path, 'r') as file:
            data = json.load(file)
        
        # Find entries containing the specified phrase
        matching_entries = [entry for entry in data if phrase in json.dumps(entry, ensure_ascii=False)]
        
        # Print matching entries
        if matching_entries:
            print(f"Entries containing '{phrase}':")
            for entry in matching_entries:
                print(json.dumps(entry, indent=4))
        else:
            print(f"No entries found containing the phrase '{phrase}'.")
    except Exception as e:
        print(f"An error occurred: {e}")

# Replace 'Tools USB.json' with the actual path to your JSON file
find_entries_with_phrase('Tools USB.json', "More info needed")
