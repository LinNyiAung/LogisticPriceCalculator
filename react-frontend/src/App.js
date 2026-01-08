import React, { useState, useEffect } from 'react';
import { Trash2, History, Calculator, Save, Weight } from 'lucide-react';

const API_URL = 'http://localhost:8000';

const PricingApp = () => {
  const [pickIds, setPickIds] = useState([]);
  const [selectedPickId, setSelectedPickId] = useState('');
  const [branches, setBranches] = useState([]);
  const [selectedBranch, setSelectedBranch] = useState('');
  const [products, setProducts] = useState([]);
  const [totalWeight, setTotalWeight] = useState(0);
  const [calculationType, setCalculationType] = useState('');
  const [calculatedProducts, setCalculatedProducts] = useState([]);
  const [calculatedTotalPrice, setCalculatedTotalPrice] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [savedCalculations, setSavedCalculations] = useState([]);
  const [notification, setNotification] = useState(null);

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

  const loadBranches = async () => {
    try {
      const response = await fetch(`${API_URL}/branches`);
      if (response.ok) {
        const data = await response.json();
        setBranches(data.branches);
      }
    } catch (error) {
      showNotification(`Error loading branches: ${error.message}`, 'error');
    }
  };

  const handlePickIdChange = async (pickId) => {
    setSelectedPickId(pickId);
    setSelectedBranch('');
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

  const handleBranchChange = (branch) => {
    setSelectedBranch(branch);
    setCalculatedProducts([]);
    setCalculatedTotalPrice(null);
    
    // Find the branch info to set calculation type
    const branchInfo = branches.find(b => b.branch === branch);
    if (branchInfo) {
      setCalculationType(branchInfo.calculation_type);
    }
  };

  const calculatePrices = async () => {
    if (!selectedPickId || !selectedBranch) {
      showNotification('Please select both Pick ID and Branch', 'error');
      return;
    }

    setIsLoading(true);
    try {
      const response = await fetch(`${API_URL}/calculate-with-branch?pick_id=${selectedPickId}&branch=${selectedBranch}`, {
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

  const loadSavedCalculations = async () => {
    try {
      const response = await fetch(`${API_URL}/calculations`);
      if (response.ok) {
        const data = await response.json();
        setSavedCalculations(data);
      }
    } catch (error) {
      console.error('Error loading calculations:', error);
    }
  };

  useEffect(() => {
    loadPickIds();
    loadBranches();
    loadSavedCalculations();
  }, []);

  if (showHistory) {
    return (
      <div className="min-h-screen bg-gray-50 p-6">
        <div className="max-w-6xl mx-auto">
          <div className="bg-white rounded-lg shadow-md p-6 mb-6">
            <div className="flex items-center justify-between mb-6">
              <h1 className="text-3xl font-bold text-gray-800">Saved Calculations</h1>
              <button
                onClick={() => setShowHistory(false)}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
              >
                Back to Calculator
              </button>
            </div>
            <p className="text-center text-gray-500 py-8">History feature not yet implemented</p>
          </div>
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

        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <div className="flex items-center justify-between mb-6">
            <h1 className="text-3xl font-bold text-gray-800">Logistic Pricing Calculator</h1>
            <button
              onClick={() => setShowHistory(true)}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
            >
              <History size={20} />
              History
            </button>
          </div>

          {/* Pick ID Selection */}
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

          {/* Branch Selection */}
          {products.length > 0 && (
            <div className="bg-white rounded-lg border p-6 mb-6">
              <h2 className="text-xl font-bold mb-4">Select Branch</h2>
              <select
                value={selectedBranch}
                onChange={(e) => handleBranchChange(e.target.value)}
                className="w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="">-- Select a Branch --</option>
                {branches.map((branch) => (
                  <option key={branch.branch} value={branch.branch}>
                    {branch.branch} - {branch.calculation_type === 'gate_pricing' ? 'Gate Pricing' : 
                     branch.calculation_type === 'direct_pricing' ? 'Direct Pricing' : 'Unknown'}
                    {branch.price && ` (${branch.price.toLocaleString()} MMK/ton)`}
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Calculation Type Display */}
          {selectedBranch && calculationType && (
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
                  <p className="text-sm text-gray-600">Selected Branch</p>
                  <p className="text-xl font-bold text-blue-600">{selectedBranch}</p>
                </div>
              </div>
            </div>
          )}

          {/* Products Section */}
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

              {/* Total Weight Display */}
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

              {/* Calculate Button */}
              {selectedBranch && (
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

              {/* Results */}
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