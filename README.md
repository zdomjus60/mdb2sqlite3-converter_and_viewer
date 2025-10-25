# MDB to SQLite3 Converter and Viewer

This project provides a set of Python scripts to convert a Microsoft Access Database (.MDB) file to a SQLite3 database and a simple graphical viewer to browse the data, including images stored as OLE objects.

## Features

- **`mdb_to_sqlite.py`**: A command-line script that converts an entire MDB file to a SQLite3 database. It handles table schemas and data insertion.
- **`viewer.py`**: A GUI application built with Tkinter that allows you to:
    - Browse tables from the generated SQLite database.
    - Navigate records one by one.
    - View text data.
    - View images stored in OLE object fields by extracting them on-the-fly from the original MDB file.

## Dependencies

- **mdb-tools**: This project relies on the `mdb-tools` command-line utilities. You must have them installed on your system.
  - On Debian/Ubuntu: `sudo apt-get install mdb-tools`
- **Python 3**: The scripts are written in Python 3.
- **Pillow**: The viewer script requires the Pillow library for image processing. It can be installed via pip:
  ```bash
  pip install Pillow
  ```

## Usage

### 1. Convert the Database

Place your `.MDB` file (e.g., `Northwind.MDB`) in the project directory. Run the conversion script from your terminal:

```bash
python3 mdb_to_sqlite.py YourDatabase.MDB output.sqlite3
```
This will generate a `output.sqlite3` file containing the converted data.

### 2. View the Data

Once the `.sqlite3` file has been created, you can run the graphical viewer:

```bash
python3 viewer.py
```
The viewer will open. Select a table from the dropdown menu to start browsing the records and associated images. The viewer reads text data from the SQLite file and extracts images directly from the original MDB file.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
