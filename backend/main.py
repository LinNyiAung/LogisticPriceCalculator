import pyodbc
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import json
from datetime import datetime
import csv
import os

app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    """Get list of branches from Gate Data.csv"""
    try:
        gate_data = load_gate_data()
        branches = []
        
        for row in gate_data:
            branch = row.get('Branch', '').strip()
            file_name = row.get('File Name', '').strip()
            price_str = row.get('Price', '').strip()
            
            if branch and file_name:
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
                
                branches.append({
                    "branch": branch,
                    "file_name": file_name,
                    "price": price,
                    "calculation_type": calc_type
                })
        
        return {"branches": branches}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading branches: {str(e)}")

@app.get("/branch-config/{branch}")
def get_branch_config(branch: str):
    """Get configuration for a specific branch including calculation type and pricing"""
    try:
        gate_data = load_gate_data()
        
        # Find the branch in gate data
        branch_row = None
        for row in gate_data:
            if row.get('Branch', '').strip() == branch:
                branch_row = row
                break
        
        if not branch_row:
            raise HTTPException(status_code=404, detail=f"Branch {branch} not found")
        
        file_name = branch_row.get('File Name', '').strip()
        price_str = branch_row.get('Price', '').strip()
        
        if not file_name:
            raise HTTPException(status_code=400, detail=f"No file name configured for branch {branch}")
        
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
            "branch": branch,
            "file_name": file_name,
            "calculation_type": calc_type,
            "gate_price": gate_price,
            "item_pricing": item_pricing
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading branch config: {str(e)}")

@app.post("/calculate-with-branch")
def calculate_with_branch(pick_id: str, branch: str):
    """Calculate prices using branch configuration"""
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
        
        # Get branch configuration
        branch_config = get_branch_config(branch)
        calc_type = branch_config['calculation_type']
        gate_price = branch_config['gate_price']
        item_pricing = branch_config['item_pricing']
        
        calculated_products = []
        total_price = 0.0
        
        if calc_type == "gate_pricing":
            # Gate pricing: use gate price per kg
            if gate_price is None:
                raise HTTPException(status_code=400, detail=f"No gate price configured for branch {branch}")
            
            
            
            for row in rows:
                item_code = row[0] if row[0] else ""
                description = row[1] if row[1] else ""
                quantity = float(row[2]) if row[2] else 0.0
                uom = row[3] if row[3] else ""
                weight = float(row[4]) if row[4] else 0.0
                
                # Calculate price based on weight
                price = weight * gate_price
                total_price += price
                
                calculated_products.append({
                    "code": item_code,
                    "name": description,
                    "quantity": quantity,
                    "uom": uom,
                    "weight": weight,
                    "calculation_type": "weight",
                    "price": price
                })
        
        elif calc_type == "direct_pricing":
            # Direct pricing: use transportation cost per item
            for row in rows:
                item_code = row[0] if row[0] else ""
                description = row[1] if row[1] else ""
                quantity = float(row[2]) if row[2] else 0.0
                uom = row[3] if row[3] else ""
                weight = float(row[4]) if row[4] else 0.0
                
                # Get pricing for this item
                pricing_info = item_pricing.get(item_code)
                
                if pricing_info and pricing_info['value'] is not None:
                    price_per_one = pricing_info['value']
                    price = quantity * price_per_one
                else:
                    price_per_one = 0.0
                    price = 0.0
                
                total_price += price
                
                calculated_products.append({
                    "code": item_code,
                    "name": description,
                    "quantity": quantity,
                    "uom": uom,
                    "weight": weight,
                    "calculation_type": "direct",
                    "price_per_one": price_per_one,
                    "price": price
                })
        
        else:
            raise HTTPException(status_code=400, detail="Unable to determine calculation type")
        
        return {
            "calculation_type": calc_type,
            "branch": branch,
            "gate_price": gate_price,
            "calculated_products": calculated_products,
            "total_price": total_price
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