import logging
import pyodbc
import sqlite3
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
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

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Database Connections ---

def get_dwbi_connection():
    """Create and return a SQL Server connection to DWBI (Read-Only Source)"""
    conn_str = (
        'DRIVER={ODBC Driver 17 for SQL Server};'
        'SERVER=phm\\reportingsvr;'
        'DATABASE=DWBI;'
        'Trusted_Connection=yes;'
    )
    return pyodbc.connect(conn_str)

def get_logistic_connection():
    """Create and return a SQLite connection to logistic.db (Read/Write Source)"""
    # Connects to a file named 'logistic.db' in the current directory
    db_path = os.path.join(os.path.dirname(__file__), 'logistic.db')
    conn = sqlite3.connect(db_path)
    return conn

# --- Initialization ---

@app.on_event("startup")
def startup_db():
    """Ensure logistic.db has the required tables"""
    try:
        conn = get_logistic_connection()
        cursor = conn.cursor()
        
        # Create Gate table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Gate (
                [Gate ID] INTEGER PRIMARY KEY,
                [Gate Name] TEXT,
                [Branch] TEXT,
                [Gate Price] REAL
            )
        """)
        
        # Create Item_Pricing table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Item_Pricing (
                [Pricing ID] INTEGER PRIMARY KEY,
                [Gate ID] INTEGER,
                [Item ID] TEXT,
                [Item Name] TEXT,
                [Is Active] TEXT,
                [Principal] TEXT,
                [Brand] TEXT,
                [UOM] TEXT,
                [Purchase Weight] REAL,
                [Transportation Cost] TEXT,
                FOREIGN KEY([Gate ID]) REFERENCES Gate([Gate ID])
            )
        """)
        
        conn.commit()
        conn.close()
        logger.info("Logistic DB initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")

# --- Pydantic Models ---

class GateData(BaseModel):
    gate_id: Optional[int] = None
    gate_name: str
    branch: str
    price: Optional[float] = None
    original_gate_name: Optional[str] = None

class ItemPricingData(BaseModel):
    pricing_id: Optional[int] = None
    gate_id: int
    item_code: str
    item_name: str
    is_active: str
    principal: Optional[str] = ""
    brand: Optional[str] = ""
    uom: Optional[str] = ""
    purchase_weight: Optional[float] = 0.0
    transportation_cost: str
    original_item_code: Optional[str] = None

# --- Helper Functions ---

def determine_calculation_type_sql(gate_id):
    """Determine calculation type based on SQLite data for a specific Gate ID"""
    try:
        conn = get_logistic_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT [Transportation Cost] FROM Item_Pricing WHERE [Gate ID] = ?", (gate_id,))
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return "unknown"

        has_ton = False
        has_number = False

        for row in rows:
            cost = str(row[0]).strip().lower()
            if cost == 'ton':
                has_ton = True
            else:
                try:
                    float(cost)
                    has_number = True
                except ValueError:
                    pass
        
        if has_number and not has_ton:
            return "direct_pricing"
        elif has_ton:
            return "gate_pricing"
        else:
            return "unknown"

    except Exception as e:
        logger.error(f"Error determining calc type: {str(e)}")
        return "unknown"

# --- Gate Management Endpoints (SQLite) ---

@app.get("/admin/gates")
def get_all_gates():
    """Get all gates from SQLite Gate table"""
    try:
        conn = get_logistic_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT [Gate ID], [Gate Name], [Branch], [Gate Price] FROM Gate")
        rows = cursor.fetchall()
        
        gates = []
        for row in rows:
            gate_id = row[0]
            calc_type = determine_calculation_type_sql(gate_id)
            
            gates.append({
                "gate_id": gate_id,
                "gate_name": row[1],
                "branch": row[2],
                "price": float(row[3]) if row[3] is not None else None,
                "calculation_type": calc_type
            })
        
        conn.close()
        return {"gates": gates}
    except Exception as e:
        logger.error(f"Error loading gates: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error loading gates: {str(e)}")

@app.post("/admin/gates")
def save_gate(gate_data: GateData):
    """Add or update a gate in SQLite"""
    try:
        conn = get_logistic_connection()
        cursor = conn.cursor()

        if gate_data.original_gate_name:
            # Update
            cursor.execute("""
                UPDATE Gate 
                SET [Gate Name] = ?, [Branch] = ?, [Gate Price] = ?
                WHERE [Gate Name] = ?
            """, (gate_data.gate_name, gate_data.branch, gate_data.price, gate_data.original_gate_name))
        else:
            # Insert (Auto-increment handles ID usually, but we can rely on schema)
            cursor.execute("""
                INSERT INTO Gate ([Gate Name], [Branch], [Gate Price])
                VALUES (?, ?, ?)
            """, (gate_data.gate_name, gate_data.branch, gate_data.price))
        
        conn.commit()
        conn.close()
        return {"message": "Gate saved successfully"}
    
    except Exception as e:
        logger.error(f"Error saving gate: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error saving gate: {str(e)}")

@app.delete("/admin/gates/{gate_id}")
def delete_gate(gate_id: int):
    """Delete a gate and its associated pricing from SQLite"""
    try:
        conn = get_logistic_connection()
        cursor = conn.cursor()
        
        # Enable foreign keys support if needed, or just manual delete
        cursor.execute("DELETE FROM Item_Pricing WHERE [Gate ID] = ?", (gate_id,))
        cursor.execute("DELETE FROM Gate WHERE [Gate ID] = ?", (gate_id,))
        
        if cursor.rowcount == 0:
             conn.close()
             raise HTTPException(status_code=404, detail="Gate not found")

        conn.commit()
        conn.close()
        return {"message": f"Gate {gate_id} deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting gate: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting gate: {str(e)}")

# --- Item Pricing Management Endpoints (SQLite) ---

@app.get("/admin/item-pricing/{gate_id}")
def get_item_pricing(gate_id: int):
    """Get all items for a specific Gate ID from SQLite"""
    try:
        conn = get_logistic_connection()
        cursor = conn.cursor()
        
        query = """
            SELECT [Pricing ID], [Item ID], [Item Name], [Is Active], [Principal], 
                   [Brand], [UOM], [Purchase Weight], [Transportation Cost]
            FROM Item_Pricing 
            WHERE [Gate ID] = ?
        """
        cursor.execute(query, (gate_id,))
        rows = cursor.fetchall()
        
        items = []
        for row in rows:
            items.append({
                "pricing_id": row[0],
                "item_code": row[1],
                "item_name": row[2],
                "is_active": row[3],
                "principal": row[4],
                "brand": row[5],
                "uom": row[6],
                "purchase_weight": row[7],
                "transportation_cost": row[8]
            })
        
        conn.close()
        return {"items": items, "gate_id": gate_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading items: {str(e)}")

@app.post("/admin/item-pricing")
def save_item_pricing(item_data: ItemPricingData):
    """Add or update an item pricing record in SQLite"""
    try:
        conn = get_logistic_connection()
        cursor = conn.cursor()

        # Check existing using Gate ID + Item Code
        query_check = "SELECT [Pricing ID] FROM Item_Pricing WHERE [Gate ID] = ? AND [Item ID] = ?"
        cursor.execute(query_check, (item_data.gate_id, item_data.original_item_code or item_data.item_code))
        existing = cursor.fetchone()

        if existing:
            # Update
            update_query = """
                UPDATE Item_Pricing
                SET [Item ID] = ?, [Item Name] = ?, [Is Active] = ?, [Principal] = ?,
                    [Brand] = ?, [UOM] = ?, [Purchase Weight] = ?, [Transportation Cost] = ?
                WHERE [Pricing ID] = ?
            """
            cursor.execute(update_query, (
                item_data.item_code, item_data.item_name, item_data.is_active,
                item_data.principal, item_data.brand, item_data.uom,
                item_data.purchase_weight, item_data.transportation_cost,
                existing[0]
            ))
        else:
            # Insert
            insert_query = """
                INSERT INTO Item_Pricing 
                ([Gate ID], [Item ID], [Item Name], [Is Active], [Principal],
                 [Brand], [UOM], [Purchase Weight], [Transportation Cost])
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            cursor.execute(insert_query, (
                item_data.gate_id, item_data.item_code, item_data.item_name,
                item_data.is_active, item_data.principal, item_data.brand, 
                item_data.uom, item_data.purchase_weight, item_data.transportation_cost
            ))

        conn.commit()
        conn.close()
        return {"message": "Item saved successfully"}
    except Exception as e:
        logger.error(f"Error saving item: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error saving item: {str(e)}")

@app.delete("/admin/item-pricing/{gate_id}/{item_code}")
def delete_item_pricing(gate_id: int, item_code: str):
    """Delete an item pricing record from SQLite"""
    try:
        conn = get_logistic_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM Item_Pricing WHERE [Gate ID] = ? AND [Item ID] = ?", (gate_id, item_code))
        
        if cursor.rowcount == 0:
            conn.close()
            raise HTTPException(status_code=404, detail="Item not found")
            
        conn.commit()
        conn.close()
        return {"message": "Item deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting item: {str(e)}")

# --- Calculation & Main Endpoints ---

@app.get("/branches")
def get_branches():
    """Get list of gates (Alias for admin/gates)"""
    return get_all_gates()

@app.post("/calculate-with-gate")
def calculate_with_gate(pick_id: str, gate_name: str, manual_total_price: Optional[float] = None):
    """Calculate prices: Joins SQL Server (Pick Data) and SQLite (Gate Data)"""
    try:
        # 1. Get Pick Details from SQL Server (DWBI)
        try:
            conn_dwbi = get_dwbi_connection()
            cursor_dwbi = conn_dwbi.cursor()
            cursor_dwbi.execute("""
                SELECT ItemCode, Dscription, Quantity, UomCode, ItemWeight
                FROM PG_PickDetail WHERE ID = ? ORDER BY ItemCode
            """, (pick_id,))
            pick_rows = cursor_dwbi.fetchall()
            conn_dwbi.close()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error fetching pick details from DWBI: {str(e)}")
        
        if not pick_rows:
            raise HTTPException(status_code=404, detail="No products found for this Pick ID")
        
        # 2. Get Gate Configuration from SQLite (logistic.db)
        try:
            conn_log = get_logistic_connection()
            cursor_log = conn_log.cursor()
            cursor_log.execute("SELECT [Gate ID], [Branch], [Gate Price] FROM Gate WHERE [Gate Name] = ?", (gate_name,))
            gate_row = cursor_log.fetchone()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error fetching gate config: {str(e)}")
        
        if not gate_row:
            if 'conn_log' in locals(): conn_log.close()
            raise HTTPException(status_code=404, detail=f"Gate {gate_name} not found")
            
        gate_id, branch, gate_price = gate_row[0], gate_row[1], float(gate_row[2] or 0)
        
        # 3. Get Item Pricing from SQLite
        cursor_log.execute("""
            SELECT [Item ID], [Transportation Cost] 
            FROM Item_Pricing 
            WHERE [Gate ID] = ?
        """, (gate_id,))
        pricing_rows = cursor_log.fetchall()
        conn_log.close()
        
        # 4. Process Pricing Logic
        item_pricing = {}
        has_ton = False
        has_number = False
        
        for row in pricing_rows:
            i_code = row[0]
            t_cost = str(row[1]).strip()
            
            if t_cost.lower() == 'ton':
                item_pricing[i_code] = {'type': 'ton', 'value': None}
                has_ton = True
            else:
                try:
                    val = float(t_cost)
                    item_pricing[i_code] = {'type': 'direct', 'value': val}
                    has_number = True
                except:
                    item_pricing[i_code] = {'type': 'unknown', 'value': None}

        # Determine Calculation Type
        calc_type = "unknown"
        if has_number and not has_ton:
            calc_type = "direct_pricing"
        elif has_ton:
            calc_type = "gate_pricing"

        calculated_products = []
        total_price = 0.0
        estimated_total_price = 0.0

        if calc_type == "gate_pricing":
            ton_items = []
            direct_items = []
            ton_cost_total = 0.0
            
            for row in pick_rows:
                # Note: PyODBC rows are accessed by index
                item_data = {
                    "code": row[0] if row[0] else "",
                    "name": row[1] if row[1] else "",
                    "quantity": float(row[2]) if row[2] else 0.0,
                    "uom": row[3] if row[3] else "",
                    "weight": float(row[4]) if row[4] else 0.0,
                }
                
                p_info = item_pricing.get(item_data['code'], {})
                p_type = p_info.get('type', 'ton')
                p_val = p_info.get('value', 0.0)
                
                if p_type == 'direct':
                    estimated_total_price += (item_data['quantity'] * p_val)
                    item_data['standard_unit_price'] = p_val
                    direct_items.append(item_data)
                else:
                    # Weight based cost
                    cost = item_data['weight'] * gate_price
                    estimated_total_price += cost
                    ton_cost_total += cost
                    item_data['price'] = cost
                    ton_items.append(item_data)

            # Manual Price Logic
            direct_unit_price = 0.0
            if manual_total_price is not None:
                remainder = manual_total_price - ton_cost_total
                total_direct_qty = sum(item['quantity'] for item in direct_items)
                if total_direct_qty > 0:
                    direct_unit_price = remainder / total_direct_qty
                total_price = manual_total_price
            else:
                total_price = estimated_total_price

            # Build Result
            for item in ton_items:
                calculated_products.append({
                    **item,
                    "calculation_type": "weight",
                    "price_per_one": None,
                    "price": item['price'] 
                })
            
            for item in direct_items:
                final_unit_price = direct_unit_price if manual_total_price is not None else item['standard_unit_price']
                final_item_price = item['quantity'] * final_unit_price
                
                calculated_products.append({
                    **item,
                    "calculation_type": "direct_split" if manual_total_price else "direct",
                    "price_per_one": final_unit_price,
                    "price": final_item_price
                })

        elif calc_type == "direct_pricing":
            for row in pick_rows:
                item_code = row[0] if row[0] else ""
                pricing_info = item_pricing.get(item_code, {})
                
                quantity = float(row[2]) if row[2] else 0.0
                weight = float(row[4]) if row[4] else 0.0
                
                price_per_one = pricing_info.get('value', 0.0) or 0.0
                price = quantity * price_per_one
                
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

        # Sort by name
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
        logger.error(f"Calculation error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Calculation error: {str(e)}")

# --- Standard Lookups (SQL Server - DWBI) ---

@app.get("/pick-ids")
def get_pick_ids():
    """Get unique Pick IDs from SQL Server"""
    try:
        conn = get_dwbi_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT ID FROM PG_PickDetail WHERE ID IS NOT NULL ORDER BY ID DESC")
        rows = cursor.fetchall()
        pick_ids = [row[0] for row in rows]
        conn.close()
        return {"pick_ids": pick_ids}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/products/{pick_id}")
def get_products_by_pick_id(pick_id: str):
    """Get products from SQL Server"""
    try:
        conn = get_dwbi_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT ItemCode, Dscription, Quantity, UomCode, ItemWeight, CardName, PickDate, VANCode, Status
            FROM PG_PickDetail WHERE ID = ? ORDER BY ItemCode
        """, (pick_id,))
        rows = cursor.fetchall()
        
        if not rows:
            conn.close()
            raise HTTPException(status_code=404, detail="No products found")
        
        products = []
        total_weight = 0.0
        pick_info = {
            "card_name": rows[0][5] or "",
            "pick_date": rows[0][6].strftime("%Y-%m-%d") if rows[0][6] else "",
            "van_code": rows[0][7] or "",
            "status": rows[0][8] or ""
        }
        
        for row in rows:
            weight = float(row[4]) if row[4] else 0.0
            total_weight += weight
            products.append({
                "item_code": row[0] or "",
                "description": row[1] or "",
                "quantity": float(row[2]) if row[2] else 0.0,
                "uom": row[3] or "",
                "item_weight": weight
            })
        
        conn.close()
        return {"products": products, "total_weight": round(total_weight, 2), "pick_info": pick_info}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)