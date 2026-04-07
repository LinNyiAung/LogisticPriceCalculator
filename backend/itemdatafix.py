import pyodbc
import csv

def get_dwbi_connection():
    """Create and return a SQL Server connection to DWBI (Read-Only Source)"""
    conn_str = (
        'DRIVER={ODBC Driver 17 for SQL Server};'
        'SERVER=phm\\reportingsvr;'
        'DATABASE=DWBI;'
        'Trusted_Connection=yes;'
    )
    return pyodbc.connect(conn_str)

def update_csv_from_db(input_csv, output_csv):
    db_lookup = {}
    
    # 1. Fetch reference data from the database
    print("Connecting to database and fetching item data...")
    try:
        conn = get_dwbi_connection()
        cursor = conn.cursor()
        
        # We only select the columns we need to save memory
        query = """
            SELECT Sector, ItemCode, ItemName, ItmsGrpNam, U_BrandName 
            FROM Itemmasterallpp
        """
        cursor.execute(query)
        rows = cursor.fetchall()
        
        # Build a dictionary with ItemCode as the key for O(1) lookups
        for row in rows:
            # row[0]=Sector, row[1]=ItemCode, row[2]=ItemName, row[3]=ItmsGrpNam, row[4]=U_BrandName
            item_code = str(row[1]).strip() if row[1] else ""
            db_lookup[item_code] = {
                'BU': str(row[0]).strip() if row[0] else "",
                'Item Name': str(row[2]).strip() if row[2] else "",
                'Principal': str(row[3]).strip() if row[3] else "",
                'Brand': str(row[4]).strip() if row[4] else ""
            }
            
        print(f"Successfully loaded {len(db_lookup)} items from the database.")
        
    except pyodbc.Error as e:
        print(f"A database error occurred: {e}")
        return
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()
            
    # 2. Process the CSV file
    print(f"Reading '{input_csv}' and updating records...")
    try:
        with open(input_csv, mode='r', encoding='utf-8-sig') as infile:
            reader = csv.DictReader(infile)
            
            # Setup the new column order (BU first, then the rest)
            original_fields = list(reader.fieldnames)
            new_fieldnames = ['BU'] + original_fields
            
            rows_to_write = []
            matched_count = 0
            
            for row in reader:
                csv_item_code = str(row.get('Item Code', '')).strip()
                
                # If the item code from the CSV is found in our database dictionary
                if csv_item_code in db_lookup:
                    db_info = db_lookup[csv_item_code]
                    
                    row['BU'] = db_info['BU']
                    row['Item Name'] = db_info['Item Name']
                    row['Principal'] = db_info['Principal']
                    row['Brand'] = db_info['Brand']
                    
                    matched_count += 1
                else:
                    # If not found in DB, leave the old data but add an empty BU
                    row['BU'] = ""
                    
                rows_to_write.append(row)

        # 3. Write the updated data to a new CSV file
        print(f"Writing updated data to '{output_csv}'...")
        with open(output_csv, mode='w', encoding='utf-8-sig', newline='') as outfile:
            writer = csv.DictWriter(outfile, fieldnames=new_fieldnames)
            
            writer.writeheader()
            writer.writerows(rows_to_write)
            
        print(f"Done! {matched_count} out of {len(rows_to_write)} rows were successfully updated.")

    except FileNotFoundError:
        print(f"Error: The file '{input_csv}' was not found. Please check the file path.")
    except Exception as e:
        print(f"An unexpected error occurred while processing the CSV: {e}")

if __name__ == "__main__":
    # Define your input and output file names
    INPUT_CSV_FILE = 'Item Master HA.csv'
    OUTPUT_CSV_FILE = 'Updated Item Master HA.csv'
    
    update_csv_from_db(INPUT_CSV_FILE, OUTPUT_CSV_FILE)