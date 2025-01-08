import sqlite3

def merge_databases(old_db_path, new_db_path):
    # Connect to both databases
    old_conn = sqlite3.connect(old_db_path)
    new_conn = sqlite3.connect(new_db_path)

    old_cursor = old_conn.cursor()
    new_cursor = new_conn.cursor()

    merged_data = {}

    # Step 1: Fetch table names from both databases
    old_cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    old_tables = {table[0] for table in old_cursor.fetchall()}

    new_cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    new_tables = {table[0] for table in new_cursor.fetchall()}

    # Step 2: Iterate through tables in the old database
    for table in old_tables:
        if table in new_tables:
            # Fetch column names from both tables
            old_cursor.execute(f"PRAGMA table_info({table});")
            old_columns = [col[1] for col in old_cursor.fetchall()]

            new_cursor.execute(f"PRAGMA table_info({table});")
            new_columns = [col[1] for col in new_cursor.fetchall()]

            # Determine common columns
            common_columns = list(set(old_columns) & set(new_columns))
            common_columns_str = ", ".join(common_columns)

            # Fetch data from the old database
            old_cursor.execute(f"SELECT {common_columns_str} FROM {table};")
            old_data = old_cursor.fetchall()

            # Insert data into the new database
            placeholders = ", ".join("?" for _ in common_columns)
            insert_query = f"INSERT OR IGNORE INTO {table} ({common_columns_str}) VALUES ({placeholders})"
            new_cursor.executemany(insert_query, old_data)

            merged_data[table] = len(old_data)  # Track number of rows merged

    # Commit changes and close connections
    new_conn.commit()
    old_conn.close()
    new_conn.close()

    return merged_data

# Paths to the old and new databases
old_db_path = "F:\___Commander\ccommander.db"  # Replace with the actual path to your old database
new_db_path = "F:\___Commander\commander.db"  # Replace with the actual path to your new database

# Merge the databases
merged_data_summary = merge_databases(old_db_path, new_db_path)

# Print the summary of merged data
print("Data merge completed. Summary:")
for table, rows in merged_data_summary.items():
    print(f"Table '{table}': {rows} rows merged.")
