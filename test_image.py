

import subprocess

MDB_PATH = 'Northwind.MDB'

def test_image_extraction():
    table = 'Employees'
    pk_col = 'EmployeeID'
    pk_val = 1
    image_col = 'Photo'

    print(f"--- Testing Image Extraction for {table} record {pk_val} ---")

    query = f'SELECT "{image_col}" FROM "{table}" WHERE "{pk_col}" = {pk_val}'
    command = ['mdb-sql', '-H', '-P', MDB_PATH]

    print(f"Executing command: {' '.join(command)}")
    print(f"With query to stdin: {query}")

    try:
        process = subprocess.run(command, input=query.encode('utf-8'), capture_output=True, check=False)
        
        if process.returncode != 0:
            print("\n--- ERROR: mdb-sql command failed ---")
            print(f"Return Code: {process.returncode}")
            print(f"Stderr: {process.stderr.decode('utf-8', 'ignore')}")
            return

        raw_output = process.stdout
        print(f"\n--- SUCCESS: mdb-sql executed ---")
        print(f"Raw output length: {len(raw_output)} bytes")

        with open("raw_photo_output.bin", "wb") as f:
            f.write(raw_output)
        print("Raw output saved to 'raw_photo_output.bin'")

        # The heuristic: Find the BMP 'BM' header to strip the OLE wrapper
        bmp_start_index = raw_output.find(b'BM')
        
        if bmp_start_index != -1:
            print(f"BMP header ('BM') found at index: {bmp_start_index}")
            cleaned_data = raw_output[bmp_start_index:]
            with open("cleaned_photo.bmp", "wb") as f:
                f.write(cleaned_data)
            print("Cleaned BMP data saved to 'cleaned_photo.bmp'")
        else:
            print("\n--- ERROR: BMP header ('BM') not found in the raw output! ---")
            # Print first 100 bytes to see what we got
            print(f"Start of raw data: {raw_output[:100]}")

    except FileNotFoundError:
        print("Error: 'mdb-sql' not found. Is mdb-tools installed and in your PATH?")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    test_image_extraction()

