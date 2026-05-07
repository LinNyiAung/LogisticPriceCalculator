import logging
import pyodbc
import sqlite3
import json
import datetime
import calendar
import time
import random
from contextlib import asynccontextmanager
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
from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import Request 

# --- Auth Configuration ---
SECRET_KEY = "CHANGE_THIS_TO_A_SUPER_SECRET_KEY"  # IMPORTANT: Change this!
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 43200 # 30 days expiration

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# --- Initialization ---

def startup_db():
    """Ensure logistic.db has the required tables and updated roles"""
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
        
        # Item_Pricing table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Item_Pricing (
                [Pricing ID] INTEGER PRIMARY KEY,
                [Gate ID] INTEGER,
                [BU] TEXT,
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
                [doc_nums] TEXT,
                [manual_total_cost] REAL,
                [additional_charges] REAL,
                [final_total_cost] REAL,
                [channel] TEXT,
                [status] TEXT DEFAULT 'saved',
                [created_by] TEXT,
                [submitted_by] TEXT,
                [submitted_at] TEXT,
                [claimed_by] TEXT,
                [claimed_at] TEXT,
                [calculated_products] TEXT
            )
        """)

        # Rate Cart Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Rate_Cart (
                [id] INTEGER PRIMARY KEY AUTOINCREMENT,
                [location] TEXT UNIQUE,
                [cost] REAL
            )
        """)
        
        # Daily Report History Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Daily_Report_History (
                [target_date] TEXT PRIMARY KEY,
                [item_report_json] TEXT,
                [township_report_json] TEXT,
                [created_at] TEXT
            )
        """)
        
        # User Activity Log Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS User_Activity_Log (
                [id] INTEGER PRIMARY KEY AUTOINCREMENT,
                [username] TEXT,
                [action] TEXT,
                [details] TEXT,
                [timestamp] TEXT
            )
        """)

        # Safely attempt to add columns for existing databases
        try: cursor.execute("ALTER TABLE Calculation_History ADD COLUMN [channel] TEXT")
        except sqlite3.OperationalError: pass
        try: cursor.execute("ALTER TABLE Calculation_History ADD COLUMN [status] TEXT DEFAULT 'saved'")
        except sqlite3.OperationalError: pass
        try: cursor.execute("ALTER TABLE Calculation_History ADD COLUMN [created_by] TEXT")
        except sqlite3.OperationalError: pass
        try: cursor.execute("ALTER TABLE Calculation_History ADD COLUMN [submitted_by] TEXT")
        except sqlite3.OperationalError: pass
        try: cursor.execute("ALTER TABLE Calculation_History ADD COLUMN [submitted_at] TEXT")
        except sqlite3.OperationalError: pass
        try: cursor.execute("ALTER TABLE Calculation_History ADD COLUMN [claimed_by] TEXT")
        except sqlite3.OperationalError: pass
        try: cursor.execute("ALTER TABLE Calculation_History ADD COLUMN [claimed_at] TEXT")
        except sqlite3.OperationalError: pass
        try: cursor.execute("ALTER TABLE Calculation_History ADD COLUMN [calculated_products] TEXT")
        except sqlite3.OperationalError: pass
        try: cursor.execute("ALTER TABLE Item_Pricing ADD COLUMN [BU] TEXT")
        except sqlite3.OperationalError: pass
        
        # --- User Table ---
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Users (
                username TEXT PRIMARY KEY,
                hashed_password TEXT,
                role TEXT
            )
        """)

        # --- Roles Table ---
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Roles (
                name TEXT PRIMARY KEY,
                permissions TEXT
            )
        """)

        # --- Reference Tables (Locations, UOMs, Channels, Rate Cart Locations) ---
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Locations (
                [id] INTEGER PRIMARY KEY AUTOINCREMENT,
                [name] TEXT UNIQUE
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Rate_Cart_Locations (
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

        # --- Rate Cart Change Log Table ---
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Rate_Cart_Change_Log (
                [id] INTEGER PRIMARY KEY AUTOINCREMENT,
                [location] TEXT,
                [changed_by] TEXT,
                [change_date] TEXT,
                [field_name] TEXT,
                [old_value] TEXT,
                [new_value] TEXT,
                FOREIGN KEY([location]) REFERENCES Rate_Cart([location])
            )
        """)
        
        
        # --- Location Mapping Table ---
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Location_Mapping (
                [id] INTEGER PRIMARY KEY AUTOINCREMENT,
                [to_location] TEXT UNIQUE,
                [branch_code] TEXT
            )
        """)
        
        # Pre-seed with existing defaults to save you time
        cursor.execute("SELECT COUNT(*) FROM Location_Mapping")
        if cursor.fetchone()[0] == 0:
            default_mappings = [
                ("Yangon", "YGN"), ("Mandalay", "MDY"), ("Naypyitaw", "NPT"),
                ("Magaway", "MGW"), ("Taunggyi", "TGI"), ("Taunggu", "TGU"),
                ("Pathein", "PTN"), ("Mawlamyine", "MLM"), ("Bago", "BGO")
            ]
            cursor.executemany("INSERT INTO Location_Mapping (to_location, branch_code) VALUES (?, ?)", default_mappings)
            
        
        # --- SEED DEFAULTS AND MIGRATE TO GRANULAR PERMISSIONS ---
        cursor.execute("SELECT COUNT(*) FROM Roles")
        if cursor.fetchone()[0] == 0:
            default_roles = [
                ('admin', json.dumps([
                    'view_calculator', 'view_history',
                    'view_users', 'add_user', 'edit_user', 'delete_user',
                    'view_roles', 'add_role', 'edit_role', 'delete_role',
                    'view_gates', 'add_gate', 'edit_gate', 'delete_gate',
                    'view_items', 'add_item', 'edit_item', 'delete_item',
                    'view_references', 'add_reference', 'delete_reference',
                    'view_all_history', 'delete_history', 'claim_calculation', 'submit_calculation',
                    'view_rate_carts', 'add_rate_cart', 'edit_rate_cart', 'delete_rate_cart',
                    'view_daily_report', 'view_dashboard', 'view_activity_logs' 
                ])),
                ('account', json.dumps([
                    'view_calculator', 'view_history',
                    'view_gates', 'add_gate', 'edit_gate', 
                    'view_items', 'add_item', 'edit_item', 
                    'view_references', 'add_reference', 'delete_reference',
                    'claim_calculation', 'view_rate_carts', 'add_rate_cart', 'edit_rate_cart'
                ])),
                ('logistic', json.dumps(['view_calculator', 'view_history', 'submit_calculation', 'view_gates', 'view_items', 'view_references', 'view_rate_carts']))
            ]
            cursor.executemany("INSERT INTO Roles (name, permissions) VALUES (?, ?)", default_roles)

        # Create default users
        cursor.execute("SELECT * FROM Users WHERE username = 'account'")
        if not cursor.fetchone():
            default_pw = pwd_context.hash("account123") 
            cursor.execute("INSERT INTO Users (username, hashed_password, role) VALUES (?, ?, ?)", ('account', default_pw, 'account'))
            
        cursor.execute("SELECT * FROM Users WHERE username = 'logistic'")
        if not cursor.fetchone():
            log_pw = pwd_context.hash("log123")
            cursor.execute("INSERT INTO Users (username, hashed_password, role) VALUES (?, ?, ?)", ('logistic', log_pw, 'logistic'))
            
        cursor.execute("SELECT * FROM Users WHERE username = 'admin'")
        if not cursor.fetchone():
            admin_pw = pwd_context.hash("admin123")
            cursor.execute("INSERT INTO Users (username, hashed_password, role) VALUES (?, ?, ?)", ('admin', admin_pw, 'admin'))

        # Seed references
        default_locs = [
            ('Yangon',), ('Mandalay',), ('Naypyitaw',), ('Magaway',), 
            ('Taunggyi',), ('Taunggu',), ('Pathein',), ('Mawlamyine',),
            ('Taungtwingyi',), ('Meikhtila',), ('Dawei',), ('Myingyan',),
            ('Yae',), ('Chauk',), ('Aunglan',), ('Danuphyu',),
            ('Ngathaingchaung',), ('Yamethin',), ('Phyue',), ('Kyauktagar',),
            ('Nyaunglaypin',), ('Nyaungoo',), ('Kyaukpadaung',), ('Myeik',),
            ('Twantay',)
        ]

        default_locsrc = [
            ('YGN',), ('MDY',), ('BGO',), ('MGW',), 
            ('TGI',), ('TGU',), ('PTN',), ('MLM',),
            ('NPT',)
        ]

        cursor.execute("SELECT COUNT(*) FROM Locations")
        if cursor.fetchone()[0] == 0:
            cursor.executemany("INSERT INTO Locations (name) VALUES (?)", default_locs)

        cursor.execute("SELECT COUNT(*) FROM Rate_Cart_Locations")
        if cursor.fetchone()[0] == 0:
            cursor.executemany("INSERT INTO Rate_Cart_Locations (name) VALUES (?)", default_locsrc)

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
        
        # --- Start Scheduler ---
        scheduler = BackgroundScheduler()
        
        # Schedule daily job at 23:55 (11:55 PM) to compute end-of-day reports
        scheduler.add_job(daily_job_generator, 'cron', hour=23, minute=55)
        
        # Schedule daily job at 01:00 AM to clean up 1-month-old activity logs
        scheduler.add_job(cleanup_old_activity_logs, 'cron', hour=1, minute=0)
        
        scheduler.start()
        logger.info("Daily end-of-day report and activity log cleanup schedulers started.")

    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    startup_db()
    yield

app = FastAPI(lifespan=lifespan)

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

# --- Helper: Activity Logger ---
def log_user_activity(username: str, action: str, details: str = ""):
    """Inserts a new record into the User_Activity_Log table."""
    try:
        conn = get_logistic_connection()
        cursor = conn.cursor()
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            "INSERT INTO User_Activity_Log (username, action, details, timestamp) VALUES (?, ?, ?, ?)",
            (username, action, details, now_str)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Failed to log user activity: {str(e)}")

def cleanup_old_activity_logs():
    """Automated job to delete activity logs older than 30 days."""
    try:
        conn = get_logistic_connection()
        cursor = conn.cursor()
        
        # Calculate the threshold date (30 days ago)
        threshold_date = (datetime.datetime.now() - datetime.timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute("DELETE FROM User_Activity_Log WHERE timestamp < ?", (threshold_date,))
        deleted_count = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} system activity logs older than {threshold_date}.")
    except Exception as e:
        logger.error(f"Failed to clean up old activity logs: {str(e)}")

# --- Pydantic Models ---

class LocationMappingItem(BaseModel):
    to_location: str
    branch_code: str

class RateCartData(BaseModel):
    location: str
    cost: float

class RateCartLogItem(BaseModel):
    id: int
    location: str
    changed_by: str
    change_date: str
    field_name: str
    old_value: Optional[str]
    new_value: Optional[str]

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
    bu: Optional[str] = ""
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
    calculated_products: List[Any] = []

class ReferenceItem(BaseModel):
    name: str

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

class RoleCreate(BaseModel):
    name: str
    permissions: List[str]

class RoleUpdate(BaseModel):
    permissions: List[str]

class RoleResponse(BaseModel):
    name: str
    permissions: List[str]

class Token(BaseModel):
    access_token: str
    token_type: str
    role: str
    username: str
    permissions: List[str]
    
class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

class ActivityLogResponse(BaseModel):
    id: int
    username: str
    action: str
    details: str
    timestamp: str

class ActivityLogPaginatedResponse(BaseModel):
    total: int
    logs: List[ActivityLogResponse]

# --- Auth Helpers ---
    
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
        permissions: list = payload.get("permissions", [])
        if username is None:
            raise credentials_exception
        return {"username": username, "role": role, "permissions": permissions}
    except JWTError:
        raise credentials_exception

def require_permission(perm: str):
    def permission_checker(current_user: dict = Depends(get_current_user)):
        if perm not in current_user.get("permissions", []):
            raise HTTPException(status_code=403, detail=f"Requires '{perm}' permission")
        return current_user
    return permission_checker

# --- Login & Token ---

@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    conn = get_logistic_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT u.username, u.hashed_password, u.role, r.permissions 
        FROM Users u
        LEFT JOIN Roles r ON u.role = r.name
        WHERE u.username = ?
    """, (form_data.username,))
    user = cursor.fetchone()
    conn.close()
    
    if not user or not verify_password(form_data.password, user[1]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    permissions = json.loads(user[3]) if user[3] else []
    access_token = create_access_token(data={"sub": user[0], "role": user[2], "permissions": permissions})
    
    # Log successful login
    log_user_activity(user[0], "LOGIN", "User authenticated successfully")
    
    return {"access_token": access_token, "token_type": "bearer", "role": user[2], "username": user[0], "permissions": permissions}

# --- System Activity Log Endpoint ---

@app.get("/admin/activity-logs", response_model=ActivityLogPaginatedResponse)
def get_activity_logs(
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    timestamp: Optional[str] = Query(None, description="Filter by timestamp"),
    username: Optional[str] = Query(None, description="Filter by username"),
    action: Optional[str] = Query(None, description="Filter by action type"),
    details: Optional[str] = Query(None, description="Filter by details"),
    user: dict = Depends(require_permission("view_activity_logs"))
):
    try:
        conn = get_logistic_connection()
        cursor = conn.cursor()
        
        query = "SELECT id, username, action, details, timestamp FROM User_Activity_Log WHERE 1=1"
        count_query = "SELECT COUNT(*) FROM User_Activity_Log WHERE 1=1"
        params = []
        
        # Dynamically build the WHERE clause based on provided filters
        if timestamp:
            query += " AND timestamp LIKE ?"
            count_query += " AND timestamp LIKE ?"
            params.append(f"%{timestamp}%")
        if username:
            query += " AND username LIKE ?"
            count_query += " AND username LIKE ?"
            params.append(f"%{username}%")
        if action:
            query += " AND action LIKE ?"
            count_query += " AND action LIKE ?"
            params.append(f"%{action}%")
        if details:
            query += " AND details LIKE ?"
            count_query += " AND details LIKE ?"
            params.append(f"%{details}%")
            
        query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        
        # Get the total count for pagination
        cursor.execute(count_query, params)
        total_count = cursor.fetchone()[0]
        
        # Get the paginated rows
        params.extend([limit, offset])
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        conn.close()
        
        logs = [{"id": r[0], "username": r[1], "action": r[2], "details": r[3], "timestamp": r[4]} for r in rows]
        return {"total": total_count, "logs": logs}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching activity logs: {str(e)}")

# --- Role Management Endpoints ---

@app.get("/roles", response_model=List[RoleResponse])
def get_all_roles(user: dict = Depends(require_permission("view_roles"))):
    try:
        conn = get_logistic_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name, permissions FROM Roles ORDER BY name")
        rows = cursor.fetchall()
        conn.close()
        return [{"name": row[0], "permissions": json.loads(row[1]) if row[1] else []} for row in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching roles: {str(e)}")

@app.post("/roles")
def create_role(role_data: RoleCreate, user: dict = Depends(require_permission("add_role"))):
    try:
        conn = get_logistic_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM Roles WHERE name = ?", (role_data.name,))
        if cursor.fetchone():
            conn.close()
            raise HTTPException(status_code=400, detail="Role already exists")
        cursor.execute("INSERT INTO Roles (name, permissions) VALUES (?, ?)", 
                      (role_data.name, json.dumps(role_data.permissions)))
        conn.commit()
        conn.close()
        
        log_user_activity(user['username'], "CREATE_ROLE", f"Created role: {role_data.name}")
        return {"message": "Role created successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating role: {str(e)}")

@app.put("/roles/{role_name}")
def update_role(role_name: str, role_data: RoleUpdate, user: dict = Depends(require_permission("edit_role"))):
    try:
        conn = get_logistic_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE Roles SET permissions = ? WHERE name = ?", (json.dumps(role_data.permissions), role_name))
        conn.commit()
        conn.close()
        
        log_user_activity(user['username'], "UPDATE_ROLE", f"Updated permissions for role: {role_name}")
        return {"message": "Role updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating role: {str(e)}")

@app.delete("/roles/{role_name}")
def delete_role(role_name: str, user: dict = Depends(require_permission("delete_role"))):
    if role_name in ['admin', 'account', 'logistic']:
        raise HTTPException(status_code=400, detail="Cannot delete default system roles")
    try:
        conn = get_logistic_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM Users WHERE role = ?", (role_name,))
        if cursor.fetchone()[0] > 0:
            conn.close()
            raise HTTPException(status_code=400, detail="Cannot delete role currently assigned to users")
        cursor.execute("DELETE FROM Roles WHERE name = ?", (role_name,))
        conn.commit()
        conn.close()
        
        log_user_activity(user['username'], "DELETE_ROLE", f"Deleted role: {role_name}")
        return {"message": "Role deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting role: {str(e)}")

# --- User Management Endpoints ---

@app.get("/users", response_model=List[UserResponse])
def get_all_users(user: dict = Depends(require_permission("view_users"))):
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
def create_user(user_data: UserCreate, user: dict = Depends(require_permission("add_user"))):
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
        
        log_user_activity(user['username'], "CREATE_USER", f"Created user: {user_data.username} with role: {user_data.role}")
        return {"message": "User created successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating user: {str(e)}")

@app.put("/users/{username}")
def update_user(username: str, user_data: UserUpdate, user: dict = Depends(require_permission("edit_user"))):
    try:
        conn = get_logistic_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT username FROM Users WHERE username = ?", (username,))
        if not cursor.fetchone():
            conn.close()
            raise HTTPException(status_code=404, detail="User not found")
            
        changes = []
        if user_data.password:
            hashed_pw = pwd_context.hash(user_data.password)
            cursor.execute("UPDATE Users SET hashed_password = ? WHERE username = ?", (hashed_pw, username))
            changes.append("password")
        if user_data.role:
            cursor.execute("UPDATE Users SET role = ? WHERE username = ?", (user_data.role, username))
            changes.append(f"role to {user_data.role}")
            
        conn.commit()
        conn.close()
        
        log_user_activity(user['username'], "UPDATE_USER", f"Updated user: {username} ({', '.join(changes)})")
        return {"message": "User updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating user: {str(e)}")

@app.delete("/users/{username}")
def delete_user(username: str, user: dict = Depends(require_permission("delete_user"))):
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
        
        log_user_activity(user['username'], "DELETE_USER", f"Deleted user: {username}")
        return {"message": "User deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting user: {str(e)}")
    
@app.put("/users/me/password")
def change_password(data: ChangePasswordRequest, current_user: dict = Depends(get_current_user)):
    username = current_user["username"]
    
    try:
        conn = get_logistic_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT hashed_password FROM Users WHERE username = ?", (username,))
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            raise HTTPException(status_code=404, detail="User not found")
            
        current_hashed_password = row[0]
        
        if not verify_password(data.old_password, current_hashed_password):
            conn.close()
            raise HTTPException(status_code=400, detail="Incorrect old password")
            
        new_hashed_password = pwd_context.hash(data.new_password)
        cursor.execute("UPDATE Users SET hashed_password = ? WHERE username = ?", (new_hashed_password, username))
        
        conn.commit()
        conn.close()
        
        log_user_activity(username, "CHANGE_PASSWORD", "User changed their own password")
        return {"message": "Password changed successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error changing password: {str(e)}")

# --- Helper Functions for Calculation ---
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

def get_rounded_ctns(val):
    if not val:
        return 0
    try:
        f_val = float(val)
        if f_val <= 0:
            return 0
        return max(1, round(f_val))
    except (ValueError, TypeError):
        return 0

def _perform_calculation_logic(gate_name, doc_nums, from_loc=None, to_loc=None, manual_total_cost=None, additional_charges=0.0):
    add_charges = float(additional_charges) if additional_charges is not None else 0.0

    pg_nums = [str(d).replace("PG - ", "").replace("PG-", "") for d in doc_nums if not str(d).startswith("PDG")]
    pdg_nums = [str(d).replace("PDG - ", "").replace("PDG-", "") for d in doc_nums if str(d).startswith("PDG")]

    pick_rows = []

    try:
        conn_dwbi = get_dwbi_connection()
        cursor_dwbi = conn_dwbi.cursor()

        if pg_nums:
            placeholders = ','.join('?' * len(pg_nums))
            query_pg = f"""
                SELECT ItemCode, MAX(Dscription), MAX(UoM), SUM(ItemWeight), MAX(DocDate), DocNum, MAX(Principal), SUM(BatchQtyByCtn), MAX(Brand), 'PG'
                FROM PG_Transfer_Details 
                WHERE DocNum IN ({placeholders}) 
                GROUP BY DocNum, ItemCode
                ORDER BY DocNum, ItemCode
            """
            cursor_dwbi.execute(query_pg, pg_nums)
            pick_rows.extend(cursor_dwbi.fetchall())

        if pdg_nums:
            placeholders = ','.join('?' * len(pdg_nums))
            query_pdg = f"""
                SELECT ItemCode, MAX(Dscription), MAX(UoM), SUM(LineTotalWeight), MAX(DocDate), DocNum, MAX(Principal), SUM(QtyCtn), MAX(Brand), 'PDG'
                FROM PDG_Transfer_Details 
                WHERE DocNum IN ({placeholders}) 
                GROUP BY DocNum, ItemCode
                ORDER BY DocNum, ItemCode
            """
            cursor_dwbi.execute(query_pdg, pdg_nums)
            pick_rows.extend(cursor_dwbi.fetchall())

        conn_dwbi.close()
    except Exception as e:
        raise Exception(f"Error fetching transfer details: {str(e)}")
    
    if not pick_rows:
        raise Exception("No products found for the selected Doc Nums")
    
    try:
        conn_log = get_logistic_connection()
        cursor_log = conn_log.cursor()
        
        if from_loc and to_loc:
            cursor_log.execute("SELECT [Gate ID], [From], [To], [Cost], [Unit] FROM Gate WHERE [Gate Name] = ? AND [From] = ? AND [To] = ?", (gate_name, from_loc, to_loc))
        else:
            cursor_log.execute("SELECT [Gate ID], [From], [To], [Cost], [Unit] FROM Gate WHERE [Gate Name] = ?", (gate_name,))
            
        gate_row = cursor_log.fetchone()
        
        cursor_log.execute("SELECT [Log-Pric], [Code], [Name], [Dept], [Principal], [Description] FROM Branch_Code")
        branch_code_map = {row[0].strip().lower(): {
            "Code": row[1], "Name": row[2], "Dept": row[3], "Principal": row[4], "Description": row[5]
        } for row in cursor_log.fetchall() if row[3]}

        cursor_log.execute("SELECT [Dept], [Principal], [Log-Pric] FROM SD_Code")
        sd_code_map = {row[2].strip().lower(): {
            "Dept": row[0], "Principal": row[1]
        } for row in cursor_log.fetchall() if row[2]}

    except Exception as e:
        raise Exception(f"Error fetching local configs: {str(e)}")
    
    if not gate_row:
        if 'conn_log' in locals(): conn_log.close()
        raise Exception(f"Gate {gate_name} not found")
        
    gate_id = gate_row[0]
    matched_from_loc = gate_row[1]
    matched_to_loc = gate_row[2]
    cost = float(gate_row[3] or 0)
    gate_unit = float(gate_row[4]) if gate_row[4] else 1.0
    
    cursor_log.execute("SELECT [Item ID], [Transportation Cost] FROM Item_Pricing WHERE [Gate ID] = ?", (gate_id,))
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

    if cost > 0: calc_type = "gate_pricing"
    else: calc_type = "direct_pricing"

    calculated_products = []
    total_cost = 0.0
    estimated_total_cost = 0.0

    if calc_type == "gate_pricing":
        ton_items = []
        direct_items = []
        ton_cost_total = 0.0
        
        for row in pick_rows:
            doc_date_val = row[4]
            if isinstance(doc_date_val, datetime.datetime):
                doc_date_str = doc_date_val.strftime("%Y-%m-%d")
            elif isinstance(doc_date_val, str) and len(doc_date_val) >= 10:
                doc_date_str = doc_date_val[:10]
            else:
                doc_date_str = str(doc_date_val) if doc_date_val else ""

            principal_val = row[6] or ""
            brand_val = row[8] or ""
            bc_info = branch_code_map.get(principal_val.strip().lower(), {})
            sd_info = sd_code_map.get(principal_val.strip().lower(), {})

            item_data = {
                "code": row[0] if row[0] else "",
                "name": row[1] if row[1] else "",
                "uom": row[2] if row[2] else "",
                "weight": float(row[3]) if row[3] else 0.0,
                "doc_date": doc_date_str,         
                "sin_no": f"{row[9]} - {str(row[5])}" if row[5] else "",           
                "principal": principal_val,
                "brand": brand_val,
                "ctns": get_rounded_ctns(row[7]),
                "bu": row[9],
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
                estimated_total_cost += (item_data['ctns'] * p_val)
                item_data['standard_unit_cost'] = p_val
                direct_items.append(item_data)
            else:
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
            if total_direct_ctns > 0: direct_unit_cost = remainder / total_direct_ctns
            total_cost = manual_total_cost
        else:
            total_cost = estimated_total_cost

        for item in ton_items:
            avg_unit_cost = item['total_cost'] / item['ctns'] if item['ctns'] > 0 else 0
            calculated_products.append({
                **item, "calculation_type": "weight", "system_rate": None,
                "unit_cost": avg_unit_cost, "total_cost": item['total_cost'] 
            })
        
        for item in direct_items:
            final_unit_cost = direct_unit_cost if manual_total_cost is not None else item['standard_unit_cost']
            final_item_cost = item['ctns'] * final_unit_cost
            calculated_products.append({
                **item, "calculation_type": "direct_split" if manual_total_cost else "direct",
                "system_rate": item['standard_unit_cost'], "unit_cost": final_unit_cost, "total_cost": final_item_cost
            })

    elif calc_type == "direct_pricing":
        for row in pick_rows:
            doc_date_val = row[4]
            if isinstance(doc_date_val, datetime.datetime):
                doc_date_str = doc_date_val.strftime("%Y-%m-%d")
            elif isinstance(doc_date_val, str) and len(doc_date_val) >= 10:
                doc_date_str = doc_date_val[:10]
            else:
                doc_date_str = str(doc_date_val) if doc_date_val else ""

            item_code = row[0] if row[0] else ""
            pricing_info = item_pricing.get(item_code, {})
            
            weight = float(row[3]) if row[3] else 0.0
            ctns = get_rounded_ctns(row[7])
            principal_val = row[6] or ""
            brand_val = row[8] or ""
            bc_info = branch_code_map.get(principal_val.strip().lower(), {})
            sd_info = sd_code_map.get(principal_val.strip().lower(), {})

            unit_cost = pricing_info.get('value', 0.0) or 0.0
            item_cost = ctns * unit_cost
            
            total_cost += item_cost
            estimated_total_cost += item_cost
            
            calculated_products.append({
                "code": item_code, "name": row[1] if row[1] else "", "ctns": ctns,
                "uom": row[2] if row[2] else "", "weight": weight, "doc_date": doc_date_str,       
                "sin_no": f"{row[9]} - {str(row[5])}" if row[5] else "", "principal": principal_val, "brand": brand_val,
                "bu": row[9], "b_code": bc_info.get("Code", ""), "b_name": bc_info.get("Name", ""), 
                "b_dept": bc_info.get("Dept", ""), "b_principal": bc_info.get("Principal", ""), 
                "b_desc": bc_info.get("Description", ""), "s_dept": sd_info.get("Dept", ""), 
                "s_principal": sd_info.get("Principal", ""), "calculation_type": "direct", 
                "system_rate": unit_cost if unit_cost > 0 else None,
                "unit_cost": unit_cost, "total_cost": item_cost
            })

    if add_charges != 0 and calculated_products:
        total_ctns = sum(p.get('ctns', 0) for p in calculated_products)
        for p in calculated_products:
            proportion = p.get('ctns', 0) / total_ctns
            extra_cost = add_charges * proportion
            p['total_cost'] += extra_cost
            if p['ctns'] > 0: 
                p['unit_cost'] = p['total_cost'] / p['ctns']

    calculated_products.sort(key=lambda x: (x.get('sin_no', ''), x['code']))
    total_cost += add_charges
    estimated_total_cost += add_charges
    
    return {
        "calculation_type": calc_type, "gate_name": gate_name, "from_loc": matched_from_loc,
        "to_loc": matched_to_loc, "cost": cost, "additional_charges": add_charges,
        "calculated_products": calculated_products, "total_cost": total_cost,
        "estimated_total_cost": estimated_total_cost
    }

# --- Rate Cart Endpoints ---

@app.get("/account/rate-cuts")
def get_rate_carts(user: dict = Depends(require_permission("view_rate_carts"))):
    try:
        conn = get_logistic_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT location, cost FROM Rate_Cart ORDER BY location")
        rows = cursor.fetchall()
        conn.close()
        return [{"location": row[0], "cost": row[1]} for row in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading rate carts: {str(e)}")

@app.post("/account/rate-cuts")
def save_rate_cart(data: RateCartData, user: dict = Depends(get_current_user)):
    perms = user.get("permissions", [])
    try:
        conn = get_logistic_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT cost FROM Rate_Cart WHERE location = ?", (data.location,))
        existing = cursor.fetchone()
        
        change_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        username = user['username']

        if existing:
            if "edit_rate_cart" not in perms:
                conn.close()
                raise HTTPException(status_code=403, detail="Requires 'edit_rate_cart' permission")
            
            old_cost = existing[0]
            if float(old_cost) != float(data.cost):
                cursor.execute("""
                    INSERT INTO Rate_Cart_Change_Log (location, changed_by, change_date, field_name, old_value, new_value)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (data.location, username, change_date, 'Cost', str(old_cost), str(data.cost)))

            cursor.execute("UPDATE Rate_Cart SET cost = ? WHERE location = ?", (data.cost, data.location))
            log_user_activity(username, "UPDATE_RATE_CART", f"Updated rate cart for {data.location}")
        else:
            if "add_rate_cart" not in perms:
                conn.close()
                raise HTTPException(status_code=403, detail="Requires 'add_rate_cart' permission")
            cursor.execute("INSERT INTO Rate_Cart (location, cost) VALUES (?, ?)", (data.location, data.cost))
            log_user_activity(username, "ADD_RATE_CART", f"Added rate cart for {data.location}")
            
        conn.commit()
        conn.close()
        return {"message": "Rate cart saved successfully"}
    except HTTPException: raise
    except Exception as e: raise HTTPException(status_code=500, detail=f"Error saving rate cart: {str(e)}")

@app.delete("/account/rate-cuts/{location}")
def delete_rate_cart(location: str, user: dict = Depends(require_permission("delete_rate_cart"))):
    try:
        conn = get_logistic_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Rate_Cart_Change_Log WHERE location = ?", (location,))
        cursor.execute("DELETE FROM Rate_Cart WHERE location = ?", (location,))
        
        if cursor.rowcount == 0:
            conn.close()
            raise HTTPException(status_code=404, detail="Rate cart not found")
        
        conn.commit()
        conn.close()
        
        log_user_activity(user['username'], "DELETE_RATE_CART", f"Deleted rate cart for {location}")
        return {"message": "Rate cart deleted successfully"}
    except HTTPException: raise
    except Exception as e: raise HTTPException(status_code=500, detail=f"Error deleting rate cart: {str(e)}")

@app.get("/account/rate-cuts/{location}/logs", response_model=List[RateCartLogItem])
def get_rate_cart_logs(location: str, user: dict = Depends(get_current_user)):
    try:
        conn = get_logistic_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, location, changed_by, change_date, field_name, old_value, new_value FROM Rate_Cart_Change_Log WHERE location = ? ORDER BY change_date DESC", (location,))
        rows = cursor.fetchall()
        logs = [{"id": r[0], "location": r[1], "changed_by": r[2], "change_date": r[3], "field_name": r[4], "old_value": r[5], "new_value": r[6]} for r in rows]
        conn.close()
        return logs
    except Exception as e: raise HTTPException(status_code=500, detail=f"Error fetching rate cart logs: {str(e)}")


# --- Daily Report Logic & Automation ---

def get_rate_carts_for_date(target_date: str) -> dict:
    conn = get_logistic_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT location, cost FROM Rate_Cart")
    current_costs = {row[0].strip().upper(): float(row[1]) for row in cursor.fetchall()}
    
    query_threshold = target_date + " 23:59:59"
    cursor.execute("""
        SELECT location, change_date, old_value 
        FROM Rate_Cart_Change_Log 
        WHERE change_date > ? 
        ORDER BY change_date DESC
    """, (query_threshold,))
    logs = cursor.fetchall()
    conn.close()

    historical_costs = current_costs.copy()
    for row in logs:
        loc = row[0].strip().upper()
        old_val_str = row[2]
        old_val = float(old_val_str) if old_val_str else 0.0
        historical_costs[loc] = old_val

    return historical_costs

def _get_daily_report_data(target_date: str):
    rate_carts = get_rate_carts_for_date(target_date)

    conn_dwbi = get_dwbi_connection()
    cursor_dwbi = conn_dwbi.cursor()
    query = """
        SELECT Branch, ItemCode, MAX(ItemName), MAX(Principal), MAX(Brand), [Driver Name], SUM(ctnQty), CustomerCode, MAX(ContactPerson), Township, SUM(SalesAmount), MAX(BU)
        FROM VersaFleetDetail_TC
        WHERE CONVERT(DATE, [Task Date]) = ? AND [Task Status] = 'successful'
        GROUP BY Branch, [Driver Name], ItemCode, CustomerCode, Township
    """
    cursor_dwbi.execute(query, (target_date,))
    rows = cursor_dwbi.fetchall()
    conn_dwbi.close()

    granular_data = []
    driver_totals = {}
    driver_customers = {} 

    for row in rows:
        branch = row[0].strip().upper() if row[0] else "UNKNOWN"
        item_code = row[1].strip() if row[1] else ""
        item_name = row[2].strip() if row[2] else ""
        principal = row[3].strip() if row[3] else ""
        brand = row[4].strip() if row[4] else ""
        driver_name = row[5].strip() if row[5] else ""
        ctns = float(row[6]) if row[6] else 0.0
        customer_code = row[7].strip() if row[7] else "UNKNOWN"
        
        contact_person_raw = row[8].strip() if row[8] else ""
        if " - " in contact_person_raw:
            contact_person = contact_person_raw.split(" - ", 1)[-1].strip()
        else:
            contact_person = contact_person_raw
        
        township = row[9].strip() if row[9] else "UNKNOWN"
        sales_amount = float(row[10]) if row[10] else 0.0
        bu = row[11].strip() if (len(row) > 11 and row[11]) else ""

        granular_data.append({
            "branch": branch, "item_code": item_code, "item_name": item_name,
            "principal": principal, "brand": brand, "driver_name": driver_name,
            "ctns": ctns, "customer_code": customer_code, "contact_person": contact_person,
            "township": township, "sales_amount": sales_amount, "bu": bu
        })
        
        driver_key = (branch, driver_name)
        driver_totals[driver_key] = driver_totals.get(driver_key, 0.0) + ctns
        
        if driver_key not in driver_customers:
            driver_customers[driver_key] = set()
        driver_customers[driver_key].add(customer_code)

    item_report_dict = {}
    township_report_dict = {}

    for g in granular_data:
        b, d = g["branch"], g["driver_name"]
        d_total = driver_totals.get((b, d), 0.0)
        b_cost = rate_carts.get(b, 0.0)
        
        cost_per_ctn = (b_cost / d_total) if d_total > 0 else 0.0
        allocated_cost = g["ctns"] * cost_per_ctn

        d_total_customers = len(driver_customers.get((b, d), set()))
        cost_per_drop_point = (b_cost / d_total_customers) if d_total_customers > 0 else 0.0

        i_key = (b, d, g["item_code"])
        if i_key not in item_report_dict:
            item_report_dict[i_key] = {
                "target_date": target_date, # INJECT DATE
                "bu": g["bu"], "branch": b, "driver_name": d, "item_code": g["item_code"],
                "item_name": g["item_name"], "principal": g["principal"], "brand": g["brand"],
                "ctns": 0.0, "allocated_cost": 0.0, "cost_per_carton": cost_per_ctn,
                "driver_total_ctns": d_total, "branch_cost": b_cost, "sales_amount": 0.0
            }
        item_report_dict[i_key]["ctns"] += g["ctns"]
        item_report_dict[i_key]["allocated_cost"] += allocated_cost
        item_report_dict[i_key]["sales_amount"] += g["sales_amount"]

        t_key = (g["branch"], g["township"], g["customer_code"], g["driver_name"])
        if t_key not in township_report_dict:
            township_report_dict[t_key] = {
                "target_date": target_date, # INJECT DATE
                "branch": b, "driver_name": g["driver_name"], "township": g["township"], 
                "customer_code": g["customer_code"], "contact_person": g["contact_person"], 
                "ctns": 0.0, "driver_total_ctns": d_total, "branch_cost": b_cost,
                "cost_per_carton": cost_per_ctn, "allocated_cost": 0.0,
                "total_drop_points": d_total_customers, "cost_per_drop_point": cost_per_drop_point,
                "sales_amount": 0.0
            }
        township_report_dict[t_key]["ctns"] += g["ctns"]
        township_report_dict[t_key]["allocated_cost"] += allocated_cost
        township_report_dict[t_key]["sales_amount"] += g["sales_amount"]

    item_report_list = list(item_report_dict.values())
    item_report_list.sort(key=lambda x: (x["branch"], x["driver_name"], x["item_code"]))

    township_report_list = list(township_report_dict.values())
    township_report_list.sort(key=lambda x: (x["branch"], x["driver_name"], x["township"], x["customer_code"]))

    return {
        "item_report": item_report_list,
        "township_report": township_report_list
    }

def generate_and_save_daily_report(target_date: str):
    try:
        data = _get_daily_report_data(target_date)
        if not data["item_report"] and not data["township_report"]:
            return 

        conn = get_logistic_connection()
        cursor = conn.cursor()
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute("""
            INSERT INTO Daily_Report_History (target_date, item_report_json, township_report_json, created_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(target_date) DO UPDATE SET
                item_report_json = excluded.item_report_json,
                township_report_json = excluded.township_report_json,
                created_at = excluded.created_at
        """, (
            target_date, 
            json.dumps(data["item_report"]), 
            json.dumps(data["township_report"]),
            now_str
        ))
        conn.commit()
        conn.close()
        logger.info(f"Successfully generated and saved report for {target_date}")
        return data
    except Exception as e:
        logger.error(f"Failed to generate and save daily report for {target_date}: {str(e)}")
        return None

def daily_job_generator():
    target_date = datetime.datetime.now().strftime("%Y-%m-%d")
    logger.info(f"Running automated EOD report generation for {target_date}")
    generate_and_save_daily_report(target_date)

def get_or_generate_daily_report(target_date: str):
    """Fetches daily report from local history DB, or generates it if not found."""
    conn = get_logistic_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT item_report_json, township_report_json FROM Daily_Report_History WHERE target_date = ?", (target_date,))
    row = cursor.fetchone()
    conn.close()

    if row:
        item_report = json.loads(row[0])
        township_report = json.loads(row[1])

        # Inject target_date for backward compatibility with existing saved records
        for item in item_report:
            item["target_date"] = target_date
        for tw in township_report:
            tw["target_date"] = target_date

        return {
            "item_report": item_report,
            "township_report": township_report
        }
    else:
        return _get_daily_report_data(target_date)

def _aggregate_reports(daily_datas: List[dict]):
    """Aggregates multiple daily reports into a single consolidated report for date ranges."""
    item_report_dict = {}
    township_report_dict = {}

    for data in daily_datas:
        
        # --- 1. Fix Item Report Aggregation ---
        for item in data.get("item_report", []):
            t_date = item.get("target_date", "")
            # Include target_date in key to prevent squashing different dates together
            i_key = (t_date, item.get("branch", ""), item.get("driver_name", ""), item.get("item_code", ""))
            if i_key not in item_report_dict:
                item_report_dict[i_key] = {
                    "target_date": t_date,
                    "bu": item.get("bu", ""), "branch": item.get("branch", ""), "driver_name": item.get("driver_name", ""),
                    "item_code": item.get("item_code", ""), "item_name": item.get("item_name", ""), 
                    "principal": item.get("principal", ""), "brand": item.get("brand", ""),
                    "ctns": 0.0, "allocated_cost": 0.0, "driver_total_ctns": 0.0, 
                    "branch_cost": item.get("branch_cost", 0.0), "sales_amount": 0.0
                }
            else:
                item_report_dict[i_key]["branch_cost"] = item.get("branch_cost", item_report_dict[i_key]["branch_cost"])

            item_report_dict[i_key]["ctns"] += item.get("ctns", 0.0)
            item_report_dict[i_key]["allocated_cost"] += item.get("allocated_cost", 0.0)
            item_report_dict[i_key]["sales_amount"] += item.get("sales_amount", 0.0)
            item_report_dict[i_key]["driver_total_ctns"] += item.get("driver_total_ctns", 0.0)

        # --- 2. Fix Township Report Aggregation ---
        for tw in data.get("township_report", []):
            t_date = tw.get("target_date", "")
            # Include target_date in key
            t_key = (t_date, tw.get("branch", ""), tw.get("township", ""), tw.get("customer_code", ""), tw.get("driver_name", ""))
            if t_key not in township_report_dict:
                township_report_dict[t_key] = {
                    "target_date": t_date,
                    "branch": tw.get("branch", ""), "driver_name": tw.get("driver_name", ""), 
                    "township": tw.get("township", ""), "customer_code": tw.get("customer_code", ""), 
                    "contact_person": tw.get("contact_person", ""), "ctns": 0.0, "allocated_cost": 0.0, 
                    "driver_total_ctns": 0.0, "branch_cost": tw.get("branch_cost", 0.0), "total_drop_points": 0.0, "sales_amount": 0.0
                }
            else:
                township_report_dict[t_key]["branch_cost"] = tw.get("branch_cost", township_report_dict[t_key]["branch_cost"])

            township_report_dict[t_key]["ctns"] += tw.get("ctns", 0.0)
            township_report_dict[t_key]["allocated_cost"] += tw.get("allocated_cost", 0.0)
            township_report_dict[t_key]["sales_amount"] += tw.get("sales_amount", 0.0)
            township_report_dict[t_key]["driver_total_ctns"] += tw.get("driver_total_ctns", 0.0)
            township_report_dict[t_key]["total_drop_points"] += tw.get("total_drop_points", 0.0)

    # Recalculate accurate averages across the whole period for items
    item_report_list = list(item_report_dict.values())
    for item in item_report_list:
        item["cost_per_carton"] = item["allocated_cost"] / item["ctns"] if item["ctns"] > 0 else 0.0
    item_report_list.sort(key=lambda x: (x.get("target_date", ""), x["branch"], x["driver_name"], x["item_code"]))

    # Recalculate accurate averages across the whole period for townships
    township_report_list = list(township_report_dict.values())
    for tw in township_report_list:
        tw["cost_per_carton"] = tw["allocated_cost"] / tw["ctns"] if tw["ctns"] > 0 else 0.0
        tw["cost_per_drop_point"] = tw["allocated_cost"] / tw["total_drop_points"] if tw["total_drop_points"] > 0 else 0.0
    township_report_list.sort(key=lambda x: (x.get("target_date", ""), x["branch"], x["driver_name"], x["township"], x["customer_code"]))

    return {
        "item_report": item_report_list,
        "township_report": township_report_list
    }

@app.get("/account/daily-rate-cut-report")
def get_daily_rate_cart_report(
    target_date: Optional[str] = None, 
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    user: dict = Depends(require_permission("view_daily_report"))
):
    try:
        # 1. Range Selection Logic
        if start_date and end_date:
            try:
                start_dt = datetime.datetime.strptime(start_date, "%Y-%m-%d")
                end_dt = datetime.datetime.strptime(end_date, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
            
            if start_dt > end_dt:
                raise HTTPException(status_code=400, detail="start_date cannot be after end_date")

            daily_datas = []
            current_dt = start_dt
            while current_dt <= end_dt:
                dt_str = current_dt.strftime("%Y-%m-%d")
                daily_datas.append(get_or_generate_daily_report(dt_str))
                current_dt += datetime.timedelta(days=1)
            
            aggregated = _aggregate_reports(daily_datas)
            return {
                "target_date": f"{start_date} to {end_date}",
                "report": aggregated["item_report"],
                "township_report": aggregated["township_report"]
            }
            
        # 2. Single Day View (Default behavior)
        else:
            if not target_date:
                target_date = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
                
            data = get_or_generate_daily_report(target_date)
            return {
                "target_date": target_date, 
                "report": data["item_report"], 
                "township_report": data["township_report"]
            }
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing daily report: {str(e)}")

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
def add_ref_location(item: ReferenceItem, user: dict = Depends(require_permission("add_reference"))):
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
        log_user_activity(user['username'], "ADD_REFERENCE", f"Added location: {item.name}")
        return {"message": "Added successfully"}
    except HTTPException: raise
    except Exception as e: raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.delete("/references/locations/{name}")
def delete_ref_location(name: str, user: dict = Depends(require_permission("delete_reference"))):
    try:
        conn = get_logistic_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Locations WHERE name = ?", (name,))
        if cursor.rowcount == 0:
             conn.close()
             raise HTTPException(status_code=404, detail="Not found")
        conn.commit()
        conn.close()
        log_user_activity(user['username'], "DELETE_REFERENCE", f"Deleted location: {name}")
        return {"message": "Deleted successfully"}
    except HTTPException: raise
    except Exception as e: raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@app.get("/references/rate-cart-locations")
def get_ref_rate_cart_locations():
    try:
        conn = get_logistic_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM Rate_Cart_Locations ORDER BY name")
        rows = cursor.fetchall()
        conn.close()
        return [row[0] for row in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.post("/references/rate-cart-locations")
def add_ref_rate_cart_location(item: ReferenceItem, user: dict = Depends(require_permission("add_reference"))):
    try:
        conn = get_logistic_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO Rate_Cart_Locations (name) VALUES (?)", (item.name,))
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            raise HTTPException(status_code=400, detail="Rate Cart Location already exists")
        conn.close()
        log_user_activity(user['username'], "ADD_REFERENCE", f"Added rate cart location: {item.name}")
        return {"message": "Added successfully"}
    except HTTPException: raise
    except Exception as e: raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.delete("/references/rate-cart-locations/{name}")
def delete_ref_rate_cart_location(name: str, user: dict = Depends(require_permission("delete_reference"))):
    try:
        conn = get_logistic_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Rate_Cart_Locations WHERE name = ?", (name,))
        if cursor.rowcount == 0:
             conn.close()
             raise HTTPException(status_code=404, detail="Not found")
        conn.commit()
        conn.close()
        log_user_activity(user['username'], "DELETE_REFERENCE", f"Deleted rate cart location: {name}")
        return {"message": "Deleted successfully"}
    except HTTPException: raise
    except Exception as e: raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@app.get("/references/uoms")
def get_ref_uoms():
    try:
        conn = get_logistic_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM UOMs ORDER BY name")
        rows = cursor.fetchall()
        conn.close()
        return [row[0] for row in rows]
    except Exception as e: raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.post("/references/uoms")
def add_ref_uom(item: ReferenceItem, user: dict = Depends(require_permission("add_reference"))):
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
        log_user_activity(user['username'], "ADD_REFERENCE", f"Added UOM: {item.name}")
        return {"message": "Added successfully"}
    except HTTPException: raise
    except Exception as e: raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.delete("/references/uoms/{name}")
def delete_ref_uom(name: str, user: dict = Depends(require_permission("delete_reference"))):
    try:
        conn = get_logistic_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM UOMs WHERE name = ?", (name,))
        if cursor.rowcount == 0:
             conn.close()
             raise HTTPException(status_code=404, detail="Not found")
        conn.commit()
        conn.close()
        log_user_activity(user['username'], "DELETE_REFERENCE", f"Deleted UOM: {name}")
        return {"message": "Deleted successfully"}
    except HTTPException: raise
    except Exception as e: raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.get("/references/channels")
def get_ref_channels():
    try:
        conn = get_logistic_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM Channels ORDER BY name")
        rows = cursor.fetchall()
        conn.close()
        return [row[0] for row in rows]
    except Exception as e: raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.post("/references/channels")
def add_ref_channel(item: ReferenceItem, user: dict = Depends(require_permission("add_reference"))):
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
        log_user_activity(user['username'], "ADD_REFERENCE", f"Added channel: {item.name}")
        return {"message": "Added successfully"}
    except HTTPException: raise
    except Exception as e: raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.delete("/references/channels/{name}")
def delete_ref_channel(name: str, user: dict = Depends(require_permission("delete_reference"))):
    try:
        conn = get_logistic_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Channels WHERE name = ?", (name,))
        if cursor.rowcount == 0:
             conn.close()
             raise HTTPException(status_code=404, detail="Not found")
        conn.commit()
        conn.close()
        log_user_activity(user['username'], "DELETE_REFERENCE", f"Deleted channel: {name}")
        return {"message": "Deleted successfully"}
    except HTTPException: raise
    except Exception as e: raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
    
    
    
@app.get("/references/location-mappings")
def get_ref_location_mappings():
    try:
        conn = get_logistic_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT to_location, branch_code FROM Location_Mapping ORDER BY to_location")
        rows = cursor.fetchall()
        conn.close()
        return [{"to_location": row[0], "branch_code": row[1]} for row in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.post("/references/location-mappings")
def add_ref_location_mapping(item: LocationMappingItem, user: dict = Depends(require_permission("add_reference"))):
    try:
        conn = get_logistic_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO Location_Mapping (to_location, branch_code) VALUES (?, ?)", (item.to_location, item.branch_code))
            conn.commit()
        except sqlite3.IntegrityError:
            # If it already exists, update it
            cursor.execute("UPDATE Location_Mapping SET branch_code = ? WHERE to_location = ?", (item.branch_code, item.to_location))
            conn.commit()
        conn.close()
        log_user_activity(user['username'], "ADD_REFERENCE", f"Mapped {item.to_location} to {item.branch_code}")
        return {"message": "Mapping saved successfully"}
    except Exception as e: raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.delete("/references/location-mappings/{to_location}")
def delete_ref_location_mapping(to_location: str, user: dict = Depends(require_permission("delete_reference"))):
    try:
        conn = get_logistic_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Location_Mapping WHERE to_location = ?", (to_location,))
        conn.commit()
        conn.close()
        log_user_activity(user['username'], "DELETE_REFERENCE", f"Deleted mapping for: {to_location}")
        return {"message": "Deleted successfully"}
    except Exception as e: raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

# --- Calculation History Endpoints ---

@app.post("/history/save")
def save_calculation(data: CalculationSaveRequest, user: dict = Depends(get_current_user)):
    try:
        conn = get_logistic_connection()
        cursor = conn.cursor()
        doc_nums_json = json.dumps(data.doc_nums)
        calculated_products_json = json.dumps(data.calculated_products)
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
                    status = ?, calculated_products = ?
                WHERE id = ?
            """, (
                created_at, data.gate_name, data.from_loc, data.to_loc,
                doc_nums_json, data.manual_total_cost, data.additional_charges, 
                data.final_total_cost, data.channel, data.status, calculated_products_json, data.id
            ))
            message = "Calculation updated successfully"
            log_user_activity(user['username'], "UPDATE_CALCULATION", f"Updated saved calculation ID: {data.id}")
        else:
            while True:
                new_id = int(datetime.datetime.now().strftime("%y%m%d%H%M%S"))
                cursor.execute("SELECT 1 FROM Calculation_History WHERE id = ?", (new_id,))
                if not cursor.fetchone(): break
                time.sleep(1)

            cursor.execute("""
                INSERT INTO Calculation_History 
                ([id], [created_at], [gate_name], [from_loc], [to_loc], 
                 [doc_nums], [manual_total_cost], [additional_charges], [final_total_cost], [channel], [status], [created_by], [calculated_products])
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                new_id, created_at, data.gate_name, data.from_loc, data.to_loc,
                doc_nums_json, data.manual_total_cost, data.additional_charges, data.final_total_cost, 
                data.channel, data.status, user["username"], calculated_products_json
            ))
            message = "Calculation saved successfully"
            log_user_activity(user['username'], "SAVE_CALCULATION", f"Saved new calculation ID: {new_id}")
        
        conn.commit()
        conn.close()
        return {"message": message}
    except HTTPException: raise
    except Exception as e: raise HTTPException(status_code=500, detail=f"Error saving history: {str(e)}")

@app.put("/history/{record_id}/submit")
def submit_history_item(record_id: int, user: dict = Depends(require_permission("submit_calculation"))):
    try:
        conn = get_logistic_connection()
        cursor = conn.cursor()
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("UPDATE Calculation_History SET status = 'submitted', submitted_by = ?, submitted_at = ? WHERE id = ?", (user["username"], now_str, record_id))
        if cursor.rowcount == 0:
            conn.close()
            raise HTTPException(status_code=404, detail="Record not found")
        conn.commit()
        conn.close()
        log_user_activity(user['username'], "SUBMIT_CALCULATION", f"Submitted calculation ID: {record_id}")
        return {"message": "Calculation submitted successfully"}
    except Exception as e: raise HTTPException(status_code=500, detail=f"Error submitting record: {str(e)}")

@app.put("/history/{record_id}/claim")
def claim_history_item(record_id: int, user: dict = Depends(require_permission("claim_calculation"))):
    try:
        conn = get_logistic_connection()
        cursor = conn.cursor()
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("UPDATE Calculation_History SET status = 'claimed', claimed_by = ?, claimed_at = ? WHERE id = ?", (user["username"], now_str, record_id))
        if cursor.rowcount == 0:
            conn.close()
            raise HTTPException(status_code=404, detail="Record not found")
        conn.commit()
        conn.close()
        log_user_activity(user['username'], "CLAIM_CALCULATION", f"Claimed calculation ID: {record_id}")
        return {"message": "Calculation claimed successfully"}
    except Exception as e: raise HTTPException(status_code=500, detail=f"Error claiming record: {str(e)}")

@app.get("/history/{record_id}")
def get_history_record(record_id: int, user: dict = Depends(require_permission("view_history"))):
    try:
        conn = get_logistic_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Calculation_History WHERE id = ?", (record_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Record not found")
        
        columns = [desc[0] for desc in cursor.description]
        record = dict(zip(columns, row))
        record['doc_nums'] = json.loads(record['doc_nums']) if record['doc_nums'] else []
        record['calculated_products'] = json.loads(record['calculated_products']) if record.get('calculated_products') else []
        conn.close()
        return record
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/history")
def get_history(user: dict = Depends(require_permission("view_history"))):
    try:
        conn = get_logistic_connection()
        cursor = conn.cursor()
        
        permissions = user.get('permissions', [])
        username = user.get('username')

        if 'view_all_history' in permissions:
            cursor.execute("SELECT * FROM Calculation_History ORDER BY created_at DESC")
        elif 'claim_calculation' in permissions:
            cursor.execute("""
                SELECT * FROM Calculation_History 
                WHERE created_by = ? OR status IN ('submitted', 'claimed') 
                ORDER BY created_at DESC
            """, (username,))
        else:
            cursor.execute("SELECT * FROM Calculation_History WHERE created_by = ? OR created_by IS NULL ORDER BY created_at DESC", (username,))
            
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        history = []
        for row in rows:
            record_dict = dict(zip(columns, row))
            record_dict["doc_nums"] = json.loads(record_dict["doc_nums"]) if record_dict["doc_nums"] else []
            if "calculated_products" in record_dict:
                del record_dict["calculated_products"]
            history.append(record_dict)
        conn.close()
        return {"history": history}
    except Exception as e: raise HTTPException(status_code=500, detail=f"Error loading history: {str(e)}")

@app.delete("/history/{record_id}")
def delete_history_item(record_id: int, user: dict = Depends(require_permission("delete_history"))):
    try:
        conn = get_logistic_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Calculation_History WHERE id = ?", (record_id,))
        if cursor.rowcount == 0:
            conn.close()
            raise HTTPException(status_code=404, detail="Record not found")
        conn.commit()
        conn.close()
        log_user_activity(user['username'], "DELETE_CALCULATION", f"Deleted calculation ID: {record_id}")
        return {"message": "Record deleted successfully"}
    except HTTPException: raise
    except Exception as e: raise HTTPException(status_code=500, detail=f"Error deleting record: {str(e)}")

@app.get("/history/{record_id}/download")
def download_history_excel(record_id: int, user: dict = Depends(require_permission("view_history"))):
    try:
        conn = get_logistic_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Calculation_History WHERE id = ?", (record_id,))
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            raise HTTPException(status_code=404, detail="History record not found")
            
        columns = [desc[0] for desc in cursor.description]
        record = dict(zip(columns, row))
        record['doc_nums'] = json.loads(record['doc_nums']) if record['doc_nums'] else []
        conn.close()

        products = []
        try:
            calc_result = _perform_calculation_logic(
                gate_name=record['gate_name'], doc_nums=record['doc_nums'],
                from_loc=record['from_loc'], to_loc=record['to_loc'],
                manual_total_cost=record['manual_total_cost'], additional_charges=record['additional_charges']
            )
            products = calc_result['calculated_products']
        except Exception as e:
            if record.get('calculated_products'):
                products = json.loads(record['calculated_products'])
            else:
                raise HTTPException(status_code=500, detail=f"Data purged from DWBI and no local save found: {str(e)}")

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Cost Details"

        headers = [
            "No", "Claim Date", "Delivery Date", "SIN No", "Area", "Code", "Name", "Principal", "Brand", "Item Code", "Item", "Ctns", 
            "Price", "Total Amount", "Weight", "UOM", "Gate", "Channel", "Month", "Year", "Description for Account", 
            "Description with cnts and price", "Branch", "B-Dept", "B-Principal", "S-Dept", "S-Principal", "BU", "Calculation ID"
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

        now = datetime.datetime.now()
        claim_date_str = now.strftime("%d/%m/%Y") 
        claim_month = now.strftime("%B") 
        claim_year = now.year
        
        for idx, item in enumerate(products, 1):
            row_num = idx + 1
            doc_date_val = item.get('doc_date')
            if isinstance(doc_date_val, datetime.datetime): doc_date_str = doc_date_val.strftime("%d/%m/%Y")
            elif isinstance(doc_date_val, str) and len(doc_date_val) >= 10:
                try: doc_date_str = datetime.datetime.strptime(doc_date_val[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
                except ValueError: doc_date_str = doc_date_val
            else: doc_date_str = str(doc_date_val) if doc_date_val else ""

            b_desc = item.get('b_desc', '')
            ctns_val = item.get('ctns', 0)
            total_cost_val = item.get('total_cost', 0)
            ctns_formatted = int(ctns_val) if float(ctns_val).is_integer() else ctns_val
            price_per_ctn = total_cost_val / ctns_val if ctns_val > 0 else 0
            price_formatted = int(price_per_ctn) if float(price_per_ctn).is_integer() else round(price_per_ctn, 2)

            concat_desc = f"{b_desc.strip()} - {ctns_formatted} ctns @{price_formatted} kyats"

            raw_sin_no = str(item.get('sin_no', ''))
            clean_sin_no = raw_sin_no.replace('PDG - ', '').replace('PDG-', '').replace('PG - ', '').replace('PG-', '').strip()

            ws.cell(row=row_num, column=1, value=idx).border = border
            ws.cell(row=row_num, column=2, value=claim_date_str).border = border
            ws.cell(row=row_num, column=3, value=doc_date_str).border = border
            ws.cell(row=row_num, column=4, value=clean_sin_no).border = border
            ws.cell(row=row_num, column=5, value=record['to_loc']).border = border
            ws.cell(row=row_num, column=6, value=item.get('b_code', '')).border = border
            ws.cell(row=row_num, column=7, value=item.get('b_name', '')).border = border
            ws.cell(row=row_num, column=8, value=item.get('principal', '')).border = border
            ws.cell(row=row_num, column=9, value=item.get('brand', '')).border = border
            ws.cell(row=row_num, column=10, value=item.get('code', '')).border = border
            ws.cell(row=row_num, column=11, value=item.get('name', '')).border = border
            ws.cell(row=row_num, column=12, value=ctns_formatted).border = border
            
            ctn_price_cell = ws.cell(row=row_num, column=13, value=price_per_ctn) 
            ctn_price_cell.number_format = '#,##0.00'
            ctn_price_cell.border = border

            amt_cell = ws.cell(row=row_num, column=14, value=total_cost_val) 
            amt_cell.number_format = '#,##0.00'
            amt_cell.border = border

            weight_cell = ws.cell(row=row_num, column=15, value=item.get('weight', 0)) 
            weight_cell.number_format = '#,##0.00'
            weight_cell.border = border

            ws.cell(row=row_num, column=16, value="Kg").border = border
            ws.cell(row=row_num, column=17, value=record['gate_name']).border = border
            ws.cell(row=row_num, column=18, value=record.get('channel', '')).border = border
            ws.cell(row=row_num, column=19, value=claim_month).border = border
            ws.cell(row=row_num, column=20, value=claim_year).border = border
            ws.cell(row=row_num, column=21, value=b_desc).border = border
            ws.cell(row=row_num, column=22, value=concat_desc).border = border
            ws.cell(row=row_num, column=23, value=record['to_loc']).border = border
            ws.cell(row=row_num, column=24, value=item.get('b_dept', '')).border = border
            ws.cell(row=row_num, column=25, value=item.get('b_principal', '')).border = border
            ws.cell(row=row_num, column=26, value=item.get('s_dept', '')).border = border
            ws.cell(row=row_num, column=27, value=item.get('s_principal', '')).border = border
            ws.cell(row=row_num, column=28, value=item.get('bu', '')).border = border 
            ws.cell(row=row_num, column=29, value=record['id']).border = border

        for col in ws.columns:
            max_length = 0
            col_letter = col[0].column_letter
            for cell in col:
                try:
                    if len(str(cell.value)) > max_length: max_length = len(str(cell.value))
                except: pass
            ws.column_dimensions[col_letter].width = max_length + 2

        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        filename = f"Calculation_{record_id}_{record['gate_name']}.xlsx"
        return StreamingResponse(
            output, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except HTTPException: raise
    except Exception as e: raise HTTPException(status_code=500, detail=f"Error generating download: {str(e)}")
    
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
        gate_name, from_loc, to_loc = gate_row[0], gate_row[1] or "", gate_row[2] or ""
        
        cursor.execute("SELECT [BU], [Item ID], [Item Name], [Principal], [Brand], [Transportation Cost] FROM Item_Pricing WHERE [Gate ID] = ? ORDER BY [Item ID]", (gate_id,))
        rows = cursor.fetchall()
        conn.close()
        
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Item Pricing"
        ws['A1'] = f"Gate: {gate_name} ({from_loc} -> {to_loc})"
        ws['A1'].font = Font(bold=True, size=14)
        
        headers = ['BU', 'Item Code', 'Item Name', 'Principal', 'Brand', 'Transportation Cost']
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
                    if len(str(cell.value)) > max_length: max_length = len(str(cell.value))
                except: pass
            ws.column_dimensions[col_letter].width = min(max_length + 2, 50)
        
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        filename = f"item_pricing_{gate_name.replace(' ', '_')}.xlsx"
        return StreamingResponse(
            output, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except HTTPException: raise
    except Exception as e: raise HTTPException(status_code=500, detail=f"Error exporting: {str(e)}")

@app.post("/account/item-pricing/import/{gate_id}")
async def import_item_pricing_excel(gate_id: int, file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    perms = user.get("permissions", [])
    if "add_item" not in perms or "edit_item" not in perms:
        raise HTTPException(status_code=403, detail="Requires both 'add_item' and 'edit_item' permissions for bulk import")

    try:
        contents = await file.read()
        wb = openpyxl.load_workbook(io.BytesIO(contents))
        ws = wb.active
        
        excel_rows = []
        item_codes_to_check = set()
        
        for row_idx, row in enumerate(ws.iter_rows(min_row=4, values_only=True), start=4):
            if not row[1]: continue
            item_code = str(row[1]).strip()
            excel_rows.append({
                "row_num": row_idx, 
                "bu": str(row[0]).strip() if row[0] else "", 
                "code": item_code, 
                "name": str(row[2]).strip() if row[2] else "",
                "principal": str(row[3]).strip() if row[3] else "", 
                "brand": str(row[4]).strip() if row[4] else "",
                "cost": str(row[5]).strip() if len(row) > 5 and row[5] else ""
            })
            item_codes_to_check.add(item_code)
            
        if not excel_rows: raise HTTPException(status_code=400, detail="No data found in Excel file")

        conn_dwbi = get_dwbi_connection()
        cursor_dwbi = conn_dwbi.cursor()
        dwbi_data = {}
        unique_codes_list = list(item_codes_to_check)
        batch_size = 1000
        
        for i in range(0, len(unique_codes_list), batch_size):
            batch = unique_codes_list[i:i + batch_size]
            placeholders = ','.join('?' * len(batch))
            cursor_dwbi.execute(f"SELECT ItemCode, ItemName, ItmsGrpNam, U_BrandName, Sector FROM Itemmasterallpp WHERE ItemCode IN ({placeholders})", batch)
            rows = cursor_dwbi.fetchall()
            for r in rows:
                dwbi_data[str(r[0]).strip()] = {
                    "name": str(r[1]).strip() if r[1] else "", 
                    "principal": str(r[2]).strip() if r[2] else "", 
                    "brand": str(r[3]).strip() if r[3] else "",
                    "bu": str(r[4]).strip() if r[4] else ""
                }
        conn_dwbi.close()
        
        errors = []
        for row in excel_rows:
            code = row["code"]
            if code not in dwbi_data:
                errors.append(f"Row {row['row_num']}: Item Code '{code}' not found in DWBI.")
                continue
            db_item = dwbi_data[code]
            if row["name"].lower() != db_item["name"].lower(): errors.append(f"Row {row['row_num']}: Item Name mismatch. Excel: '{row['name']}', System: '{db_item['name']}'")
            if row["principal"].lower() != db_item["principal"].lower(): errors.append(f"Row {row['row_num']}: Principal mismatch.")
            if row["brand"].lower() != db_item["brand"].lower(): errors.append(f"Row {row['row_num']}: Brand mismatch.")
            if row["bu"].lower() != db_item["bu"].lower(): errors.append(f"Row {row['row_num']}: BU mismatch.")

        if errors:
            error_msg = errors[:10]
            if len(errors) > 10: error_msg.append(f"... and {len(errors) - 10} more errors.")
            raise HTTPException(status_code=400, detail=error_msg)

        conn = get_logistic_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT [Item ID], [Pricing ID], [Transportation Cost] FROM Item_Pricing WHERE [Gate ID] = ?", (gate_id,))
        existing_items_data = {row[0]: {'pricing_id': row[1], 'cost': row[2]} for row in cursor.fetchall()}
        existing_items = set(existing_items_data.keys())
        
        cursor.execute("SELECT [Pricing ID] FROM Item_Pricing")
        used_ids = {row[0] for row in cursor.fetchall()}
        
        updated_items_set = set()
        updates_made, inserts_made, deletes_made = 0, 0, 0
        
        change_logs = []
        change_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        username = user['username']
        
        for row in excel_rows:
            item_code = row["code"]
            updated_items_set.add(item_code)
            
            if item_code in existing_items:
                pricing_id = existing_items_data[item_code]['pricing_id']
                old_cost = existing_items_data[item_code]['cost']
                old_cost_str = str(old_cost).strip() if old_cost else ""
                new_cost_str = str(row["cost"]).strip() if row["cost"] else ""
                
                if old_cost_str != new_cost_str:
                    change_logs.append((pricing_id, username, change_date, 'Transportation Cost', old_cost_str, new_cost_str))

                cursor.execute("""
                    UPDATE Item_Pricing
                    SET [BU] = ?, [Item Name] = ?, [Principal] = ?, [Brand] = ?, [Transportation Cost] = ?
                    WHERE [Gate ID] = ? AND [Item ID] = ?
                """, (row["bu"], row["name"], row["principal"], row["brand"], row["cost"], gate_id, item_code))
                updates_made += 1
            else:
                while True:
                    new_id = random.randint(10000000, 99999999)
                    if new_id not in used_ids:
                        used_ids.add(new_id)
                        break
                cursor.execute("""
                    INSERT INTO Item_Pricing ([Pricing ID], [Gate ID], [BU], [Item ID], [Item Name], [Principal], [Brand], [Transportation Cost])
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (new_id, gate_id, row["bu"], item_code, row["name"], row["principal"], row["brand"], row["cost"]))
                inserts_made += 1
                
        if change_logs:
            cursor.executemany("INSERT INTO Item_Change_Log (pricing_id, changed_by, change_date, field_name, old_value, new_value) VALUES (?, ?, ?, ?, ?, ?)", change_logs)
        
        items_to_delete = existing_items - updated_items_set
        for item_code in items_to_delete:
            pricing_id = existing_items_data[item_code]['pricing_id']
            cursor.execute("DELETE FROM Item_Change_Log WHERE pricing_id = ?", (pricing_id,))
            cursor.execute("DELETE FROM Item_Pricing WHERE [Gate ID] = ? AND [Item ID] = ?", (gate_id, item_code))
            deletes_made += 1
            
        conn.commit()
        conn.close()
        
        log_user_activity(username, "BULK_IMPORT_ITEMS", f"Imported items to gate ID {gate_id} (Updates: {updates_made}, Inserts: {inserts_made}, Deletes: {deletes_made})")
        return {"message": "Import completed successfully", "updates": updates_made, "inserts": inserts_made, "deletes": deletes_made}
    except HTTPException: raise
    except Exception as e: raise HTTPException(status_code=500, detail=f"Error importing: {str(e)}")

# --- Gate Management Endpoints (SQLite) ---

@app.get("/account/gates")
def get_all_gates(
    gate_name: Optional[str] = Query(None, description="Filter by gate name"),
    from_loc: Optional[str] = Query(None, description="Filter by origin location"),
    to_loc: Optional[str] = Query(None, description="Filter by destination location"),
    uom: Optional[str] = Query(None, description="Filter by UOM"),
    cost: Optional[str] = Query(None, description="Filter by cost"),
    user: dict = Depends(get_current_user)
):
    try:
        conn = get_logistic_connection()
        cursor = conn.cursor()
        
        query = "SELECT [Gate ID], [Gate Name], [From], [To], [UOM], [Unit], [Cost] FROM Gate WHERE 1=1"
        params = []
        
        if gate_name:
            query += " AND [Gate Name] LIKE ?"
            params.append(f"%{gate_name}%")
        if from_loc:
            query += " AND [From] LIKE ?"
            params.append(f"%{from_loc}%")
        if to_loc:
            query += " AND [To] LIKE ?"
            params.append(f"%{to_loc}%")
        if uom:
            query += " AND [UOM] LIKE ?"
            params.append(f"%{uom}%")
        if cost:
            query += " AND CAST([Cost] AS TEXT) LIKE ?"
            params.append(f"%{cost}%")

        cursor.execute(query, params)
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
        raise HTTPException(status_code=500, detail=f"Error loading gates: {str(e)}")

@app.post("/account/gates")
def save_gate(gate_data: GateData, user: dict = Depends(get_current_user)):
    perms = user.get("permissions", [])
    try:
        conn = get_logistic_connection()
        cursor = conn.cursor()

        # --- NEW VALIDATION: Prevent duplicate gate name + from/to locations ---
        cursor.execute("""
            SELECT [Gate ID] FROM Gate 
            WHERE [Gate Name] = ? AND [From] = ? AND [To] = ?
        """, (gate_data.gate_name, gate_data.from_loc, gate_data.to_loc))
        existing_gate = cursor.fetchone()

        if existing_gate:
            if gate_data.gate_id is None:
                # Adding a new gate that perfectly matches an existing one
                conn.close()
                raise HTTPException(status_code=400, detail="A gate with this name, origin, and destination already exists.")
            elif existing_gate[0] != gate_data.gate_id:
                # Editing a gate to conflict with a different existing gate
                conn.close()
                raise HTTPException(status_code=400, detail="Another gate with this name, origin, and destination already exists.")
        # -----------------------------------------------------------------------

        if gate_data.gate_id is not None:
            if "edit_gate" not in perms:
                conn.close()
                raise HTTPException(status_code=403, detail="Requires 'edit_gate' permission")
            
            cursor.execute("SELECT [Gate ID], [UOM], [Unit], [Cost] FROM Gate WHERE [Gate ID] = ?", (gate_data.gate_id,))
            current_row = cursor.fetchone()
            
            if current_row:
                gate_id, old_uom, old_unit, old_cost = current_row
                old_uom = old_uom if old_uom else None
                new_uom = gate_data.uom if gate_data.uom else None
                old_unit = old_unit if old_unit is not None else None
                new_unit = gate_data.unit if gate_data.unit is not None else None
                old_cost = float(old_cost) if old_cost is not None else None
                new_cost = float(gate_data.cost) if gate_data.cost is not None else None

                change_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                username = user['username']
                changes = []

                if old_uom != new_uom: changes.append((gate_id, username, change_date, 'UOM', str(old_uom or ''), str(new_uom or '')))
                if old_unit != new_unit: changes.append((gate_id, username, change_date, 'Unit', str(old_unit) if old_unit is not None else '', str(new_unit) if new_unit is not None else ''))
                if old_cost != new_cost: changes.append((gate_id, username, change_date, 'Cost', str(old_cost) if old_cost is not None else '', str(new_cost) if new_cost is not None else ''))
                
                if changes:
                    cursor.executemany("INSERT INTO Gate_Change_Log (gate_id, changed_by, change_date, field_name, old_value, new_value) VALUES (?, ?, ?, ?, ?, ?)", changes)

            cursor.execute("""
                UPDATE Gate SET [Gate Name] = ?, [From] = ?, [To] = ?, [UOM] = ?, [Unit] = ?, [Cost] = ? WHERE [Gate ID] = ?
            """, (gate_data.gate_name, gate_data.from_loc, gate_data.to_loc, gate_data.uom, gate_data.unit, gate_data.cost, gate_data.gate_id))
            log_user_activity(user['username'], "UPDATE_GATE", f"Updated gate ID {gate_data.gate_id}: {gate_data.gate_name}")
        else:
            if "add_gate" not in perms:
                conn.close()
                raise HTTPException(status_code=403, detail="Requires 'add_gate' permission")
                
            cursor.execute("INSERT INTO Gate ([Gate Name], [From], [To], [UOM], [Unit], [Cost]) VALUES (?, ?, ?, ?, ?, ?)", 
                  (gate_data.gate_name, gate_data.from_loc, gate_data.to_loc, gate_data.uom, gate_data.unit, gate_data.cost))
            log_user_activity(user['username'], "CREATE_GATE", f"Created gate: {gate_data.gate_name}")
        
        conn.commit()
        conn.close()
        return {"message": "Gate saved successfully"}
    except HTTPException: raise
    except Exception as e: raise HTTPException(status_code=500, detail=f"Error saving gate: {str(e)}")

@app.get("/account/gates/{gate_id}/logs", response_model=List[GateLogItem])
def get_gate_logs(gate_id: int, user: dict = Depends(get_current_user)):
    try:
        conn = get_logistic_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, gate_id, changed_by, change_date, field_name, old_value, new_value FROM Gate_Change_Log WHERE gate_id = ? ORDER BY change_date DESC", (gate_id,))
        rows = cursor.fetchall()
        logs = [{"id": r[0], "gate_id": r[1], "changed_by": r[2], "change_date": r[3], "field_name": r[4], "old_value": r[5], "new_value": r[6]} for r in rows]
        conn.close()
        return logs
    except Exception as e: raise HTTPException(status_code=500, detail=f"Error fetching logs: {str(e)}")

@app.delete("/account/gates/{gate_id}")
def delete_gate(gate_id: int, user: dict = Depends(require_permission("delete_gate"))): 
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
        
        log_user_activity(user['username'], "DELETE_GATE", f"Deleted gate ID: {gate_id}")
        return {"message": f"Gate {gate_id} deleted successfully"}
    except HTTPException: raise
    except Exception as e: raise HTTPException(status_code=500, detail=f"Error deleting gate: {str(e)}")

@app.get("/account/item-pricing/{gate_id}")
def get_item_pricing(gate_id: int, user: dict = Depends(get_current_user)):
    try:
        conn = get_logistic_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT [Pricing ID], [BU], [Item ID], [Item Name], [Principal], [Brand], [Transportation Cost] FROM Item_Pricing WHERE [Gate ID] = ?", (gate_id,))
        rows = cursor.fetchall()
        items = [{"pricing_id": r[0], "bu": r[1], "item_code": r[2], "item_name": r[3], "principal": r[4], "brand": r[5], "transportation_cost": r[6]} for r in rows]
        conn.close()
        return {"items": items, "gate_id": gate_id}
    except Exception as e: raise HTTPException(status_code=500, detail=f"Error loading items: {str(e)}")

@app.post("/account/item-pricing")
def save_item_pricing(item_data: ItemPricingData, user: dict = Depends(get_current_user)):
    perms = user.get("permissions", [])
    try:
        conn = get_logistic_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT [Pricing ID], [Transportation Cost] FROM Item_Pricing WHERE [Gate ID] = ? AND [Item ID] = ?", (item_data.gate_id, item_data.original_item_code or item_data.item_code))
        existing = cursor.fetchone()

        if existing:
            if "edit_item" not in perms:
                conn.close()
                raise HTTPException(status_code=403, detail="Requires 'edit_item' permission")
                
            pricing_id, old_cost = existing
            old_cost_str = str(old_cost).strip() if old_cost else ""
            new_cost_str = str(item_data.transportation_cost).strip() if item_data.transportation_cost else ""
            
            change_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            username = user['username']
            changes = []
            
            if old_cost_str != new_cost_str:
                 changes.append((pricing_id, username, change_date, 'Transportation Cost', old_cost_str, new_cost_str))

            if changes:
                 cursor.executemany("INSERT INTO Item_Change_Log (pricing_id, changed_by, change_date, field_name, old_value, new_value) VALUES (?, ?, ?, ?, ?, ?)", changes)

            cursor.execute("UPDATE Item_Pricing SET [Item ID] = ?, [BU] = ?, [Item Name] = ?, [Principal] = ?, [Brand] = ?, [Transportation Cost] = ? WHERE [Pricing ID] = ?", 
                (item_data.item_code, item_data.bu, item_data.item_name, item_data.principal, item_data.brand, item_data.transportation_cost, pricing_id))
            log_user_activity(user['username'], "UPDATE_ITEM_PRICING", f"Updated pricing for item {item_data.item_code} on gate ID {item_data.gate_id}")
        else:
            if "add_item" not in perms:
                conn.close()
                raise HTTPException(status_code=403, detail="Requires 'add_item' permission")
                
            while True:
                new_id = random.randint(10000000, 99999999)
                cursor.execute("SELECT 1 FROM Item_Pricing WHERE [Pricing ID] = ?", (new_id,))
                if not cursor.fetchone(): break
            cursor.execute("INSERT INTO Item_Pricing ([Pricing ID], [Gate ID], [BU], [Item ID], [Item Name], [Principal], [Brand], [Transportation Cost]) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", 
                (new_id, item_data.gate_id, item_data.bu, item_data.item_code, item_data.item_name, item_data.principal, item_data.brand, item_data.transportation_cost))
            log_user_activity(user['username'], "CREATE_ITEM_PRICING", f"Added pricing for item {item_data.item_code} to gate ID {item_data.gate_id}")

        conn.commit()
        conn.close()
        return {"message": "Item saved successfully"}
    except HTTPException: raise
    except Exception as e: raise HTTPException(status_code=500, detail=f"Error saving item: {str(e)}")

@app.get("/account/items/{pricing_id}/logs", response_model=List[ItemLogItem])
def get_item_logs(pricing_id: int, user: dict = Depends(get_current_user)):
    try:
        conn = get_logistic_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, pricing_id, changed_by, change_date, field_name, old_value, new_value FROM Item_Change_Log WHERE pricing_id = ? ORDER BY change_date DESC", (pricing_id,))
        rows = cursor.fetchall()
        logs = [{"id": r[0], "pricing_id": r[1], "changed_by": r[2], "change_date": r[3], "field_name": r[4], "old_value": r[5], "new_value": r[6]} for r in rows]
        conn.close()
        return logs
    except Exception as e: raise HTTPException(status_code=500, detail=f"Error fetching logs: {str(e)}")

@app.delete("/account/item-pricing/{gate_id}/{item_code}")
def delete_item_pricing(gate_id: int, item_code: str, user: dict = Depends(require_permission("delete_item"))): 
    try:
        conn = get_logistic_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT [Pricing ID] FROM Item_Pricing WHERE [Gate ID] = ? AND [Item ID] = ?", (gate_id, item_code))
        row = cursor.fetchone()
        if row: cursor.execute("DELETE FROM Item_Change_Log WHERE pricing_id = ?", (row[0],))

        cursor.execute("DELETE FROM Item_Pricing WHERE [Gate ID] = ? AND [Item ID] = ?", (gate_id, item_code))
        if cursor.rowcount == 0:
            conn.close()
            raise HTTPException(status_code=404, detail="Item not found")
        conn.commit()
        conn.close()
        log_user_activity(user['username'], "DELETE_ITEM_PRICING", f"Deleted item {item_code} from gate {gate_id}")
        return {"message": "Item deleted successfully"}
    except Exception as e: raise HTTPException(status_code=500, detail=f"Error deleting item: {str(e)}")

@app.get("/dwbi/items/search")
def search_dwbi_items(q: str = Query(..., min_length=2)):
    try:
        conn = get_dwbi_connection()
        cursor = conn.cursor()
        search_term = f"%{q}%"
        cursor.execute("SELECT TOP 50 ItemCode, ItemName, ItmsGrpNam, U_BrandName, Sector FROM Itemmasterallpp WHERE ItemCode LIKE ? OR ItemName LIKE ?", (search_term, search_term))
        rows = cursor.fetchall()
        items = [{"item_code": r[0], "item_name": r[1], "principal": r[2], "brand": r[3], "bu": r[4]} for r in rows]
        conn.close()
        return {"items": items}
    except Exception as e: 
        raise HTTPException(status_code=500, detail=f"Error searching items: {str(e)}")

@app.get("/dwbi/items/validate")
def validate_dwbi_item(code: str = Query(...)):
    try:
        conn = get_dwbi_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT ItemCode, ItemName, ItmsGrpNam, U_BrandName, Sector FROM Itemmasterallpp WHERE ItemCode = ?", (code,))
        row = cursor.fetchone()
        conn.close()
        
        if row: 
            return {"valid": True, "item": {"item_code": row[0], "item_name": row[1], "principal": row[2], "brand": row[3], "bu": row[4]}}
        return {"valid": False}
    except Exception as e: 
        raise HTTPException(status_code=500, detail=f"Validation error: {str(e)}")

@app.get("/locations/from")
def get_from_locations():
    try:
        conn = get_logistic_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT [From] FROM Gate WHERE [From] IS NOT NULL ORDER BY [From]")
        rows = cursor.fetchall()
        conn.close()
        return {"locations": [r[0] for r in rows if r[0]]}
    except Exception as e: raise HTTPException(status_code=500, detail=f"Error loading from locations: {str(e)}")

@app.get("/locations/to")
def get_to_locations(from_loc: Optional[str] = None):
    try:
        conn = get_logistic_connection()
        cursor = conn.cursor()
        if from_loc: cursor.execute("SELECT DISTINCT [To] FROM Gate WHERE [From] = ? AND [To] IS NOT NULL ORDER BY [To]", (from_loc,))
        else: cursor.execute("SELECT DISTINCT [To] FROM Gate WHERE [To] IS NOT NULL ORDER BY [To]")
        rows = cursor.fetchall()
        conn.close()
        return {"locations": [r[0] for r in rows if r[0]]}
    except Exception as e: raise HTTPException(status_code=500, detail=f"Error loading to locations: {str(e)}")

@app.post("/calculate-with-gate")
def calculate_with_gate(
    gate_name: str, 
    from_loc: Optional[str] = Query(None),
    to_loc: Optional[str] = Query(None),
    doc_nums: List[str] = Query(...),
    manual_total_cost: Optional[float] = None, 
    additional_charges: Optional[float] = 0.0,
    user: dict = Depends(require_permission("view_calculator"))
):
    try:
        if not doc_nums: raise HTTPException(status_code=400, detail="No Doc Nums provided")
        return _perform_calculation_logic(
            gate_name=gate_name, 
            doc_nums=doc_nums, 
            from_loc=from_loc,
            to_loc=to_loc,
            manual_total_cost=manual_total_cost, 
            additional_charges=additional_charges
        )
    except HTTPException: raise
    except Exception as e: raise HTTPException(status_code=500, detail=f"Calculation error: {str(e)}")

@app.get("/doc-nums")
def get_doc_nums():
    try:
        conn = get_dwbi_connection()
        cursor = conn.cursor()
        query = """
            SELECT source, DocNum, DocDate FROM (
                SELECT 'PG' as source, DocNum, MAX(DocDate) as DocDate FROM PG_Transfer_Details WHERE DocNum IS NOT NULL GROUP BY DocNum
                UNION ALL
                SELECT 'PDG' as source, DocNum, MAX(DocDate) as DocDate FROM PDG_Transfer_Details WHERE DocNum IS NOT NULL GROUP BY DocNum
            ) t
            ORDER BY DocDate DESC, DocNum DESC
        """
        cursor.execute(query)
        rows = cursor.fetchall()
        doc_nums = []
        for row in rows:
            doc_date_val = row[2]
            if isinstance(doc_date_val, datetime.datetime): doc_date_str = doc_date_val.strftime("%Y-%m-%d")
            elif isinstance(doc_date_val, str) and len(doc_date_val) >= 10: doc_date_str = doc_date_val[:10]
            else: doc_date_str = str(doc_date_val) if doc_date_val else ""
            
            doc_nums.append({"doc_num": f"{row[0]} - {row[1]}", "doc_date": doc_date_str})
        conn.close()
        return {"doc_nums": doc_nums}
    except Exception as e: raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.get("/products-by-doc-nums")
def get_products_by_doc_nums(doc_nums: List[str] = Query(..., alias="doc_nums")):
    try:
        if not doc_nums: return {"products": [], "total_weight": 0}
        
        pg_nums = [str(d).replace("PG - ", "").replace("PG-", "") for d in doc_nums if not str(d).startswith("PDG")]
        pdg_nums = [str(d).replace("PDG - ", "").replace("PDG-", "") for d in doc_nums if str(d).startswith("PDG")]
        
        conn = get_dwbi_connection()
        cursor = conn.cursor()
        products, total_weight = [], 0.0
        
        if pg_nums:
            placeholders = ','.join('?' * len(pg_nums))
            cursor.execute(f"SELECT ItemCode, MAX(Dscription), MAX(UoM), SUM(ItemWeight), DocNum, SUM(BatchQtyByCtn), MAX(Brand), 'PG' FROM PG_Transfer_Details WHERE DocNum IN ({placeholders}) GROUP BY DocNum, ItemCode", pg_nums)
            rows = cursor.fetchall()
            for row in rows:
                weight = float(row[3]) if row[3] else 0.0
                total_weight += weight
                products.append({"code": row[0] or "", "name": row[1] or "", "uom": row[2] or "", "weight": weight, "ctns": get_rounded_ctns(row[5] if len(row) > 5 else 0), "brand": row[6] or "", "bu": row[7], "sin_no": f"{row[7]} - {row[4]}"})
                
        if pdg_nums:
            placeholders = ','.join('?' * len(pdg_nums))
            cursor.execute(f"SELECT ItemCode, MAX(Dscription), MAX(UoM), SUM(LineTotalWeight), DocNum, SUM(QtyCtn), MAX(Brand), 'PDG' FROM PDG_Transfer_Details WHERE DocNum IN ({placeholders}) GROUP BY DocNum, ItemCode", pdg_nums)
            rows = cursor.fetchall()
            for row in rows:
                weight = float(row[3]) if row[3] else 0.0
                total_weight += weight
                products.append({"code": row[0] or "", "name": row[1] or "", "uom": row[2] or "", "weight": weight, "ctns": get_rounded_ctns(row[5] if len(row) > 5 else 0), "brand": row[6] or "", "bu": row[7], "sin_no": f"{row[7]} - {row[4]}"})
        
        conn.close()
        return {"products": products, "total_weight": round(total_weight, 2)}
    except Exception as e: raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/products/{doc_num}")
def get_products_by_doc_num(doc_num: str):
    try:
        is_pdg = doc_num.startswith("PDG")
        actual_num = doc_num.replace("PDG - ", "").replace("PDG-", "").replace("PG - ", "").replace("PG-", "")

        conn = get_dwbi_connection()
        cursor = conn.cursor()

        if is_pdg:
            cursor.execute("SELECT ItemCode, MAX(Dscription), MAX(UoM), SUM(LineTotalWeight), DocNum, SUM(QtyCtn), MAX(Brand), 'PDG' FROM PDG_Transfer_Details WHERE DocNum = ? GROUP BY DocNum, ItemCode ORDER BY DocNum, ItemCode", (actual_num,))
        else:
            cursor.execute("SELECT ItemCode, MAX(Dscription), MAX(UoM), SUM(ItemWeight), DocNum, SUM(BatchQtyByCtn), MAX(Brand), 'PG' FROM PG_Transfer_Details WHERE DocNum = ? GROUP BY DocNum, ItemCode ORDER BY DocNum, ItemCode", (actual_num,))
            
        rows = cursor.fetchall()
        if not rows:
            conn.close()
            raise HTTPException(status_code=404, detail="No products found")
            
        products, total_weight = [], 0.0
        for row in rows:
            weight = float(row[3]) if row[3] else 0.0
            total_weight += weight
            products.append({"item_code": row[0] or "", "description": row[1] or "", "uom": row[2] or "", "item_weight": weight, "ctns": get_rounded_ctns(row[5] if len(row) > 5 else 0), "brand": row[6] or "", "bu": row[7]})
            
        conn.close()
        return {"products": products, "total_weight": round(total_weight, 2)}
    except Exception as e: raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
    
# --- Submitted Calculation Allocation Report Endpoints ---

@app.get("/account/submitted-allocation-report")
def get_submitted_allocation_report(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    user: dict = Depends(require_permission("view_daily_report"))
):
    """
    Fetches and flattens calculated products from submitted or claimed calculation histories
    to generate a comprehensive allocation report.
    """
    try:
        conn = get_logistic_connection()
        cursor = conn.cursor()

        # Query to fetch all submitted/claimed calculations with explicit submitted_at
        query = """
            SELECT 
                id, 
                submitted_at, 
                gate_name, 
                from_loc, 
                to_loc, 
                channel, 
                calculated_products 
            FROM Calculation_History 
            WHERE status IN ('submitted', 'claimed')
        """
        params = []

        # Apply date filters if provided
        if start_date and end_date:
            try:
                # Validate date format implicitly
                datetime.datetime.strptime(start_date, "%Y-%m-%d")
                datetime.datetime.strptime(end_date, "%Y-%m-%d")
                
                query += " AND SUBSTR(submitted_at, 1, 10) BETWEEN ? AND ?"
                params.extend([start_date, end_date])
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
        
        query += " ORDER BY submitted_at DESC"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        allocation_data = []

        # Flatten the calculated_products JSON into a tabular format
        for row in rows:
            calc_id = row[0]
            submitted_at = row[1]
            gate_name = row[2]
            from_loc = row[3]
            to_loc = row[4]
            channel = row[5]
            products_json = row[6]

            if not products_json:
                continue
            
            try:
                products = json.loads(products_json)
            except Exception as e:
                logger.error(f"Failed to parse calculated_products for ID {calc_id}: {str(e)}")
                continue
            
            for p in products:
                ctns = float(p.get("ctns", 0) or 0)
                cost = float(p.get("total_cost", 0) or 0)
                weight = float(p.get("weight", 0) or 0)
                
                # Skip items with no cost or cartons to keep the report clean
                if ctns <= 0 and cost <= 0:
                    continue 
                    
                allocation_data.append({
                    "calc_id": calc_id,
                    "submitted_at": submitted_at,
                    "doc_date": p.get("doc_date", ""),
                    "sin_no": p.get("sin_no", ""),
                    "gate_name": gate_name,
                    "from_loc": from_loc,
                    "to_loc": to_loc,
                    "channel": channel,
                    "bu": p.get("bu", ""),
                    "item_code": p.get("code", ""),
                    "item_name": p.get("name", ""),
                    "principal": p.get("principal", ""),
                    "brand": p.get("brand", ""),
                    "b_code": p.get("b_code", ""),
                    "b_name": p.get("b_name", ""),
                    "b_desc": p.get("b_desc", ""),
                    "s_dept": p.get("s_dept", ""),
                    "s_principal": p.get("s_principal", ""),
                    "ctns": ctns,
                    "weight": weight,
                    "total_cost": cost,
                    "unit_cost": p.get("unit_cost", 0),
                    "calculation_type": p.get("calculation_type", "")
                })

        return {
            "status": "success", 
            "total_records": len(allocation_data),
            "data": allocation_data
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating submitted allocation report: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating submitted allocation report: {str(e)}")
    
    
# --- Dashboard Helper Functions ---

def _generate_allocation_data(target_month: str, target_branch: Optional[str] = None):
    try:
        year, month = map(int, target_month.split('-'))
    except ValueError:
        raise ValueError("Invalid target_month format. Use YYYY-MM")

    months_list = []
    temp_year, temp_month = year, month
    for _ in range(12):
        months_list.append(f"{temp_year:04d}-{temp_month:02d}")
        temp_month -= 1
        if temp_month == 0:
            temp_month = 12
            temp_year -= 1

    valid_months = set(months_list)

    # Keep month0_label because the return statement needs it, 
    # but remove month1_label and month2_label.
    month0_label = months_list[0]

    start_date = f"{months_list[-1]}-01"
    _, last_day = calendar.monthrange(year, month)
    end_date = f"{year:04d}-{month:02d}-{last_day:02d}"

    conn = get_logistic_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT target_date, item_report_json 
        FROM Daily_Report_History 
        WHERE target_date >= ? AND target_date <= ?
    """, (start_date, end_date))
    rows = cursor.fetchall()
    conn.close()

    brands_data = {}
    available_branches = set()

    for row in rows:
        target_date_str = row[0]
        task_month = target_date_str[:7]
        
        if task_month not in valid_months:
            continue

        try:
            report_items = json.loads(row[1])
        except Exception:
            continue
            
        for item in report_items:
            brand = item.get("brand", "").strip() or "UNKNOWN"
            branch = item.get("branch", "").strip() or "UNKNOWN"
            
            # Collect unique branches for the frontend dropdown
            available_branches.add(branch)
            
            # Apply branch filter if provided
            if target_branch and target_branch.strip().lower() != branch.lower():
                continue
            
            try:
                ctns = float(item.get("ctns", 0) or 0)
                allocated_cost = float(item.get("allocated_cost", 0) or 0)
            except ValueError:
                continue

            if ctns <= 0:
                continue
                
            if brand not in brands_data:
                brands_data[brand] = {m: {"cost": 0.0, "ctns": 0.0} for m in months_list}

            brands_data[brand][task_month]["cost"] += allocated_cost
            brands_data[brand][task_month]["ctns"] += ctns

    dashboard_results = []
    for brand, data in brands_data.items():
        # Cleaned up result dictionary
        result = {
            "brand": brand
        }
        
        trend_data = []
        for m_label in reversed(months_list):
            t_cost = data[m_label]["cost"]
            t_ctns = data[m_label]["ctns"]
            avg_cost = (t_cost / t_ctns) if t_ctns > 0 else 0.0
            
            trend_data.append({
                "month": m_label,
                "avg_cost": round(avg_cost, 2),
                "total_ctns": round(t_ctns, 2),
                "total_cost": round(t_cost, 2)
            })
        
        result["trend"] = trend_data
        dashboard_results.append(result)

    # Fix the sorting to use the current month from the trend array instead of the deleted month_0 field
    dashboard_results.sort(key=lambda x: x["trend"][-1]["total_ctns"], reverse=True)
    
    return dashboard_results, month0_label, sorted(list(available_branches))


def _generate_calculated_data(target_month: str, target_to_loc: Optional[str] = None):
    try:
        year, month = map(int, target_month.split('-'))
    except ValueError:
        raise ValueError("Invalid target_month format. Use YYYY-MM")

    months_list = []
    temp_year, temp_month = year, month
    for _ in range(12):
        months_list.append(f"{temp_year:04d}-{temp_month:02d}")
        temp_month -= 1
        if temp_month == 0:
            temp_month = 12
            temp_year -= 1

    valid_months = set(months_list)

    # Keep month0_label for the return statement
    month0_label = months_list[0]

    conn = get_logistic_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT calculated_products, COALESCE(submitted_at, created_at), to_loc 
        FROM Calculation_History 
        WHERE status IN ('submitted', 'claimed')
    """)
    rows = cursor.fetchall()
    conn.close()

    brands_data = {}
    available_to_locs = set()

    for row in rows:
        if not row[0]:
            continue
        
        try:
            products = json.loads(row[0])
        except Exception:
            continue
        
        fallback_date = row[1][:10] if row[1] else "" 
        to_loc = row[2].strip() if row[2] else "UNKNOWN"
        
        # Collect unique locations for the frontend dropdown
        available_to_locs.add(to_loc)

        # Apply location filter if provided
        if target_to_loc and target_to_loc.strip().lower() != to_loc.lower():
            continue
        
        for p in products:
            brand = p.get("brand", "").strip() or "UNKNOWN"
            
            try:
                ctns = float(p.get("ctns", 0) or 0)
                cost = float(p.get("total_cost", 0) or 0)
            except ValueError:
                continue

            if ctns <= 0:
                continue
                
            doc_date_str = str(p.get("doc_date", ""))
            if len(doc_date_str) >= 7:
                task_month = doc_date_str[:7]
            elif len(fallback_date) >= 7:
                task_month = fallback_date[:7]
            else:
                continue

            if task_month in valid_months:
                if brand not in brands_data:
                    brands_data[brand] = {m: {"cost": 0.0, "ctns": 0.0} for m in months_list}

                brands_data[brand][task_month]["cost"] += cost
                brands_data[brand][task_month]["ctns"] += ctns

    dashboard_results = []
    for brand, data in brands_data.items():
        # Cleaned up result dictionary
        result = {
            "brand": brand
        }
        
        trend_data = []
        for m_label in reversed(months_list):
            t_cost = data[m_label]["cost"]
            t_ctns = data[m_label]["ctns"]
            avg_cost = (t_cost / t_ctns) if t_ctns > 0 else 0.0
            
            trend_data.append({
                "month": m_label,
                "avg_cost": round(avg_cost, 2),
                "total_ctns": round(t_ctns, 2),
                "total_cost": round(t_cost, 2)
            })
        
        result["trend"] = trend_data
        dashboard_results.append(result)

    # Fix the sorting to use the current month from the trend array
    dashboard_results.sort(key=lambda x: x["trend"][-1]["total_ctns"], reverse=True)
    return dashboard_results, month0_label, sorted(list(available_to_locs))


# --- Dashboard Endpoints ---

@app.get("/dashboard/brand-allocation-cost")
def get_brand_allocation_cost_dashboard(
    target_month: Optional[str] = None, 
    branch: Optional[str] = Query(None, description="Filter by Branch"),
    user: dict = Depends(get_current_user)
):
    if not target_month:
        target_month = datetime.datetime.now().strftime("%Y-%m")
    try:
        results, month, available_branches = _generate_allocation_data(target_month, target_branch=branch)
        return {
            "status": "success", 
            "target_month": month, 
            "data": results,
            "available_branches": available_branches
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating dashboard data: {str(e)}")
    
    
@app.get("/dashboard/calculated-brand-cost")
def get_calculated_brand_cost_dashboard(
    target_month: Optional[str] = None, 
    to_loc: Optional[str] = Query(None, description="Filter by To Location"),
    user: dict = Depends(require_permission("view_dashboard"))
):
    if not target_month:
        target_month = datetime.datetime.now().strftime("%Y-%m")
    try:
        results, month, available_to_locs = _generate_calculated_data(target_month, target_to_loc=to_loc)
        return {
            "status": "success", 
            "target_month": month, 
            "data": results,
            "available_to_locs": available_to_locs
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating calculated dashboard data: {str(e)}")


@app.get("/dashboard/combined")
def get_combined_dashboard(
    target_month: Optional[str] = None, 
    branch: Optional[str] = Query(None, description="Filter by Branch"),
    to_loc: Optional[str] = Query(None, description="Filter by To Location"),
    user: dict = Depends(require_permission("view_dashboard"))
):
    if not target_month:
        target_month = datetime.datetime.now().strftime("%Y-%m")
        
    try:
        alloc_data, month, available_branches = _generate_allocation_data(target_month, target_branch=branch)
        calc_data, _, available_to_locs = _generate_calculated_data(target_month, target_to_loc=to_loc)
        
        return {
            "status": "success",
            "target_month": month,
            "allocation_data": alloc_data,
            "calculated_data": calc_data,
            "available_branches": available_branches,
            "available_to_locs": available_to_locs
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating combined dashboard data: {str(e)}")


@app.get("/dashboard/principal-brand-allocation")
def get_principal_brand_allocation(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    user: dict = Depends(require_permission("view_dashboard"))
):
    """
    Independent endpoint that fetches available historical data 
    and groups it dynamically: BU -> Branch -> Principal -> Brand -> Item Name -> Date.
    """
    try:
        conn = get_logistic_connection()
        cursor = conn.cursor()
        
        query = "SELECT target_date, item_report_json FROM Daily_Report_History"
        params = []
        
        # Apply date filters
        if start_date and end_date:
            query += " WHERE target_date BETWEEN ? AND ?"
            params.extend([start_date, end_date])
        elif start_date:
            query += " WHERE target_date >= ?"
            params.append(start_date)
        elif end_date:
            query += " WHERE target_date <= ?"
            params.append(end_date)
            
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        hierarchy = {}

        for row in rows:
            target_date = row[0]
            if not target_date: continue
            
            try: items = json.loads(row[1])
            except Exception: continue

            for item in items:
                bu = str(item.get("bu", "")).strip() or "UNKNOWN"
                branch = str(item.get("branch", "")).strip() or "UNKNOWN"
                principal = str(item.get("principal", "")).strip() or "UNKNOWN"
                brand = str(item.get("brand", "")).strip() or "UNKNOWN"
                item_name = str(item.get("item_name", "")).strip() or "UNKNOWN"

                try:
                    ctns = float(item.get("ctns", 0) or 0)
                    cost = float(item.get("allocated_cost", 0) or 0)
                except ValueError:
                    continue

                if ctns <= 0: continue

                # Build dictionary: BU -> Branch -> Principal -> Brand -> Item Name -> Date
                if bu not in hierarchy: hierarchy[bu] = {}
                if branch not in hierarchy[bu]: hierarchy[bu][branch] = {}
                if principal not in hierarchy[bu][branch]: hierarchy[bu][branch][principal] = {}
                if brand not in hierarchy[bu][branch][principal]: hierarchy[bu][branch][principal][brand] = {}
                if item_name not in hierarchy[bu][branch][principal][brand]:
                    hierarchy[bu][branch][principal][brand][item_name] = {"ctns": 0.0, "cost": 0.0, "dates": {}}
                
                hierarchy[bu][branch][principal][brand][item_name]["ctns"] += ctns
                hierarchy[bu][branch][principal][brand][item_name]["cost"] += cost

                if target_date not in hierarchy[bu][branch][principal][brand][item_name]["dates"]:
                    hierarchy[bu][branch][principal][brand][item_name]["dates"][target_date] = {"ctns": 0.0, "cost": 0.0}
                
                hierarchy[bu][branch][principal][brand][item_name]["dates"][target_date]["ctns"] += ctns
                hierarchy[bu][branch][principal][brand][item_name]["dates"][target_date]["cost"] += cost

        result = []
        for bu, branch_data in hierarchy.items():
            bu_total_cost = 0.0; bu_total_ctns = 0.0; bu_branches = []
            
            for branch, princ_data in branch_data.items():
                b_total_cost = 0.0; b_total_ctns = 0.0; branch_principals = []
                
                for princ, brand_data in princ_data.items():
                    p_total_cost = 0.0; p_total_ctns = 0.0; princ_brands = []
                    
                    for brnd, item_data in brand_data.items():
                        br_total_cost = 0.0; br_total_ctns = 0.0; br_items = []
                        
                        for itm, d_data in item_data.items():
                            i_total_cost = d_data["cost"]; i_total_ctns = d_data["ctns"]
                            
                            i_dates = []
                            for date, d_vals in d_data["dates"].items():
                                d_avg_cost = d_vals["cost"] / d_vals["ctns"] if d_vals["ctns"] > 0 else 0
                                i_dates.append({
                                    "date": date,
                                    "avg_cost": round(d_avg_cost, 2),
                                    "total_cost": round(d_vals["cost"], 2),
                                    "total_ctns": round(d_vals["ctns"], 2)
                                })
                            
                            i_dates.sort(key=lambda x: x["date"], reverse=True)
                            i_avg_cost = i_total_cost / i_total_ctns if i_total_ctns > 0 else 0
                            
                            br_items.append({
                                "item_name": itm,
                                "avg_cost": round(i_avg_cost, 2),
                                "total_cost": round(i_total_cost, 2),
                                "total_ctns": round(i_total_ctns, 2),
                                "dates": i_dates
                            })
                            
                            br_total_cost += i_total_cost
                            br_total_ctns += i_total_ctns
                        
                        br_items.sort(key=lambda x: x["item_name"])
                        br_avg_cost = br_total_cost / br_total_ctns if br_total_ctns > 0 else 0
                        
                        princ_brands.append({
                            "brand": brnd,
                            "avg_cost": round(br_avg_cost, 2),
                            "total_cost": round(br_total_cost, 2),
                            "total_ctns": round(br_total_ctns, 2),
                            "items": br_items
                        })
                        
                        p_total_cost += br_total_cost
                        p_total_ctns += br_total_ctns
                        
                    princ_brands.sort(key=lambda x: x["brand"])
                    p_avg_cost = p_total_cost / p_total_ctns if p_total_ctns > 0 else 0
                    
                    branch_principals.append({
                        "principal": princ,
                        "avg_cost": round(p_avg_cost, 2),
                        "total_cost": round(p_total_cost, 2),
                        "total_ctns": round(p_total_ctns, 2),
                        "brands": princ_brands
                    })
                    
                    b_total_cost += p_total_cost
                    b_total_ctns += p_total_ctns
                
                branch_principals.sort(key=lambda x: x["principal"])
                b_avg_cost = b_total_cost / b_total_ctns if b_total_ctns > 0 else 0
                
                bu_branches.append({
                    "branch": branch,
                    "avg_cost": round(b_avg_cost, 2),
                    "total_cost": round(b_total_cost, 2),
                    "total_ctns": round(b_total_ctns, 2),
                    "principals": branch_principals
                })
                
                bu_total_cost += b_total_cost
                bu_total_ctns += b_total_ctns
            
            bu_branches.sort(key=lambda x: x["branch"])
            bu_avg_cost = bu_total_cost / bu_total_ctns if bu_total_ctns > 0 else 0
            
            result.append({
                "bu": bu,
                "avg_cost": round(bu_avg_cost, 2),
                "total_cost": round(bu_total_cost, 2),
                "total_ctns": round(bu_total_ctns, 2),
                "branches": bu_branches
            })
        
        result.sort(key=lambda x: x["bu"])
        return {"status": "success", "data": result}

    except Exception as e:
        logger.error(f"Error generating dynamic allocation hierarchy: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating hierarchy data: {str(e)}")
    
    
    
@app.get("/dashboard/third-party-allocation")
def get_third_party_allocation(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    user: dict = Depends(require_permission("view_dashboard"))
):
    """
    Independent endpoint that fetches calculated third-party data 
    and groups it dynamically: BU -> To_Loc (Branch) -> Principal -> Brand -> Item Name -> Date.
    """
    try:
        conn = get_logistic_connection()
        cursor = conn.cursor()
        
        query = "SELECT submitted_at, to_loc, calculated_products FROM Calculation_History WHERE status IN ('submitted', 'claimed')"
        params = []
        
        # Apply date filters
        if start_date and end_date:
            query += " AND SUBSTR(submitted_at, 1, 10) BETWEEN ? AND ?"
            params.extend([start_date, end_date])
        elif start_date:
            query += " AND SUBSTR(submitted_at, 1, 10) >= ?"
            params.append(start_date)
        elif end_date:
            query += " AND SUBSTR(submitted_at, 1, 10) <= ?"
            params.append(end_date)
            
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        hierarchy = {}

        for row in rows:
            submitted_at = row[0]
            target_date = submitted_at[:10] if submitted_at else ""
            if not target_date: continue
            
            to_loc = str(row[1] or "UNKNOWN").strip()
            
            try: items = json.loads(row[2])
            except Exception: continue

            for item in items:
                bu = str(item.get("bu", "")).strip() or "UNKNOWN"
                principal = str(item.get("principal", "")).strip() or "UNKNOWN"
                brand = str(item.get("brand", "")).strip() or "UNKNOWN"
                item_name = str(item.get("name", "")).strip() or "UNKNOWN"

                try:
                    ctns = float(item.get("ctns", 0) or 0)
                    cost = float(item.get("total_cost", 0) or 0)
                except ValueError:
                    continue

                if ctns <= 0: continue

                # Build dictionary: BU -> To Loc -> Principal -> Brand -> Item Name -> Date
                if bu not in hierarchy: hierarchy[bu] = {}
                if to_loc not in hierarchy[bu]: hierarchy[bu][to_loc] = {}
                if principal not in hierarchy[bu][to_loc]: hierarchy[bu][to_loc][principal] = {}
                if brand not in hierarchy[bu][to_loc][principal]: hierarchy[bu][to_loc][principal][brand] = {}
                if item_name not in hierarchy[bu][to_loc][principal][brand]:
                    hierarchy[bu][to_loc][principal][brand][item_name] = {"ctns": 0.0, "cost": 0.0, "dates": {}}
                
                hierarchy[bu][to_loc][principal][brand][item_name]["ctns"] += ctns
                hierarchy[bu][to_loc][principal][brand][item_name]["cost"] += cost

                if target_date not in hierarchy[bu][to_loc][principal][brand][item_name]["dates"]:
                    hierarchy[bu][to_loc][principal][brand][item_name]["dates"][target_date] = {"ctns": 0.0, "cost": 0.0}
                
                hierarchy[bu][to_loc][principal][brand][item_name]["dates"][target_date]["ctns"] += ctns
                hierarchy[bu][to_loc][principal][brand][item_name]["dates"][target_date]["cost"] += cost

        result = []
        for bu, branch_data in hierarchy.items():
            bu_total_cost = 0.0; bu_total_ctns = 0.0; bu_branches = []
            
            for branch, princ_data in branch_data.items():
                b_total_cost = 0.0; b_total_ctns = 0.0; branch_principals = []
                
                for princ, brand_data in princ_data.items():
                    p_total_cost = 0.0; p_total_ctns = 0.0; princ_brands = []
                    
                    for brnd, item_data in brand_data.items():
                        br_total_cost = 0.0; br_total_ctns = 0.0; br_items = []
                        
                        for itm, d_data in item_data.items():
                            i_total_cost = d_data["cost"]; i_total_ctns = d_data["ctns"]
                            
                            i_dates = []
                            for date, d_vals in d_data["dates"].items():
                                d_avg_cost = d_vals["cost"] / d_vals["ctns"] if d_vals["ctns"] > 0 else 0
                                i_dates.append({
                                    "date": date,
                                    "avg_cost": round(d_avg_cost, 2),
                                    "total_cost": round(d_vals["cost"], 2),
                                    "total_ctns": round(d_vals["ctns"], 2)
                                })
                            
                            i_dates.sort(key=lambda x: x["date"], reverse=True)
                            i_avg_cost = i_total_cost / i_total_ctns if i_total_ctns > 0 else 0
                            
                            br_items.append({
                                "item_name": itm,
                                "avg_cost": round(i_avg_cost, 2),
                                "total_cost": round(i_total_cost, 2),
                                "total_ctns": round(i_total_ctns, 2),
                                "dates": i_dates
                            })
                            
                            br_total_cost += i_total_cost
                            br_total_ctns += i_total_ctns
                        
                        br_items.sort(key=lambda x: x["item_name"])
                        br_avg_cost = br_total_cost / br_total_ctns if br_total_ctns > 0 else 0
                        
                        princ_brands.append({
                            "brand": brnd,
                            "avg_cost": round(br_avg_cost, 2),
                            "total_cost": round(br_total_cost, 2),
                            "total_ctns": round(br_total_ctns, 2),
                            "items": br_items
                        })
                        
                        p_total_cost += br_total_cost
                        p_total_ctns += br_total_ctns
                        
                    princ_brands.sort(key=lambda x: x["brand"])
                    p_avg_cost = p_total_cost / p_total_ctns if p_total_ctns > 0 else 0
                    
                    branch_principals.append({
                        "principal": princ,
                        "avg_cost": round(p_avg_cost, 2),
                        "total_cost": round(p_total_cost, 2),
                        "total_ctns": round(p_total_ctns, 2),
                        "brands": princ_brands
                    })
                    
                    b_total_cost += p_total_cost
                    b_total_ctns += p_total_ctns
                
                branch_principals.sort(key=lambda x: x["principal"])
                b_avg_cost = b_total_cost / b_total_ctns if b_total_ctns > 0 else 0
                
                bu_branches.append({
                    "branch": branch,
                    "avg_cost": round(b_avg_cost, 2),
                    "total_cost": round(b_total_cost, 2),
                    "total_ctns": round(b_total_ctns, 2),
                    "principals": branch_principals
                })
                
                bu_total_cost += b_total_cost
                bu_total_ctns += b_total_ctns
            
            bu_branches.sort(key=lambda x: x["branch"])
            bu_avg_cost = bu_total_cost / bu_total_ctns if bu_total_ctns > 0 else 0
            
            result.append({
                "bu": bu,
                "avg_cost": round(bu_avg_cost, 2),
                "total_cost": round(bu_total_cost, 2),
                "total_ctns": round(bu_total_ctns, 2),
                "branches": bu_branches
            })
        
        result.sort(key=lambda x: x["bu"])
        return {"status": "success", "data": result}

    except Exception as e:
        logger.error(f"Error generating third party allocation hierarchy: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating hierarchy data: {str(e)}")
    
    
    
# --- Cost Comparison Report Endpoint ---

@app.get("/dashboard/cost-comparison")
def get_cost_comparison(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    user: dict = Depends(require_permission("view_dashboard"))
):
    """
    Endpoint for the combined Logistics Cost comparison tab.
    Merges Rate Cart (Daily Report) and Calculated Cost (Third Party) data using DocDate.
    """
    try:
        conn = get_logistic_connection()
        cursor = conn.cursor()
        
        # 1. Fetch Rate Cart Data (Already uses target_date/doc date)
        rc_query = "SELECT target_date, item_report_json FROM Daily_Report_History WHERE 1=1"
        rc_params = []
        if start_date and end_date:
            rc_query += " AND target_date BETWEEN ? AND ?"
            rc_params.extend([start_date, end_date])
        elif start_date:
            rc_query += " AND target_date >= ?"
            rc_params.append(start_date)
        elif end_date:
            rc_query += " AND target_date <= ?"
            rc_params.append(end_date)
            
        cursor.execute(rc_query, rc_params)
        rc_rows = cursor.fetchall()
        
        # 2. Fetch Calculated Cost Data
        # We NO LONGER filter by submitted_at in SQL because we need to check the doc_date inside the JSON
        cc_query = "SELECT submitted_at, to_loc, calculated_products FROM Calculation_History WHERE status IN ('submitted', 'claimed')"
        cursor.execute(cc_query)
        cc_rows = cursor.fetchall()
        
        # 3. Fetch Location Mappings 
        cursor.execute("SELECT to_location, branch_code FROM Location_Mapping")
        mapping_rows = cursor.fetchall()
        
        LOCATION_MAP = {}
        DISPLAY_MAP = {} 
        
        for row in mapping_rows:
            if row[0] and row[1]:
                raw_to_loc = str(row[0]).strip()
                raw_branch = str(row[1]).strip()
                LOCATION_MAP[raw_to_loc.upper()] = raw_branch.upper()
                DISPLAY_MAP[raw_branch.upper()] = raw_to_loc
        
        conn.close()
        
        comparison_dict = {}
        
        # --- Process Rate Cart Data ---
        for row in rc_rows:
            date = row[0]
            if not date: continue
            
            try:
                items = json.loads(row[1])
            except Exception:
                continue
                
            for item in items:
                bu = str(item.get("bu", "")).strip() or "UNKNOWN"
                branch = str(item.get("branch", "")).strip().upper() or "UNKNOWN"
                principal = str(item.get("principal", "")).strip() or "UNKNOWN"
                brand = str(item.get("brand", "")).strip() or "UNKNOWN"
                item_code = str(item.get("item_code", "")).strip() or "UNKNOWN"
                item_name = str(item.get("item_name", "")).strip() or "UNKNOWN"
                
                try:
                    ctns = float(item.get("ctns", 0) or 0)
                    cost = float(item.get("allocated_cost", 0) or 0)
                except ValueError:
                    continue
                    
                if ctns <= 0: continue
                
                key = (date, bu, branch, principal, brand, item_code, item_name)
                if key not in comparison_dict:
                    comparison_dict[key] = {"rc_ctns": 0.0, "rc_cost": 0.0, "cc_ctns": 0.0, "cc_cost": 0.0}
                
                comparison_dict[key]["rc_ctns"] += ctns
                comparison_dict[key]["rc_cost"] += cost
                
        # --- Process Calculated Cost Data ---
        for row in cc_rows:
            submitted_at = row[0]
            fallback_date = submitted_at[:10] if submitted_at else ""
            raw_to_loc = str(row[1] or "UNKNOWN").strip().upper()
            
            try:
                items = json.loads(row[2])
            except Exception:
                continue
                
            for item in items:
                # --- NEW DOC DATE LOGIC ---
                doc_date_raw = str(item.get("doc_date", "")).strip()
                # Use doc_date if available, otherwise fallback to submitted_at
                item_date = doc_date_raw[:10] if len(doc_date_raw) >= 10 else fallback_date
                
                if not item_date: 
                    continue
                    
                # Apply Date Filtering in Python based on the exact Doc Date
                if start_date and item_date < start_date:
                    continue
                if end_date and item_date > end_date:
                    continue
                # --------------------------

                bu = str(item.get("bu", "")).strip() or "UNKNOWN"
                branch = LOCATION_MAP.get(raw_to_loc, raw_to_loc)
                principal = str(item.get("principal", "")).strip() or "UNKNOWN"
                brand = str(item.get("brand", "")).strip() or "UNKNOWN"
                item_code = str(item.get("code", "")).strip() or "UNKNOWN"
                item_name = str(item.get("name", "")).strip() or "UNKNOWN"
                
                try:
                    ctns = float(item.get("ctns", 0) or 0)
                    cost = float(item.get("total_cost", 0) or 0)
                except ValueError:
                    continue
                    
                if ctns <= 0: continue
                
                # Group by item_date (doc_date) instead of submitted date
                key = (item_date, bu, branch, principal, brand, item_code, item_name)
                if key not in comparison_dict:
                    comparison_dict[key] = {"rc_ctns": 0.0, "rc_cost": 0.0, "cc_ctns": 0.0, "cc_cost": 0.0}
                    
                comparison_dict[key]["cc_ctns"] += ctns
                comparison_dict[key]["cc_cost"] += cost
                
        # --- Format Final Results ---
        result = []
        for key, val in comparison_dict.items():
            date, bu, branch, principal, brand, item_code, item_name = key
            
            rc_avg = val["rc_cost"] / val["rc_ctns"] if val["rc_ctns"] > 0 else None
            cc_avg = val["cc_cost"] / val["cc_ctns"] if val["cc_ctns"] > 0 else None
            
            if rc_avg is None and cc_avg is None:
                continue
                
            total_avg = 0.0
            if rc_avg is not None: total_avg += rc_avg
            if cc_avg is not None: total_avg += cc_avg
            
            display_branch = branch
            if branch in DISPLAY_MAP:
                display_branch = f"{branch} / {DISPLAY_MAP[branch]}"
                
            result.append({
                "date": date,
                "bu": bu,
                "branch": display_branch, 
                "principal": principal,
                "brand": brand,
                "item_code": item_code,
                "item_name": item_name,
                "avg_cost_rate_cart": round(rc_avg, 2) if rc_avg is not None else None,
                "avg_cost_calculated": round(cc_avg, 2) if cc_avg is not None else None,
                "total_avg_cost": round(total_avg, 2)
            })
            
        result.sort(key=lambda x: (x["date"], x["branch"], x["item_code"]), reverse=True)
        
        return {
            "status": "success",
            "data": result
        }

    except Exception as e:
        logger.error(f"Error generating cost comparison report: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating comparison data: {str(e)}")
    
    
# --- Daily Report Excel Export Endpoints ---

@app.get("/account/daily-rate-cut-report/export")
def export_daily_rate_cut_report(
    request: Request,
    report_type: str = Query(..., description="'item' or 'township'"),
    target_date: Optional[str] = None, 
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    user: dict = Depends(require_permission("view_daily_report"))
):
    try:
        # 1. Fetch Data
        if start_date and end_date:
            start_dt = datetime.datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.datetime.strptime(end_date, "%Y-%m-%d")
            if start_dt > end_dt: 
                raise HTTPException(status_code=400, detail="start_date cannot be after end_date")
            
            daily_datas = []
            current_dt = start_dt
            while current_dt <= end_dt:
                daily_datas.append(get_or_generate_daily_report(current_dt.strftime("%Y-%m-%d")))
                current_dt += datetime.timedelta(days=1)
            
            aggregated = _aggregate_reports(daily_datas)
            report_data = aggregated["item_report"] if report_type == 'item' else aggregated["township_report"]
            date_str = f"{start_date}_to_{end_date}"
        else:
            if not target_date: 
                target_date = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
            
            data = get_or_generate_daily_report(target_date)
            report_data = data["item_report"] if report_type == 'item' else data["township_report"]
            date_str = target_date

        # --- NEW: Apply Dynamic Filters ---
        filters = dict(request.query_params)
        # Pop the API specific parameters so they aren't treated as raw text filters
        for k in ['report_type', 'target_date', 'start_date', 'end_date']:
            filters.pop(k, None) 
            
        if filters:
            filtered_data = []
            for row in report_data:
                match = True
                for key, val in filters.items():
                    # Map the frontend 'date_filter' to the actual row key 'target_date'
                    actual_key = 'target_date' if key == 'date_filter' else key
                    
                    row_val = str(row.get(actual_key, '')).lower()
                    if str(val).lower() not in row_val:
                        match = False
                        break
                if match:
                    filtered_data.append(row)
            report_data = filtered_data
        # ----------------------------------

        # 2. Build Excel Workbook
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Item Allocation" if report_type == 'item' else "Township Allocation"
        
        header_fill = PatternFill(start_color='4472C4', end_color='4472C4', fill_type='solid')
        header_font = Font(bold=True, color='FFFFFF')
        border_style = Side(border_style="thin", color="000000")
        border = Border(left=border_style, right=border_style, top=border_style, bottom=border_style)

        # 3. Define Headers (Date added as the second column)
        if report_type == 'item':
            headers = [
                "BU", "Date", "Branch", "Driver Name", "Principal", "Brand", "Item Code", "Item Name", 
                "Cartons", "Driver Total (Ctns)", "Branch Rate Cost", "Cost per Carton", 
                "Allocated Cost", "Sales Amount"
            ]
        else:
            headers = [
                "Branch", "Date", "Driver Name", "Township", "Customer Code", "Contact Person", 
                "Customer Total (Ctns)", "Driver Total (Ctns)", "Branch Rate Cost", "Total Drop Points", 
                "Cost per Drop Point", "Cost per Carton", "Allocated Cost", "Sales Amount"
            ]

        for col_num, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col_num, value=header)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal='center')
            cell.border = border

        # 4. Write Rows (Adding row.get("target_date") at index 1)
        for idx, row in enumerate(report_data, 2):
            if report_type == 'item':
                row_data = [
                    row.get("bu", "-"), row.get("target_date", ""), row.get("branch", ""), row.get("driver_name", ""),
                    row.get("principal", ""), row.get("brand", ""), row.get("item_code", ""),
                    row.get("item_name", ""), row.get("ctns", 0), row.get("driver_total_ctns", 0),
                    row.get("branch_cost", 0), row.get("cost_per_carton", 0), row.get("allocated_cost", 0),
                    row.get("sales_amount", 0)
                ]
            else:
                row_data = [
                    row.get("branch", ""), row.get("target_date", ""), row.get("driver_name", ""), row.get("township", ""),
                    row.get("customer_code", ""), row.get("contact_person", ""), row.get("ctns", 0),
                    row.get("driver_total_ctns", 0), row.get("branch_cost", 0), row.get("total_drop_points", 0),
                    row.get("cost_per_drop_point", 0), row.get("cost_per_carton", 0), row.get("allocated_cost", 0),
                    row.get("sales_amount", 0)
                ]
            
            for col_num, val in enumerate(row_data, 1):
                cell = ws.cell(row=idx, column=col_num, value=val)
                cell.border = border
                if isinstance(val, (int, float)):
                    cell.number_format = '#,##0.00'

        for col in ws.columns:
            max_length = 0
            col_letter = col[0].column_letter
            for cell in col:
                try:
                    if len(str(cell.value)) > max_length: 
                        max_length = len(str(cell.value))
                except: 
                    pass
            ws.column_dimensions[col_letter].width = min(max_length + 2, 50)

        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        filename = f"{report_type}_allocation_{date_str}.xlsx"
        
        return StreamingResponse(
            output, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error exporting daily report: {str(e)}")


@app.get("/account/submitted-allocation-report/export")
def export_submitted_allocation_report(
    request: Request,
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    user: dict = Depends(require_permission("view_daily_report"))
):
    try:
        report_response = get_submitted_allocation_report(start_date, end_date, user)
        allocation_data = report_response["data"]

        # --- NEW: Apply Dynamic Filters ---
        filters = dict(request.query_params)
        for k in ['start_date', 'end_date']:
            filters.pop(k, None)
            
        if filters:
            filtered_data = []
            for row in allocation_data:
                match = True
                for key, val in filters.items():
                    # Map the frontend text search filter to actual data key
                    actual_key = 'submitted_at' if key == 'date_filter' else key
                    
                    if actual_key == 'route':
                        route_str = f"{row.get('from_loc', '')} {row.get('to_loc', '')}".lower()
                        if val.lower() not in route_str:
                            match = False
                            break
                    else:
                        row_val = str(row.get(actual_key, '')).lower()
                        
                        # Only match against the date part so time doesn't break the filter
                        if actual_key == 'submitted_at':
                            row_val = row_val[:10]
                            
                        if val.lower() not in row_val:
                            match = False
                            break
                if match:
                    filtered_data.append(row)
            allocation_data = filtered_data
        # ----------------------------------

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Submitted Allocations"
        
        header_fill = PatternFill(start_color='4472C4', end_color='4472C4', fill_type='solid')
        header_font = Font(bold=True, color='FFFFFF')
        border_style = Side(border_style="thin", color="000000")
        border = Border(left=border_style, right=border_style, top=border_style, bottom=border_style)

        headers = [
            "Calc ID", "Date", "Doc Date", "SIN No", "Gate Name", "From Loc", "To Loc", "Channel",
            "BU", "Item Code", "Item Name", "Principal", "Brand", "B-Code", "B-Name", "B-Desc", "S-Dept", 
            "S-Principal", "Cartons", "Weight", "Unit Cost", "Total Cost", "Calculation Type"
        ]

        for col_num, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col_num, value=header)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal='center')
            cell.border = border

        for idx, row in enumerate(allocation_data, 2):
            
            # Extract just the Date (YYYY-MM-DD) from the full timestamp
            raw_date = row.get("submitted_at", "")
            formatted_date = raw_date[:10] if raw_date else ""

            row_data = [
                row.get("calc_id", ""), formatted_date, row.get("doc_date", ""),
                row.get("sin_no", ""), row.get("gate_name", ""), row.get("from_loc", ""),
                row.get("to_loc", ""), row.get("channel", ""), row.get("bu", ""),
                row.get("item_code", ""), row.get("item_name", ""), row.get("principal", ""),
                row.get("brand", ""), row.get("b_code", ""), row.get("b_name", ""),
                row.get("b_desc", ""), row.get("s_dept", ""), row.get("s_principal", ""),
                row.get("ctns", 0), row.get("weight", 0), row.get("unit_cost", 0),
                row.get("total_cost", 0), row.get("calculation_type", "")
            ]
            
            for col_num, val in enumerate(row_data, 1):
                cell = ws.cell(row=idx, column=col_num, value=val)
                cell.border = border
                if isinstance(val, (int, float)):
                    cell.number_format = '#,##0.00'

        for col in ws.columns:
            max_length = 0
            col_letter = col[0].column_letter
            for cell in col:
                try:
                    if len(str(cell.value)) > max_length: 
                        max_length = len(str(cell.value))
                except: 
                    pass
            ws.column_dimensions[col_letter].width = min(max_length + 2, 50)

        date_str = f"{start_date}_to_{end_date}" if start_date and end_date else "all_time"
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        filename = f"submitted_allocation_report_{date_str}.xlsx"
        
        return StreamingResponse(
            output, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error exporting submitted report: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)