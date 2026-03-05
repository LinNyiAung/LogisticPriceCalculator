import logging
import pyodbc
import sqlite3
import json
import datetime
import time
import random
from fastapi import FastAPI, HTTPException, UploadFile, File, Query, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Any
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
ACCESS_TOKEN_EXPIRE_MINUTES = 43200 # 30 days expiration

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
        
        # Gate table 
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Gate (
                [Gate ID] INTEGER PRIMARY KEY,
                [Gate Name] TEXT,
                [From] TEXT,
                [To] TEXT,
                [UOM] TEXT,
                [Unit] INTEGER,
                [Cost] REAL
            )
        """)
        
        # Item_Pricing table (UOM Removed)
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
                [id] INTEGER PRIMARY KEY, 
                [created_at] TEXT,
                [gate_name] TEXT,
                [from_loc] TEXT,
                [to_loc] TEXT,
                [doc_nums] TEXT, -- Stored as JSON string (contains DocNums)
                [manual_total_cost] REAL,
                [additional_charges] REAL,
                [final_total_cost] REAL,
                [channel] TEXT,
                [status] TEXT DEFAULT 'saved',
                [created_by] TEXT
            )
        """)

        # Safely attempt to add columns for existing databases
        try:
            cursor.execute("ALTER TABLE Calculation_History ADD COLUMN [channel] TEXT")
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute("ALTER TABLE Calculation_History ADD COLUMN [status] TEXT DEFAULT 'saved'")
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute("ALTER TABLE Calculation_History ADD COLUMN [created_by] TEXT")
        except sqlite3.OperationalError:
            pass
        
        # --- User Table ---
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Users (
                username TEXT PRIMARY KEY,
                hashed_password TEXT,
                role TEXT
            )
        """)

        # --- Reference Tables (Locations, UOMs, Channels) ---
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Locations (
                [id] INTEGER PRIMARY KEY AUTOINCREMENT,
                [name] TEXT UNIQUE
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS UOMs (
                [id] INTEGER PRIMARY KEY AUTOINCREMENT,
                [name] TEXT UNIQUE
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Channels (
                [id] INTEGER PRIMARY KEY AUTOINCREMENT,
                [name] TEXT UNIQUE
            )
        """)

        # --- Branch Code Mapping Table ---
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Branch_Code (
                [Log-Pric] TEXT,
                [Code] TEXT,
                [Name] TEXT,
                [Dept] TEXT,
                [Principal] TEXT,
                [Description] TEXT
            )
        """)

        # --- SD Code Mapping Table ---
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS SD_Code (
                [Channel] TEXT,
                [Code] TEXT,
                [Name] TEXT,
                [Dept] TEXT,
                [Principal] TEXT,
                [Log-Pric] TEXT
            )
        """)

        # --- Gate Change Log Table ---
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Gate_Change_Log (
                [id] INTEGER PRIMARY KEY AUTOINCREMENT,
                [gate_id] INTEGER,
                [changed_by] TEXT,
                [change_date] TEXT,
                [field_name] TEXT,
                [old_value] TEXT,
                [new_value] TEXT,
                FOREIGN KEY([gate_id]) REFERENCES Gate([Gate ID])
            )
        """)

        # --- Item Change Log Table ---
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Item_Change_Log (
                [id] INTEGER PRIMARY KEY AUTOINCREMENT,
                [pricing_id] INTEGER,
                [changed_by] TEXT,
                [change_date] TEXT,
                [field_name] TEXT,
                [old_value] TEXT,
                [new_value] TEXT,
                FOREIGN KEY([pricing_id]) REFERENCES Item_Pricing([Pricing ID])
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
            
        # Create default admin user
        cursor.execute("SELECT * FROM Users WHERE username = 'admin'")
        if not cursor.fetchone():
            admin_pw = pwd_context.hash("admin123")
            cursor.execute("INSERT INTO Users (username, hashed_password, role) VALUES (?, ?, ?)", 
                          ('admin', admin_pw, 'admin'))

        # --- SEED DEFAULTS FOR REFERENCES ---
        cursor.execute("SELECT COUNT(*) FROM Locations")
        if cursor.fetchone()[0] == 0:
            default_locs = [('YGN',), ('MDY',), ('NPT',), ('MGW',), ('TGI',), ('TGU',), ('PTN',), ('MLM',)]
            cursor.executemany("INSERT INTO Locations (name) VALUES (?)", default_locs)

        cursor.execute("SELECT COUNT(*) FROM UOMs")
        if cursor.fetchone()[0] == 0:
            default_uoms = [('Kg',), ('Ton',)]
            cursor.executemany("INSERT INTO UOMs (name) VALUES (?)", default_uoms)

        cursor.execute("SELECT COUNT(*) FROM Channels")
        if cursor.fetchone()[0] == 0:
            default_channels = [('SD',), ('Branch',), ('Telecom Branch',), ('Telecom SD',), ('Outlet',)]
            cursor.executemany("INSERT INTO Channels (name) VALUES (?)", default_channels)
        
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
    cost: Optional[float] = None 
    original_gate_name: Optional[str] = None

class GateLogItem(BaseModel):
    id: int
    gate_id: int
    changed_by: str
    change_date: str
    field_name: str
    old_value: Optional[str]
    new_value: Optional[str]

class ItemLogItem(BaseModel):
    id: int
    pricing_id: int
    changed_by: str
    change_date: str
    field_name: str
    old_value: Optional[str]
    new_value: Optional[str]

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
    doc_nums: List[str]
    manual_total_cost: Optional[float] = None
    additional_charges: Optional[float] = 0.0
    final_total_cost: float
    channel: Optional[str] = ""
    status: Optional[str] = "saved"

class ReferenceItem(BaseModel):
    name: str

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
    try:
        conn = get_logistic_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT [Cost] FROM Gate WHERE [Gate ID] = ?", (gate_id,))
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

def _perform_calculation_logic(gate_name, doc_nums, manual_total_cost=None, additional_charges=0.0):
    add_charges = float(additional_charges) if additional_charges is not None else 0.0

    # 1. Get Transfer Data from DWBI (PG_TransferDetails)
    # BatchQty removed
    try:
        conn_dwbi = get_dwbi_connection()
        cursor_dwbi = conn_dwbi.cursor()
        
        placeholders = ','.join('?' * len(doc_nums))
        
        query = f"""
            SELECT ItemCode, MAX(Dscription), MAX(UoM), SUM(ItemWeight), MAX(DocDate), DocNum, MAX(Principal), SUM(BatchQtyByCtn)
            FROM PG_TransferDetails 
            WHERE DocNum IN ({placeholders}) 
            GROUP BY DocNum, ItemCode
            ORDER BY DocNum, ItemCode
        """
        cursor_dwbi.execute(query, doc_nums)
        pick_rows = cursor_dwbi.fetchall()
        conn_dwbi.close()
    except Exception as e:
        raise Exception(f"Error fetching transfer details: {str(e)}")
    
    if not pick_rows:
        raise Exception("No products found for the selected Doc Nums")
    
    # 2. Get Gate Data, Branch_Code, and SD_Code mapping
    try:
        conn_log = get_logistic_connection()
        cursor_log = conn_log.cursor()
        
        cursor_log.execute("SELECT [Gate ID], [From], [To], [Cost], [Unit] FROM Gate WHERE [Gate Name] = ?", (gate_name,))
        gate_row = cursor_log.fetchone()
        
        # Fetch Branch_Code mapping
        cursor_log.execute("SELECT [Log-Pric], [Code], [Name], [Dept], [Principal], [Description] FROM Branch_Code")
        branch_code_map = {row[0].strip().lower(): {
            "Code": row[1],
            "Name": row[2],
            "Dept": row[3],
            "Principal": row[4],
            "Description": row[5]
        } for row in cursor_log.fetchall() if row[3]}

        # Fetch SD_Code mapping (Mapped by Log-Pric)
        cursor_log.execute("SELECT [Dept], [Principal], [Log-Pric] FROM SD_Code")
        sd_code_map = {row[2].strip().lower(): {
            "Dept": row[0],
            "Principal": row[1]
        } for row in cursor_log.fetchall() if row[2]}

    except Exception as e:
        raise Exception(f"Error fetching local configs: {str(e)}")
    
    if not gate_row:
        if 'conn_log' in locals(): conn_log.close()
        raise Exception(f"Gate {gate_name} not found")
        
    gate_id = gate_row[0]
    from_loc = gate_row[1]
    to_loc = gate_row[2]
    cost = float(gate_row[3] or 0)
    gate_unit = float(gate_row[4]) if gate_row[4] else 1.0 # default to 1 if Unit is missing
    
    # 3. Get Item Pricing (UOM removed)
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
        t_cost = str(row[1]).strip() if row[1] else ""
        
        if not t_cost or t_cost.lower() == 'nan' or t_cost.lower() == 'none' or t_cost == '':
            item_pricing[i_code] = {'type': 'ton', 'value': None}
        else:
            try:
                val = float(t_cost)
                item_pricing[i_code] = {'type': 'direct', 'value': val}
            except:
                item_pricing[i_code] = {'type': 'unknown', 'value': None}

    if cost > 0:
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
            principal_val = row[6] or ""
            bc_info = branch_code_map.get(principal_val.strip().lower(), {})
            sd_info = sd_code_map.get(principal_val.strip().lower(), {})

            item_data = {
                "code": row[0] if row[0] else "",
                "name": row[1] if row[1] else "",
                "uom": row[2] if row[2] else "",
                "weight": float(row[3]) if row[3] else 0.0,
                "doc_date": row[4],         
                "sin_no": row[5],           
                "principal": principal_val,   
                "ctns": round(float(row[7])) if row[7] else 0, # ROUNDED CTNS
                "b_code": bc_info.get("Code", ""),
                "b_name": bc_info.get("Name", ""),
                "b_dept": bc_info.get("Dept", ""),
                "b_principal": bc_info.get("Principal", ""),
                "b_desc": bc_info.get("Description", ""),
                "s_dept": sd_info.get("Dept", ""),
                "s_principal": sd_info.get("Principal", "")
            }
            
            p_info = item_pricing.get(item_data['code'], {})
            p_type = p_info.get('type', 'ton')
            p_val = p_info.get('value', 0.0)
            
            if p_type == 'direct':
                # Calculation based on ROUNDED CTNS
                estimated_total_cost += (item_data['ctns'] * p_val)
                item_data['standard_unit_cost'] = p_val
                direct_items.append(item_data)
            else:
                # Calculate cost based on Unit (e.g. cost per 1000 kg vs cost per 1 kg)
                effective_rate = cost / gate_unit if gate_unit > 0 else cost
                cost_item = item_data['weight'] * effective_rate
                
                estimated_total_cost += cost_item
                ton_cost_total += cost_item
                item_data['total_cost'] = cost_item
                ton_items.append(item_data)

        direct_unit_cost = 0.0
        if manual_total_cost is not None:
            remainder = manual_total_cost - ton_cost_total
            total_direct_ctns = sum(item['ctns'] for item in direct_items)
            
            if total_direct_ctns > 0:
                direct_unit_cost = remainder / total_direct_ctns
            
            total_cost = manual_total_cost
        else:
            total_cost = estimated_total_cost

        for item in ton_items:
            avg_unit_cost = item['total_cost'] / item['ctns'] if item['ctns'] > 0 else 0
            
            calculated_products.append({
                **item,
                "calculation_type": "weight",
                "unit_cost": avg_unit_cost, 
                "total_cost": item['total_cost'] 
            })
        
        for item in direct_items:
            final_unit_cost = direct_unit_cost if manual_total_cost is not None else item['standard_unit_cost']
            final_item_cost = item['ctns'] * final_unit_cost # Based on CTNS
            
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
            
            weight = float(row[3]) if row[3] else 0.0
            ctns = round(float(row[7])) if row[7] else 0 # ROUNDED CTNS
            principal_val = row[6] or ""
            bc_info = branch_code_map.get(principal_val.strip().lower(), {})
            sd_info = sd_code_map.get(principal_val.strip().lower(), {})

            unit_cost = pricing_info.get('value', 0.0) or 0.0
            item_cost = ctns * unit_cost # Based on CTNS
            
            total_cost += item_cost
            estimated_total_cost += item_cost
            
            calculated_products.append({
                "code": item_code,
                "name": row[1] if row[1] else "",
                "ctns": ctns,
                "uom": row[2] if row[2] else "",
                "weight": weight,
                "doc_date": row[4],       
                "sin_no": row[5],         
                "principal": principal_val,
                "b_code": bc_info.get("Code", ""),
                "b_name": bc_info.get("Name", ""),
                "b_dept": bc_info.get("Dept", ""),
                "b_principal": bc_info.get("Principal", ""),
                "b_desc": bc_info.get("Description", ""),
                "s_dept": sd_info.get("Dept", ""),
                "s_principal": sd_info.get("Principal", ""),
                "calculation_type": "direct",
                "unit_cost": unit_cost,
                "total_cost": item_cost
            })

    # --- DISTRIBUTE ADDITIONAL CHARGES TO INDIVIDUAL ITEMS EQUALLY ---
    if add_charges != 0 and calculated_products:
        num_items = len(calculated_products)
        equal_extra_cost = add_charges / num_items
        
        for p in calculated_products:
            p['total_cost'] += equal_extra_cost
            
            # Recalculate the unit cost to reflect the added charge
            if p['ctns'] > 0:
                p['unit_cost'] = p['total_cost'] / p['ctns']

    calculated_products.sort(key=lambda x: (x.get('sin_no', ''), x['code']))
    
    total_cost += add_charges
    estimated_total_cost += add_charges
    
    return {
        "calculation_type": calc_type,
        "gate_name": gate_name,
        "from_loc": from_loc,
        "to_loc": to_loc,
        "cost": cost, 
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

# --- Reference Management Endpoints ---

@app.get("/references/locations")
def get_ref_locations():
    try:
        conn = get_logistic_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM Locations ORDER BY name")
        rows = cursor.fetchall()
        conn.close()
        return [row[0] for row in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.post("/references/locations")
def add_ref_location(item: ReferenceItem, user: dict = Depends(get_account_user)):
    try:
        conn = get_logistic_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO Locations (name) VALUES (?)", (item.name,))
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            raise HTTPException(status_code=400, detail="Location already exists")
        conn.close()
        return {"message": "Added successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.delete("/references/locations/{name}")
def delete_ref_location(name: str, user: dict = Depends(get_account_user)):
    try:
        conn = get_logistic_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Locations WHERE name = ?", (name,))
        if cursor.rowcount == 0:
             conn.close()
             raise HTTPException(status_code=404, detail="Not found")
        conn.commit()
        conn.close()
        return {"message": "Deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.get("/references/uoms")
def get_ref_uoms():
    try:
        conn = get_logistic_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM UOMs ORDER BY name")
        rows = cursor.fetchall()
        conn.close()
        return [row[0] for row in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.post("/references/uoms")
def add_ref_uom(item: ReferenceItem, user: dict = Depends(get_account_user)):
    try:
        conn = get_logistic_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO UOMs (name) VALUES (?)", (item.name,))
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            raise HTTPException(status_code=400, detail="UOM already exists")
        conn.close()
        return {"message": "Added successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.delete("/references/uoms/{name}")
def delete_ref_uom(name: str, user: dict = Depends(get_account_user)):
    try:
        conn = get_logistic_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM UOMs WHERE name = ?", (name,))
        if cursor.rowcount == 0:
             conn.close()
             raise HTTPException(status_code=404, detail="Not found")
        conn.commit()
        conn.close()
        return {"message": "Deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.get("/references/channels")
def get_ref_channels():
    try:
        conn = get_logistic_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM Channels ORDER BY name")
        rows = cursor.fetchall()
        conn.close()
        return [row[0] for row in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.post("/references/channels")
def add_ref_channel(item: ReferenceItem, user: dict = Depends(get_account_user)):
    try:
        conn = get_logistic_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO Channels (name) VALUES (?)", (item.name,))
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            raise HTTPException(status_code=400, detail="Channel already exists")
        conn.close()
        return {"message": "Added successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.delete("/references/channels/{name}")
def delete_ref_channel(name: str, user: dict = Depends(get_account_user)):
    try:
        conn = get_logistic_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Channels WHERE name = ?", (name,))
        if cursor.rowcount == 0:
             conn.close()
             raise HTTPException(status_code=404, detail="Not found")
        conn.commit()
        conn.close()
        return {"message": "Deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

# --- Calculation History Endpoints ---

@app.post("/history/save")
def save_calculation(data: CalculationSaveRequest, user: dict = Depends(get_current_user)):
    try:
        conn = get_logistic_connection()
        cursor = conn.cursor()
        
        doc_nums_json = json.dumps(data.doc_nums)
        created_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if data.id:
            cursor.execute("SELECT id FROM Calculation_History WHERE id = ?", (data.id,))
            if not cursor.fetchone():
                conn.close()
                raise HTTPException(status_code=404, detail="Record to update not found")
            cursor.execute("""
                UPDATE Calculation_History 
                SET created_at = ?, gate_name = ?, from_loc = ?, to_loc = ?, 
                    doc_nums = ?, manual_total_cost = ?, additional_charges = ?, final_total_cost = ?, channel = ?,
                    status = ?
                WHERE id = ?
            """, (
                created_at, data.gate_name, data.from_loc, data.to_loc,
                doc_nums_json, data.manual_total_cost, data.additional_charges, 
                data.final_total_cost, data.channel, data.status, data.id
            ))
            message = "Calculation updated successfully"
        else:
            while True:
                # Generate 12-digit ID: YYMMDDHHMMSS
                new_id = int(datetime.datetime.now().strftime("%y%m%d%H%M%S"))
                cursor.execute("SELECT 1 FROM Calculation_History WHERE id = ?", (new_id,))
                if not cursor.fetchone():
                    break
                time.sleep(1) # Prevent duplicate ID if multiple saves happen in the exact same second

            cursor.execute("""
                INSERT INTO Calculation_History 
                ([id], [created_at], [gate_name], [from_loc], [to_loc], 
                 [doc_nums], [manual_total_cost], [additional_charges], [final_total_cost], [channel], [status], [created_by])
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                new_id, created_at, data.gate_name, data.from_loc, data.to_loc,
                doc_nums_json, data.manual_total_cost, data.additional_charges, data.final_total_cost, data.channel, data.status, user["username"]
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

@app.put("/history/{record_id}/submit")
def submit_history_item(record_id: int, user: dict = Depends(get_current_user)):
    try:
        conn = get_logistic_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE Calculation_History SET status = 'submitted' WHERE id = ?", (record_id,))
        if cursor.rowcount == 0:
            conn.close()
            raise HTTPException(status_code=404, detail="Record not found")
        conn.commit()
        conn.close()
        return {"message": "Calculation submitted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error submitting record: {str(e)}")

@app.put("/history/{record_id}/claim")
def claim_history_item(record_id: int, user: dict = Depends(get_account_user)):
    try:
        conn = get_logistic_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE Calculation_History SET status = 'claimed' WHERE id = ?", (record_id,))
        if cursor.rowcount == 0:
            conn.close()
            raise HTTPException(status_code=404, detail="Record not found")
        conn.commit()
        conn.close()
        return {"message": "Calculation claimed successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error claiming record: {str(e)}")

@app.get("/history")
def get_history(user: dict = Depends(get_current_user)):
    try:
        conn = get_logistic_connection()
        cursor = conn.cursor()
        
        role = user.get('role')
        username = user.get('username')

        if role == 'admin':
            cursor.execute("SELECT * FROM Calculation_History ORDER BY created_at DESC")
        elif role == 'account':
            # Account users can see both submitted and already claimed records
            cursor.execute("SELECT * FROM Calculation_History WHERE status IN ('submitted', 'claimed') ORDER BY created_at DESC")
        else: # logistic
            cursor.execute("SELECT * FROM Calculation_History WHERE created_by = ? OR created_by IS NULL ORDER BY created_at DESC", (username,))
            
        rows = cursor.fetchall()
        history = []
        for row in rows:
            history.append({
                "id": row[0],
                "created_at": row[1],
                "gate_name": row[2],
                "from_loc": row[3],
                "to_loc": row[4],
                "doc_nums": json.loads(row[5]),
                "manual_total_cost": row[6],
                "additional_charges": row[7],
                "final_total_cost": row[8],
                "channel": row[9],
                "status": row[10] if len(row) > 10 else 'saved',
                "created_by": row[11] if len(row) > 11 else 'unknown'
            })
        conn.close()
        return {"history": history}
    except Exception as e:
        logger.error(f"Error loading history: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error loading history: {str(e)}")

@app.delete("/history/{record_id}")
def delete_history_item(record_id: int, user: dict = Depends(get_admin_user)):
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
        conn = get_logistic_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Calculation_History WHERE id = ?", (record_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            raise HTTPException(status_code=404, detail="History record not found")

        record = {
            "id": row[0],
            "gate_name": row[2],
            "from_loc": row[3],
            "to_loc": row[4],
            "doc_nums": json.loads(row[5]),
            "manual_total_cost": row[6],
            "additional_charges": row[7],
            "channel": row[9] 
        }

        try:
            calc_result = _perform_calculation_logic(
                gate_name=record['gate_name'],
                doc_nums=record['doc_nums'],
                manual_total_cost=record['manual_total_cost'],
                additional_charges=record['additional_charges']
            )
        except Exception as e:
             raise HTTPException(status_code=500, detail=f"Error recalculating data: {str(e)}")

        products = calc_result['calculated_products']

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Cost Details"

        # Headers updated: Removed "Quantity" and "Price"
        headers = [
            "No", "Claim Date", "Delivery Date", "SIN No", "Area", 
            "Code", "Name", "Principal", "Item Code", "Item", "Ctns", 
            "Price", "Total Amount", "Weight", "UOM", "Gate", "Channel", "Month", "Year", 
            "Description for Account", "Description with cnts and price", 
            "Branch", "B-Dept", "B-Principal", "S-Dept", "S-Principal", "Calculation ID"
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

        # Claim Date Logic
        now = datetime.datetime.now()
        claim_date_str = now.strftime("%d/%m/%Y") 
        claim_month = now.strftime("%B") 
        claim_year = now.year
        
        for idx, item in enumerate(products, 1):
            row_num = idx + 1
            
            # Delivery Date (Doc Date) Logic
            doc_date_val = item.get('doc_date')
            if isinstance(doc_date_val, datetime.datetime):
                doc_date_str = doc_date_val.strftime("%d/%m/%Y")
            elif isinstance(doc_date_val, str) and len(doc_date_val) >= 10:
                try:
                    parsed_date = datetime.datetime.strptime(doc_date_val[:10], "%Y-%m-%d")
                    doc_date_str = parsed_date.strftime("%d/%m/%Y")
                except ValueError:
                    doc_date_str = doc_date_val
            else:
                doc_date_str = str(doc_date_val) if doc_date_val else ""

            # Extract necessary items for calculations
            b_desc = item.get('b_desc', '')
            ctns_val = item.get('ctns', 0)
            total_cost_val = item.get('total_cost', 0)
            
            # Formatting variables
            ctns_formatted = int(ctns_val) if float(ctns_val).is_integer() else ctns_val
            
            # Calculate Price(ctn)
            price_per_ctn = total_cost_val / ctns_val if ctns_val > 0 else 0
            price_formatted = int(price_per_ctn) if float(price_per_ctn).is_integer() else round(price_per_ctn, 2)

            concat_desc = f"{b_desc.strip()} - {ctns_formatted} ctns @{price_formatted} kyats"

            # Populating columns
            ws.cell(row=row_num, column=1, value=idx).border = border # No
            ws.cell(row=row_num, column=2, value=claim_date_str).border = border # Claim Date
            ws.cell(row=row_num, column=3, value=doc_date_str).border = border # Delivery Date
            ws.cell(row=row_num, column=4, value=item.get('sin_no', '')).border = border # SIN No
            ws.cell(row=row_num, column=5, value=record['to_loc']).border = border # Area
            ws.cell(row=row_num, column=6, value=item.get('b_code', '')).border = border # Code
            ws.cell(row=row_num, column=7, value=item.get('b_name', '')).border = border # Name
            ws.cell(row=row_num, column=8, value=item.get('principal', '')).border = border # Principal
            
            ws.cell(row=row_num, column=9, value=item['code']).border = border # Item Code
            ws.cell(row=row_num, column=10, value=item['name']).border = border # Item
            ws.cell(row=row_num, column=11, value=ctns_formatted).border = border # Ctns
            
            # Price(ctn) Column is now 12 (Quantity was removed)
            ctn_price_cell = ws.cell(row=row_num, column=12, value=price_per_ctn) 
            ctn_price_cell.number_format = '#,##0.00'
            ctn_price_cell.border = border

            # Total Amount Column is now 13 (Price was removed)
            amt_cell = ws.cell(row=row_num, column=13, value=total_cost_val) 
            amt_cell.number_format = '#,##0.00'
            amt_cell.border = border

            # Shifted remaining columns down by 2 (Weight is now 14)
            weight_cell = ws.cell(row=row_num, column=14, value=item['weight']) 
            weight_cell.number_format = '#,##0.00'
            weight_cell.border = border

            ws.cell(row=row_num, column=15, value="Kg").border = border # UOM hardcoded to "Kg"
            ws.cell(row=row_num, column=16, value=record['gate_name']).border = border # Gate
            ws.cell(row=row_num, column=17, value=record.get('channel', '')).border = border # Channel 
            ws.cell(row=row_num, column=18, value=claim_month).border = border # Month
            ws.cell(row=row_num, column=19, value=claim_year).border = border # Year
            ws.cell(row=row_num, column=20, value=b_desc).border = border # Description for Account
            ws.cell(row=row_num, column=21, value=concat_desc).border = border # Description with cnts and price
            ws.cell(row=row_num, column=22, value=record['to_loc']).border = border # Branch
            ws.cell(row=row_num, column=23, value=item.get('b_dept', '')).border = border # B-Dept
            ws.cell(row=row_num, column=24, value=item.get('b_principal', '')).border = border # B-Principal
            ws.cell(row=row_num, column=25, value=item.get('s_dept', '')).border = border # S-Dept
            ws.cell(row=row_num, column=26, value=item.get('s_principal', '')).border = border # S-Principal
            ws.cell(row=row_num, column=27, value=record['id']).border = border # Calculation ID

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
    
# --- Item Pricing Excel Export/Import ---

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
        
        # UOM Removed
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
        
        # UOM Removed
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
        
        excel_rows = []
        item_codes_to_check = set()
        
        # Updated indices for UOM removal
        for row_idx, row in enumerate(ws.iter_rows(min_row=4, values_only=True), start=4):
            if not row[0]: continue
            
            item_code = str(row[0]).strip()
            item_name = str(row[1]).strip() if row[1] else ""
            principal = str(row[2]).strip() if row[2] else ""
            brand = str(row[3]).strip() if row[3] else ""
            transport_cost = str(row[4]).strip() if len(row) > 4 and row[4] else ""
            
            excel_rows.append({
                "row_num": row_idx,
                "code": item_code,
                "name": item_name,
                "principal": principal,
                "brand": brand,
                "cost": transport_cost
            })
            item_codes_to_check.add(item_code)
            
        if not excel_rows:
             raise HTTPException(status_code=400, detail="No data found in Excel file")

        conn_dwbi = get_dwbi_connection()
        cursor_dwbi = conn_dwbi.cursor()
        
        dwbi_data = {}
        unique_codes_list = list(item_codes_to_check)
        batch_size = 1000
        
        for i in range(0, len(unique_codes_list), batch_size):
            batch = unique_codes_list[i:i + batch_size]
            placeholders = ','.join('?' * len(batch))
            query_dwbi = f"""
                SELECT ItemCode, ItemName, ItemGroupName, BrandName 
                FROM _ItemAllinone 
                WHERE ItemCode IN ({placeholders})
            """
            cursor_dwbi.execute(query_dwbi, batch)
            rows = cursor_dwbi.fetchall()
            for r in rows:
                dwbi_data[str(r[0]).strip()] = {
                    "name": str(r[1]).strip() if r[1] else "",
                    "principal": str(r[2]).strip() if r[2] else "", 
                    "brand": str(r[3]).strip() if r[3] else ""
                }
        
        conn_dwbi.close()
        
        errors = []
        for row in excel_rows:
            code = row["code"]
            if code not in dwbi_data:
                errors.append(f"Row {row['row_num']}: Item Code '{code}' not found in DWBI.")
                continue
            db_item = dwbi_data[code]
            if row["name"].lower() != db_item["name"].lower():
                 errors.append(f"Row {row['row_num']}: Item Name mismatch. Excel: '{row['name']}', System: '{db_item['name']}'")
            if row["principal"].lower() != db_item["principal"].lower():
                 errors.append(f"Row {row['row_num']}: Principal mismatch. Excel: '{row['principal']}', System: '{db_item['principal']}'")
            if row["brand"].lower() != db_item["brand"].lower():
                 errors.append(f"Row {row['row_num']}: Brand mismatch. Excel: '{row['brand']}', System: '{db_item['brand']}'")

        if errors:
            error_msg = errors[:10]
            if len(errors) > 10:
                error_msg.append(f"... and {len(errors) - 10} more errors.")
            raise HTTPException(status_code=400, detail=error_msg)

        conn = get_logistic_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT [Item ID] FROM Item_Pricing WHERE [Gate ID] = ?", (gate_id,))
        existing_items = {row[0] for row in cursor.fetchall()}
        
        cursor.execute("SELECT [Pricing ID] FROM Item_Pricing")
        used_ids = {row[0] for row in cursor.fetchall()}
        
        updated_items_set = set()
        updates_made = 0
        inserts_made = 0
        
        for row in excel_rows:
            item_code = row["code"]
            updated_items_set.add(item_code)
            
            # Update query modified (UOM removed)
            if item_code in existing_items:
                cursor.execute("""
                    UPDATE Item_Pricing
                    SET [Item Name] = ?, [Principal] = ?, [Brand] = ?, [Transportation Cost] = ?
                    WHERE [Gate ID] = ? AND [Item ID] = ?
                """, (row["name"], row["principal"], row["brand"], row["cost"], gate_id, item_code))
                updates_made += 1
            else:
                while True:
                    new_id = random.randint(10000000, 99999999)
                    if new_id not in used_ids:
                        used_ids.add(new_id)
                        break
                # Insert query modified (UOM removed)
                cursor.execute("""
                    INSERT INTO Item_Pricing 
                    ([Pricing ID], [Gate ID], [Item ID], [Item Name], [Principal], [Brand], [Transportation Cost])
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (new_id, gate_id, item_code, row["name"], row["principal"], row["brand"], row["cost"]))
                inserts_made += 1
        
        items_to_delete = existing_items - updated_items_set
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
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error importing Excel: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error importing: {str(e)}")

# --- Gate Management Endpoints (SQLite) ---

@app.get("/account/gates")
def get_all_gates(user: dict = Depends(get_current_user)):
    try:
        conn = get_logistic_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT [Gate ID], [Gate Name], [From], [To], [UOM], [Unit], [Cost] FROM Gate")
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
                "cost": float(row[6]) if row[6] is not None else None, 
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

        # Check for changes if editing existing gate
        if gate_data.original_gate_name:
            # 1. Fetch current data before update to detect changes
            cursor.execute("""
                SELECT [Gate ID], [UOM], [Unit], [Cost] 
                FROM Gate 
                WHERE [Gate Name] = ?
            """, (gate_data.original_gate_name,))
            current_row = cursor.fetchone()
            
            if current_row:
                gate_id, old_uom, old_unit, old_cost = current_row
                
                # Normalize values for comparison
                old_uom = old_uom if old_uom else None
                new_uom = gate_data.uom if gate_data.uom else None
                
                old_unit = old_unit if old_unit is not None else None
                new_unit = gate_data.unit if gate_data.unit is not None else None
                
                old_cost = float(old_cost) if old_cost is not None else None
                new_cost = float(gate_data.cost) if gate_data.cost is not None else None

                change_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                username = user['username']
                
                changes = []

                if old_uom != new_uom:
                    changes.append((gate_id, username, change_date, 'UOM', str(old_uom or ''), str(new_uom or '')))
                
                if old_unit != new_unit:
                    changes.append((gate_id, username, change_date, 'Unit', str(old_unit) if old_unit is not None else '', str(new_unit) if new_unit is not None else ''))
                
                if old_cost != new_cost:
                    changes.append((gate_id, username, change_date, 'Cost', str(old_cost) if old_cost is not None else '', str(new_cost) if new_cost is not None else ''))
                
                # Insert logs if changes detected
                if changes:
                    cursor.executemany("""
                        INSERT INTO Gate_Change_Log (gate_id, changed_by, change_date, field_name, old_value, new_value)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, changes)

            # 2. Perform Update
            cursor.execute("""
                UPDATE Gate 
                SET [Gate Name] = ?, [From] = ?, [To] = ?, [UOM] = ?, [Unit] = ?, [Cost] = ?
                WHERE [Gate Name] = ?
            """, (gate_data.gate_name, gate_data.from_loc, gate_data.to_loc, 
                  gate_data.uom, gate_data.unit, gate_data.cost, 
                  gate_data.original_gate_name))
        else:
            # Insert New Gate
            cursor.execute("""
                INSERT INTO Gate ([Gate Name], [From], [To], [UOM], [Unit], [Cost])
                VALUES (?, ?, ?, ?, ?, ?)
            """, (gate_data.gate_name, gate_data.from_loc, gate_data.to_loc, 
                  gate_data.uom, gate_data.unit, gate_data.cost))
        
        conn.commit()
        conn.close()
        return {"message": "Gate saved successfully"}
    
    except Exception as e:
        logger.error(f"Error saving gate: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error saving gate: {str(e)}")

@app.get("/account/gates/{gate_id}/logs", response_model=List[GateLogItem])
def get_gate_logs(gate_id: int, user: dict = Depends(get_current_user)):
    try:
        conn = get_logistic_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, gate_id, changed_by, change_date, field_name, old_value, new_value
            FROM Gate_Change_Log
            WHERE gate_id = ?
            ORDER BY change_date DESC
        """, (gate_id,))
        rows = cursor.fetchall()
        logs = []
        for row in rows:
            logs.append({
                "id": row[0],
                "gate_id": row[1],
                "changed_by": row[2],
                "change_date": row[3],
                "field_name": row[4],
                "old_value": row[5],
                "new_value": row[6]
            })
        conn.close()
        return logs
    except Exception as e:
        logger.error(f"Error fetching logs: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching logs: {str(e)}")

@app.delete("/account/gates/{gate_id}")
def delete_gate(gate_id: int, user: dict = Depends(get_admin_user)): 
    try:
        conn = get_logistic_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM Gate_Change_Log WHERE gate_id = ?", (gate_id,))
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

@app.get("/account/item-pricing/{gate_id}")
def get_item_pricing(gate_id: int, user: dict = Depends(get_current_user)):
    try:
        conn = get_logistic_connection()
        cursor = conn.cursor()
        # UOM Removed
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

        # UOM Removed from check
        query_check = "SELECT [Pricing ID], [Transportation Cost] FROM Item_Pricing WHERE [Gate ID] = ? AND [Item ID] = ?"
        cursor.execute(query_check, (item_data.gate_id, item_data.original_item_code or item_data.item_code))
        existing = cursor.fetchone()

        if existing:
            pricing_id, old_cost = existing
            
            old_cost_str = str(old_cost).strip() if old_cost else ""
            new_cost_str = str(item_data.transportation_cost).strip() if item_data.transportation_cost else ""
            
            change_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            username = user['username']
            changes = []
            
            if old_cost_str != new_cost_str:
                 changes.append((pricing_id, username, change_date, 'Transportation Cost', old_cost_str, new_cost_str))

            if changes:
                 cursor.executemany("""
                    INSERT INTO Item_Change_Log (pricing_id, changed_by, change_date, field_name, old_value, new_value)
                    VALUES (?, ?, ?, ?, ?, ?)
                 """, changes)

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
                pricing_id
            ))
        else:
            while True:
                new_id = random.randint(10000000, 99999999)
                cursor.execute("SELECT 1 FROM Item_Pricing WHERE [Pricing ID] = ?", (new_id,))
                if not cursor.fetchone():
                    break
            insert_query = """
                INSERT INTO Item_Pricing 
                ([Pricing ID], [Gate ID], [Item ID], [Item Name], [Principal],
                 [Brand], [Transportation Cost])
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            cursor.execute(insert_query, (
                new_id, item_data.gate_id, item_data.item_code, item_data.item_name,
                item_data.principal, item_data.brand, item_data.transportation_cost
            ))

        conn.commit()
        conn.close()
        return {"message": "Item saved successfully"}
    except Exception as e:
        logger.error(f"Error saving item: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error saving item: {str(e)}")

@app.get("/account/items/{pricing_id}/logs", response_model=List[ItemLogItem])
def get_item_logs(pricing_id: int, user: dict = Depends(get_current_user)):
    try:
        conn = get_logistic_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, pricing_id, changed_by, change_date, field_name, old_value, new_value
            FROM Item_Change_Log
            WHERE pricing_id = ?
            ORDER BY change_date DESC
        """, (pricing_id,))
        rows = cursor.fetchall()
        logs = []
        for row in rows:
            logs.append({
                "id": row[0],
                "pricing_id": row[1],
                "changed_by": row[2],
                "change_date": row[3],
                "field_name": row[4],
                "old_value": row[5],
                "new_value": row[6]
            })
        conn.close()
        return logs
    except Exception as e:
        logger.error(f"Error fetching logs: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching logs: {str(e)}")

@app.delete("/account/item-pricing/{gate_id}/{item_code}")
def delete_item_pricing(gate_id: int, item_code: str, user: dict = Depends(get_admin_user)): 
    try:
        conn = get_logistic_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT [Pricing ID] FROM Item_Pricing WHERE [Gate ID] = ? AND [Item ID] = ?", (gate_id, item_code))
        row = cursor.fetchone()
        if row:
             pricing_id = row[0]
             cursor.execute("DELETE FROM Item_Change_Log WHERE pricing_id = ?", (pricing_id,))

        cursor.execute("DELETE FROM Item_Pricing WHERE [Gate ID] = ? AND [Item ID] = ?", (gate_id, item_code))
        if cursor.rowcount == 0:
            conn.close()
            raise HTTPException(status_code=404, detail="Item not found")
        conn.commit()
        conn.close()
        return {"message": "Item deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting item: {str(e)}")

@app.get("/dwbi/items/search")
def search_dwbi_items(q: str = Query(..., min_length=2)):
    try:
        conn = get_dwbi_connection()
        cursor = conn.cursor()
        query_sql = """
            SELECT TOP 50 ItemCode, ItemName, ItemGroupName, BrandName 
            FROM _ItemAllinone 
            WHERE ItemCode LIKE ? OR ItemName LIKE ?
        """
        search_term = f"%{q}%"
        cursor.execute(query_sql, (search_term, search_term))
        rows = cursor.fetchall()
        
        items = []
        for row in rows:
            items.append({
                "item_code": row[0],
                "item_name": row[1],
                "principal": row[2], 
                "brand": row[3]      
            })
        conn.close()
        return {"items": items}
    except Exception as e:
        logger.error(f"Error searching DWBI items: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error searching items: {str(e)}")

@app.get("/dwbi/items/validate")
def validate_dwbi_item(code: str = Query(...)):
    try:
        conn = get_dwbi_connection()
        cursor = conn.cursor()
        query = "SELECT ItemCode, ItemName, ItemGroupName, BrandName FROM _ItemAllinone WHERE ItemCode = ?"
        cursor.execute(query, (code,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                "valid": True,
                "item": {
                    "item_code": row[0],
                    "item_name": row[1],
                    "principal": row[2],
                    "brand": row[3]
                }
            }
        return {"valid": False}
    except Exception as e:
        logger.error(f"Error validating item: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Validation error: {str(e)}")

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
    doc_nums: List[str] = Query(...),
    manual_total_cost: Optional[float] = None, 
    additional_charges: Optional[float] = 0.0
):
    try:
        if not doc_nums:
            raise HTTPException(status_code=400, detail="No Doc Nums provided")
        result = _perform_calculation_logic(
            gate_name=gate_name, 
            doc_nums=doc_nums, 
            manual_total_cost=manual_total_cost, 
            additional_charges=additional_charges
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Calculation error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Calculation error: {str(e)}")

@app.get("/doc-nums")
def get_doc_nums():
    try:
        conn = get_dwbi_connection()
        cursor = conn.cursor()
        # Fetching DocNum and maximum DocDate grouping by DocNum
        cursor.execute("""
            SELECT DocNum, MAX(DocDate) 
            FROM PG_TransferDetails 
            WHERE DocNum IS NOT NULL 
            GROUP BY DocNum 
            ORDER BY DocNum DESC
        """)
        rows = cursor.fetchall()
        doc_nums = []
        for row in rows:
            doc_num = row[0]
            doc_date_val = row[1]
            doc_date_str = ""
            if isinstance(doc_date_val, datetime.datetime):
                doc_date_str = doc_date_val.strftime("%Y-%m-%d")
            elif isinstance(doc_date_val, str) and len(doc_date_val) >= 10:
                doc_date_str = doc_date_val[:10]
            else:
                doc_date_str = str(doc_date_val) if doc_date_val else ""
            
            # Now returning dict objects
            doc_nums.append({"doc_num": doc_num, "doc_date": doc_date_str})
        conn.close()
        return {"doc_nums": doc_nums}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/products-by-doc-nums")
def get_products_by_doc_nums(doc_nums: List[str] = Query(..., alias="doc_nums")):
    try:
        if not doc_nums:
            return {"products": [], "total_weight": 0}
        conn = get_dwbi_connection()
        cursor = conn.cursor()
        placeholders = ','.join('?' * len(doc_nums))
        
        # BatchQty Removed
        query = f"""
            SELECT ItemCode, MAX(Dscription), MAX(UoM), SUM(ItemWeight), DocNum, SUM(BatchQtyByCtn)
            FROM PG_TransferDetails 
            WHERE DocNum IN ({placeholders}) 
            GROUP BY DocNum, ItemCode
            ORDER BY DocNum, ItemCode
        """
        cursor.execute(query, doc_nums)
        rows = cursor.fetchall()
        products = []
        total_weight = 0.0
        for row in rows:
            weight = float(row[3]) if row[3] else 0.0
            total_weight += weight
            products.append({
                "code": row[0] or "",
                "name": row[1] or "",
                "uom": row[2] or "",
                "weight": weight,
                "ctns": round(float(row[5])) if len(row) > 5 and row[5] is not None else 0
            })
        conn.close()
        return {"products": products, "total_weight": round(total_weight, 2)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/products/{doc_num}")
def get_products_by_doc_num(doc_num: str):
    try:
        conn = get_dwbi_connection()
        cursor = conn.cursor()
        # BatchQty Removed
        cursor.execute("""
            SELECT ItemCode, MAX(Dscription), MAX(UoM), SUM(ItemWeight), DocNum, SUM(BatchQtyByCtn)
            FROM PG_TransferDetails 
            WHERE DocNum = ? 
            GROUP BY DocNum, ItemCode
            ORDER BY DocNum, ItemCode
        """, (doc_num,))
        rows = cursor.fetchall()
        if not rows:
            conn.close()
            raise HTTPException(status_code=404, detail="No products found")
        products = []
        total_weight = 0.0
        for row in rows:
            weight = float(row[3]) if row[3] else 0.0
            total_weight += weight
            products.append({
                "item_code": row[0] or "",
                "description": row[1] or "",
                "uom": row[2] or "",
                "item_weight": weight,
                "ctns": round(float(row[5])) if len(row) > 5 and row[5] is not None else 0
            })
        conn.close()
        return {"products": products, "total_weight": round(total_weight, 2)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)