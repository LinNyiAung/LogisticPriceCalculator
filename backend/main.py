import pyodbc
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import json
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

# New endpoints using PG_PickDetail table
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
        
        # Get counts and date range
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