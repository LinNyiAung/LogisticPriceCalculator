import logging
import pyodbc
import sqlite3
import json
import datetime
from fastapi import FastAPI, HTTPException, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
import os
import io
import openpyxl
from openpyxl.styles import Font, PatternFill

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
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Gate (
                [Gate ID] INTEGER PRIMARY KEY,
                [Gate Name] TEXT,
                [From] TEXT,
                [To] TEXT,
                [Gate Price] REAL
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Item_Pricing (
                [Pricing ID] INTEGER PRIMARY KEY,
                [Gate ID] INTEGER,
                [Item ID] TEXT,
                [Item Name] TEXT,
                [Principal] TEXT,
                [Brand] TEXT,
                [Transportation Cost] TEXT,
                FOREIGN KEY([Gate ID]) REFERENCES Gate([Gate ID])
            )
        """)

        # Calculation History Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Calculation_History (
                [id] INTEGER PRIMARY KEY AUTOINCREMENT,
                [created_at] TEXT,
                [name] TEXT,
                [gate_name] TEXT,
                [from_loc] TEXT,
                [to_loc] TEXT,
                [pick_ids] TEXT, -- Stored as JSON string
                [manual_total_price] REAL,
                [additional_charges] REAL,
                [final_total_price] REAL
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
    from_loc: str  
    to_loc: str    
    price: Optional[float] = None
    original_gate_name: Optional[str] = None

class ItemPricingData(BaseModel):
    pricing_id: Optional[int] = None
    gate_id: int
    item_code: str
    item_name: str
    principal: Optional[str] = ""
    brand: Optional[str] = ""
    transportation_cost: str
    original_item_code: Optional[str] = None

# UPDATED: Added 'id' for updates
class CalculationSaveRequest(BaseModel):
    id: Optional[int] = None
    name: str
    gate_name: str
    from_loc: str
    to_loc: str
    pick_ids: List[str]
    manual_total_price: Optional[float] = None
    additional_charges: Optional[float] = 0.0
    final_total_price: float

# --- Helper Functions ---

def determine_calculation_type_sql(gate_id):
    """
    Determines calculation type based on Gate Price.
    If Gate Price exists and > 0 -> gate_pricing
    Else -> direct_pricing
    """
    try:
        conn = get_logistic_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT [Gate Price] FROM Gate WHERE [Gate ID] = ?", (gate_id,))
        row = cursor.fetchone()
        conn.close()

        if row and row[0] is not None:
            try:
                price = float(row[0])
                if price > 0:
                    return "gate_pricing"
            except ValueError:
                pass
        
        return "direct_pricing"

    except Exception as e:
        logger.error(f"Error determining calc type: {str(e)}")
        return "unknown"

# --- Calculation History Endpoints ---

@app.post("/history/save")
def save_calculation(data: CalculationSaveRequest):
    try:
        conn = get_logistic_connection()
        cursor = conn.cursor()
        
        pick_ids_json = json.dumps(data.pick_ids)
        created_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # UPDATED LOGIC: Update if ID is present, else Insert
        if data.id:
            # Check existence
            cursor.execute("SELECT id FROM Calculation_History WHERE id = ?", (data.id,))
            if not cursor.fetchone():
                conn.close()
                raise HTTPException(status_code=404, detail="Record to update not found")

            cursor.execute("""
                UPDATE Calculation_History 
                SET created_at = ?, name = ?, gate_name = ?, from_loc = ?, to_loc = ?, 
                    pick_ids = ?, manual_total_price = ?, additional_charges = ?, final_total_price = ?
                WHERE id = ?
            """, (
                created_at, data.name, data.gate_name, data.from_loc, data.to_loc,
                pick_ids_json, data.manual_total_price, data.additional_charges, 
                data.final_total_price, data.id
            ))
            message = "Calculation updated successfully"
        else:
            cursor.execute("""
                INSERT INTO Calculation_History 
                ([created_at], [name], [gate_name], [from_loc], [to_loc], 
                 [pick_ids], [manual_total_price], [additional_charges], [final_total_price])
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                created_at, data.name, data.gate_name, data.from_loc, data.to_loc,
                pick_ids_json, data.manual_total_price, data.additional_charges, data.final_total_price
            ))
            message = "Calculation saved successfully"
        
        conn.commit()
        conn.close()
        return {"message": message}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving history: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error saving history: {str(e)}")

@app.get("/history")
def get_history():
    try:
        conn = get_logistic_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM Calculation_History ORDER BY id DESC")
        rows = cursor.fetchall()
        
        history = []
        for row in rows:
            history.append({
                "id": row[0],
                "created_at": row[1],
                "name": row[2],
                "gate_name": row[3],
                "from_loc": row[4],
                "to_loc": row[5],
                "pick_ids": json.loads(row[6]), # Convert JSON string back to list
                "manual_total_price": row[7],
                "additional_charges": row[8],
                "final_total_price": row[9]
            })
            
        conn.close()
        return {"history": history}
    except Exception as e:
        logger.error(f"Error loading history: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error loading history: {str(e)}")

@app.delete("/history/{record_id}")
def delete_history_item(record_id: int):
    try:
        conn = get_logistic_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM Calculation_History WHERE id = ?", (record_id,))
        if cursor.rowcount == 0:
            conn.close()
            raise HTTPException(status_code=404, detail="Record not found")
            
        conn.commit()
        conn.close()
        return {"message": "Record deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting record: {str(e)}")

# --- Excel Export/Import Endpoints ---

@app.get("/admin/item-pricing/export/{gate_id}")
def export_item_pricing_excel(gate_id: int):
    try:
        conn = get_logistic_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT [Gate Name], [From], [To] FROM Gate WHERE [Gate ID] = ?", (gate_id,))
        gate_row = cursor.fetchone()
        
        if not gate_row:
            conn.close()
            raise HTTPException(status_code=404, detail="Gate not found")
        
        gate_name = gate_row[0]
        from_loc = gate_row[1] or ""
        to_loc = gate_row[2] or ""
        
        query = """
            SELECT [Item ID], [Item Name], [Principal], [Brand], [Transportation Cost]
            FROM Item_Pricing 
            WHERE [Gate ID] = ?
            ORDER BY [Item ID]
        """
        cursor.execute(query, (gate_id,))
        rows = cursor.fetchall()
        conn.close()
        
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Item Pricing"
        
        ws['A1'] = f"Gate: {gate_name} ({from_loc} -> {to_loc})"
        ws['A1'].font = Font(bold=True, size=14)
        
        headers = ['Item Code', 'Item Name', 'Principal', 'Brand', 'Transportation Cost']
        header_fill = PatternFill(start_color='4472C4', end_color='4472C4', fill_type='solid')
        header_font = Font(bold=True, color='FFFFFF')
        
        for col_num, header in enumerate(headers, 1):
            cell = ws.cell(row=3, column=col_num)
            cell.value = header
            cell.fill = header_fill
            cell.font = header_font
        
        for row_num, row_data in enumerate(rows, 4):
            for col_num, value in enumerate(row_data, 1):
                ws.cell(row=row_num, column=col_num, value=value)
        
        for col in ws.columns:
            max_length = 0
            col_letter = col[0].column_letter
            for cell in col:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            ws.column_dimensions[col_letter].width = adjusted_width
        
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        
        filename = f"item_pricing_{gate_name.replace(' ', '_')}.xlsx"
        
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting Excel: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error exporting: {str(e)}")

@app.post("/admin/item-pricing/import/{gate_id}")
async def import_item_pricing_excel(gate_id: int, file: UploadFile = File(...)):
    try:
        contents = await file.read()
        wb = openpyxl.load_workbook(io.BytesIO(contents))
        ws = wb.active
        
        conn = get_logistic_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT [Item ID] FROM Item_Pricing WHERE [Gate ID] = ?", (gate_id,))
        existing_items = {row[0] for row in cursor.fetchall()}
        
        updated_items = set()
        updates_made = 0
        inserts_made = 0
        
        for row in ws.iter_rows(min_row=4, values_only=True):
            if not row[0]:
                continue
            
            item_code = str(row[0]).strip()
            item_name = str(row[1]) if row[1] else ""
            principal = str(row[2]) if row[2] else ""
            brand = str(row[3]) if row[3] else ""
            transportation_cost = str(row[4]) if row[4] else "Ton"
            
            updated_items.add(item_code)
            
            if item_code in existing_items:
                cursor.execute("""
                    UPDATE Item_Pricing
                    SET [Item Name] = ?, [Principal] = ?, [Brand] = ?, [Transportation Cost] = ?
                    WHERE [Gate ID] = ? AND [Item ID] = ?
                """, (item_name, principal, brand, transportation_cost, gate_id, item_code))
                updates_made += 1
            else:
                cursor.execute("""
                    INSERT INTO Item_Pricing 
                    ([Gate ID], [Item ID], [Item Name], [Principal], [Brand], [Transportation Cost])
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (gate_id, item_code, item_name, principal, brand, transportation_cost))
                inserts_made += 1
        
        items_to_delete = existing_items - updated_items
        deletes_made = 0
        for item_code in items_to_delete:
            cursor.execute("""
                DELETE FROM Item_Pricing 
                WHERE [Gate ID] = ? AND [Item ID] = ?
            """, (gate_id, item_code))
            deletes_made += 1
        
        conn.commit()
        conn.close()
        
        return {
            "message": "Import completed successfully",
            "updates": updates_made,
            "inserts": inserts_made,
            "deletes": deletes_made
        }
        
    except Exception as e:
        logger.error(f"Error importing Excel: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error importing: {str(e)}")

# --- Gate Management Endpoints (SQLite) ---

@app.get("/admin/gates")
def get_all_gates():
    try:
        conn = get_logistic_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT [Gate ID], [Gate Name], [From], [To], [Gate Price] FROM Gate")
        rows = cursor.fetchall()
        
        gates = []
        for row in rows:
            gate_id = row[0]
            calc_type = determine_calculation_type_sql(gate_id)
            
            gates.append({
                "gate_id": gate_id,
                "gate_name": row[1],
                "from_loc": row[2], 
                "to_loc": row[3],   
                "price": float(row[4]) if row[4] is not None else None,
                "calculation_type": calc_type
            })
        
        conn.close()
        return {"gates": gates}
    except Exception as e:
        logger.error(f"Error loading gates: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error loading gates: {str(e)}")

@app.post("/admin/gates")
def save_gate(gate_data: GateData):
    try:
        conn = get_logistic_connection()
        cursor = conn.cursor()

        if gate_data.original_gate_name:
            cursor.execute("""
                UPDATE Gate 
                SET [Gate Name] = ?, [From] = ?, [To] = ?, [Gate Price] = ?
                WHERE [Gate Name] = ?
            """, (gate_data.gate_name, gate_data.from_loc, gate_data.to_loc, 
                  gate_data.price, gate_data.original_gate_name))
        else:
            cursor.execute("""
                INSERT INTO Gate ([Gate Name], [From], [To], [Gate Price])
                VALUES (?, ?, ?, ?)
            """, (gate_data.gate_name, gate_data.from_loc, gate_data.to_loc, gate_data.price))
        
        conn.commit()
        conn.close()
        return {"message": "Gate saved successfully"}
    
    except Exception as e:
        logger.error(f"Error saving gate: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error saving gate: {str(e)}")

@app.delete("/admin/gates/{gate_id}")
def delete_gate(gate_id: int):
    try:
        conn = get_logistic_connection()
        cursor = conn.cursor()
        
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
    try:
        conn = get_logistic_connection()
        cursor = conn.cursor()
        
        query = """
            SELECT [Pricing ID], [Item ID], [Item Name], [Principal], 
                   [Brand], [Transportation Cost]
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
                "principal": row[3],
                "brand": row[4],
                "transportation_cost": row[5]
            })
        
        conn.close()
        return {"items": items, "gate_id": gate_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading items: {str(e)}")

@app.post("/admin/item-pricing")
def save_item_pricing(item_data: ItemPricingData):
    try:
        conn = get_logistic_connection()
        cursor = conn.cursor()

        query_check = "SELECT [Pricing ID] FROM Item_Pricing WHERE [Gate ID] = ? AND [Item ID] = ?"
        cursor.execute(query_check, (item_data.gate_id, item_data.original_item_code or item_data.item_code))
        existing = cursor.fetchone()

        if existing:
            update_query = """
                UPDATE Item_Pricing
                SET [Item ID] = ?, [Item Name] = ?, [Principal] = ?,
                    [Brand] = ?, [Transportation Cost] = ?
                WHERE [Pricing ID] = ?
            """
            cursor.execute(update_query, (
                item_data.item_code, item_data.item_name,
                item_data.principal, item_data.brand,
                item_data.transportation_cost,
                existing[0]
            ))
        else:
            insert_query = """
                INSERT INTO Item_Pricing 
                ([Gate ID], [Item ID], [Item Name], [Principal],
                 [Brand], [Transportation Cost])
                VALUES (?, ?, ?, ?, ?, ?)
            """
            cursor.execute(insert_query, (
                item_data.gate_id, item_data.item_code, item_data.item_name,
                item_data.principal, item_data.brand, item_data.transportation_cost
            ))

        conn.commit()
        conn.close()
        return {"message": "Item saved successfully"}
    except Exception as e:
        logger.error(f"Error saving item: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error saving item: {str(e)}")

@app.delete("/admin/item-pricing/{gate_id}/{item_code}")
def delete_item_pricing(gate_id: int, item_code: str):
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

@app.get("/locations/from")
def get_from_locations():
    try:
        conn = get_logistic_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT [From] FROM Gate WHERE [From] IS NOT NULL ORDER BY [From]")
        rows = cursor.fetchall()
        locations = [row[0] for row in rows if row[0]]
        conn.close()
        return {"locations": locations}
    except Exception as e:
        logger.error(f"Error loading from locations: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error loading from locations: {str(e)}")

@app.get("/locations/to")
def get_to_locations(from_loc: Optional[str] = None):
    try:
        conn = get_logistic_connection()
        cursor = conn.cursor()
        
        if from_loc:
            cursor.execute("SELECT DISTINCT [To] FROM Gate WHERE [From] = ? AND [To] IS NOT NULL ORDER BY [To]", (from_loc,))
        else:
            cursor.execute("SELECT DISTINCT [To] FROM Gate WHERE [To] IS NOT NULL ORDER BY [To]")
            
        rows = cursor.fetchall()
        locations = [row[0] for row in rows if row[0]]
        conn.close()
        return {"locations": locations}
    except Exception as e:
        logger.error(f"Error loading to locations: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error loading to locations: {str(e)}")

@app.post("/calculate-with-gate")
def calculate_with_gate(
    gate_name: str, 
    pick_ids: List[str] = Query(...), 
    manual_total_price: Optional[float] = None,
    additional_charges: Optional[float] = 0.0
):
    """Calculate prices for multiple Pick IDs"""
    try:
        add_charges = float(additional_charges) if additional_charges is not None else 0.0

        if not pick_ids:
            raise HTTPException(status_code=400, detail="No Pick IDs provided")

        # 1. Get Pick Data from DWBI for ALL IDs
        try:
            conn_dwbi = get_dwbi_connection()
            cursor_dwbi = conn_dwbi.cursor()
            
            # Prepare query for multiple IDs
            placeholders = ','.join('?' * len(pick_ids))
            query = f"""
                SELECT ItemCode, Dscription, Quantity, UomCode, ItemWeight
                FROM PG_PickDetail 
                WHERE ID IN ({placeholders}) 
                ORDER BY ItemCode
            """
            cursor_dwbi.execute(query, pick_ids)
            pick_rows = cursor_dwbi.fetchall()
            conn_dwbi.close()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error fetching pick details: {str(e)}")
        
        if not pick_rows:
            raise HTTPException(status_code=404, detail="No products found for the selected Pick IDs")
        
        # 2. Get Gate Data
        try:
            conn_log = get_logistic_connection()
            cursor_log = conn_log.cursor()
            cursor_log.execute("SELECT [Gate ID], [From], [To], [Gate Price] FROM Gate WHERE [Gate Name] = ?", (gate_name,))
            gate_row = cursor_log.fetchone()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error fetching gate config: {str(e)}")
        
        if not gate_row:
            if 'conn_log' in locals(): conn_log.close()
            raise HTTPException(status_code=404, detail=f"Gate {gate_name} not found")
            
        gate_id = gate_row[0]
        from_loc = gate_row[1]
        to_loc = gate_row[2]
        gate_price = float(gate_row[3] or 0)
        
        # 3. Get Item Pricing
        # UPDATED query to fetch only ID and Cost (Weight/Active were removed from table)
        cursor_log.execute("""
            SELECT [Item ID], [Transportation Cost] 
            FROM Item_Pricing 
            WHERE [Gate ID] = ?
        """, (gate_id,))
        pricing_rows = cursor_log.fetchall()
        conn_log.close()
        
        item_pricing = {}
        for row in pricing_rows:
            i_code = row[0]
            t_cost = str(row[1]).strip()
            
            if t_cost.lower() == 'ton':
                item_pricing[i_code] = {'type': 'ton', 'value': None}
            else:
                try:
                    val = float(t_cost)
                    item_pricing[i_code] = {'type': 'direct', 'value': val}
                except:
                    item_pricing[i_code] = {'type': 'unknown', 'value': None}

        # Determine type based on gate_price
        if gate_price > 0:
            calc_type = "gate_pricing"
        else:
            calc_type = "direct_pricing"

        calculated_products = []
        total_price = 0.0
        estimated_total_price = 0.0

        if calc_type == "gate_pricing":
            ton_items = []
            direct_items = []
            ton_cost_total = 0.0
            
            for row in pick_rows:
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
                    cost = item_data['weight'] * gate_price
                    estimated_total_price += cost
                    ton_cost_total += cost
                    item_data['price'] = cost
                    ton_items.append(item_data)

            direct_unit_price = 0.0
            if manual_total_price is not None:
                remainder = manual_total_price - ton_cost_total
                total_direct_qty = sum(item['quantity'] for item in direct_items)
                if total_direct_qty > 0:
                    direct_unit_price = remainder / total_direct_qty
                total_price = manual_total_price
            else:
                total_price = estimated_total_price

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

        calculated_products.sort(key=lambda x: x['name'])
        
        total_price += add_charges
        estimated_total_price += add_charges
        
        return {
            "calculation_type": calc_type,
            "gate_name": gate_name,
            "from_loc": from_loc,
            "to_loc": to_loc,
            "gate_price": gate_price,
            "additional_charges": add_charges,
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

# NEW: Aggregated endpoint for multiple IDs
@app.get("/products-by-ids")
def get_products_by_pick_ids(pick_ids: List[str] = Query(...)):
    """Get aggregated products for multiple Pick IDs"""
    try:
        if not pick_ids:
            return {"products": [], "total_weight": 0}

        conn = get_dwbi_connection()
        cursor = conn.cursor()
        
        placeholders = ','.join('?' * len(pick_ids))
        query = f"""
            SELECT ItemCode, Dscription, Quantity, UomCode, ItemWeight
            FROM PG_PickDetail 
            WHERE ID IN ({placeholders}) 
            ORDER BY ItemCode
        """
        
        cursor.execute(query, pick_ids)
        rows = cursor.fetchall()
        
        products = []
        total_weight = 0.0
        
        for row in rows:
            weight = float(row[4]) if row[4] else 0.0
            total_weight += weight
            products.append({
                "code": row[0] or "",
                "name": row[1] or "",
                "quantity": float(row[2]) if row[2] else 0.0,
                "uom": row[3] or "",
                "weight": weight
            })
        
        conn.close()
        return {"products": products, "total_weight": round(total_weight, 2)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

# Keep single ID version for backward compatibility if needed, 
# but the frontend will use the multi-version.
@app.get("/products/{pick_id}")
def get_products_by_pick_id(pick_id: str):
    """Get products from SQL Server (Single ID)"""
    try:
        conn = get_dwbi_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT ItemCode, Dscription, Quantity, UomCode, ItemWeight
            FROM PG_PickDetail WHERE ID = ? ORDER BY ItemCode
        """, (pick_id,))
        rows = cursor.fetchall()
        
        if not rows:
            conn.close()
            raise HTTPException(status_code=404, detail="No products found")
        
        products = []
        total_weight = 0.0
        
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
        return {"products": products, "total_weight": round(total_weight, 2)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)