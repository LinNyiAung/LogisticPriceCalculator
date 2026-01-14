import logging
import pyodbc
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import json
from datetime import datetime
import csv
import os
import shutil
from datetime import datetime

app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add these imports at the top if not already present
import shutil
from datetime import datetime
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Helper function to write CSV with proper encoding
def write_csv_file(file_path, headers, data):
    """Write data to CSV file with UTF-8 encoding"""
    try:
        # Create a backup before writing
        if os.path.exists(file_path):
            backup_path = file_path + '.backup'
            shutil.copy2(file_path, backup_path)
        
        with open(file_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(data)
        
        logger.info(f"Successfully wrote {len(data)} rows to {file_path}")
        return True
    except Exception as e:
        # Restore from backup if write failed
        backup_path = file_path + '.backup'
        if os.path.exists(backup_path):
            shutil.copy2(backup_path, file_path)
            logger.error(f"Error writing CSV, restored from backup: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error writing CSV: {str(e)}")

# Gate Data Management Endpoints

@app.get("/admin/gates")
def get_all_gates():
    """Get all gates from Gate Data.csv"""
    try:
        gate_data = load_gate_data()
        gates = []
        
        for row in gate_data:
            gate_entry = {
                "gate_name": row.get('Gate Name', '').strip(),
                "branch": row.get('Branch', '').strip(),
                "file_name": row.get('File Name', '').strip(),
                "price": row.get('Price', '').strip()
            }
            gates.append(gate_entry)
            logger.info(f"Loaded gate: {gate_entry}")
        
        return {"gates": gates}
    except Exception as e:
        logger.error(f"Error loading gates: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error loading gates: {str(e)}")

@app.post("/admin/gates")
def save_gate(gate_data: dict):
    """Add or update a gate in Gate Data.csv"""
    try:
        file_path = os.path.join(os.path.dirname(__file__), 'Gate Data.csv')
        
        # Load existing data
        existing_gates = load_gate_data()
        
        # Get the gate name to search for (use original_gate_name if editing)
        gate_name = gate_data.get('gate_name', '').strip()
        original_gate_name = gate_data.get('original_gate_name', gate_name).strip()
        
        logger.info(f"Saving gate - New name: {gate_name}, Original name: {original_gate_name}")
        
        found = False
        
        new_gate_entry = {
            'Gate Name': gate_name,
            'Branch': gate_data.get('branch', '').strip(),
            'File Name': gate_data.get('file_name', '').strip(),
            'Price': gate_data.get('price', '').strip()
        }
        
        # Look for existing gate using original_gate_name
        for i, row in enumerate(existing_gates):
            existing_name = row.get('Gate Name', '').strip()
            logger.info(f"Comparing existing gate '{existing_name}' with original '{original_gate_name}'")
            
            if existing_name == original_gate_name:
                # Update existing gate
                logger.info(f"Updating existing gate at index {i}")
                existing_gates[i] = new_gate_entry
                found = True
                break
        
        if not found:
            # Add new gate
            logger.info(f"Adding new gate: {gate_name}")
            existing_gates.append(new_gate_entry)
        
        # Write back to CSV
        headers = ['Gate Name', 'Branch', 'File Name', 'Price']
        write_csv_file(file_path, headers, existing_gates)
        
        return {"message": "Gate saved successfully", "gate": new_gate_entry}
    
    except Exception as e:
        logger.error(f"Error saving gate: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error saving gate: {str(e)}")

@app.delete("/admin/gates/{gate_name}")
async def delete_gate(gate_name: str):
    """Delete a gate from Gate Data.csv"""
    try:
        logger.info(f"Attempting to delete gate: {gate_name}")
        file_path = os.path.join(os.path.dirname(__file__), 'Gate Data.csv')
        
        # Load existing data
        existing_gates = load_gate_data()
        logger.info(f"Loaded {len(existing_gates)} gates")
        
        # Filter out the gate to delete
        updated_gates = [
            row for row in existing_gates 
            if row.get('Gate Name', '').strip() != gate_name
        ]
        
        if len(updated_gates) == len(existing_gates):
            logger.warning(f"Gate {gate_name} not found")
            raise HTTPException(status_code=404, detail=f"Gate {gate_name} not found")
        
        logger.info(f"Deleted gate, {len(updated_gates)} gates remaining")
        
        # Write back to CSV
        headers = ['Gate Name', 'Branch', 'File Name', 'Price']
        write_csv_file(file_path, headers, updated_gates)
        
        return {"message": f"Gate {gate_name} deleted successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting gate: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting gate: {str(e)}")

# Item Master Management Endpoints

@app.get("/admin/item-master-files")
def get_item_master_files():
    """Get list of all Item Master CSV files"""
    try:
        current_dir = os.path.dirname(__file__)
        files = [f for f in os.listdir(current_dir) if f.startswith('Item Master') and f.endswith('.csv')]
        return {"files": sorted(files)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing files: {str(e)}")

@app.get("/admin/item-master/{file_name}")
def get_item_master(file_name: str):
    """Get all items from a specific Item Master file"""
    try:
        # Security check - ensure file_name is safe
        if not file_name.startswith('Item Master') or not file_name.endswith('.csv'):
            raise HTTPException(status_code=400, detail="Invalid file name")
        
        data = load_item_master(file_name)
        
        items = []
        for row in data:
            items.append({
                "item_code": row.get('Item Code', '').strip(),
                "item_name": row.get('Item Name', '').strip(),
                "is_active": row.get('Is Active', '').strip(),
                "principal": row.get('Principal', '').strip(),
                "brand": row.get('Brand', '').strip(),
                "uom": row.get('UOM', '').strip(),
                "purchase_weight": row.get('Purchase Weight', '').strip(),
                "transportation_cost": row.get('Transportation Cost', '').strip()
            })
        
        return {"items": items, "file_name": file_name}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading item master: {str(e)}")

@app.post("/admin/item-master/{file_name}")
def save_item(file_name: str, item_data: dict):
    """Add or update an item in Item Master file"""
    try:
        # Security check
        if not file_name.startswith('Item Master') or not file_name.endswith('.csv'):
            raise HTTPException(status_code=400, detail="Invalid file name")
        
        file_path = os.path.join(os.path.dirname(__file__), file_name)
        
        # Load existing data
        existing_items = load_item_master(file_name)
        
        # Check if updating existing item
        item_code = item_data.get('item_code', '').strip()
        found = False
        
        for i, row in enumerate(existing_items):
            if row.get('Item Code', '').strip() == item_code:
                # Update existing item
                existing_items[i] = {
                    'Item Code': item_data.get('item_code', ''),
                    'Item Name': item_data.get('item_name', ''),
                    'Is Active': item_data.get('is_active', 'Active'),
                    'Principal': item_data.get('principal', ''),
                    'Brand': item_data.get('brand', ''),
                    'UOM': item_data.get('uom', ''),
                    'Purchase Weight': item_data.get('purchase_weight', ''),
                    'Transportation Cost': item_data.get('transportation_cost', 'Ton')
                }
                found = True
                break
        
        if not found:
            # Add new item
            existing_items.append({
                'Item Code': item_data.get('item_code', ''),
                'Item Name': item_data.get('item_name', ''),
                'Is Active': item_data.get('is_active', 'Active'),
                'Principal': item_data.get('principal', ''),
                'Brand': item_data.get('brand', ''),
                'UOM': item_data.get('uom', ''),
                'Purchase Weight': item_data.get('purchase_weight', ''),
                'Transportation Cost': item_data.get('transportation_cost', 'Ton')
            })
        
        # Write back to CSV
        headers = ['Item Code', 'Item Name', 'Is Active', 'Principal', 'Brand', 'UOM', 'Purchase Weight', 'Transportation Cost']
        write_csv_file(file_path, headers, existing_items)
        
        return {"message": "Item saved successfully", "item": item_data}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving item: {str(e)}")

@app.delete("/admin/item-master/{file_name}/{item_code}")
def delete_item(file_name: str, item_code: str):
    """Delete an item from Item Master file"""
    try:
        # Security check
        if not file_name.startswith('Item Master') or not file_name.endswith('.csv'):
            raise HTTPException(status_code=400, detail="Invalid file name")
        
        file_path = os.path.join(os.path.dirname(__file__), file_name)
        
        # Load existing data
        existing_items = load_item_master(file_name)
        
        # Filter out the item to delete
        updated_items = [
            row for row in existing_items 
            if row.get('Item Code', '').strip() != item_code
        ]
        
        if len(updated_items) == len(existing_items):
            raise HTTPException(status_code=404, detail=f"Item {item_code} not found")
        
        # Write back to CSV
        headers = ['Item Code', 'Item Name', 'Is Active', 'Principal', 'Brand', 'UOM', 'Purchase Weight', 'Transportation Cost']
        write_csv_file(file_path, headers, updated_items)
        
        return {"message": f"Item {item_code} deleted successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting item: {str(e)}")

# Optional: Backup functionality
@app.post("/admin/backup")
def create_backup():
    """Create backup of all CSV files"""
    try:
        current_dir = os.path.dirname(__file__)
        backup_dir = os.path.join(current_dir, 'backups')
        
        # Create backup directory if it doesn't exist
        os.makedirs(backup_dir, exist_ok=True)
        
        # Create timestamped backup folder
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_folder = os.path.join(backup_dir, f'backup_{timestamp}')
        os.makedirs(backup_folder, exist_ok=True)
        
        # Backup Gate Data.csv
        gate_file = os.path.join(current_dir, 'Gate Data.csv')
        if os.path.exists(gate_file):
            shutil.copy2(gate_file, backup_folder)
        
        # Backup all Item Master files
        item_files = [f for f in os.listdir(current_dir) if f.startswith('Item Master') and f.endswith('.csv')]
        for file_name in item_files:
            file_path = os.path.join(current_dir, file_name)
            shutil.copy2(file_path, backup_folder)
        
        return {
            "message": "Backup created successfully",
            "backup_folder": backup_folder,
            "files_backed_up": len(item_files) + 1
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating backup: {str(e)}")

# SQL Server connection string for reading data
def get_db_connection():
    """Create and return a SQL Server connection"""
    conn_str = (
        'DRIVER={ODBC Driver 17 for SQL Server};'
        'SERVER=phm\\reportingsvr;'
        'DATABASE=DWBI;'
        'Trusted_Connection=yes;'
    )
    return pyodbc.connect(conn_str)

# CSV Helper Functions
def read_csv_with_encoding(file_path):
    """Try multiple encodings to read CSV file"""
    encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252', 'utf-8-sig']
    
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                reader = csv.DictReader(f)
                data = list(reader)
                return data
        except (UnicodeDecodeError, Exception):
            continue
    
    raise HTTPException(status_code=500, detail=f"Could not read file {file_path} with any encoding")

def load_gate_data():
    """Load Gate Data.csv"""
    file_path = os.path.join(os.path.dirname(__file__), 'Gate Data.csv')
    return read_csv_with_encoding(file_path)

def load_item_master(file_name):
    """Load specific Item Master CSV file"""
    file_path = os.path.join(os.path.dirname(__file__), file_name)
    return read_csv_with_encoding(file_path)

def determine_calculation_type(item_master_data):
    """Determine if gate pricing or direct pricing based on Transportation Cost column"""
    if not item_master_data:
        return "unknown"
    
    has_ton = False
    has_number = False
    
    for row in item_master_data:
        transport_cost = str(row.get('Transportation Cost', '')).strip()
        
        if transport_cost.lower() == 'ton':
            has_ton = True
        else:
            try:
                float(transport_cost)
                has_number = True
            except ValueError:
                pass
    
    # If all are numbers, it's direct pricing
    if has_number and not has_ton:
        return "direct_pricing"
    # If has "Ton" (either all or mixed), it's gate pricing
    elif has_ton:
        return "gate_pricing"
    else:
        return "unknown"

# Pydantic models
class Product(BaseModel):
    code: str
    name: str
    quantity: float
    uom: str
    weight: float
    calculation_type: str
    price_per_one: Optional[float] = None

class GatePricing(BaseModel):
    gate_name: str
    weight_unit: str
    weight_unit_number: float
    weight_unit_price: float

class CalculationRequest(BaseModel):
    calculation_type: str
    gate_pricing: Optional[GatePricing] = None
    products: List[Product]
    total_price: Optional[float] = None

class CalculatedProduct(BaseModel):
    code: str
    name: str
    quantity: float
    uom: str
    weight: float
    calculation_type: str
    price_per_one: Optional[float] = None
    price: float

class CalculationResponse(BaseModel):
    calculated_products: List[CalculatedProduct]
    total_price: Optional[float] = None

class SavedCalculation(BaseModel):
    id: int
    created_at: str
    calculation_type: str
    gate_pricing: Optional[GatePricing]
    products: List[Product]
    total_price: Optional[float]
    calculated_products: List[CalculatedProduct]

class CSVProduct(BaseModel):
    item_code: str
    description: str
    quantity: float
    uom: str
    item_weight: float

class BranchInfo(BaseModel):
    branch: str
    file_name: str
    price: Optional[float]
    calculation_type: str

# New CSV-related endpoints
@app.get("/branches")
def get_branches():
    """Get list of gates from Gate Data.csv"""
    try:
        gate_data = load_gate_data()
        gates = []
        
        for row in gate_data:
            gate_name = row.get('Gate Name', '').strip()
            branch = row.get('Branch', '').strip()
            file_name = row.get('File Name', '').strip()
            price_str = row.get('Price', '').strip()
            
            if gate_name and file_name:
                # Load item master to determine calculation type
                try:
                    item_master = load_item_master(file_name)
                    calc_type = determine_calculation_type(item_master)
                except:
                    calc_type = "unknown"
                
                # Parse price
                price = None
                if price_str:
                    try:
                        price = float(price_str)
                    except ValueError:
                        pass
                
                gates.append({
                    "gate_name": gate_name,
                    "branch": branch,
                    "file_name": file_name,
                    "price": price,
                    "calculation_type": calc_type
                })
        
        return {"gates": gates}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading gates: {str(e)}")

@app.get("/gate-config/{gate_name}")
def get_gate_config(gate_name: str):
    """Get configuration for a specific gate including calculation type and pricing"""
    try:
        gate_data = load_gate_data()
        
        # Find the gate in gate data
        gate_row = None
        for row in gate_data:
            if row.get('Gate Name', '').strip() == gate_name:
                gate_row = row
                break
        
        if not gate_row:
            raise HTTPException(status_code=404, detail=f"Gate {gate_name} not found")
        
        branch = gate_row.get('Branch', '').strip()
        file_name = gate_row.get('File Name', '').strip()
        price_str = gate_row.get('Price', '').strip()
        
        if not file_name:
            raise HTTPException(status_code=400, detail=f"No file name configured for gate {gate_name}")
        
        # Load item master
        item_master = load_item_master(file_name)
        calc_type = determine_calculation_type(item_master)
        
        # Parse price
        gate_price = None
        if price_str:
            try:
                gate_price = float(price_str)
            except ValueError:
                pass
        
        # Create item code to transport cost mapping
        item_pricing = {}
        for row in item_master:
            item_code = row.get('Item Code', '').strip()
            transport_cost = row.get('Transportation Cost', '').strip()
            
            if item_code:
                if transport_cost.lower() == 'ton':
                    item_pricing[item_code] = {'type': 'ton', 'value': None}
                else:
                    try:
                        cost = float(transport_cost)
                        item_pricing[item_code] = {'type': 'direct', 'value': cost}
                    except ValueError:
                        item_pricing[item_code] = {'type': 'unknown', 'value': None}
        
        return {
            "gate_name": gate_name,
            "branch": branch,
            "file_name": file_name,
            "calculation_type": calc_type,
            "gate_price": gate_price,
            "item_pricing": item_pricing
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading gate config: {str(e)}")

@app.post("/calculate-with-gate")
def calculate_with_gate(pick_id: str, gate_name: str, manual_total_price: Optional[float] = None):
    """Calculate prices using gate configuration with optional manual total price override"""
    try:
        # Get products from pick ID
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                ItemCode,
                Dscription,
                Quantity,
                UomCode,
                ItemWeight
            FROM PG_PickDetail 
            WHERE ID = ?
            ORDER BY ItemCode
        """, (pick_id,))
        
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        
        if not rows:
            raise HTTPException(status_code=404, detail="No products found for this Pick ID")
        
        # Get gate configuration
        gate_config = get_gate_config(gate_name)
        calc_type = gate_config['calculation_type']
        gate_price = gate_config['gate_price']
        item_pricing = gate_config['item_pricing']
        branch = gate_config['branch']
        
        calculated_products = []
        total_price = 0.0
        estimated_total_price = 0.0 # To track the theoretical price if manual wasn't provided
        
        if calc_type == "gate_pricing":
            if gate_price is None:
                raise HTTPException(status_code=400, detail=f"No gate price configured for gate {gate_name}")
            
            # 1. Segregate items and calculate the base "Ton" cost
            ton_items = []
            direct_items = []
            ton_cost_total = 0.0
            
            for row in rows:
                item_data = {
                    "code": row[0] if row[0] else "",
                    "name": row[1] if row[1] else "",
                    "quantity": float(row[2]) if row[2] else 0.0,
                    "uom": row[3] if row[3] else "",
                    "weight": float(row[4]) if row[4] else 0.0,
                }
                
                # Check item master config for this specific item
                p_info = item_pricing.get(item_data['code'], {})
                p_type = p_info.get('type', 'ton') # Default to ton if not specified
                p_val = p_info.get('value', 0.0)
                
                # Calculate Estimated Cost (Standard Logic)
                if p_type == 'direct':
                    estimated_total_price += (item_data['quantity'] * (p_val if p_val else 0))
                    item_data['standard_unit_price'] = p_val if p_val else 0
                    direct_items.append(item_data)
                else:
                    cost = item_data['weight'] * gate_price
                    estimated_total_price += cost
                    ton_cost_total += cost
                    item_data['price'] = cost
                    ton_items.append(item_data)

            # 2. Determine Direct Item Pricing Strategy
            direct_unit_price = 0.0
            
            if manual_total_price is not None:
                # User provided total: Calculate remainder for direct items
                remainder = manual_total_price - ton_cost_total
                total_direct_qty = sum(item['quantity'] for item in direct_items)
                
                if total_direct_qty > 0:
                    direct_unit_price = remainder / total_direct_qty
                
                total_price = manual_total_price
            else:
                # Use estimated/standard calculation
                total_price = estimated_total_price
            
            # 3. Build Final Result
            
            # Add Ton Items
            for item in ton_items:
                calculated_products.append({
                    **item,
                    "calculation_type": "weight",
                    "price_per_one": None,
                    "price": item['price'] 
                })
            
            # Add Direct Items
            for item in direct_items:
                # If manual total exists, use calculated rate. If not, use standard rate.
                if manual_total_price is not None:
                    final_unit_price = direct_unit_price
                else:
                    final_unit_price = item['standard_unit_price']
                
                final_item_price = item['quantity'] * final_unit_price
                
                calculated_products.append({
                    **item,
                    "calculation_type": "direct_split" if manual_total_price else "direct",
                    "price_per_one": final_unit_price,
                    "price": final_item_price
                })
                
                # If we are in standard mode, we sum up here (already done in estimate, but just to be safe for display)
                # If in manual mode, total is forced to manual_total_price
                
        elif calc_type == "direct_pricing":
            # Direct pricing logic (unchanged)
            for row in rows:
                item_code = row[0] if row[0] else ""
                pricing_info = item_pricing.get(item_code)
                
                quantity = float(row[2]) if row[2] else 0.0
                weight = float(row[4]) if row[4] else 0.0
                
                if pricing_info and pricing_info['value'] is not None:
                    price_per_one = pricing_info['value']
                    price = quantity * price_per_one
                else:
                    price_per_one = 0.0
                    price = 0.0
                
                total_price += price
                estimated_total_price += price
                
                calculated_products.append({
                    "code": item_code,
                    "name": row[1] if row[1] else "",
                    "quantity": quantity,
                    "uom": row[3] if row[3] else "",
                    "weight": weight,
                    "calculation_type": "direct",
                    "price_per_one": price_per_one,
                    "price": price
                })
        
        else:
            raise HTTPException(status_code=400, detail="Unable to determine calculation type")
        
        # Sort by name for clean display
        calculated_products.sort(key=lambda x: x['name'])
        
        return {
            "calculation_type": calc_type,
            "gate_name": gate_name,
            "branch": branch,
            "gate_price": gate_price,
            "calculated_products": calculated_products,
            "total_price": total_price,
            "estimated_total_price": estimated_total_price
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Calculation error: {str(e)}")

# Existing endpoints
@app.get("/pick-ids")
def get_pick_ids():
    """Get list of unique Pick IDs from PG_PickDetail table"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT DISTINCT ID 
            FROM PG_PickDetail 
            WHERE ID IS NOT NULL 
            ORDER BY ID DESC
        """)
        
        rows = cursor.fetchall()
        pick_ids = [row[0] for row in rows]
        
        cursor.close()
        conn.close()
        
        return {"pick_ids": pick_ids}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/products/{pick_id}")
def get_products_by_pick_id(pick_id: str):
    """Get products for a specific Pick ID from PG_PickDetail table"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                ItemCode,
                Dscription,
                Quantity,
                UomCode,
                ItemWeight,
                CardName,
                PickDate,
                VANCode,
                Status
            FROM PG_PickDetail 
            WHERE ID = ?
            ORDER BY ItemCode
        """, (pick_id,))
        
        rows = cursor.fetchall()
        
        if not rows:
            cursor.close()
            conn.close()
            raise HTTPException(status_code=404, detail="No products found for this Pick ID")
        
        products = []
        total_weight = 0.0
        
        # Get additional info from first row
        pick_info = {
            "card_name": rows[0][5] if rows[0][5] else "",
            "pick_date": rows[0][6].strftime("%Y-%m-%d") if rows[0][6] else "",
            "van_code": rows[0][7] if rows[0][7] else "",
            "status": rows[0][8] if rows[0][8] else ""
        }
        
        for row in rows:
            item_code = row[0] if row[0] else ""
            description = row[1] if row[1] else ""
            quantity = float(row[2]) if row[2] else 0.0
            uom_code = row[3] if row[3] else ""
            item_weight = float(row[4]) if row[4] else 0.0
            
            total_weight += item_weight
            
            products.append({
                "item_code": item_code,
                "description": description,
                "quantity": quantity,
                "uom": uom_code,
                "item_weight": item_weight
            })
        
        cursor.close()
        conn.close()
        
        return {
            "products": products,
            "total_weight": round(total_weight, 2),
            "pick_info": pick_info
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/pick-summary")
def get_pick_summary():
    """Get summary statistics of pick data"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT ID) as total_picks,
                COUNT(*) as total_items,
                MIN(PickDate) as earliest_date,
                MAX(PickDate) as latest_date,
                SUM(CAST(ItemWeight AS FLOAT)) as total_weight
            FROM PG_PickDetail
        """)
        
        row = cursor.fetchone()
        
        summary = {
            "total_picks": row[0] if row[0] else 0,
            "total_items": row[1] if row[1] else 0,
            "earliest_date": row[2].strftime("%Y-%m-%d") if row[2] else None,
            "latest_date": row[3].strftime("%Y-%m-%d") if row[3] else None,
            "total_weight": round(float(row[4]), 2) if row[4] else 0.0
        }
        
        cursor.close()
        conn.close()
        
        return summary
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/search-picks")
def search_picks(
    card_name: Optional[str] = None,
    van_code: Optional[str] = None,
    status: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None
):
    """Search pick IDs by various criteria"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = "SELECT DISTINCT ID, CardName, PickDate, VANCode, Status, TotalWeight FROM PG_PickDetail WHERE 1=1"
        params = []
        
        if card_name:
            query += " AND CardName LIKE ?"
            params.append(f"%{card_name}%")
        
        if van_code:
            query += " AND VANCode = ?"
            params.append(van_code)
        
        if status:
            query += " AND Status = ?"
            params.append(status)
        
        if from_date:
            query += " AND PickDate >= ?"
            params.append(from_date)
        
        if to_date:
            query += " AND PickDate <= ?"
            params.append(to_date)
        
        query += " ORDER BY PickDate DESC"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        results = []
        for row in rows:
            results.append({
                "id": row[0],
                "card_name": row[1] if row[1] else "",
                "pick_date": row[2].strftime("%Y-%m-%d") if row[2] else "",
                "van_code": row[3] if row[3] else "",
                "status": row[4] if row[4] else "",
                "total_weight": float(row[5]) if row[5] else 0.0
            })
        
        cursor.close()
        conn.close()
        
        return {"results": results}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.post("/calculate", response_model=CalculationResponse)
def calculate_prices(request: CalculationRequest):
    try:
        if request.calculation_type == "gate_pricing":
            return calculate_gate_pricing(request)
        elif request.calculation_type == "direct_pricing":
            return calculate_direct_pricing(request)
        else:
            raise HTTPException(status_code=400, detail="Invalid calculation type")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

def calculate_gate_pricing(request: CalculationRequest):
    gate = request.gate_pricing
    products = request.products
    total_price = request.total_price
    
    if not gate or total_price is None:
        raise HTTPException(status_code=400, detail="Gate pricing and total price required")
    
    if gate.weight_unit.lower() == 'tonne':
        price_per_kg = gate.weight_unit_price / (gate.weight_unit_number * 1000)
    else:
        price_per_kg = gate.weight_unit_price / gate.weight_unit_number
    
    weight_products = [p for p in products if p.calculation_type.lower() == "weight"]
    pack_products = [p for p in products if p.calculation_type.lower() == "pack"]
    
    weight_total = sum(p.weight * price_per_kg for p in weight_products)
    pack_total = total_price - weight_total
    num_packs = sum(p.quantity for p in pack_products)
    price_per_pack = pack_total / num_packs if num_packs > 0 else 0
    
    calculated = []
    for p in weight_products:
        calculated.append(CalculatedProduct(
            code=p.code,
            name=p.name,
            quantity=p.quantity,
            uom=p.uom,
            weight=p.weight,
            calculation_type=p.calculation_type,
            price=p.weight * price_per_kg
        ))
    
    for p in pack_products:
        calculated.append(CalculatedProduct(
            code=p.code,
            name=p.name,
            quantity=p.quantity,
            uom=p.uom,
            weight=p.weight,
            calculation_type=p.calculation_type,
            price=p.quantity * price_per_pack
        ))
    
    return CalculationResponse(calculated_products=calculated, total_price=total_price)

def calculate_direct_pricing(request: CalculationRequest):
    calculated = []
    total = 0.0
    
    for p in request.products:
        if p.price_per_one is None:
            raise HTTPException(status_code=400, detail="Price per one required for direct pricing")
        
        price = p.quantity * p.price_per_one
        total += price
        
        calculated.append(CalculatedProduct(
            code=p.code,
            name=p.name,
            quantity=p.quantity,
            uom=p.uom,
            weight=p.weight,
            calculation_type=p.calculation_type,
            price_per_one=p.price_per_one,
            price=price
        ))
    
    return CalculationResponse(calculated_products=calculated, total_price=total)

@app.post("/save")
def save_calculation(request: CalculationRequest):
    """Save calculation - requires 'calculations' table to exist"""
    raise HTTPException(
        status_code=501, 
        detail="Save feature not implemented yet. Table 'calculations' needs to be created first."
    )

@app.get("/calculations", response_model=List[SavedCalculation])
def get_calculations():
    """Get saved calculations - requires 'calculations' table to exist"""
    raise HTTPException(
        status_code=501, 
        detail="Get calculations feature not implemented yet. Table 'calculations' needs to be created first."
    )

@app.delete("/calculations/{calc_id}")
def delete_calculation(calc_id: int):
    """Delete a calculation - requires 'calculations' table to exist"""
    raise HTTPException(
        status_code=501, 
        detail="Delete calculation feature not implemented yet. Table 'calculations' needs to be created first."
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)