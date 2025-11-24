// ============================================================================
// R2 STRATEGY MODULE - 3 vs 6 FORWARDS
// Dodaj ten kod do swojego kalendarz-fx.html
// ============================================================================

// Rozszerzenie appState o strategię
appState.strategyMode = 3; // 3 lub 6 forwardów
appState.historicalData = [];
appState.r2Signals = [];
appState.activeForwardsData = [];

// Funkcja do parsowania CSV
function parseCSVDate(dateStr) {
    // Parse MM/DD/YYYY format
    const parts = dateStr.split('/');
    if (parts.length === 3) {
        return new Date(parts[2], parts[0] - 1, parts[1]);
    }
    return null;
}

// Obliczanie Pivot Points (MT5 style)
function calculatePivotPoints(data, index, lookback = 14) {
    if (index < lookback) return null;
    
    const window = data.slice(index - lookback, index);
    const avgHigh = window.reduce((sum, d) => sum + d.high, 0) / lookback;
    const avgLow = window.reduce((sum, d) => sum + d.low, 0) / lookback;
    const avgClose = window.reduce((sum, d) => sum + d.close, 0) / lookback;
    const range = avgHigh - avgLow;
    const pivot = (avgHigh + avgLow + avgClose) / 3;
    
    return {
        pivot: pivot,
        r1: pivot + (pivot - avgLow),
        r2: pivot + range,
        s1: pivot - (avgHigh - pivot),
        s2: pivot - range
    };
}

// Upload CSV handler
function handleCSVUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    const statusDiv = document.getElementById('csvStatus');
    statusDiv.innerHTML = '<span class="text-blue-600">📊 Wczytuję dane...</span>';

    const reader = new FileReader();
    reader.onload = function(e) {
        const text = e.target.result;
        const lines = text.trim().split('\n');
        
        appState.historicalData = [];
        let validRows = 0;

        lines.forEach((line, idx) => {
            const cols = line.split(',');
            if (cols.length >= 5) {
                const date = parseCSVDate(cols[0]);
                if (date) {
                    appState.historicalData.push({
                        date: date,
                        close: parseFloat(cols[1]),
                        open: parseFloat(cols[2]),
                        high: parseFloat(cols[3]),
                        low: parseFloat(cols[4])
                    });
                    validRows++;
                }
            }
        });

        // Sort by date ascending
        appState.historicalData.sort((a, b) => a.date - b.date);

        if (validRows > 0) {
            statusDiv.innerHTML = `<span class="text-green-600">✅ Wczytano ${validRows} wierszy danych</span>`;
            calculateR2Signals();
            renderStrategyTab();
        } else {
            statusDiv.innerHTML = '<span class="text-red-600">❌ Błąd: Nie udało się wczytać danych</span>';
        }
    };

    reader.readAsText(file);
}

// Generowanie sygnałów R2
function calculateR2Signals() {
    appState.r2Signals = [];
    
    const today = new Date();
    const oneYearAgo = new Date(today.getFullYear() - 1, today.getMonth(), today.getDate());

    appState.historicalData.forEach((row, index) => {
        // Only Mondays
        if (row.date.getDay() !== 1) return;
        
        // Only last 12 months
        if (row.date < oneYearAgo) return;

        const pivots = calculatePivotPoints(appState.historicalData, index, 14);
        if (!pivots) return;

        // R2 SELL signal: Open >= R2
        if (row.open >= pivots.r2) {
            const forwards = [];
            
            // Strategia 3 forwardy: 0, 30, 60 dni
            if (appState.strategyMode === 3) {
                forwards.push(
                    { num: 1, startOffset: 0, startDate: new Date(row.date) },
                    { num: 2, startOffset: 30, startDate: new Date(row.date.getTime() + 30*24*60*60*1000) },
                    { num: 3, startOffset: 60, startDate: new Date(row.date.getTime() + 60*24*60*60*1000) }
                );
            }
            // Strategia 6 forwardów: 0, 30, 60, 90, 120, 150 dni
            else if (appState.strategyMode === 6) {
                forwards.push(
                    { num: 1, startOffset: 0, startDate: new Date(row.date) },
                    { num: 2, startOffset: 30, startDate: new Date(row.date.getTime() + 30*24*60*60*1000) },
                    { num: 3, startOffset: 60, startDate: new Date(row.date.getTime() + 60*24*60*60*1000) },
                    { num: 4, startOffset: 90, startDate: new Date(row.date.getTime() + 90*24*60*60*1000) },
                    { num: 5, startOffset: 120, startDate: new Date(row.date.getTime() + 120*24*60*60*1000) },
                    { num: 6, startOffset: 150, startDate: new Date(row.date.getTime() + 150*24*60*60*1000) }
                );
            }
            
            appState.r2Signals.push({
                date: row.date,
                open: row.open,
                r2: pivots.r2,
                pivot: pivots.pivot,
                forwards: forwards
            });
        }
    });

    // Update count
    document.getElementById('totalR2Signals').textContent = appState.r2Signals.length;
    document.getElementById('r2SignalsCount').textContent = appState.r2Signals.length;
    
    calculateActiveForwards();
}

// Obliczanie aktywnych forwardów
function calculateActiveForwards() {
    const today = new Date();
    let activeCount = 0;
    let totalExposure = 0;

    appState.r2Signals.forEach(signal => {
        signal.forwards.forEach(fwd => {
            const endDate = new Date(fwd.startDate.getTime() + 60*24*60*60*1000);
            if (fwd.startDate <= today && today <= endDate) {
                activeCount++;
                totalExposure += 1; // EUR 1M per forward
            }
        });
    });

    document.getElementById('activeForwards').textContent = activeCount;
    document.getElementById('totalExposure').textContent = `EUR ${totalExposure}M`;
    
    // Expected P/L based on strategy mode
    const expectedPerYear = appState.strategyMode === 3 ? 479000 : 471000;
    document.getElementById('expectedPnL').textContent = `+${(expectedPerYear/1000).toFixed(0)}k PLN`;
    
    // Update comparison metrics
    updateStrategyComparison();
}

// Zmiana strategii (3 vs 6)
function changeStrategyMode(mode) {
    appState.strategyMode = mode;
    
    // Update button states
    document.getElementById('strategy3Btn').className = mode === 3
        ? 'px-6 py-3 bg-blue-600 text-white rounded-lg font-semibold shadow-lg'
        : 'px-6 py-3 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300';
    
    document.getElementById('strategy6Btn').className = mode === 6
        ? 'px-6 py-3 bg-blue-600 text-white rounded-lg font-semibold shadow-lg'
        : 'px-6 py-3 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300';
    
    // Recalculate signals
    if (appState.historicalData.length > 0) {
        calculateR2Signals();
        renderStrategyTab();
    }
}

// Update strategy comparison
function updateStrategyComparison() {
    const mode = appState.strategyMode;
    
    // Backtest results
    const results = {
        3: {
            total: 5.00,      // +5.00M PLN
            perYear: 479,     // +479k PLN/rok
            winRate: 74.8,    // 74.8%
            perSignal: 61,    // +61k PLN
            signalsPerYear: 7.9
        },
        6: {
            total: 4.95,      // +4.95M PLN
            perYear: 471,     // +471k PLN/rok
            winRate: 70.8,    // 70.8%
            perSignal: 60,    // +60k PLN
            signalsPerYear: 7.8
        }
    };
    
    const data = results[mode];
    
    document.getElementById('strategyTotal').textContent = `+${data.total.toFixed(2)}M PLN`;
    document.getElementById('strategyPerYear').textContent = `+${data.perYear}k PLN`;
    document.getElementById('strategyWinRate').textContent = `${data.winRate}%`;
    document.getElementById('strategyPerSignal').textContent = `+${data.perSignal}k PLN`;
    
    // Update comparison text
    const comparisonDiv = document.getElementById('strategyComparison');
    if (mode === 3) {
        comparisonDiv.innerHTML = `
            <div class="bg-green-50 border border-green-200 rounded-lg p-4">
                <h4 class="font-semibold text-green-800 mb-2">✅ Strategia 3 Forwardy (REKOMENDOWANA)</h4>
                <ul class="text-sm text-green-900 space-y-1">
                    <li>• <strong>Lepszy wynik:</strong> +5.00M vs +4.95M (6 fwd)</li>
                    <li>• <strong>Wyższy win rate:</strong> 74.8% vs 70.8%</li>
                    <li>• <strong>Prostsze zarządzanie:</strong> 3 pozycje vs 6</li>
                    <li>• <strong>Mniejsze exposure:</strong> EUR 3M vs EUR 6M</li>
                    <li>• <strong>Forwardy 4-6 są słabe:</strong> średnio -0.03%</li>
                </ul>
            </div>
        `;
    } else {
        comparisonDiv.innerHTML = `
            <div class="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                <h4 class="font-semibold text-yellow-800 mb-2">⚠️ Strategia 6 Forwardów</h4>
                <ul class="text-sm text-yellow-900 space-y-1">
                    <li>• <strong>Podobny wynik:</strong> +4.95M vs +5.00M (3 fwd)</li>
                    <li>• <strong>Niższy win rate:</strong> 70.8% vs 74.8%</li>
                    <li>• <strong>2× więcej pracy:</strong> 6 pozycji vs 3</li>
                    <li>• <strong>2× większe exposure:</strong> EUR 6M vs EUR 3M</li>
                    <li>• <strong>Problem:</strong> Forwardy 4-6 prawie bezwartościowe</li>
                </ul>
            </div>
        `;
    }
}

// Render strategy tab
function renderStrategyTab() {
    renderR2SignalsTimeline();
    renderR2SignalsTable();
    renderForwardPerformanceChart();
}

// Render timeline with forwards
function renderR2SignalsTimeline() {
    const timeline = document.getElementById('r2SignalsTimeline');
    if (!timeline || appState.r2Signals.length === 0) {
        if (timeline) {
            timeline.innerHTML = `
                <div class="text-center text-gray-500 py-12">
                    <p class="text-lg">Brak sygnałów R2 w ostatnich 12 miesiącach</p>
                    <p class="text-sm mt-2">Wgraj dane historyczne aby zobaczyć sygnały</p>
                </div>
            `;
        }
        return;
    }

    const today = new Date();
    const oneYearAgo = new Date(today.getFullYear() - 1, today.getMonth(), today.getDate());
    const oneYearFromNow = new Date(today.getFullYear() + 1, today.getMonth(), today.getDate());
    
    let html = '<div class="space-y-4">';
    
    // Timeline scale (12 months)
    const months = ['Sty', 'Lut', 'Mar', 'Kwi', 'Maj', 'Cze', 'Lip', 'Sie', 'Wrz', 'Paź', 'Lis', 'Gru'];
    html += '<div class="flex justify-between text-xs text-gray-500 mb-4 border-b pb-2">';
    for (let i = 0; i < 12; i++) {
        const monthDate = new Date(oneYearAgo.getFullYear(), oneYearAgo.getMonth() + i + 1, 1);
        html += `<div class="text-center flex-1">${months[monthDate.getMonth()]}</div>`;
    }
    html += '</div>';

    // Render each signal with its forwards
    appState.r2Signals.forEach((signal, idx) => {
        html += `
            <div class="relative bg-gray-50 rounded-lg p-4 hover:bg-gray-100 transition-colors">
                <div class="flex items-center justify-between mb-3">
                    <div class="text-sm font-semibold text-gray-800">
                        🎯 Sygnał ${idx + 1}: ${signal.date.toLocaleDateString('pl-PL')} (${signal.date.toLocaleDateString('en-US', {weekday: 'short'})})
                    </div>
                    <div class="text-xs text-gray-600">
                        Open: <span class="font-bold text-blue-600">${signal.open.toFixed(4)}</span> | 
                        R2: <span class="font-bold text-purple-600">${signal.r2.toFixed(4)}</span>
                    </div>
                </div>
                <div class="space-y-2">
        `;

        // Colors for forwards
        const colors = [
            'bg-blue-500',
            'bg-green-500', 
            'bg-purple-500',
            'bg-orange-500',
            'bg-pink-500',
            'bg-indigo-500'
        ];

        // Expected P/L per forward (from backtests)
        const expectedPnL = {
            3: [0.79, 0.58, 0.26],  // FWD 1, 2, 3 (ROLL strategy)
            6: [0.79, 0.58, 0.26, -0.05, 0.13, -0.16]  // FWD 1-6
        };

        // Render each forward
        signal.forwards.forEach((fwd, fwdIdx) => {
            const endDate = new Date(fwd.startDate.getTime() + 60*24*60*60*1000);
            const startPercent = Math.max(0, Math.min(100, ((fwd.startDate - oneYearAgo) / (oneYearFromNow - oneYearAgo)) * 100));
            const endPercent = Math.max(0, Math.min(100, ((endDate - oneYearAgo) / (oneYearFromNow - oneYearAgo)) * 100));
            const width = Math.max(2, endPercent - startPercent);
            
            const pnl = expectedPnL[appState.strategyMode][fwdIdx];
            const pnlColor = pnl > 0 ? 'text-green-600' : 'text-red-600';
            
            html += `
                <div class="relative">
                    <div class="flex items-center space-x-2">
                        <span class="text-xs text-gray-600 w-16 font-medium">FWD ${fwd.num}</span>
                        <div class="flex-1 relative h-8 bg-gray-200 rounded">
                            <div class="${colors[fwdIdx]} absolute h-8 rounded timeline-bar flex items-center justify-center cursor-pointer"
                                 style="left: ${startPercent}%; width: ${width}%;"
                                 title="Start: ${fwd.startDate.toLocaleDateString('pl-PL')} | End: ${endDate.toLocaleDateString('pl-PL')} | Expected: ${pnl > 0 ? '+' : ''}${pnl}%">
                                <span class="text-white text-xs font-medium">60d</span>
                            </div>
                        </div>
                        <span class="text-xs ${pnlColor} w-20 font-bold">${pnl > 0 ? '+' : ''}${pnl}%</span>
                        <span class="text-xs text-gray-600 w-24">EUR 1M</span>
                    </div>
                </div>
            `;
        });

        // Total per signal
        const totalPnL = signal.forwards.reduce((sum, fwd, idx) => sum + expectedPnL[appState.strategyMode][idx], 0);
        const totalPLN = totalPnL / 100 * appState.strategyMode * 1000000 * appState.spotRate;

        html += `
                    <div class="mt-3 pt-3 border-t border-gray-300">
                        <div class="flex items-center justify-between text-sm">
                            <span class="text-gray-600">Total per sygnał:</span>
                            <span class="font-bold ${totalPnL > 0 ? 'text-green-600' : 'text-red-600'}">
                                ${totalPnL > 0 ? '+' : ''}${totalPnL.toFixed(2)}% = ${totalPLN > 0 ? '+' : ''}${(totalPLN/1000).toFixed(0)}k PLN
                            </span>
                        </div>
                    </div>
                </div>
            </div>
        `;
    });

    html += '</div>';
    timeline.innerHTML = html;
}

// Render signals table
function renderR2SignalsTable() {
    const table = document.getElementById('r2SignalsTable');
    if (!table || appState.r2Signals.length === 0) {
        if (table) {
            table.innerHTML = '<div class="text-center text-gray-500 py-8">Brak sygnałów do wyświetlenia</div>';
        }
        return;
    }

    let html = `
        <table class="w-full text-sm">
            <thead class="bg-gray-50 border-b border-gray-200">
                <tr>
                    <th class="px-4 py-3 text-left font-medium text-gray-600">Lp.</th>
                    <th class="px-4 py-3 text-left font-medium text-gray-600">Data Sygnału</th>
                    <th class="px-4 py-3 text-left font-medium text-gray-600">Open</th>
                    <th class="px-4 py-3 text-left font-medium text-gray-600">R2</th>
                    <th class="px-4 py-3 text-left font-medium text-gray-600">Pivot</th>
                    <th class="px-4 py-3 text-center font-medium text-gray-600">Forwardy</th>
                    <th class="px-4 py-3 text-right font-medium text-gray-600">Exposure</th>
                    <th class="px-4 py-3 text-right font-medium text-gray-600">Expected P/L</th>
                </tr>
            </thead>
            <tbody class="divide-y divide-gray-200">
    `;

    const expectedPnL = {
        3: [0.79, 0.58, 0.26],
        6: [0.79, 0.58, 0.26, -0.05, 0.13, -0.16]
    };

    appState.r2Signals.forEach((signal, idx) => {
        const totalPnL = signal.forwards.reduce((sum, fwd, fIdx) => sum + expectedPnL[appState.strategyMode][fIdx], 0);
        const totalPLN = totalPnL / 100 * appState.strategyMode * 1000000 * appState.spotRate;

        html += `
            <tr class="hover:bg-gray-50">
                <td class="px-4 py-3 text-gray-800 font-medium">${idx + 1}</td>
                <td class="px-4 py-3 text-gray-800">${signal.date.toLocaleDateString('pl-PL')}</td>
                <td class="px-4 py-3 text-blue-600 font-bold">${signal.open.toFixed(4)}</td>
                <td class="px-4 py-3 text-purple-600 font-bold">${signal.r2.toFixed(4)}</td>
                <td class="px-4 py-3 text-gray-600">${signal.pivot.toFixed(4)}</td>
                <td class="px-4 py-3 text-center">
                    <span class="text-xs text-gray-600">${appState.strategyMode} forwardy</span>
                </td>
                <td class="px-4 py-3 text-right text-gray-800 font-medium">EUR ${appState.strategyMode}M</td>
                <td class="px-4 py-3 text-right font-bold ${totalPnL > 0 ? 'text-green-600' : 'text-red-600'}">
                    ${totalPnL > 0 ? '+' : ''}${(totalPLN/1000).toFixed(0)}k PLN
                </td>
            </tr>
        `;
    });

    html += `
            </tbody>
        </table>
    `;

    table.innerHTML = html;
}

// Render forward performance chart
function renderForwardPerformanceChart() {
    const chart = document.getElementById('forwardPerformanceChart');
    if (!chart) return;

    const data = {
        3: [
            { name: 'FWD 1 (0d)', pnl: 0.79, color: 'bg-blue-500' },
            { name: 'FWD 2 (30d)', pnl: 0.58, color: 'bg-green-500' },
            { name: 'FWD 3 (60d)', pnl: 0.26, color: 'bg-purple-500' }
        ],
        6: [
            { name: 'FWD 1 (0d)', pnl: 0.79, color: 'bg-blue-500' },
            { name: 'FWD 2 (30d)', pnl: 0.58, color: 'bg-green-500' },
            { name: 'FWD 3 (60d)', pnl: 0.26, color: 'bg-purple-500' },
            { name: 'FWD 4 (90d)', pnl: -0.05, color: 'bg-orange-500' },
            { name: 'FWD 5 (120d)', pnl: 0.13, color: 'bg-pink-500' },
            { name: 'FWD 6 (150d)', pnl: -0.16, color: 'bg-indigo-500' }
        ]
    };

    const forwards = data[appState.strategyMode];
    const maxPnl = Math.max(...forwards.map(f => Math.abs(f.pnl)));

    let html = '<div class="space-y-3">';

    forwards.forEach(fwd => {
        const barWidth = Math.abs(fwd.pnl) / maxPnl * 100;
        const isPositive = fwd.pnl > 0;

        html += `
            <div>
                <div class="flex items-center justify-between mb-1">
                    <span class="text-sm font-medium text-gray-700">${fwd.name}</span>
                    <span class="text-sm font-bold ${isPositive ? 'text-green-600' : 'text-red-600'}">
                        ${isPositive ? '+' : ''}${fwd.pnl.toFixed(2)}%
                    </span>
                </div>
                <div class="relative w-full h-6 bg-gray-200 rounded">
                    <div class="${fwd.color} h-6 rounded ${isPositive ? '' : 'opacity-50'}"
                         style="width: ${barWidth}%">
                    </div>
                </div>
            </div>
        `;
    });

    html += '</div>';
    chart.innerHTML = html;
}

// Expose functions globally
window.handleCSVUpload = handleCSVUpload;
window.changeStrategyMode = changeStrategyMode;
