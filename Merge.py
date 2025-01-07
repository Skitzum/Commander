import json
import sqlite3

# Paths
json_file_path = "Tools USB.json"
db_file_path = "commander.db"

# Load JSON data
with open(json_file_path, "r") as file:
    json_data = json.load(file)

# Connect to SQLite database
conn = sqlite3.connect(db_file_path)
cursor = conn.cursor()

# Ensure "Uncategorized" category exists
default_category = "Uncategorized"
cursor.execute("INSERT OR IGNORE INTO categories (name) VALUES (?)", (default_category,))
cursor.execute("SELECT id FROM categories WHERE name = ?", (default_category,))
uncategorized_id = cursor.fetchone()[0]

# Process JSON data
for tool in json_data:
    # Handle missing category
    category = tool.get("category", default_category)
    cursor.execute("INSERT OR IGNORE INTO categories (name) VALUES (?)", (category,))
    cursor.execute("SELECT id FROM categories WHERE name = ?", (category,))
    category_id = cursor.fetchone()[0]

    # Insert shortcut and skip if conflict
    name = tool.get("name", "Unnamed Tool")
    command = tool.get("path", "")
    description = tool.get("description", "")
    cursor.execute("""
        INSERT OR IGNORE INTO shortcuts (name, command, description, category_id)
        VALUES (?, ?, ?, ?)
    """, (name, command, description, category_id))

# Commit changes
conn.commit()
conn.close()

print("JSON data merged into the database, skipping conflicts.")
