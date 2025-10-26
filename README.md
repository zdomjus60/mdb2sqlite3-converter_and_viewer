# Access (MDB/ACCDB) to SQLite3 Converter and Viewer

This project provides a set of Python scripts to convert Microsoft Access Database files (.MDB and .ACCDB) to a SQLite3 database and a simple graphical viewer to browse the data, including images stored as OLE objects.

## Features

- **`access_to_sqlite.py`**: A command-line script that converts an entire MDB or ACCDB file to a SQLite3 database.
    - Preserves table schemas (column names, data types, nullability).
    - Handles data insertion.
    - Uses `UCanAccess` for robust conversion.
- **`viewer.py`**: A GUI application built with Tkinter that allows you to:
    - Browse tables from the generated SQLite database.
    - Navigate records one by one.
    - View text data.
    - View images stored in OLE object fields by extracting them on-the-fly from the original MDB file.
    - Uses `mdb-tools` for image extraction (due to UCanAccess limitations).
- **`compare_sqlite_dbs.py`**: A utility script to compare the schema and row counts of two SQLite databases, useful for validating conversions.

## Dependencies

- **Python 3**: All scripts are written in Python 3.
- **Pillow**: The viewer script requires the Pillow library for image processing.
  ```bash
  pip install Pillow
  ```
- **UCanAccess**: A Java-based JDBC driver used by `access_to_sqlite.py` for robust Access database parsing.
  - Download the latest binary distribution from [UCanAccess SourceForge](https://ucanaccess.sourceforge.net/site.html#download).
  - Extract the downloaded `.zip` file into a folder named `UCanAccess-5.0.1.bin` (or similar, matching the version) in the project's root directory.
- **mdb-tools**: Command-line utilities required by `viewer.py` for extracting images from MDB files.
  - On Debian/Ubuntu: `sudo apt-get install mdbtools`
  - On other systems, refer to `mdb-tools` documentation.
- **tkinter**: Usually included with Python, but might need to be installed separately on some Linux distributions.
  - On Debian/Ubuntu: `sudo apt-get install python3-tk`

## Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/zdomjus60/mdb2sqlite3-converter_and_viewer.git
    cd mdb2sqlite3-converter_and_viewer
    ```
2.  **Install Python dependencies:**
    ```bash
    pip install Pillow
    ```
3.  **Install `mdb-tools`:**
    ```bash
    sudo apt-get install mdbtools
    ```
4.  **Install `tkinter` (if needed):**
    ```bash
    sudo apt-get install python3-tk
    ```
5.  **Download and setup UCanAccess:**
    - Download the latest binary distribution from [UCanAccess SourceForge](https://ucanaccess.sourceforge.net/site.html#download).
    - Extract the downloaded `.zip` file into a folder named `UCanAccess-5.0.1.bin` (or similar, matching the version) in the project's root directory. Ensure the `console.sh` script inside this folder is executable (`chmod +x UCanAccess-5.0.1.bin/console.sh`).

## Usage

### 1. Convert your Access Database

Use the `access_to_sqlite.py` script to convert your `.mdb` or `.accdb` file.

```bash
./access_to_sqlite.py YourDatabase.mdb output.sqlite
# or for ACCDB files:
./access_to_sqlite.py YourDatabase.accdb output.sqlite
```

-   This will generate an `output.sqlite` file containing the converted data.
-   **Note on Limitations**: While this script is robust, complex Access databases (especially those with intricate queries, forms, or reports) might not convert perfectly. Some tables or data might be missing due to limitations of the underlying `UCanAccess` tool.

### 2. View the Converted Data and Images

Use the `viewer.py` script to browse the converted SQLite database and view images from the original Access file.

```bash
python3 viewer.py output.sqlite YourDatabase.mdb
```

-   The viewer requires both the converted SQLite file (for table listing) and the original MDB file (for data and image extraction).
-   **Note on Limitations**: Some complex queries from the original Access database might appear as tables in the viewer but may not display data, as `mdb-export` (used for image extraction) has limitations with certain query types.

### 3. Compare SQLite Databases (for Validation)

Use `compare_sqlite_dbs.py` to validate your conversions against a reference SQLite database.

```bash
./compare_sqlite_dbs.py reference.sqlite converted.sqlite
```

-   This script compares table names, column schemas (case-insensitively), and row counts.

## Troubleshooting

-   **`Exec format error` when running `./script.py`**: Ensure the script has execute permissions (`chmod +x script.py`) and is run with `python3 script.py` if a shebang is missing or incorrect.
-   **`UCanAccess console script not found`**: Ensure `UCanAccess` is downloaded, extracted, and the `UCANACCESS_DIR` variable in the script points to the correct location. Also, ensure `UCanAccess-5.0.1.bin/console.sh` is executable (`chmod +x`).
-   **`mdb-export: command not found`**: Ensure `mdb-tools` is installed and in your system's PATH.
-   **Viewer is empty or shows errors**: Check the console output for `mdb-export` errors. Ensure the original `.mdb` file is present and accessible.
-   **`TO_HEX` not found error in UCanAccess output**: This indicates `TO_HEX()` is not supported by your UCanAccess version. The current `viewer.py` uses `mdb-export` for images, so this error should no longer occur.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.