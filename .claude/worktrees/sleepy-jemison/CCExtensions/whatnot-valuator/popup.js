// popup.js - Extension popup logic
// NO require() or module.exports - pure browser JavaScript

document.addEventListener('DOMContentLoaded', () => {
  loadStats();
  
  document.getElementById('export-btn').addEventListener('click', exportSales);
  document.getElementById('refresh-btn').addEventListener('click', loadStats);
  document.getElementById('clear-btn').addEventListener('click', clearHistory);
});

function loadStats() {
  // Get stats from background
  chrome.runtime.sendMessage({ type: 'GET_STATS' }, (response) => {
    if (chrome.runtime.lastError) {
      console.log('Error:', chrome.runtime.lastError);
      return;
    }
    
    const stats = response?.stats || { totalSales: 0, activeTabs: 0, recentSales: [] };
    
    // Update stat boxes
    document.getElementById('total-sales').textContent = stats.totalSales || 0;
    document.getElementById('active-tabs').textContent = stats.activeTabs || 0;
    
    // Calculate total value
    const totalValue = (stats.recentSales || []).reduce((sum, s) => sum + (s.price || 0), 0);
    document.getElementById('total-value').textContent = `$${totalValue.toLocaleString()}`;
    
    // Update recent sales list
    updateSalesList(stats.recentSales || []);
  });
  
  // Get active tabs
  chrome.runtime.sendMessage({ type: 'GET_ALL_TABS' }, (response) => {
    if (chrome.runtime.lastError) return;
    
    const tabs = response?.tabs || [];
    updateTabsList(tabs);
    document.getElementById('active-tabs').textContent = tabs.length;
  });
}

function updateTabsList(tabs) {
  const container = document.getElementById('tabs-list');
  
  if (tabs.length === 0) {
    container.innerHTML = '<div class="empty-state">No active Whatnot tabs</div>';
    return;
  }
  
  container.innerHTML = tabs.map(tab => `
    <div class="tab-item">
      <span class="stream-name">${escapeHtml(tab.title || 'Unknown Stream')}</span>
      <span class="tab-status">● Active</span>
    </div>
  `).join('');
}

function updateSalesList(sales) {
  const container = document.getElementById('sales-list');
  
  if (sales.length === 0) {
    container.innerHTML = '<div class="empty-state">No sales recorded yet</div>';
    return;
  }
  
  container.innerHTML = sales.map(sale => {
    const time = sale.timestamp ? formatTime(sale.timestamp) : '';
    const title = sale.series && sale.issue 
      ? `${sale.series} #${sale.issue}` 
      : (sale.title || 'Unknown').substring(0, 30);
    
    return `
      <div class="sale-item">
        <span class="sale-title">${escapeHtml(title)}</span>
        <span class="sale-price">$${(sale.price || 0).toFixed(0)}</span>
        <span class="sale-time">${time}</span>
      </div>
    `;
  }).join('');
}

function exportSales() {
  chrome.runtime.sendMessage({ type: 'GET_ALL_SALES' }, (response) => {
    if (chrome.runtime.lastError) {
      alert('Error exporting sales');
      return;
    }
    
    const sales = response?.sales || [];
    const json = JSON.stringify(sales, null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    
    const a = document.createElement('a');
    a.href = url;
    a.download = `whatnot-sales-${Date.now()}.json`;
    a.click();
    
    URL.revokeObjectURL(url);
  });
}

function clearHistory() {
  if (confirm('Clear all sale history? This cannot be undone.')) {
    chrome.runtime.sendMessage({ type: 'CLEAR_HISTORY' }, () => {
      loadStats();
    });
  }
}

function formatTime(timestamp) {
  const date = new Date(timestamp);
  const now = new Date();
  const diffMs = now - date;
  const diffMins = Math.floor(diffMs / 60000);
  
  if (diffMins < 1) return 'now';
  if (diffMins < 60) return `${diffMins}m`;
  if (diffMins < 1440) return `${Math.floor(diffMins / 60)}h`;
  return `${Math.floor(diffMins / 1440)}d`;
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}
