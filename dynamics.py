import React, { useState, useMemo, useEffect } from 'react';

function PivotTable() {
  const [csvData, setCsvData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showOnlyTrades, setShowOnlyTrades] = useState(false);
  const [sortColumn, setSortColumn] = useState('date');
  const [sortDirection, setSortDirection] = useState('desc');

  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true);
        
        const csvContent = await window.fs.readFile('USD_PLN Historical Data 18.csv', { encoding: 'utf8' });
        
        const lines = csvContent.trim().split('\n');
        const headers = lines[0].split(',').map(h => h.replace(/"/g, ''));
        
        const rawData = [];
        for (let i = 1; i < lines.length; i++) {
          const values = lines[i].split(',').map(v => v.replace(/"/g, ''));
          if (values.length >= 7) {
            rawData.push({
              date: new Date(values[0]),
              dateStr: values[0],
              open: parseFloat(values[2]) || 0,
              high: parseFloat(values[3]) || 0,
              low: parseFloat(values[4]) || 0,
              close: parseFloat(values[1]) || 0,
              changePercent: values[6]
            });
          }
        }
        
        rawData.sort((a, b) => a.date - b.date);
        
        const processedData = [];
        
        for (let i = 0; i < rawData.length; i++) {
          const currentDay = rawData[i];
          let pivots = null;
          let signal = 'NO TRADE';
          let pnl = null;
          let pnlPercent = null;
          
          if (i >= 7) {
            const last7Days = rawData.slice(i - 7, i);
            const avgHigh = last7Days.reduce((sum, day) => sum + day.high, 0) / 7;
            const avgLow = last7Days.reduce((sum, day) => sum + day.low, 0) / 7;
            const avgClose = last7Days.reduce((sum, day) => sum + day.close, 0) / 7;
            const pivotPoint = (avgHigh + avgLow + avgClose) / 3;
            
            pivots = {
              PP: pivotPoint,
              R1: (2 * pivotPoint) - avgLow,
              R2: pivotPoint + (avgHigh - avgLow),
              S1: (2 * pivotPoint) - avgHigh,
              S2: pivotPoint - (avgHigh - avgLow)
            };
            
            if (currentDay.open > pivots.PP) {
              signal = 'BUY';
              pnl = currentDay.close - currentDay.open;
            } else if (currentDay.open < pivots.PP) {
              signal = 'SELL';
              pnl = currentDay.open - currentDay.close;
            }
            
            if (pnl !== null) {
              pnlPercent = (pnl / currentDay.open) * 100;
            }
          }
          
          processedData.push({
            date: currentDay.dateStr,
            open: currentDay.open,
            high: currentDay.high,
            low: currentDay.low,
            close: currentDay.close,
            PP: pivots ? pivots.PP : null,
            R1: pivots ? pivots.R1 : null,
            R2: pivots ? pivots.R2 : null,
            S1: pivots ? pivots.S1 : null,
            S2: pivots ? pivots.S2 : null,
            signal,
            pnl,
            pnlPercent
          });
        }
        
        setCsvData(processedData);
        setError(null);
      } catch (err) {
        console.error('Error loading CSV:', err);
        setError('Failed to load CSV file. Make sure "USD_PLN Historical Data 18.csv" is uploaded.');
      } finally {
        setLoading(false);
      }
    };
    
    loadData();
  }, []);

  const filteredData = useMemo(() => {
    if (showOnlyTrades) {
      return csvData.filter(row => row.signal !== 'NO TRADE');
    }
    return csvData;
  }, [csvData, showOnlyTrades]);

  const sortedData = useMemo(() => {
    return [...filteredData].sort((a, b) => {
      if (sortColumn === 'date') {
        const dateA = new Date(a.date);
        const dateB = new Date(b.date);
        return sortDirection === 'asc' ? dateA - dateB : dateB - dateA;
      }
      if (sortColumn === 'pnl') {
        const aVal = a.pnl || 0;
        const bVal = b.pnl || 0;
        return sortDirection === 'asc' ? aVal - bVal : bVal - aVal;
      }
      if (sortColumn === 'signal') {
        return sortDirection === 'asc' ? a.signal.localeCompare(b.signal) : b.signal.localeCompare(a.signal);
      }
      return 0;
    });
  }, [filteredData, sortColumn, sortDirection]);

  const handleSort = (column) => {
    if (sortColumn === column) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortColumn(column);
      setSortDirection('desc');
    }
  };

  const tradingDays = csvData.filter(row => row.signal !== 'NO TRADE');
  const buyTrades = tradingDays.filter(row => row.signal === 'BUY');
  const sellTrades = tradingDays.filter(row => row.signal === 'SELL');
  const winningTrades = tradingDays.filter(row => row.pnl > 0);
  const totalPnL = tradingDays.reduce((sum, row) => sum + (row.pnl || 0), 0);

  const formatNumber = (num, decimals = 4) => {
    if (num === null || num === undefined) return '—';
    return num.toFixed(decimals);
  };

  const getRowColor = (row) => {
    if (row.signal === 'NO TRADE') return 'bg-gray-50';
    if (row.signal === 'BUY') return row.pnl > 0 ? 'bg-green-50' : 'bg-red-50';
    if (row.signal === 'SELL') return row.pnl > 0 ? 'bg-green-50' : 'bg-red-50';
    return '';
  };

  if (loading) {
    return (
      <div className="w-full p-6 bg-gray-50">
        <div className="bg-white rounded-lg shadow-lg p-6">
          <div className="flex items-center justify-center h-64">
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
              <p className="text-gray-600">Loading and processing CSV data...</p>
              <p className="text-sm text-gray-500 mt-2">Calculating 7-day rolling pivot points</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="w-full p-6 bg-gray-50">
        <div className="bg-white rounded-lg shadow-lg p-6">
          <div className="text-center h-64 flex items-center justify-center">
            <div>
              <div className="text-red-600 text-xl mb-4">⚠️ Error Loading Data</div>
              <p className="text-gray-600 mb-4">{error}</p>
              <p className="text-sm text-gray-500">
                Please make sure you have uploaded the CSV file named "USD_PLN Historical Data 18.csv"
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full p-6 bg-gray-50">
      <div className="bg-white rounded-lg shadow-lg p-6">
        <div className="mb-6">
          <h2 className="text-2xl font-bold text-gray-800 mb-2">7-Day Rolling Pivot Points Trading Strategy</h2>
          <p className="text-gray-600">Live analysis of your uploaded USD/PLN CSV data</p>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div className="p-4 bg-blue-50 rounded-lg">
            <div className="text-sm text-blue-600">Total Days</div>
            <div className="text-xl font-bold text-blue-800">{csvData.length}</div>
          </div>
          <div className="p-4 bg-green-50 rounded-lg">
            <div className="text-sm text-green-600">Trading Days</div>
            <div className="text-xl font-bold text-green-800">{tradingDays.length}</div>
          </div>
          <div className="p-4 bg-yellow-50 rounded-lg">
            <div className="text-sm text-yellow-600">Win Rate</div>
            <div className="text-xl font-bold text-yellow-800">
              {tradingDays.length > 0 ? ((winningTrades.length / tradingDays.length) * 100).toFixed(1) : 0}%
            </div>
          </div>
          <div className="p-4 bg-purple-50 rounded-lg">
            <div className="text-sm text-purple-600">Total P&L</div>
            <div className={`text-xl font-bold ${totalPnL >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              {formatNumber(totalPnL)}
            </div>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-4 mb-6">
          <div className="p-3 bg-blue-100 rounded">
            <div className="text-sm font-medium text-blue-800">BUY Signals</div>
            <div className="text-lg font-bold text-blue-900">
              {buyTrades.length} ({tradingDays.length > 0 ? ((buyTrades.length / tradingDays.length) * 100).toFixed(1) : 0}%)
            </div>
            <div className="text-xs text-blue-600">
              Win Rate: {buyTrades.length > 0 ? ((buyTrades.filter(t => t.pnl > 0).length / buyTrades.length) * 100).toFixed(1) : 0}%
            </div>
          </div>
          <div className="p-3 bg-red-100 rounded">
            <div className="text-sm font-medium text-red-800">SELL Signals</div>
            <div className="text-lg font-bold text-red-900">
              {sellTrades.length} ({tradingDays.length > 0 ? ((sellTrades.length / tradingDays.length) * 100).toFixed(1) : 0}%)
            </div>
            <div className="text-xs text-red-600">
              Win Rate: {sellTrades.length > 0 ? ((sellTrades.filter(t => t.pnl > 0).length / sellTrades.length) * 100).toFixed(1) : 0}%
            </div>
          </div>
          <div className="p-3 bg-gray-100 rounded">
            <div className="text-sm font-medium text-gray-800">No Trade</div>
            <div className="text-lg font-bold text-gray-900">
              {csvData.filter(row => row.signal === 'NO TRADE').length}
            </div>
            <div className="text-xs text-gray-600">
              First 7 days
            </div>
          </div>
        </div>

        <div className="mb-4 flex gap-4 items-center">
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={showOnlyTrades}
              onChange={(e) => setShowOnlyTrades(e.target.checked)}
              className="rounded"
            />
            <span className="text-sm font-medium">Show only trading days</span>
          </label>
          <div className="text-sm text-gray-600">
            Showing {sortedData.length} of {csvData.length} rows
          </div>
        </div>

        <div className="mb-6 p-4 bg-blue-50 rounded-lg">
          <h3 className="font-semibold text-blue-800 mb-2">Strategy Rules:</h3>
          <div className="text-sm text-blue-700 space-y-1">
            <p><strong>BUY Signal:</strong> When Open Price > Pivot Point (PP)</p>
            <p><strong>SELL Signal:</strong> When Open Price < Pivot Point (PP)</p>
            <p><strong>Exit:</strong> Close all positions at end of day</p>
            <p><strong>Pivot Calculation:</strong> 7-day rolling average of (High + Low + Close) / 3</p>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-100 sticky top-0">
              <tr>
                <th 
                  className="p-2 text-left cursor-pointer hover:bg-gray-200"
                  onClick={() => handleSort('date')}
                >
                  Date {sortColumn === 'date' && (sortDirection === 'asc' ? '↑' : '↓')}
                </th>
                <th className="p-2 text-right">Open</th>
                <th className="p-2 text-right">High</th>
                <th className="p-2 text-right">Low</th>
                <th className="p-2 text-right">Close</th>
                <th className="p-2 text-right">Pivot Point</th>
                <th className="p-2 text-right">R1</th>
                <th className="p-2 text-right">R2</th>
                <th className="p-2 text-right">S1</th>
                <th className="p-2 text-right">S2</th>
                <th 
                  className="p-2 text-center cursor-pointer hover:bg-gray-200"
                  onClick={() => handleSort('signal')}
                >
                  Signal {sortColumn === 'signal' && (sortDirection === 'asc' ? '↑' : '↓')}
                </th>
                <th 
                  className="p-2 text-right cursor-pointer hover:bg-gray-200"
                  onClick={() => handleSort('pnl')}
                >
                  P&L {sortColumn === 'pnl' && (sortDirection === 'asc' ? '↑' : '↓')}
                </th>
                <th className="p-2 text-right">P&L %</th>
              </tr>
            </thead>
            <tbody>
              {sortedData.map((row, index) => (
                <tr key={index} className={`border-b ${getRowColor(row)} hover:bg-gray-100`}>
                  <td className="p-2 font-medium">{row.date}</td>
                  <td className="p-2 text-right">{formatNumber(row.open)}</td>
                  <td className="p-2 text-right">{formatNumber(row.high)}</td>
                  <td className="p-2 text-right">{formatNumber(row.low)}</td>
                  <td className="p-2 text-right">{formatNumber(row.close)}</td>
                  <td className="p-2 text-right font-medium text-red-600">
                    {formatNumber(row.PP)}
                  </td>
                  <td className="p-2 text-right text-orange-600">
                    {formatNumber(row.R1)}
                  </td>
                  <td className="p-2 text-right text-orange-500">
                    {formatNumber(row.R2)}
                  </td>
                  <td className="p-2 text-right text-green-600">
                    {formatNumber(row.S1)}
                  </td>
                  <td className="p-2 text-right text-green-500">
                    {formatNumber(row.S2)}
                  </td>
                  <td className="p-2 text-center">
                    <span className={`px-2 py-1 rounded text-xs font-medium ${
                      row.signal === 'BUY' ? 'bg-blue-100 text-blue-800' :
                      row.signal === 'SELL' ? 'bg-red-100 text-red-800' :
                      'bg-gray-100 text-gray-600'
                    }`}>
                      {row.signal}
                    </span>
                  </td>
                  <td className={`p-2 text-right font-medium ${
                    row.pnl === null ? 'text-gray-400' :
                    row.pnl > 0 ? 'text-green-600' : 'text-red-600'
                  }`}>
                    {formatNumber(row.pnl)}
                  </td>
                  <td className={`p-2 text-right ${
                    row.pnlPercent === null ? 'text-gray-400' :
                    row.pnlPercent > 0 ? 'text-green-600' : 'text-red-600'
                  }`}>
                    {row.pnlPercent !== null ? `${row.pnlPercent.toFixed(2)}%` : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="mt-4 text-xs text-gray-600 space-y-1">
          <p><strong>Color Legend:</strong></p>
          <p>• <span className="bg-green-50 px-1">Green rows</span> = Profitable trades</p>
          <p>• <span className="bg-red-50 px-1">Red rows</span> = Losing trades</p>
          <p>• <span className="bg-gray-50 px-1">Gray rows</span> = No trading signal (first 7 days)</p>
          <p>• <span className="text-red-600">Red PP</span> = Main pivot point, <span className="text-orange-600">Orange R1/R2</span> = Resistance levels, <span className="text-green-600">Green S1/S2</span> = Support levels</p>
        </div>

        <div className="mt-4 p-3 bg-gray-100 rounded text-sm">
          <p><strong>Data Source:</strong> USD_PLN Historical Data 18.csv</p>
          <p><strong>Processed:</strong> {csvData.length} total rows, {tradingDays.length} trading signals generated</p>
          <p><strong>Date Range:</strong> {csvData.length > 0 ? `${csvData[0].date} to ${csvData[csvData.length-1].date}` : 'No data'}</p>
        </div>
      </div>
    </div>
  );
}

export default PivotTable;
