// Tab 2 — MUSE Outreach Generator
// AI-powered outreach drafting. Three warmth variants per company.

const Muse = ({ companies, selectedCompanyId, onUpdateCompany, apiCall }) => {
  const [companyId, setCompanyId] = React.useState(selectedCompanyId || '');
  const [triggerOverride, setTriggerOverride] = React.useState('');
  const [loading, setLoading] = React.useState(false);
  const [variants, setVariants] = React.useState({ warm: null, intro: null, cold: null });
  const [error, setError] = React.useState(null);
  const [copiedId, setCopiedId] = React.useState(null);
  const [regeneratingId, setRegeneratingId] = React.useState(null);

  // Sync when parent passes a new company
  React.useEffect(() => {
    if (selectedCompanyId) setCompanyId(selectedCompanyId);
  }, [selectedCompanyId]);

  const company = companies.find(c => c.id === companyId);
  const triggerText = triggerOverride || (company ? company.trigger : '');

  const buildSystemPrompt = () => {
    const ctx = window.MIKE_CONTEXT;
    return `You are MUSE, Mike Berry's outreach drafting agent.

MIKE'S BACKGROUND: ${ctx.background}

MIKE'S PROOF POINTS (use ONE maximum per message, woven naturally — NEVER listed):
${ctx.proofPoints.map((p, i) => `${i + 1}. ${p.label}: ${p.story}`).join('\n')}

TARGET TITLES: ${ctx.targetTitles.join(', ')}

STRICT RULES:
- Maximum 4 sentences per message
- Lead with the COMPANY and their news — NEVER with Mike's credentials
- ONE proof point maximum, woven naturally — never listed
- NEVER use: synergy, leverage, passionate, excited, "hope this finds you well"
- Be specific to the company and trigger — no generic outreach`;
  };

  const buildUserPrompt = (variant) => {
    if (!company) return '';
    const variantInstructions = {
      warm: 'Write a WARM LinkedIn DM (1st degree connection). Casual, direct, 3-4 sentences max. Assume they already know of Mike.',
      intro: 'Write an INTRO REQUEST — a note Mike sends to a mutual connection asking them to make an introduction. Easy to forward. 3-4 sentences. Include a one-line "what to say about me" the mutual can use.',
      cold: 'Write a COLD outreach — cold email or LinkedIn connection request. 3 sentences maximum. No fluff. Lead with value to them.'
    };

    return `Company: ${company.name}
Bucket: ${company.bucket}
Stage: ${company.stage}
Trigger Event: ${triggerText}
Why Mike Fits: ${company.whyFit}

${variantInstructions[variant]}`;
  };

  const generateVariant = async (variant) => {
    const response = await apiCall({
      model: 'claude-sonnet-4-20250514',
      max_tokens: 500,
      system: buildSystemPrompt(),
      messages: [{ role: 'user', content: buildUserPrompt(variant) }]
    });

    if (response.error) throw new Error(response.error);

    const text = response.content
      ? response.content.map(b => b.text || '').join('')
      : 'No response generated';
    return text;
  };

  const generateAll = async () => {
    if (!company) return;
    setLoading(true);
    setError(null);
    setVariants({ warm: null, intro: null, cold: null });

    try {
      const [warm, intro, cold] = await Promise.all([
        generateVariant('warm'),
        generateVariant('intro'),
        generateVariant('cold')
      ]);
      setVariants({ warm, intro, cold });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const regenerateSingle = async (variant) => {
    setRegeneratingId(variant);
    try {
      const text = await generateVariant(variant);
      setVariants(prev => ({ ...prev, [variant]: text }));
    } catch (err) {
      setError(err.message);
    } finally {
      setRegeneratingId(null);
    }
  };

  const copyToClipboard = async (text, id) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedId(id);
      setTimeout(() => setCopiedId(null), 2000);
    } catch {
      // Fallback
      const ta = document.createElement('textarea');
      ta.value = text;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
      setCopiedId(id);
      setTimeout(() => setCopiedId(null), 2000);
    }
  };

  const markSent = () => {
    if (company) {
      onUpdateCompany(company.id, { status: 'outreach_sent' });
    }
  };

  const VariantCard = ({ variant, label, tone, text }) => {
    const toneColors = {
      warm: 'border-green-200 bg-green-50',
      intro: 'border-blue-200 bg-blue-50',
      cold: 'border-gray-200 bg-gray-50'
    };
    const headerColors = {
      warm: 'bg-green-600',
      intro: 'bg-blue-600',
      cold: 'bg-gray-600'
    };

    return (
      <div className={`rounded-lg border-2 ${toneColors[variant]} overflow-hidden`}>
        <div className={`${headerColors[variant]} text-white px-4 py-2 flex items-center justify-between`}>
          <span className="font-semibold text-sm">{label}</span>
          <span className="text-xs opacity-80">{tone}</span>
        </div>
        <div className="p-4">
          {text ? (
            <>
              <p className="text-sm text-gray-800 whitespace-pre-wrap leading-relaxed">{text}</p>
              <div className="flex gap-2 mt-4 pt-3 border-t border-gray-200/50">
                <button
                  className="text-xs px-3 py-1.5 bg-white border rounded-md hover:bg-gray-50 transition-colors"
                  onClick={() => copyToClipboard(text, variant)}>
                  {copiedId === variant ? 'Copied!' : 'Copy'}
                </button>
                <button
                  className="text-xs px-3 py-1.5 bg-white border rounded-md hover:bg-gray-50 transition-colors"
                  disabled={regeneratingId === variant}
                  onClick={() => regenerateSingle(variant)}>
                  {regeneratingId === variant ? 'Regenerating...' : 'Regenerate'}
                </button>
                <button
                  className="text-xs px-3 py-1.5 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 transition-colors ml-auto"
                  onClick={markSent}>
                  Mark Sent
                </button>
              </div>
            </>
          ) : loading ? (
            <div className="flex items-center gap-2 py-6 justify-center">
              <div className="w-4 h-4 border-2 border-gray-300 border-t-indigo-600 rounded-full animate-spin"></div>
              <span className="text-sm text-gray-500">Generating {label.toLowerCase()}...</span>
            </div>
          ) : (
            <p className="text-sm text-gray-400 italic py-6 text-center">Select a company and click Generate All</p>
          )}
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-4">
      {/* Company Selector + Context */}
      <div className="bg-white rounded-lg border p-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Selector */}
          <div>
            <label className="text-xs font-medium text-gray-700 block mb-1">Select Company</label>
            <select
              className="w-full text-sm border rounded-lg px-3 py-2 bg-white"
              value={companyId}
              onChange={e => { setCompanyId(e.target.value); setVariants({ warm: null, intro: null, cold: null }); }}>
              <option value="">Choose a company...</option>
              {companies.map(c => (
                <option key={c.id} value={c.id}>
                  {c.name} — {c.bucket} (P-{c.priority})
                </option>
              ))}
            </select>
          </div>

          {/* Context Display */}
          {company && (
            <div className="md:col-span-2">
              <div className="flex gap-2 mb-2">
                <span className="px-2 py-0.5 rounded text-xs font-medium"
                      style={{ backgroundColor: window.BUCKET_COLORS[company.bucket].bg,
                               color: window.BUCKET_COLORS[company.bucket].text }}>
                  {company.bucket}
                </span>
                <span className="px-2 py-0.5 rounded text-xs font-bold"
                      style={{ backgroundColor: window.PRIORITY_STYLES[company.priority].bg,
                               color: window.PRIORITY_STYLES[company.priority].text }}>
                  P-{company.priority}
                </span>
                <span className="text-xs text-gray-500">{company.stage}</span>
                <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                  company.status === 'outreach_sent' ? 'bg-blue-100 text-blue-800' : 'bg-gray-100 text-gray-600'
                }`}>{window.PIPELINE_LABELS[company.status]}</span>
              </div>
              <p className="text-sm text-gray-700"><span className="font-medium">Why fit:</span> {company.whyFit}</p>
              <p className="text-sm text-amber-700 mt-1"><span className="font-medium">Default trigger:</span> {company.trigger}</p>
            </div>
          )}
        </div>

        {/* Trigger Override */}
        {company && (
          <div className="mt-3">
            <label className="text-xs font-medium text-gray-700 block mb-1">
              Trigger Override <span className="text-gray-400 font-normal">(leave blank to use default)</span>
            </label>
            <input
              type="text"
              className="w-full text-sm border rounded-lg px-3 py-2"
              placeholder="e.g., 'Just hired CMO from Shopify' — overrides the default trigger"
              value={triggerOverride}
              onChange={e => setTriggerOverride(e.target.value)}
            />
          </div>
        )}
      </div>

      {/* Mike's Proof Points */}
      <div className="bg-indigo-50 border border-indigo-200 rounded-lg p-4">
        <h3 className="text-xs font-semibold text-indigo-800 mb-2 uppercase tracking-wide">Mike's Proof Points (available to MUSE)</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {window.MIKE_CONTEXT.proofPoints.map((pp, i) => (
            <div key={i} className="bg-white rounded border border-indigo-100 p-2.5">
              <p className="text-xs font-semibold text-indigo-700">{pp.label}</p>
              <p className="text-xs text-gray-600 mt-0.5">{pp.story}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Generate Button */}
      <div className="text-center">
        <button
          className="px-8 py-3 bg-indigo-600 text-white rounded-lg font-semibold hover:bg-indigo-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed shadow-sm"
          disabled={!company || loading}
          onClick={generateAll}>
          {loading ? (
            <span className="flex items-center gap-2">
              <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></span>
              Generating All Variants...
            </span>
          ) : 'Generate All Variants'}
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700">
          <span className="font-medium">Error:</span> {error}
        </div>
      )}

      {/* Three Variant Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <VariantCard variant="warm" label="Warm" tone="1st Degree DM" text={variants.warm} />
        <VariantCard variant="intro" label="Intro" tone="Ask Mutual" text={variants.intro} />
        <VariantCard variant="cold" label="Cold" tone="No Connection" text={variants.cold} />
      </div>
    </div>
  );
};

window.Muse = Muse;
