import React, { useState, useEffect } from 'react';
import { Trash2, Calculator, Database, FileText, Plus, Edit2, Download, Upload, X, History, Save, FileDown, LogOut, User, Users, List as ListIcon, Search, Clock, CheckCircle, Shield, Scissors, Calendar, ShoppingCart, Percent } from 'lucide-react';

const API_URL = 'http://localhost:8000';

const AVAILABLE_PERMISSIONS = [
  { id: 'view_users', label: 'View Users' },
  { id: 'add_user', label: 'Add User' },
  { id: 'edit_user', label: 'Edit User' },
  { id: 'delete_user', label: 'Delete User' },
  { id: 'view_roles', label: 'View Roles' },
  { id: 'add_role', label: 'Add Role' },
  { id: 'edit_role', label: 'Edit Role' },
  { id: 'delete_role', label: 'Delete Role' },
  { id: 'view_gates', label: 'View Gates' },
  { id: 'add_gate', label: 'Add Gate' },
  { id: 'edit_gate', label: 'Edit Gate' },
  { id: 'delete_gate', label: 'Delete Gate' },
  { id: 'view_items', label: 'View Items' },
  { id: 'add_item', label: 'Add Item' },
  { id: 'edit_item', label: 'Edit Item' },
  { id: 'delete_item', label: 'Delete Item' },
  { id: 'view_references', label: 'View References' },
  { id: 'add_reference', label: 'Add Reference' },
  { id: 'delete_reference', label: 'Delete Reference' },
  { id: 'view_all_history', label: 'View All History' },
  { id: 'submit_calculation', label: 'Submit Calculation' },
  { id: 'claim_calculation', label: 'Claim Calculation' },
  { id: 'delete_history', label: 'Delete History' },
  { id: 'view_rate_carts', label: 'View Rate Carts' },
  { id: 'add_rate_cart', label: 'Add Rate Cart' },
  { id: 'edit_rate_cart', label: 'Edit Rate Cart' },
  { id: 'delete_rate_cart', label: 'Delete Rate Cart' },
  { id: 'view_daily_report', label: 'View Daily Report' }
];

// --- Login Component ---
const LoginScreen = ({ onLogin }) => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    
    const formData = new FormData();
    formData.append('username', username);
    formData.append('password', password);

    try {
      const response = await fetch(`${API_URL}/token`, {
        method: 'POST',
        body: formData,
      });

      if (response.ok) {
        const data = await response.json();
        onLogin(data);
      } else {
        setError('Invalid username or password');
      }
    } catch (err) {
      setError('Login failed. Check server connection.');
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-100">
      <div className="bg-white p-8 rounded-lg shadow-md w-96">
        <h1 className="text-2xl font-bold mb-6 text-center text-blue-600">Logistic App Login</h1>
        {error && <div className="bg-red-100 text-red-700 p-2 rounded mb-4 text-sm text-center">{error}</div>}
        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label className="block text-gray-700 text-sm font-bold mb-2">Username <span className="text-red-500">*</span></label>
            <input type="text" value={username} onChange={(e) => setUsername(e.target.value)} className="w-full p-2 border rounded focus:outline-none focus:border-blue-500" placeholder="Enter username" required />
          </div>
          <div className="mb-6">
            <label className="block text-gray-700 text-sm font-bold mb-2">Password <span className="text-red-500">*</span></label>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} className="w-full p-2 border rounded focus:outline-none focus:border-blue-500" placeholder="Enter password" required />
          </div>
          <button type="submit" className="w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700 transition font-semibold">Sign In</button>
        </form>
      </div>
    </div>
  );
};

// --- Main Application Component ---
const PricingApp = () => {
  // --- Global UI Zoom Effect ---
  useEffect(() => {
    document.documentElement.style.fontSize = '14px';
    return () => { document.documentElement.style.fontSize = ''; };
  }, []);

  // Auth State
  const [token, setToken] = useState(localStorage.getItem('token') || null);
  const [userRole, setUserRole] = useState(localStorage.getItem('userRole') || null);
  const [username, setUsername] = useState(localStorage.getItem('username') || '');
  const [permissions, setPermissions] = useState(JSON.parse(localStorage.getItem('permissions')) || []);

  // App State
  const [currentPage, setCurrentPage] = useState('calculator');
  const [docNums, setDocNums] = useState([]); 
  const [selectedDocNums, setSelectedDocNums] = useState([]); 
  const [docNumSearchTerm, setDocNumSearchTerm] = useState('');
  const [showDocNumDropdown, setShowDocNumDropdown] = useState(false);
  
  const [fromLocations, setFromLocations] = useState([]);
  const [toLocations, setToLocations] = useState([]);
  const [selectedFrom, setSelectedFrom] = useState('');
  const [selectedTo, setSelectedTo] = useState('');
  
  const [gates, setGates] = useState([]);
  const [selectedGate, setSelectedGate] = useState('');
  
  const [products, setProducts] = useState([]);
  const [totalWeight, setTotalWeight] = useState(0);
  const [calculationType, setCalculationType] = useState('');
  const [calculatedProducts, setCalculatedProducts] = useState([]);
  
  const [calculatedTotalCost, setCalculatedTotalCost] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [notification, setNotification] = useState(null);

  const [gateData, setGateData] = useState([]);
  const [selectedGateForPricing, setSelectedGateForPricing] = useState('');
  const [itemPricingData, setItemPricingData] = useState([]);
  
  const [itemFilters, setItemFilters] = useState({ item_code: '', item_name: '', principal: '', brand: '', transportation_cost: '' });

  const [editingGate, setEditingGate] = useState(null);
  const [editingItem, setEditingItem] = useState(null);
  const [showAddGateModal, setShowAddGateModal] = useState(false);
  const [showAddItemModal, setShowAddItemModal] = useState(false);
  const [confirmDialog, setConfirmDialog] = useState(null);
  const [originalGateName, setOriginalGateName] = useState(null);
  const [originalItemCode, setOriginalItemCode] = useState(null);

  const [manualTotalCost, setManualTotalCost] = useState('');
  const [isManualTotalCostEnabled, setIsManualTotalCostEnabled] = useState(false);
  const [additionalCharges, setAdditionalCharges] = useState('');
  const [estimatedTotalCost, setEstimatedTotalCost] = useState(null);

  const [historyData, setHistoryData] = useState([]);
  const [currentHistoryId, setCurrentHistoryId] = useState(null);
  const [historyFilters, setHistoryFilters] = useState({ id_status: '', date: '', route: '', doc_nums: '', total_cost: '', author: '' });

  // Rate Cart State
  const [rateCarts, setRateCarts] = useState([]);
  const [showRateCartModal, setShowRateCartModal] = useState(false);
  const [editingRateCart, setEditingRateCart] = useState(null);

  // Daily Report State
  const [dailyReportDate, setDailyReportDate] = useState('');
  const [dailyReportData, setDailyReportData] = useState([]);
  const [dailyTownshipReportData, setDailyTownshipReportData] = useState([]);
  const [isDailyReportLoading, setIsDailyReportLoading] = useState(false);
  const [activeDailyTab, setActiveDailyTab] = useState('item'); 
  
  const [dailyReportFilters, setDailyReportFilters] = useState({ 
    branch: '', item_code: '', item_name: '', principal: '', brand: '', driver_name: '',
    ctns: '', driver_total_ctns: '', branch_cost: '', cost_per_carton: '', allocated_cost: '' 
  });
  
  const [townshipFilters, setTownshipFilters] = useState({ 
    branch: '', driver_name: '', township: '', customer_code: '', ctns: '', driver_total_ctns: '', branch_cost: '', total_drop_points: '', cost_per_drop_point: '', cost_per_carton: '', allocated_cost: '' 
  });

  // User & Role Management State
  const [usersList, setUsersList] = useState([]);
  const [showUserModal, setShowUserModal] = useState(false);
  const [editingUser, setEditingUser] = useState(null);

  const [rolesList, setRolesList] = useState([]);
  const [showRoleModal, setShowRoleModal] = useState(false);
  const [editingRole, setEditingRole] = useState(null);

  // Reference Management State
  const [refLocations, setRefLocations] = useState([]);
  const [refUOMs, setRefUOMs] = useState([]);
  const [refChannels, setRefChannels] = useState([]); 
  const [selectedChannel, setSelectedChannel] = useState(''); 
  const [newRefValue, setNewRefValue] = useState('');

  // Log Modal States
  const [showLogModal, setShowLogModal] = useState(false);
  const [logsData, setLogsData] = useState([]);
  const [currentLogGateName, setCurrentLogGateName] = useState('');

  const [showItemLogModal, setShowItemLogModal] = useState(false);
  const [itemLogsData, setItemLogsData] = useState([]);
  const [currentLogItemName, setCurrentLogItemName] = useState('');

  const [showRateCartLogModal, setShowRateCartLogModal] = useState(false);
  const [rateCartLogsData, setRateCartLogsData] = useState([]);
  const [currentLogRateCartLocation, setCurrentLogRateCartLocation] = useState('');

  // --- Formatting & UI Helpers ---
  const formatNumber = (num) => {
    if (num === null || num === undefined || num === '') return '-';
    if (isNaN(num)) return num;
    return Number(num).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  };

  const getNotificationColor = (type) => {
    switch (type) {
      case 'success': return 'bg-green-500';
      case 'error': return 'bg-red-500';
      case 'info': return 'bg-blue-500';
      case 'warning': return 'bg-yellow-500';
      default: return 'bg-gray-800';
    }
  };

  const showNotification = (message, type = 'success') => {
    setNotification({ message, type });
    setTimeout(() => setNotification(null), 5000); 
  };

  const getErrorMessage = (error) => {
    if (!error?.detail) return 'An unknown error occurred';
    if (Array.isArray(error.detail)) return error.detail.map(e => `${e.loc ? e.loc.slice(-1) + ': ' : ''}${e.msg}`).join('\n');
    if (typeof error.detail === 'object') return JSON.stringify(error.detail);
    return String(error.detail);
  };

  // --- Auth Helpers ---
  const handleLogin = (data) => {
    setToken(data.access_token);
    setUserRole(data.role);
    setUsername(data.username);
    setPermissions(data.permissions || []);
    localStorage.setItem('token', data.access_token);
    localStorage.setItem('userRole', data.role);
    localStorage.setItem('username', data.username);
    localStorage.setItem('permissions', JSON.stringify(data.permissions || []));
  };

  const handleLogout = () => {
    setToken(null);
    setUserRole(null);
    setUsername('');
    setPermissions([]);
    localStorage.removeItem('token');
    localStorage.removeItem('userRole');
    localStorage.removeItem('username');
    localStorage.removeItem('permissions');
    setCurrentPage('calculator');
  };

  const authFetch = async (url, options = {}) => {
    const headers = options.headers || {};
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const response = await fetch(url, { ...options, headers });
    if (response.status === 401) {
        handleLogout();
        throw new Error("Session expired. Please login again.");
    }
    return response;
  };

  // --- Data Loading Functions ---
  const loadDocNums = async () => {
    try {
      const response = await authFetch(`${API_URL}/doc-nums`);
      if (response.ok) { const data = await response.json(); setDocNums(data.doc_nums); }
    } catch (error) { showNotification(`Error loading Doc Nums: ${error.message}`, 'error'); }
  };

  const loadGates = async () => {
    try {
      const response = await authFetch(`${API_URL}/account/gates`);
      if (response.ok) { const data = await response.json(); setGates(data.gates); setGateData(data.gates); }
    } catch (error) { showNotification(`Error loading gates: ${error.message}`, 'error'); }
  };

  const loadFromLocations = async () => {
    try {
      const response = await authFetch(`${API_URL}/locations/from`);
      if (response.ok) { const data = await response.json(); setFromLocations(data.locations); }
    } catch (error) { showNotification(`Error loading locations: ${error.message}`, 'error'); }
  };

  const loadToLocations = async (fromLoc) => {
    try {
      let url = `${API_URL}/locations/to`;
      if (fromLoc) url += `?from_loc=${encodeURIComponent(fromLoc)}`;
      const response = await authFetch(url);
      if (response.ok) { const data = await response.json(); setToLocations(data.locations); }
    } catch (error) { showNotification(`Error loading destinations: ${error.message}`, 'error'); }
  };

  const loadItemPricing = async (gateId) => {
    if (!gateId) return;
    try {
      setItemFilters({ item_code: '', item_name: '', principal: '', brand: '', transportation_cost: '' });
      const response = await authFetch(`${API_URL}/account/item-pricing/${gateId}`);
      if (response.ok) { const data = await response.json(); setItemPricingData(data.items); }
    } catch (error) { showNotification(`Error loading items: ${error.message}`, 'error'); }
  };

  const loadHistory = async () => {
    try {
      const response = await authFetch(`${API_URL}/history`);
      if (response.ok) { const data = await response.json(); setHistoryData(data.history); }
    } catch (error) { showNotification(`Error loading history: ${error.message}`, 'error'); }
  };

  const loadUsers = async () => {
    try {
        const response = await authFetch(`${API_URL}/users`);
        if (response.ok) { const data = await response.json(); setUsersList(data); }
    } catch (error) { showNotification(`Error loading users: ${error.message}`, 'error'); }
  };

  const loadRoles = async () => {
    try {
        const response = await authFetch(`${API_URL}/roles`);
        if (response.ok) { const data = await response.json(); setRolesList(data); }
    } catch (error) { showNotification(`Error loading roles: ${error.message}`, 'error'); }
  };

  const loadReferenceData = async () => {
      try {
          const locResp = await authFetch(`${API_URL}/references/locations`);
          if (locResp.ok) setRefLocations(await locResp.json());
          const uomResp = await authFetch(`${API_URL}/references/uoms`);
          if (uomResp.ok) setRefUOMs(await uomResp.json());
          const chanResp = await authFetch(`${API_URL}/references/channels`);
          if (chanResp.ok) setRefChannels(await chanResp.json());
      } catch (error) { showNotification('Error loading reference data', 'error'); }
  }

  const loadRateCarts = async () => {
      try {
          const response = await authFetch(`${API_URL}/account/rate-cuts`);
          if (response.ok) { const data = await response.json(); setRateCarts(data); }
      } catch (error) { showNotification(`Error loading rate carts: ${error.message}`, 'error'); }
  };

  const fetchDailyReport = async (targetDate) => {
      setIsDailyReportLoading(true);
      try {
          let url = `${API_URL}/account/daily-rate-cut-report`;
          if (targetDate) url += `?target_date=${encodeURIComponent(targetDate)}`;
          const response = await authFetch(url);
          if (response.ok) {
              const data = await response.json();
              setDailyReportData(data.report || []);
              setDailyTownshipReportData(data.township_report || []);
              setDailyReportDate(data.target_date);
              showNotification(`Report loaded for ${data.target_date}`, 'success');
          } else {
              const error = await response.json();
              showNotification(getErrorMessage(error), 'error');
          }
      } catch (error) { showNotification(`Error fetching report: ${error.message}`, 'error'); } 
      finally { setIsDailyReportLoading(false); }
  };

  // --- API Actions ---
  const addReference = async (type, value) => {
      if(!value.trim()) return;
      try {
          const response = await authFetch(`${API_URL}/references/${type}`, {
              method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name: value })
          });
          if(response.ok) { showNotification('Added successfully', 'success'); setNewRefValue(''); loadReferenceData(); } 
          else { const err = await response.json(); showNotification(getErrorMessage(err), 'error'); }
      } catch (error) { showNotification(`Error: ${error.message}`, 'error'); }
  }

  const deleteReference = async (type, value) => {
      if(!window.confirm(`Delete ${value}?`)) return;
      try {
          const response = await authFetch(`${API_URL}/references/${type}/${value}`, { method: 'DELETE' });
          if(response.ok) loadReferenceData();
      } catch (error) { showNotification(`Error: ${error.message}`, 'error'); }
  }

  const handleSaveCalculation = async (isUpdate = false) => {
    if (!selectedChannel) { showNotification('Channel is required to save.', 'error'); return; }
    try {
      const payload = {
        id: isUpdate ? currentHistoryId : null, gate_name: selectedGate, from_loc: selectedFrom, to_loc: selectedTo,
        doc_nums: selectedDocNums.map(String), manual_total_cost: (manualTotalCost && isManualTotalCostEnabled) ? parseFloat(manualTotalCost) : null,
        additional_charges: additionalCharges ? parseFloat(additionalCharges) : 0, final_total_cost: calculatedTotalCost, channel: selectedChannel, status: "saved",
        calculated_products: calculatedProducts
      };
      const response = await authFetch(`${API_URL}/history/save`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
      if (response.ok) { showNotification('Calculation saved successfully', 'success'); loadHistory(); } 
      else { const error = await response.json(); showNotification(getErrorMessage(error), 'error'); }
    } catch (error) { showNotification(`Error: ${error.message}`, 'error'); }
  };

  const handleSubmitHistory = async (id) => {
    if(!window.confirm("Submit calculation? Account users will review it.")) return;
    try {
      const response = await authFetch(`${API_URL}/history/${id}/submit`, { method: 'PUT' });
      if (response.ok) { showNotification('Calculation submitted', 'success'); loadHistory(); } 
      else { const err = await response.json(); showNotification(getErrorMessage(err), 'error'); }
    } catch (error) { showNotification(`Error: ${error.message}`, 'error'); }
  };

  const handleClaimHistory = async (id) => {
    if(!window.confirm("Claim this calculation?")) return;
    try {
      const response = await authFetch(`${API_URL}/history/${id}/claim`, { method: 'PUT' });
      if (response.ok) { showNotification('Calculation claimed', 'success'); loadHistory(); } 
      else { const err = await response.json(); showNotification(getErrorMessage(err), 'error'); }
    } catch (error) { showNotification(`Error: ${error.message}`, 'error'); }
  };

  const deleteHistory = async (id) => {
    if(!window.confirm("Delete this saved calculation?")) return;
    try {
      const response = await authFetch(`${API_URL}/history/${id}`, { method: 'DELETE' });
      if (response.ok) { showNotification('Record deleted', 'success'); loadHistory(); } 
      else { showNotification('Error deleting record', 'error'); }
    } catch (error) { showNotification(`Error: ${error.message}`, 'error'); }
  };

  const saveGate = async (gateData) => {
    if (!gateData.gate_name?.trim() || !gateData.from_loc || !gateData.to_loc) { showNotification('Required fields missing.', 'error'); return; }
    try {
      const payload = { 
        ...gateData, 
        gate_id: editingGate ? editingGate.gate_id : null,
        unit: gateData.unit === '' ? null : parseInt(gateData.unit), 
        cost: gateData.cost === '' ? null : parseFloat(gateData.cost)
      };
      
      const response = await authFetch(`${API_URL}/account/gates`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
      if (response.ok) { showNotification('Gate saved', 'success'); loadGates(); loadFromLocations(); setShowAddGateModal(false); setEditingGate(null); } 
      else { const error = await response.json(); showNotification(getErrorMessage(error), 'error'); }
    } catch (error) { showNotification(`Error: ${error.message}`, 'error'); }
  };

  const deleteGate = async (gateId) => {
    setConfirmDialog({
      message: `Delete this gate and all associated item pricing?`,
      onConfirm: async () => {
        try {
          const response = await authFetch(`${API_URL}/account/gates/${gateId}`, { method: 'DELETE' });
          if (response.ok) { showNotification('Gate deleted', 'success'); loadGates(); loadFromLocations(); } 
          else { const error = await response.json(); showNotification(getErrorMessage(error), 'error'); }
        } catch (error) { showNotification(`Error: ${error.message}`, 'error'); }
        setConfirmDialog(null);
      },
      onCancel: () => setConfirmDialog(null)
    });
  };

  const saveItem = async (itemData) => {
    try {
      const payload = { ...itemData, gate_id: selectedGateForPricing, original_item_code: originalItemCode || itemData.item_code };
      const response = await authFetch(`${API_URL}/account/item-pricing`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
      if (response.ok) { showNotification('Item saved', 'success'); loadItemPricing(selectedGateForPricing); setShowAddItemModal(false); setEditingItem(null); setOriginalItemCode(null); } 
      else { const error = await response.json(); showNotification(getErrorMessage(error), 'error'); }
    } catch (error) { showNotification(`Error: ${error.message}`, 'error'); }
  };

  const deleteItem = async (itemCode) => {
    setConfirmDialog({
      message: `Delete item "${itemCode}"?`,
      onConfirm: async () => {
        try {
          const response = await authFetch(`${API_URL}/account/item-pricing/${selectedGateForPricing}/${encodeURIComponent(itemCode)}`, { method: 'DELETE' });
          if (response.ok) { showNotification('Item deleted', 'success'); loadItemPricing(selectedGateForPricing); } 
          else { const error = await response.json(); showNotification(getErrorMessage(error), 'error'); }
        } catch (error) { showNotification(`Error: ${error.message}`, 'error'); }
        setConfirmDialog(null);
      },
      onCancel: () => setConfirmDialog(null)
    });
  };

  const saveUser = async (userData) => {
    try {
        let url = `${API_URL}/users`;
        let method = 'POST';
        if (editingUser) { url += `/${editingUser.username}`; method = 'PUT'; }
        const response = await authFetch(url, { method: method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(userData) });
        if (response.ok) { showNotification(editingUser ? 'User updated' : 'User created', 'success'); loadUsers(); setShowUserModal(false); setEditingUser(null); } 
        else { const error = await response.json(); showNotification(getErrorMessage(error), 'error'); }
    } catch (error) { showNotification(`Error: ${error.message}`, 'error'); }
  };

  const deleteUser = async (userToDelete) => {
    if (userToDelete === username) return; 
    setConfirmDialog({
        message: `Delete user "${userToDelete}"?`,
        onConfirm: async () => {
            try {
                const response = await authFetch(`${API_URL}/users/${userToDelete}`, { method: 'DELETE' });
                if (response.ok) { showNotification('User deleted', 'success'); loadUsers(); } 
                else { const error = await response.json(); showNotification(getErrorMessage(error), 'error'); }
            } catch (error) { showNotification(`Error: ${error.message}`, 'error'); }
            setConfirmDialog(null);
        },
        onCancel: () => setConfirmDialog(null)
    });
  };

  const saveRole = async (roleData) => {
    try {
      const isNew = !rolesList.find(r => r.name === roleData.name);
      const response = await authFetch(`${API_URL}/roles${isNew ? '' : `/${roleData.name}`}`, {
        method: isNew ? 'POST' : 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(roleData)
      });
      if (response.ok) { showNotification(isNew ? 'Role created' : 'Role updated', 'success'); loadRoles(); setShowRoleModal(false); } 
      else { const err = await response.json(); showNotification(getErrorMessage(err), 'error'); }
    } catch (error) { showNotification(`Error: ${error.message}`, 'error'); }
  };

  const deleteRole = async (roleName) => {
    if(!window.confirm(`Delete role ${roleName}?`)) return;
    try {
      const response = await authFetch(`${API_URL}/roles/${roleName}`, { method: 'DELETE' });
      if (response.ok) { showNotification('Role deleted', 'success'); loadRoles(); } 
      else { const err = await response.json(); showNotification(getErrorMessage(err), 'error'); }
    } catch (error) { showNotification(`Error: ${error.message}`, 'error'); }
  };

  const saveRateCart = async (data) => {
    if (!data.location || data.cost === '') { showNotification('Both fields are required', 'error'); return; }
    try {
        const response = await authFetch(`${API_URL}/account/rate-cuts`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' }, 
            body: JSON.stringify({ location: data.location, cost: parseFloat(data.cost) })
        });
        if (response.ok) { showNotification('Rate cart saved', 'success'); loadRateCarts(); setShowRateCartModal(false); }
        else { const err = await response.json(); showNotification(getErrorMessage(err), 'error'); }
    } catch (error) { showNotification(`Error: ${error.message}`, 'error'); }
  };

  const deleteRateCart = async (location) => {
      if (!window.confirm(`Delete rate cart for ${location}?`)) return;
      try {
          const response = await authFetch(`${API_URL}/account/rate-cuts/${encodeURIComponent(location)}`, { method: 'DELETE' });
          if (response.ok) { showNotification('Deleted successfully', 'success'); loadRateCarts(); }
          else { const err = await response.json(); showNotification(getErrorMessage(err), 'error'); }
      } catch (error) { showNotification(`Error: ${error.message}`, 'error'); }
  };

  // --- Effects ---
  useEffect(() => {
    if (token) { loadDocNums(); loadGates(); loadFromLocations(); loadReferenceData(); }
  }, [token]);

  useEffect(() => {
    if (token && selectedGateForPricing) loadItemPricing(selectedGateForPricing);
    else setItemPricingData([]);
  }, [selectedGateForPricing, token]);

  useEffect(() => {
    if (token && currentPage === 'history') loadHistory();
    if (token && currentPage === 'users' && permissions.includes('view_users')) { loadUsers(); loadRoles(); }
    if (token && currentPage === 'roles' && permissions.includes('view_roles')) loadRoles();
    if (token && currentPage === 'references' && permissions.includes('view_references')) loadReferenceData();
    if (token && currentPage === 'rate_carts' && permissions.includes('view_rate_carts')) { loadRateCarts(); loadReferenceData(); }
    if (token && currentPage === 'daily_report' && permissions.includes('view_daily_report')) { fetchDailyReport(dailyReportDate); }
  }, [currentPage, token, permissions]);

  useEffect(() => {
    const checkManualCostStatus = async () => {
      if (currentPage !== 'calculator' || !token) return;
      if (calculationType !== 'gate_pricing' || !selectedGate) { setIsManualTotalCostEnabled(false); return; }
      const gateInfo = gates.find(g => g.gate_name === selectedGate);
      if (!gateInfo) { setIsManualTotalCostEnabled(false); return; }

      try {
        const response = await authFetch(`${API_URL}/account/item-pricing/${gateInfo.gate_id}`);
        if (response.ok) {
          const data = await response.json();
          const hasDirectPricingItem = products.some(p => {
            const pricing = data.items.find(item => item.item_code === p.code);
            if (!pricing) return false;
            const tc = String(pricing.transportation_cost || '').trim().toLowerCase();
            return tc !== '' && tc !== 'nan' && tc !== 'none' && tc !== 'null';
          });
          setIsManualTotalCostEnabled(hasDirectPricingItem);
        } else setIsManualTotalCostEnabled(false);
      } catch (err) { setIsManualTotalCostEnabled(false); }
    };
    checkManualCostStatus();
  }, [selectedGate, calculationType, products, gates, token, currentPage]);

  // --- Utility Fetch/Calculations Functions ---
  
  const calculateCosts = async () => {
    if (selectedDocNums.length === 0 || !selectedFrom || !selectedTo || !selectedGate || !selectedChannel) { showNotification('Please select Doc Num(s), From, To, Gate, and Channel', 'error'); return; }
    setIsLoading(true);
    try {
      let url = `${API_URL}/calculate-with-gate?gate_name=${encodeURIComponent(selectedGate)}&from_loc=${encodeURIComponent(selectedFrom)}&to_loc=${encodeURIComponent(selectedTo)}`;
      selectedDocNums.forEach(id => url += `&doc_nums=${encodeURIComponent(id)}`);
      if (manualTotalCost && isManualTotalCostEnabled) url += `&manual_total_cost=${manualTotalCost}`;
      if (additionalCharges) url += `&additional_charges=${additionalCharges}`;
      
      const response = await authFetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' } });
      if (response.ok) {
        const data = await response.json();
        setCalculatedProducts(data.calculated_products); setCalculatedTotalCost(data.total_cost); setEstimatedTotalCost(data.estimated_total_cost);
        showNotification('Calculation completed successfully', 'success');
      } else { const error = await response.json(); showNotification(getErrorMessage(error), 'error'); }
    } catch (error) { showNotification(`Error: ${error.message}`, 'error'); } 
    finally { setIsLoading(false); }
  };

  const fetchAggregatedProducts = async (ids) => {
    if (ids.length === 0) { setProducts([]); setTotalWeight(0); return; }
    try {
      const queryString = ids.map(id => `doc_nums=${encodeURIComponent(id)}`).join('&');
      const response = await authFetch(`${API_URL}/products-by-doc-nums?${queryString}`);
      if (response.ok) {
        const data = await response.json();
        setProducts(data.products); setTotalWeight(data.total_weight || 0);
      } else showNotification('Failed to load products', 'error');
    } catch (error) { showNotification(`Error: ${error.message}`, 'error'); }
  };

  // --- Event Handlers ---
  const handleAddDocNum = (docNum) => {
    if (!docNum) return;
    if (selectedDocNums.includes(docNum)) { showNotification('Doc Num already selected', 'info'); return; }
    const newSelection = [...selectedDocNums, docNum];
    setSelectedDocNums(newSelection); setSelectedFrom(''); setSelectedTo(''); setSelectedGate(''); setSelectedChannel(''); setCalculationType(''); setCalculatedProducts([]); setCalculatedTotalCost(null); setEstimatedTotalCost(null); setManualTotalCost(''); setAdditionalCharges('');
    fetchAggregatedProducts(newSelection);
  };
  const handleRemoveDocNum = (docNum) => {
    const newSelection = selectedDocNums.filter(id => id !== docNum);
    setSelectedDocNums(newSelection); setCalculatedProducts([]); setCalculatedTotalCost(null); setEstimatedTotalCost(null);
    fetchAggregatedProducts(newSelection);
  };
  const handleFromChange = (val) => {
    setSelectedFrom(val); setSelectedTo(''); setSelectedGate(''); setSelectedChannel(''); setCalculatedProducts([]); setCalculatedTotalCost(null); setEstimatedTotalCost(null); setManualTotalCost('');
    if (val) loadToLocations(val); else setToLocations([]);
  };
  const handleToChange = (val) => { setSelectedTo(val); setSelectedGate(''); setSelectedChannel(''); setCalculatedProducts([]); setCalculatedTotalCost(null); setEstimatedTotalCost(null); setManualTotalCost(''); };
  const handleGateChange = (gateName) => {
    setSelectedGate(gateName); setSelectedChannel(''); setCalculatedProducts([]); setCalculatedTotalCost(null); setEstimatedTotalCost(null); setManualTotalCost('');
    // Safely attempt to match the first found for calculation type label
    const gateInfo = gates.find(g => g.gate_name === gateName && g.from_loc === selectedFrom && g.to_loc === selectedTo);
    if (gateInfo) setCalculationType(gateInfo.calculation_type);
  };

  // UPDATED: Attempt to load from PG (Live DWBI) first. If it fails, fallback to SQLite.
  const loadSavedCalculation = async (record) => {
    try {
      setCurrentPage('calculator');
      setIsLoading(true);
      setCurrentHistoryId(record.id);

      // Fetch the full detailed record from the local backend endpoint
      const response = await authFetch(`${API_URL}/history/${record.id}`);
      if (response.ok) {
        const fullRecord = await response.json();
        
        setSelectedDocNums(fullRecord.doc_nums); 
        setSelectedFrom(fullRecord.from_loc); 
        await loadToLocations(fullRecord.from_loc); 
        setSelectedTo(fullRecord.to_loc);
        setSelectedGate(fullRecord.gate_name); 
        setSelectedChannel(fullRecord.channel || ''); 
        setManualTotalCost(fullRecord.manual_total_cost || ''); 
        setAdditionalCharges(fullRecord.additional_charges || '');
        
        let loadedFromPG = false;
        
        try {
            // STEP 1: ATTEMPT TO FETCH FRESH DATA FROM PG_TRANSFER_DETAILS
            const queryString = fullRecord.doc_nums.map(id => `doc_nums=${encodeURIComponent(id)}`).join('&');
            const pgResponse = await authFetch(`${API_URL}/products-by-doc-nums?${queryString}`);
            
            if (pgResponse.ok) {
                const pgData = await pgResponse.json();
                
                if (pgData.products && pgData.products.length > 0) {
                    // Data is still available in PG_Transfer_Details!
                    setProducts(pgData.products);
                    setTotalWeight(pgData.total_weight || 0);
                    
                    // Recalculate using PG live data to get all pricing logic
                    let url = `${API_URL}/calculate-with-gate?gate_name=${encodeURIComponent(fullRecord.gate_name)}&from_loc=${encodeURIComponent(fullRecord.from_loc)}&to_loc=${encodeURIComponent(fullRecord.to_loc)}`;
                    fullRecord.doc_nums.forEach(id => url += `&doc_nums=${encodeURIComponent(id)}`);
                    if (fullRecord.manual_total_cost !== null && fullRecord.manual_total_cost !== undefined) {
                        url += `&manual_total_cost=${fullRecord.manual_total_cost}`;
                    }
                    if (fullRecord.additional_charges) url += `&additional_charges=${fullRecord.additional_charges}`;
                    
                    const calcResponse = await authFetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' } });
                    
                    if (calcResponse.ok) {
                        const calcData = await calcResponse.json();
                        setCalculatedProducts(calcData.calculated_products);
                        setCalculatedTotalCost(calcData.total_cost);
                        setEstimatedTotalCost(calcData.estimated_total_cost);
                        loadedFromPG = true;
                        showNotification(`Loaded and verified with live PG_Transfer_Details (ID: ${fullRecord.id}).`, 'success');
                    }
                }
            }
        } catch (e) {
            console.log("DWBI check failed, falling back to local DB...", e);
        }

        if (!loadedFromPG) {
            // STEP 2: FALLBACK TO LOCAL SQLITE SNAPSHOT (if PG data was deleted)
            if (fullRecord.calculated_products && fullRecord.calculated_products.length > 0) {
                setCalculatedProducts(fullRecord.calculated_products);
                setProducts(fullRecord.calculated_products); // To display the grid and details properly
                const calculatedWeight = fullRecord.calculated_products.reduce((acc, curr) => acc + (curr.weight || 0), 0);
                setTotalWeight(calculatedWeight);
                setCalculatedTotalCost(fullRecord.final_total_cost);
                showNotification(`Data cleared from external DB. Loaded saved snapshot from local DB (ID: ${fullRecord.id}).`, 'info');
            } else {
                showNotification('Data purged from PG and no local saved products found. Cannot load calculation details.', 'error');
            }
        }
      } else {
         showNotification('Failed to fetch full record details', 'error');
      }
      setIsLoading(false);
    } catch (error) { 
      setIsLoading(false);
      showNotification(`Error loading record: ${error.message}`, 'error'); 
    }
  };

  const handleDownloadHistoryExcel = async (record) => {
    try {
      showNotification('Generating Excel file...', 'info');
      const response = await authFetch(`${API_URL}/history/${record.id}/download`);
      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a'); a.href = url; a.download = `Calculation_${record.id}.xlsx`;
        document.body.appendChild(a); a.click(); window.URL.revokeObjectURL(url); document.body.removeChild(a);
        showNotification('History Excel file downloaded', 'success');
      } else { const error = await response.json(); showNotification(getErrorMessage(error), 'error'); }
    } catch (error) { showNotification(`Error downloading file: ${error.message}`, 'error'); }
  };

  const handleExportExcel = async () => {
    if (!selectedGateForPricing) { showNotification('Please select a gate first', 'error'); return; }
    try {
      const response = await authFetch(`${API_URL}/account/item-pricing/export/${selectedGateForPricing}`);
      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a'); a.href = url; a.download = 'item_costing.xlsx';
        document.body.appendChild(a); a.click(); window.URL.revokeObjectURL(url); document.body.removeChild(a);
        showNotification('Excel file downloaded successfully', 'success');
      } else { const error = await response.json(); showNotification(getErrorMessage(error), 'error'); }
    } catch (error) { showNotification(`Error: ${error.message}`, 'error'); }
  };

  const handleImportExcel = async (event) => {
    const file = event.target.files[0];
    if (!file) return;
    if (!selectedGateForPricing) { showNotification('Please select a gate first', 'error'); event.target.value = ''; return; }
    try {
      const formData = new FormData(); formData.append('file', file);
      const response = await authFetch(`${API_URL}/account/item-pricing/import/${selectedGateForPricing}`, { method: 'POST', body: formData });
      if (response.ok) {
        const result = await response.json();
        showNotification(`Import successful! Updated: ${result.updates}, Added: ${result.inserts}, Deleted: ${result.deletes}`, 'success');
        await loadItemPricing(selectedGateForPricing);
      } else {
        const error = await response.json();
        if(Array.isArray(error.detail)) alert(`Import Errors:\n${error.detail.join('\n')}`); 
        else showNotification(getErrorMessage(error), 'error');
      }
    } catch (error) { showNotification(`Error: ${error.message}`, 'error'); } 
    finally { event.target.value = ''; }
  };

  const fetchGateLogs = async (gate) => {
      try {
          const response = await authFetch(`${API_URL}/account/gates/${gate.gate_id}/logs`);
          if(response.ok) { setLogsData(await response.json()); setCurrentLogGateName(gate.gate_name); setShowLogModal(true); } 
          else showNotification('Failed to fetch logs', 'error');
      } catch (error) { showNotification(`Error: ${error.message}`, 'error'); }
  };

  const fetchItemLogs = async (item) => {
    try {
        const response = await authFetch(`${API_URL}/account/items/${item.pricing_id}/logs`);
        if (response.ok) { setItemLogsData(await response.json()); setCurrentLogItemName(item.item_name); setShowItemLogModal(true); } 
        else showNotification('Failed to fetch logs', 'error');
    } catch (error) { showNotification(`Error: ${error.message}`, 'error'); }
  };

  const fetchRateCartLogs = async (rc) => {
      try {
          const response = await authFetch(`${API_URL}/account/rate-cuts/${encodeURIComponent(rc.location)}/logs`);
          if (response.ok) { 
              setRateCartLogsData(await response.json()); 
              setCurrentLogRateCartLocation(rc.location); 
              setShowRateCartLogModal(true); 
          } 
          else showNotification('Failed to fetch rate cart logs', 'error');
      } catch (error) { showNotification(`Error: ${error.message}`, 'error'); }
  };

  // --- Sub-Components ---
  const GateModal = ({ gate, onSave, onClose }) => {
    const [formData, setFormData] = useState(gate || { gate_name: '', from_loc: '', to_loc: '', uom: '', unit: '', cost: '' });
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg p-6 w-full max-w-md">
          <h2 className="text-2xl font-bold mb-4">{gate ? 'Edit Gate' : 'Add New Gate'}</h2>
          <div className="space-y-4">
            <div><label className="block text-sm font-semibold mb-1">Gate Name <span className="text-red-500">*</span></label><input type="text" value={formData.gate_name ?? ''} onChange={(e) => setFormData({...formData, gate_name: e.target.value})} className="w-full p-2 border rounded" /></div>
            <div><label className="block text-sm font-semibold mb-1">From <span className="text-red-500">*</span></label><select value={formData.from_loc ?? ''} onChange={(e) => setFormData({...formData, from_loc: e.target.value})} className="w-full p-2 border rounded"><option value="">-- Select --</option>{refLocations.map((loc, i) => (<option key={i} value={loc}>{loc}</option>))}</select></div>
            <div><label className="block text-sm font-semibold mb-1">To <span className="text-red-500">*</span></label><select value={formData.to_loc ?? ''} onChange={(e) => setFormData({...formData, to_loc: e.target.value})} className="w-full p-2 border rounded"><option value="">-- Select --</option>{refLocations.map((loc, i) => (<option key={i} value={loc}>{loc}</option>))}</select></div>
            <div className="grid grid-cols-2 gap-4">
                <div><label className="block text-sm font-semibold mb-1">UOM</label><select value={formData.uom ?? ''} onChange={(e) => setFormData({...formData, uom: e.target.value})} className="w-full p-2 border rounded"><option value="">-- Select --</option>{refUOMs.map((u, i) => (<option key={i} value={u}>{u}</option>))}</select></div>
                <div><label className="block text-sm font-semibold mb-1">Unit</label><input type="number" value={formData.unit ?? ''} onChange={(e) => setFormData({...formData, unit: e.target.value})} className="w-full p-2 border rounded" placeholder="1" /></div>
            </div>
            <div><label className="block text-sm font-semibold mb-1">Cost</label><input type="number" value={formData.cost ?? ''} onChange={(e) => setFormData({...formData, cost: e.target.value})} className="w-full p-2 border rounded" /></div>
          </div>
          <div className="flex gap-2 mt-6">
            <button onClick={() => onSave(formData)} className="flex-1 bg-blue-600 text-white py-2 rounded hover:bg-blue-700">Save</button>
            <button onClick={onClose} className="flex-1 bg-gray-300 text-gray-700 py-2 rounded hover:bg-gray-400">Cancel</button>
          </div>
        </div>
      </div>
    );
  };

  const ItemModal = ({ item, onSave, onClose }) => {
    const [formData, setFormData] = useState(item || { item_code: '', item_name: '', principal: '', brand: '', transportation_cost: '' });
    const [searchResults, setSearchResults] = useState([]);
    const [isSearching, setIsSearching] = useState(false);
    const [isValidating, setIsValidating] = useState(false);
    const [searchTerm, setSearchTerm] = useState(item ? item.item_code : '');

    const handleSearch = async (query) => {
        setSearchTerm(query);
        if (query.length < 2) { setSearchResults([]); return; }
        setIsSearching(true);
        try {
            const response = await authFetch(`${API_URL}/dwbi/items/search?q=${encodeURIComponent(query)}`);
            if (response.ok) setSearchResults((await response.json()).items);
        } catch (error) {} finally { setIsSearching(false); }
    };

    const selectItem = (selectedItem) => {
        setFormData({ ...formData, item_code: selectedItem.item_code, item_name: selectedItem.item_name, principal: selectedItem.principal || '', brand: selectedItem.brand || '' });
        setSearchTerm(selectedItem.item_code); setSearchResults([]); 
    };

    const handleSaveButton = async () => {
        if (!searchTerm) { showNotification("Item Code required", "error"); return; }
        setIsValidating(true);
        try {
            const response = await authFetch(`${API_URL}/dwbi/items/validate?code=${encodeURIComponent(searchTerm)}`);
            if (response.ok) {
                const result = await response.json();
                if (result.valid) onSave({ ...formData, item_code: result.item.item_code, item_name: result.item.item_name, principal: result.item.principal, brand: result.item.brand });
                else showNotification("Invalid Item Code.", "error");
            } else showNotification("Validation check failed.", "error");
        } catch (error) { showNotification("Network error", "error"); } finally { setIsValidating(false); }
    };

    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg p-6 w-full max-w-2xl max-h-screen overflow-y-auto">
          <h2 className="text-2xl font-bold mb-4">{item ? 'Edit Item' : 'Add New Item'}</h2>
          <div className="grid grid-cols-2 gap-4">
            <div className="relative">
              <label className="block text-sm font-semibold mb-1">Item Code (Search) <span className="text-red-500">*</span></label>
              <div className="relative"><input type="text" value={searchTerm} onChange={(e) => handleSearch(e.target.value)} className="w-full p-2 border rounded pr-8" placeholder="Type code or name..." /><div className="absolute right-2 top-2 text-gray-400"><Search size={18} /></div></div>
              {searchResults.length > 0 && (<div className="absolute z-10 w-full bg-white border rounded shadow-lg max-h-48 overflow-y-auto mt-1">{searchResults.map((res, idx) => (<div key={idx} onClick={() => selectItem(res)} className="p-2 hover:bg-blue-50 cursor-pointer border-b last:border-0 text-sm"><div className="font-bold text-gray-800">{res.item_code}</div><div className="text-gray-600 truncate">{res.item_name}</div></div>))}</div>)}
            </div>
            <div><label className="block text-sm font-semibold mb-1">Item Name</label><input type="text" value={formData.item_name ?? ''} readOnly className="w-full p-2 border rounded bg-gray-50" /></div>
            <div><label className="block text-sm font-semibold mb-1">Principal</label><input type="text" value={formData.principal ?? ''} readOnly className="w-full p-2 border rounded bg-gray-50" /></div>
            <div><label className="block text-sm font-semibold mb-1">Brand</label><input type="text" value={formData.brand ?? ''} readOnly className="w-full p-2 border rounded bg-gray-50" /></div>
            <div><label className="block text-sm font-semibold mb-1">Transportation Cost</label><input type="number" step="any" value={formData.transportation_cost ?? ''} onChange={(e) => setFormData({...formData, transportation_cost: e.target.value})} className="w-full p-2 border rounded" /></div>
          </div>
          <div className="flex gap-2 mt-6">
            <button onClick={handleSaveButton} disabled={isValidating} className="flex-1 bg-blue-600 text-white py-2 rounded hover:bg-blue-700 disabled:bg-blue-400">{isValidating ? "Validating..." : "Save"}</button>
            <button onClick={onClose} disabled={isValidating} className="flex-1 bg-gray-300 text-gray-700 py-2 rounded hover:bg-gray-400">Cancel</button>
          </div>
        </div>
      </div>
    );
  };

  const UserModal = ({ user, onSave, onClose }) => {
    const [formData, setFormData] = useState(user ? { ...user, password: '' } : { username: '', password: '', role: rolesList.length > 0 ? rolesList[0].name : '' });
    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg p-6 w-full max-w-md">
                <h2 className="text-2xl font-bold mb-4">{user ? 'Edit User' : 'Add New User'}</h2>
                <div className="space-y-4">
                    <div><label className="block text-sm font-semibold mb-1">Username <span className="text-red-500">*</span></label><input type="text" value={formData.username} onChange={(e) => setFormData({...formData, username: e.target.value})} className="w-full p-2 border rounded" disabled={!!user} /></div>
                    <div><label className="block text-sm font-semibold mb-1">Password {!user && <span className="text-red-500">*</span>}</label><input type="password" value={formData.password} onChange={(e) => setFormData({...formData, password: e.target.value})} className="w-full p-2 border rounded" placeholder={user ? "Leave blank to keep" : "Required"} /></div>
                    <div>
                        <label className="block text-sm font-semibold mb-1">Role <span className="text-red-500">*</span></label>
                        <select value={formData.role} onChange={(e) => setFormData({...formData, role: e.target.value})} className="w-full p-2 border rounded">
                            {rolesList.map(r => <option key={r.name} value={r.name}>{r.name}</option>)}
                        </select>
                    </div>
                </div>
                <div className="flex gap-2 mt-6">
                    <button onClick={() => onSave(formData)} className="flex-1 bg-blue-600 text-white py-2 rounded hover:bg-blue-700" disabled={!user && !formData.password}>Save</button>
                    <button onClick={onClose} className="flex-1 bg-gray-300 text-gray-700 py-2 rounded hover:bg-gray-400">Cancel</button>
                </div>
            </div>
        </div>
    );
  };

  const RoleModal = ({ role, onSave, onClose }) => {
    const [formData, setFormData] = useState(role || { name: '', permissions: [] });

    const handleToggle = (permId) => {
      const perms = formData.permissions;
      if (perms.includes(permId)) { setFormData({ ...formData, permissions: perms.filter(p => p !== permId) }); } 
      else { setFormData({ ...formData, permissions: [...perms, permId] }); }
    };

    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg p-6 w-full max-w-lg">
          <h2 className="text-2xl font-bold mb-4">{role ? 'Edit Role' : 'Add New Role'}</h2>
          <div className="space-y-4">
            <div><label className="block text-sm font-semibold mb-1">Role Name <span className="text-red-500">*</span></label><input type="text" value={formData.name} onChange={(e) => setFormData({...formData, name: e.target.value})} className="w-full p-2 border rounded" disabled={!!role} /></div>
            <div>
              <label className="block text-sm font-semibold mb-2">Permissions</label>
              <div className="grid grid-cols-2 gap-2 max-h-60 overflow-y-auto border p-3 rounded bg-gray-50">
                {AVAILABLE_PERMISSIONS.map(perm => (
                  <label key={perm.id} className="flex items-center gap-2 text-sm cursor-pointer hover:bg-gray-100 p-1 rounded">
                    <input type="checkbox" checked={formData.permissions.includes(perm.id)} onChange={() => handleToggle(perm.id)} className="rounded text-blue-600 focus:ring-blue-500"/>
                    {perm.label}
                  </label>
                ))}
              </div>
            </div>
          </div>
          <div className="flex gap-2 mt-6">
            <button onClick={() => onSave(formData)} className="flex-1 bg-blue-600 text-white py-2 rounded hover:bg-blue-700" disabled={!formData.name.trim()}>Save</button>
            <button onClick={onClose} className="flex-1 bg-gray-300 text-gray-700 py-2 rounded hover:bg-gray-400">Cancel</button>
          </div>
        </div>
      </div>
    );
  };

  const RateCartModal = ({ rateCart, onSave, onClose }) => {
    const [formData, setFormData] = useState(rateCart || { location: '', cost: '' });
    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg p-6 w-full max-w-md">
                <h2 className="text-2xl font-bold mb-4">{rateCart ? 'Edit Rate Cart' : 'Add New Rate Cart'}</h2>
                <div className="space-y-4">
                    <div>
                        <label className="block text-sm font-semibold mb-1">Location <span className="text-red-500">*</span></label>
                        <select 
                            value={formData.location} 
                            onChange={(e) => setFormData({...formData, location: e.target.value})} 
                            className="w-full p-2 border rounded"
                            disabled={!!rateCart}
                        >
                            <option value="">-- Select Location --</option>
                            {refLocations.map((loc, i) => (<option key={i} value={loc}>{loc}</option>))}
                        </select>
                    </div>
                    <div>
                        <label className="block text-sm font-semibold mb-1">Cost <span className="text-red-500">*</span></label>
                        <input type="number" step="any" value={formData.cost} onChange={(e) => setFormData({...formData, cost: e.target.value})} className="w-full p-2 border rounded" />
                    </div>
                </div>
                <div className="flex gap-2 mt-6">
                    <button onClick={() => onSave(formData)} className="flex-1 bg-blue-600 text-white py-2 rounded hover:bg-blue-700" disabled={!formData.location || formData.cost === ''}>Save</button>
                    <button onClick={onClose} className="flex-1 bg-gray-300 text-gray-700 py-2 rounded hover:bg-gray-400">Cancel</button>
                </div>
            </div>
        </div>
    );
  };

  const ConfirmDialog = ({ message, onConfirm, onCancel }) => (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 w-full max-w-md">
        <h2 className="text-xl font-bold mb-4">Confirm Action</h2>
        <p className="text-gray-700 mb-6">{message}</p>
        <div className="flex gap-2">
          <button onClick={onConfirm} className="flex-1 bg-red-600 text-white py-2 rounded hover:bg-red-700">Confirm</button>
          <button onClick={onCancel} className="flex-1 bg-gray-300 text-gray-700 py-2 rounded hover:bg-gray-400">Cancel</button>
        </div>
      </div>
    </div>
  );

  const LogTableModal = ({ logs, title, onClose }) => (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg p-6 w-full max-w-4xl max-h-[80vh] overflow-hidden flex flex-col">
            <div className="flex justify-between items-center mb-4"><h2 className="text-2xl font-bold">Change Log: {title}</h2><button onClick={onClose} className="text-gray-500 hover:text-gray-700"><X size={24} /></button></div>
            <div className="overflow-y-auto flex-1 border rounded">
                <table className="w-full border-collapse">
                    <thead className="bg-gray-100 sticky top-0"><tr><th className="border p-3 text-left">Date</th><th className="border p-3 text-left">User</th><th className="border p-3 text-left">Field</th><th className="border p-3 text-left">Old Value</th><th className="border p-3 text-left">New Value</th></tr></thead>
                    <tbody>
                        {logs.length === 0 ? (<tr><td colSpan="5" className="p-4 text-center text-gray-500">No changes recorded.</td></tr>) : (
                            logs.map((log) => (<tr key={log.id} className="hover:bg-gray-50 text-sm"><td className="border p-3 whitespace-nowrap">{log.change_date}</td><td className="border p-3">{log.changed_by}</td><td className="border p-3 font-semibold">{log.field_name}</td><td className="border p-3 text-red-600 bg-red-50">{log.old_value || '(empty)'}</td><td className="border p-3 text-green-600 bg-green-50">{log.new_value || '(empty)'}</td></tr>))
                        )}
                    </tbody>
                </table>
            </div>
            <div className="mt-4 flex justify-end"><button onClick={onClose} className="bg-gray-300 text-gray-700 px-4 py-2 rounded hover:bg-gray-400">Close</button></div>
        </div>
    </div>
  );

  const renderNavigation = () => (
    <div className="bg-white shadow-md mb-6">
      <div className="max-w-7xl mx-auto px-6 py-4 flex flex-wrap justify-between items-center gap-4">
        <div className="flex flex-wrap gap-2">
          <button onClick={() => setCurrentPage('calculator')} className={`flex items-center gap-2 px-3 py-2 rounded transition ${currentPage === 'calculator' ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'}`}><Calculator size={18} /> Calculator</button>
          {permissions.includes('view_gates') && <button onClick={() => setCurrentPage('gates')} className={`flex items-center gap-2 px-3 py-2 rounded transition ${currentPage === 'gates' ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'}`}><Database size={18} /> Gates</button>}
          {permissions.includes('view_items') && <button onClick={() => setCurrentPage('items')} className={`flex items-center gap-2 px-3 py-2 rounded transition ${currentPage === 'items' ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'}`}><FileText size={18} /> Items</button>}
          {permissions.includes('view_rate_carts') && <button onClick={() => setCurrentPage('rate_carts')} className={`flex items-center gap-2 px-3 py-2 rounded transition ${currentPage === 'rate_carts' ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'}`}><Percent size={18} /> Rate Carts</button>}
          {permissions.includes('view_daily_report') && <button onClick={() => setCurrentPage('daily_report')} className={`flex items-center gap-2 px-3 py-2 rounded transition ${currentPage === 'daily_report' ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'}`}><Calendar size={18} /> Daily Report</button>}
          <button onClick={() => setCurrentPage('history')} className={`flex items-center gap-2 px-3 py-2 rounded transition ${currentPage === 'history' ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'}`}><History size={18} /> History</button>
          {permissions.includes('view_references') && (<button onClick={() => setCurrentPage('references')} className={`flex items-center gap-2 px-3 py-2 rounded transition ${currentPage === 'references' ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'}`}><ListIcon size={18} /> References</button>)}
          {permissions.includes('view_users') && (<button onClick={() => setCurrentPage('users')} className={`flex items-center gap-2 px-3 py-2 rounded transition ${currentPage === 'users' ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'}`}><Users size={18} /> Users</button>)}
          {permissions.includes('view_roles') && (<button onClick={() => setCurrentPage('roles')} className={`flex items-center gap-2 px-3 py-2 rounded transition ${currentPage === 'roles' ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'}`}><Shield size={18} /> Roles</button>)}
        </div>
        <div className="flex items-center gap-4">
            <div className="text-right"><p className="text-xs text-gray-500">Logged in as</p><div className="flex items-center gap-1"><User size={14} className="text-blue-600"/><p className="font-bold text-sm text-blue-600 capitalize">{username} ({userRole})</p></div></div>
            <button onClick={handleLogout} className="text-gray-500 hover:text-red-500 transition p-2 hover:bg-red-50 rounded-full" title="Logout"><LogOut size={20} /></button>
        </div>
      </div>
    </div>
  );

  // --- Views ---
  if (!token) return <LoginScreen onLogin={handleLogin} />;

  if (currentPage === 'roles' && permissions.includes('view_roles')) {
    return (
      <div className="min-h-screen bg-gray-50 p-6">
        <div className="max-w-6xl mx-auto">
          {notification && <div className={`fixed top-4 right-4 px-6 py-3 rounded-lg shadow-lg text-white z-50 ${getNotificationColor(notification.type)}`}>{notification.message}</div>}
          {renderNavigation()}
          <div className="bg-white rounded-lg shadow-md p-6">
            <div className="flex items-center justify-between mb-6">
              <h1 className="text-3xl font-bold text-gray-800">Role Management</h1>
              {permissions.includes('add_role') && <button onClick={() => { setEditingRole(null); setShowRoleModal(true); }} className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition"><Plus size={20} /> Add Role</button>}
            </div>
            <table className="w-full border-collapse border">
              <thead className="bg-gray-100"><tr><th className="border p-3 text-left">Role Name</th><th className="border p-3 text-left">Permissions</th><th className="border p-3 text-center w-32">Actions</th></tr></thead>
              <tbody>{rolesList.map((r, i) => (<tr key={i} className="hover:bg-gray-50"><td className="border p-3 font-semibold text-gray-700">{r.name}</td><td className="border p-3 text-xs text-gray-600"><div className="flex flex-wrap gap-1">{r.permissions.map(p => <span key={p} className="bg-gray-200 px-2 py-1 rounded text-gray-700">{p.replace('_', ' ')}</span>)}</div></td><td className="border p-3 text-center"><div className="flex justify-center gap-2">{permissions.includes('edit_role') && <button onClick={() => { setEditingRole(r); setShowRoleModal(true); }} className="p-2 bg-blue-100 text-blue-600 rounded"><Edit2 size={16} /></button>}{permissions.includes('delete_role') && <button onClick={() => deleteRole(r.name)} className="p-2 bg-red-100 text-red-600 rounded"><Trash2 size={16} /></button>}</div></td></tr>))}</tbody>
            </table>
          </div>
        </div>
        {showRoleModal && <RoleModal role={editingRole} onSave={saveRole} onClose={() => setShowRoleModal(false)} />}
      </div>
    );
  }

  if (currentPage === 'users' && permissions.includes('view_users')) {
      return (
        <div className="min-h-screen bg-gray-50 p-6">
            <div className="max-w-6xl mx-auto">
                {notification && <div className={`fixed top-4 right-4 px-6 py-3 rounded-lg shadow-lg text-white z-50 ${getNotificationColor(notification.type)}`}>{notification.message}</div>}
                {renderNavigation()}
                <div className="bg-white rounded-lg shadow-md p-6">
                    <div className="flex items-center justify-between mb-6">
                        <h1 className="text-3xl font-bold text-gray-800">User Management</h1>
                        {permissions.includes('add_user') && <button onClick={() => { setEditingUser(null); setShowUserModal(true); }} className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition"><Plus size={20} /> Add User</button>}
                    </div>
                    <div className="overflow-x-auto">
                        <table className="w-full border-collapse border">
                            <thead className="bg-gray-100"><tr><th className="border p-3 text-left">Username</th><th className="border p-3 text-left">Role</th><th className="border p-3 text-center w-32">Actions</th></tr></thead>
                            <tbody>{usersList.map((u, index) => (<tr key={index} className="hover:bg-gray-50"><td className="border p-3 font-semibold text-gray-700">{u.username}</td><td className="border p-3"><span className="px-2 py-1 rounded text-xs font-bold uppercase bg-blue-100 text-blue-700">{u.role}</span></td><td className="border p-3 text-center"><div className="flex justify-center gap-2">{permissions.includes('edit_user') && <button onClick={() => { setEditingUser(u); setShowUserModal(true); }} className="p-2 bg-blue-100 text-blue-600 rounded hover:bg-blue-200"><Edit2 size={16} /></button>}{permissions.includes('delete_user') && u.username !== username && (<button onClick={() => deleteUser(u.username)} className="p-2 bg-red-100 text-red-600 rounded hover:bg-red-200"><Trash2 size={16} /></button>)}</div></td></tr>))}</tbody>
                        </table>
                    </div>
                </div>
            </div>
            {showUserModal && <UserModal user={editingUser} onSave={saveUser} onClose={() => setShowUserModal(false)} />}
            {confirmDialog && <ConfirmDialog message={confirmDialog.message} onConfirm={confirmDialog.onConfirm} onCancel={confirmDialog.onCancel} />}
        </div>
      );
  }

  if (currentPage === 'rate_carts' && permissions.includes('view_rate_carts')) {
    return (
        <div className="min-h-screen bg-gray-50 p-6">
            <div className="max-w-6xl mx-auto">
                {notification && <div className={`fixed top-4 right-4 px-6 py-3 rounded-lg shadow-lg text-white z-50 ${getNotificationColor(notification.type)}`}>{notification.message}</div>}
                {renderNavigation()}
                <div className="bg-white rounded-lg shadow-md p-6">
                    <div className="flex items-center justify-between mb-6">
                        <h1 className="text-3xl font-bold text-gray-800">Rate Carts Management</h1>
                        {permissions.includes('add_rate_cart') && <button onClick={() => { setEditingRateCart(null); setShowRateCartModal(true); }} className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition"><Plus size={20} /> Add Rate Cart</button>}
                    </div>
                    <div className="overflow-x-auto">
                        <table className="w-full border-collapse border">
                            <thead className="bg-gray-100">
                                <tr>
                                    <th className="border p-3 text-left">Location</th>
                                    <th className="border p-3 text-left">Cost Cut Amount</th>
                                    <th className="border p-3 text-center w-32">Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {rateCarts.length === 0 ? (<tr><td colSpan="3" className="text-center p-4 text-gray-500">No Rate Carts Found</td></tr>) : 
                                    rateCarts.map((rc, i) => (
                                        <tr key={i} className="hover:bg-gray-50">
                                            <td className="border p-3 font-semibold text-gray-700">{rc.location}</td>
                                            <td className="border p-3">{formatNumber(rc.cost)}</td>
                                            <td className="border p-3 text-center">
                                                <div className="flex justify-center gap-2">
                                                    <button onClick={() => fetchRateCartLogs(rc)} className="p-2 bg-gray-100 text-gray-600 rounded hover:bg-gray-200" title="View Change Logs"><Clock size={16} /></button>
                                                    {permissions.includes('edit_rate_cart') && <button onClick={() => { setEditingRateCart(rc); setShowRateCartModal(true); }} className="p-2 bg-blue-100 text-blue-600 rounded hover:bg-blue-200"><Edit2 size={16} /></button>}
                                                    {permissions.includes('delete_rate_cart') && <button onClick={() => deleteRateCart(rc.location)} className="p-2 bg-red-100 text-red-600 rounded hover:bg-red-200"><Trash2 size={16} /></button>}
                                                </div>
                                            </td>
                                        </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
            {showRateCartModal && <RateCartModal rateCart={editingRateCart} onSave={saveRateCart} onClose={() => setShowRateCartModal(false)} />}
            {showRateCartLogModal && <LogTableModal logs={rateCartLogsData} title={currentLogRateCartLocation} onClose={() => setShowRateCartLogModal(false)} />}
        </div>
    );
  }

  if (currentPage === 'daily_report' && permissions.includes('view_daily_report')) {
      const filteredDailyReportData = dailyReportData.filter(row => {
        const matchBranch = (row.branch || '').toLowerCase().includes(dailyReportFilters.branch.toLowerCase());
        const matchItemCode = (row.item_code || '').toLowerCase().includes(dailyReportFilters.item_code.toLowerCase());
        const matchItemName = (row.item_name || '').toLowerCase().includes(dailyReportFilters.item_name.toLowerCase());
        const matchPrincipal = (row.principal || '').toLowerCase().includes(dailyReportFilters.principal.toLowerCase());
        const matchBrand = (row.brand || '').toLowerCase().includes(dailyReportFilters.brand.toLowerCase());
        const matchDriverName = (row.driver_name || '').toLowerCase().includes(dailyReportFilters.driver_name.toLowerCase());
        const matchCtns = String(row.ctns || '').toLowerCase().includes(dailyReportFilters.ctns.toLowerCase());
        const matchDriverTotal = String(row.driver_total_ctns || '').toLowerCase().includes(dailyReportFilters.driver_total_ctns.toLowerCase());
        const matchBranchCost = String(row.branch_cost || '').toLowerCase().includes(dailyReportFilters.branch_cost.toLowerCase());
        const matchCostPerCarton = String(row.cost_per_carton || '').toLowerCase().includes(dailyReportFilters.cost_per_carton.toLowerCase());
        const matchAllocatedCost = String(row.allocated_cost || '').toLowerCase().includes(dailyReportFilters.allocated_cost.toLowerCase());

        return matchBranch && matchItemCode && matchItemName && matchPrincipal && matchBrand && matchDriverName && matchCtns && matchDriverTotal && matchBranchCost && matchCostPerCarton && matchAllocatedCost;
      });

      const filteredTownshipReportData = dailyTownshipReportData.filter(row => {
        const matchBranch = (row.branch || '').toLowerCase().includes(townshipFilters.branch.toLowerCase());
        const matchDriver = (row.driver_name || '').toLowerCase().includes(townshipFilters.driver_name.toLowerCase());
        const matchTownship = (row.township || '').toLowerCase().includes(townshipFilters.township.toLowerCase());
        const matchCustomer = (row.customer_code || '').toLowerCase().includes(townshipFilters.customer_code.toLowerCase());
        const matchCtns = String(row.ctns || '').toLowerCase().includes(townshipFilters.ctns.toLowerCase());
        const matchDriverTotal = String(row.driver_total_ctns || '').toLowerCase().includes(townshipFilters.driver_total_ctns.toLowerCase());
        const matchBranchCost = String(row.branch_cost || '').toLowerCase().includes(townshipFilters.branch_cost.toLowerCase());
        const matchTotalDropPoints = String(row.total_drop_points || '').toLowerCase().includes(townshipFilters.total_drop_points.toLowerCase());
        const matchCostPerDropPoint = String(row.cost_per_drop_point || '').toLowerCase().includes(townshipFilters.cost_per_drop_point.toLowerCase());
        const matchCostPerCarton = String(row.cost_per_carton || '').toLowerCase().includes(townshipFilters.cost_per_carton.toLowerCase());
        const matchAllocatedCost = String(row.allocated_cost || '').toLowerCase().includes(townshipFilters.allocated_cost.toLowerCase());
        
        return matchBranch && matchDriver && matchTownship && matchCustomer && matchCtns && matchDriverTotal && matchBranchCost && matchTotalDropPoints && matchCostPerDropPoint && matchCostPerCarton && matchAllocatedCost;
      });

      return (
          <div className="min-h-screen bg-gray-50 p-6">
              <div className="max-w-full mx-auto">
                  {notification && <div className={`fixed top-4 right-4 px-6 py-3 rounded-lg shadow-lg text-white z-50 ${getNotificationColor(notification.type)}`}>{notification.message}</div>}
                  {renderNavigation()}
                  <div className="bg-white rounded-lg shadow-md p-6">
                      <div className="flex items-center justify-between mb-6">
                          <h1 className="text-3xl font-bold text-gray-800">Daily Allocation Report</h1>
                          <div className="flex gap-4">
                              <input 
                                  type="date" 
                                  value={dailyReportDate} 
                                  onChange={(e) => setDailyReportDate(e.target.value)}
                                  className="border p-2 rounded"
                              />
                              <button onClick={() => fetchDailyReport(dailyReportDate)} disabled={isDailyReportLoading} className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition disabled:bg-gray-400">
                                  {isDailyReportLoading ? 'Loading...' : 'Fetch Report'}
                              </button>
                          </div>
                      </div>

                      {/* --- TAB NAVIGATION --- */}
                      <div className="flex border-b mb-6 border-gray-200">
                          <button
                              className={`py-3 px-6 font-semibold text-lg transition-colors border-b-2 ${
                                  activeDailyTab === 'item' 
                                      ? 'border-blue-600 text-blue-600 bg-blue-50' 
                                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:bg-gray-50'
                              }`}
                              onClick={() => setActiveDailyTab('item')}
                          >
                              Allocation by Item
                          </button>
                          <button
                              className={`py-3 px-6 font-semibold text-lg transition-colors border-b-2 ${
                                  activeDailyTab === 'township' 
                                      ? 'border-blue-600 text-blue-600 bg-blue-50' 
                                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:bg-gray-50'
                              }`}
                              onClick={() => setActiveDailyTab('township')}
                          >
                              Allocation by Township & Customer
                          </button>
                      </div>

                      {/* --- ITEM LEVEL TABLE TAB CONTENT --- */}
                      {activeDailyTab === 'item' && (
                          <div className="animation-fade-in">
                              <div className="overflow-x-auto border rounded mb-8">
                                  <table className="w-full border-collapse">
                                      <thead className="bg-gray-100 sticky top-0">
                                          <tr>
                                              <th className="border p-2 text-left">
                                                  <div>Branch</div>
                                                  <input type="text" placeholder="Filter..." className="w-full mt-1 p-1 border rounded text-xs font-normal" value={dailyReportFilters.branch} onChange={(e) => setDailyReportFilters({...dailyReportFilters, branch: e.target.value})} />
                                              </th>
                                              <th className="border p-2 text-left">
                                                  <div>Driver Name</div>
                                                  <input type="text" placeholder="Filter..." className="w-full mt-1 p-1 border rounded text-xs font-normal" value={dailyReportFilters.driver_name} onChange={(e) => setDailyReportFilters({...dailyReportFilters, driver_name: e.target.value})} />
                                              </th>
                                              <th className="border p-2 text-left">
                                                  <div>Principal</div>
                                                  <input type="text" placeholder="Filter..." className="w-full mt-1 p-1 border rounded text-xs font-normal" value={dailyReportFilters.principal} onChange={(e) => setDailyReportFilters({...dailyReportFilters, principal: e.target.value})} />
                                              </th>
                                              <th className="border p-2 text-left">
                                                  <div>Brand</div>
                                                  <input type="text" placeholder="Filter..." className="w-full mt-1 p-1 border rounded text-xs font-normal" value={dailyReportFilters.brand} onChange={(e) => setDailyReportFilters({...dailyReportFilters, brand: e.target.value})} />
                                              </th>
                                              <th className="border p-2 text-left">
                                                  <div>Item Code</div>
                                                  <input type="text" placeholder="Filter..." className="w-full mt-1 p-1 border rounded text-xs font-normal" value={dailyReportFilters.item_code} onChange={(e) => setDailyReportFilters({...dailyReportFilters, item_code: e.target.value})} />
                                              </th>
                                              <th className="border p-2 text-left">
                                                  <div>Item Name</div>
                                                  <input type="text" placeholder="Filter..." className="w-full mt-1 p-1 border rounded text-xs font-normal" value={dailyReportFilters.item_name} onChange={(e) => setDailyReportFilters({...dailyReportFilters, item_name: e.target.value})} />
                                              </th>
                                              <th className="border p-2 text-right">
                                                  <div>Cartons</div>
                                                  <input type="text" placeholder="Filter..." className="w-full mt-1 p-1 border rounded text-xs font-normal text-left" value={dailyReportFilters.ctns} onChange={(e) => setDailyReportFilters({...dailyReportFilters, ctns: e.target.value})} />
                                              </th>
                                              <th className="border p-2 text-right">
                                                  <div>Driver Total (Ctns)</div>
                                                  <input type="text" placeholder="Filter..." className="w-full mt-1 p-1 border rounded text-xs font-normal text-left" value={dailyReportFilters.driver_total_ctns} onChange={(e) => setDailyReportFilters({...dailyReportFilters, driver_total_ctns: e.target.value})} />
                                              </th>
                                              <th className="border p-2 text-right">
                                                  <div>Branch Rate Cost</div>
                                                  <input type="text" placeholder="Filter..." className="w-full mt-1 p-1 border rounded text-xs font-normal text-left" value={dailyReportFilters.branch_cost} onChange={(e) => setDailyReportFilters({...dailyReportFilters, branch_cost: e.target.value})} />
                                              </th>
                                              <th className="border p-2 text-right text-purple-700">
                                                  <div>Cost per Carton</div>
                                                  <input type="text" placeholder="Filter..." className="w-full mt-1 p-1 border rounded text-xs font-normal text-left" value={dailyReportFilters.cost_per_carton} onChange={(e) => setDailyReportFilters({...dailyReportFilters, cost_per_carton: e.target.value})} />
                                              </th>
                                              <th className="border p-2 text-right text-blue-700">
                                                  <div>Allocated Cost</div>
                                                  <input type="text" placeholder="Filter..." className="w-full mt-1 p-1 border rounded text-xs font-normal text-left" value={dailyReportFilters.allocated_cost} onChange={(e) => setDailyReportFilters({...dailyReportFilters, allocated_cost: e.target.value})} />
                                              </th>
                                          </tr>
                                      </thead>
                                      <tbody>
                                          {filteredDailyReportData.length === 0 ? (
                                              <tr><td colSpan="11" className="text-center p-6 text-gray-500 italic">No allocation data found for the selected date or matching filters.</td></tr>
                                          ) : (
                                              filteredDailyReportData.map((row, idx) => (
                                                  <tr key={idx} className="hover:bg-gray-50 text-sm">
                                                      <td className="border p-2 font-bold text-gray-700">{row.branch}</td>
                                                      <td className="border p-2">{row.driver_name}</td>
                                                      <td className="border p-2">{row.principal}</td>
                                                      <td className="border p-2">{row.brand}</td>
                                                      <td className="border p-2">{row.item_code}</td>
                                                      <td className="border p-2">{row.item_name}</td>
                                                      <td className="border p-2 text-right">{formatNumber(row.ctns)}</td>
                                                      <td className="border p-2 text-right text-gray-500">{formatNumber(row.driver_total_ctns)}</td>
                                                      <td className="border p-2 text-right text-gray-500">{formatNumber(row.branch_cost)}</td>
                                                      <td className="border p-2 text-right font-bold text-purple-600">{formatNumber(row.cost_per_carton)}</td>
                                                      <td className="border p-2 text-right font-bold text-blue-600">{formatNumber(row.allocated_cost)}</td>
                                                  </tr>
                                              ))
                                          )}
                                      </tbody>
                                  </table>
                              </div>
                          </div>
                      )}

                      {/* --- TOWNSHIP LEVEL TABLE TAB CONTENT --- */}
                      {activeDailyTab === 'township' && (
                          <div className="animation-fade-in">
                              <div className="overflow-x-auto border rounded">
                                  <table className="w-full border-collapse">
                                      <thead className="bg-gray-100 sticky top-0">
                                          <tr>
                                              <th className="border p-2 text-left">
                                                  <div>Branch</div>
                                                  <input type="text" placeholder="Filter..." className="w-full mt-1 p-1 border rounded text-xs font-normal" value={townshipFilters.branch} onChange={(e) => setTownshipFilters({...townshipFilters, branch: e.target.value})} />
                                              </th>
                                              <th className="border p-2 text-left">
                                                  <div>Driver Name</div>
                                                  <input type="text" placeholder="Filter..." className="w-full mt-1 p-1 border rounded text-xs font-normal" value={townshipFilters.driver_name} onChange={(e) => setTownshipFilters({...townshipFilters, driver_name: e.target.value})} />
                                              </th>
                                              <th className="border p-2 text-left">
                                                  <div>Township</div>
                                                  <input type="text" placeholder="Filter..." className="w-full mt-1 p-1 border rounded text-xs font-normal" value={townshipFilters.township} onChange={(e) => setTownshipFilters({...townshipFilters, township: e.target.value})} />
                                              </th>
                                              <th className="border p-2 text-left">
                                                  <div>Customer Code</div>
                                                  <input type="text" placeholder="Filter..." className="w-full mt-1 p-1 border rounded text-xs font-normal" value={townshipFilters.customer_code} onChange={(e) => setTownshipFilters({...townshipFilters, customer_code: e.target.value})} />
                                              </th>
                                              <th className="border p-2 text-right">
                                                  <div>Customer Total (Ctns)</div>
                                                  <input type="text" placeholder="Filter..." className="w-full mt-1 p-1 border rounded text-xs font-normal text-left" value={townshipFilters.ctns} onChange={(e) => setTownshipFilters({...townshipFilters, ctns: e.target.value})} />
                                              </th>
                                              <th className="border p-2 text-right">
                                                  <div>Driver Total (Ctns)</div>
                                                  <input type="text" placeholder="Filter..." className="w-full mt-1 p-1 border rounded text-xs font-normal text-left" value={townshipFilters.driver_total_ctns} onChange={(e) => setTownshipFilters({...townshipFilters, driver_total_ctns: e.target.value})} />
                                              </th>
                                              <th className="border p-2 text-right">
                                                  <div>Branch Rate Cost</div>
                                                  <input type="text" placeholder="Filter..." className="w-full mt-1 p-1 border rounded text-xs font-normal text-left" value={townshipFilters.branch_cost} onChange={(e) => setTownshipFilters({...townshipFilters, branch_cost: e.target.value})} />
                                              </th>
                                              <th className="border p-2 text-right">
                                                  <div>Total Drop Points</div>
                                                  <input type="text" placeholder="Filter..." className="w-full mt-1 p-1 border rounded text-xs font-normal text-left" value={townshipFilters.total_drop_points} onChange={(e) => setTownshipFilters({...townshipFilters, total_drop_points: e.target.value})} />
                                              </th>
                                              <th className="border p-2 text-right text-orange-700">
                                                  <div>Cost per Drop Point</div>
                                                  <input type="text" placeholder="Filter..." className="w-full mt-1 p-1 border rounded text-xs font-normal text-left" value={townshipFilters.cost_per_drop_point} onChange={(e) => setTownshipFilters({...townshipFilters, cost_per_drop_point: e.target.value})} />
                                              </th>
                                              <th className="border p-2 text-right text-purple-700">
                                                  <div>Cost per Carton</div>
                                                  <input type="text" placeholder="Filter..." className="w-full mt-1 p-1 border rounded text-xs font-normal text-left" value={townshipFilters.cost_per_carton} onChange={(e) => setTownshipFilters({...townshipFilters, cost_per_carton: e.target.value})} />
                                              </th>
                                              <th className="border p-2 text-right text-blue-700">
                                                  <div>Allocated Cost</div>
                                                  <input type="text" placeholder="Filter..." className="w-full mt-1 p-1 border rounded text-xs font-normal text-left" value={townshipFilters.allocated_cost} onChange={(e) => setTownshipFilters({...townshipFilters, allocated_cost: e.target.value})} />
                                              </th>
                                          </tr>
                                      </thead>
                                      <tbody>
                                          {filteredTownshipReportData.length === 0 ? (
                                              <tr><td colSpan="11" className="text-center p-6 text-gray-500 italic">No allocation data found matching filters.</td></tr>
                                          ) : (
                                              filteredTownshipReportData.map((row, idx) => (
                                                  <tr key={idx} className="hover:bg-gray-50 text-sm">
                                                      <td className="border p-2 font-bold text-gray-700">{row.branch}</td>
                                                      <td className="border p-2">{row.driver_name}</td>
                                                      <td className="border p-2">{row.township}</td>
                                                      <td className="border p-2">{row.customer_code}</td>
                                                      <td className="border p-2 text-right">{formatNumber(row.ctns)}</td>
                                                      <td className="border p-2 text-right text-gray-500">{formatNumber(row.driver_total_ctns)}</td>
                                                      <td className="border p-2 text-right text-gray-500">{formatNumber(row.branch_cost)}</td>
                                                      <td className="border p-2 text-right text-gray-500">{formatNumber(row.total_drop_points)}</td>
                                                      <td className="border p-2 text-right font-bold text-orange-600">{formatNumber(row.cost_per_drop_point)}</td>
                                                      <td className="border p-2 text-right font-bold text-purple-600">{formatNumber(row.cost_per_carton)}</td>
                                                      <td className="border p-2 text-right font-bold text-blue-600">{formatNumber(row.allocated_cost)}</td>
                                                  </tr>
                                              ))
                                          )}
                                      </tbody>
                                  </table>
                              </div>
                          </div>
                      )}
                  </div>
              </div>
          </div>
      );
  }

  if (currentPage === 'references' && permissions.includes('view_references')) {
      return (
        <div className="min-h-screen bg-gray-50 p-6">
            <div className="max-w-6xl mx-auto">
                {notification && <div className={`fixed top-4 right-4 px-6 py-3 rounded-lg shadow-lg text-white z-50 ${getNotificationColor(notification.type)}`}>{notification.message}</div>}
                {renderNavigation()}
                <h1 className="text-3xl font-bold text-gray-800 mb-6">Manage Reference Data</h1>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    <div className="bg-white rounded-lg shadow-md p-6"><h2 className="text-xl font-bold mb-4 text-blue-700">Locations (From/To)</h2>{permissions.includes('add_reference') && <div className="flex gap-2 mb-4"><input type="text" placeholder="New Location..." className="border p-2 rounded flex-1" id="new-loc" /><button onClick={() => { addReference('locations', document.getElementById('new-loc').value); document.getElementById('new-loc').value = ''; }} className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700">Add</button></div>}<div className="border rounded max-h-96 overflow-y-auto">{refLocations.map((loc, i) => (<div key={i} className="flex justify-between items-center p-3 border-b last:border-0 hover:bg-gray-50"><span>{loc}</span>{permissions.includes('delete_reference') && <button onClick={() => deleteReference('locations', loc)} className="text-red-500 hover:text-red-700"><X size={18} /></button>}</div>))}</div></div>
                    <div className="bg-white rounded-lg shadow-md p-6"><h2 className="text-xl font-bold mb-4 text-purple-700">Units of Measure</h2>{permissions.includes('add_reference') && <div className="flex gap-2 mb-4"><input type="text" placeholder="New UOM..." className="border p-2 rounded flex-1" id="new-uom" /><button onClick={() => { addReference('uoms', document.getElementById('new-uom').value); document.getElementById('new-uom').value = ''; }} className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700">Add</button></div>}<div className="border rounded max-h-96 overflow-y-auto">{refUOMs.map((u, i) => (<div key={i} className="flex justify-between items-center p-3 border-b last:border-0 hover:bg-gray-50"><span>{u}</span>{permissions.includes('delete_reference') && <button onClick={() => deleteReference('uoms', u)} className="text-red-500 hover:text-red-700"><X size={18} /></button>}</div>))}</div></div>
                    <div className="bg-white rounded-lg shadow-md p-6"><h2 className="text-xl font-bold mb-4 text-orange-700">Channels</h2>{permissions.includes('add_reference') && <div className="flex gap-2 mb-4"><input type="text" placeholder="New Channel..." className="border p-2 rounded flex-1" id="new-chan" /><button onClick={() => { addReference('channels', document.getElementById('new-chan').value); document.getElementById('new-chan').value = ''; }} className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700">Add</button></div>}<div className="border rounded max-h-96 overflow-y-auto">{refChannels.map((c, i) => (<div key={i} className="flex justify-between items-center p-3 border-b last:border-0 hover:bg-gray-50"><span>{c}</span>{permissions.includes('delete_reference') && <button onClick={() => deleteReference('channels', c)} className="text-red-500 hover:text-red-700"><X size={18} /></button>}</div>))}</div></div>
                </div>
            </div>
        </div>
      );
  }

  if (currentPage === 'history') {
    const canSubmit = permissions.includes('submit_calculation');
    const canClaim = permissions.includes('claim_calculation');
    const canDeleteHistory = permissions.includes('delete_history');

    const filteredHistory = historyData.filter(record => {
      const matchIdStatus = (String(record.id) + ' ' + (record.status || '')).toLowerCase().includes(historyFilters.id_status.toLowerCase());
      const matchDate = (record.created_at || '').toLowerCase().includes(historyFilters.date.toLowerCase());
      const matchRoute = ((record.gate_name || '') + ' ' + (record.from_loc || '') + ' ' + (record.to_loc || '')).toLowerCase().includes(historyFilters.route.toLowerCase());
      const matchDocNums = (record.doc_nums ? record.doc_nums.join(', ') : '').toLowerCase().includes(historyFilters.doc_nums.toLowerCase());
      const matchTotalCost = (String(record.final_total_cost) || '').toLowerCase().includes(historyFilters.total_cost.toLowerCase());
      const matchAuthor = [record.created_by, record.submitted_by, record.claimed_by]
          .filter(Boolean)
          .join(' ')
          .toLowerCase()
          .includes((historyFilters.author || '').toLowerCase());

      return matchIdStatus && matchDate && matchRoute && matchDocNums && matchTotalCost && matchAuthor;
    });

    return (
      <div className="min-h-screen bg-gray-50 p-6">
        <div className="max-w-6xl mx-auto">
          {notification && <div className={`fixed top-4 right-4 px-6 py-3 rounded-lg shadow-lg text-white z-50 ${getNotificationColor(notification.type)}`}>{notification.message}</div>}
          {renderNavigation()}
          <div className="bg-white rounded-lg shadow-md p-6">
            <h1 className="text-3xl font-bold text-gray-800 mb-6">Calculation History</h1>
            <div className="overflow-x-auto">
              <table className="w-full border-collapse border">
                <thead className="bg-gray-100">
                  <tr>
                    <th className="border p-2 text-left"><div>ID / Status</div><input type="text" placeholder="Filter..." className="w-full mt-1 p-1 border rounded text-xs font-normal" value={historyFilters.id_status} onChange={(e) => setHistoryFilters({...historyFilters, id_status: e.target.value})} /></th>
                    <th className="border p-2 text-left"><div>Date</div><input type="text" placeholder="Filter..." className="w-full mt-1 p-1 border rounded text-xs font-normal" value={historyFilters.date} onChange={(e) => setHistoryFilters({...historyFilters, date: e.target.value})} /></th>
                    <th className="border p-2 text-left"><div>Route</div><input type="text" placeholder="Filter..." className="w-full mt-1 p-1 border rounded text-xs font-normal" value={historyFilters.route} onChange={(e) => setHistoryFilters({...historyFilters, route: e.target.value})} /></th>
                    <th className="border p-2 text-left"><div>Doc Nums</div><input type="text" placeholder="Filter..." className="w-full mt-1 p-1 border rounded text-xs font-normal" value={historyFilters.doc_nums} onChange={(e) => setHistoryFilters({...historyFilters, doc_nums: e.target.value})} /></th>
                    <th className="border p-2 text-left"><div>Total Cost (MMK)</div><input type="text" placeholder="Filter..." className="w-full mt-1 p-1 border rounded text-xs font-normal" value={historyFilters.total_cost} onChange={(e) => setHistoryFilters({...historyFilters, total_cost: e.target.value})} /></th>
                    <th className="border p-2 text-left"><div>Author</div><input type="text" placeholder="Filter..." className="w-full mt-1 p-1 border rounded text-xs font-normal" value={historyFilters.author} onChange={(e) => setHistoryFilters({...historyFilters, author: e.target.value})} /></th>
                    <th className="border p-2 text-center align-top">Actions</th>
                  </tr>
                </thead>
                <tbody>{filteredHistory.length === 0 ? (<tr><td colSpan="7" className="text-center p-4 text-gray-500">No matching calculations found.</td></tr>) : (filteredHistory.map((record) => (
                    <tr key={record.id} className="hover:bg-gray-50">
                        <td className="border p-3"><span className="text-sm text-gray-600 font-bold block mb-1">#{record.id}</span><span className={`px-2 py-1 rounded text-xs font-bold uppercase ${record.status === 'claimed' ? 'bg-blue-100 text-blue-700' : record.status === 'submitted' ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'}`}>{record.status}</span></td>
                        <td className="border p-3 text-sm text-gray-600"><div className="font-semibold">{record.created_at}</div></td>
                        <td className="border p-3"><span className="font-bold text-gray-700">{record.gate_name}</span> <br/><span className="text-xs text-gray-500">{record.from_loc} &rarr; {record.to_loc}</span></td>
                        <td className="border p-3 text-sm">{record.doc_nums.length} Doc(s): {record.doc_nums.join(', ')}</td>
                        <td className="border p-3 text-right font-bold text-blue-600">{formatNumber(record.final_total_cost)}</td>
                        <td className="border p-3 text-sm">
                            <div className="mb-1"><span className="text-gray-500 text-xs">Saved:</span> <span className="font-semibold text-gray-800">{record.created_by || 'unknown'}</span></div>
                            {record.submitted_by && <div className="mb-1"><span className="text-gray-500 text-xs">Submitted:</span> <span className="font-semibold text-blue-600">{record.submitted_by}</span></div>}
                            {record.claimed_by && <div><span className="text-gray-500 text-xs">Claimed:</span> <span className="font-semibold text-green-600">{record.claimed_by}</span></div>}
                        </td>
                        <td className="border p-3 text-center">
                            <div className="flex justify-center gap-2">
                                <button onClick={() => handleDownloadHistoryExcel(record)} className="px-3 py-1 bg-purple-100 text-purple-700 rounded hover:bg-purple-200 text-sm font-semibold flex items-center gap-1"><FileDown size={16} /></button>
                                <button onClick={() => loadSavedCalculation(record)} className="px-3 py-1 bg-green-100 text-green-700 rounded hover:bg-green-200 text-sm font-semibold">Load</button>
                                {canSubmit && record.status === 'saved' && (<button onClick={() => handleSubmitHistory(record.id)} className="px-3 py-1 bg-blue-100 text-blue-700 rounded hover:bg-blue-200 text-sm font-semibold flex items-center gap-1" title="Submit"><CheckCircle size={16} /> Submit</button>)}
                                {canClaim && record.status === 'submitted' && (<button onClick={() => handleClaimHistory(record.id)} className="px-3 py-1 bg-indigo-100 text-indigo-700 rounded hover:bg-indigo-200 text-sm font-semibold flex items-center gap-1" title="Claim"><CheckCircle size={16} /> Claim</button>)}
                                {canDeleteHistory && (<button onClick={() => deleteHistory(record.id)} className="p-1 text-red-500 hover:bg-red-50 rounded"><Trash2 size={18} /></button>)}
                            </div>
                        </td>
                    </tr>)))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (currentPage === 'gates' && permissions.includes('view_gates')) {
    return (
      <div className="min-h-screen bg-gray-50 p-6">
        <div className="max-w-6xl mx-auto">
          {notification && <div className={`fixed top-4 right-4 px-6 py-3 rounded-lg shadow-lg text-white z-50 ${getNotificationColor(notification.type)}`}>{notification.message}</div>}
          {renderNavigation()}
          <div className="bg-white rounded-lg shadow-md p-6">
            <div className="flex items-center justify-between mb-6">
              <h1 className="text-3xl font-bold text-gray-800">Transportation Cost by Gate</h1>
              {permissions.includes('add_gate') && (<button onClick={() => setShowAddGateModal(true)} className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition"><Plus size={20} /> Add Gate</button>)}
            </div>
            <div className="overflow-x-auto">
              <table className="w-full border-collapse border">
                <thead className="bg-gray-100"><tr><th className="border p-3 text-left">Gate Name</th><th className="border p-3 text-left">From</th><th className="border p-3 text-left">To</th><th className="border p-3 text-left">UOM</th><th className="border p-3 text-left">Unit</th><th className="border p-3 text-left">Cost</th><th className="border p-3 text-center">Actions</th></tr></thead>
                <tbody>{gateData.map((gate, index) => (<tr key={index}><td className="border p-3">{gate.gate_name}</td><td className="border p-3">{gate.from_loc}</td><td className="border p-3">{gate.to_loc}</td><td className="border p-3">{gate.uom || '-'}</td><td className="border p-3">{gate.unit || '-'}</td><td className="border p-3">{formatNumber(gate.cost)}</td><td className="border p-3 text-center"><div className="flex items-center justify-center gap-2"><button onClick={() => fetchGateLogs(gate)} className="p-2 bg-gray-100 text-gray-600 rounded hover:bg-gray-200" title="View Change Logs"><Clock size={16} /></button>{permissions.includes('edit_gate') && <button onClick={() => { setOriginalGateName(gate.gate_name); setEditingGate(gate); setShowAddGateModal(true); }} className="p-2 bg-blue-500 text-white rounded hover:bg-blue-600"><Edit2 size={16} /></button>}{permissions.includes('delete_gate') && <button onClick={() => deleteGate(gate.gate_id)} className="p-2 bg-red-500 text-white rounded hover:bg-red-600"><Trash2 size={16} /></button>}</div></td></tr>))}</tbody>
              </table>
            </div>
          </div>
          {showAddGateModal && <GateModal gate={editingGate} onSave={saveGate} onClose={() => { setShowAddGateModal(false); setEditingGate(null); setOriginalGateName(null); }} />}
          {showLogModal && <LogTableModal logs={logsData} title={currentLogGateName} onClose={() => setShowLogModal(false)} />}
          {confirmDialog && <ConfirmDialog message={confirmDialog.message} onConfirm={confirmDialog.onConfirm} onCancel={confirmDialog.onCancel} />}
        </div>
      </div>
    );
  }

  if (currentPage === 'items' && permissions.includes('view_items')) {
    const filteredItems = itemPricingData.filter(item => {
      const matchCode = (item.item_code || '').toLowerCase().includes(itemFilters.item_code.toLowerCase());
      const matchName = (item.item_name || '').toLowerCase().includes(itemFilters.item_name.toLowerCase());
      const matchPrincipal = (item.principal || '').toLowerCase().includes(itemFilters.principal.toLowerCase());
      const matchBrand = (item.brand || '').toLowerCase().includes(itemFilters.brand.toLowerCase());
      const matchCost = (String(item.transportation_cost) || '').toLowerCase().includes(itemFilters.transportation_cost.toLowerCase());
      return matchCode && matchName && matchPrincipal && matchBrand && matchCost;
    });

    return (
      <div className="min-h-screen bg-gray-50 p-6">
        <div className="max-w-7xl mx-auto">
          {notification && <div className={`fixed top-4 right-4 px-6 py-3 rounded-lg shadow-lg text-white z-50 ${getNotificationColor(notification.type)}`}>{notification.message}</div>}
          {renderNavigation()}
          <div className="bg-white rounded-lg shadow-md p-6">
            <div className="flex items-center justify-between mb-6">
              <h1 className="text-3xl font-bold text-gray-800">Transportation Cost by Item</h1>
              <div className="flex gap-2">
                {selectedGateForPricing && (
                  <><button onClick={handleExportExcel} className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"><Download size={20} /> Download Excel</button>
                    {(permissions.includes('add_item') && permissions.includes('edit_item')) && <label className="flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition cursor-pointer"><Upload size={20} /> Upload Excel <input type="file" accept=".xlsx,.xls" onChange={handleImportExcel} className="hidden" /></label>}
                    {permissions.includes('add_item') && <button onClick={() => setShowAddItemModal(true)} className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition"><Plus size={20} /> Add Item</button>}
                  </>
                )}
              </div>
            </div>

            <div className="mb-6">
              <label className="block text-sm font-semibold mb-2">Select Gate</label>
              <select value={selectedGateForPricing} onChange={(e) => setSelectedGateForPricing(e.target.value)} className="w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-500">
                <option value="">-- Select a Gate --</option>
                {gates.map((gate) => (<option key={gate.gate_id} value={gate.gate_id}>{gate.gate_name} ({gate.from_loc} &rarr; {gate.to_loc})</option>))}
              </select>
            </div>

            {selectedGateForPricing && (
              <div className="overflow-x-auto">
                <table className="w-full border-collapse border text-sm">
                  <thead className="bg-gray-100">
                    <tr>
                      <th className="border p-2 text-left"><div>Item Code</div><input type="text" placeholder="Filter..." className="w-full mt-1 p-1 border rounded text-xs font-normal" value={itemFilters.item_code} onChange={(e) => setItemFilters({...itemFilters, item_code: e.target.value})} /></th>
                      <th className="border p-2 text-left"><div>Item Name</div><input type="text" placeholder="Filter..." className="w-full mt-1 p-1 border rounded text-xs font-normal" value={itemFilters.item_name} onChange={(e) => setItemFilters({...itemFilters, item_name: e.target.value})} /></th>
                      <th className="border p-2 text-left"><div>Principal</div><input type="text" placeholder="Filter..." className="w-full mt-1 p-1 border rounded text-xs font-normal" value={itemFilters.principal} onChange={(e) => setItemFilters({...itemFilters, principal: e.target.value})} /></th>
                      <th className="border p-2 text-left"><div>Brand</div><input type="text" placeholder="Filter..." className="w-full mt-1 p-1 border rounded text-xs font-normal" value={itemFilters.brand} onChange={(e) => setItemFilters({...itemFilters, brand: e.target.value})} /></th>
                      <th className="border p-2 text-left"><div>Transport Cost</div><input type="text" placeholder="Filter..." className="w-full mt-1 p-1 border rounded text-xs font-normal" value={itemFilters.transportation_cost} onChange={(e) => setItemFilters({...itemFilters, transportation_cost: e.target.value})} /></th>
                      <th className="border p-2 text-left">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredItems.map((item, index) => (
                      <tr key={index}>
                        <td className="border p-2">{item.item_code}</td><td className="border p-2">{item.item_name}</td><td className="border p-2">{item.principal}</td><td className="border p-2">{item.brand}</td><td className="border p-2">{formatNumber(item.transportation_cost)}</td>
                        <td className="border p-2">
                          <div className="flex gap-2">
                                <button onClick={() => fetchItemLogs(item)} className="p-1 bg-gray-100 text-gray-600 rounded hover:bg-gray-200" title="View Change Logs"><Clock size={14} /></button>
                                {permissions.includes('edit_item') && <button onClick={() => { setOriginalItemCode(item.item_code); setEditingItem(item); setShowAddItemModal(true); }} className="p-1 bg-blue-500 text-white rounded hover:bg-blue-600"><Edit2 size={14} /></button>}
                                {permissions.includes('delete_item') && <button onClick={() => deleteItem(item.item_code)} className="p-1 bg-red-500 text-white rounded hover:bg-red-600"><Trash2 size={14} /></button>}
                          </div>
                        </td>
                      </tr>
                    ))}
                    {filteredItems.length === 0 && (<tr><td colSpan="6" className="text-center p-4 text-gray-500 italic">No items found matching your filters.</td></tr>)}
                  </tbody>
                </table>
              </div>
            )}
          </div>
          {showAddItemModal && <ItemModal item={editingItem} onSave={saveItem} onClose={() => { setShowAddItemModal(false); setEditingItem(null); setOriginalItemCode(null); }} />}
          {showItemLogModal && <LogTableModal logs={itemLogsData} title={currentLogItemName} onClose={() => setShowItemLogModal(false)} />}
          {confirmDialog && <ConfirmDialog message={confirmDialog.message} onConfirm={confirmDialog.onConfirm} onCancel={confirmDialog.onCancel} />}
        </div>
      </div>
    );
  }

  // Calculator View (Default)
  const hasCalculated = calculatedProducts.length > 0;
  const rawTableData = hasCalculated ? calculatedProducts : products;
  const hasDirectPricingItems = hasCalculated && calculatedProducts.some(p => p.system_rate !== undefined && p.system_rate !== null);

  const tableData = Object.values(rawTableData.reduce((acc, curr) => {
    if (!acc[curr.code]) { acc[curr.code] = { ...curr }; } 
    else {
      acc[curr.code].ctns = (acc[curr.code].ctns || 0) + (curr.ctns || 0);
      acc[curr.code].weight += curr.weight || 0;
      if (curr.total_cost !== undefined) acc[curr.code].total_cost = (acc[curr.code].total_cost || 0) + curr.total_cost;
    }
    return acc;
  }, {})).map(item => {
    if (item.total_cost !== undefined && item.ctns > 0) item.display_calculated_rate = item.total_cost / item.ctns;
    else item.display_calculated_rate = item.unit_cost; 
    return item;
  }).sort((a, b) => a.code.localeCompare(b.code));

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-6xl mx-auto">
        {notification && <div className={`fixed top-4 right-4 px-6 py-3 rounded-lg shadow-lg text-white z-50 ${getNotificationColor(notification.type)}`}>{notification.message}</div>}
        {renderNavigation()}
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <h1 className="text-3xl font-bold text-gray-800 mb-6">Logistic Cost Calculator</h1>
          <div className="bg-white rounded-lg border p-6 mb-6">
            <h2 className="text-xl font-bold mb-4">Select Doc Nums (Transfer IDs) <span className="text-red-500">*</span></h2>
            <div className="relative mb-4">
              <div className="relative">
                <input type="text" placeholder="Search and add a Doc Num (e.g. 22#####)..." value={docNumSearchTerm} onChange={(e) => { setDocNumSearchTerm(e.target.value); setShowDocNumDropdown(true); }} onFocus={() => setShowDocNumDropdown(true)} onBlur={() => setTimeout(() => setShowDocNumDropdown(false), 200)} className="w-full p-3 pl-10 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none" />
                <div className="absolute left-3 top-3 text-gray-400"><Search size={20} /></div>
              </div>
              {showDocNumDropdown && (
                <div className="absolute z-10 w-full mt-1 bg-white border rounded-lg shadow-xl max-h-60 overflow-y-auto">
                  {docNums.filter(doc => !selectedDocNums.includes(doc.doc_num)).filter(doc => `${doc.doc_num} ${doc.doc_date || ''}`.toLowerCase().includes(docNumSearchTerm.toLowerCase())).map((doc) => (
                      <div key={doc.doc_num} className="p-3 hover:bg-blue-50 cursor-pointer border-b last:border-0" onMouseDown={(e) => { e.preventDefault(); handleAddDocNum(doc.doc_num); setDocNumSearchTerm(''); setShowDocNumDropdown(false); }}>
                        <span className="font-semibold text-gray-800">{doc.doc_num}</span>{doc.doc_date && <span className="text-gray-500 ml-2">- {doc.doc_date}</span>}
                      </div>
                    ))}
                  {docNums.filter(doc => !selectedDocNums.includes(doc.doc_num) && `${doc.doc_num} ${doc.doc_date || ''}`.toLowerCase().includes(docNumSearchTerm.toLowerCase())).length === 0 && (<div className="p-3 text-gray-500 italic">No matching Doc Nums found.</div>)}
                </div>
              )}
            </div>
            <div className="flex flex-wrap gap-2">
              {selectedDocNums.length === 0 && (<p className="text-gray-500 text-sm italic">No Doc Nums selected</p>)}
              
              {/* UPDATED: Graceful fallback for displaying missing Date attributes */}
              {selectedDocNums.map(id => {
                const docObj = docNums.find(d => String(d.doc_num) === String(id));
                let displayDate = docObj ? docObj.doc_date : null;

                // Fallback: If not found in fresh live external data (DWBI purged), look up the loaded calculated products state!
                if (!displayDate && calculatedProducts && calculatedProducts.length > 0) {
                    const matchedProd = calculatedProducts.find(p => String(p.sin_no) === String(id));
                    if (matchedProd && matchedProd.doc_date) {
                        const dateStr = String(matchedProd.doc_date);
                        displayDate = dateStr.length >= 10 ? dateStr.substring(0, 10) : dateStr;
                    }
                }

                return (
                    <div key={id} className="flex items-center gap-2 bg-blue-100 text-blue-800 px-3 py-1 rounded-full border border-blue-200">
                        <span className="font-semibold">{displayDate ? `${id} - ${displayDate}` : id}</span>
                        <button onClick={() => handleRemoveDocNum(id)} className="hover:text-red-600 transition"><X size={16} /></button>
                    </div>
                );
              })}
            </div>
          </div>
          
          {products.length > 0 && (
            <div className="flex flex-col gap-6 mb-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="bg-white rounded-lg border p-6"><h2 className="text-xl font-bold mb-4">Select From <span className="text-red-500">*</span></h2><select value={selectedFrom} onChange={(e) => handleFromChange(e.target.value)} className="w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-500"><option value="">-- Select Origin --</option>{fromLocations.map((loc) => (<option key={loc} value={loc}>{loc}</option>))}</select></div>
                <div className="bg-white rounded-lg border p-6"><h2 className="text-xl font-bold mb-4">Select To <span className="text-red-500">*</span></h2><select value={selectedTo} onChange={(e) => handleToChange(e.target.value)} className="w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed" disabled={!selectedFrom}><option value="">-- Select Destination --</option>{toLocations.map((loc) => (<option key={loc} value={loc}>{loc}</option>))}</select></div>
              </div>
              {(selectedFrom && selectedTo) && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="bg-white rounded-lg border p-6"><h2 className="text-xl font-bold mb-4">Select Gate <span className="text-red-500">*</span></h2><select value={selectedGate} onChange={(e) => handleGateChange(e.target.value)} className="w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-500"><option value="">-- Select a Gate --</option>{gates.filter(gate => gate.from_loc === selectedFrom && gate.to_loc === selectedTo).map((gate) => (<option key={gate.gate_name} value={gate.gate_name}>{gate.gate_name} - {gate.calculation_type === 'gate_pricing' ? ' Gate Pricing' : gate.calculation_type === 'direct_pricing' ? ' Direct Pricing' : ' Unknown'}</option>))}</select></div>
                  <div className="bg-white rounded-lg border p-6"><h2 className="text-xl font-bold mb-4">Select Channel <span className="text-red-500">*</span></h2><select value={selectedChannel} onChange={(e) => setSelectedChannel(e.target.value)} className="w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-500"><option value="">-- Select a Channel --</option>{refChannels.map((chan, i) => (<option key={i} value={chan}>{chan}</option>))}</select></div>
                </div>
              )}
            </div>
          )}

          {products.length > 0 && selectedGate && (() => {
            const currentGate = gates.find(g => g.gate_name === selectedGate && g.from_loc === selectedFrom && g.to_loc === selectedTo);
            return (
              <div className="bg-blue-50 rounded-lg border-2 border-blue-300 p-6 mb-6">
                <div className="flex items-center justify-between flex-wrap gap-4">
                  <div><h3 className="text-lg font-semibold text-gray-800">Calculation Type</h3><p className="text-gray-600 mt-1">{calculationType === 'gate_pricing' ? 'Gate Pricing Calculation' : calculationType === 'direct_pricing' ? 'Direct Pricing Calculation' : 'Unknown Type'}</p></div>
                  {currentGate && currentGate.cost !== null && (<div className="text-center"><p className="text-sm text-gray-600">Gate Cost</p><p className="text-xl font-bold text-green-600">{formatNumber(currentGate.cost)} MMK {currentGate.uom && <span className="text-sm font-medium text-gray-500 ml-1">/ {currentGate.unit || 1} {currentGate.uom}</span>}</p></div>)}
                  <div className="text-right"><p className="text-sm text-gray-600">Route</p><p className="text-xl font-bold text-blue-600">{selectedFrom} &rarr; {selectedTo}</p></div>
                </div>
              </div>
            );
          })()}

          {products.length > 0 && (
            <>
              <div className="bg-white rounded-lg border p-6 mb-6">
                <h2 className="text-xl font-bold mb-4">{hasCalculated ? "Calculated Results" : "Product Details"}</h2>
                <div className="overflow-x-auto">
                  <table className="w-full border-collapse border">
                    <thead className="bg-gray-100">
                      <tr>
                        <th className="border p-2 text-left">Item Code</th><th className="border p-2 text-left">Description</th><th className="border p-2 text-left">Cartons</th><th className="border p-2 text-left">Weight</th><th className="border p-2 text-left">UOM</th>
                        {hasDirectPricingItems && (<th className="border p-2 text-left">System Rate (Ctn)</th>)}
                        {hasCalculated && (<th className="border p-2 text-left">Calculated Rate (Ctn)</th>)}
                        {hasCalculated && (<th className="border p-2 text-left">Cost (MMK)</th>)}
                      </tr>
                    </thead>
                    <tbody>
                      {tableData.map((product, index) => (
                        <tr key={index}>
                          <td className="border p-2">{product.code}</td><td className="border p-2">{product.name}</td><td className="border p-2">{product.ctns}</td><td className="border p-2">{formatNumber(product.weight)}</td><td className="border p-2">Kg</td>
                          {hasDirectPricingItems && (<td className="border p-2">{product.system_rate !== undefined && product.system_rate !== null ? formatNumber(product.system_rate) : '-'}</td>)}
                          {hasCalculated && (<td className="border p-2">{product.display_calculated_rate !== undefined && product.display_calculated_rate !== null ? formatNumber(product.display_calculated_rate) : '-'}</td>)}
                          {hasCalculated && (<td className="border p-2 font-semibold">{product.total_cost !== undefined ? formatNumber(product.total_cost) : '-'}</td>)}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
              
              <div className="bg-white rounded-lg border p-6 mb-6">
                <h2 className="text-xl font-bold mb-4">Total Summary</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="bg-gradient-to-r from-purple-50 to-purple-100 rounded-lg border border-purple-200 p-6 flex flex-col justify-center"><div className="flex justify-between items-center mb-2"><span className="text-lg font-semibold text-gray-700 mb-2">Total Weight</span><span className="text-3xl font-bold text-purple-600">{formatNumber(totalWeight)} Kg</span></div></div>
                  {calculatedTotalCost !== null && (
                    <div className="bg-gradient-to-r from-blue-50 to-blue-100 rounded-lg border border-blue-200 p-6 flex flex-col justify-center">
                      <div className="flex justify-between items-center mb-2"><span className="text-lg font-semibold text-gray-700">Total Cost</span><span className="text-3xl font-bold text-blue-600">{formatNumber(calculatedTotalCost)} MMK</span></div>
                      {additionalCharges && (
                        <div className="mt-2 pt-2 border-t border-blue-200 text-sm text-gray-600 space-y-1">
                          <div className="flex justify-between"><span>Subtotal (Transport):</span><span>{formatNumber(calculatedTotalCost - (parseFloat(additionalCharges) || 0))} MMK</span></div>
                          <div className="flex justify-between"><span>Additional Charges:</span><span>{formatNumber(additionalCharges)} MMK</span></div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>

              <div className="bg-white rounded-lg border p-6 mb-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <label className={`block text-sm font-semibold mb-2 ${!isManualTotalCostEnabled ? 'text-gray-400' : 'text-gray-700'}`}>Total Cost (Manual Override)</label>
                    <input type="number" value={manualTotalCost} onChange={(e) => setManualTotalCost(e.target.value)} placeholder={isManualTotalCostEnabled ? "Enter base transport amount..." : "Not applicable for selected items"} className={`w-full p-3 border rounded-lg ${!isManualTotalCostEnabled ? 'bg-gray-100 cursor-not-allowed text-gray-500' : ''}`} disabled={!isManualTotalCostEnabled} />
                    <p className={`text-xs mt-1 ${!isManualTotalCostEnabled ? 'text-gray-400' : 'text-gray-500'}`}>{isManualTotalCostEnabled ? "Overrides calculated item costs." : "Only enabled if selected items have specific transport costs."}</p>
                  </div>
                  <div>
                    <label className="block text-sm font-semibold text-gray-700 mb-2">Additional Charges (Optional)</label>
                    <input type="number" value={additionalCharges} onChange={(e) => setAdditionalCharges(e.target.value)} placeholder="e.g. Labor, Toll fees..." className="w-full p-3 border rounded-lg" />
                    <p className="text-xs text-gray-500 mt-1">Added to the final total.</p>
                  </div>
                  {estimatedTotalCost !== null && (manualTotalCost || additionalCharges) && (
                    <div className="bg-gray-50 p-4 rounded-lg border border-gray-200 flex flex-col justify-center col-span-1 md:col-span-2">
                      <span className="text-sm text-gray-600">Standard Estimated Total Cost (Inc. Extras):</span>
                      <span className="text-xl font-bold text-gray-700">{formatNumber(estimatedTotalCost)} MMK</span>
                    </div>
                  )}
                </div>
              </div>
               <div className="flex gap-4 mb-6">
                  <button onClick={calculateCosts} disabled={isLoading} className="flex-1 flex items-center justify-center gap-2 px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition disabled:bg-gray-400"><Calculator size={20} /> {isLoading ? 'Calculating...' : 'Calculate Costs'}</button>
                  {calculatedTotalCost !== null && (<button onClick={() => handleSaveCalculation(false)} className="flex items-center justify-center gap-2 px-6 py-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition"><Save size={20} /> Save as New</button>)}
              </div>
              </>
            )}
        </div>
        {confirmDialog && <ConfirmDialog message={confirmDialog.message} onConfirm={confirmDialog.onConfirm} onCancel={confirmDialog.onCancel} />}
      </div>
    </div>
  );
};

export default PricingApp;