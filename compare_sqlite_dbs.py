#!/usr/bin/env python3
import sqlite3
import sys
from collections import namedtuple

# A simple structure to hold schema info for a column
ColumnInfo = namedtuple('ColumnInfo', ['name', 'type', 'notnull', 'default_value', 'pk'])

def get_db_schema(cursor):
    """Returns a dictionary describing the database schema."""
    schema = {}
    tables = cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';").fetchall()
    for (table_name,) in tables:
        columns_raw = cursor.execute(f'PRAGMA table_info("{table_name}");').fetchall()
        columns = {}
        for col in columns_raw:
            # col is a tuple: (cid, name, type, notnull, dflt_value, pk)
            info = ColumnInfo(name=col[1], type=col[2], notnull=col[3], default_value=col[4], pk=col[5])
            columns[info.name] = info
        schema[table_name] = columns
    return schema

def get_row_counts(cursor):
    """Returns a dictionary with table names and their row counts."""
    counts = {}
    tables = cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';").fetchall()
    for (table_name,) in tables:
        count = cursor.execute(f'SELECT COUNT(*) FROM "{table_name}";').fetchone()[0]
        counts[table_name] = count
    return counts

def compare_databases(db1_path, db2_path):
    """
    Compares the schema and row counts of two SQLite databases.
    db1 is considered the 'reference' database.
    db2 is the 'candidate' database to be checked against the reference.
    This comparison is case-insensitive for table and column names.
    """
    print(f"--- Comparing Databases ---")
    print(f"Reference (DB1): {db1_path}")
    print(f"Candidate (DB2): {db2_path}\n")

    conn1 = sqlite3.connect(db1_path)
    cursor1 = conn1.cursor()
    conn2 = sqlite3.connect(db2_path)
    cursor2 = conn2.cursor()

    schema1 = get_db_schema(cursor1)
    schema2 = get_db_schema(cursor2)

    errors_found = 0

    # --- Case-insensitive mapping ---
    map1 = {name.lower(): name for name in schema1.keys()}
    map2 = {name.lower(): name for name in schema2.keys()}

    tables1_lower = set(map1.keys())
    tables2_lower = set(map2.keys())

    # 1. Compare table lists (case-insensitively)
    print("--- 1. Comparing Tables (case-insensitive) ---")
    missing_in_db2 = tables1_lower - tables2_lower
    added_in_db2 = tables2_lower - tables1_lower

    if not missing_in_db2 and not added_in_db2:
        print("OK: Both databases have the same set of tables.")
    else:
        if missing_in_db2:
            print(f"ERROR: The candidate database is missing tables: {sorted(list(missing_in_db2))}")
            errors_found += 1
        if added_in_db2:
            # This is a warning because the converter might be exporting system views etc.
            print(f"WARNING: The candidate database has extra tables/views: {sorted(list(added_in_db2))}")
    
    common_tables_lower = sorted(list(tables1_lower & tables2_lower))
    print(f"\nFound {len(common_tables_lower)} common tables to compare further.")

    # 2. Compare schemas of common tables (case-insensitively)
    print("\n--- 2. Comparing Column Schemas (for common tables) ---")
    for lower_table in common_tables_lower:
        orig_name1 = map1[lower_table]
        orig_name2 = map2[lower_table]
        
        cols1 = schema1[orig_name1]
        cols2 = schema2[orig_name2]

        col_map1 = {name.lower(): name for name in cols1.keys()}
        col_map2 = {name.lower(): name for name in cols2.keys()}

        col_names1_lower = set(col_map1.keys())
        col_names2_lower = set(col_map2.keys())

        missing_cols = col_names1_lower - col_names2_lower
        added_cols = col_names2_lower - col_names1_lower

        if not missing_cols and not added_cols:
            # Check types and constraints for matching columns
            schema_mismatch = False
            for lower_col in col_names1_lower:
                orig_col1 = col_map1[lower_col]
                orig_col2 = col_map2[lower_col]
                
                # Compare schema but ignore case for data types (e.g., DATETIME vs DateTime)
                s1 = cols1[orig_col1]
                s2 = cols2[orig_col2]
                
                # Simple comparison, making type check case-insensitive
                if s1.name.lower() != s2.name.lower() or \
                   str(s1.type).lower() != str(s2.type).lower() or \
                   s1.notnull != s2.notnull or \
                   s1.pk != s2.pk:
                    print(f"ERROR [{orig_name2}]: Column '{orig_col2}' has a schema mismatch.")
                    print(f"  - Reference: {s1}")
                    print(f"  - Candidate: {s2}")
                    schema_mismatch = True
                    errors_found += 1
            if not schema_mismatch:
                print(f"OK: Schema for table '{orig_name2}' matches.")
        else:
            if missing_cols:
                print(f"ERROR [{orig_name2}]: Candidate is missing columns: {sorted(list(missing_cols))}")
                errors_found += 1
            if added_cols:
                print(f"WARNING [{orig_name2}]: Candidate has extra columns: {sorted(list(added_cols))}")

    # 3. Compare row counts of common tables
    print("\n--- 3. Comparing Row Counts (for common tables) ---")
    counts1 = get_row_counts(cursor1)
    counts2 = get_row_counts(cursor2)

    for lower_table in common_tables_lower:
        orig_name1 = map1[lower_table]
        orig_name2 = map2[lower_table]

        if counts1.get(orig_name1) == counts2.get(orig_name2):
            print(f"OK: Row count for table '{orig_name2}' matches ({counts2[orig_name2]}).")
        else:
            print(f"ERROR [{orig_name2}]: Row count mismatch.")
            print(f"  - Reference: {counts1.get(orig_name1)}")
            print(f"  - Candidate: {counts2.get(orig_name2)}")
            errors_found += 1

    conn1.close()
    conn2.close()

    print("\n--- Summary ---")
    if errors_found == 0:
        print("SUCCESS: The databases appear to be equivalent!")
    else:
        print(f"FAILURE: Found {errors_found} significant difference(s).")

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: ./compare_sqlite_dbs.py <reference_db_path> <candidate_db_path>")
        sys.exit(1)

    db1 = sys.argv[1]
    db2 = sys.argv[2]
    compare_databases(db1, db2)
