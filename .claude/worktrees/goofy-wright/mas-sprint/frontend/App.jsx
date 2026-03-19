// App.jsx — Main three-tab shell for MAS Job Search Sprint
// Shared state for company data across all tabs

const App = () => {
  const [activeTab, setActiveTab] = React.useState('dashboard');
  const [companies, setCompanies] = React.useState(
    JSON.parse(JSON.stringify(window.TIER1_COMPANIES))
  );
  const [museCompanyId, setMuseCompanyId] = React.useState('');

  // Get password from sessionStorage (set by login gate)
  const password = sessionStorage.getItem('mas_password');

  // API call helper — proxies through backend
  const apiCall = async (body) => {
    try {
      const API_BASE = window.MAS_API_URL || '';
      const response = await fetch(`${API_BASE}/api/claude`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-mas-password': password
        },
        body: JSON.stringify(body)
      });

      if (response.status === 401) {
        sessionStorage.removeItem('mas_password');
        window.location.reload();
        return { error: 'Session expired. Please log in again.' };
      }

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        return { error: errData.detail || errData.error || `HTTP ${response.status}` };
      }

      return await response.json();
    } catch (err) {
      return { error: `Network error: ${err.message}` };
    }
  };

  // Update a company's data (status, notes, etc.)
  const updateCompany = (companyId, updates) => {
    setCompanies(prev => prev.map(c =>
      c.id === companyId ? { ...c, ...updates } : c
    ));
  };

  // Open MUSE tab with a specific company
  const openMuse = (company) => {
    setMuseCompanyId(company.id);
    setActiveTab('muse');
  };

  const tabs = [
    { id: 'dashboard', label: 'Track 2 \u2014 Intelligence', icon: '\uD83D\uDCCA' },
    { id: 'muse', label: 'MUSE \u2014 Outreach', icon: '\u270D\uFE0F' },
    { id: 'compass', label: 'COMPASS \u2014 Brief', icon: '\uD83E\uDDED' }
  ];

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4">
          <div className="flex items-center justify-between h-14">
            <div className="flex items-center gap-3">
              <h1 className="text-lg font-bold text-gray-900">MAS</h1>
              <span className="text-xs text-gray-400 hidden sm:inline">Job Search Sprint</span>
            </div>

            {/* Tab Navigation */}
            <nav className="flex gap-1">
              {tabs.map(tab => (
                <button
                  key={tab.id}
                  className={`px-3 py-2 text-sm font-medium rounded-lg transition-colors ${
                    activeTab === tab.id
                      ? 'bg-indigo-50 text-indigo-700'
                      : 'text-gray-500 hover:text-gray-700 hover:bg-gray-50'
                  }`}
                  onClick={() => setActiveTab(tab.id)}>
                  <span className="mr-1.5">{tab.icon}</span>
                  <span className="hidden sm:inline">{tab.label}</span>
                </button>
              ))}
            </nav>

            {/* Logout */}
            <button
              className="text-xs text-gray-400 hover:text-gray-600 transition-colors"
              onClick={() => {
                sessionStorage.removeItem('mas_password');
                window.location.reload();
              }}>
              Logout
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 py-6">
        {activeTab === 'dashboard' && (
          <Dashboard
            companies={companies}
            onUpdateCompany={updateCompany}
            onOpenMuse={openMuse}
          />
        )}
        {activeTab === 'muse' && (
          <Muse
            companies={companies}
            selectedCompanyId={museCompanyId}
            onUpdateCompany={updateCompany}
            apiCall={apiCall}
          />
        )}
        {activeTab === 'compass' && (
          <Compass
            companies={companies}
            apiCall={apiCall}
          />
        )}
      </main>

      {/* Footer */}
      <footer className="text-center py-4 text-xs text-gray-400 border-t bg-white mt-8">
        MAS Job Search Sprint &middot; Mike Berry &middot; San Carlos, CA &middot; {new Date().getFullYear()}
      </footer>
    </div>
  );
};

window.App = App;
