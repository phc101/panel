import React, { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

const FxRiskManagementDashboard = () => {
  // State for currency pairs and spot rates
  const [spotRates, setSpotRates] = useState({
    'EUR/USD': 1.10,
    'EUR/PLN': 4.30,
    'USD/PLN': 3.90
  });

  // Forward points for different tenors (1-12 months)
  // These are expressed in pips (0.0001 for EUR/USD, USD/PLN and 0.001 for EUR/PLN)
  const [forwardPoints, setForwardPoints] = useState({
    'EUR/USD': [10, 22, 35, 48, 60, 72, 85, 98, 110, 123, 135, 148],
    'EUR/PLN': [35, 72, 110, 150, 190, 230, 270, 310, 350, 390, 430, 470],
    'USD/PLN': [25, 52, 80, 110, 140, 170, 200, 230, 260, 290, 320, 350]
  });

  // Calculate pip values for different currency pairs
  const getPipValue = (currencyPair) => {
    if (currencyPair === 'EUR/PLN' || currencyPair === 'USD/PLN') {
      return 0.0001;
    }
    return 0.0001; // EUR/USD
  };

  // State for currency amounts, hedging percentages and rates
  const [currencyData, setCurrencyData] = useState(() => {
    const initialData = [];
    for (let i = 0; i < 12; i++) {
      initialData.push({
        month: i + 1,
        monthName: new Date(2025, i, 1).toLocaleString('default', { month: 'short' }),
        plannedSale: 100000,
        hedgePercentage: i < 3 ? 80 : i < 6 ? 60 : i < 9 ? 40 : 20,
      });
    }
    return initialData;
  });

  const [budgetRate, setBudgetRate] = useState(1.05);
  const [baseCurrency, setBaseCurrency] = useState('EUR');
  const [targetCurrency, setTargetCurrency] = useState('USD');
  const [currencyPair, setCurrencyPair] = useState('EUR/USD');

  // Calculate forward rates based on spot rate and forward points
  const calculateForwardRates = () => {
    return currencyData.map((item, index) => {
      const forwardPointValue = forwardPoints[currencyPair][index] * getPipValue(currencyPair);
      return spotRates[currencyPair] + forwardPointValue;
    });
  };

  // Update forward rates when relevant inputs change
  useEffect(() => {
    const newRates = calculateForwardRates();
    const updatedData = currencyData.map((item, index) => ({
      ...item,
      forwardRate: newRates[index],
      spotRate: spotRates[currencyPair]
    }));
    setCurrencyData(updatedData);
  }, [spotRates, currencyPair, forwardPoints]);

  // Update currency pair when base or target currency changes
  useEffect(() => {
    const newPair = `${baseCurrency}/${targetCurrency}`;
    if (Object.keys(spotRates).includes(newPair)) {
      setCurrencyPair(newPair);
    } else {
      // If the pair doesn't exist in our data, we need to find a way to derive it
      if (baseCurrency === 'PLN' && targetCurrency === 'EUR') {
        setCurrencyPair('EUR/PLN');
        // Need to invert the rate for display
      } else if (baseCurrency === 'PLN' && targetCurrency === 'USD') {
        setCurrencyPair('USD/PLN');
        // Need to invert the rate for display
      } else if (baseCurrency === 'USD' && targetCurrency === 'EUR') {
        setCurrencyPair('EUR/USD');
        // Need to invert the rate for display
      }
    }
  }, [baseCurrency, targetCurrency]);

  // Calculate hedging metrics based on input data
  const [hedgingResults, setHedgingResults] = useState([]);

  useEffect(() => {
    const results = currencyData.map(item => {
      // Get actual rate - handle inverted pairs
      let actualSpotRate = item.spotRate;
      let actualForwardRate = item.forwardRate;
      
      if ((baseCurrency === 'PLN' && targetCurrency === 'EUR') || 
          (baseCurrency === 'PLN' && targetCurrency === 'USD') ||
          (baseCurrency === 'USD' && targetCurrency === 'EUR')) {
        actualSpotRate = 1 / item.spotRate;
        actualForwardRate = 1 / item.forwardRate;
      }
      
      const hedgedAmount = item.plannedSale * (item.hedgePercentage / 100);
      const unhedgedAmount = item.plannedSale - hedgedAmount;
      
      const hedgedValue = hedgedAmount * actualForwardRate;
      const unhedgedValue = unhedgedAmount * actualSpotRate;
      const totalValue = hedgedValue + unhedgedValue;
      
      const effectiveRate = totalValue / item.plannedSale;
      const budgetDeviation = ((effectiveRate - budgetRate) / budgetRate) * 100;
      
      return {
        ...item,
        actualSpotRate,
        actualForwardRate,
        hedgedAmount,
        unhedgedAmount,
        hedgedValue,
        unhedgedValue,
        totalValue,
        effectiveRate,
        budgetDeviation,
        isBelowBudget: effectiveRate < budgetRate
      };
    });
    
    setHedgingResults(results);
  }, [currencyData, budgetRate, baseCurrency, targetCurrency]);

  // Handle input changes
  const handleCurrencyDataChange = (index, field, value) => {
    const newData = [...currencyData];
    newData[index][field] = value;
    setCurrencyData(newData);
  };

  // Handle spot rate change
  const handleSpotRateChange = (value) => {
    const newSpotRates = {...spotRates};
    newSpotRates[currencyPair] = value;
    setSpotRates(newSpotRates);
  };

  // Handle forward points change
  const handleForwardPointsChange = (index, value) => {
    const newForwardPoints = {...forwardPoints};
    newForwardPoints[currencyPair][index] = value;
    setForwardPoints(newForwardPoints);
    
    // Recalculate forward rates
    const newRates = calculateForwardRates();
    const updatedData = [...currencyData];
    updatedData[index].forwardRate = newRates[index];
    setCurrencyData(updatedData);
  };

  // Handle currency changes
  const handleCurrencyChange = (type, value) => {
    if (type === 'base') {
      setBaseCurrency(value);
    } else {
      setTargetCurrency(value);
    }
  };

  return (
    <div className="p-6 bg-gray-50 min-h-screen">
      <h1 className="text-2xl font-bold text-center mb-6">FX Risk Management Dashboard</h1>
      
      {/* Currency and budget settings */}
      <div className="bg-white p-4 rounded-lg shadow mb-6">
        <h2 className="text-lg font-semibold mb-3">Currency Settings</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium mb-1">Base Currency</label>
            <select 
              className="w-full p-2 border rounded"
              value={baseCurrency}
              onChange={(e) => handleCurrencyChange('base', e.target.value)}
            >
              <option value="EUR">EUR</option>
              <option value="USD">USD</option>
              <option value="PLN">PLN</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Target Currency</label>
            <select 
              className="w-full p-2 border rounded"
              value={targetCurrency}
              onChange={(e) => handleCurrencyChange('target', e.target.value)}
            >
              <option value="USD">USD</option>
              <option value="EUR">EUR</option>
              <option value="PLN">PLN</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Budget Rate ({baseCurrency}/{targetCurrency})</label>
            <input 
              type="number" 
              step="0.0001"
              className="w-full p-2 border rounded"
              value={budgetRate}
              onChange={(e) => setBudgetRate(parseFloat(e.target.value))}
            />
          </div>
        </div>
        
        <div className="mt-4">
          <h3 className="text-md font-semibold mb-2">Currency Pair: {currencyPair}</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Spot Rate</label>
              <input 
                type="number" 
                step="0.0001"
                className="w-full p-2 border rounded"
                value={spotRates[currencyPair]}
                onChange={(e) => handleSpotRateChange(parseFloat(e.target.value))}
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Forward Points Calculation</label>
              <p className="text-sm text-gray-600">Forward Rate = Spot Rate + (Forward Points × Pip Value)</p>
            </div>
          </div>
        </div>
      </div>
      
      {/* Monthly forecast data input */}
      <div className="bg-white p-4 rounded-lg shadow mb-6 overflow-x-auto">
        <h2 className="text-lg font-semibold mb-3">Monthly Currency Exposure</h2>
        <table className="w-full border-collapse">
          <thead>
            <tr className="bg-gray-100">
              <th className="p-2 border text-left">Month</th>
              <th className="p-2 border text-left">Planned Sale ({baseCurrency})</th>
              <th className="p-2 border text-left">Hedge %</th>
              <th className="p-2 border text-left">Spot Rate</th>
              <th className="p-2 border text-left">Forward Points</th>
              <th className="p-2 border text-left">Forward Rate</th>
            </tr>
          </thead>
          <tbody>
            {currencyData.map((item, index) => (
              <tr key={index} className={index % 2 === 0 ? "bg-gray-50" : ""}>
                <td className="p-2 border">{item.monthName}</td>
                <td className="p-2 border">
                  <input
                    type="number"
                    className="w-full p-1 border rounded"
                    value={item.plannedSale}
                    onChange={(e) => handleCurrencyDataChange(index, 'plannedSale', parseFloat(e.target.value))}
                  />
                </td>
                <td className="p-2 border">
                  <input
                    type="number"
                    min="0"
                    max="100"
                    className="w-full p-1 border rounded"
                    value={item.hedgePercentage}
                    onChange={(e) => handleCurrencyDataChange(index, 'hedgePercentage', parseFloat(e.target.value))}
                  />
                </td>
                <td className="p-2 border text-right">
                  {item.spotRate?.toFixed(4) || spotRates[currencyPair]?.toFixed(4)}
                </td>
                <td className="p-2 border">
                  <input
                    type="number"
                    className="w-full p-1 border rounded"
                    value={forwardPoints[currencyPair][index]}
                    onChange={(e) => handleForwardPointsChange(index, parseFloat(e.target.value))}
                  />
                </td>
                <td className="p-2 border text-right">
                  {item.forwardRate?.toFixed(4) || '-'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      
      {/* Hedging strategy visualization */}
      <div className="bg-white p-4 rounded-lg shadow mb-6">
        <h2 className="text-lg font-semibold mb-3">Hedging Results</h2>
        <div className="h-64 mb-6">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={hedgingResults}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="monthName" />
              <YAxis yAxisId="left" orientation="left" domain={['auto', 'auto']} />
              <YAxis yAxisId="right" orientation="right" domain={[0, 100]} />
              <Tooltip />
              <Legend />
              <Line 
                yAxisId="left"
                type="monotone" 
                dataKey="effectiveRate" 
                name={`Effective Rate (${baseCurrency}/${targetCurrency})`} 
                stroke="#4299e1" 
                strokeWidth={2} 
              />
              <Line 
                yAxisId="left"
                type="monotone" 
                dataKey="actualForwardRate" 
                name={`Forward Rate (${baseCurrency}/${targetCurrency})`} 
                stroke="#9f7aea" 
                strokeWidth={2} 
              />
              <Line 
                yAxisId="left"
                type="monotone" 
                dataKey={() => budgetRate} 
                name={`Budget Rate (${baseCurrency}/${targetCurrency})`} 
                stroke="#f56565" 
                strokeWidth={2} 
                dot={false}
              />
              <Line 
                yAxisId="right"
                type="monotone" 
                dataKey="hedgePercentage" 
                name="Hedge %" 
                stroke="#68d391" 
                strokeWidth={2} 
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
        
        {/* Hedging summary table */}
        <h3 className="text-md font-semibold mb-2">Hedging Summary</h3>
        <div className="overflow-x-auto">
          <table className="w-full border-collapse">
            <thead>
              <tr className="bg-gray-100">
                <th className="p-2 border text-left">Month</th>
                <th className="p-2 border text-right">Planned ({baseCurrency})</th>
                <th className="p-2 border text-right">Hedge %</th>
                <th className="p-2 border text-right">Hedged ({baseCurrency})</th>
                <th className="p-2 border text-right">Unhedged ({baseCurrency})</th>
                <th className="p-2 border text-right">Effective Rate</th>
                <th className="p-2 border text-right">Budget Deviation</th>
                <th className="p-2 border text-right">Status</th>
              </tr>
            </thead>
            <tbody>
              {hedgingResults.map((item, index) => (
                <tr key={index} className={item.isBelowBudget ? "bg-red-100" : "bg-green-100"}>
                  <td className="p-2 border">{item.monthName}</td>
                  <td className="p-2 border text-right">{item.plannedSale.toLocaleString()}</td>
                  <td className="p-2 border text-right">{item.hedgePercentage}%</td>
                  <td className="p-2 border text-right">{Math.round(item.hedgedAmount).toLocaleString()}</td>
                  <td className="p-2 border text-right">{Math.round(item.unhedgedAmount).toLocaleString()}</td>
                  <td className="p-2 border text-right">{item.effectiveRate?.toFixed(4) || '-'}</td>
                  <td className="p-2 border text-right">{item.budgetDeviation?.toFixed(2) || '-'}%</td>
                  <td className="p-2 border text-right">
                    {item.isBelowBudget 
                      ? <span className="text-red-600 font-semibold">Below Budget</span> 
                      : <span className="text-green-600 font-semibold">Above Budget</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      
      {/* Summary statistics */}
      <div className="bg-white p-4 rounded-lg shadow">
        <h2 className="text-lg font-semibold mb-3">Risk Assessment</h2>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="p-3 bg-blue-50 rounded-lg">
            <h3 className="font-semibold">Total Exposure</h3>
            <p className="text-lg">{hedgingResults.reduce((sum, item) => sum + item.plannedSale, 0).toLocaleString()} {baseCurrency}</p>
          </div>
          <div className="p-3 bg-purple-50 rounded-lg">
            <h3 className="font-semibold">Average Hedge Ratio</h3>
            <p className="text-lg">{(hedgingResults.reduce((sum, item) => sum + (item.hedgePercentage || 0), 0) / hedgingResults.length).toFixed(1)}%</p>
          </div>
          <div className="p-3 bg-yellow-50 rounded-lg">
            <h3 className="font-semibold">Average Forward Points</h3>
            <p className="text-lg">{(forwardPoints[currencyPair].reduce((sum, points) => sum + points, 0) / forwardPoints[currencyPair].length).toFixed(1)}</p>
          </div>
          <div className={`p-3 ${hedgingResults.some(item => item.isBelowBudget) ? "bg-red-50" : "bg-green-50"} rounded-lg`}>
            <h3 className="font-semibold">Budget Risk</h3>
            <p className="text-lg">{hedgingResults.filter(item => item.isBelowBudget).length} months below budget</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default FxRiskManagementDashboard;
