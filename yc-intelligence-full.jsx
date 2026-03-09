import { useState, useEffect, useRef, useCallback } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, LineChart, Line, AreaChart, Area } from "recharts";

// ─── Styles ──────────────────────────────────────────────────────────────────
const FONT_DISPLAY = "'Instrument Serif', Georgia, serif";
const FONT_MONO = "'JetBrains Mono', 'Fira Code', monospace";
const FONT_BODY = "'DM Sans', 'Helvetica Neue', sans-serif";

const PALETTE = {
  bg: "#08080c", surface: "#0f0f14", surfaceLight: "#16161e",
  border: "rgba(255,255,255,0.06)", borderHover: "rgba(255,255,255,0.12)",
  text: "#e8e8f0", textMuted: "#7a7a8c", textDim: "#4a4a5c",
  accent: "#ff6b35", accentSoft: "rgba(255,107,53,0.12)",
  green: "#22c55e", red: "#ef4444", blue: "#3b82f6", purple: "#a855f7",
  yellow: "#eab308", cyan: "#06b6d4", pink: "#ec4899",
};

const CHART_COLORS = ["#ff6b35","#3b82f6","#22c55e","#a855f7","#eab308","#06b6d4","#ec4899","#f97316","#6366f1","#14b8a6","#f43f5e","#84cc16"];

// ─── Data Processing Utilities ───────────────────────────────────────────────
function processCompanies(raw) {
  if (!Array.isArray(raw)) return [];
  return raw.map(c => ({
    name: c.name || "Unknown",
    oneLiner: c.one_liner || c.oneLiner || "",
    industry: c.industry || "Unspecified",
    subindustry: c.subindustry || "",
    batch: c.batch || "",
    status: c.status || "Unknown",
    teamSize: parseInt(c.team_size || c.teamSize) || 0,
    tags: Array.isArray(c.tags) ? c.tags.join(", ") : (c.tags || ""),
    topCompany: c.top_company || c.topCompany || false,
    isHiring: c.isHiring || false,
    website: c.website || "",
    longDesc: c.long_description || "",
    stage: c.stage || "",
    regions: Array.isArray(c.regions) ? c.regions.join(", ") : (c.regions || ""),
    url: c.url || "",
  }));
}

function getSectorData(companies) {
  const map = {};
  companies.forEach(c => {
    if (!map[c.industry]) map[c.industry] = { name: c.industry, count: 0, active: 0, inactive: 0, hiring: 0, topCos: 0 };
    map[c.industry].count++;
    if (c.status === "Active") map[c.industry].active++;
    if (c.status === "Inactive" || c.status === "Shutdown") map[c.industry].inactive++;
    if (c.isHiring) map[c.industry].hiring++;
    if (c.topCompany) map[c.industry].topCos++;
  });
  return Object.values(map)
    .map(s => ({ ...s, successRate: s.count > 0 ? Math.round((s.active / s.count) * 100) : 0 }))
    .sort((a, b) => b.count - a.count);
}

function getBatchTrends(companies) {
  const map = {};
  companies.forEach(c => {
    if (!c.batch) return;
    if (!map[c.batch]) map[c.batch] = { batch: c.batch, count: 0 };
    map[c.batch].count++;
  });
  return Object.values(map).sort((a, b) => a.batch.localeCompare(b.batch)).slice(-20);
}

function getStatusData(companies) {
  const map = {};
  companies.forEach(c => {
    map[c.status] = (map[c.status] || 0) + 1;
  });
  return Object.entries(map).map(([name, value]) => ({ name, value })).sort((a, b) => b.value - a.value);
}

// ─── Components ──────────────────────────────────────────────────────────────
function Stat({ label, value, sub, color = PALETTE.accent }) {
  return (
    <div style={{ background: PALETTE.surface, border: `1px solid ${PALETTE.border}`, borderRadius: 10, padding: "18px 22px", flex: "1 1 160px", minWidth: 150 }}>
      <div style={{ fontFamily: FONT_MONO, fontSize: 10, color: PALETTE.textDim, textTransform: "uppercase", letterSpacing: 2, marginBottom: 8 }}>{label}</div>
      <div style={{ fontFamily: FONT_DISPLAY, fontSize: 34, fontWeight: 400, color, lineHeight: 1, fontStyle: "italic" }}>{value}</div>
      {sub && <div style={{ fontFamily: FONT_MONO, fontSize: 10, color: PALETTE.textDim, marginTop: 6 }}>{sub}</div>}
    </div>
  );
}

function Tab({ active, label, onClick }) {
  return (
    <button onClick={onClick} style={{
      padding: "10px 22px", borderRadius: 8, border: "none", cursor: "pointer",
      fontFamily: FONT_BODY, fontSize: 13, fontWeight: 500, letterSpacing: 0.3,
      background: active ? PALETTE.accentSoft : "transparent",
      color: active ? PALETTE.accent : PALETTE.textDim,
      transition: "all 0.2s"
    }}>{label}</button>
  );
}

function Pill({ label, active, onClick }) {
  return (
    <button onClick={onClick} style={{
      padding: "5px 14px", borderRadius: 20, border: `1px solid ${active ? PALETTE.accent : PALETTE.border}`,
      background: active ? PALETTE.accentSoft : "transparent", cursor: "pointer",
      fontFamily: FONT_MONO, fontSize: 11, color: active ? PALETTE.accent : PALETTE.textMuted,
      transition: "all 0.15s", whiteSpace: "nowrap"
    }}>{label}</button>
  );
}

function ChatBubble({ role, text }) {
  const isUser = role === "user";
  const formatText = (t) => t.split("\n").map((line, i) => {
    const parts = line.split(/(\*\*[^*]+\*\*)/g);
    return (
      <p key={i} style={{ margin: "5px 0", lineHeight: 1.7 }}>
        {parts.map((part, j) =>
          part.startsWith("**") && part.endsWith("**")
            ? <strong key={j} style={{ color: PALETTE.accent }}>{part.slice(2, -2)}</strong>
            : part
        )}
      </p>
    );
  });

  return (
    <div style={{
      alignSelf: isUser ? "flex-end" : "flex-start",
      maxWidth: isUser ? "75%" : "92%",
      background: isUser ? PALETTE.accentSoft : PALETTE.surface,
      border: `1px solid ${isUser ? "rgba(255,107,53,0.2)" : PALETTE.border}`,
      borderRadius: 14, padding: "14px 20px",
      fontSize: 13, fontFamily: FONT_BODY, color: PALETTE.text, lineHeight: 1.7,
      animation: "fadeUp 0.3s ease"
    }}>
      {isUser ? text : formatText(text)}
    </div>
  );
}

function LoadingDots() {
  return (
    <div style={{ display: "flex", gap: 6, padding: "14px 20px", background: PALETTE.surface, border: `1px solid ${PALETTE.border}`, borderRadius: 14, width: "fit-content" }}>
      {[0, 1, 2].map(i => (
        <div key={i} style={{ width: 7, height: 7, borderRadius: "50%", background: PALETTE.accent, opacity: 0.4, animation: `pulse 1.2s ease-in-out ${i * 0.2}s infinite` }} />
      ))}
    </div>
  );
}

// ─── Main App ────────────────────────────────────────────────────────────────
export default function YCIntelligencePlatform() {
  const [tab, setTab] = useState("overview");
  const [companies, setCompanies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Explorer state
  const [sectorFilter, setSectorFilter] = useState("All");
  const [statusFilter, setStatusFilter] = useState("All");
  const [searchTerm, setSearchTerm] = useState("");
  const [sortBy, setSortBy] = useState("name");

  // AI state
  const [chatHistory, setChatHistory] = useState([]);
  const [query, setQuery] = useState("");
  const [aiLoading, setAiLoading] = useState(false);
  const chatEndRef = useRef(null);

  // Idea evaluator state
  const [ideaInput, setIdeaInput] = useState("");
  const [ideaResult, setIdeaResult] = useState(null);
  const [ideaLoading, setIdeaLoading] = useState(false);

  // Sector deep dive state
  const [deepDiveSector, setDeepDiveSector] = useState("");
  const [deepDiveResult, setDeepDiveResult] = useState(null);
  const [deepDiveLoading, setDeepDiveLoading] = useState(false);

  // ── Load data from YC API ──────────────────────────────────────────────────
  useEffect(() => {
    async function loadData() {
      try {
        const res = await fetch("https://yc-oss.github.io/api/companies/all.json");
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const raw = await res.json();
        setCompanies(processCompanies(raw));
        setLoading(false);
      } catch (e) {
        setError(e.message);
        setLoading(false);
      }
    }
    loadData();
  }, []);

  useEffect(() => { chatEndRef.current?.scrollIntoView({ behavior: "smooth" }); }, [chatHistory]);

  // ── Derived data ───────────────────────────────────────────────────────────
  const sectors = getSectorData(companies);
  const batchTrends = getBatchTrends(companies);
  const statusData = getStatusData(companies);
  const allSectors = ["All", ...sectors.map(s => s.name)];
  const allStatuses = ["All", ...statusData.map(s => s.name)];

  const filtered = companies.filter(c => {
    if (sectorFilter !== "All" && c.industry !== sectorFilter) return false;
    if (statusFilter !== "All" && c.status !== statusFilter) return false;
    if (searchTerm && !c.name.toLowerCase().includes(searchTerm.toLowerCase()) && !c.oneLiner.toLowerCase().includes(searchTerm.toLowerCase())) return false;
    return true;
  }).sort((a, b) => {
    if (sortBy === "name") return a.name.localeCompare(b.name);
    if (sortBy === "team") return b.teamSize - a.teamSize;
    if (sortBy === "batch") return (b.batch || "").localeCompare(a.batch || "");
    return 0;
  });

  // ── Claude API helper ──────────────────────────────────────────────────────
  const buildContext = useCallback(() => {
    const sample = companies.slice(0, 120).map(c => ({
      name: c.name, one_liner: c.oneLiner, industry: c.industry, batch: c.batch,
      status: c.status, team_size: c.teamSize, top_company: c.topCompany,
    }));
    const stats = {
      total: companies.length,
      sectors: sectors.slice(0, 12).map(s => `${s.name}: ${s.count} (${s.successRate}% active)`).join("; "),
      statuses: statusData.map(s => `${s.name}: ${s.value}`).join(", "),
      recentBatches: batchTrends.slice(-5).map(b => `${b.batch}: ${b.count}`).join(", "),
    };
    return { sample, stats };
  }, [companies, sectors, statusData, batchTrends]);

  const callClaude = async (systemExtra, userPrompt) => {
    const { sample, stats } = buildContext();
    const system = `You are a world-class Y Combinator startup analyst. You have data on ${stats.total} YC companies.

SECTOR SUMMARY: ${stats.sectors}
STATUS BREAKDOWN: ${stats.statuses}
RECENT BATCHES: ${stats.recentBatches}

SAMPLE COMPANIES (${sample.length}):
${JSON.stringify(sample)}

${systemExtra}

Be specific, cite real companies, quantify everything. Use **bold** for emphasis. Keep it concise and actionable.`;

    const res = await fetch("https://api.anthropic.com/v1/messages", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        model: "claude-sonnet-4-20250514",
        max_tokens: 1000,
        system,
        messages: [{ role: "user", content: userPrompt }],
      }),
    });
    const data = await res.json();
    return data.content?.map(b => b.text || "").join("\n") || "Analysis unavailable.";
  };

  // ── Chat handler ───────────────────────────────────────────────────────────
  const sendChat = async (msg) => {
    if (!msg.trim() || aiLoading) return;
    setChatHistory(prev => [...prev, { role: "user", text: msg }]);
    setQuery("");
    setAiLoading(true);
    try {
      const result = await callClaude("Answer questions about YC trends, sectors, opportunities, and startup strategy.", msg);
      setChatHistory(prev => [...prev, { role: "assistant", text: result }]);
    } catch {
      setChatHistory(prev => [...prev, { role: "assistant", text: "Could not reach Claude API. This feature requires running inside Claude.ai artifacts." }]);
    }
    setAiLoading(false);
  };

  // ── Idea evaluator ────────────────────────────────────────────────────────
  const evaluateIdea = async () => {
    if (!ideaInput.trim() || ideaLoading) return;
    setIdeaLoading(true);
    setIdeaResult(null);
    try {
      const result = await callClaude(
        "Evaluate startup ideas against the YC dataset. Be brutally honest.",
        `Evaluate this startup idea: "${ideaInput}"

1. How many similar companies exist in YC? Name them.
2. Is this sector growing or declining in recent batches?
3. Competitive landscape?
4. What angle would make this most fundable?
5. Rate: Fundability (1-10), Market Timing (1-10), Competition (Low/Med/High)
6. Your honest verdict: build, pivot, or avoid?`
      );
      setIdeaResult(result);
    } catch {
      setIdeaResult("Could not reach Claude API. Run this artifact inside Claude.ai.");
    }
    setIdeaLoading(false);
  };

  // ── Sector deep dive ──────────────────────────────────────────────────────
  const runDeepDive = async () => {
    if (!deepDiveSector || deepDiveLoading) return;
    setDeepDiveLoading(true);
    setDeepDiveResult(null);
    const sectorCompanies = companies.filter(c => c.industry === deepDiveSector);
    const sectorSample = sectorCompanies.slice(0, 60).map(c => ({
      name: c.name, one_liner: c.oneLiner, batch: c.batch, status: c.status, team_size: c.teamSize
    }));
    try {
      const result = await callClaude(
        `DEEP DIVE SECTOR DATA (${sectorCompanies.length} companies in ${deepDiveSector}):
${JSON.stringify(sectorSample)}`,
        `Deep dive into the ${deepDiveSector} sector in YC:
1. How many companies, what % are active vs inactive?
2. What sub-niches exist? Which are oversaturated?
3. What are the top companies and why did they win?
4. What's the biggest whitespace opportunity right now?
5. If I wanted to build here, what specific problem should I solve?
6. Rate the sector: Opportunity Score (1-10), Saturation (1-10), Timing (1-10)`
      );
      setDeepDiveResult(result);
    } catch {
      setDeepDiveResult("Could not reach Claude API.");
    }
    setDeepDiveLoading(false);
  };

  // ── Quick prompts ──────────────────────────────────────────────────────────
  const quickPrompts = [
    "What are the 3 best startup opportunities right now based on this data?",
    "Which YC sectors have the highest failure rate and why?",
    "What do all YC top companies have in common?",
    "Give me a startup idea in healthcare with high fundability",
    "What's the most underserved market in YC's portfolio?",
  ];

  const formatResult = (text) => {
    if (!text) return null;
    return text.split("\n").map((line, i) => {
      const parts = line.split(/(\*\*[^*]+\*\*)/g);
      return <p key={i} style={{ margin: "5px 0", lineHeight: 1.7 }}>{parts.map((p, j) =>
        p.startsWith("**") && p.endsWith("**") ? <strong key={j} style={{ color: PALETTE.accent }}>{p.slice(2, -2)}</strong> : p
      )}</p>;
    });
  };

  // ── Render ─────────────────────────────────────────────────────────────────
  if (loading) return (
    <div style={{ minHeight: "100vh", background: PALETTE.bg, display: "flex", alignItems: "center", justifyContent: "center", flexDirection: "column", gap: 16 }}>
      <div style={{ width: 40, height: 40, border: `3px solid ${PALETTE.border}`, borderTop: `3px solid ${PALETTE.accent}`, borderRadius: "50%", animation: "spin 0.8s linear infinite" }} />
      <div style={{ fontFamily: FONT_MONO, fontSize: 13, color: PALETTE.textMuted }}>Loading {companies.length > 0 ? companies.length : "5,000+"} YC companies...</div>
    </div>
  );

  if (error) return (
    <div style={{ minHeight: "100vh", background: PALETTE.bg, display: "flex", alignItems: "center", justifyContent: "center", flexDirection: "column", gap: 12, padding: 40 }}>
      <div style={{ fontFamily: FONT_DISPLAY, fontSize: 28, color: PALETTE.red, fontStyle: "italic" }}>Failed to load data</div>
      <div style={{ fontFamily: FONT_MONO, fontSize: 12, color: PALETTE.textMuted }}>{error}</div>
    </div>
  );

  return (
    <div style={{ minHeight: "100vh", background: PALETTE.bg, color: PALETTE.text }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=JetBrains+Mono:wght@400;500;600&family=DM+Sans:wght@400;500;600;700&display=swap');
        @keyframes spin { to { transform: rotate(360deg) } }
        @keyframes fadeUp { from { opacity:0; transform:translateY(10px) } to { opacity:1; transform:translateY(0) } }
        @keyframes pulse { 0%,100% { opacity:0.3 } 50% { opacity:1 } }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        ::-webkit-scrollbar { width: 5px; }
        ::-webkit-scrollbar-thumb { background: #333; border-radius: 3px; }
        ::selection { background: rgba(255,107,53,0.3); }
      `}</style>

      {/* ── Header ──────────────────────────────────────────────────────────── */}
      <header style={{
        padding: "16px 28px", display: "flex", alignItems: "center", justifyContent: "space-between",
        borderBottom: `1px solid ${PALETTE.border}`, background: "rgba(8,8,12,0.95)",
        backdropFilter: "blur(20px)", position: "sticky", top: 0, zIndex: 100
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <div style={{
            width: 34, height: 34, background: `linear-gradient(135deg, ${PALETTE.accent}, #d4380d)`,
            borderRadius: 7, display: "flex", alignItems: "center", justifyContent: "center",
            fontFamily: FONT_DISPLAY, fontSize: 20, color: "#fff", fontStyle: "italic"
          }}>Y</div>
          <div>
            <div style={{ fontFamily: FONT_DISPLAY, fontSize: 20, color: "#fff", fontStyle: "italic", lineHeight: 1 }}>YC Intelligence</div>
            <div style={{ fontFamily: FONT_MONO, fontSize: 9, color: PALETTE.textDim, letterSpacing: 2.5, textTransform: "uppercase", marginTop: 2 }}>
              {companies.length.toLocaleString()} companies · live data
            </div>
          </div>
        </div>
        <nav style={{ display: "flex", gap: 2, background: PALETTE.surface, borderRadius: 10, padding: 3 }}>
          {[
            { id: "overview", label: "Overview" },
            { id: "explorer", label: "Explorer" },
            { id: "sectors", label: "Sector Deep Dive" },
            { id: "ideas", label: "Idea Evaluator" },
            { id: "analyst", label: "AI Analyst" },
          ].map(t => <Tab key={t.id} active={tab === t.id} label={t.label} onClick={() => setTab(t.id)} />)}
        </nav>
      </header>

      <main style={{ padding: 28, maxWidth: 1320, margin: "0 auto" }}>

        {/* ── OVERVIEW TAB ────────────────────────────────────────────────── */}
        {tab === "overview" && (
          <div style={{ animation: "fadeUp 0.4s ease" }}>
            <div style={{ display: "flex", gap: 14, flexWrap: "wrap", marginBottom: 28 }}>
              <Stat label="Companies" value={companies.length.toLocaleString()} sub="In YC directory" color={PALETTE.accent} />
              <Stat label="Active" value={companies.filter(c => c.status === "Active").length.toLocaleString()} sub={`${Math.round(companies.filter(c => c.status === "Active").length / companies.length * 100)}% of total`} color={PALETTE.green} />
              <Stat label="Inactive" value={companies.filter(c => c.status === "Inactive").length.toLocaleString()} color={PALETTE.red} />
              <Stat label="Acquired" value={companies.filter(c => c.status === "Acquired").length.toLocaleString()} color={PALETTE.blue} />
              <Stat label="Public" value={companies.filter(c => c.status === "Public").length.toLocaleString()} color={PALETTE.purple} />
              <Stat label="Sectors" value={sectors.length} color={PALETTE.yellow} />
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20, marginBottom: 24 }}>
              <div style={{ background: PALETTE.surface, border: `1px solid ${PALETTE.border}`, borderRadius: 12, padding: 22 }}>
                <div style={{ fontFamily: FONT_MONO, fontSize: 10, color: PALETTE.textDim, textTransform: "uppercase", letterSpacing: 2, marginBottom: 14 }}>Companies by Sector</div>
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart data={sectors.slice(0, 8)} margin={{ left: -10, bottom: 5 }}>
                    <XAxis dataKey="name" tick={{ fill: PALETTE.textDim, fontSize: 10 }} axisLine={false} tickLine={false} interval={0} angle={-20} textAnchor="end" height={55} />
                    <YAxis tick={{ fill: PALETTE.textDim, fontSize: 10 }} axisLine={false} tickLine={false} />
                    <Tooltip contentStyle={{ background: PALETTE.surfaceLight, border: `1px solid ${PALETTE.border}`, borderRadius: 8, fontFamily: FONT_MONO, fontSize: 12 }} />
                    <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                      {sectors.slice(0, 8).map((_, i) => <Cell key={i} fill={CHART_COLORS[i]} />)}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>

              <div style={{ background: PALETTE.surface, border: `1px solid ${PALETTE.border}`, borderRadius: 12, padding: 22 }}>
                <div style={{ fontFamily: FONT_MONO, fontSize: 10, color: PALETTE.textDim, textTransform: "uppercase", letterSpacing: 2, marginBottom: 14 }}>Batch Size Trend</div>
                <ResponsiveContainer width="100%" height={280}>
                  <AreaChart data={batchTrends}>
                    <defs>
                      <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor={PALETTE.accent} stopOpacity={0.3} />
                        <stop offset="100%" stopColor={PALETTE.accent} stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <XAxis dataKey="batch" tick={{ fill: PALETTE.textDim, fontSize: 9 }} axisLine={false} tickLine={false} interval={2} />
                    <YAxis tick={{ fill: PALETTE.textDim, fontSize: 10 }} axisLine={false} tickLine={false} />
                    <Tooltip contentStyle={{ background: PALETTE.surfaceLight, border: `1px solid ${PALETTE.border}`, borderRadius: 8, fontFamily: FONT_MONO, fontSize: 12 }} />
                    <Area type="monotone" dataKey="count" stroke={PALETTE.accent} fill="url(#areaGrad)" strokeWidth={2} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
              <div style={{ background: PALETTE.surface, border: `1px solid ${PALETTE.border}`, borderRadius: 12, padding: 22 }}>
                <div style={{ fontFamily: FONT_MONO, fontSize: 10, color: PALETTE.textDim, textTransform: "uppercase", letterSpacing: 2, marginBottom: 14 }}>Status Distribution</div>
                <ResponsiveContainer width="100%" height={220}>
                  <PieChart>
                    <Pie data={statusData} cx="50%" cy="50%" innerRadius={50} outerRadius={85} paddingAngle={3} dataKey="value">
                      {statusData.map((_, i) => <Cell key={i} fill={CHART_COLORS[i]} />)}
                    </Pie>
                    <Tooltip contentStyle={{ background: PALETTE.surfaceLight, border: `1px solid ${PALETTE.border}`, borderRadius: 8, fontFamily: FONT_MONO, fontSize: 12 }} />
                  </PieChart>
                </ResponsiveContainer>
                <div style={{ display: "flex", flexWrap: "wrap", gap: "4px 14px", marginTop: 4 }}>
                  {statusData.map((d, i) => (
                    <div key={i} style={{ display: "flex", alignItems: "center", gap: 5, fontFamily: FONT_MONO, fontSize: 10, color: PALETTE.textMuted }}>
                      <div style={{ width: 7, height: 7, borderRadius: 2, background: CHART_COLORS[i] }} />{d.name}: {d.value}
                    </div>
                  ))}
                </div>
              </div>

              <div style={{ background: PALETTE.surface, border: `1px solid ${PALETTE.border}`, borderRadius: 12, padding: 22 }}>
                <div style={{ fontFamily: FONT_MONO, fontSize: 10, color: PALETTE.textDim, textTransform: "uppercase", letterSpacing: 2, marginBottom: 14 }}>Sector Success Rates</div>
                <div style={{ maxHeight: 260, overflowY: "auto" }}>
                  {sectors.slice(0, 10).map((s, i) => (
                    <div key={i} style={{ display: "flex", alignItems: "center", gap: 12, padding: "8px 0", borderBottom: `1px solid ${PALETTE.border}` }}>
                      <div style={{ fontFamily: FONT_BODY, fontSize: 13, color: PALETTE.text, flex: 1 }}>{s.name}</div>
                      <div style={{ fontFamily: FONT_MONO, fontSize: 11, color: PALETTE.textMuted, width: 50, textAlign: "right" }}>{s.count}</div>
                      <div style={{ width: 100, height: 6, background: PALETTE.surfaceLight, borderRadius: 3, overflow: "hidden" }}>
                        <div style={{ width: `${s.successRate}%`, height: "100%", background: s.successRate > 70 ? PALETTE.green : s.successRate > 50 ? PALETTE.yellow : PALETTE.red, borderRadius: 3 }} />
                      </div>
                      <div style={{ fontFamily: FONT_MONO, fontSize: 11, color: s.successRate > 70 ? PALETTE.green : s.successRate > 50 ? PALETTE.yellow : PALETTE.red, width: 36, textAlign: "right" }}>{s.successRate}%</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ── EXPLORER TAB ────────────────────────────────────────────────── */}
        {tab === "explorer" && (
          <div style={{ animation: "fadeUp 0.4s ease" }}>
            <div style={{ display: "flex", gap: 10, marginBottom: 20, flexWrap: "wrap", alignItems: "center" }}>
              <input
                value={searchTerm} onChange={e => setSearchTerm(e.target.value)}
                placeholder="Search companies..."
                style={{ flex: "1 1 200px", background: PALETTE.surface, border: `1px solid ${PALETTE.border}`, borderRadius: 8, padding: "10px 16px", color: PALETTE.text, fontFamily: FONT_BODY, fontSize: 13, outline: "none" }}
              />
              <select value={sectorFilter} onChange={e => setSectorFilter(e.target.value)} style={{ background: PALETTE.surface, border: `1px solid ${PALETTE.border}`, borderRadius: 8, padding: "10px 14px", color: PALETTE.text, fontFamily: FONT_MONO, fontSize: 12, cursor: "pointer", outline: "none" }}>
                {allSectors.map(s => <option key={s} value={s}>{s}</option>)}
              </select>
              <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)} style={{ background: PALETTE.surface, border: `1px solid ${PALETTE.border}`, borderRadius: 8, padding: "10px 14px", color: PALETTE.text, fontFamily: FONT_MONO, fontSize: 12, cursor: "pointer", outline: "none" }}>
                {allStatuses.map(s => <option key={s} value={s}>{s}</option>)}
              </select>
              <select value={sortBy} onChange={e => setSortBy(e.target.value)} style={{ background: PALETTE.surface, border: `1px solid ${PALETTE.border}`, borderRadius: 8, padding: "10px 14px", color: PALETTE.text, fontFamily: FONT_MONO, fontSize: 12, cursor: "pointer", outline: "none" }}>
                <option value="name">Sort: Name</option>
                <option value="team">Sort: Team Size</option>
                <option value="batch">Sort: Newest</option>
              </select>
              <div style={{ fontFamily: FONT_MONO, fontSize: 11, color: PALETTE.textDim }}>{filtered.length.toLocaleString()} results</div>
            </div>

            <div style={{ background: PALETTE.surface, border: `1px solid ${PALETTE.border}`, borderRadius: 12, overflow: "hidden" }}>
              <div style={{ display: "grid", gridTemplateColumns: "2fr 1.3fr 0.7fr 0.7fr 0.6fr", padding: "10px 16px", fontFamily: FONT_MONO, fontSize: 10, color: PALETTE.textDim, textTransform: "uppercase", letterSpacing: 1.5, borderBottom: `1px solid ${PALETTE.border}` }}>
                <div>Company</div><div>Sector</div><div>Batch</div><div>Status</div><div>Team</div>
              </div>
              <div style={{ maxHeight: 520, overflowY: "auto" }}>
                {filtered.slice(0, 200).map((c, i) => {
                  const statusCol = { Active: PALETTE.green, Inactive: PALETTE.red, Acquired: PALETTE.blue, Public: PALETTE.purple }[c.status] || PALETTE.textMuted;
                  return (
                    <div key={i} style={{ display: "grid", gridTemplateColumns: "2fr 1.3fr 0.7fr 0.7fr 0.6fr", padding: "10px 16px", fontSize: 12, fontFamily: FONT_BODY, color: PALETTE.text, borderBottom: `1px solid ${PALETTE.border}`, background: i % 2 === 0 ? "transparent" : "rgba(255,255,255,0.01)" }}>
                      <div>
                        <span style={{ fontWeight: 600 }}>{c.name}</span>
                        {c.topCompany && <span style={{ marginLeft: 6, fontSize: 9, color: PALETTE.accent, background: PALETTE.accentSoft, padding: "1px 6px", borderRadius: 4 }}>TOP</span>}
                        <div style={{ fontSize: 11, color: PALETTE.textMuted, marginTop: 2, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{c.oneLiner}</div>
                      </div>
                      <div style={{ color: PALETTE.textMuted, fontSize: 12 }}>{c.industry}</div>
                      <div style={{ fontFamily: FONT_MONO, fontSize: 11, color: PALETTE.textMuted }}>{c.batch}</div>
                      <div><span style={{ color: statusCol, background: `${statusCol}15`, padding: "2px 8px", borderRadius: 4, fontSize: 10, fontFamily: FONT_MONO }}>{c.status}</span></div>
                      <div style={{ fontFamily: FONT_MONO, fontSize: 11, color: PALETTE.textMuted }}>{c.teamSize > 0 ? c.teamSize : "—"}</div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        )}

        {/* ── SECTOR DEEP DIVE TAB ────────────────────────────────────────── */}
        {tab === "sectors" && (
          <div style={{ animation: "fadeUp 0.4s ease" }}>
            <div style={{ marginBottom: 24 }}>
              <div style={{ fontFamily: FONT_DISPLAY, fontSize: 28, color: "#fff", fontStyle: "italic", marginBottom: 8 }}>Sector Deep Dive</div>
              <div style={{ fontFamily: FONT_BODY, fontSize: 14, color: PALETTE.textMuted, marginBottom: 20 }}>
                Pick a sector and Claude will analyze the competitive landscape, whitespace, and best opportunities.
              </div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 20 }}>
                {sectors.slice(0, 10).map(s => (
                  <Pill key={s.name} label={`${s.name} (${s.count})`} active={deepDiveSector === s.name} onClick={() => setDeepDiveSector(s.name)} />
                ))}
              </div>
              <button onClick={runDeepDive} disabled={!deepDiveSector || deepDiveLoading} style={{
                background: `linear-gradient(135deg, ${PALETTE.accent}, #d4380d)`, border: "none", borderRadius: 8,
                padding: "12px 28px", color: "#fff", fontFamily: FONT_BODY, fontSize: 14, fontWeight: 600,
                cursor: "pointer", opacity: !deepDiveSector || deepDiveLoading ? 0.4 : 1
              }}>
                {deepDiveLoading ? "Analyzing..." : `Analyze ${deepDiveSector || "sector"}`}
              </button>
            </div>

            {deepDiveLoading && <LoadingDots />}
            {deepDiveResult && (
              <div style={{ background: PALETTE.surface, border: `1px solid ${PALETTE.border}`, borderRadius: 14, padding: 24, fontFamily: FONT_BODY, fontSize: 14, color: PALETTE.text, lineHeight: 1.7, animation: "fadeUp 0.4s ease" }}>
                {formatResult(deepDiveResult)}
              </div>
            )}
          </div>
        )}

        {/* ── IDEA EVALUATOR TAB ──────────────────────────────────────────── */}
        {tab === "ideas" && (
          <div style={{ animation: "fadeUp 0.4s ease" }}>
            <div style={{ fontFamily: FONT_DISPLAY, fontSize: 28, color: "#fff", fontStyle: "italic", marginBottom: 8 }}>Startup Idea Evaluator</div>
            <div style={{ fontFamily: FONT_BODY, fontSize: 14, color: PALETTE.textMuted, marginBottom: 24 }}>
              Describe your startup idea and Claude will evaluate it against {companies.length.toLocaleString()} YC companies.
            </div>

            <div style={{ display: "flex", gap: 10, marginBottom: 24 }}>
              <input
                value={ideaInput} onChange={e => setIdeaInput(e.target.value)}
                onKeyDown={e => { if (e.key === "Enter") evaluateIdea(); }}
                placeholder="e.g. AI-powered contract analysis for small law firms..."
                style={{ flex: 1, background: PALETTE.surface, border: `1px solid ${PALETTE.border}`, borderRadius: 10, padding: "14px 20px", color: PALETTE.text, fontFamily: FONT_BODY, fontSize: 14, outline: "none" }}
                onFocus={e => e.target.style.borderColor = PALETTE.accent}
                onBlur={e => e.target.style.borderColor = PALETTE.border}
              />
              <button onClick={evaluateIdea} disabled={!ideaInput.trim() || ideaLoading} style={{
                background: `linear-gradient(135deg, ${PALETTE.accent}, #d4380d)`, border: "none", borderRadius: 10,
                padding: "14px 28px", color: "#fff", fontFamily: FONT_BODY, fontSize: 14, fontWeight: 600,
                cursor: "pointer", opacity: !ideaInput.trim() || ideaLoading ? 0.4 : 1, whiteSpace: "nowrap"
              }}>
                {ideaLoading ? "Evaluating..." : "Evaluate"}
              </button>
            </div>

            {ideaLoading && <LoadingDots />}
            {ideaResult && (
              <div style={{ background: PALETTE.surface, border: `1px solid ${PALETTE.border}`, borderRadius: 14, padding: 24, fontFamily: FONT_BODY, fontSize: 14, color: PALETTE.text, lineHeight: 1.7, animation: "fadeUp 0.4s ease" }}>
                {formatResult(ideaResult)}
              </div>
            )}
          </div>
        )}

        {/* ── AI ANALYST TAB ──────────────────────────────────────────────── */}
        {tab === "analyst" && (
          <div style={{ animation: "fadeUp 0.4s ease", display: "flex", flexDirection: "column", height: "calc(100vh - 140px)" }}>
            {chatHistory.length === 0 && (
              <div style={{ marginBottom: 20 }}>
                <div style={{ fontFamily: FONT_DISPLAY, fontSize: 28, color: "#fff", fontStyle: "italic", marginBottom: 8 }}>AI Analyst</div>
                <div style={{ fontFamily: FONT_BODY, fontSize: 14, color: PALETTE.textMuted, marginBottom: 16 }}>Ask anything about YC startups, trends, and opportunities.</div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                  {quickPrompts.map((p, i) => (
                    <button key={i} onClick={() => sendChat(p)} style={{
                      background: PALETTE.surface, border: `1px solid ${PALETTE.border}`, borderRadius: 10,
                      padding: "10px 16px", color: PALETTE.text, fontFamily: FONT_BODY, fontSize: 12,
                      cursor: "pointer", textAlign: "left", maxWidth: 320, lineHeight: 1.4,
                      transition: "border-color 0.2s"
                    }}
                    onMouseOver={e => e.target.style.borderColor = PALETTE.accent}
                    onMouseOut={e => e.target.style.borderColor = PALETTE.border}
                    >{p}</button>
                  ))}
                </div>
              </div>
            )}

            <div style={{ flex: 1, overflowY: "auto", display: "flex", flexDirection: "column", gap: 14, marginBottom: 14 }}>
              {chatHistory.map((msg, i) => <ChatBubble key={i} role={msg.role} text={msg.text} />)}
              {aiLoading && <LoadingDots />}
              <div ref={chatEndRef} />
            </div>

            <div style={{ display: "flex", gap: 8 }}>
              <input
                value={query} onChange={e => setQuery(e.target.value)}
                onKeyDown={e => { if (e.key === "Enter") sendChat(query); }}
                placeholder="Ask Claude about YC trends, sectors, opportunities..."
                style={{ flex: 1, background: PALETTE.surface, border: `1px solid ${PALETTE.border}`, borderRadius: 10, padding: "14px 20px", color: PALETTE.text, fontFamily: FONT_BODY, fontSize: 13, outline: "none" }}
                onFocus={e => e.target.style.borderColor = PALETTE.accent}
                onBlur={e => e.target.style.borderColor = PALETTE.border}
              />
              <button onClick={() => sendChat(query)} disabled={!query.trim() || aiLoading} style={{
                background: `linear-gradient(135deg, ${PALETTE.accent}, #d4380d)`, border: "none", borderRadius: 10,
                padding: "14px 24px", color: "#fff", fontFamily: FONT_BODY, fontSize: 14, fontWeight: 600,
                cursor: "pointer", opacity: !query.trim() || aiLoading ? 0.4 : 1
              }}>Send</button>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
