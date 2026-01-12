import React, { useState, useEffect } from 'react';
import { Trash2, History, Calculator, Save, Weight, Settings, Plus, Edit2, X, Database, FileText } from 'lucide-react';

const API_URL = 'http://localhost:8000';

const PricingApp = () => {
  const [currentPage, setCurrentPage] = useState('calculator');
  const [pickIds, setPickIds] = useState([]);
  const [selectedPickId, setSelectedPickId] = useState('');
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
  const [itemMasterFiles, setItemMasterFiles] = useState([]);
  const [selectedItemMaster, setSelectedItemMaster] = useState('');
  const [itemMasterData, setItemMasterData] = useState([]);
  const [editingGate, setEditingGate] = useState(null);
  const [editingItem, setEditingItem] = useState(null);
  const [showAddGateModal, setShowAddGateModal] = useState(false);
  const [showAddItemModal, setShowAddItemModal] = useState(false);
  const [confirmDialog, setConfirmDialog] = useState(null);
  const [originalGateName, setOriginalGateName] = useState(null);
  const [originalItemCode, setOriginalItemCode] = useState(null);

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
      const response = await fetch(`${API_URL}/branches`);
      if (response.ok) {
        const data = await response.json();
        setGates(data.gates);
      }
    } catch (error) {
      showNotification(`Error loading gates: ${error.message}`, 'error');
    }
  };

  const loadGateData = async () => {
    try {
      const response = await fetch(`${API_URL}/admin/gates`);
      if (response.ok) {
        const data = await response.json();
        setGateData(data.gates);
      }
    } catch (error) {
      showNotification(`Error loading gate data: ${error.message}`, 'error');
    }
  };

  const loadItemMasterFiles = async () => {
    try {
      const response = await fetch(`${API_URL}/admin/item-master-files`);
      if (response.ok) {
        const data = await response.json();
        setItemMasterFiles(data.files);
      }
    } catch (error) {
      showNotification(`Error loading item master files: ${error.message}`, 'error');
    }
  };

  const loadItemMasterData = async (fileName) => {
    try {
      const response = await fetch(`${API_URL}/admin/item-master/${fileName}`);
      if (response.ok) {
        const data = await response.json();
        setItemMasterData(data.items);
      }
    } catch (error) {
      showNotification(`Error loading item master: ${error.message}`, 'error');
    }
  };

  const handlePickIdChange = async (pickId) => {
    setSelectedPickId(pickId);
    setSelectedGate('');
    setCalculationType('');
    setCalculatedProducts([]);
    setCalculatedTotalPrice(null);
    
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
          uom: p.uom,
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

  const handleGateChange = (gateName) => {
    setSelectedGate(gateName);
    setCalculatedProducts([]);
    setCalculatedTotalPrice(null);
    
    const gateInfo = gates.find(g => g.gate_name === gateName);
    if (gateInfo) {
      setCalculationType(gateInfo.calculation_type);
    }
  };

  const calculatePrices = async () => {
    if (!selectedPickId || !selectedGate) {
      showNotification('Please select both Pick ID and Gate', 'error');
      return;
    }

    setIsLoading(true);
    try {
      const response = await fetch(`${API_URL}/calculate-with-gate?pick_id=${selectedPickId}&gate_name=${selectedGate}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });

      if (response.ok) {
        const data = await response.json();
        setCalculatedProducts(data.calculated_products);
        setCalculatedTotalPrice(data.total_price);
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

  const saveGate = async (gateData) => {
    try {
      const payload = {
        ...gateData,
        original_gate_name: originalGateName || gateData.gate_name
      };
      
      const response = await fetch(`${API_URL}/admin/gates`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (response.ok) {
        showNotification('Gate saved successfully', 'success');
        await loadGateData();
        await loadGates();
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

  const deleteGate = async (gateName) => {
    setConfirmDialog({
      message: `Are you sure you want to delete gate "${gateName}"?`,
      onConfirm: async () => {
        try {
          const encodedGateName = encodeURIComponent(gateName);
          const response = await fetch(`${API_URL}/admin/gates/${encodedGateName}`, {
            method: 'DELETE'
          });

          if (response.ok) {
            showNotification('Gate deleted successfully', 'success');
            await loadGateData();
            await loadGates();
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
        original_item_code: originalItemCode || itemData.item_code
      };
      
      const response = await fetch(`${API_URL}/admin/item-master/${selectedItemMaster}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (response.ok) {
        showNotification('Item saved successfully', 'success');
        await loadItemMasterData(selectedItemMaster);
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
          const response = await fetch(`${API_URL}/admin/item-master/${selectedItemMaster}/${encodedItemCode}`, {
            method: 'DELETE'
          });

          if (response.ok) {
            showNotification('Item deleted successfully', 'success');
            await loadItemMasterData(selectedItemMaster);
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
  }, []);

  useEffect(() => {
    if (currentPage === 'gates') {
      loadGateData();
    } else if (currentPage === 'items') {
      loadItemMasterFiles();
    }
  }, [currentPage]);

  useEffect(() => {
    if (selectedItemMaster) {
      loadItemMasterData(selectedItemMaster);
    }
  }, [selectedItemMaster]);

  const GateModal = ({ gate, onSave, onClose }) => {
    const [formData, setFormData] = useState(gate || {
      gate_name: '',
      branch: '',
      file_name: '',
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
                placeholder="Gate 1"
              />
            </div>
            <div>
              <label className="block text-sm font-semibold mb-1">Branch</label>
              <input
                type="text"
                value={formData.branch}
                onChange={(e) => setFormData({...formData, branch: e.target.value})}
                className="w-full p-2 border rounded"
                placeholder="MDY"
              />
            </div>
            <div>
              <label className="block text-sm font-semibold mb-1">File Name</label>
              <input
                type="text"
                value={formData.file_name}
                onChange={(e) => setFormData({...formData, file_name: e.target.value})}
                className="w-full p-2 border rounded"
                placeholder="Item Master MDY.csv"
              />
            </div>
            <div>
              <label className="block text-sm font-semibold mb-1">Price (MMK/ton)</label>
              <input
                type="number"
                value={formData.price}
                onChange={(e) => setFormData({...formData, price: e.target.value})}
                className="w-full p-2 border rounded"
                placeholder="140000"
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
      uom: '',
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
              <label className="block text-sm font-semibold mb-1">Principal</label>
              <input
                type="text"
                value={formData.principal}
                onChange={(e) => setFormData({...formData, principal: e.target.value})}
                className="w-full p-2 border rounded"
              />
            </div>
            <div>
              <label className="block text-sm font-semibold mb-1">Brand</label>
              <input
                type="text"
                value={formData.brand}
                onChange={(e) => setFormData({...formData, brand: e.target.value})}
                className="w-full p-2 border rounded"
              />
            </div>
            <div>
              <label className="block text-sm font-semibold mb-1">UOM</label>
              <input
                type="number"
                value={formData.uom}
                onChange={(e) => setFormData({...formData, uom: e.target.value})}
                className="w-full p-2 border rounded"
              />
            </div>
            <div>
              <label className="block text-sm font-semibold mb-1">Purchase Weight</label>
              <input
                type="number"
                step="0.01"
                value={formData.purchase_weight}
                onChange={(e) => setFormData({...formData, purchase_weight: e.target.value})}
                className="w-full p-2 border rounded"
              />
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
            Gate Data
          </button>
          <button
            onClick={() => setCurrentPage('items')}
            className={`flex items-center gap-2 px-4 py-2 rounded transition ${
              currentPage === 'items' ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            }`}
          >
            <FileText size={20} />
            Product Price
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
              <h1 className="text-3xl font-bold text-gray-800">Gate Data Management</h1>
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
                    <th className="border p-3 text-left">Branch</th>
                    <th className="border p-3 text-left">File Name</th>
                    <th className="border p-3 text-left">Price (MMK/ton)</th>
                    <th className="border p-3 text-left">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {gateData.map((gate, index) => (
                    <tr key={index}>
                      <td className="border p-3">{gate.gate_name}</td>
                      <td className="border p-3">{gate.branch}</td>
                      <td className="border p-3">{gate.file_name}</td>
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
                            onClick={() => deleteGate(gate.gate_name)}
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
              <h1 className="text-3xl font-bold text-gray-800">Product Price Management</h1>
              {selectedItemMaster && (
                <button
                  onClick={() => setShowAddItemModal(true)}
                  className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition"
                >
                  <Plus size={20} />
                  Add Item
                </button>
              )}
            </div>

            <div className="mb-6">
              <label className="block text-sm font-semibold mb-2">Select Product Price File</label>
              <select
                value={selectedItemMaster}
                onChange={(e) => setSelectedItemMaster(e.target.value)}
                className="w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-500"
              >
                <option value="">-- Select a file --</option>
                {itemMasterFiles.map((file) => (
                  <option key={file} value={file}>{file}</option>
                ))}
              </select>
            </div>

            {selectedItemMaster && (
              <div className="overflow-x-auto">
                <table className="w-full border-collapse border text-sm">
                  <thead className="bg-gray-100">
                    <tr>
                      <th className="border p-2 text-left">Item Code</th>
                      <th className="border p-2 text-left">Item Name</th>
                      <th className="border p-2 text-left">Status</th>
                      <th className="border p-2 text-left">Principal</th>
                      <th className="border p-2 text-left">Brand</th>
                      <th className="border p-2 text-left">UOM</th>
                      <th className="border p-2 text-left">Weight</th>
                      <th className="border p-2 text-left">Transport Cost</th>
                      <th className="border p-2 text-left">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {itemMasterData.map((item, index) => (
                      <tr key={index}>
                        <td className="border p-2">{item.item_code}</td>
                        <td className="border p-2">{item.item_name}</td>
                        <td className="border p-2">{item.is_active}</td>
                        <td className="border p-2">{item.principal}</td>
                        <td className="border p-2">{item.brand}</td>
                        <td className="border p-2">{item.uom}</td>
                        <td className="border p-2">{item.purchase_weight}</td>
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
              className="w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="">-- Select a Pick ID --</option>
              {pickIds.map((pickId) => (
                <option key={pickId} value={pickId}>
                  {pickId}
                </option>
              ))}
            </select>
          </div>

          {products.length > 0 && (
            <div className="bg-white rounded-lg border p-6 mb-6">
              <h2 className="text-xl font-bold mb-4">Select Gate</h2>
              <select
                value={selectedGate}
                onChange={(e) => handleGateChange(e.target.value)}
                className="w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="">-- Select a Gate --</option>
                {gates.map((gate) => (
                  <option key={gate.gate_name} value={gate.gate_name}>
                    {gate.gate_name} ({gate.branch}) - {gate.calculation_type === 'gate_pricing' ? 'Gate Pricing' : 
                     gate.calculation_type === 'direct_pricing' ? 'Direct Pricing' : 'Unknown'}
                    {gate.price && ` (${gate.price.toLocaleString()} MMK/ton)`}
                  </option>
                ))}
              </select>
            </div>
          )}

          {selectedGate && calculationType && (
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
                  <p className="text-sm text-gray-600">Selected Gate</p>
                  <p className="text-xl font-bold text-blue-600">{selectedGate}</p>
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
                        <th className="border p-2 text-left">UoM</th>
                        <th className="border p-2 text-left">Weight</th>
                      </tr>
                    </thead>
                    <tbody>
                      {products.map((product, index) => (
                        <tr key={index}>
                          <td className="border p-2">{product.code}</td>
                          <td className="border p-2">{product.name}</td>
                          <td className="border p-2">{product.quantity}</td>
                          <td className="border p-2">{product.uom}</td>
                          <td className="border p-2">{product.weight}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              <div className="bg-gradient-to-r from-purple-50 to-purple-100 rounded-lg border-2 border-purple-300 p-6 mb-6">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <Weight size={28} className="text-purple-600" />
                    <span className="text-lg font-semibold text-gray-700">Total Weight:</span>
                  </div>
                  <span className="text-3xl font-bold text-purple-600">
                    {totalWeight.toFixed(2)} 
                  </span>
                </div>
              </div>

              {selectedGate && (
                <div className="mb-6">
                  <button
                    onClick={calculatePrices}
                    disabled={isLoading}
                    className="w-full flex items-center justify-center gap-2 px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition disabled:bg-gray-400"
                  >
                    <Calculator size={20} />
                    {isLoading ? 'Calculating...' : 'Calculate Prices'}
                  </button>
                </div>
              )}

              {calculatedProducts.length > 0 && (
                <div className="bg-white rounded-lg border p-6">
                  <h2 className="text-xl font-bold mb-4">Calculated Results</h2>
                  <div className="overflow-x-auto">
                    <table className="w-full border-collapse border">
                      <thead className="bg-gray-100">
                        <tr>
                          <th className="border p-3 text-left">Item Code</th>
                          <th className="border p-3 text-left">Description</th>
                          <th className="border p-3 text-left">Quantity</th>
                          <th className="border p-3 text-left">UoM</th>
                          <th className="border p-3 text-left">Weight</th>
                          {calculationType === 'direct_pricing' && (
                            <th className="border p-3 text-left">Price/Unit</th>
                          )}
                          <th className="border p-3 text-left">Price (MMK)</th>
                        </tr>
                      </thead>
                      <tbody>
                        {calculatedProducts.map((product, index) => (
                          <tr key={index}>
                            <td className="border p-3">{product.code}</td>
                            <td className="border p-3">{product.name}</td>
                            <td className="border p-3">{product.quantity}</td>
                            <td className="border p-3">{product.uom}</td>
                            <td className="border p-3">{product.weight.toFixed(2)}</td>
                            {calculationType === 'direct_pricing' && (
                              <td className="border p-3">
                                {product.price_per_one ? product.price_per_one.toFixed(2) : '0.00'}
                              </td>
                            )}
                            <td className="border p-3 font-semibold">{product.price.toFixed(2)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  {calculatedTotalPrice !== null && (
                    <div className="mt-4 p-4 bg-blue-50 rounded-lg flex justify-between items-center">
                      <span className="text-lg font-bold">Total Price:</span>
                      <span className="text-2xl font-bold text-blue-600">
                        {calculatedTotalPrice.toFixed(2)} MMK
                      </span>
                    </div>
                  )}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default PricingApp;