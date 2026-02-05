import logging
import pyodbc
import sqlite3
import json
import datetime
from fastapi import FastAPI, HTTPException, UploadFile, File, Query, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
import os
import io
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.context import CryptContext
from jose import JWTError, jwt

# --- Auth Configuration ---
SECRET_KEY = "CHANGE_THIS_TO_A_SUPER_SECRET_KEY"  # IMPORTANT: Change this!
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 300 # 5 hours expiration

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

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
        
        # Gate table uses "Cost Per Unit"
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Gate (
                [Gate ID] INTEGER PRIMARY KEY,
                [Gate Name] TEXT,
                [From] TEXT,
                [To] TEXT,
                [UOM] TEXT,
                [Unit] INTEGER,
                [Cost Per Unit] REAL
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
                [gate_name] TEXT,
                [from_loc] TEXT,
                [to_loc] TEXT,
                [pick_ids] TEXT, -- Stored as JSON string
                [manual_total_cost] REAL,
                [additional_charges] REAL,
                [final_total_cost] REAL
            )
        """)
        
        # --- User Table ---
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Users (
                username TEXT PRIMARY KEY,
                hashed_password TEXT,
                role TEXT
            )
        """)
        
        # Create default account user if not exists
        cursor.execute("SELECT * FROM Users WHERE username = 'account'")
        if not cursor.fetchone():
            default_pw = pwd_context.hash("account123") 
            cursor.execute("INSERT INTO Users (username, hashed_password, role) VALUES (?, ?, ?)", 
                          ('account', default_pw, 'account'))
            
        # Create default logistic user if not exists
        cursor.execute("SELECT * FROM Users WHERE username = 'logistic'")
        if not cursor.fetchone():
            log_pw = pwd_context.hash("log123")
            cursor.execute("INSERT INTO Users (username, hashed_password, role) VALUES (?, ?, ?)", 
                          ('logistic', log_pw, 'logistic'))
            
        # --- NEW: Create default admin user ---
        cursor.execute("SELECT * FROM Users WHERE username = 'admin'")
        if not cursor.fetchone():
            admin_pw = pwd_context.hash("admin123")
            cursor.execute("INSERT INTO Users (username, hashed_password, role) VALUES (?, ?, ?)", 
                          ('admin', admin_pw, 'admin'))
        
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
    uom: Optional[str] = None       
    unit: Optional[int] = None      
    cost_per_unit: Optional[float] = None 
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

class CalculationSaveRequest(BaseModel):
    id: Optional[int] = None
    gate_name: str
    from_loc: str
    to_loc: str
    pick_ids: List[str]
    manual_total_cost: Optional[float] = None
    additional_charges: Optional[float] = 0.0
    final_total_cost: float

# --- User Management Models ---

class UserCreate(BaseModel):
    username: str
    password: str
    role: str

class UserUpdate(BaseModel):
    password: Optional[str] = None
    role: Optional[str] = None

class UserResponse(BaseModel):
    username: str
    role: str

# --- Auth Models & Helpers ---

class Token(BaseModel):
    access_token: str
    token_type: str
    role: str
    username: str
    
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role")
        if username is None:
            raise credentials_exception
        return {"username": username, "role": role}
    except JWTError:
        raise credentials_exception

async def get_account_user(current_user: dict = Depends(get_current_user)):
    # Account features are accessible by 'account' OR 'admin'
    if current_user["role"] not in ["account", "admin"]:
        raise HTTPException(status_code=403, detail="Privileged access required (Account or Admin)")
    return current_user

async def get_admin_user(current_user: dict = Depends(get_current_user)):
    # Admin features are ONLY for 'admin'
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return current_user

# --- Helper Functions ---

def determine_calculation_type_sql(gate_id):
    """
    Determines calculation type based on Cost Per Unit.
    If Cost Per Unit exists and > 0 -> gate_pricing
    Else -> direct_pricing
    """
    try:
        conn = get_logistic_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT [Cost Per Unit] FROM Gate WHERE [Gate ID] = ?", (gate_id,))
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

def _perform_calculation_logic(gate_name, pick_ids, manual_total_cost=None, additional_charges=0.0):
    add_charges = float(additional_charges) if additional_charges is not None else 0.0

    # 1. Get Pick Data from DWBI
    try:
        conn_dwbi = get_dwbi_connection()
        cursor_dwbi = conn_dwbi.cursor()
        
        placeholders = ','.join('?' * len(pick_ids))
        query = f"""
            SELECT ItemCode, MAX(Dscription), SUM(Quantity), MAX(UomCode), SUM(ItemWeight)
            FROM PG_PickDetail 
            WHERE ID IN ({placeholders}) 
            GROUP BY ItemCode
            ORDER BY ItemCode
        """
        cursor_dwbi.execute(query, pick_ids)
        pick_rows = cursor_dwbi.fetchall()
        conn_dwbi.close()
    except Exception as e:
        raise Exception(f"Error fetching pick details: {str(e)}")
    
    if not pick_rows:
        raise Exception("No products found for the selected Pick IDs")
    
    # 2. Get Gate Data
    try:
        conn_log = get_logistic_connection()
        cursor_log = conn_log.cursor()
        cursor_log.execute("SELECT [Gate ID], [From], [To], [Cost Per Unit] FROM Gate WHERE [Gate Name] = ?", (gate_name,))
        gate_row = cursor_log.fetchone()
    except Exception as e:
        raise Exception(f"Error fetching gate config: {str(e)}")
    
    if not gate_row:
        if 'conn_log' in locals(): conn_log.close()
        raise Exception(f"Gate {gate_name} not found")
        
    gate_id = gate_row[0]
    from_loc = gate_row[1]
    to_loc = gate_row[2]
    cost_per_unit = float(gate_row[3] or 0)
    
    # 3. Get Item Pricing
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

    if cost_per_unit > 0:
        calc_type = "gate_pricing"
    else:
        calc_type = "direct_pricing"

    calculated_products = []
    total_cost = 0.0
    estimated_total_cost = 0.0

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
                estimated_total_cost += (item_data['quantity'] * p_val)
                item_data['standard_unit_cost'] = p_val
                direct_items.append(item_data)
            else:
                cost = item_data['weight'] * cost_per_unit
                estimated_total_cost += cost
                ton_cost_total += cost
                item_data['total_cost'] = cost
                ton_items.append(item_data)

        direct_unit_cost = 0.0
        if manual_total_cost is not None:
            remainder = manual_total_cost - ton_cost_total
            total_direct_qty = sum(item['quantity'] for item in direct_items)
            if total_direct_qty > 0:
                direct_unit_cost = remainder / total_direct_qty
            total_cost = manual_total_cost
        else:
            total_cost = estimated_total_cost

        for item in ton_items:
            avg_unit_cost = item['total_cost'] / item['quantity'] if item['quantity'] > 0 else 0
            
            calculated_products.append({
                **item,
                "calculation_type": "weight",
                "unit_cost": avg_unit_cost, 
                "total_cost": item['total_cost'] 
            })
        
        for item in direct_items:
            final_unit_cost = direct_unit_cost if manual_total_cost is not None else item['standard_unit_cost']
            final_item_cost = item['quantity'] * final_unit_cost
            
            calculated_products.append({
                **item,
                "calculation_type": "direct_split" if manual_total_cost else "direct",
                "unit_cost": final_unit_cost,
                "total_cost": final_item_cost
            })

    elif calc_type == "direct_pricing":
        for row in pick_rows:
            item_code = row[0] if row[0] else ""
            pricing_info = item_pricing.get(item_code, {})
            
            quantity = float(row[2]) if row[2] else 0.0
            weight = float(row[4]) if row[4] else 0.0
            
            unit_cost = pricing_info.get('value', 0.0) or 0.0
            cost = quantity * unit_cost
            
            total_cost += cost
            estimated_total_cost += cost
            
            calculated_products.append({
                "code": item_code,
                "name": row[1] if row[1] else "",
                "quantity": quantity,
                "uom": row[3] if row[3] else "",
                "weight": weight,
                "calculation_type": "direct",
                "unit_cost": unit_cost,
                "total_cost": cost
            })

    calculated_products.sort(key=lambda x: x['code'])
    
    total_cost += add_charges
    estimated_total_cost += add_charges
    
    return {
        "calculation_type": calc_type,
        "gate_name": gate_name,
        "from_loc": from_loc,
        "to_loc": to_loc,
        "cost_per_unit": cost_per_unit, 
        "additional_charges": add_charges,
        "calculated_products": calculated_products,
        "total_cost": total_cost,
        "estimated_total_cost": estimated_total_cost
    }

# --- Login & Token ---

@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    conn = get_logistic_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT username, hashed_password, role FROM Users WHERE username = ?", (form_data.username,))
    user = cursor.fetchone()
    conn.close()
    
    if not user or not verify_password(form_data.password, user[1]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": user[0], "role": user[2]})
    return {"access_token": access_token, "token_type": "bearer", "role": user[2], "username": user[0]}

# --- User Management Endpoints (Admin Only) ---

@app.get("/users", response_model=List[UserResponse])
def get_all_users(user: dict = Depends(get_admin_user)):
    try:
        conn = get_logistic_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT username, role FROM Users ORDER BY username")
        rows = cursor.fetchall()
        conn.close()
        return [{"username": row[0], "role": row[1]} for row in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching users: {str(e)}")

@app.post("/users")
def create_user(user_data: UserCreate, user: dict = Depends(get_admin_user)):
    try:
        conn = get_logistic_connection()
        cursor = conn.cursor()
        
        # Check if user exists
        cursor.execute("SELECT username FROM Users WHERE username = ?", (user_data.username,))
        if cursor.fetchone():
            conn.close()
            raise HTTPException(status_code=400, detail="Username already exists")
        
        hashed_pw = pwd_context.hash(user_data.password)
        cursor.execute("INSERT INTO Users (username, hashed_password, role) VALUES (?, ?, ?)", 
                      (user_data.username, hashed_pw, user_data.role))
        
        conn.commit()
        conn.close()
        return {"message": "User created successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating user: {str(e)}")

@app.put("/users/{username}")
def update_user(username: str, user_data: UserUpdate, user: dict = Depends(get_admin_user)):
    try:
        conn = get_logistic_connection()
        cursor = conn.cursor()
        
        # Check if user exists
        cursor.execute("SELECT username FROM Users WHERE username = ?", (username,))
        if not cursor.fetchone():
            conn.close()
            raise HTTPException(status_code=404, detail="User not found")
        
        if user_data.password:
            hashed_pw = pwd_context.hash(user_data.password)
            cursor.execute("UPDATE Users SET hashed_password = ? WHERE username = ?", (hashed_pw, username))
            
        if user_data.role:
            cursor.execute("UPDATE Users SET role = ? WHERE username = ?", (user_data.role, username))
            
        conn.commit()
        conn.close()
        return {"message": "User updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating user: {str(e)}")

@app.delete("/users/{username}")
def delete_user(username: str, user: dict = Depends(get_admin_user)):
    if username == user["username"]:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
        
    try:
        conn = get_logistic_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM Users WHERE username = ?", (username,))
        if cursor.rowcount == 0:
            conn.close()
            raise HTTPException(status_code=404, detail="User not found")
            
        conn.commit()
        conn.close()
        return {"message": "User deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting user: {str(e)}")


# --- Calculation History Endpoints ---

@app.post("/history/save")
def save_calculation(data: CalculationSaveRequest, user: dict = Depends(get_current_user)):
    try:
        conn = get_logistic_connection()
        cursor = conn.cursor()
        
        pick_ids_json = json.dumps(data.pick_ids)
        created_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if data.id:
            # Check existence
            cursor.execute("SELECT id FROM Calculation_History WHERE id = ?", (data.id,))
            if not cursor.fetchone():
                conn.close()
                raise HTTPException(status_code=404, detail="Record to update not found")

            cursor.execute("""
                UPDATE Calculation_History 
                SET created_at = ?, gate_name = ?, from_loc = ?, to_loc = ?, 
                    pick_ids = ?, manual_total_cost = ?, additional_charges = ?, final_total_cost = ?
                WHERE id = ?
            """, (
                created_at, data.gate_name, data.from_loc, data.to_loc,
                pick_ids_json, data.manual_total_cost, data.additional_charges, 
                data.final_total_cost, data.id
            ))
            message = "Calculation updated successfully"
        else:
            cursor.execute("""
                INSERT INTO Calculation_History 
                ([created_at], [gate_name], [from_loc], [to_loc], 
                 [pick_ids], [manual_total_cost], [additional_charges], [final_total_cost])
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                created_at, data.gate_name, data.from_loc, data.to_loc,
                pick_ids_json, data.manual_total_cost, data.additional_charges, data.final_total_cost
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
def get_history(user: dict = Depends(get_current_user)):
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
                "gate_name": row[2],
                "from_loc": row[3],
                "to_loc": row[4],
                "pick_ids": json.loads(row[5]),
                "manual_total_cost": row[6],
                "additional_charges": row[7],
                "final_total_cost": row[8]
            })
            
        conn.close()
        return {"history": history}
    except Exception as e:
        logger.error(f"Error loading history: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error loading history: {str(e)}")

@app.delete("/history/{record_id}")
def delete_history_item(record_id: int, user: dict = Depends(get_current_user)):
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

@app.get("/history/{record_id}/download")
def download_history_excel(record_id: int):
    try:
        # 1. Fetch the history record
        conn = get_logistic_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Calculation_History WHERE id = ?", (record_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            raise HTTPException(status_code=404, detail="History record not found")

        # Map row to dictionary
        record = {
            "id": row[0],
            "gate_name": row[2],
            "from_loc": row[3],
            "to_loc": row[4],
            "pick_ids": json.loads(row[5]),
            "manual_total_cost": row[6],
            "additional_charges": row[7]
        }

        # 2. Re-calculate cost breakdown using helper
        try:
            calc_result = _perform_calculation_logic(
                gate_name=record['gate_name'],
                pick_ids=record['pick_ids'],
                manual_total_cost=record['manual_total_cost'],
                additional_charges=record['additional_charges']
            )
        except Exception as e:
             raise HTTPException(status_code=500, detail=f"Error recalculating data: {str(e)}")

        products = calc_result['calculated_products']

        # 3. Create Excel
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Cost Details"

        headers = [
            "No", "Claim Date", "Area", "Item", "Quantity", 
            "Price", "Total Amount", "Ton", "Gate", "Branch"
        ]
        
        header_fill = PatternFill(start_color='4472C4', end_color='4472C4', fill_type='solid')
        header_font = Font(bold=True, color='FFFFFF')
        border_style = Side(border_style="thin", color="000000")
        border = Border(left=border_style, right=border_style, top=border_style, bottom=border_style)

        for col_num, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col_num)
            cell.value = header
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal='center')
            cell.border = border

        claim_date = datetime.datetime.now().strftime("%Y-%m-%d")
        
        for idx, item in enumerate(products, 1):
            row_num = idx + 1
            ws.cell(row=row_num, column=1, value=idx).border = border
            ws.cell(row=row_num, column=2, value=claim_date).border = border
            ws.cell(row=row_num, column=3, value=record['to_loc']).border = border
            ws.cell(row=row_num, column=4, value=item['name']).border = border
            ws.cell(row=row_num, column=5, value=item['quantity']).border = border
            
            price_cell = ws.cell(row=row_num, column=6, value=item['unit_cost']) 
            price_cell.number_format = '#,##0.00'
            price_cell.border = border

            amt_cell = ws.cell(row=row_num, column=7, value=item['total_cost'])
            amt_cell.number_format = '#,##0.00'
            amt_cell.border = border

            weight_cell = ws.cell(row=row_num, column=8, value=item['weight'])
            weight_cell.number_format = '#,##0.00'
            weight_cell.border = border

            ws.cell(row=row_num, column=9, value=record['gate_name']).border = border
            ws.cell(row=row_num, column=10, value=record['to_loc']).border = border

        for col in ws.columns:
            max_length = 0
            col_letter = col[0].column_letter
            for cell in col:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            ws.column_dimensions[col_letter].width = max_length + 2

        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        
        filename = f"Calculation_{record_id}_{record['gate_name']}.xlsx"
        
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating download: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating download: {str(e)}")

# --- Excel Export/Import Endpoints (account or admin) ---

@app.get("/account/item-pricing/export/{gate_id}")
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

@app.post("/account/item-pricing/import/{gate_id}")
async def import_item_pricing_excel(gate_id: int, file: UploadFile = File(...), user: dict = Depends(get_account_user)):
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

@app.get("/account/gates")
def get_all_gates(user: dict = Depends(get_current_user)):
    try:
        conn = get_logistic_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT [Gate ID], [Gate Name], [From], [To], [UOM], [Unit], [Cost Per Unit] FROM Gate")
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
                "uom": row[4],         
                "unit": row[5],        
                "cost_per_unit": float(row[6]) if row[6] is not None else None, 
                "calculation_type": calc_type
            })
        
        conn.close()
        return {"gates": gates}
    except Exception as e:
        logger.error(f"Error loading gates: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error loading gates: {str(e)}")

@app.post("/account/gates")
def save_gate(gate_data: GateData, user: dict = Depends(get_account_user)):
    try:
        conn = get_logistic_connection()
        cursor = conn.cursor()

        if gate_data.original_gate_name:
            cursor.execute("""
                UPDATE Gate 
                SET [Gate Name] = ?, [From] = ?, [To] = ?, [UOM] = ?, [Unit] = ?, [Cost Per Unit] = ?
                WHERE [Gate Name] = ?
            """, (gate_data.gate_name, gate_data.from_loc, gate_data.to_loc, 
                  gate_data.uom, gate_data.unit, gate_data.cost_per_unit, 
                  gate_data.original_gate_name))
        else:
            cursor.execute("""
                INSERT INTO Gate ([Gate Name], [From], [To], [UOM], [Unit], [Cost Per Unit])
                VALUES (?, ?, ?, ?, ?, ?)
            """, (gate_data.gate_name, gate_data.from_loc, gate_data.to_loc, 
                  gate_data.uom, gate_data.unit, gate_data.cost_per_unit))
        
        conn.commit()
        conn.close()
        return {"message": "Gate saved successfully"}
    
    except Exception as e:
        logger.error(f"Error saving gate: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error saving gate: {str(e)}")

@app.delete("/account/gates/{gate_id}")
def delete_gate(gate_id: int, user: dict = Depends(get_admin_user)): # CHANGED to get_admin_user
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

@app.get("/account/item-pricing/{gate_id}")
def get_item_pricing(gate_id: int, user: dict = Depends(get_current_user)):
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

@app.post("/account/item-pricing")
def save_item_pricing(item_data: ItemPricingData, user: dict = Depends(get_account_user)):
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

@app.delete("/account/item-pricing/{gate_id}/{item_code}")
def delete_item_pricing(gate_id: int, item_code: str, user: dict = Depends(get_admin_user)): # CHANGED to get_admin_user
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
    manual_total_cost: Optional[float] = None, 
    additional_charges: Optional[float] = 0.0
):
    try:
        if not pick_ids:
            raise HTTPException(status_code=400, detail="No Pick IDs provided")
            
        result = _perform_calculation_logic(
            gate_name=gate_name, 
            pick_ids=pick_ids, 
            manual_total_cost=manual_total_cost, 
            additional_charges=additional_charges
        )
        return result

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
            SELECT ItemCode, MAX(Dscription), SUM(Quantity), MAX(UomCode), SUM(ItemWeight)
            FROM PG_PickDetail 
            WHERE ID IN ({placeholders}) 
            GROUP BY ItemCode
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

@app.get("/products/{pick_id}")
def get_products_by_pick_id(pick_id: str):
    """Get products from SQL Server (Single ID)"""
    try:
        conn = get_dwbi_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT ItemCode, MAX(Dscription), SUM(Quantity), MAX(UomCode), SUM(ItemWeight)
            FROM PG_PickDetail 
            WHERE ID = ? 
            GROUP BY ItemCode
            ORDER BY ItemCode
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