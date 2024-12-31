import sqlite3
import json
import os

# File paths
JSON_FILE = "shortcuts.json"  # Path to your JSON file
SQLITE_DB = "commander.db"    # Name of your SQLite database

# Connect to SQLite database (creates if not exists)
conn = sqlite3.connect(SQLITE_DB)
cursor = conn.cursor()

# Step 1: Create Tables
def create_tables():
    # Main shortcuts table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS shortcuts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            command TEXT NOT NULL,
            description TEXT,
            tags TEXT,
            type TEXT DEFAULT 'command',
            file_path TEXT,
            category_id INTEGER,
            requires_input BOOLEAN NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # Tags table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        );
    """)

    # Shortcut-Tags many-to-many table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS shortcut_tags (
            shortcut_id INTEGER NOT NULL,
            tag_id INTEGER NOT NULL,
            FOREIGN KEY (shortcut_id) REFERENCES shortcuts(id),
            FOREIGN KEY (tag_id) REFERENCES tags(id)
        );
    """)

    # Categories table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        );
    """)

    # Settings table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
    """)

    conn.commit()

# Step 2: Load JSON Data
def load_json():
    if not os.path.exists(JSON_FILE):
        print(f"Error: {JSON_FILE} not found.")
        return None
    with open(JSON_FILE, 'r') as f:
        return json.load(f)

# Step 3: Insert Data into SQLite
def migrate_data(data):
    # Migrate categories
    categories_map = {}
    for shortcut in data['shortcuts']:
        category_name = shortcut.get('category', None)
        if category_name and category_name not in categories_map:
            cursor.execute("INSERT OR IGNORE INTO categories (name) VALUES (?)", (category_name,))
            cursor.execute("SELECT id FROM categories WHERE name = ?", (category_name,))
            categories_map[category_name] = cursor.fetchone()[0]

    # Migrate shortcuts
    for shortcut in data['shortcuts']:
        category_id = categories_map.get(shortcut.get('category', None))
        print(f"Inserting shortcut: {shortcut['name']}")
        cursor.execute("""
            INSERT INTO shortcuts (name, command, description, tags, type, file_path, category_id, requires_input)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            shortcut['name'],
            shortcut['command'],
            shortcut.get('description', None),
            ', '.join(shortcut.get('tags', [])),
            shortcut.get('type', 'command'),
            shortcut.get('file_path', None),
            category_id,
            shortcut.get('requires_input', False)
        ))

    # Migrate tags and shortcut_tags
    for shortcut in data['shortcuts']:
        shortcut_id = cursor.lastrowid
        for tag_name in shortcut.get('tags', []):
            print(f"Inserting tag: {tag_name} for shortcut ID: {shortcut_id}")
            cursor.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (tag_name,))
            cursor.execute("SELECT id FROM tags WHERE name = ?", (tag_name,))
            tag_id = cursor.fetchone()[0]
            cursor.execute("INSERT INTO shortcut_tags (shortcut_id, tag_id) VALUES (?, ?)", (shortcut_id, tag_id))

    # Migrate settings
    for key, value in data.get('settings', {}).items():
        print(f"Inserting setting: {key} = {value}")
        cursor.execute("""
            INSERT OR REPLACE INTO settings (key, value)
            VALUES (?, ?)
        """, (key, value))

    conn.commit()

# Step 4: Verify Migration
def verify_migration():
    cursor.execute("SELECT COUNT(*) FROM shortcuts")
    shortcuts_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM settings")
    settings_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM tags")
    tags_count = cursor.fetchone()[0]

    print(f"Migration complete: {shortcuts_count} shortcuts, {tags_count} tags, and {settings_count} settings migrated.")

# Main Migration Process
if __name__ == "__main__":
    print("Starting migration...")
    create_tables()
    
    data = load_json()
    if data:
        migrate_data(data)
        verify_migration()
    else:
        print("No data to migrate.")

    conn.close()
