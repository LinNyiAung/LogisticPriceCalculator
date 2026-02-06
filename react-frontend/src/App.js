import React, { useState, useEffect } from 'react';
import { Trash2, Calculator, Database, FileText, Plus, Edit2, Download, Upload, X, History, Save, FileDown, LogOut, User, Users, Lock } from 'lucide-react';

const API_URL = 'http://localhost:8000';

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
            <label className="block text-gray-700 text-sm font-bold mb-2">Username</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full p-2 border rounded focus:outline-none focus:border-blue-500"
              placeholder="Enter username"
              required
            />
          </div>
          <div className="mb-6">
            <label className="block text-gray-700 text-sm font-bold mb-2">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full p-2 border rounded focus:outline-none focus:border-blue-500"
              placeholder="Enter password"
              required
            />
          </div>
          <button type="submit" className="w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700 transition font-semibold">
            Sign In
          </button>
        </form>
        <div className="mt-4 text-xs text-center text-gray-500">
          <p>Default Admin: admin / admin123</p>
          <p>Default Account: account / account123</p>
          <p>Default Logistic: logistic / log123</p>
        </div>
      </div>
    </div>
  );
};

// --- Main Application Component ---
const PricingApp = () => {
  // Auth State
  const [token, setToken] = useState(localStorage.getItem('token') || null);
  const [userRole, setUserRole] = useState(localStorage.getItem('userRole') || null);
  const [username, setUsername] = useState(localStorage.getItem('username') || '');

  // App State
  const [currentPage, setCurrentPage] = useState('calculator');
  const [pickIds, setPickIds] = useState([]);
  
  const [selectedPickIds, setSelectedPickIds] = useState([]);
  
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
  
  const [editingGate, setEditingGate] = useState(null);
  const [editingItem, setEditingItem] = useState(null);
  const [showAddGateModal, setShowAddGateModal] = useState(false);
  const [showAddItemModal, setShowAddItemModal] = useState(false);
  const [confirmDialog, setConfirmDialog] = useState(null);
  const [originalGateName, setOriginalGateName] = useState(null);
  const [originalItemCode, setOriginalItemCode] = useState(null);

  const [manualTotalCost, setManualTotalCost] = useState('');
  const [additionalCharges, setAdditionalCharges] = useState('');
  const [estimatedTotalCost, setEstimatedTotalCost] = useState(null);

  const [historyData, setHistoryData] = useState([]);
  
  // Changed: Removed showSaveModal state as we always save new
  const [currentHistoryId, setCurrentHistoryId] = useState(null);

  // User Management State
  const [usersList, setUsersList] = useState([]);
  const [showUserModal, setShowUserModal] = useState(false);
  const [editingUser, setEditingUser] = useState(null);

  // --- Auth Helpers ---

  const handleLogin = (data) => {
    setToken(data.access_token);
    setUserRole(data.role);
    setUsername(data.username);
    localStorage.setItem('token', data.access_token);
    localStorage.setItem('userRole', data.role);
    localStorage.setItem('username', data.username);
  };

  const handleLogout = () => {
    setToken(null);
    setUserRole(null);
    setUsername('');
    localStorage.removeItem('token');
    localStorage.removeItem('userRole');
    localStorage.removeItem('username');
    setCurrentPage('calculator');
  };

  const authFetch = async (url, options = {}) => {
    const headers = options.headers || {};
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    const updatedOptions = { ...options, headers };
    
    const response = await fetch(url, updatedOptions);
    
    if (response.status === 401) {
        handleLogout();
        throw new Error("Session expired. Please login again.");
    }
    return response;
  };

  // --- General Helpers ---

  const getErrorMessage = (error) => {
    if (!error?.detail) return 'An unknown error occurred';
    if (Array.isArray(error.detail)) {
        return error.detail.map(e => `${e.loc.slice(-1)}: ${e.msg}`).join(', ');
    }
    if (typeof error.detail === 'object') {
        return JSON.stringify(error.detail);
    }
    return String(error.detail);
  };

  const showNotification = (message, type = 'success') => {
    setNotification({ message, type });
    setTimeout(() => setNotification(null), 3000);
  };

  // --- Data Loading Functions ---

  const loadPickIds = async () => {
    try {
      const response = await authFetch(`${API_URL}/pick-ids`);
      if (response.ok) {
        const data = await response.json();
        setPickIds(data.pick_ids);
      }
    } catch (error) {
      showNotification(`Error loading pick IDs: ${error.message}`, 'error');
    }
  };

  const loadGates = async () => {
    try {
      const response = await authFetch(`${API_URL}/account/gates`);
      if (response.ok) {
        const data = await response.json();
        setGates(data.gates); 
        setGateData(data.gates);
      }
    } catch (error) {
      showNotification(`Error loading gates: ${error.message}`, 'error');
    }
  };

  const loadFromLocations = async () => {
    try {
      const response = await authFetch(`${API_URL}/locations/from`);
      if (response.ok) {
        const data = await response.json();
        setFromLocations(data.locations);
      }
    } catch (error) {
      showNotification(`Error loading locations: ${error.message}`, 'error');
    }
  };

  const loadToLocations = async (fromLoc) => {
    try {
      let url = `${API_URL}/locations/to`;
      if (fromLoc) {
        url += `?from_loc=${encodeURIComponent(fromLoc)}`;
      }
      const response = await authFetch(url);
      if (response.ok) {
        const data = await response.json();
        setToLocations(data.locations);
      }
    } catch (error) {
      showNotification(`Error loading destinations: ${error.message}`, 'error');
    }
  };

  const loadItemPricing = async (gateId) => {
    if (!gateId) return;
    try {
      const response = await authFetch(`${API_URL}/account/item-pricing/${gateId}`);
      if (response.ok) {
        const data = await response.json();
        setItemPricingData(data.items);
      }
    } catch (error) {
      showNotification(`Error loading items: ${error.message}`, 'error');
    }
  };

  const loadHistory = async () => {
    try {
      const response = await authFetch(`${API_URL}/history`);
      if (response.ok) {
        const data = await response.json();
        setHistoryData(data.history);
      }
    } catch (error) {
      showNotification(`Error loading history: ${error.message}`, 'error');
    }
  };

  const loadUsers = async () => {
    if (userRole !== 'admin') return;
    try {
        const response = await authFetch(`${API_URL}/users`);
        if (response.ok) {
            const data = await response.json();
            setUsersList(data);
        } else {
             const error = await response.json();
             showNotification(getErrorMessage(error), 'error');
        }
    } catch (error) {
        showNotification(`Error loading users: ${error.message}`, 'error');
    }
  }

  // --- Action Functions ---

  // Changed: isUpdate logic simplified to always false in usage
  const handleSaveCalculation = async (isUpdate = false) => {
    try {
      const payload = {
        // Force ID to null if we want to save as new (which is the new default behavior)
        id: isUpdate ? currentHistoryId : null,
        gate_name: selectedGate,
        from_loc: selectedFrom,
        to_loc: selectedTo,
        pick_ids: selectedPickIds,
        manual_total_cost: manualTotalCost ? parseFloat(manualTotalCost) : null,
        additional_charges: additionalCharges ? parseFloat(additionalCharges) : 0,
        final_total_cost: calculatedTotalCost
      };

      const response = await authFetch(`${API_URL}/history/save`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (response.ok) {
        // Changed message to reflect new behavior
        showNotification('Calculation saved as new record successfully', 'success');
        
        // We do not set currentHistoryId here, so further saves also create new records 
        // unless we reload the history list and pick the new one.
        // If you want to "stay" on the new record, the backend would need to return the new ID.
        // For now, this safely creates copies.
        loadHistory();
      } else {
        const error = await response.json();
        showNotification(getErrorMessage(error), 'error');
      }
    } catch (error) {
      showNotification(`Error: ${error.message}`, 'error');
    }
  };

  const handleSaveButtonClick = () => {
    // Changed: Always save as NEW.
    // passing false ensures payload.id is null, triggering an insert on backend.
    handleSaveCalculation(false);
  };

  const loadSavedCalculation = async (record) => {
    try {
      setCurrentPage('calculator');
      
      setCurrentHistoryId(record.id);

      setSelectedPickIds(record.pick_ids);
      await fetchAggregatedProducts(record.pick_ids);
      
      setSelectedFrom(record.from_loc);
      await loadToLocations(record.from_loc);
      
      setSelectedTo(record.to_loc);
      setSelectedGate(record.gate_name);
      
      setManualTotalCost(record.manual_total_cost || '');
      setAdditionalCharges(record.additional_charges || '');
      
      setCalculatedProducts([]); 
      setCalculatedTotalCost(record.final_total_cost);
      setEstimatedTotalCost(null);

      showNotification(`Loaded calculation record (ID: ${record.id}).`, 'info');
      
    } catch (error) {
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
        const a = document.createElement('a');
        a.href = url;
        
        const contentDisposition = response.headers.get('Content-Disposition');
        let filename = `Calculation_${record.id}.xlsx`;
        if (contentDisposition) {
          const filenameMatch = contentDisposition.match(/filename="?(.+)"?/i);
          if (filenameMatch) filename = filenameMatch[1];
        }
        
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        
        showNotification('History Excel file downloaded successfully', 'success');
      } else {
        const error = await response.json();
        showNotification(getErrorMessage(error), 'error');
      }
    } catch (error) {
      showNotification(`Error downloading file: ${error.message}`, 'error');
    }
  };

  const deleteHistory = async (id) => {
    if(!window.confirm("Are you sure you want to delete this saved calculation?")) return;
    
    try {
      const response = await authFetch(`${API_URL}/history/${id}`, { method: 'DELETE' });
      if (response.ok) {
        showNotification('Record deleted', 'success');
        loadHistory();
      } else {
         showNotification('Error deleting record', 'error');
      }
    } catch (error) {
      showNotification(`Error: ${error.message}`, 'error');
    }
  };

  const handleExportExcel = async () => {
    if (!selectedGateForPricing) {
      showNotification('Please select a gate first', 'error');
      return;
    }
    try {
      const response = await authFetch(`${API_URL}/account/item-pricing/export/${selectedGateForPricing}`);
      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        const contentDisposition = response.headers.get('Content-Disposition');
        let filename = 'item_costing.xlsx';
        if (contentDisposition) {
          const filenameMatch = contentDisposition.match(/filename="?(.+)"?/i);
          if (filenameMatch) filename = filenameMatch[1];
        }
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        showNotification('Excel file downloaded successfully', 'success');
      } else {
        const error = await response.json();
        showNotification(getErrorMessage(error), 'error');
      }
    } catch (error) {
      showNotification(`Error: ${error.message}`, 'error');
    }
  };

  const handleImportExcel = async (event) => {
    const file = event.target.files[0];
    if (!file) return;
    if (!selectedGateForPricing) {
      showNotification('Please select a gate first', 'error');
      event.target.value = '';
      return;
    }
    try {
      const formData = new FormData();
      formData.append('file', file);
      const response = await authFetch(`${API_URL}/account/item-pricing/import/${selectedGateForPricing}`, {
        method: 'POST',
        body: formData
      });
      if (response.ok) {
        const result = await response.json();
        showNotification(`Import successful! Updated: ${result.updates}, Added: ${result.inserts}, Deleted: ${result.deletes}`, 'success');
        await loadItemPricing(selectedGateForPricing);
      } else {
        const error = await response.json();
        showNotification(getErrorMessage(error), 'error');
      }
    } catch (error) {
      showNotification(`Error: ${error.message}`, 'error');
    } finally {
      event.target.value = '';
    }
  };

  const fetchAggregatedProducts = async (ids) => {
    if (ids.length === 0) {
      setProducts([]);
      setTotalWeight(0);
      return;
    }

    try {
      const queryString = ids.map(id => `pick_ids=${encodeURIComponent(id)}`).join('&');
      const response = await authFetch(`${API_URL}/products-by-ids?${queryString}`);
      
      if (response.ok) {
        const data = await response.json();
        setProducts(data.products);
        setTotalWeight(data.total_weight || 0);
      } else {
        showNotification('Failed to load products', 'error');
      }
    } catch (error) {
      showNotification(`Error: ${error.message}`, 'error');
    }
  };

  const handleAddPickId = (pickId) => {
    if (!pickId) return;
    
    if (selectedPickIds.includes(pickId)) {
      showNotification('Pick ID already selected', 'info');
      return;
    }

    const newSelection = [...selectedPickIds, pickId];
    setSelectedPickIds(newSelection);
    
    setSelectedFrom('');
    setSelectedTo('');
    setSelectedGate('');
    setCalculationType('');
    setCalculatedProducts([]);
    setCalculatedTotalCost(null);
    setEstimatedTotalCost(null);
    setManualTotalCost('');
    setAdditionalCharges('');

    fetchAggregatedProducts(newSelection);
  };

  const handleRemovePickId = (pickId) => {
    const newSelection = selectedPickIds.filter(id => id !== pickId);
    setSelectedPickIds(newSelection);
    
    setCalculatedProducts([]);
    setCalculatedTotalCost(null);
    setEstimatedTotalCost(null);
    
    fetchAggregatedProducts(newSelection);
  };

  const handleFromChange = (val) => {
    setSelectedFrom(val);
    setSelectedTo('');
    setSelectedGate('');
    setCalculatedProducts([]);
    setCalculatedTotalCost(null);
    setEstimatedTotalCost(null);
    setManualTotalCost('');
    
    if (val) {
      loadToLocations(val);
    } else {
      setToLocations([]);
    }
  };

  const handleToChange = (val) => {
    setSelectedTo(val);
    setSelectedGate('');
    setCalculatedProducts([]);
    setCalculatedTotalCost(null);
    setEstimatedTotalCost(null);
    setManualTotalCost('');
  };

  const handleGateChange = (gateName) => {
    setSelectedGate(gateName);
    setCalculatedProducts([]);
    setCalculatedTotalCost(null);
    setEstimatedTotalCost(null);
    setManualTotalCost('');
    
    const gateInfo = gates.find(g => g.gate_name === gateName);
    if (gateInfo) {
      setCalculationType(gateInfo.calculation_type);
    }
  };

  const calculateCosts = async () => {
    if (selectedPickIds.length === 0 || !selectedGate) {
      showNotification('Please select Pick ID(s), From, To, and Gate', 'error');
      return;
    }

    setIsLoading(true);
    try {
      let url = `${API_URL}/calculate-with-gate?gate_name=${encodeURIComponent(selectedGate)}`;
      
      selectedPickIds.forEach(id => {
        url += `&pick_ids=${encodeURIComponent(id)}`;
      });

      if (manualTotalCost) {
        url += `&manual_total_cost=${manualTotalCost}`;
      }
      if (additionalCharges) {
        url += `&additional_charges=${additionalCharges}`;
      }

      const response = await authFetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });

      if (response.ok) {
        const data = await response.json();
        setCalculatedProducts(data.calculated_products);
        setCalculatedTotalCost(data.total_cost);
        setEstimatedTotalCost(data.estimated_total_cost);
        showNotification('Calculation completed successfully', 'success');
      } else {
        const error = await response.json();
        showNotification(getErrorMessage(error), 'error');
      }
    } catch (error) {
      showNotification(`Error: ${error.message}`, 'error');
    } finally {
      setIsLoading(false);
    }
  };

  const saveGate = async (gateData) => {
    const hasUOM = gateData.uom && gateData.uom.trim().length > 0;
    const hasUnit = gateData.unit !== '' && gateData.unit !== null && gateData.unit !== undefined;
    const hasCost = gateData.cost !== '' && gateData.cost !== null && gateData.cost !== undefined;

    if ((hasUOM || hasUnit || hasCost) && !(hasUOM && hasUnit && hasCost)) {
      showNotification('Validation Error: UOM, Unit, and Cost must either ALL be filled or ALL be empty.', 'error');
      return;
    }

    try {
      const payload = {
        ...gateData,
        unit: gateData.unit === '' ? null : parseInt(gateData.unit),
        cost: gateData.cost === '' ? null : parseFloat(gateData.cost),
        original_gate_name: originalGateName
      };

      const response = await authFetch(`${API_URL}/account/gates`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (response.ok) {
        showNotification('Gate saved successfully', 'success');
        await loadGates();
        await loadFromLocations();
        setShowAddGateModal(false);
        setEditingGate(null);
        setOriginalGateName(null);
      } else {
        const error = await response.json();
        showNotification(getErrorMessage(error), 'error');
      }
    } catch (error) {
      showNotification(`Error: ${error.message}`, 'error');
    }
  };

  const deleteGate = async (gateId) => {
    setConfirmDialog({
      message: `Are you sure you want to delete this gate? All associated costs will also be deleted.`,
      onConfirm: async () => {
        try {
          const response = await authFetch(`${API_URL}/account/gates/${gateId}`, {
            method: 'DELETE'
          });
          if (response.ok) {
            showNotification('Gate deleted successfully', 'success');
            await loadGates();
            await loadFromLocations();
          } else {
            const error = await response.json();
            showNotification(getErrorMessage(error), 'error');
          }
        } catch (error) {
          showNotification(`Error: ${error.message}`, 'error');
        }
        setConfirmDialog(null);
      },
      onCancel: () => setConfirmDialog(null)
    });
  };

  const saveItem = async (itemData) => {
    try {
      const payload = {
        ...itemData,
        gate_id: selectedGateForPricing,
        original_item_code: originalItemCode || itemData.item_code
      };
      const response = await authFetch(`${API_URL}/account/item-pricing`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (response.ok) {
        showNotification('Item saved successfully', 'success');
        await loadItemPricing(selectedGateForPricing);
        setShowAddItemModal(false);
        setEditingItem(null);
        setOriginalItemCode(null);
      } else {
        const error = await response.json();
        showNotification(getErrorMessage(error), 'error');
      }
    } catch (error) {
      showNotification(`Error: ${error.message}`, 'error');
    }
  };

  const deleteItem = async (itemCode) => {
    setConfirmDialog({
      message: `Are you sure you want to delete item "${itemCode}"?`,
      onConfirm: async () => {
        try {
          const encodedItemCode = encodeURIComponent(itemCode);
          const response = await authFetch(`${API_URL}/account/item-pricing/${selectedGateForPricing}/${encodedItemCode}`, {
            method: 'DELETE'
          });
          if (response.ok) {
            showNotification('Item deleted successfully', 'success');
            await loadItemPricing(selectedGateForPricing);
          } else {
            const error = await response.json();
            showNotification(getErrorMessage(error), 'error');
          }
        } catch (error) {
          showNotification(`Error: ${error.message}`, 'error');
        }
        setConfirmDialog(null);
      },
      onCancel: () => setConfirmDialog(null)
    });
  };

  const saveUser = async (userData) => {
    try {
        let url = `${API_URL}/users`;
        let method = 'POST';
        
        // If editing, append username to URL and change method to PUT
        if (editingUser) {
            url += `/${editingUser.username}`;
            method = 'PUT';
        }
        
        const response = await authFetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(userData)
        });

        if (response.ok) {
            showNotification(editingUser ? 'User updated successfully' : 'User created successfully', 'success');
            await loadUsers();
            setShowUserModal(false);
            setEditingUser(null);
        } else {
            const error = await response.json();
            showNotification(getErrorMessage(error), 'error');
        }
    } catch (error) {
        showNotification(`Error: ${error.message}`, 'error');
    }
  };

  const deleteUser = async (username) => {
    if (username === userRole.username) return; 
    
    setConfirmDialog({
        message: `Are you sure you want to delete user "${username}"?`,
        onConfirm: async () => {
            try {
                const response = await authFetch(`${API_URL}/users/${username}`, { method: 'DELETE' });
                if (response.ok) {
                    showNotification('User deleted successfully', 'success');
                    await loadUsers();
                } else {
                    const error = await response.json();
                    showNotification(getErrorMessage(error), 'error');
                }
            } catch (error) {
                showNotification(`Error: ${error.message}`, 'error');
            }
            setConfirmDialog(null);
        },
        onCancel: () => setConfirmDialog(null)
    });
  };


  useEffect(() => {
    if (token) {
        loadPickIds();
        loadGates();
        loadFromLocations();
    }
  }, [token]);

  useEffect(() => {
    if (token && selectedGateForPricing) {
      loadItemPricing(selectedGateForPricing);
    } else {
      setItemPricingData([]);
    }
  }, [selectedGateForPricing, token]);

  useEffect(() => {
    if (token && currentPage === 'history') {
      loadHistory();
    }
    if (token && currentPage === 'users' && userRole === 'admin') {
        loadUsers();
    }
  }, [currentPage, token, userRole]);

  // --- Sub-Components ---

  const GateModal = ({ gate, onSave, onClose }) => {
    const [formData, setFormData] = useState(gate || {
      gate_name: '',
      from_loc: '',
      to_loc: '',
      uom: '',
      unit: '',
      cost: ''
    });

    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg p-6 w-full max-w-md">
          <h2 className="text-2xl font-bold mb-4">{gate ? 'Edit Gate' : 'Add New Gate'}</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-semibold mb-1">Gate Name</label>
              <input
                type="text"
                value={formData.gate_name ?? ''}
                onChange={(e) => setFormData({...formData, gate_name: e.target.value})}
                className="w-full p-2 border rounded"
              />
            </div>
            <div>
              <label className="block text-sm font-semibold mb-1">From</label>
              <input
                type="text"
                value={formData.from_loc ?? ''}
                onChange={(e) => setFormData({...formData, from_loc: e.target.value})}
                className="w-full p-2 border rounded"
                placeholder="e.g. YGN"
              />
            </div>
            <div>
              <label className="block text-sm font-semibold mb-1">To</label>
              <input
                type="text"
                value={formData.to_loc ?? ''}
                onChange={(e) => setFormData({...formData, to_loc: e.target.value})}
                className="w-full p-2 border rounded"
                placeholder="e.g. MDY"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-semibold mb-1">UOM</label>
                  <input
                    type="text"
                    value={formData.uom ?? ''}
                    onChange={(e) => setFormData({...formData, uom: e.target.value})}
                    className="w-full p-2 border rounded"
                    placeholder="e.g. Kg"
                  />
                </div>
                <div>
                  <label className="block text-sm font-semibold mb-1">Unit</label>
                  <input
                    type="number"
                    value={formData.unit ?? ''}
                    onChange={(e) => setFormData({...formData, unit: e.target.value})}
                    className="w-full p-2 border rounded"
                    placeholder="1"
                  />
                </div>
            </div>
            <div>
              <label className="block text-sm font-semibold mb-1">Cost</label>
              <input
                type="number"
                value={formData.cost ?? ''}
                onChange={(e) => setFormData({...formData, cost: e.target.value})}
                className="w-full p-2 border rounded"
              />
            </div>
          </div>
          <div className="flex gap-2 mt-6">
            <button
              onClick={() => onSave(formData)}
              className="flex-1 bg-blue-600 text-white py-2 rounded hover:bg-blue-700"
            >
              Save
            </button>
            <button
              onClick={onClose}
              className="flex-1 bg-gray-300 text-gray-700 py-2 rounded hover:bg-gray-400"
            >
              Cancel
            </button>
          </div>
        </div>
      </div>
    );
  };

  const ItemModal = ({ item, onSave, onClose }) => {
    const [formData, setFormData] = useState(item || {
      item_code: '',
      item_name: '',
      principal: '',
      brand: '',
      transportation_cost: 'Ton'
    });

    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg p-6 w-full max-w-2xl max-h-screen overflow-y-auto">
          <h2 className="text-2xl font-bold mb-4">{item ? 'Edit Item' : 'Add New Item'}</h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-semibold mb-1">Item Code</label>
              <input
                type="text"
                value={formData.item_code ?? ''}
                onChange={(e) => setFormData({...formData, item_code: e.target.value})}
                className="w-full p-2 border rounded"
                disabled={!!item}
              />
            </div>
            <div>
              <label className="block text-sm font-semibold mb-1">Item Name</label>
              <input
                type="text"
                value={formData.item_name ?? ''}
                onChange={(e) => setFormData({...formData, item_name: e.target.value})}
                className="w-full p-2 border rounded"
              />
            </div>
            <div>
              <label className="block text-sm font-semibold mb-1">Transportation Cost</label>
              <input
                type="text"
                value={formData.transportation_cost ?? ''}
                onChange={(e) => setFormData({...formData, transportation_cost: e.target.value})}
                className="w-full p-2 border rounded"
                placeholder="Ton or numeric value"
              />
            </div>
          </div>
          <div className="flex gap-2 mt-6">
            <button
              onClick={() => onSave(formData)}
              className="flex-1 bg-blue-600 text-white py-2 rounded hover:bg-blue-700"
            >
              Save
            </button>
            <button
              onClick={onClose}
              className="flex-1 bg-gray-300 text-gray-700 py-2 rounded hover:bg-gray-400"
            >
              Cancel
            </button>
          </div>
        </div>
      </div>
    );
  };

  const UserModal = ({ user, onSave, onClose }) => {
    const [formData, setFormData] = useState(user ? { ...user, password: '' } : {
        username: '',
        password: '',
        role: 'logistic' // default role
    });

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg p-6 w-full max-w-md">
                <h2 className="text-2xl font-bold mb-4">{user ? 'Edit User' : 'Add New User'}</h2>
                <div className="space-y-4">
                    <div>
                        <label className="block text-sm font-semibold mb-1">Username</label>
                        <input
                            type="text"
                            value={formData.username}
                            onChange={(e) => setFormData({...formData, username: e.target.value})}
                            className="w-full p-2 border rounded"
                            disabled={!!user} // Username cannot be changed
                        />
                    </div>
                    <div>
                        <label className="block text-sm font-semibold mb-1">Password</label>
                        <input
                            type="password"
                            value={formData.password}
                            onChange={(e) => setFormData({...formData, password: e.target.value})}
                            className="w-full p-2 border rounded"
                            placeholder={user ? "Leave blank to keep existing" : "Required"}
                        />
                    </div>
                    <div>
                        <label className="block text-sm font-semibold mb-1">Role</label>
                        <select
                            value={formData.role}
                            onChange={(e) => setFormData({...formData, role: e.target.value})}
                            className="w-full p-2 border rounded"
                        >
                            <option value="logistic">Logistic (Read Only)</option>
                            <option value="account">Account (Manage Gates/Items)</option>
                            <option value="admin">Admin (Full Access)</option>
                        </select>
                    </div>
                </div>
                <div className="flex gap-2 mt-6">
                    <button
                        onClick={() => onSave(formData)}
                        className="flex-1 bg-blue-600 text-white py-2 rounded hover:bg-blue-700"
                        disabled={!user && !formData.password}
                    >
                        Save
                    </button>
                    <button
                        onClick={onClose}
                        className="flex-1 bg-gray-300 text-gray-700 py-2 rounded hover:bg-gray-400"
                    >
                        Cancel
                    </button>
                </div>
            </div>
        </div>
    );
  };

  // Removed SaveModal as it's no longer used

  const ConfirmDialog = ({ message, onConfirm, onCancel }) => (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 w-full max-w-md">
        <h2 className="text-xl font-bold mb-4">Confirm Action</h2>
        <p className="text-gray-700 mb-6">{message}</p>
        <div className="flex gap-2">
          <button
            onClick={onConfirm}
            className="flex-1 bg-red-600 text-white py-2 rounded hover:bg-red-700"
          >
            Delete
          </button>
          <button
            onClick={onCancel}
            className="flex-1 bg-gray-300 text-gray-700 py-2 rounded hover:bg-gray-400"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );

  const renderNavigation = () => (
    <div className="bg-white shadow-md mb-6">
      <div className="max-w-6xl mx-auto px-6 py-4 flex justify-between items-center">
        <div className="flex gap-4">
          <button
            onClick={() => setCurrentPage('calculator')}
            className={`flex items-center gap-2 px-4 py-2 rounded transition ${
              currentPage === 'calculator' ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            }`}
          >
            <Calculator size={20} />
            Calculator
          </button>
          <button
            onClick={() => setCurrentPage('gates')}
            className={`flex items-center gap-2 px-4 py-2 rounded transition ${
              currentPage === 'gates' ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            }`}
          >
            <Database size={20} />
            Gates
          </button>
          <button
            onClick={() => setCurrentPage('items')}
            className={`flex items-center gap-2 px-4 py-2 rounded transition ${
              currentPage === 'items' ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            }`}
          >
            <FileText size={20} />
            Items
          </button>
          <button
            onClick={() => setCurrentPage('history')}
            className={`flex items-center gap-2 px-4 py-2 rounded transition ${
              currentPage === 'history' ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            }`}
          >
            <History size={20} />
            History
          </button>
          {userRole === 'admin' && (
              <button
                onClick={() => setCurrentPage('users')}
                className={`flex items-center gap-2 px-4 py-2 rounded transition ${
                  currentPage === 'users' ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                }`}
              >
                <Users size={20} />
                Users
              </button>
          )}
        </div>
        
        {/* User Info & Logout */}
        <div className="flex items-center gap-4">
            <div className="text-right">
                <p className="text-xs text-gray-500">Logged in as</p>
                <div className="flex items-center gap-1">
                    <User size={14} className="text-blue-600"/>
                    <p className="font-bold text-sm text-blue-600 capitalize">{username} ({userRole})</p>
                </div>
            </div>
            <button 
                onClick={handleLogout}
                className="text-gray-500 hover:text-red-500 transition p-2 hover:bg-red-50 rounded-full"
                title="Logout"
            >
                <LogOut size={20} />
            </button>
        </div>
      </div>
    </div>
  );

  // --- Auth Check ---
  if (!token) {
    return <LoginScreen onLogin={handleLogin} />;
  }

  // --- Views ---
  
  // 1. Users View (Admin Only)
  if (currentPage === 'users' && userRole === 'admin') {
      return (
        <div className="min-h-screen bg-gray-50 p-6">
            <div className="max-w-6xl mx-auto">
                {notification && (
                    <div className={`fixed top-4 right-4 px-6 py-3 rounded-lg shadow-lg ${
                    notification.type === 'success' ? 'bg-green-500' : 'bg-red-500'
                    } text-white z-50`}>
                    {notification.message}
                    </div>
                )}
                {renderNavigation()}
                <div className="bg-white rounded-lg shadow-md p-6">
                    <div className="flex items-center justify-between mb-6">
                        <h1 className="text-3xl font-bold text-gray-800">User Management</h1>
                        <button
                            onClick={() => {
                                setEditingUser(null);
                                setShowUserModal(true);
                            }}
                            className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition"
                        >
                            <Plus size={20} />
                            Add User
                        </button>
                    </div>
                    <div className="overflow-x-auto">
                        <table className="w-full border-collapse border">
                            <thead className="bg-gray-100">
                                <tr>
                                    <th className="border p-3 text-left">Username</th>
                                    <th className="border p-3 text-left">Role</th>
                                    <th className="border p-3 text-center">Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {usersList.map((u, index) => (
                                    <tr key={index} className="hover:bg-gray-50">
                                        <td className="border p-3 font-semibold text-gray-700">{u.username}</td>
                                        <td className="border p-3">
                                            <span className={`px-2 py-1 rounded text-xs font-bold uppercase ${
                                                u.role === 'admin' ? 'bg-red-100 text-red-700' :
                                                u.role === 'account' ? 'bg-blue-100 text-blue-700' :
                                                'bg-gray-100 text-gray-700'
                                            }`}>
                                                {u.role}
                                            </span>
                                        </td>
                                        <td className="border p-3 text-center">
                                            <div className="flex justify-center gap-2">
                                                <button
                                                    onClick={() => {
                                                        setEditingUser(u);
                                                        setShowUserModal(true);
                                                    }}
                                                    className="p-2 bg-blue-100 text-blue-600 rounded hover:bg-blue-200"
                                                    title="Edit User"
                                                >
                                                    <Edit2 size={16} />
                                                </button>
                                                {u.username !== username && (
                                                    <button
                                                        onClick={() => deleteUser(u.username)}
                                                        className="p-2 bg-red-100 text-red-600 rounded hover:bg-red-200"
                                                        title="Delete User"
                                                    >
                                                        <Trash2 size={16} />
                                                    </button>
                                                )}
                                                {u.username === username && (
                                                    <span className="p-2 text-gray-400 cursor-not-allowed" title="Cannot delete yourself">
                                                        <Lock size={16} />
                                                    </span>
                                                )}
                                            </div>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
            {showUserModal && (
                <UserModal
                    user={editingUser}
                    onSave={saveUser}
                    onClose={() => {
                        setShowUserModal(false);
                        setEditingUser(null);
                    }}
                />
            )}
            {confirmDialog && (
                <ConfirmDialog
                    message={confirmDialog.message}
                    onConfirm={confirmDialog.onConfirm}
                    onCancel={confirmDialog.onCancel}
                />
            )}
        </div>
      );
  }

  // 2. History View
  if (currentPage === 'history') {
    return (
      <div className="min-h-screen bg-gray-50 p-6">
        <div className="max-w-6xl mx-auto">
          {notification && (
            <div className={`fixed top-4 right-4 px-6 py-3 rounded-lg shadow-lg ${
              notification.type === 'success' ? 'bg-green-500' : 'bg-red-500'
            } text-white z-50`}>
              {notification.message}
            </div>
          )}
          {renderNavigation()}
          <div className="bg-white rounded-lg shadow-md p-6">
            <h1 className="text-3xl font-bold text-gray-800 mb-6">Calculation History</h1>
            <div className="overflow-x-auto">
              <table className="w-full border-collapse border">
                <thead className="bg-gray-100">
                  <tr>
                    <th className="border p-3 text-left">Date</th>
                    <th className="border p-3 text-left">Route</th>
                    <th className="border p-3 text-left">Pick IDs</th>
                    <th className="border p-3 text-right">Total Cost (MMK)</th>
                    <th className="border p-3 text-center">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {historyData.length === 0 ? (
                    <tr><td colSpan="5" className="text-center p-4 text-gray-500">No saved calculations found.</td></tr>
                  ) : (
                    historyData.map((record) => (
                      <tr key={record.id} className="hover:bg-gray-50">
                        <td className="border p-3 text-sm text-gray-600">{record.created_at}</td>
                        <td className="border p-3">
                          <span className="font-bold text-gray-700">{record.gate_name}</span> <br/>
                          <span className="text-xs text-gray-500">{record.from_loc} &rarr; {record.to_loc}</span>
                        </td>
                        <td className="border p-3 text-sm">
                          {record.pick_ids.length} ID(s): {record.pick_ids.join(', ')}
                        </td>
                        <td className="border p-3 text-right font-bold text-blue-600">
                          {record.final_total_cost?.toLocaleString()}
                        </td>
                        <td className="border p-3 text-center">
                          <div className="flex justify-center gap-2">
                            <button
                              onClick={() => handleDownloadHistoryExcel(record)}
                              className="px-3 py-1 bg-purple-100 text-purple-700 rounded hover:bg-purple-200 text-sm font-semibold flex items-center gap-1"
                              title="Download Excel"
                            >
                                <FileDown size={16} />
                            </button>
                            <button
                              onClick={() => loadSavedCalculation(record)}
                              className="px-3 py-1 bg-green-100 text-green-700 rounded hover:bg-green-200 text-sm font-semibold"
                            >
                              Load
                            </button>
                            {userRole === 'admin' && (
                                <button
                                    onClick={() => deleteHistory(record.id)}
                                    className="p-1 text-red-500 hover:bg-red-50 rounded"
                                    title="Delete Record"
                                >
                                    <Trash2 size={18} />
                                </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // 3. Gates View
  if (currentPage === 'gates') {
    const canEdit = ['account', 'admin'].includes(userRole);
    const canDelete = userRole === 'admin'; // Only admin can delete

    return (
      <div className="min-h-screen bg-gray-50 p-6">
        <div className="max-w-6xl mx-auto">
          {notification && (
            <div className={`fixed top-4 right-4 px-6 py-3 rounded-lg shadow-lg ${
              notification.type === 'success' ? 'bg-green-500' : 'bg-red-500'
            } text-white z-50`}>
              {notification.message}
            </div>
          )}
          {renderNavigation()}
          <div className="bg-white rounded-lg shadow-md p-6">
            <div className="flex items-center justify-between mb-6">
              <h1 className="text-3xl font-bold text-gray-800">Transportation Cost by Gate</h1>
              {canEdit && (
                <button
                  onClick={() => setShowAddGateModal(true)}
                  className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition"
                >
                  <Plus size={20} />
                  Add Gate
                </button>
              )}
            </div>
            <div className="overflow-x-auto">
              <table className="w-full border-collapse border">
                <thead className="bg-gray-100">
                  <tr>
                    <th className="border p-3 text-left">Gate Name</th>
                    <th className="border p-3 text-left">From</th>
                    <th className="border p-3 text-left">To</th>
                    <th className="border p-3 text-left">UOM</th>
                    <th className="border p-3 text-left">Unit</th>
                    <th className="border p-3 text-left">Cost</th>
                    <th className="border p-3 text-left">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {gateData.map((gate, index) => (
                    <tr key={index}>
                      <td className="border p-3">{gate.gate_name}</td>
                      <td className="border p-3">{gate.from_loc}</td>
                      <td className="border p-3">{gate.to_loc}</td>
                      <td className="border p-3">{gate.uom || '-'}</td>
                      <td className="border p-3">{gate.unit || '-'}</td>
                      <td className="border p-3">{gate.cost || '-'}</td>
                      <td className="border p-3">
                        {canEdit ? (
                            <div className="flex gap-2">
                                <button
                                    onClick={() => {
                                    setOriginalGateName(gate.gate_name);
                                    setEditingGate(gate);
                                    setShowAddGateModal(true);
                                    }}
                                    className="p-2 bg-blue-500 text-white rounded hover:bg-blue-600"
                                >
                                    <Edit2 size={16} />
                                </button>
                                {canDelete && (
                                    <button
                                        onClick={() => deleteGate(gate.gate_id)}
                                        className="p-2 bg-red-500 text-white rounded hover:bg-red-600"
                                    >
                                        <Trash2 size={16} />
                                    </button>
                                )}
                            </div>
                        ) : (
                            <span className="text-gray-400 text-sm">Read Only</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
          {showAddGateModal && (
            <GateModal
              gate={editingGate}
              onSave={saveGate}
              onClose={() => {
                setShowAddGateModal(false);
                setEditingGate(null);
                setOriginalGateName(null);
              }}
            />
          )}
          {confirmDialog && (
            <ConfirmDialog
              message={confirmDialog.message}
              onConfirm={confirmDialog.onConfirm}
              onCancel={confirmDialog.onCancel}
            />
          )}
        </div>
      </div>
    );
  }

  // 4. Items View
  if (currentPage === 'items') {
    const canEdit = ['account', 'admin'].includes(userRole);
    const canDelete = userRole === 'admin'; // Only admin can delete

    return (
      <div className="min-h-screen bg-gray-50 p-6">
        <div className="max-w-7xl mx-auto">
          {notification && (
            <div className={`fixed top-4 right-4 px-6 py-3 rounded-lg shadow-lg ${
              notification.type === 'success' ? 'bg-green-500' : 'bg-red-500'
            } text-white z-50`}>
              {notification.message}
            </div>
          )}
          {renderNavigation()}
          <div className="bg-white rounded-lg shadow-md p-6">
            <div className="flex items-center justify-between mb-6">
              <h1 className="text-3xl font-bold text-gray-800">Transportation Cost by Item</h1>
              <div className="flex gap-2">
                {selectedGateForPricing && (
                  <>
                    <button
                      onClick={handleExportExcel}
                      className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
                    >
                      <Download size={20} />
                      Download Excel
                    </button>
                    
                    {canEdit && (
                        <>
                            <label className="flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition cursor-pointer">
                            <Upload size={20} />
                            Upload Excel
                            <input
                                type="file"
                                accept=".xlsx,.xls"
                                onChange={handleImportExcel}
                                className="hidden"
                            />
                            </label>
                            <button
                            onClick={() => setShowAddItemModal(true)}
                            className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition"
                            >
                            <Plus size={20} />
                            Add Item
                            </button>
                        </>
                    )}
                  </>
                )}
              </div>
            </div>

            <div className="mb-6">
              <label className="block text-sm font-semibold mb-2">Select Gate</label>
              <select
                value={selectedGateForPricing}
                onChange={(e) => setSelectedGateForPricing(e.target.value)}
                className="w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-500"
              >
                <option value="">-- Select a Gate --</option>
                {gates.map((gate) => (
                  <option key={gate.gate_id} value={gate.gate_id}>
                    {gate.gate_name} ({gate.from_loc} &rarr; {gate.to_loc})
                  </option>
                ))}
              </select>
            </div>

            {selectedGateForPricing && (
              <div className="overflow-x-auto">
                <table className="w-full border-collapse border text-sm">
                  <thead className="bg-gray-100">
                    <tr>
                      <th className="border p-2 text-left">Item Code</th>
                      <th className="border p-2 text-left">Item Name</th>
                      <th className="border p-2 text-left">Transport Cost</th>
                      <th className="border p-2 text-left">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {itemPricingData.map((item, index) => (
                      <tr key={index}>
                        <td className="border p-2">{item.item_code}</td>
                        <td className="border p-2">{item.item_name}</td>
                        <td className="border p-2">{item.transportation_cost}</td>
                        <td className="border p-2">
                          {canEdit ? (
                            <div className="flex gap-2">
                                <button
                                    onClick={() => {
                                        setOriginalItemCode(item.item_code);
                                        setEditingItem(item);
                                        setShowAddItemModal(true);
                                    }}
                                    className="p-1 bg-blue-500 text-white rounded hover:bg-blue-600"
                                >
                                    <Edit2 size={14} />
                                </button>
                                {canDelete && (
                                    <button
                                        onClick={() => deleteItem(item.item_code)}
                                        className="p-1 bg-red-500 text-white rounded hover:bg-red-600"
                                    >
                                        <Trash2 size={14} />
                                    </button>
                                )}
                            </div>
                          ) : (
                             <span className="text-gray-400 text-xs">Read Only</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
          {showAddItemModal && (
            <ItemModal
              item={editingItem}
              onSave={saveItem}
              onClose={() => {
                setShowAddItemModal(false);
                setEditingItem(null);
                setOriginalItemCode(null);
              }}
            />
          )}
          {confirmDialog && (
            <ConfirmDialog
              message={confirmDialog.message}
              onConfirm={confirmDialog.onConfirm}
              onCancel={confirmDialog.onCancel}
            />
          )}
        </div>
      </div>
    );
  }

  // 5. Default: Calculator View
  const hasCalculated = calculatedProducts.length > 0;
  const tableData = hasCalculated ? calculatedProducts : products;

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-6xl mx-auto">
        {notification && (
          <div className={`fixed top-4 right-4 px-6 py-3 rounded-lg shadow-lg ${
            notification.type === 'success' ? 'bg-green-500' : 'bg-red-500'
          } text-white z-50`}>
            {notification.message}
          </div>
        )}
        {renderNavigation()}
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <h1 className="text-3xl font-bold text-gray-800 mb-6">Logistic Cost Calculator</h1>
          
          <div className="bg-white rounded-lg border p-6 mb-6">
            <h2 className="text-xl font-bold mb-4">Select Pick IDs</h2>
            
            <div className="mb-4">
               <select
                onChange={(e) => handleAddPickId(e.target.value)}
                value=""
                className="w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-500"
              >
                <option value="">-- Add a Pick ID --</option>
                {pickIds
                  .filter(id => !selectedPickIds.includes(id)) 
                  .map((pickId) => (
                    <option key={pickId} value={pickId}>{pickId}</option>
                  ))}
              </select>
            </div>

            <div className="flex flex-wrap gap-2">
              {selectedPickIds.length === 0 && (
                <p className="text-gray-500 text-sm italic">No Pick IDs selected</p>
              )}
              {selectedPickIds.map(id => (
                <div key={id} className="flex items-center gap-2 bg-blue-100 text-blue-800 px-3 py-1 rounded-full border border-blue-200">
                  <span className="font-semibold">{id}</span>
                  <button 
                    onClick={() => handleRemovePickId(id)}
                    className="hover:text-red-600 transition"
                  >
                    <X size={16} />
                  </button>
                </div>
              ))}
            </div>
          </div>
          
          {products.length > 0 && (
            <>
              <div className="bg-white rounded-lg border p-6 mb-6">
                <h2 className="text-xl font-bold mb-4">Select From</h2>
                <select
                  value={selectedFrom}
                  onChange={(e) => handleFromChange(e.target.value)}
                  className="w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">-- Select Origin --</option>
                  {fromLocations.map((loc) => (
                    <option key={loc} value={loc}>
                      {loc}
                    </option>
                  ))}
                </select>
              </div>

              {selectedFrom && (
                <div className="bg-white rounded-lg border p-6 mb-6">
                  <h2 className="text-xl font-bold mb-4">Select To</h2>
                  <select
                    value={selectedTo}
                    onChange={(e) => handleToChange(e.target.value)}
                    className="w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="">-- Select Destination --</option>
                    {toLocations.map((loc) => (
                      <option key={loc} value={loc}>
                        {loc}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              {selectedTo && (
                <div className="bg-white rounded-lg border p-6 mb-6">
                  <h2 className="text-xl font-bold mb-4">Select Gate</h2>
                  <select
                    value={selectedGate}
                    onChange={(e) => handleGateChange(e.target.value)}
                    className="w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="">-- Select a Gate --</option>
                    {gates
                      .filter(gate => gate.from_loc === selectedFrom && gate.to_loc === selectedTo)
                      .map((gate) => (
                        <option key={gate.gate_name} value={gate.gate_name}>
                          {gate.gate_name} - 
                          {gate.calculation_type === 'gate_pricing' ? ' Gate Pricing' : 
                           gate.calculation_type === 'direct_pricing' ? ' Direct Pricing' : ' Unknown'}
                        </option>
                      ))}
                  </select>
                </div>
              )}
            </>
          )}

          {selectedGate && (
              <div className="bg-blue-50 rounded-lg border-2 border-blue-300 p-6 mb-6">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-lg font-semibold text-gray-800">Calculation Type</h3>
                  <p className="text-gray-600 mt-1">
                    {calculationType === 'gate_pricing' ? 'Gate Pricing Calculation' : 
                     calculationType === 'direct_pricing' ? 'Direct Pricing Calculation' : 
                     'Unknown Type'}
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-sm text-gray-600">Route</p>
                  <p className="text-xl font-bold text-blue-600">{selectedFrom} &rarr; {selectedTo}</p>
                </div>
              </div>
            </div>
          )}

          {products.length > 0 && (
            <>
              <div className="bg-white rounded-lg border p-6 mb-6">
                <h2 className="text-xl font-bold mb-4">
                    {hasCalculated ? "Calculated Results" : "Product Details"}
                </h2>
                <div className="overflow-x-auto">
                  <table className="w-full border-collapse border">
                    <thead className="bg-gray-100">
                      <tr>
                        <th className="border p-2 text-left">Item Code</th>
                        <th className="border p-2 text-left">Description</th>
                        <th className="border p-2 text-left">Quantity</th>
                        <th className="border p-2 text-left">Weight</th>
                        {hasCalculated && (
                            <th className="border p-2 text-left">Cost (MMK)</th>
                        )}
                      </tr>
                    </thead>
                    <tbody>
                      {tableData.map((product, index) => (
                        <tr key={index}>
                          <td className="border p-2">{product.code}</td>
                          <td className="border p-2">{product.name}</td>
                          <td className="border p-2">{product.quantity}</td>
                          <td className="border p-2">{product.weight.toFixed(2)}</td>
                          {hasCalculated && (
                            <td className="border p-2 font-semibold">
                                {product.total_cost !== undefined ? product.total_cost.toFixed(2) : '-'}
                            </td>
                          )}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
              
              <div className="bg-gradient-to-r from-purple-50 to-purple-100 rounded-lg border-2 border-purple-300 p-6 mb-6">
                <div className="flex items-center justify-between">
                  <span className="text-lg font-semibold text-gray-700">Total Weight:</span>
                  <span className="text-3xl font-bold text-purple-600">{totalWeight.toFixed(2)}</span>
                </div>
              </div>
              <div className="bg-white rounded-lg border p-6 mb-6">
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <label className="block text-sm font-semibold text-gray-700 mb-2">Total Cost (Manual Override)</label>
                    <input
                      type="number"
                      value={manualTotalCost}
                      onChange={(e) => setManualTotalCost(e.target.value)}
                      placeholder="Enter base transport amount..."
                      className="w-full p-3 border rounded-lg"
                    />
                    <p className="text-xs text-gray-500 mt-1">Overrides calculated item costs.</p>
                  </div>
                  
                  <div>
                    <label className="block text-sm font-semibold text-gray-700 mb-2">Additional Charges (Optional)</label>
                    <input
                      type="number"
                      value={additionalCharges}
                      onChange={(e) => setAdditionalCharges(e.target.value)}
                      placeholder="e.g. Labor, Toll fees..."
                      className="w-full p-3 border rounded-lg"
                    />
                    <p className="text-xs text-gray-500 mt-1">Added to the final total.</p>
                  </div>

                  {estimatedTotalCost !== null && (manualTotalCost || additionalCharges) && (
                    <div className="bg-gray-50 p-4 rounded-lg border border-gray-200 flex flex-col justify-center col-span-1 md:col-span-2">
                      <span className="text-sm text-gray-600">Standard Estimated Total Cost (Inc. Extras):</span>
                      <span className="text-xl font-bold text-gray-700">
                        {estimatedTotalCost.toLocaleString()} MMK
                      </span>
                    </div>
                  )}
                </div>
              </div>

               <div className="flex gap-4 mb-6">
                  <button
                    onClick={calculateCosts}
                    disabled={isLoading}
                    className="flex-1 flex items-center justify-center gap-2 px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition disabled:bg-gray-400"
                  >
                    <Calculator size={20} />
                    {isLoading ? 'Calculating...' : 'Calculate Costs'}
                  </button>
                  
                  {calculatedTotalCost !== null && (
                    <button
                      onClick={handleSaveButtonClick}
                      className="flex items-center justify-center gap-2 px-6 py-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition"
                    >
                      <Save size={20} />
                      Save as New
                    </button>
                  )}
              </div>

              </>
            )}

             {calculatedTotalCost !== null && (
                <div className="bg-white rounded-lg border p-6">
                  <h2 className="text-xl font-bold mb-4">Total Summary</h2>
                   <div className="mt-4 p-4 bg-blue-50 rounded-lg">
                      <div className="flex flex-col gap-2 items-end">
                        {additionalCharges && (
                          <>
                            <div className="flex justify-between w-full md:w-1/3 text-gray-600">
                              <span>Subtotal (Transport):</span>
                              <span>{(calculatedTotalCost - (parseFloat(additionalCharges) || 0)).toFixed(2)} MMK</span>
                            </div>
                            <div className="flex justify-between w-full md:w-1/3 text-gray-600">
                              <span>Additional Charges:</span>
                              <span>{parseFloat(additionalCharges).toFixed(2)} MMK</span>
                            </div>
                            <div className="w-full md:w-1/3 border-b border-gray-300 my-1"></div>
                          </>
                        )}
                        
                        <div className="flex justify-between w-full md:w-1/3 items-center">
                          <span className="text-lg font-bold">Total Cost:</span>
                          <span className="text-2xl font-bold text-blue-600">
                            {calculatedTotalCost.toFixed(2)} MMK
                          </span>
                        </div>
                      </div>
                    </div>
                </div>
             )}
        </div>
        
        {confirmDialog && (
            <ConfirmDialog
              message={confirmDialog.message}
              onConfirm={confirmDialog.onConfirm}
              onCancel={confirmDialog.onCancel}
            />
        )}
      </div>
    </div>
  );
};

export default PricingApp;