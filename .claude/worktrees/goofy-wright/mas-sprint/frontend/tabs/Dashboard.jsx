// Tab 1 — Track 2 Intelligence Dashboard
// Command center for proactive monitoring of all 23 Target companies

const Dashboard = ({ companies, onUpdateCompany, onOpenMuse }) => {
  const [view, setView] = React.useState('grid'); // 'grid' | 'pipeline'
  const [filterBucket, setFilterBucket] = React.useState('all');
  const [filterPriority, setFilterPriority] = React.useState('all');
  const [searchText, setSearchText] = React.useState('');
  const [modalCompany, setModalCompany] = React.useState(null);
  const [modalNotes, setModalNotes] = React.useState('');
  const [modalStatus, setModalStatus] = React.useState('');

  const buckets = ['all', 'MarTech', 'B2C Ecomm', 'Fintech', 'AI/Data', 'B2B SaaS', 'PropTech', 'AI-Native'];
  const priorities = ['all', 'A', 'B', 'C'];

  // Filter companies
  const filtered = companies.filter(c => {
    if (filterBucket !== 'all' && c.bucket !== filterBucket) return false;
    if (filterPriority !== 'all' && c.priority !== filterPriority) return false;
    if (searchText && !c.name.toLowerCase().includes(searchText.toLowerCase()) &&
        !c.bucket.toLowerCase().includes(searchText.toLowerCase())) return false;
    return true;
  });

  // Stats
  const stats = {
    watching: companies.filter(c => c.status === 'watching').length,
    triggered: companies.filter(c => c.status === 'triggered').length,
    outreach: companies.filter(c => c.status === 'outreach_sent').length,
    active: companies.filter(c => c.status === 'active_convo').length
  };

  const openModal = (company) => {
    setModalCompany(company);
    setModalNotes(company.notes || '');
    setModalStatus(company.status);
  };

  const saveModal = () => {
    if (modalCompany) {
      onUpdateCompany(modalCompany.id, { notes: modalNotes, status: modalStatus });
      setModalCompany(null);
    }
  };

  const StatusBadge = ({ status }) => {
    const colors = {
      watching: 'bg-gray-100 text-gray-700',
      triggered: 'bg-amber-100 text-amber-800',
      outreach_sent: 'bg-blue-100 text-blue-800',
      active_convo: 'bg-green-100 text-green-800',
      paused: 'bg-red-100 text-red-700'
    };
    return (
      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${colors[status] || 'bg-gray-100'}`}>
        {window.PIPELINE_LABELS[status]}
      </span>
    );
  };

  const PriorityBadge = ({ priority }) => {
    const style = window.PRIORITY_STYLES[priority];
    return (
      <span className="px-2 py-0.5 rounded text-xs font-bold"
            style={{ backgroundColor: style.bg, color: style.text }}>
        P-{priority}
      </span>
    );
  };

  const BucketTag = ({ bucket }) => {
    const c = window.BUCKET_COLORS[bucket];
    return (
      <span className="px-2 py-0.5 rounded text-xs font-medium"
            style={{ backgroundColor: c.bg, color: c.text, border: `1px solid ${c.border}` }}>
        {bucket}
      </span>
    );
  };

  // Company Card for Grid View
  const CompanyCard = ({ company }) => (
    <div className="bg-white rounded-lg border border-gray-200 p-4 hover:shadow-md transition-shadow cursor-pointer"
         onClick={() => openModal(company)}>
      <div className="flex items-start justify-between mb-2">
        <h3 className="font-semibold text-gray-900">{company.name}</h3>
        <PriorityBadge priority={company.priority} />
      </div>
      <div className="flex gap-1.5 mb-2 flex-wrap">
        <BucketTag bucket={company.bucket} />
        <StatusBadge status={company.status} />
      </div>
      <p className="text-xs text-gray-500 mb-1"><span className="font-medium">Stage:</span> {company.stage}</p>
      <p className="text-xs text-gray-600 mb-2">{company.whyFit}</p>
      <p className="text-xs text-amber-700 bg-amber-50 rounded px-2 py-1 mb-3">
        <span className="font-medium">Trigger:</span> {company.trigger}
      </p>
      {company.notes && (
        <p className="text-xs text-gray-500 italic border-t pt-2 truncate">
          {company.notes}
        </p>
      )}
      <div className="flex gap-2 mt-3">
        <select
          className="text-xs border rounded px-2 py-1 bg-white"
          value={company.status}
          onClick={(e) => e.stopPropagation()}
          onChange={(e) => {
            e.stopPropagation();
            onUpdateCompany(company.id, { status: e.target.value });
          }}>
          {window.PIPELINE_STATUSES.map(s => (
            <option key={s} value={s}>{window.PIPELINE_LABELS[s]}</option>
          ))}
        </select>
        <button
          className="text-xs bg-indigo-600 text-white px-3 py-1 rounded hover:bg-indigo-700 transition-colors"
          onClick={(e) => { e.stopPropagation(); onOpenMuse(company); }}>
          MUSE
        </button>
      </div>
    </div>
  );

  // Pipeline / Kanban View
  const PipelineView = () => {
    const columns = window.PIPELINE_STATUSES.map(status => ({
      status,
      label: window.PIPELINE_LABELS[status],
      companies: filtered.filter(c => c.status === status)
    }));

    const colColors = {
      watching: 'border-gray-300 bg-gray-50',
      triggered: 'border-amber-300 bg-amber-50',
      outreach_sent: 'border-blue-300 bg-blue-50',
      active_convo: 'border-green-300 bg-green-50',
      paused: 'border-red-300 bg-red-50'
    };

    return (
      <div className="flex gap-3 overflow-x-auto pb-4">
        {columns.map(col => (
          <div key={col.status} className={`flex-shrink-0 w-56 rounded-lg border-2 ${colColors[col.status]} p-3`}>
            <h3 className="font-semibold text-sm text-gray-700 mb-2">
              {col.label} <span className="text-gray-400">({col.companies.length})</span>
            </h3>
            <div className="space-y-2">
              {col.companies.map(c => (
                <div key={c.id}
                     className="bg-white rounded border border-gray-200 p-2.5 cursor-pointer hover:shadow-sm transition-shadow"
                     onClick={() => openModal(c)}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-medium text-sm">{c.name}</span>
                    <PriorityBadge priority={c.priority} />
                  </div>
                  <BucketTag bucket={c.bucket} />
                  <p className="text-xs text-gray-500 mt-1.5 truncate">{c.trigger}</p>
                  <button
                    className="text-xs text-indigo-600 hover:text-indigo-800 mt-1.5 font-medium"
                    onClick={(e) => { e.stopPropagation(); onOpenMuse(c); }}>
                    Open in MUSE &rarr;
                  </button>
                </div>
              ))}
              {col.companies.length === 0 && (
                <p className="text-xs text-gray-400 italic text-center py-4">No companies</p>
              )}
            </div>
          </div>
        ))}
      </div>
    );
  };

  return (
    <div className="space-y-4">
      {/* Stats Bar */}
      <div className="grid grid-cols-4 gap-3">
        <div className="bg-gray-50 rounded-lg p-3 text-center border">
          <div className="text-2xl font-bold text-gray-700">{stats.watching}</div>
          <div className="text-xs text-gray-500">Watching</div>
        </div>
        <div className="bg-amber-50 rounded-lg p-3 text-center border border-amber-200">
          <div className="text-2xl font-bold text-amber-700">{stats.triggered}</div>
          <div className="text-xs text-amber-600">Triggered</div>
        </div>
        <div className="bg-blue-50 rounded-lg p-3 text-center border border-blue-200">
          <div className="text-2xl font-bold text-blue-700">{stats.outreach}</div>
          <div className="text-xs text-blue-600">Outreach Sent</div>
        </div>
        <div className="bg-green-50 rounded-lg p-3 text-center border border-green-200">
          <div className="text-2xl font-bold text-green-700">{stats.active}</div>
          <div className="text-xs text-green-600">Active</div>
        </div>
      </div>

      {/* Controls Bar */}
      <div className="flex flex-wrap items-center gap-3 bg-white rounded-lg border p-3">
        {/* View Toggle */}
        <div className="flex bg-gray-100 rounded-lg p-0.5">
          <button
            className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${view === 'grid' ? 'bg-white shadow text-gray-900' : 'text-gray-500'}`}
            onClick={() => setView('grid')}>
            Grid
          </button>
          <button
            className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${view === 'pipeline' ? 'bg-white shadow text-gray-900' : 'text-gray-500'}`}
            onClick={() => setView('pipeline')}>
            Pipeline
          </button>
        </div>

        {/* Bucket Filter */}
        <select
          className="text-xs border rounded-lg px-3 py-1.5 bg-white"
          value={filterBucket}
          onChange={e => setFilterBucket(e.target.value)}>
          {buckets.map(b => (
            <option key={b} value={b}>{b === 'all' ? 'All Buckets' : b}</option>
          ))}
        </select>

        {/* Priority Filter */}
        <select
          className="text-xs border rounded-lg px-3 py-1.5 bg-white"
          value={filterPriority}
          onChange={e => setFilterPriority(e.target.value)}>
          {priorities.map(p => (
            <option key={p} value={p}>{p === 'all' ? 'All Priorities' : `Priority ${p}`}</option>
          ))}
        </select>

        {/* Search */}
        <input
          type="text"
          placeholder="Search companies..."
          className="text-xs border rounded-lg px-3 py-1.5 flex-1 min-w-[150px]"
          value={searchText}
          onChange={e => setSearchText(e.target.value)}
        />

        <span className="text-xs text-gray-400">{filtered.length} of {companies.length}</span>
      </div>

      {/* Content */}
      {view === 'grid' ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
          {filtered.map(c => <CompanyCard key={c.id} company={c} />)}
        </div>
      ) : (
        <PipelineView />
      )}

      {/* Notes Modal */}
      {modalCompany && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4"
             onClick={() => setModalCompany(null)}>
          <div className="bg-white rounded-xl shadow-xl max-w-lg w-full p-6" onClick={e => e.stopPropagation()}>
            <div className="flex items-start justify-between mb-4">
              <div>
                <h2 className="text-lg font-bold text-gray-900">{modalCompany.name}</h2>
                <div className="flex gap-2 mt-1">
                  <BucketTag bucket={modalCompany.bucket} />
                  <PriorityBadge priority={modalCompany.priority} />
                  <span className="text-xs text-gray-500">{modalCompany.stage}</span>
                </div>
              </div>
              <button className="text-gray-400 hover:text-gray-600 text-xl" onClick={() => setModalCompany(null)}>
                &times;
              </button>
            </div>

            <p className="text-sm text-gray-600 mb-2">{modalCompany.whyFit}</p>
            <p className="text-sm text-amber-700 bg-amber-50 rounded px-3 py-2 mb-4">
              <span className="font-medium">Trigger:</span> {modalCompany.trigger}
            </p>

            {/* Status */}
            <div className="mb-4">
              <label className="text-xs font-medium text-gray-700 block mb-1">Pipeline Status</label>
              <select
                className="w-full text-sm border rounded-lg px-3 py-2 bg-white"
                value={modalStatus}
                onChange={e => setModalStatus(e.target.value)}>
                {window.PIPELINE_STATUSES.map(s => (
                  <option key={s} value={s}>{window.PIPELINE_LABELS[s]}</option>
                ))}
              </select>
            </div>

            {/* Notes */}
            <div className="mb-4">
              <label className="text-xs font-medium text-gray-700 block mb-1">Intel Notes</label>
              <textarea
                className="w-full text-sm border rounded-lg px-3 py-2 h-28 resize-none"
                placeholder="Add intel notes, signals, contacts..."
                value={modalNotes}
                onChange={e => setModalNotes(e.target.value)}
              />
            </div>

            <div className="flex gap-2 justify-end">
              <button
                className="px-4 py-2 text-sm text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors font-medium"
                onClick={() => { setModalCompany(null); onOpenMuse(modalCompany); }}>
                Open in MUSE
              </button>
              <button
                className="px-4 py-2 text-sm bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors"
                onClick={() => setModalCompany(null)}>
                Cancel
              </button>
              <button
                className="px-4 py-2 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors font-medium"
                onClick={saveModal}>
                Save
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

window.Dashboard = Dashboard;
