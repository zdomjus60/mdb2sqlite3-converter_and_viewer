#!/usr/bin/env python3
import subprocess
import sqlite3
import sys
import os
import tempfile
import csv
import re

# --- CONFIGURATION ---
UCANACCESS_DIR = os.path.abspath("UCanAccess-5.0.1.bin")

def run_ucanaccess_command(db_file, command):
    """Runs a command in the UCanAccess console and returns the output."""
    console_script = os.path.join(UCANACCESS_DIR, 'console.sh')
    if not os.path.exists(console_script):
        print(f"Error: UCanAccess console script not found at {console_script}")
        sys.exit(1)

    full_command = f"{db_file}\n{command}\nquit;\n"
    try:
        proc = subprocess.run(
            ['sh', console_script],
            input=full_command, capture_output=True, text=True, encoding='utf-8', errors='replace'
        )
        if proc.returncode != 0:
            print(f"Error running UCanAccess command. STDERR: {proc.stderr}")
        return proc.stdout
    except Exception as e:
        print(f"An unexpected error occurred while running UCanAccess: {e}")
        return ""

def get_access_tables(db_file):
    """Returns a list of table names from an Access file."""
    print("  - Getting table list from Access file...")
    sql_command = "SELECT TABLE_NAME FROM information_schema.tables WHERE TABLE_SCHEMA='PUBLIC';"
    output = run_ucanaccess_command(db_file, sql_command)
    tables = re.findall(r'\|\s*([^|\s]+)\s*\|', output)
    # The regex might pick up the header, so we filter it out.
    return [t for t in tables if t != 'TABLE_NAME']

def get_table_schema_from_access(db_file, table_name):
    """Gets column definitions for a table from Access."""
    print(f"  - Getting schema for table '{table_name}'...")
    sql = f"SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE FROM information_schema.columns WHERE TABLE_NAME = '{table_name.upper()}' ORDER BY ORDINAL_POSITION;"
    output = run_ucanaccess_command(db_file, sql)
    
    # Regex to find the column data from the messy output
    # Looks for | COL_NAME | TYPE | NULLABLE |
    columns_raw = re.findall(r'\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|', output)

    if not columns_raw:
        print(f"  - WARNING: Could not retrieve schema for table '{table_name}'. It may be a view or query.")
        return None

    # Filter out headers
    columns_raw = [c for c in columns_raw if c[0].strip() != 'COLUMN_NAME']

    # Map Access data types to SQLite data types
    def map_type(access_type):
        access_type = access_type.upper()
        if any(t in access_type for t in ['CHAR', 'TEXT', 'MEMO', 'STRING']):
            return 'TEXT'
        if any(t in access_type for t in ['INT', 'LONG', 'BYTE', 'COUNTER']):
            return 'INTEGER'
        if any(t in access_type for t in ['DOUBLE', 'FLOAT', 'SINGLE']):
            return 'REAL'
        if 'DATETIME' in access_type:
            return 'DATETIME'
        if 'CURRENCY' in access_type:
            return 'NUMERIC'
        if 'BIT' in access_type:
            return 'INTEGER' # Boolean
        if 'OLE' in access_type or 'BINARY' in access_type:
            return 'BLOB'
        return 'TEXT' # Default fallback

    column_defs = []
    for name, dtype, nullable in columns_raw:
        name = name.strip()
        sqlite_type = map_type(dtype.strip())
        is_nullable = nullable.strip().upper()
        col_def = f'"{name}" {sqlite_type}'
        if is_nullable == 'NO':
            col_def += ' NOT NULL'
        column_defs.append(col_def)

    return column_defs

def convert_access_to_sqlite(access_file, sqlite_file):
    if not os.path.exists(access_file):
        print(f"Error: Access file not found at '{access_file}'")
        return

    if os.path.exists(sqlite_file):
        os.remove(sqlite_file)

    print(f"Connecting to new SQLite database: {sqlite_file}")
    conn = sqlite3.connect(sqlite_file)
    cursor = conn.cursor()

    tables = get_access_tables(access_file)
    if not tables:
        print("No tables found in the Access file. Exiting.")
        conn.close()
        return

    print(f"Found {len(tables)} tables/views. Attempting to convert...")

    with tempfile.TemporaryDirectory() as temp_dir:
        total_rows_imported = 0
        for table in tables:
            print(f"\n--- Processing: {table} ---")
            
            # 1. Get schema and create table in SQLite
            column_defs = get_table_schema_from_access(access_file, table)
            if not column_defs:
                print(f"  - Skipping '{table}' (could not determine schema, likely a view).")
                continue

            create_table_sql = f'CREATE TABLE "{table}" ({ ", ".join(column_defs) })'
            try:
                print(f"  - Creating table '{table}' in SQLite...")
                cursor.execute(create_table_sql)
            except sqlite3.OperationalError as e:
                print(f"  - ERROR creating table '{table}': {e}")
                continue

            # 2. Export data to CSV
            csv_file_path = os.path.join(temp_dir, f"{table}.csv")
            print(f"  - Exporting data to CSV...")
            export_command = f'export -t "{table}" "{csv_file_path}";'
            run_ucanaccess_command(access_file, export_command)

            if not os.path.exists(csv_file_path) or os.path.getsize(csv_file_path) == 0:
                print(f"  - WARNING: CSV file was not created or is empty for table '{table}'.")
                continue

            # 3. Import data from CSV
            try:
                with open(csv_file_path, 'r', encoding='utf-8', errors='replace') as f:
                    reader = csv.reader(f, delimiter=';')
                    header = next(reader) # Get header to match with schema
                    
                    placeholders = ', '.join(['?' for _ in header])
                    insert_sql = f'INSERT INTO "{table}" VALUES ({placeholders})'
                    
                    rows_in_table = 0
                    for row in reader:
                        if len(row) != len(header):
                            print(f"    - WARNING: Skipping row with incorrect column count: {row}")
                            continue
                        
                        # Handle empty strings for non-TEXT columns by turning them to NULL
                        processed_row = []
                        for i, value in enumerate(row):
                            col_name_in_header = header[i]
                            # Find corresponding column definition
                            col_def_str = next((s for s in column_defs if s.strip().startswith(f'"{col_name_in_header}"')), "")
                            
                            if value == '' and 'TEXT' not in col_def_str.upper() and 'DATETIME' not in col_def_str.upper():
                                processed_row.append(None)
                            else:
                                processed_row.append(value)
                        
                        try:
                            cursor.execute(insert_sql, processed_row)
                            rows_in_table += 1
                        except sqlite3.InterfaceError as e:
                            print(f"    - ERROR on row: {processed_row}")
                            print(f"    - {e}")

                    conn.commit()
                    total_rows_imported += rows_in_table
                    print(f"  - Successfully imported {rows_in_table} rows.")

            except Exception as e:
                print(f"  - An unexpected error occurred while importing table '{table}' from CSV: {e}")

    print(f"\nConversion complete. Total rows imported across all tables: {total_rows_imported}")
    conn.close()

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: ./access_to_sqlite.py <path_to_mdb_or_accdb_file> <path_to_sqlite_file>")
        sys.exit(1)

    console_script_path = os.path.join(UCANACCESS_DIR, 'console.sh')
    if os.path.exists(console_script_path):
        os.chmod(console_script_path, 0o755)

    access_path = sys.argv[1]
    sqlite_path = sys.argv[2]
    
    convert_access_to_sqlite(access_path, sqlite_path)
