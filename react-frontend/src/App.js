//
import React, { useState, useEffect } from 'react';
import { Trash2, Calculator, Database, FileText, Plus, Edit2, Download, Upload } from 'lucide-react';

const API_URL = 'http://localhost:8000';

const PricingApp = () => {
  const [currentPage, setCurrentPage] = useState('calculator');
  const [pickIds, setPickIds] = useState([]);
  const [selectedPickId, setSelectedPickId] = useState('');
  
  // New Location/Gate State
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
  const [calculatedTotalPrice, setCalculatedTotalPrice] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [notification, setNotification] = useState(null);

  // Data management states
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

  const [manualTotalPrice, setManualTotalPrice] = useState('');
  const [additionalCharges, setAdditionalCharges] = useState('');
  const [estimatedTotalPrice, setEstimatedTotalPrice] = useState(null);

  const showNotification = (message, type = 'success') => {
    setNotification({ message, type });
    setTimeout(() => setNotification(null), 3000);
  };

  const loadPickIds = async () => {
    try {
      const response = await fetch(`${API_URL}/pick-ids`);
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
      const response = await fetch(`${API_URL}/admin/gates`);
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
      const response = await fetch(`${API_URL}/locations/from`);
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
      const response = await fetch(url);
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
      const response = await fetch(`${API_URL}/admin/item-pricing/${gateId}`);
      if (response.ok) {
        const data = await response.json();
        setItemPricingData(data.items);
      }
    } catch (error) {
      showNotification(`Error loading items: ${error.message}`, 'error');
    }
  };

  // --- Handlers ---

  const handleExportExcel = async () => {
    if (!selectedGateForPricing) {
      showNotification('Please select a gate first', 'error');
      return;
    }
    try {
      const response = await fetch(`${API_URL}/admin/item-pricing/export/${selectedGateForPricing}`);
      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        const contentDisposition = response.headers.get('Content-Disposition');
        let filename = 'item_pricing.xlsx';
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
        showNotification(error.detail || 'Failed to export Excel', 'error');
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
      const response = await fetch(`${API_URL}/admin/item-pricing/import/${selectedGateForPricing}`, {
        method: 'POST',
        body: formData
      });
      if (response.ok) {
        const result = await response.json();
        showNotification(`Import successful! Updated: ${result.updates}, Added: ${result.inserts}, Deleted: ${result.deletes}`, 'success');
        await loadItemPricing(selectedGateForPricing);
      } else {
        const error = await response.json();
        showNotification(error.detail || 'Failed to import Excel', 'error');
      }
    } catch (error) {
      showNotification(`Error: ${error.message}`, 'error');
    } finally {
      event.target.value = '';
    }
  };

  const handlePickIdChange = async (pickId) => {
    setSelectedPickId(pickId);
    // Reset subsequent selections
    setSelectedFrom('');
    setSelectedTo('');
    setSelectedGate('');
    setCalculationType('');
    setCalculatedProducts([]);
    setCalculatedTotalPrice(null);
    setEstimatedTotalPrice(null);
    setManualTotalPrice('');
    setAdditionalCharges('');
    
    if (!pickId) {
      setProducts([]);
      setTotalWeight(0);
      return;
    }

    try {
      const response = await fetch(`${API_URL}/products/${pickId}`);
      if (response.ok) {
        const data = await response.json();
        const productList = data.products.map(p => ({
          code: p.item_code,
          name: p.description,
          quantity: p.quantity,
          weight: p.item_weight
        }));
        setProducts(productList);
        setTotalWeight(data.total_weight || 0);
      } else {
        showNotification('Failed to load products', 'error');
      }
    } catch (error) {
      showNotification(`Error: ${error.message}`, 'error');
    }
  };

  const handleFromChange = (val) => {
    setSelectedFrom(val);
    setSelectedTo('');
    setSelectedGate('');
    setCalculatedProducts([]);
    setCalculatedTotalPrice(null);
    setEstimatedTotalPrice(null);
    setManualTotalPrice('');
    
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
    setCalculatedTotalPrice(null);
    setEstimatedTotalPrice(null);
    setManualTotalPrice('');
  };

  const handleGateChange = (gateName) => {
    setSelectedGate(gateName);
    setCalculatedProducts([]);
    setCalculatedTotalPrice(null);
    setEstimatedTotalPrice(null);
    setManualTotalPrice('');
    
    const gateInfo = gates.find(g => g.gate_name === gateName);
    if (gateInfo) {
      setCalculationType(gateInfo.calculation_type);
    }
  };

  const calculatePrices = async () => {
    if (!selectedPickId || !selectedGate) {
      showNotification('Please select Pick ID, From, To, and Gate', 'error');
      return;
    }

    setIsLoading(true);
    try {
      let url = `${API_URL}/calculate-with-gate?pick_id=${selectedPickId}&gate_name=${selectedGate}`;
      if (manualTotalPrice) {
        url += `&manual_total_price=${manualTotalPrice}`;
      }
      // --- Add this block ---
      if (additionalCharges) {
        url += `&additional_charges=${additionalCharges}`;
      }
      // ---------------------

      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });

      if (response.ok) {
        const data = await response.json();
        setCalculatedProducts(data.calculated_products);
        setCalculatedTotalPrice(data.total_price);
        setEstimatedTotalPrice(data.estimated_total_price);
        showNotification('Calculation completed successfully', 'success');
      } else {
        const error = await response.json();
        showNotification(error.detail || 'Failed to calculate prices', 'error');
      }
    } catch (error) {
      showNotification(`Error: ${error.message}`, 'error');
    } finally {
      setIsLoading(false);
    }
  };

  // --- CRUD Operations ---

  const saveGate = async (gateData) => {
    try {
      const payload = {
        ...gateData,
        original_gate_name: originalGateName
      };
      const response = await fetch(`${API_URL}/admin/gates`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (response.ok) {
        showNotification('Gate saved successfully', 'success');
        await loadGates();
        await loadFromLocations(); // Refresh locations list
        setShowAddGateModal(false);
        setEditingGate(null);
        setOriginalGateName(null);
      } else {
        const error = await response.json();
        showNotification(error.detail || 'Failed to save gate', 'error');
      }
    } catch (error) {
      showNotification(`Error: ${error.message}`, 'error');
    }
  };

  const deleteGate = async (gateId) => {
    setConfirmDialog({
      message: `Are you sure you want to delete this gate? All associated pricing will also be deleted.`,
      onConfirm: async () => {
        try {
          const response = await fetch(`${API_URL}/admin/gates/${gateId}`, {
            method: 'DELETE'
          });
          if (response.ok) {
            showNotification('Gate deleted successfully', 'success');
            await loadGates();
            await loadFromLocations();
          } else {
            const error = await response.json();
            showNotification(error.detail || 'Failed to delete gate', 'error');
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
      const response = await fetch(`${API_URL}/admin/item-pricing`, {
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
        showNotification(error.detail || 'Failed to save item', 'error');
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
          const response = await fetch(`${API_URL}/admin/item-pricing/${selectedGateForPricing}/${encodedItemCode}`, {
            method: 'DELETE'
          });
          if (response.ok) {
            showNotification('Item deleted successfully', 'success');
            await loadItemPricing(selectedGateForPricing);
          } else {
            const error = await response.json();
            showNotification(error.detail || 'Failed to delete item', 'error');
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
    loadPickIds();
    loadGates();
    loadFromLocations();
  }, []);

  useEffect(() => {
    if (selectedGateForPricing) {
      loadItemPricing(selectedGateForPricing);
    } else {
      setItemPricingData([]);
    }
  }, [selectedGateForPricing]);

  // --- Components ---

  const GateModal = ({ gate, onSave, onClose }) => {
    const [formData, setFormData] = useState(gate || {
      gate_name: '',
      from_loc: '',
      to_loc: '',
      price: ''
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
                value={formData.gate_name}
                onChange={(e) => setFormData({...formData, gate_name: e.target.value})}
                className="w-full p-2 border rounded"
              />
            </div>
            <div>
              <label className="block text-sm font-semibold mb-1">From</label>
              <input
                type="text"
                value={formData.from_loc}
                onChange={(e) => setFormData({...formData, from_loc: e.target.value})}
                className="w-full p-2 border rounded"
                placeholder="e.g. YGN"
              />
            </div>
            <div>
              <label className="block text-sm font-semibold mb-1">To</label>
              <input
                type="text"
                value={formData.to_loc}
                onChange={(e) => setFormData({...formData, to_loc: e.target.value})}
                className="w-full p-2 border rounded"
                placeholder="e.g. MDY"
              />
            </div>
            <div>
              <label className="block text-sm font-semibold mb-1">Price (MMK/ton)</label>
              <input
                type="number"
                value={formData.price}
                onChange={(e) => setFormData({...formData, price: e.target.value})}
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
      is_active: 'Active',
      principal: '',
      brand: '',
      purchase_weight: '',
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
                value={formData.item_code}
                onChange={(e) => setFormData({...formData, item_code: e.target.value})}
                className="w-full p-2 border rounded"
                disabled={!!item}
              />
            </div>
            <div>
              <label className="block text-sm font-semibold mb-1">Item Name</label>
              <input
                type="text"
                value={formData.item_name}
                onChange={(e) => setFormData({...formData, item_name: e.target.value})}
                className="w-full p-2 border rounded"
              />
            </div>
            <div>
              <label className="block text-sm font-semibold mb-1">Status</label>
              <select
                value={formData.is_active}
                onChange={(e) => setFormData({...formData, is_active: e.target.value})}
                className="w-full p-2 border rounded"
              >
                <option value="Active">Active</option>
                <option value="Inactive">Inactive</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-semibold mb-1">Transportation Cost</label>
              <input
                type="text"
                value={formData.transportation_cost}
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
      <div className="max-w-6xl mx-auto px-6 py-4">
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
            Transport Cost by Gate
          </button>
          <button
            onClick={() => setCurrentPage('items')}
            className={`flex items-center gap-2 px-4 py-2 rounded transition ${
              currentPage === 'items' ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            }`}
          >
            <FileText size={20} />
            Transport Cost by Item
          </button>
        </div>
      </div>
    </div>
  );

  if (currentPage === 'gates') {
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
              <h1 className="text-3xl font-bold text-gray-800">Transport Cost by Gate</h1>
              <button
                onClick={() => setShowAddGateModal(true)}
                className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition"
              >
                <Plus size={20} />
                Add Gate
              </button>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full border-collapse border">
                <thead className="bg-gray-100">
                  <tr>
                    <th className="border p-3 text-left">Gate Name</th>
                    <th className="border p-3 text-left">From</th>
                    <th className="border p-3 text-left">To</th>
                    <th className="border p-3 text-left">Price (MMK/ton)</th>
                    <th className="border p-3 text-left">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {gateData.map((gate, index) => (
                    <tr key={index}>
                      <td className="border p-3">{gate.gate_name}</td>
                      <td className="border p-3">{gate.from_loc}</td>
                      <td className="border p-3">{gate.to_loc}</td>
                      <td className="border p-3">{gate.price || '-'}</td>
                      <td className="border p-3">
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
                          <button
                            onClick={() => deleteGate(gate.gate_id)}
                            className="p-2 bg-red-500 text-white rounded hover:bg-red-600"
                          >
                            <Trash2 size={16} />
                          </button>
                        </div>
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

  if (currentPage === 'items') {
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
              <h1 className="text-3xl font-bold text-gray-800">Transport Cost by Item</h1>
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
                      <th className="border p-2 text-left">Status</th>
                      <th className="border p-2 text-left">Transport Cost</th>
                      <th className="border p-2 text-left">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {itemPricingData.map((item, index) => (
                      <tr key={index}>
                        <td className="border p-2">{item.item_code}</td>
                        <td className="border p-2">{item.item_name}</td>
                        <td className="border p-2">{item.is_active}</td>
                        <td className="border p-2">{item.transportation_cost}</td>
                        <td className="border p-2">
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
                            <button
                              onClick={() => deleteItem(item.item_code)}
                              className="p-1 bg-red-500 text-white rounded hover:bg-red-600"
                            >
                              <Trash2 size={14} />
                            </button>
                          </div>
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

  // Calculator View
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
          <h1 className="text-3xl font-bold text-gray-800 mb-6">Logistic Pricing Calculator</h1>
          <div className="bg-white rounded-lg border p-6 mb-6">
            <h2 className="text-xl font-bold mb-4">Select Pick ID</h2>
            <select
              value={selectedPickId}
              onChange={(e) => handlePickIdChange(e.target.value)}
              className="w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-500"
            >
              <option value="">-- Select a Pick ID --</option>
              {pickIds.map((pickId) => (
                <option key={pickId} value={pickId}>{pickId}</option>
              ))}
            </select>
          </div>
          
          {products.length > 0 && (
            <>
              {/* Select From */}
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

              {/* Select To (Only if From is selected) */}
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

              {/* Select Gate (Only if To is selected) */}
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

          {/* Rest of the Calculator (Unchanged in logic, just re-rendered) */}
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
                <h2 className="text-xl font-bold mb-4">Products</h2>
                <div className="overflow-x-auto">
                  <table className="w-full border-collapse border">
                    <thead className="bg-gray-100">
                      <tr>
                        <th className="border p-2 text-left">Item Code</th>
                        <th className="border p-2 text-left">Description</th>
                        <th className="border p-2 text-left">Quantity</th>
                        <th className="border p-2 text-left">Weight</th>
                      </tr>
                    </thead>
                    <tbody>
                      {products.map((product, index) => (
                        <tr key={index}>
                          <td className="border p-2">{product.code}</td>
                          <td className="border p-2">{product.name}</td>
                          <td className="border p-2">{product.quantity}</td>
                          <td className="border p-2">{product.weight}</td>
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
                <h2 className="text-xl font-bold mb-4">Pricing Options</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <label className="block text-sm font-semibold text-gray-700 mb-2">Target Transport Price (Optional)</label>
                    <input
                      type="number"
                      value={manualTotalPrice}
                      onChange={(e) => setManualTotalPrice(e.target.value)}
                      placeholder="Enter base transport amount..."
                      className="w-full p-3 border rounded-lg"
                    />
                    <p className="text-xs text-gray-500 mt-1">Overrides calculated item prices.</p>
                  </div>
                  
                  {/* --- New Field Start --- */}
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
                  {/* --- New Field End --- */}

                  {estimatedTotalPrice !== null && (manualTotalPrice || additionalCharges) && (
                    <div className="bg-gray-50 p-4 rounded-lg border border-gray-200 flex flex-col justify-center col-span-1 md:col-span-2">
                      <span className="text-sm text-gray-600">Standard Estimated Total (Inc. Extras):</span>
                      <span className="text-xl font-bold text-gray-700">
                        {estimatedTotalPrice.toLocaleString()} MMK
                      </span>
                    </div>
                  )}
                </div>
              </div>
               <button
                    onClick={calculatePrices}
                    disabled={isLoading}
                    className="w-full flex items-center justify-center gap-2 px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition disabled:bg-gray-400 mb-6"
                  >
                    <Calculator size={20} />
                    {isLoading ? 'Calculating...' : 'Calculate Prices'}
                  </button>
              </>
            )}
             {calculatedProducts.length > 0 && (
                <div className="bg-white rounded-lg border p-6">
                  <h2 className="text-xl font-bold mb-4">Calculated Results</h2>
                  <table className="w-full border-collapse border">
                      <thead className="bg-gray-100">
                        <tr>
                          <th className="border p-3 text-left">Item Code</th>
                          <th className="border p-3 text-left">Description</th>
                          <th className="border p-3 text-left">Quantity</th>
                          <th className="border p-3 text-left">Weight</th>
                          <th className="border p-3 text-left">Price (MMK)</th>
                        </tr>
                      </thead>
                      <tbody>
                        {calculatedProducts.map((product, index) => (
                          <tr key={index}>
                            <td className="border p-3">{product.code}</td>
                            <td className="border p-3">{product.name}</td>
                            <td className="border p-3">{product.quantity}</td>
                            <td className="border p-3">{product.weight.toFixed(2)}</td>
                            <td className="border p-3 font-semibold">{product.price.toFixed(2)}</td>
                          </tr>
                        ))}
                      </tbody>
                  </table>
                   {calculatedTotalPrice !== null && (
                    <div className="mt-4 p-4 bg-blue-50 rounded-lg">
                      <div className="flex flex-col gap-2 items-end">
                        {/* Show breakdown if additional charges exist */}
                        {additionalCharges && (
                          <>
                            <div className="flex justify-between w-full md:w-1/3 text-gray-600">
                              <span>Subtotal (Transport):</span>
                              <span>{(calculatedTotalPrice - (parseFloat(additionalCharges) || 0)).toFixed(2)} MMK</span>
                            </div>
                            <div className="flex justify-between w-full md:w-1/3 text-gray-600">
                              <span>Additional Charges:</span>
                              <span>{parseFloat(additionalCharges).toFixed(2)} MMK</span>
                            </div>
                            <div className="w-full md:w-1/3 border-b border-gray-300 my-1"></div>
                          </>
                        )}
                        
                        <div className="flex justify-between w-full md:w-1/3 items-center">
                          <span className="text-lg font-bold">Total Price:</span>
                          <span className="text-2xl font-bold text-blue-600">
                            {calculatedTotalPrice.toFixed(2)} MMK
                          </span>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
             )}
        </div>
      </div>
    </div>
  );
};

export default PricingApp;