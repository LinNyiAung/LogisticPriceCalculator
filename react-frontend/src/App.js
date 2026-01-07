import React, { useState, useEffect } from 'react';
import { Trash2, History, Calculator, Save, Weight } from 'lucide-react';

const API_URL = 'http://localhost:8000';

const PricingApp = () => {
  const [calculationType, setCalculationType] = useState('gate_pricing');
  const [pickIds, setPickIds] = useState([]);
  const [selectedPickId, setSelectedPickId] = useState('');
  const [products, setProducts] = useState([]);
  const [totalWeight, setTotalWeight] = useState(0);
  const [gatePricing, setGatePricing] = useState({
    gateName: '',
    weightUnit: 'kg',
    weightUnitNumber: 1,
    weightUnitPrice: 0
  });
  const [totalPrice, setTotalPrice] = useState(0);
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

  const handlePickIdChange = async (pickId) => {
    setSelectedPickId(pickId);
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
          weight: p.item_weight,
          calculationType: 'weight',
          pricePerOne: 0
        }));
        setProducts(productList);
        setTotalWeight(data.total_weight || 0);
        setCalculatedProducts([]);
        setCalculatedTotalPrice(null);
      } else {
        showNotification('Failed to load products', 'error');
      }
    } catch (error) {
      showNotification(`Error: ${error.message}`, 'error');
    }
  };

  const updateProduct = (index, field, value) => {
    const newProducts = [...products];
    newProducts[index][field] = value;
    setProducts(newProducts);
  };

  const calculatePrices = async () => {
    setIsLoading(true);
    try {
      const requestBody = {
        calculation_type: calculationType,
        products: products.map(p => ({
          code: p.code,
          name: p.name,
          quantity: p.quantity,
          uom: p.uom,
          weight: p.weight,
          calculation_type: p.calculationType,
          ...(calculationType === 'direct_pricing' && { price_per_one: parseFloat(p.pricePerOne) || 0 })
        }))
      };

      if (calculationType === 'gate_pricing') {
        requestBody.gate_pricing = {
          gate_name: gatePricing.gateName,
          weight_unit: gatePricing.weightUnit,
          weight_unit_number: parseFloat(gatePricing.weightUnitNumber) || 0,
          weight_unit_price: parseFloat(gatePricing.weightUnitPrice) || 0
        };
        requestBody.total_price = parseFloat(totalPrice) || 0;
      }

      const response = await fetch(`${API_URL}/calculate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestBody)
      });

      if (response.ok) {
        const data = await response.json();
        setCalculatedProducts(data.calculated_products);
        setCalculatedTotalPrice(data.total_price);
      } else {
        showNotification('Failed to calculate prices', 'error');
      }
    } catch (error) {
      showNotification(`Error: ${error.message}`, 'error');
    } finally {
      setIsLoading(false);
    }
  };

  const saveCalculation = async () => {
    setIsLoading(true);
    try {
      const requestBody = {
        calculation_type: calculationType,
        products: products.map(p => ({
          code: p.code,
          name: p.name,
          quantity: p.quantity,
          uom: p.uom,
          weight: p.weight,
          calculation_type: p.calculationType,
          ...(calculationType === 'direct_pricing' && { price_per_one: parseFloat(p.pricePerOne) || 0 })
        }))
      };

      if (calculationType === 'gate_pricing') {
        requestBody.gate_pricing = {
          gate_name: gatePricing.gateName,
          weight_unit: gatePricing.weightUnit,
          weight_unit_number: parseFloat(gatePricing.weightUnitNumber) || 0,
          weight_unit_price: parseFloat(gatePricing.weightUnitPrice) || 0
        };
        requestBody.total_price = parseFloat(totalPrice) || 0;
      }

      const response = await fetch(`${API_URL}/save`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestBody)
      });

      if (response.ok) {
        showNotification('Calculation saved successfully', 'success');
        loadSavedCalculations();
      } else {
        showNotification('Failed to save calculation', 'error');
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

  const deleteCalculation = async (id) => {
    try {
      const response = await fetch(`${API_URL}/calculations/${id}`, {
        method: 'DELETE'
      });
      if (response.ok) {
        showNotification('Calculation deleted', 'success');
        loadSavedCalculations();
      }
    } catch (error) {
      showNotification(`Error: ${error.message}`, 'error');
    }
  };

  useEffect(() => {
    loadPickIds();
    loadSavedCalculations();
  }, []);

  const handleCalculationTypeChange = (type) => {
    setCalculationType(type);
    setCalculatedProducts([]);
    setCalculatedTotalPrice(null);
  };

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

            {savedCalculations.length === 0 ? (
              <p className="text-center text-gray-500 py-8">No saved calculations</p>
            ) : (
              <div className="space-y-4">
                {savedCalculations.map((calc) => (
                  <div key={calc.id} className="border rounded-lg p-4">
                    <div className="flex items-center justify-between mb-4">
                      <div>
                        <h3 className="text-lg font-semibold">
                          Calculation #{calc.id} - {calc.calculation_type === 'gate_pricing' ? 'Gate Pricing' : 'Direct Pricing'}
                        </h3>
                        <p className="text-sm text-gray-500">{new Date(calc.created_at).toLocaleString()}</p>
                      </div>
                      <button
                        onClick={() => deleteCalculation(calc.id)}
                        className="text-red-600 hover:text-red-700"
                      >
                        <Trash2 size={20} />
                      </button>
                    </div>

                    {calc.total_price && (
                      <p className="font-semibold mb-4">Total Price: {calc.total_price.toFixed(2)}</p>
                    )}

                    <div className="overflow-x-auto">
                      <table className="w-full border-collapse border">
                        <thead className="bg-gray-100">
                          <tr>
                            <th className="border p-2 text-left">Item Code</th>
                            <th className="border p-2 text-left">Description</th>
                            <th className="border p-2 text-left">Quantity</th>
                            <th className="border p-2 text-left">UoM</th>
                            <th className="border p-2 text-left">Weight</th>
                            {calc.calculation_type === 'gate_pricing' && (
                              <th className="border p-2 text-left">Calc Type</th>
                            )}
                            {calc.calculation_type === 'direct_pricing' && (
                              <th className="border p-2 text-left">Price/One</th>
                            )}
                            <th className="border p-2 text-left">Price</th>
                          </tr>
                        </thead>
                        <tbody>
                          {calc.calculated_products.map((p, idx) => (
                            <tr key={idx}>
                              <td className="border p-2">{p.code}</td>
                              <td className="border p-2">{p.name}</td>
                              <td className="border p-2">{p.quantity}</td>
                              <td className="border p-2">{p.uom}</td>
                              <td className="border p-2">{p.weight}</td>
                              {calc.calculation_type === 'gate_pricing' && (
                                <td className="border p-2">{p.calculation_type}</td>
                              )}
                              {calc.calculation_type === 'direct_pricing' && (
                                <td className="border p-2">{p.price_per_one?.toFixed(2) || '0.00'}</td>
                              )}
                              <td className="border p-2">{p.price.toFixed(2)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                ))}
              </div>
            )}
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

          {/* Calculation Type Selector */}
          {products.length > 0 && (
            <>
              <div className="bg-white rounded-lg border p-6 mb-6">
                <h2 className="text-xl font-bold mb-4">Calculation Type</h2>
                <select
                  value={calculationType}
                  onChange={(e) => handleCalculationTypeChange(e.target.value)}
                  className="w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="gate_pricing">Gate Pricing Calculation</option>
                  <option value="direct_pricing">Direct Pricing Calculation</option>
                </select>
              </div>

              {/* Gate Pricing Section */}
              {calculationType === 'gate_pricing' && (
                <div className="bg-white rounded-lg border p-6 mb-6">
                  <h2 className="text-xl font-bold mb-4">Gate Pricing</h2>
                  <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">Gate Name</label>
                      <input
                        type="text"
                        value={gatePricing.gateName}
                        onChange={(e) => setGatePricing({ ...gatePricing, gateName: e.target.value })}
                        className="w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                        placeholder="Enter gate name"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">UOM</label>
                      <select
                        value={gatePricing.weightUnit}
                        onChange={(e) => setGatePricing({ ...gatePricing, weightUnit: e.target.value })}
                        className="w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      >
                        <option value="kg">kg</option>
                        <option value="tonne">tonne</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">Unit</label>
                      <input
                        type="number"
                        value={gatePricing.weightUnitNumber}
                        onChange={(e) => setGatePricing({ ...gatePricing, weightUnitNumber: e.target.value })}
                        className="w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">Unit Price</label>
                      <input
                        type="number"
                        value={gatePricing.weightUnitPrice}
                        onChange={(e) => setGatePricing({ ...gatePricing, weightUnitPrice: e.target.value })}
                        className="w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      />
                    </div>
                  </div>
                </div>
              )}

              {/* Products Section */}
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
                        {calculationType === 'gate_pricing' && (
                          <th className="border p-2 text-left">Calc Type</th>
                        )}
                        {calculationType === 'direct_pricing' && (
                          <th className="border p-2 text-left">Price/One</th>
                        )}
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
                          {calculationType === 'gate_pricing' && (
                            <td className="border p-2">
                              <select
                                value={product.calculationType}
                                onChange={(e) => updateProduct(index, 'calculationType', e.target.value)}
                                className="w-full p-2 border rounded focus:ring-2 focus:ring-blue-500"
                              >
                                <option value="weight">Weight</option>
                                <option value="pack">Pack</option>
                              </select>
                            </td>
                          )}
                          {calculationType === 'direct_pricing' && (
                            <td className="border p-2">
                              <input
                                type="number"
                                value={product.pricePerOne}
                                onChange={(e) => updateProduct(index, 'pricePerOne', e.target.value)}
                                className="w-full p-2 border rounded focus:ring-2 focus:ring-blue-500"
                              />
                            </td>
                          )}
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
                    {totalWeight.toFixed(2)} kg
                  </span>
                </div>
              </div>

              {/* Total Price Input (Gate Pricing Only) */}
              {calculationType === 'gate_pricing' && (
                <div className="bg-white rounded-lg border p-6 mb-6">
                  <label className="block text-sm font-medium text-gray-700 mb-2">Total Price</label>
                  <input
                    type="number"
                    value={totalPrice}
                    onChange={(e) => setTotalPrice(e.target.value)}
                    className="w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
              )}

              {/* Action Buttons */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                <button
                  onClick={calculatePrices}
                  disabled={isLoading}
                  className="flex items-center justify-center gap-2 px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition disabled:bg-gray-400"
                >
                  <Calculator size={20} />
                  {isLoading ? 'Calculating...' : 'Calculate'}
                </button>
                <button
                  onClick={saveCalculation}
                  disabled={isLoading}
                  className="flex items-center justify-center gap-2 px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 transition disabled:bg-gray-400"
                >
                  <Save size={20} />
                  Save
                </button>
              </div>

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
                          {calculationType === 'gate_pricing' && (
                            <th className="border p-3 text-left">Calc Type</th>
                          )}
                          {calculationType === 'direct_pricing' && (
                            <th className="border p-3 text-left">Price/One</th>
                          )}
                          <th className="border p-3 text-left">Price</th>
                        </tr>
                      </thead>
                      <tbody>
                        {calculatedProducts.map((product, index) => (
                          <tr key={index}>
                            <td className="border p-3">{product.code}</td>
                            <td className="border p-3">{product.name}</td>
                            <td className="border p-3">{product.quantity}</td>
                            <td className="border p-3">{product.uom}</td>
                            <td className="border p-3">{product.weight}</td>
                            {calculationType === 'gate_pricing' && (
                              <td className="border p-3">{product.calculation_type}</td>
                            )}
                            {calculationType === 'direct_pricing' && (
                              <td className="border p-3">{product.price_per_one?.toFixed(2) || '0.00'}</td>
                            )}
                            <td className="border p-3">{product.price.toFixed(2)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  {calculatedTotalPrice !== null && (
                    <div className="mt-4 p-4 bg-blue-50 rounded-lg flex justify-between items-center">
                      <span className="text-lg font-bold">Total Price:</span>
                      <span className="text-2xl font-bold text-blue-600">
                        {calculatedTotalPrice.toFixed(2)}
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