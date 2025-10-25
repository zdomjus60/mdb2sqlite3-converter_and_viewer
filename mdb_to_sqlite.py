#!/usr/bin/env python3
import subprocess
import sqlite3
import sys
import os

def get_mdb_tables(mdb_file):
    """Returns a list of table names from an MDB file."""
    try:
        tables_raw = subprocess.check_output(['mdb-tables', '-1', mdb_file]).decode('utf-8')
        return [table for table in tables_raw.split('\n') if table]
    except subprocess.CalledProcessError as e:
        print(f"Error getting tables from {mdb_file}: {e}")
        return []
    except FileNotFoundError:
        print("Error: 'mdb-tools' not found. Please ensure it is installed and in your PATH.")
        sys.exit(1)

def convert_mdb_to_sqlite(mdb_file, sqlite_file):
    """
    Converts an MDB database to an SQLite database by generating direct INSERT statements.
    """
    if not os.path.exists(mdb_file):
        print(f"Error: MDB file not found at '{mdb_file}'")
        return

    if os.path.exists(sqlite_file):
        os.remove(sqlite_file)

    print(f"Connecting to new SQLite database: {sqlite_file}")
    conn = sqlite3.connect(sqlite_file)
    cursor = conn.cursor()

    tables = get_mdb_tables(mdb_file)
    if not tables:
        print("No tables found in the MDB file. Exiting.")
        conn.close()
        return

    print(f"Found tables: {', '.join(tables)}")

    total_rows_imported = 0

    for table in tables:
        print(f"\n--- Processing table: {table} ---")
        try:
            # 1. Get schema and create table in SQLite
            print("  - Exporting schema for SQLite...")
            schema_sql = subprocess.check_output(['mdb-schema', mdb_file, '-T', table, 'sqlite']).decode('utf-8')
            
            print(f"  - Creating table '{table}' in SQLite...")
            cursor.executescript(schema_sql)
            conn.commit()

            # 2. Export data as INSERT statements and execute them
            print("  - Exporting data as INSERT statements...")
            # -I sqlite: Generate INSERT statements for SQLite.
            # -b strip: Ignore binary data fields, which cause errors.
            export_command = ['mdb-export', '-I', 'sqlite', '-D', '%Y-%m-%d %H:%M:%S', '-b', 'strip', mdb_file, table]
            insert_sql_bytes = subprocess.check_output(export_command)
            insert_sql = insert_sql_bytes.decode('utf-8', errors='replace')

            print(f"  - Importing rows into '{table}'...")
            # Execute the entire batch of INSERT statements
            cursor.executescript(insert_sql)
            conn.commit()
            
            # Count the rows that were just inserted
            count_cursor = conn.cursor()
            count_cursor.execute(f'SELECT COUNT(*) FROM "{table}"')
            rows_imported = count_cursor.fetchone()[0]
            total_rows_imported += rows_imported
            print(f"  - Successfully imported {rows_imported} rows.")

        except subprocess.CalledProcessError as e:
            print(f"  - ERROR processing table '{table}': {e}")
            if e.stdout:
                print(f"  - STDOUT: {e.stdout.decode('utf-8', 'ignore')}")
            if e.stderr:
                print(f"  - STDERR: {e.stderr.decode('utf-8', 'ignore')}")
        except Exception as e:
            print(f"  - An unexpected error occurred while processing table '{table}': {e}")

    print(f"\nConversion complete. Total rows imported across all tables: {total_rows_imported}")
    conn.close()

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: ./mdb_to_sqlite.py <path_to_mdb_file> <path_to_sqlite_file>")
        sys.exit(1)

    mdb_path = sys.argv[1]
    sqlite_path = sys.argv[2]
    
    convert_mdb_to_sqlite(mdb_path, sqlite_path)
