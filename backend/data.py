import pandas as pd
import os

def clean_sql_string(value):
    """Escapes single quotes and handles missing values for strings."""
    if pd.isna(value):
        return "NULL"
    # Escape single quotes by doubling them
    clean_val = str(value).replace("'", "''")
    return f"'{clean_val}'"

def clean_sql_number(value):
    """Handles missing values for numbers."""
    if pd.isna(value):
        return "NULL"
    return str(value)

def read_csv_robust(file_path, **kwargs):
    """
    Attempts to read a CSV file with multiple encodings to handle special characters.
    Accepts **kwargs to allow passing parameters like dtype.
    """
    encodings = ['utf-8', 'cp1252', 'latin1', 'ISO-8859-1']
    for encoding in encodings:
        try:
            return pd.read_csv(file_path, encoding=encoding, **kwargs)
        except UnicodeDecodeError:
            continue
    
    # If all encodings fail, force read with errors ignored/replaced
    print(f"Warning: Could not determine encoding for {file_path}. Reading with data loss allowed.")
    return pd.read_csv(file_path, encoding='utf-8', errors='replace', **kwargs)

def generate_sql():
    # 1. Load the main Gate Data file
    try:
        gate_df = read_csv_robust("Gate Data.csv")
    except FileNotFoundError:
        print("Error: 'Gate Data.csv' not found.")
        return

    sql_statements = []
    
    # Create Table Definitions (DDL)
    sql_statements.append("CREATE TABLE Gate ([Gate ID] INTEGER PRIMARY KEY, [Gate Name] VARCHAR(255), [From] VARCHAR(255), [To] VARCHAR(255), [Gate Price] DECIMAL(18,2));")
    sql_statements.append("CREATE TABLE Item_Pricing ([Pricing ID] INTEGER PRIMARY KEY, [Gate ID] INT, [Item ID] VARCHAR(50), [Item Name] VARCHAR(255), [Principal] VARCHAR(255), [Brand] VARCHAR(255), [Transportation Cost] VARCHAR(50));")
    sql_statements.append("")

    pricing_id_counter = 1

    # 2. Iterate through each gate to generate SQL
    for index, row in gate_df.iterrows():
        # Generate a Gate ID (1, 2, 3...)
        gate_id = index + 1
        
        gate_name = row['Gate Name']
        from_location = row['From']
        to_location = row['To']
        gate_price = row['Price']
        file_name = row['File Name']
        
        # Prepare values for SQL
        val_gate_id = str(gate_id)
        val_gate_name = clean_sql_string(gate_name)
        val_from = clean_sql_string(from_location)
        val_to = clean_sql_string(to_location)
        val_gate_price = clean_sql_number(gate_price)
        
        # INSERT statement for Gate table
        sql_statements.append(f"INSERT INTO Gate ([Gate ID], [Gate Name], [From], [To], [Gate Price]) VALUES ({val_gate_id}, {val_gate_name}, {val_from}, {val_to}, {val_gate_price});")
        
        # 3. Process the corresponding Item Master file if it exists
        if pd.notna(file_name):
            if os.path.exists(file_name):
                try:
                    # FIX: Pass dtype={'Item Code': str} to keep leading zeros (e.g. 0201...)
                    item_df = read_csv_robust(file_name, dtype={'Item Code': str})
                    
                    for _, item_row in item_df.iterrows():
                        # Map columns
                        val_pricing_id = str(pricing_id_counter)
                        val_gate_fk = str(gate_id)
                        
                        val_item_id = clean_sql_string(item_row.get('Item Code'))
                        val_item_name = clean_sql_string(item_row.get('Item Name'))
                        val_principal = clean_sql_string(item_row.get('Principal'))
                        val_brand = clean_sql_string(item_row.get('Brand'))
                        val_trans_cost = clean_sql_string(item_row.get('Transportation Cost'))
                        
                        sql_statements.append(f"INSERT INTO Item_Pricing ([Pricing ID], [Gate ID], [Item ID], [Item Name], [Principal], [Brand], [Transportation Cost]) VALUES ({val_pricing_id}, {val_gate_fk}, {val_item_id}, {val_item_name}, {val_principal}, {val_brand}, {val_trans_cost});")
                        
                        pricing_id_counter += 1
                except Exception as e:
                    print(f"Error processing {file_name}: {e}")
                    sql_statements.append(f"-- Error processing file {file_name}: {e}")
            else:
                print(f"File not found: {file_name}")
                sql_statements.append(f"-- File not found: {file_name}")

    # 4. Save to a SQL file
    output_filename = 'output_script.sql'
    with open(output_filename, 'w', encoding='utf-8') as f:
        f.write('\n'.join(sql_statements))
    
    print(f"SQL generation complete. Saved to {output_filename}")

if __name__ == "__main__":
    generate_sql()