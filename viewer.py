import tkinter as tk
from tkinter import ttk
import sqlite3
import subprocess
import io
import csv
import sys
import os
from PIL import Image, ImageTk

# Common names for columns that might contain images
IMAGE_COLUMN_CANDIDATES = ['Photo', 'Picture']

class MdbImageViewer(tk.Tk):
    def __init__(self, sqlite_path, mdb_path):
        super().__init__()

        if not os.path.exists(sqlite_path):
            raise FileNotFoundError(f"SQLite file not found: {sqlite_path}")
        if not os.path.exists(mdb_path):
            raise FileNotFoundError(f"MDB file not found: {mdb_path}")

        self.sqlite_path = sqlite_path
        self.mdb_path = mdb_path

        self.title(f"Viewer - {os.path.basename(sqlite_path)}")
        self.geometry("800x600")

        # Data storage
        self.table_data_cache = {} # Cache for table data
        self.current_record_index = -1
        self.current_table = ""
        self.image_col = ""

        # --- UI Setup ---
        top_frame = ttk.Frame(self)
        top_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(top_frame, text="Select Table:").pack(side=tk.LEFT, padx=(0, 5))
        self.table_selector = ttk.Combobox(top_frame, state="readonly")
        self.table_selector.pack(fill=tk.X, expand=True)
        self.table_selector.bind("<<ComboboxSelected>>", self.on_table_select)

        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_columnconfigure(1, weight=1)
        main_frame.grid_rowconfigure(0, weight=1)

        text_frame = ttk.LabelFrame(main_frame, text="Record Data", padding="10")
        text_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        self.text_data_display = tk.Text(text_frame, wrap=tk.WORD, state=tk.DISABLED, height=10, width=40)
        self.text_data_display.pack(fill=tk.BOTH, expand=True)

        image_frame = ttk.LabelFrame(main_frame, text="Image", padding="10")
        image_frame.grid(row=0, column=1, sticky="nsew")
        self.image_label = ttk.Label(image_frame, anchor=tk.CENTER)
        self.image_label.pack(fill=tk.BOTH, expand=True)
        self.no_image_label = ttk.Label(image_frame, text="No Image", anchor=tk.CENTER)

        nav_frame = ttk.Frame(self)
        nav_frame.pack(fill=tk.X, padx=10, pady=5)

        self.prev_button = ttk.Button(nav_frame, text="<< Previous", command=self.prev_record, state=tk.DISABLED)
        self.prev_button.pack(side=tk.LEFT)

        self.record_status_label = ttk.Label(nav_frame, text="Record X of Y")
        self.record_status_label.pack(side=tk.LEFT, expand=True)

        self.next_button = ttk.Button(nav_frame, text="Next >>", command=self.next_record, state=tk.DISABLED)
        self.next_button.pack(side=tk.RIGHT)

        self.load_table_names()

    def load_table_names(self):
        """Connects to the SQLite DB just to get the list of tables."""
        try:
            with sqlite3.connect(self.sqlite_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
                tables = [row[0] for row in cursor.fetchall()]
                self.table_selector['values'] = tables
                if tables:
                    self.table_selector.current(0)
                    self.on_table_select()
        except sqlite3.Error as e:
            self.show_error(f"Database Error: {e}")

    def load_data_from_mdb(self, table_name):
        """Loads data for a table directly from MDB using mdb-export with hex encoding."""
        if table_name in self.table_data_cache:
            return self.table_data_cache[table_name]

        print(f"Loading data for '{table_name}' from MDB...")
        try:
            command = ['mdb-export', '-b', 'hex', '-D', '%Y-%m-%d %H:%M:%S', self.mdb_path, table_name]
            csv_output = subprocess.check_output(command).decode('utf-8')
            
            reader = csv.reader(csv_output.splitlines())
            header = next(reader)
            
            data = [dict(zip(header, row)) for row in reader]
            self.table_data_cache[table_name] = data
            print(f"Successfully loaded and cached {len(data)} records.")
            return data
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            self.show_error(f"Failed to load data from MDB for table {table_name}.\n\n{e}")
            return []

    def on_table_select(self, event=None):
        """Loads data for the selected table from the MDB file."""
        self.current_table = self.table_selector.get()
        if not self.current_table:
            return

        table_data = self.load_data_from_mdb(self.current_table)
        self.image_col = ""
        if table_data:
            header = table_data[0].keys()
            for col_name in header:
                if col_name in IMAGE_COLUMN_CANDIDATES:
                    self.image_col = col_name
                    break
            
            self.current_record_index = 0
            self.display_record()
        else:
            self.current_record_index = -1
            self.clear_display()
        
        self.update_nav_state()

    def display_record(self):
        """Displays the current record's text and image data from the cache."""
        table_data = self.table_data_cache.get(self.current_table, [])
        if not table_data or self.current_record_index < 0:
            return

        record = table_data[self.current_record_index]
        
        text_content = ""
        hex_image_string = ""
        for key, value in record.items():
            if key == self.image_col:
                hex_image_string = value
            text_content += f"{key}: {value}\n"
        
        self.text_data_display.config(state=tk.NORMAL)
        self.text_data_display.delete(1.0, tk.END)
        self.text_data_display.insert(tk.END, text_content)
        self.text_data_display.config(state=tk.DISABLED)

        self.image_label.config(image='')
        self.no_image_label.pack_forget()

        if hex_image_string:
            try:
                binary_data = bytes.fromhex(hex_image_string)
                
                bmp_start = binary_data.find(b'BM')
                if bmp_start != -1:
                    binary_data = binary_data[bmp_start:]

                img = Image.open(io.BytesIO(binary_data))
                img.thumbnail((300, 300))
                photo = ImageTk.PhotoImage(img)
                
                self.image_label.config(image=photo)
                self.image_label.image = photo
            except (ValueError, TypeError, Exception) as e:
                print(f"Error processing image data for record: {e}")
                self.show_no_image_label()
        else:
            self.show_no_image_label()

        self.update_nav_state()

    def next_record(self):
        table_data = self.table_data_cache.get(self.current_table, [])
        if self.current_record_index < len(table_data) - 1:
            self.current_record_index += 1
            self.display_record()

    def prev_record(self):
        if self.current_record_index > 0:
            self.current_record_index -= 1
            self.display_record()
            
    def update_nav_state(self):
        total_records = len(self.table_data_cache.get(self.current_table, []))
        if self.current_record_index != -1:
            self.record_status_label.config(text=f"Record {self.current_record_index + 1} of {total_records}")
        else:
            self.record_status_label.config(text="No records")

        self.prev_button.config(state=tk.NORMAL if self.current_record_index > 0 else tk.DISABLED)
        self.next_button.config(state=tk.NORMAL if self.current_record_index < total_records - 1 else tk.DISABLED)

    def clear_display(self):
        self.text_data_display.config(state=tk.NORMAL)
        self.text_data_display.delete(1.0, tk.END)
        self.text_data_display.config(state=tk.DISABLED)
        self.image_label.config(image='')
        self.show_no_image_label()

    def show_no_image_label(self):
        self.image_label.image = None
        self.no_image_label.pack(expand=True)

    def show_error(self, message):
        self.clear_display()
        self.text_data_display.config(state=tk.NORMAL)
        self.text_data_display.insert(tk.END, f"ERROR:\n\n{message}")
        self.text_data_display.config(state=tk.DISABLED)

    def on_closing(self):
        self.destroy()

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python3 viewer.py <path_to_sqlite_file> <path_to_mdb_file>")
        sys.exit(1)

    sqlite_path = sys.argv[1]
    mdb_path = sys.argv[2]
    
    app = MdbImageViewer(sqlite_path, mdb_path)
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
