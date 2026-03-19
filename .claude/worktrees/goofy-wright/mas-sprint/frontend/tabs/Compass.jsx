// Tab 3 — COMPASS Weekly Brief
// Monday morning intelligence brief with live web search

const Compass = ({ companies, apiCall }) => {
  const [focus, setFocus] = React.useState('all');
  const [customSignal, setCustomSignal] = React.useState('');
  const [loading, setLoading] = React.useState(false);
  const [briefContent, setBriefContent] = React.useState(null);
  const [error, setError] = React.useState(null);
  const [copiedBrief, setCopiedBrief] = React.useState(false);

  // Heartbeat state
  const [currentPhase, setCurrentPhase] = React.useState(-1);
  const phaseTimerRef = React.useRef(null);
  const phasesRef = React.useRef([]);

  const focusOptions = [
    { value: 'all', label: 'All Buckets', filter: () => true },
    { value: 'martech', label: 'MarTech Only', filter: c => c.bucket === 'MarTech' },
    { value: 'ai-native', label: 'AI-Native Only', filter: c => c.bucket === 'AI-Native' },
    { value: 'fintech-b2c', label: 'Fintech + B2C', filter: c => c.bucket === 'Fintech' || c.bucket === 'B2C Ecomm' },
    { value: 'b2b', label: 'B2B SaaS Only', filter: c => c.bucket === 'B2B SaaS' },
    { value: 'priority-a', label: 'Priority A Only', filter: c => c.priority === 'A' },
    { value: 'funding', label: 'Funding Signals', filter: c => c.trigger.toLowerCase().includes('fund') || c.trigger.toLowerCase().includes('series') }
  ];

  const activeFocus = focusOptions.find(f => f.value === focus);
  const targetCompanies = companies.filter(activeFocus.filter);

  // 9-phase heartbeat
  const phases = [
    { label: 'Initializing COMPASS', icon: '\u2699\uFE0F', detail: 'Loading Target 23 data and Mike context...', duration: 2500 },
    { label: 'Searching web \u2014 Trigger events', icon: '\uD83D\uDD0D', detail: 'Scanning for leadership changes and funding rounds...', duration: 6000 },
    { label: 'Searching web \u2014 Open roles', icon: '\uD83D\uDD0D', detail: 'Checking job boards and career pages...', duration: 6000 },
    { label: 'Searching web \u2014 Industry signals', icon: '\uD83D\uDD0D', detail: 'Monitoring MarTech and AI news sources...', duration: 5000 },
    { label: 'Searching web \u2014 Company news', icon: '\uD83D\uDD0D', detail: 'Checking press releases and announcements...', duration: 5000 },
    { label: 'Analyzing signals', icon: '\uD83E\uDDE0', detail: 'Cross-referencing triggers against Target 23...', duration: 5000 },
    { label: 'Checking pipeline', icon: '\uD83D\uDCCA', detail: 'Reviewing current pipeline status and gaps...', duration: 4000 },
    { label: 'Writing brief', icon: '\u270D\uFE0F', detail: 'Composing six-section intelligence brief...', duration: 6000 },
    { label: 'Finalizing', icon: '\u2705', detail: 'Formatting and quality-checking output...', duration: 3000 }
  ];

  const startHeartbeat = () => {
    setCurrentPhase(0);
    let phaseIndex = 0;

    const advancePhase = () => {
      phaseIndex++;
      if (phaseIndex < phases.length) {
        setCurrentPhase(phaseIndex);
        phaseTimerRef.current = setTimeout(advancePhase, phases[phaseIndex].duration);
      }
    };

    phaseTimerRef.current = setTimeout(advancePhase, phases[0].duration);
  };

  const stopHeartbeat = () => {
    if (phaseTimerRef.current) {
      clearTimeout(phaseTimerRef.current);
      phaseTimerRef.current = null;
    }
    setCurrentPhase(phases.length); // all done
  };

  React.useEffect(() => {
    return () => {
      if (phaseTimerRef.current) clearTimeout(phaseTimerRef.current);
    };
  }, []);

  const buildSystemPrompt = () => {
    const ctx = window.MIKE_CONTEXT;
    const companyList = targetCompanies.map(c =>
      `- ${c.name} (${c.bucket}, P-${c.priority}, ${c.stage}) — Trigger: ${c.trigger} — Status: ${window.PIPELINE_LABELS[c.status]}`
    ).join('\n');

    return `You are COMPASS, Mike Berry's strategic intelligence agent.

TODAY'S DATE: ${new Date().toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}

MIKE'S BACKGROUND: ${ctx.background}

MIKE'S TARGET TITLES: ${ctx.targetTitles.join(', ')}

MIKE'S PROOF POINTS:
${ctx.proofPoints.map(p => `- ${p.label}: ${p.story}`).join('\n')}

TARGET COMPANIES TO SCAN:
${companyList}

${customSignal ? `MIKE'S CUSTOM SIGNAL THIS WEEK:\n${customSignal}\n` : ''}

STRICT RULES:
- Use REAL, CURRENT information from web search — never fabricate signals
- Every company mentioned must be from the Target 23 list above
- Every role mentioned must match Mike's target titles
- Be specific: name companies, name roles, name people when found
- Urgency ratings must reflect actual recency and relevance
- The 3-Hour Plan must have specific time allocations`;
  };

  const generateBrief = async () => {
    setLoading(true);
    setError(null);
    setBriefContent(null);
    startHeartbeat();

    try {
      const response = await apiCall({
        model: 'claude-sonnet-4-20250514',
        max_tokens: 4000,
        tools: [{
          type: 'web_search_20250305',
          name: 'web_search',
          max_uses: 10
        }],
        system: buildSystemPrompt(),
        messages: [{
          role: 'user',
          content: `Generate my Monday morning COMPASS Weekly Brief. Search the web for REAL, CURRENT signals about these companies.

You MUST produce exactly these six sections with these exact headers:

\uD83C\uDFAF THIS WEEK'S PRIORITY ACTION
One specific named action — company name + specific action Mike should take. Not generic advice.

\u26A1 TRIGGER EVENTS DETECTED
3-5 real signals found across the Target companies. Each must include:
- Company name
- What happened (specific event)
- Urgency: HIGH / MED / LOW
- Suggested response

\uD83D\uDCCB OPEN ROLES WORTH WATCHING
3-5 specific roles at Target companies that match Mike's target titles. Include:
- Company name
- Role title
- Why it's relevant

\uD83E\uDDE0 INDUSTRY SIGNAL
One sharp paragraph about a live MarTech, AI, or product trend Mike can reference in outreach. Must be current.

\uD83D\uDCCA PIPELINE HEALTH CHECK
2-sentence assessment of Mike's current pipeline plus the biggest gap to address this week.

\u23F0 THIS WEEK'S 3-HOUR PLAN
Specific time allocation across Track 1 (reactive) and Track 2 (proactive). Example: "45min COMPASS review, 60min Iterable outreach, 30min LinkedIn applications, 45min follow-ups"`
        }]
      });

      stopHeartbeat();

      if (response.error) throw new Error(response.error);

      // Extract text blocks from response
      const textBlocks = (response.content || [])
        .filter(b => b.type === 'text')
        .map(b => b.text)
        .join('\n\n');

      if (!textBlocks) throw new Error('No text content in response');
      setBriefContent(textBlocks);
    } catch (err) {
      stopHeartbeat();
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const copyBrief = async () => {
    if (!briefContent) return;
    try {
      await navigator.clipboard.writeText(briefContent);
      setCopiedBrief(true);
      setTimeout(() => setCopiedBrief(false), 2000);
    } catch {
      const ta = document.createElement('textarea');
      ta.value = briefContent;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
      setCopiedBrief(true);
      setTimeout(() => setCopiedBrief(false), 2000);
    }
  };

  const newBrief = () => {
    setBriefContent(null);
    setCurrentPhase(-1);
    setError(null);
  };

  // Compute next Monday
  const getNextMonday = () => {
    const now = new Date();
    const day = now.getDay();
    const diff = day === 0 ? 1 : day === 1 ? 7 : 8 - day;
    const next = new Date(now);
    next.setDate(now.getDate() + diff);
    return next.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' });
  };

  // Progress percentage
  const totalDuration = phases.reduce((sum, p) => sum + p.duration, 0);
  const elapsedDuration = phases.slice(0, Math.max(0, currentPhase)).reduce((sum, p) => sum + p.duration, 0);
  const progressPct = currentPhase >= phases.length ? 100 : Math.round((elapsedDuration / totalDuration) * 100);

  // Heartbeat UI
  const HeartbeatPanel = () => (
    <div className="bg-gray-900 rounded-xl p-6 text-white">
      {/* Progress Bar */}
      <div className="h-1.5 bg-gray-700 rounded-full mb-6 overflow-hidden">
        <div className="h-full bg-green-500 rounded-full transition-all duration-1000 ease-linear"
             style={{ width: `${progressPct}%` }} />
      </div>

      <div className="space-y-2">
        {phases.map((phase, i) => {
          let state = 'pending';
          if (i < currentPhase || currentPhase >= phases.length) state = 'done';
          else if (i === currentPhase) state = 'active';

          return (
            <div key={i} className={`flex items-center gap-3 py-1.5 px-3 rounded-lg transition-all ${
              state === 'active' ? 'bg-gray-800' : ''
            } ${state === 'pending' ? 'opacity-40' : ''}`}>
              <span className="text-lg w-7 text-center">
                {state === 'done' ? '\u2705' : phase.icon}
              </span>
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span className={`text-sm font-medium ${state === 'active' ? 'text-green-400' : 'text-gray-300'}`}>
                    {phase.label}
                  </span>
                  {state === 'active' && (
                    <span className="px-1.5 py-0.5 bg-green-500 text-white text-[10px] font-bold rounded animate-pulse">
                      LIVE
                    </span>
                  )}
                  {state === 'done' && (
                    <span className="px-1.5 py-0.5 bg-gray-600 text-gray-300 text-[10px] font-bold rounded">
                      DONE
                    </span>
                  )}
                </div>
                {state === 'active' && (
                  <p className="text-xs text-gray-400 mt-0.5">{phase.detail}</p>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );

  // Parse and render brief sections with styling
  const BriefSection = ({ content }) => {
    // Split by section headers (emoji + header text)
    const sectionPattern = /(\uD83C\uDFAF|\u26A1|\uD83D\uDCCB|\uD83E\uDDE0|\uD83D\uDCCA|\u23F0)\s*(.+)/;
    const lines = content.split('\n');
    const sections = [];
    let currentSection = null;

    for (const line of lines) {
      const match = line.match(sectionPattern);
      if (match) {
        if (currentSection) sections.push(currentSection);
        currentSection = { icon: match[1], title: match[2].trim(), lines: [] };
      } else if (currentSection) {
        currentSection.lines.push(line);
      } else {
        // Pre-section content
        if (line.trim()) {
          sections.push({ icon: '', title: '', lines: [line], isPreamble: true });
        }
      }
    }
    if (currentSection) sections.push(currentSection);

    const sectionColors = {
      '\uD83C\uDFAF': 'border-red-200 bg-red-50',
      '\u26A1': 'border-amber-200 bg-amber-50',
      '\uD83D\uDCCB': 'border-blue-200 bg-blue-50',
      '\uD83E\uDDE0': 'border-purple-200 bg-purple-50',
      '\uD83D\uDCCA': 'border-green-200 bg-green-50',
      '\u23F0': 'border-indigo-200 bg-indigo-50'
    };

    return (
      <div className="space-y-4">
        {sections.map((sec, i) => {
          if (sec.isPreamble) {
            return <p key={i} className="text-sm text-gray-600">{sec.lines.join('\n')}</p>;
          }
          const colorClass = sectionColors[sec.icon] || 'border-gray-200 bg-gray-50';
          return (
            <div key={i} className={`rounded-lg border-2 ${colorClass} overflow-hidden`}>
              <div className="px-4 py-2.5 border-b border-inherit bg-white/50">
                <h3 className="font-bold text-sm text-gray-900">
                  {sec.icon} {sec.title}
                </h3>
              </div>
              <div className="px-4 py-3">
                <div className="text-sm text-gray-700 whitespace-pre-wrap leading-relaxed">
                  {sec.lines.join('\n').trim()}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    );
  };

  return (
    <div className="space-y-4">
      {/* Config Panel (hidden during loading) */}
      {!loading && !briefContent && (
        <>
          <div className="bg-white rounded-lg border p-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Focus Selector */}
              <div>
                <label className="text-xs font-medium text-gray-700 block mb-1">Focus Area</label>
                <select
                  className="w-full text-sm border rounded-lg px-3 py-2 bg-white"
                  value={focus}
                  onChange={e => setFocus(e.target.value)}>
                  {focusOptions.map(f => (
                    <option key={f.value} value={f.value}>{f.label}</option>
                  ))}
                </select>
              </div>

              {/* Target Preview */}
              <div>
                <label className="text-xs font-medium text-gray-700 block mb-1">
                  Companies to Scan ({targetCompanies.length})
                </label>
                <div className="flex flex-wrap gap-1">
                  {targetCompanies.map(c => (
                    <span key={c.id} className="text-xs px-2 py-0.5 rounded-full"
                          style={{ backgroundColor: window.BUCKET_COLORS[c.bucket].bg,
                                   color: window.BUCKET_COLORS[c.bucket].text }}>
                      {c.name}
                    </span>
                  ))}
                </div>
              </div>
            </div>

            {/* Custom Signal */}
            <div className="mt-4">
              <label className="text-xs font-medium text-gray-700 block mb-1">
                Custom Signal <span className="text-gray-400 font-normal">(anything you noticed this week)</span>
              </label>
              <textarea
                className="w-full text-sm border rounded-lg px-3 py-2 h-20 resize-none"
                placeholder="e.g., 'Saw Iterable CMO post about AI on LinkedIn' or 'Heard Typeface is raising Series C'"
                value={customSignal}
                onChange={e => setCustomSignal(e.target.value)}
              />
            </div>
          </div>

          {/* Mike Context Panel */}
          <div className="bg-indigo-50 border border-indigo-200 rounded-lg p-4">
            <h3 className="text-xs font-semibold text-indigo-800 mb-2 uppercase tracking-wide">Context Loaded into Brief</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div>
                <p className="text-xs font-medium text-indigo-700 mb-1">Target Titles</p>
                <ul className="text-xs text-gray-600 space-y-0.5">
                  {window.MIKE_CONTEXT.targetTitles.map((t, i) => (
                    <li key={i}>{t}</li>
                  ))}
                </ul>
              </div>
              <div>
                <p className="text-xs font-medium text-indigo-700 mb-1">Proof Points</p>
                {window.MIKE_CONTEXT.proofPoints.map((pp, i) => (
                  <p key={i} className="text-xs text-gray-600 mb-1">
                    <span className="font-medium">{pp.label}:</span> {pp.story.substring(0, 80)}...
                  </p>
                ))}
              </div>
            </div>
          </div>

          {/* Generate Button */}
          <div className="text-center">
            <button
              className="px-8 py-3 bg-indigo-600 text-white rounded-lg font-semibold hover:bg-indigo-700 transition-colors shadow-sm"
              onClick={generateBrief}>
              Generate Weekly Brief
            </button>
          </div>
        </>
      )}

      {/* Heartbeat (shown during loading) */}
      {loading && <HeartbeatPanel />}

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700">
          <span className="font-medium">Error:</span> {error}
          <button className="ml-3 text-red-600 underline" onClick={newBrief}>Try again</button>
        </div>
      )}

      {/* Brief Output */}
      {briefContent && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold text-gray-900">COMPASS Weekly Brief</h2>
            <div className="flex gap-2">
              <button
                className="px-4 py-2 text-sm bg-white border rounded-lg hover:bg-gray-50 transition-colors"
                onClick={copyBrief}>
                {copiedBrief ? 'Copied!' : 'Copy Brief'}
              </button>
              <button
                className="px-4 py-2 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
                onClick={newBrief}>
                New Brief
              </button>
            </div>
          </div>

          <BriefSection content={briefContent} />
        </div>
      )}

      {/* Footer */}
      <div className="text-center text-xs text-gray-400 py-2">
        Next brief: {getNextMonday()}
      </div>
    </div>
  );
};

window.Compass = Compass;
