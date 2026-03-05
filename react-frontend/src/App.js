import React, { useState, useEffect } from 'react';
import { Trash2, Calculator, Database, FileText, Plus, Edit2, Download, Upload, X, History, Save, FileDown, LogOut, User, Users, List as ListIcon, Search, Clock, CheckCircle } from 'lucide-react';

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
  const [docNums, setDocNums] = useState([]); 
  
  const [selectedDocNums, setSelectedDocNums] = useState([]); 
  // New state for Doc Num Search
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
  
  // Filter State for Items
  const [itemFilters, setItemFilters] = useState({
    item_code: '',
    item_name: '',
    principal: '',
    brand: '',
    transportation_cost: ''
  });

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

  // Filter State for History
  const [historyFilters, setHistoryFilters] = useState({
    id_status: '',
    date: '',
    route: '',
    doc_nums: '',
    total_cost: ''
  });

  // User Management State
  const [usersList, setUsersList] = useState([]);
  const [showUserModal, setShowUserModal] = useState(false);
  const [editingUser, setEditingUser] = useState(null);

  // Reference Management State
  const [refLocations, setRefLocations] = useState([]);
  const [refUOMs, setRefUOMs] = useState([]);
  const [refChannels, setRefChannels] = useState([]); 
  const [selectedChannel, setSelectedChannel] = useState(''); 
  const [newRefValue, setNewRefValue] = useState('');

  // Log Modal State
  const [showLogModal, setShowLogModal] = useState(false);
  const [logsData, setLogsData] = useState([]);
  const [currentLogGateName, setCurrentLogGateName] = useState('');

  // Item Log Modal State
  const [showItemLogModal, setShowItemLogModal] = useState(false);
  const [itemLogsData, setItemLogsData] = useState([]);
  const [currentLogItemName, setCurrentLogItemName] = useState('');

  // --- Formatting & UI Helpers ---
  const formatNumber = (num) => {
    if (num === null || num === undefined || num === '') return '-';
    if (isNaN(num)) return num;
    
    return Number(num).toLocaleString(undefined, { 
      minimumFractionDigits: 2, 
      maximumFractionDigits: 2 
    });
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
        return error.detail.map(e => {
            if (typeof e === 'string') return e;
            return `${e.loc ? e.loc.slice(-1) + ': ' : ''}${e.msg}`;
        }).join('\n');
    }
    if (typeof error.detail === 'object') {
        return JSON.stringify(error.detail);
    }
    return String(error.detail);
  };

  // --- Data Loading Functions ---
  const loadDocNums = async () => {
    try {
      const response = await authFetch(`${API_URL}/doc-nums`);
      if (response.ok) {
        const data = await response.json();
        setDocNums(data.doc_nums);
      }
    } catch (error) {
      showNotification(`Error loading Doc Nums: ${error.message}`, 'error');
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
      setItemFilters({
        item_code: '',
        item_name: '',
        principal: '',
        brand: '',
        transportation_cost: ''
      });
      
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
        }
    } catch (error) {
        showNotification(`Error loading users: ${error.message}`, 'error');
    }
  }

  const loadReferenceData = async () => {
      try {
          const locResp = await authFetch(`${API_URL}/references/locations`);
          if (locResp.ok) setRefLocations(await locResp.json());
          
          const uomResp = await authFetch(`${API_URL}/references/uoms`);
          if (uomResp.ok) setRefUOMs(await uomResp.json());

          const chanResp = await authFetch(`${API_URL}/references/channels`);
          if (chanResp.ok) setRefChannels(await chanResp.json());
      } catch (error) {
          showNotification('Error loading reference data', 'error');
      }
  }

  const addReference = async (type, value) => {
      if(!value.trim()) return;
      try {
          const response = await authFetch(`${API_URL}/references/${type}`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ name: value })
          });
          if(response.ok) {
              showNotification('Added successfully', 'success');
              setNewRefValue('');
              loadReferenceData();
          } else {
              const err = await response.json();
              showNotification(getErrorMessage(err), 'error');
          }
      } catch (error) {
          showNotification(`Error: ${error.message}`, 'error');
      }
  }

  const deleteReference = async (type, value) => {
      if(!window.confirm(`Delete ${value}?`)) return;
      try {
          const response = await authFetch(`${API_URL}/references/${type}/${value}`, {
              method: 'DELETE'
          });
          if(response.ok) {
              loadReferenceData();
          }
      } catch (error) {
           showNotification(`Error: ${error.message}`, 'error');
      }
  }

  const fetchGateLogs = async (gate) => {
      try {
          const response = await authFetch(`${API_URL}/account/gates/${gate.gate_id}/logs`);
          if(response.ok) {
              const data = await response.json();
              setLogsData(data);
              setCurrentLogGateName(gate.gate_name);
              setShowLogModal(true);
          } else {
              showNotification('Failed to fetch logs', 'error');
          }
      } catch (error) {
          showNotification(`Error: ${error.message}`, 'error');
      }
  };

  const fetchItemLogs = async (item) => {
    try {
        const response = await authFetch(`${API_URL}/account/items/${item.pricing_id}/logs`);
        if (response.ok) {
            const data = await response.json();
            setItemLogsData(data);
            setCurrentLogItemName(item.item_name);
            setShowItemLogModal(true);
        } else {
            showNotification('Failed to fetch logs', 'error');
        }
    } catch (error) {
        showNotification(`Error: ${error.message}`, 'error');
    }
  };

  // --- Action Functions ---

  const handleSaveCalculation = async (isUpdate = false) => {
    if (!selectedChannel) {
        showNotification('Channel is required to save.', 'error');
        return;
    }

    try {
      const payload = {
        id: isUpdate ? currentHistoryId : null,
        gate_name: selectedGate,
        from_loc: selectedFrom,
        to_loc: selectedTo,
        doc_nums: selectedDocNums.map(String),
        manual_total_cost: (manualTotalCost && isManualTotalCostEnabled) ? parseFloat(manualTotalCost) : null,
        additional_charges: additionalCharges ? parseFloat(additionalCharges) : 0,
        final_total_cost: calculatedTotalCost,
        channel: selectedChannel,
        status: "saved"
      };

      const response = await authFetch(`${API_URL}/history/save`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (response.ok) {
        showNotification('Calculation saved as new record successfully', 'success');
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
    handleSaveCalculation(false);
  };

  const handleSubmitHistory = async (id) => {
    if(!window.confirm("Are you sure you want to submit this calculation? Once submitted, account users will be able to review it.")) return;
    try {
      const response = await authFetch(`${API_URL}/history/${id}/submit`, { method: 'PUT' });
      if (response.ok) {
        showNotification('Calculation submitted successfully', 'success');
        loadHistory();
      } else {
         const err = await response.json();
         showNotification(getErrorMessage(err), 'error');
      }
    } catch (error) {
      showNotification(`Error: ${error.message}`, 'error');
    }
  };

  const handleClaimHistory = async (id) => {
    if(!window.confirm("Are you sure you want to claim this calculation?")) return;
    try {
      const response = await authFetch(`${API_URL}/history/${id}/claim`, { method: 'PUT' });
      if (response.ok) {
        showNotification('Calculation claimed successfully', 'success');
        loadHistory();
      } else {
         const err = await response.json();
         showNotification(getErrorMessage(err), 'error');
      }
    } catch (error) {
      showNotification(`Error: ${error.message}`, 'error');
    }
  };

  const loadSavedCalculation = async (record) => {
    try {
      setCurrentPage('calculator');
      setCurrentHistoryId(record.id);
      setSelectedDocNums(record.doc_nums); 
      await fetchAggregatedProducts(record.doc_nums);
      setSelectedFrom(record.from_loc);
      await loadToLocations(record.from_loc);
      setSelectedTo(record.to_loc);
      setSelectedGate(record.gate_name);
      setSelectedChannel(record.channel || '');
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
        if(Array.isArray(error.detail)) {
            const msg = error.detail.join('\n');
            alert(`Import Errors:\n${msg}`); 
        } else {
            showNotification(getErrorMessage(error), 'error');
        }
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
      const queryString = ids.map(id => `doc_nums=${encodeURIComponent(id)}`).join('&');
      const response = await authFetch(`${API_URL}/products-by-doc-nums?${queryString}`);
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

  const handleAddDocNum = (docNum) => {
    if (!docNum) return;
    if (selectedDocNums.includes(docNum)) {
      showNotification('Doc Num already selected', 'info');
      return;
    }
    const newSelection = [...selectedDocNums, docNum];
    setSelectedDocNums(newSelection);
    setSelectedFrom('');
    setSelectedTo('');
    setSelectedGate('');
    setSelectedChannel('');
    setCalculationType('');
    setCalculatedProducts([]);
    setCalculatedTotalCost(null);
    setEstimatedTotalCost(null);
    setManualTotalCost('');
    setAdditionalCharges('');
    fetchAggregatedProducts(newSelection);
  };

  const handleRemoveDocNum = (docNum) => {
    const newSelection = selectedDocNums.filter(id => id !== docNum);
    setSelectedDocNums(newSelection);
    setCalculatedProducts([]);
    setCalculatedTotalCost(null);
    setEstimatedTotalCost(null);
    fetchAggregatedProducts(newSelection);
  };

  const handleFromChange = (val) => {
    setSelectedFrom(val);
    setSelectedTo('');
    setSelectedGate('');
    setSelectedChannel('');
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
    setSelectedChannel('');
    setCalculatedProducts([]);
    setCalculatedTotalCost(null);
    setEstimatedTotalCost(null);
    setManualTotalCost('');
  };

  const handleGateChange = (gateName) => {
    setSelectedGate(gateName);
    setSelectedChannel('');
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
    if (selectedDocNums.length === 0 || !selectedFrom || !selectedTo || !selectedGate || !selectedChannel) {
      showNotification('Please select Doc Num(s), From, To, Gate, and Channel', 'error');
      return;
    }
    setIsLoading(true);
    try {
      let url = `${API_URL}/calculate-with-gate?gate_name=${encodeURIComponent(selectedGate)}`;
      selectedDocNums.forEach(id => {
        url += `&doc_nums=${encodeURIComponent(id)}`;
      });
      if (manualTotalCost && isManualTotalCostEnabled) {
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
        loadDocNums(); 
        loadGates();
        loadFromLocations();
        loadReferenceData();
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
    if (token && currentPage === 'references') {
        loadReferenceData();
    }
  }, [currentPage, token, userRole]);

  // EFFECT: Check if Manual Override should be enabled based on selected gate and products
  useEffect(() => {
    const checkManualCostStatus = async () => {
      // Only run on calculator view to prevent unnecessary fetches
      if (currentPage !== 'calculator' || !token) return;
      
      if (calculationType !== 'gate_pricing' || !selectedGate) {
        setIsManualTotalCostEnabled(false);
        return;
      }

      const gateInfo = gates.find(g => g.gate_name === selectedGate);
      if (!gateInfo) {
        setIsManualTotalCostEnabled(false);
        return;
      }

      try {
        const response = await authFetch(`${API_URL}/account/item-pricing/${gateInfo.gate_id}`);
        if (response.ok) {
          const data = await response.json();
          // Find if at least one product has a 'transportation_cost' configured in this gate
          const hasDirectPricingItem = products.some(p => {
            const pricing = data.items.find(item => item.item_code === p.code);
            if (!pricing) return false;
            const tc = String(pricing.transportation_cost || '').trim().toLowerCase();
            return tc !== '' && tc !== 'nan' && tc !== 'none' && tc !== 'null';
          });
          
          setIsManualTotalCostEnabled(hasDirectPricingItem);
        } else {
          setIsManualTotalCostEnabled(false);
        }
      } catch (err) {
        console.error("Failed to check item pricing for manual cost calculation", err);
        setIsManualTotalCostEnabled(false);
      }
    };

    checkManualCostStatus();
  }, [selectedGate, calculationType, products, gates, token, currentPage]);

  // --- Sub-Components ---
  const GateLogModal = ({ logs, gateName, onClose }) => {
    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg p-6 w-full max-w-4xl max-h-[80vh] overflow-hidden flex flex-col">
                <div className="flex justify-between items-center mb-4">
                    <h2 className="text-2xl font-bold">Change Log: {gateName}</h2>
                    <button onClick={onClose} className="text-gray-500 hover:text-gray-700">
                        <X size={24} />
                    </button>
                </div>
                <div className="overflow-y-auto flex-1 border rounded">
                    <table className="w-full border-collapse">
                        <thead className="bg-gray-100 sticky top-0">
                            <tr>
                                <th className="border p-3 text-left">Date</th>
                                <th className="border p-3 text-left">User</th>
                                <th className="border p-3 text-left">Field</th>
                                <th className="border p-3 text-left">Old Value</th>
                                <th className="border p-3 text-left">New Value</th>
                            </tr>
                        </thead>
                        <tbody>
                            {logs.length === 0 ? (
                                <tr>
                                    <td colSpan="5" className="p-4 text-center text-gray-500">No changes recorded.</td>
                                </tr>
                            ) : (
                                logs.map((log) => (
                                    <tr key={log.id} className="hover:bg-gray-50 text-sm">
                                        <td className="border p-3 whitespace-nowrap">{log.change_date}</td>
                                        <td className="border p-3">{log.changed_by}</td>
                                        <td className="border p-3 font-semibold">{log.field_name}</td>
                                        <td className="border p-3 text-red-600 bg-red-50">{log.old_value || '(empty)'}</td>
                                        <td className="border p-3 text-green-600 bg-green-50">{log.new_value || '(empty)'}</td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>
                <div className="mt-4 flex justify-end">
                    <button onClick={onClose} className="bg-gray-300 text-gray-700 px-4 py-2 rounded hover:bg-gray-400">Close</button>
                </div>
            </div>
        </div>
    );
  };

  const ItemLogModal = ({ logs, itemName, onClose }) => {
    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg p-6 w-full max-w-4xl max-h-[80vh] overflow-hidden flex flex-col">
                <div className="flex justify-between items-center mb-4">
                    <h2 className="text-2xl font-bold">Change Log: {itemName}</h2>
                    <button onClick={onClose} className="text-gray-500 hover:text-gray-700">
                        <X size={24} />
                    </button>
                </div>
                <div className="overflow-y-auto flex-1 border rounded">
                    <table className="w-full border-collapse">
                        <thead className="bg-gray-100 sticky top-0">
                            <tr>
                                <th className="border p-3 text-left">Date</th>
                                <th className="border p-3 text-left">User</th>
                                <th className="border p-3 text-left">Field</th>
                                <th className="border p-3 text-left">Old Value</th>
                                <th className="border p-3 text-left">New Value</th>
                            </tr>
                        </thead>
                        <tbody>
                            {logs.length === 0 ? (
                                <tr>
                                    <td colSpan="5" className="p-4 text-center text-gray-500">No changes recorded.</td>
                                </tr>
                            ) : (
                                logs.map((log) => (
                                    <tr key={log.id} className="hover:bg-gray-50 text-sm">
                                        <td className="border p-3 whitespace-nowrap">{log.change_date}</td>
                                        <td className="border p-3">{log.changed_by}</td>
                                        <td className="border p-3 font-semibold">{log.field_name}</td>
                                        <td className="border p-3 text-red-600 bg-red-50">{log.old_value || '(empty)'}</td>
                                        <td className="border p-3 text-green-600 bg-green-50">{log.new_value || '(empty)'}</td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>
                <div className="mt-4 flex justify-end">
                    <button onClick={onClose} className="bg-gray-300 text-gray-700 px-4 py-2 rounded hover:bg-gray-400">Close</button>
                </div>
            </div>
        </div>
    );
  };

  const GateModal = ({ gate, onSave, onClose }) => {
    const [formData, setFormData] = useState(gate || {
      gate_name: '', from_loc: '', to_loc: '', uom: '', unit: '', cost: ''
    });

    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg p-6 w-full max-w-md">
          <h2 className="text-2xl font-bold mb-4">{gate ? 'Edit Gate' : 'Add New Gate'}</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-semibold mb-1">Gate Name</label>
              <input type="text" value={formData.gate_name ?? ''} onChange={(e) => setFormData({...formData, gate_name: e.target.value})} className="w-full p-2 border rounded" />
            </div>
            <div>
              <label className="block text-sm font-semibold mb-1">From</label>
              <select value={formData.from_loc ?? ''} onChange={(e) => setFormData({...formData, from_loc: e.target.value})} className="w-full p-2 border rounded">
                  <option value="">-- Select --</option>
                  {refLocations.map((loc, i) => (<option key={i} value={loc}>{loc}</option>))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-semibold mb-1">To</label>
              <select value={formData.to_loc ?? ''} onChange={(e) => setFormData({...formData, to_loc: e.target.value})} className="w-full p-2 border rounded">
                  <option value="">-- Select --</option>
                  {refLocations.map((loc, i) => (<option key={i} value={loc}>{loc}</option>))}
              </select>
            </div>
            <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-semibold mb-1">UOM</label>
                  <select value={formData.uom ?? ''} onChange={(e) => setFormData({...formData, uom: e.target.value})} className="w-full p-2 border rounded">
                      <option value="">-- Select --</option>
                      {refUOMs.map((u, i) => (<option key={i} value={u}>{u}</option>))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-semibold mb-1">Unit</label>
                  <input type="number" value={formData.unit ?? ''} onChange={(e) => setFormData({...formData, unit: e.target.value})} className="w-full p-2 border rounded" placeholder="1" />
                </div>
            </div>
            <div>
              <label className="block text-sm font-semibold mb-1">Cost</label>
              <input type="number" value={formData.cost ?? ''} onChange={(e) => setFormData({...formData, cost: e.target.value})} className="w-full p-2 border rounded" />
            </div>
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
    const [formData, setFormData] = useState(item || {
      item_code: '', item_name: '', principal: '', brand: '', transportation_cost: '' 
    });
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
            if (response.ok) { const data = await response.json(); setSearchResults(data.items); }
        } catch (error) { console.error("Search failed", error); } finally { setIsSearching(false); }
    };

    const selectItem = (selectedItem) => {
        setFormData({
            ...formData, item_code: selectedItem.item_code, item_name: selectedItem.item_name,
            principal: selectedItem.principal || '', brand: selectedItem.brand || ''
        });
        setSearchTerm(selectedItem.item_code);
        setSearchResults([]); 
    };

    const handleSaveButton = async () => {
        if (!searchTerm) { showNotification("Item Code is required", "error"); return; }
        setIsValidating(true);
        try {
            const response = await authFetch(`${API_URL}/dwbi/items/validate?code=${encodeURIComponent(searchTerm)}`);
            if (response.ok) {
                const result = await response.json();
                if (result.valid) {
                    onSave({
                        ...formData, item_code: result.item.item_code, item_name: result.item.item_name,
                        principal: result.item.principal, brand: result.item.brand
                    });
                } else { showNotification("Invalid Item Code.", "error"); }
            } else { showNotification("Validation check failed.", "error"); }
        } catch (error) { showNotification("Network error", "error"); } finally { setIsValidating(false); }
    };

    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg p-6 w-full max-w-2xl max-h-screen overflow-y-auto">
          <h2 className="text-2xl font-bold mb-4">{item ? 'Edit Item' : 'Add New Item'}</h2>
          <div className="grid grid-cols-2 gap-4">
            <div className="relative">
              <label className="block text-sm font-semibold mb-1">Item Code (Search)</label>
              <div className="relative">
                <input type="text" value={searchTerm} onChange={(e) => handleSearch(e.target.value)} className="w-full p-2 border rounded pr-8" placeholder="Type code or name..." />
                <div className="absolute right-2 top-2 text-gray-400"><Search size={18} /></div>
              </div>
              {searchResults.length > 0 && (
                  <div className="absolute z-10 w-full bg-white border rounded shadow-lg max-h-48 overflow-y-auto mt-1">
                      {searchResults.map((res, idx) => (
                          <div key={idx} onClick={() => selectItem(res)} className="p-2 hover:bg-blue-50 cursor-pointer border-b last:border-0 text-sm">
                              <div className="font-bold text-gray-800">{res.item_code}</div>
                              <div className="text-gray-600 truncate">{res.item_name}</div>
                          </div>
                      ))}
                  </div>
              )}
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
    const [formData, setFormData] = useState(user ? { ...user, password: '' } : { username: '', password: '', role: 'logistic' });
    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg p-6 w-full max-w-md">
                <h2 className="text-2xl font-bold mb-4">{user ? 'Edit User' : 'Add New User'}</h2>
                <div className="space-y-4">
                    <div><label className="block text-sm font-semibold mb-1">Username</label><input type="text" value={formData.username} onChange={(e) => setFormData({...formData, username: e.target.value})} className="w-full p-2 border rounded" disabled={!!user} /></div>
                    <div><label className="block text-sm font-semibold mb-1">Password</label><input type="password" value={formData.password} onChange={(e) => setFormData({...formData, password: e.target.value})} className="w-full p-2 border rounded" placeholder={user ? "Leave blank to keep" : "Required"} /></div>
                    <div>
                        <label className="block text-sm font-semibold mb-1">Role</label>
                        <select value={formData.role} onChange={(e) => setFormData({...formData, role: e.target.value})} className="w-full p-2 border rounded">
                            <option value="logistic">Logistic (Read Only)</option>
                            <option value="account">Account (Manage Gates/Items)</option>
                            <option value="admin">Admin (Full Access)</option>
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

  const renderNavigation = () => (
    <div className="bg-white shadow-md mb-6">
      <div className="max-w-6xl mx-auto px-6 py-4 flex justify-between items-center">
        <div className="flex gap-4">
          <button onClick={() => setCurrentPage('calculator')} className={`flex items-center gap-2 px-4 py-2 rounded transition ${currentPage === 'calculator' ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'}`}><Calculator size={20} /> Calculator</button>
          <button onClick={() => setCurrentPage('gates')} className={`flex items-center gap-2 px-4 py-2 rounded transition ${currentPage === 'gates' ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'}`}><Database size={20} /> Gates</button>
          <button onClick={() => setCurrentPage('items')} className={`flex items-center gap-2 px-4 py-2 rounded transition ${currentPage === 'items' ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'}`}><FileText size={20} /> Items</button>
          <button onClick={() => setCurrentPage('history')} className={`flex items-center gap-2 px-4 py-2 rounded transition ${currentPage === 'history' ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'}`}><History size={20} /> History</button>
          {['admin', 'account'].includes(userRole) && (<button onClick={() => setCurrentPage('references')} className={`flex items-center gap-2 px-4 py-2 rounded transition ${currentPage === 'references' ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'}`}><ListIcon size={20} /> References</button>)}
          {userRole === 'admin' && (<button onClick={() => setCurrentPage('users')} className={`flex items-center gap-2 px-4 py-2 rounded transition ${currentPage === 'users' ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'}`}><Users size={20} /> Users</button>)}
        </div>
        <div className="flex items-center gap-4">
            <div className="text-right">
                <p className="text-xs text-gray-500">Logged in as</p>
                <div className="flex items-center gap-1"><User size={14} className="text-blue-600"/><p className="font-bold text-sm text-blue-600 capitalize">{username} ({userRole})</p></div>
            </div>
            <button onClick={handleLogout} className="text-gray-500 hover:text-red-500 transition p-2 hover:bg-red-50 rounded-full" title="Logout"><LogOut size={20} /></button>
        </div>
      </div>
    </div>
  );

  // --- Auth Check ---
  if (!token) return <LoginScreen onLogin={handleLogin} />;

  // --- Views ---

  if (currentPage === 'users' && userRole === 'admin') {
      return (
        <div className="min-h-screen bg-gray-50 p-6">
            <div className="max-w-6xl mx-auto">
                {notification && <div className={`fixed top-4 right-4 px-6 py-3 rounded-lg shadow-lg text-white z-50 ${getNotificationColor(notification.type)}`}>{notification.message}</div>}
                {renderNavigation()}
                <div className="bg-white rounded-lg shadow-md p-6">
                    <div className="flex items-center justify-between mb-6">
                        <h1 className="text-3xl font-bold text-gray-800">User Management</h1>
                        <button onClick={() => { setEditingUser(null); setShowUserModal(true); }} className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition"><Plus size={20} /> Add User</button>
                    </div>
                    <div className="overflow-x-auto">
                        <table className="w-full border-collapse border">
                            <thead className="bg-gray-100"><tr><th className="border p-3 text-left">Username</th><th className="border p-3 text-left">Role</th><th className="border p-3 text-center">Actions</th></tr></thead>
                            <tbody>{usersList.map((u, index) => (<tr key={index} className="hover:bg-gray-50"><td className="border p-3 font-semibold text-gray-700">{u.username}</td><td className="border p-3"><span className={`px-2 py-1 rounded text-xs font-bold uppercase ${u.role === 'admin' ? 'bg-red-100 text-red-700' : u.role === 'account' ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-700'}`}>{u.role}</span></td><td className="border p-3 text-center"><div className="flex justify-center gap-2"><button onClick={() => { setEditingUser(u); setShowUserModal(true); }} className="p-2 bg-blue-100 text-blue-600 rounded hover:bg-blue-200"><Edit2 size={16} /></button>{u.username !== username && (<button onClick={() => deleteUser(u.username)} className="p-2 bg-red-100 text-red-600 rounded hover:bg-red-200"><Trash2 size={16} /></button>)}</div></td></tr>))}</tbody>
                        </table>
                    </div>
                </div>
            </div>
            {showUserModal && <UserModal user={editingUser} onSave={saveUser} onClose={() => { setShowUserModal(false); setEditingUser(null); }} />}
            {confirmDialog && <ConfirmDialog message={confirmDialog.message} onConfirm={confirmDialog.onConfirm} onCancel={confirmDialog.onCancel} />}
        </div>
      );
  }

  if (currentPage === 'references' && ['admin', 'account'].includes(userRole)) {
      return (
        <div className="min-h-screen bg-gray-50 p-6">
            <div className="max-w-6xl mx-auto">
                {notification && <div className={`fixed top-4 right-4 px-6 py-3 rounded-lg shadow-lg text-white z-50 ${getNotificationColor(notification.type)}`}>{notification.message}</div>}
                {renderNavigation()}
                <h1 className="text-3xl font-bold text-gray-800 mb-6">Manage Reference Data</h1>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    <div className="bg-white rounded-lg shadow-md p-6">
                        <h2 className="text-xl font-bold mb-4 text-blue-700">Locations (From/To)</h2>
                        <div className="flex gap-2 mb-4"><input type="text" placeholder="New Location (e.g., NPT)" className="border p-2 rounded flex-1" id="new-loc" /><button onClick={() => { const val = document.getElementById('new-loc').value; addReference('locations', val); document.getElementById('new-loc').value = ''; }} className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700">Add</button></div>
                        <div className="border rounded max-h-96 overflow-y-auto">{refLocations.map((loc, i) => (<div key={i} className="flex justify-between items-center p-3 border-b last:border-0 hover:bg-gray-50"><span>{loc}</span><button onClick={() => deleteReference('locations', loc)} className="text-red-500 hover:text-red-700"><X size={18} /></button></div>))}</div>
                    </div>
                    <div className="bg-white rounded-lg shadow-md p-6">
                        <h2 className="text-xl font-bold mb-4 text-purple-700">Units of Measure (UOM)</h2>
                        <div className="flex gap-2 mb-4"><input type="text" placeholder="New UOM (e.g., Box)" className="border p-2 rounded flex-1" id="new-uom" /><button onClick={() => { const val = document.getElementById('new-uom').value; addReference('uoms', val); document.getElementById('new-uom').value = ''; }} className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700">Add</button></div>
                        <div className="border rounded max-h-96 overflow-y-auto">{refUOMs.map((u, i) => (<div key={i} className="flex justify-between items-center p-3 border-b last:border-0 hover:bg-gray-50"><span>{u}</span><button onClick={() => deleteReference('uoms', u)} className="text-red-500 hover:text-red-700"><X size={18} /></button></div>))}</div>
                    </div>
                    <div className="bg-white rounded-lg shadow-md p-6">
                        <h2 className="text-xl font-bold mb-4 text-orange-700">Channels</h2>
                        <div className="flex gap-2 mb-4"><input type="text" placeholder="New Channel (e.g., SD)" className="border p-2 rounded flex-1" id="new-chan" /><button onClick={() => { const val = document.getElementById('new-chan').value; addReference('channels', val); document.getElementById('new-chan').value = ''; }} className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700">Add</button></div>
                        <div className="border rounded max-h-96 overflow-y-auto">{refChannels.map((c, i) => (<div key={i} className="flex justify-between items-center p-3 border-b last:border-0 hover:bg-gray-50"><span>{c}</span><button onClick={() => deleteReference('channels', c)} className="text-red-500 hover:text-red-700"><X size={18} /></button></div>))}</div>
                    </div>
                </div>
            </div>
        </div>
      );
  }

  if (currentPage === 'history') {
    const filteredHistory = historyData.filter(record => {
      const matchIdStatus = (String(record.id) + ' ' + (record.status || '')).toLowerCase().includes(historyFilters.id_status.toLowerCase());
      const matchDate = (record.created_at || '').toLowerCase().includes(historyFilters.date.toLowerCase());
      const matchRoute = ((record.gate_name || '') + ' ' + (record.from_loc || '') + ' ' + (record.to_loc || '')).toLowerCase().includes(historyFilters.route.toLowerCase());
      const matchDocNums = (record.doc_nums ? record.doc_nums.join(', ') : '').toLowerCase().includes(historyFilters.doc_nums.toLowerCase());
      const matchTotalCost = (String(record.final_total_cost) || '').toLowerCase().includes(historyFilters.total_cost.toLowerCase());
      return matchIdStatus && matchDate && matchRoute && matchDocNums && matchTotalCost;
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
                    <th className="border p-2 text-left">
                      <div>ID / Status</div>
                      <input type="text" placeholder="Filter..." className="w-full mt-1 p-1 border rounded text-xs font-normal" value={historyFilters.id_status} onChange={(e) => setHistoryFilters({...historyFilters, id_status: e.target.value})} />
                    </th>
                    <th className="border p-2 text-left">
                      <div>Date</div>
                      <input type="text" placeholder="Filter..." className="w-full mt-1 p-1 border rounded text-xs font-normal" value={historyFilters.date} onChange={(e) => setHistoryFilters({...historyFilters, date: e.target.value})} />
                    </th>
                    <th className="border p-2 text-left">
                      <div>Route</div>
                      <input type="text" placeholder="Filter..." className="w-full mt-1 p-1 border rounded text-xs font-normal" value={historyFilters.route} onChange={(e) => setHistoryFilters({...historyFilters, route: e.target.value})} />
                    </th>
                    <th className="border p-2 text-left">
                      <div>Doc Nums</div>
                      <input type="text" placeholder="Filter..." className="w-full mt-1 p-1 border rounded text-xs font-normal" value={historyFilters.doc_nums} onChange={(e) => setHistoryFilters({...historyFilters, doc_nums: e.target.value})} />
                    </th>
                    <th className="border p-2 text-right">
                      <div>Total Cost (MMK)</div>
                      <input type="text" placeholder="Filter..." className="w-full mt-1 p-1 border rounded text-xs font-normal text-right" value={historyFilters.total_cost} onChange={(e) => setHistoryFilters({...historyFilters, total_cost: e.target.value})} />
                    </th>
                    <th className="border p-2 text-center align-top">Actions</th>
                  </tr>
                </thead>
                <tbody>{filteredHistory.length === 0 ? (<tr><td colSpan="6" className="text-center p-4 text-gray-500">No matching calculations found.</td></tr>) : (filteredHistory.map((record) => (
                    <tr key={record.id} className="hover:bg-gray-50">
                        <td className="border p-3">
                            <span className="text-sm text-gray-600 font-bold block mb-1">#{record.id}</span>
                            <span className={`px-2 py-1 rounded text-xs font-bold uppercase ${record.status === 'claimed' ? 'bg-blue-100 text-blue-700' : record.status === 'submitted' ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'}`}>{record.status}</span>
                        </td>
                        <td className="border p-3 text-sm text-gray-600">
                            <div className="font-semibold">{record.created_at}</div>
                        </td>
                        <td className="border p-3"><span className="font-bold text-gray-700">{record.gate_name}</span> <br/><span className="text-xs text-gray-500">{record.from_loc} &rarr; {record.to_loc}</span></td>
                        <td className="border p-3 text-sm">{record.doc_nums.length} Doc(s): {record.doc_nums.join(', ')}</td>
                        <td className="border p-3 text-right font-bold text-blue-600">{formatNumber(record.final_total_cost)}</td>
                        <td className="border p-3 text-center">
                            <div className="flex justify-center gap-2">
                                <button onClick={() => handleDownloadHistoryExcel(record)} className="px-3 py-1 bg-purple-100 text-purple-700 rounded hover:bg-purple-200 text-sm font-semibold flex items-center gap-1"><FileDown size={16} /></button>
                                <button onClick={() => loadSavedCalculation(record)} className="px-3 py-1 bg-green-100 text-green-700 rounded hover:bg-green-200 text-sm font-semibold">Load</button>
                                {userRole === 'logistic' && record.status === 'saved' && (
                                    <button onClick={() => handleSubmitHistory(record.id)} className="px-3 py-1 bg-blue-100 text-blue-700 rounded hover:bg-blue-200 text-sm font-semibold flex items-center gap-1" title="Submit Calculation"><CheckCircle size={16} /> Submit</button>
                                )}
                                {userRole === 'account' && record.status === 'submitted' && (
                                    <button onClick={() => handleClaimHistory(record.id)} className="px-3 py-1 bg-indigo-100 text-indigo-700 rounded hover:bg-indigo-200 text-sm font-semibold flex items-center gap-1" title="Claim Calculation"><CheckCircle size={16} /> Claim</button>
                                )}
                                {userRole === 'admin' && (<button onClick={() => deleteHistory(record.id)} className="p-1 text-red-500 hover:bg-red-50 rounded"><Trash2 size={18} /></button>)}
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

  if (currentPage === 'gates') {
    const canEdit = ['account', 'admin'].includes(userRole);
    const canDelete = userRole === 'admin'; 
    return (
      <div className="min-h-screen bg-gray-50 p-6">
        <div className="max-w-6xl mx-auto">
          {notification && <div className={`fixed top-4 right-4 px-6 py-3 rounded-lg shadow-lg text-white z-50 ${getNotificationColor(notification.type)}`}>{notification.message}</div>}
          {renderNavigation()}
          <div className="bg-white rounded-lg shadow-md p-6">
            <div className="flex items-center justify-between mb-6">
              <h1 className="text-3xl font-bold text-gray-800">Transportation Cost by Gate</h1>
              {canEdit && (<button onClick={() => setShowAddGateModal(true)} className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition"><Plus size={20} /> Add Gate</button>)}
            </div>
            <div className="overflow-x-auto">
              <table className="w-full border-collapse border">
                <thead className="bg-gray-100"><tr><th className="border p-3 text-left">Gate Name</th><th className="border p-3 text-left">From</th><th className="border p-3 text-left">To</th><th className="border p-3 text-left">UOM</th><th className="border p-3 text-left">Unit</th><th className="border p-3 text-left">Cost</th><th className="border p-3 text-center">Actions</th></tr></thead>
                <tbody>{gateData.map((gate, index) => (<tr key={index}><td className="border p-3">{gate.gate_name}</td><td className="border p-3">{gate.from_loc}</td><td className="border p-3">{gate.to_loc}</td><td className="border p-3">{gate.uom || '-'}</td><td className="border p-3">{gate.unit || '-'}</td><td className="border p-3">{formatNumber(gate.cost)}</td><td className="border p-3 text-center"><div className="flex items-center justify-center gap-2"><button onClick={() => fetchGateLogs(gate)} className="p-2 bg-gray-100 text-gray-600 rounded hover:bg-gray-200" title="View Change Logs"><Clock size={16} /></button>{canEdit ? (<><button onClick={() => { setOriginalGateName(gate.gate_name); setEditingGate(gate); setShowAddGateModal(true); }} className="p-2 bg-blue-500 text-white rounded hover:bg-blue-600"><Edit2 size={16} /></button>{canDelete && (<button onClick={() => deleteGate(gate.gate_id)} className="p-2 bg-red-500 text-white rounded hover:bg-red-600"><Trash2 size={16} /></button>)}</>) : (<span className="text-gray-400 text-sm ml-2">Read Only</span>)}</div></td></tr>))}</tbody>
              </table>
            </div>
          </div>
          {showAddGateModal && <GateModal gate={editingGate} onSave={saveGate} onClose={() => { setShowAddGateModal(false); setEditingGate(null); setOriginalGateName(null); }} />}
          {showLogModal && <GateLogModal logs={logsData} gateName={currentLogGateName} onClose={() => setShowLogModal(false)} />}
          {confirmDialog && <ConfirmDialog message={confirmDialog.message} onConfirm={confirmDialog.onConfirm} onCancel={confirmDialog.onCancel} />}
        </div>
      </div>
    );
  }

  if (currentPage === 'items') {
    const canEdit = ['account', 'admin'].includes(userRole);
    const canDelete = userRole === 'admin'; 
    
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
                    {canEdit && (<><label className="flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition cursor-pointer"><Upload size={20} /> Upload Excel <input type="file" accept=".xlsx,.xls" onChange={handleImportExcel} className="hidden" /></label><button onClick={() => setShowAddItemModal(true)} className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition"><Plus size={20} /> Add Item</button></>)}
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
                                {canEdit && (<><button onClick={() => { setOriginalItemCode(item.item_code); setEditingItem(item); setShowAddItemModal(true); }} className="p-1 bg-blue-500 text-white rounded hover:bg-blue-600"><Edit2 size={14} /></button>{canDelete && (<button onClick={() => deleteItem(item.item_code)} className="p-1 bg-red-500 text-white rounded hover:bg-red-600"><Trash2 size={14} /></button>)}</>)}
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
          {showItemLogModal && <ItemLogModal logs={itemLogsData} itemName={currentLogItemName} onClose={() => setShowItemLogModal(false)} />}
          {confirmDialog && <ConfirmDialog message={confirmDialog.message} onConfirm={confirmDialog.onConfirm} onCancel={confirmDialog.onCancel} />}
        </div>
      </div>
    );
  }

  // Calculator View (Default)
  const hasCalculated = calculatedProducts.length > 0;
  const rawTableData = hasCalculated ? calculatedProducts : products;

  // Aggregate items by item code for the frontend UI view only
  const tableData = Object.values(rawTableData.reduce((acc, curr) => {
    if (!acc[curr.code]) {
      acc[curr.code] = { ...curr };
    } else {
      acc[curr.code].ctns = (acc[curr.code].ctns || 0) + (curr.ctns || 0);
      acc[curr.code].weight += curr.weight || 0;
      if (curr.total_cost !== undefined) {
        acc[curr.code].total_cost = (acc[curr.code].total_cost || 0) + curr.total_cost;
      }
    }
    return acc;
  }, {})).sort((a, b) => a.code.localeCompare(b.code));

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-6xl mx-auto">
        {notification && <div className={`fixed top-4 right-4 px-6 py-3 rounded-lg shadow-lg text-white z-50 ${getNotificationColor(notification.type)}`}>{notification.message}</div>}
        {renderNavigation()}
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <h1 className="text-3xl font-bold text-gray-800 mb-6">Logistic Cost Calculator</h1>
          <div className="bg-white rounded-lg border p-6 mb-6">
            <h2 className="text-xl font-bold mb-4">Select Doc Nums (Transfer IDs) <span className="text-red-500">*</span></h2>
            
            {/* --- REPLACED <select> WITH CUSTOM SEARCHABLE DROPDOWN --- */}
            <div className="relative mb-4">
              <div className="relative">
                <input
                  type="text"
                  placeholder="Search and add a Doc Num (e.g. 22#####)..."
                  value={docNumSearchTerm}
                  onChange={(e) => {
                    setDocNumSearchTerm(e.target.value);
                    setShowDocNumDropdown(true);
                  }}
                  onFocus={() => setShowDocNumDropdown(true)}
                  onBlur={() => setTimeout(() => setShowDocNumDropdown(false), 200)}
                  className="w-full p-3 pl-10 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
                />
                <div className="absolute left-3 top-3 text-gray-400">
                  <Search size={20} />
                </div>
              </div>
              
              {showDocNumDropdown && (
                <div className="absolute z-10 w-full mt-1 bg-white border rounded-lg shadow-xl max-h-60 overflow-y-auto">
                  {docNums
                    .filter(doc => !selectedDocNums.includes(doc.doc_num))
                    .filter(doc => {
                      const searchStr = `${doc.doc_num} ${doc.doc_date || ''}`.toLowerCase();
                      return searchStr.includes(docNumSearchTerm.toLowerCase());
                    })
                    .map((doc) => (
                      <div
                        key={doc.doc_num}
                        className="p-3 hover:bg-blue-50 cursor-pointer border-b last:border-0"
                        onMouseDown={(e) => {
                          e.preventDefault(); // Prevents input from losing focus
                          handleAddDocNum(doc.doc_num);
                          setDocNumSearchTerm('');
                          setShowDocNumDropdown(false);
                        }}
                      >
                        <span className="font-semibold text-gray-800">{doc.doc_num}</span>
                        {doc.doc_date && <span className="text-gray-500 ml-2">- {doc.doc_date}</span>}
                      </div>
                    ))}
                  {docNums.filter(doc => !selectedDocNums.includes(doc.doc_num) && `${doc.doc_num} ${doc.doc_date || ''}`.toLowerCase().includes(docNumSearchTerm.toLowerCase())).length === 0 && (
                    <div className="p-3 text-gray-500 italic">No matching Doc Nums found.</div>
                  )}
                </div>
              )}
            </div>
            {/* --- END CUSTOM DROPDOWN --- */}

            <div className="flex flex-wrap gap-2">
              {selectedDocNums.length === 0 && (<p className="text-gray-500 text-sm italic">No Doc Nums selected</p>)}
              {selectedDocNums.map(id => {
                const docObj = docNums.find(d => d.doc_num === id);
                const displayLabel = docObj && docObj.doc_date ? `${id} - ${docObj.doc_date}` : id;
                return (
                  <div key={id} className="flex items-center gap-2 bg-blue-100 text-blue-800 px-3 py-1 rounded-full border border-blue-200">
                    <span className="font-semibold">{displayLabel}</span>
                    <button onClick={() => handleRemoveDocNum(id)} className="hover:text-red-600 transition"><X size={16} /></button>
                  </div>
                );
              })}
            </div>
          </div>
          
          {products.length > 0 && (
            <>
              <div className="bg-white rounded-lg border p-6 mb-6">
                <h2 className="text-xl font-bold mb-4">Select From <span className="text-red-500">*</span></h2>
                <select value={selectedFrom} onChange={(e) => handleFromChange(e.target.value)} className="w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-500">
                  <option value="">-- Select Origin --</option>
                  {fromLocations.map((loc) => (<option key={loc} value={loc}>{loc}</option>))}
                </select>
              </div>
              {selectedFrom && (
                <div className="bg-white rounded-lg border p-6 mb-6">
                  <h2 className="text-xl font-bold mb-4">Select To <span className="text-red-500">*</span></h2>
                  <select value={selectedTo} onChange={(e) => handleToChange(e.target.value)} className="w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-500">
                    <option value="">-- Select Destination --</option>
                    {toLocations.map((loc) => (<option key={loc} value={loc}>{loc}</option>))}
                  </select>
                </div>
              )}
              {selectedTo && (
                <div className="bg-white rounded-lg border p-6 mb-6">
                  <h2 className="text-xl font-bold mb-4">Select Gate <span className="text-red-500">*</span></h2>
                  <select value={selectedGate} onChange={(e) => handleGateChange(e.target.value)} className="w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-500">
                    <option value="">-- Select a Gate --</option>
                    {gates.filter(gate => gate.from_loc === selectedFrom && gate.to_loc === selectedTo).map((gate) => (<option key={gate.gate_name} value={gate.gate_name}>{gate.gate_name} - {gate.calculation_type === 'gate_pricing' ? ' Gate Pricing' : gate.calculation_type === 'direct_pricing' ? ' Direct Pricing' : ' Unknown'}</option>))}
                  </select>
                </div>
              )}
              {selectedGate && (
                <div className="bg-white rounded-lg border p-6 mb-6">
                  <h2 className="text-xl font-bold mb-4">Select Channel <span className="text-red-500">*</span></h2>
                  <select value={selectedChannel} onChange={(e) => setSelectedChannel(e.target.value)} className="w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-500">
                    <option value="">-- Select a Channel --</option>
                    {refChannels.map((chan, i) => (<option key={i} value={chan}>{chan}</option>))}
                  </select>
                </div>
              )}
            </>
          )}

          {selectedGate && (() => {
            const currentGate = gates.find(g => g.gate_name === selectedGate);
            return (
              <div className="bg-blue-50 rounded-lg border-2 border-blue-300 p-6 mb-6">
                <div className="flex items-center justify-between flex-wrap gap-4">
                  <div>
                    <h3 className="text-lg font-semibold text-gray-800">Calculation Type</h3>
                    <p className="text-gray-600 mt-1">
                      {calculationType === 'gate_pricing' ? 'Gate Pricing Calculation' : calculationType === 'direct_pricing' ? 'Direct Pricing Calculation' : 'Unknown Type'}
                    </p>
                  </div>
                  
                  {currentGate && currentGate.cost !== null && (
                    <div className="text-center">
                      <p className="text-sm text-gray-600">Gate Cost</p>
                      <p className="text-xl font-bold text-green-600">
                        {formatNumber(currentGate.cost)} MMK 
                        {currentGate.uom && <span className="text-sm font-medium text-gray-500 ml-1">/ {currentGate.unit || 1} {currentGate.uom}</span>}
                      </p>
                    </div>
                  )}

                  <div className="text-right">
                    <p className="text-sm text-gray-600">Route</p>
                    <p className="text-xl font-bold text-blue-600">{selectedFrom} &rarr; {selectedTo}</p>
                  </div>
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
                        <th className="border p-2 text-left">Item Code</th>
                        <th className="border p-2 text-left">Description</th>
                        <th className="border p-2 text-left">Cartons</th>
                        <th className="border p-2 text-left">Weight</th>
                        <th className="border p-2 text-left">UOM</th>
                        {hasCalculated && (<th className="border p-2 text-left">Cost (MMK)</th>)}
                      </tr>
                    </thead>
                    <tbody>
                      {tableData.map((product, index) => (
                        <tr key={index}>
                          <td className="border p-2">{product.code}</td>
                          <td className="border p-2">{product.name}</td>
                          <td className="border p-2">{product.ctns}</td>
                          <td className="border p-2">{formatNumber(product.weight)}</td>
                          <td className="border p-2">Kg</td>
                          {hasCalculated && (<td className="border p-2 font-semibold">{product.total_cost !== undefined ? formatNumber(product.total_cost) : '-'}</td>)}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
              
              {/* --- UPDATED TOTAL SUMMARY SECTION --- */}
              <div className="bg-white rounded-lg border p-6 mb-6">
                <h2 className="text-xl font-bold mb-4">Total Summary</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  
                  {/* Weight Summary - Always shows if products exist */}
                  <div className="bg-gradient-to-r from-purple-50 to-purple-100 rounded-lg border border-purple-200 p-6 flex flex-col justify-center">
                    <span className="text-lg font-semibold text-gray-700 mb-2">Total Weight</span>
                    <span className="text-3xl font-bold text-purple-600">{formatNumber(totalWeight)} Kg</span>
                  </div>

                  {/* Cost Summary - Only shows if calculated */}
                  {calculatedTotalCost !== null && (
                    <div className="bg-gradient-to-r from-blue-50 to-blue-100 rounded-lg border border-blue-200 p-6 flex flex-col justify-center">
                      <div className="flex justify-between items-center mb-2">
                         <span className="text-lg font-semibold text-gray-700">Total Cost</span>
                         <span className="text-3xl font-bold text-blue-600">{formatNumber(calculatedTotalCost)} MMK</span>
                      </div>
                      
                      {additionalCharges && (
                        <div className="mt-2 pt-2 border-t border-blue-200 text-sm text-gray-600 space-y-1">
                          <div className="flex justify-between">
                            <span>Subtotal (Transport):</span>
                            <span>{formatNumber(calculatedTotalCost - (parseFloat(additionalCharges) || 0))} MMK</span>
                          </div>
                          <div className="flex justify-between">
                            <span>Additional Charges:</span>
                            <span>{formatNumber(additionalCharges)} MMK</span>
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
              {/* --- END UPDATED TOTAL SUMMARY SECTION --- */}

              <div className="bg-white rounded-lg border p-6 mb-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <label className={`block text-sm font-semibold mb-2 ${!isManualTotalCostEnabled ? 'text-gray-400' : 'text-gray-700'}`}>Total Cost (Manual Override)</label>
                    <input 
                      type="number" 
                      value={manualTotalCost} 
                      onChange={(e) => setManualTotalCost(e.target.value)} 
                      placeholder={isManualTotalCostEnabled ? "Enter base transport amount..." : "Not applicable for selected items"} 
                      className={`w-full p-3 border rounded-lg ${!isManualTotalCostEnabled ? 'bg-gray-100 cursor-not-allowed text-gray-500' : ''}`}
                      disabled={!isManualTotalCostEnabled}
                    />
                    <p className={`text-xs mt-1 ${!isManualTotalCostEnabled ? 'text-gray-400' : 'text-gray-500'}`}>
                      {isManualTotalCostEnabled ? "Overrides calculated item costs." : "Only enabled if selected items have specific transport costs."}
                    </p>
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
                  {calculatedTotalCost !== null && (<button onClick={handleSaveButtonClick} className="flex items-center justify-center gap-2 px-6 py-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition"><Save size={20} /> Save as New</button>)}
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