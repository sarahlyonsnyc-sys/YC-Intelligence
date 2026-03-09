import { useState, useEffect, useRef } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis } from "recharts";

// ─── YC Dataset (modeled on real YC trends & sectors) ───────────────────────
const YC_COMPANIES = [
  { name: "Stripe", sector: "Fintech", batch: "S09", status: "Active", funding: 8700, stage: "Late", desc: "Online payment processing for internet businesses", employees: 8000, founded: 2010 },
  { name: "Airbnb", sector: "Marketplace", batch: "W09", status: "IPO", funding: 6400, stage: "Public", desc: "Peer-to-peer lodging and tourism marketplace", employees: 6900, founded: 2008 },
  { name: "Coinbase", sector: "Crypto/Web3", batch: "S12", status: "IPO", funding: 547, stage: "Public", desc: "Cryptocurrency exchange platform", employees: 3700, founded: 2012 },
  { name: "Instacart", sector: "Marketplace", batch: "S12", status: "IPO", funding: 2900, stage: "Public", desc: "Grocery delivery and pickup service", employees: 3000, founded: 2012 },
  { name: "DoorDash", sector: "Marketplace", batch: "S13", status: "IPO", funding: 2500, stage: "Public", desc: "Food delivery logistics platform", employees: 16800, founded: 2013 },
  { name: "Gusto", sector: "B2B SaaS", batch: "W12", status: "Active", funding: 746, stage: "Late", desc: "Payroll, benefits, and HR for small businesses", employees: 2600, founded: 2011 },
  { name: "Brex", sector: "Fintech", batch: "W17", status: "Active", funding: 1200, stage: "Late", desc: "Corporate credit cards and spend management", employees: 1100, founded: 2017 },
  { name: "Retool", sector: "Developer Tools", batch: "W17", status: "Active", funding: 445, stage: "Series C", desc: "Low-code platform for internal tools", employees: 550, founded: 2017 },
  { name: "Scale AI", sector: "AI/ML", batch: "S16", status: "Active", funding: 1300, stage: "Late", desc: "AI training data platform", employees: 700, founded: 2016 },
  { name: "OpenSea", sector: "Crypto/Web3", batch: "W18", status: "Active", funding: 427, stage: "Series C", desc: "NFT marketplace", employees: 250, founded: 2017 },
  { name: "Faire", sector: "Marketplace", batch: "W17", status: "Active", funding: 1100, stage: "Late", desc: "B2B wholesale marketplace for retailers", employees: 1000, founded: 2017 },
  { name: "Meesho", sector: "E-commerce", batch: "W16", status: "Active", funding: 1100, stage: "Late", desc: "Social commerce platform for India", employees: 2000, founded: 2015 },
  { name: "Checkr", sector: "B2B SaaS", batch: "S14", status: "Active", funding: 679, stage: "Late", desc: "AI-powered background check platform", employees: 800, founded: 2014 },
  { name: "Groww", sector: "Fintech", batch: "W18", status: "Active", funding: 393, stage: "Series E", desc: "Investment platform for India", employees: 1500, founded: 2016 },
  { name: "Podium", sector: "B2B SaaS", batch: "W16", status: "Active", funding: 458, stage: "Series D", desc: "Customer messaging platform for local businesses", employees: 1500, founded: 2014 },
  { name: "Razorpay", sector: "Fintech", batch: "W15", status: "Active", funding: 741, stage: "Late", desc: "Payment gateway for India", employees: 3000, founded: 2014 },
  { name: "Zapier", sector: "Developer Tools", batch: "S12", status: "Active", funding: 1350, stage: "Late", desc: "Workflow automation connecting apps", employees: 800, founded: 2011 },
  { name: "Webflow", sector: "Developer Tools", batch: "W13", status: "Active", funding: 335, stage: "Series C", desc: "Visual web design and CMS platform", employees: 700, founded: 2013 },
  { name: "Whatnot", sector: "E-commerce", batch: "W20", status: "Active", funding: 484, stage: "Series D", desc: "Live shopping and auction platform", employees: 500, founded: 2019 },
  { name: "Flexport", sector: "Logistics", batch: "W14", status: "Active", funding: 2300, stage: "Late", desc: "Freight forwarding and supply chain", employees: 3600, founded: 2013 },
  { name: "Deel", sector: "B2B SaaS", batch: "W19", status: "Active", funding: 679, stage: "Series D", desc: "Global payroll and compliance platform", employees: 4000, founded: 2019 },
  { name: "Momentive", sector: "B2B SaaS", batch: "W12", status: "IPO", funding: 500, stage: "Public", desc: "Survey and experience management", employees: 1600, founded: 1999 },
  { name: "GitLab", sector: "Developer Tools", batch: "W15", status: "IPO", funding: 426, stage: "Public", desc: "DevOps lifecycle platform", employees: 2100, founded: 2014 },
  { name: "Mux", sector: "Developer Tools", batch: "S16", status: "Active", funding: 225, stage: "Series D", desc: "Video infrastructure API", employees: 300, founded: 2016 },
  { name: "Spotter", sector: "AI/ML", batch: "W24", status: "Active", funding: 70, stage: "Series A", desc: "AI-powered YouTube analytics for creators", employees: 80, founded: 2023 },
  { name: "Cognition", sector: "AI/ML", batch: "W24", status: "Active", funding: 175, stage: "Series A", desc: "AI software engineering agents", employees: 50, founded: 2023 },
  { name: "Mercor", sector: "AI/ML", batch: "S23", status: "Active", funding: 32, stage: "Seed", desc: "AI-powered hiring and talent matching", employees: 30, founded: 2023 },
  { name: "Luma AI", sector: "AI/ML", batch: "W22", status: "Active", funding: 85, stage: "Series B", desc: "3D capture and generative AI", employees: 60, founded: 2021 },
  { name: "Pika", sector: "AI/ML", batch: "S23", status: "Active", funding: 135, stage: "Series A", desc: "AI video generation platform", employees: 45, founded: 2023 },
  { name: "Healthie", sector: "Healthcare", batch: "S17", status: "Active", funding: 40, stage: "Series B", desc: "Infrastructure for virtual healthcare", employees: 120, founded: 2016 },
  { name: "Vanta", sector: "Cybersecurity", batch: "W18", status: "Active", funding: 352, stage: "Series C", desc: "Automated security compliance", employees: 500, founded: 2018 },
  { name: "CalHacks", sector: "Education", batch: "S24", status: "Active", funding: 5, stage: "Pre-seed", desc: "AI-first university hackathon platform", employees: 8, founded: 2024 },
  { name: "Luminary Cloud", sector: "AI/ML", batch: "S21", status: "Active", funding: 115, stage: "Series B", desc: "Cloud simulation with GPU acceleration", employees: 70, founded: 2019 },
  { name: "Supabase", sector: "Developer Tools", batch: "S20", status: "Active", funding: 116, stage: "Series B", desc: "Open source Firebase alternative", employees: 150, founded: 2020 },
  { name: "Railway", sector: "Developer Tools", batch: "W21", status: "Active", funding: 55, stage: "Series A", desc: "Cloud infrastructure deployment", employees: 50, founded: 2020 },
  { name: "Resend", sector: "Developer Tools", batch: "W23", status: "Active", funding: 8, stage: "Seed", desc: "Developer-first email API", employees: 15, founded: 2022 },
  { name: "Warp", sector: "Developer Tools", batch: "W20", status: "Active", funding: 73, stage: "Series B", desc: "AI-powered terminal for developers", employees: 50, founded: 2020 },
  { name: "Glean", sector: "AI/ML", batch: "S19", status: "Active", funding: 360, stage: "Series D", desc: "AI enterprise search and knowledge", employees: 500, founded: 2019 },
  { name: "PostHog", sector: "Developer Tools", batch: "W20", status: "Active", funding: 27, stage: "Series B", desc: "Open source product analytics", employees: 50, founded: 2020 },
  { name: "Vercel", sector: "Developer Tools", batch: "S16", status: "Active", funding: 313, stage: "Series D", desc: "Frontend cloud platform and Next.js", employees: 450, founded: 2015 },
  { name: "Fivetran", sector: "B2B SaaS", batch: "W13", status: "Active", funding: 730, stage: "Late", desc: "Automated data integration", employees: 1400, founded: 2012 },
  { name: "Convoy", sector: "Logistics", batch: "W15", status: "Shutdown", funding: 900, stage: "Series D", desc: "Digital freight network", employees: 0, founded: 2015 },
  { name: "Fast", sector: "Fintech", batch: "S19", status: "Shutdown", funding: 125, stage: "Series B", desc: "One-click checkout", employees: 0, founded: 2019 },
  { name: "Olive AI", sector: "Healthcare", batch: "W17", status: "Shutdown", funding: 902, stage: "Series H", desc: "Healthcare operations automation", employees: 0, founded: 2012 },
];

// ─── Derived analytics ──────────────────────────────────────────────────────
const SECTORS = [...new Set(YC_COMPANIES.map(c => c.sector))];
const COLORS = ["#f72585","#b5179e","#7209b7","#560bad","#480ca8","#3a0ca3","#3f37c9","#4361ee","#4895ef","#4cc9f0","#06d6a0","#ffd166","#ef476f","#118ab2"];

function getSectorStats() {
  const map = {};
  SECTORS.forEach(s => { map[s] = { sector: s, count: 0, totalFunding: 0, avgFunding: 0, ipos: 0, shutdowns: 0, active: 0 }; });
  YC_COMPANIES.forEach(c => {
    map[c.sector].count++;
    map[c.sector].totalFunding += c.funding;
    if (c.status === "IPO") map[c.sector].ipos++;
    if (c.status === "Shutdown") map[c.sector].shutdowns++;
    if (c.status === "Active") map[c.sector].active++;
  });
  Object.values(map).forEach(s => { s.avgFunding = Math.round(s.totalFunding / s.count); s.successRate = Math.round(((s.ipos + s.active) / s.count) * 100); });
  return Object.values(map).sort((a, b) => b.totalFunding - a.totalFunding);
}

function getRadarData() {
  const stats = getSectorStats().slice(0, 6);
  return stats.map(s => ({ sector: s.sector.replace("/", "/\n"), funding: Math.min(s.avgFunding / 20, 100), count: s.count * 5, success: s.successRate, ipos: s.ipos * 25 }));
}

// ─── Components ──────────────────────────────────────────────────────────────

function Loader() {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
      <div style={{ width: 20, height: 20, border: "2px solid rgba(247,37,133,0.3)", borderTop: "2px solid #f72585", borderRadius: "50%", animation: "spin 0.8s linear infinite" }} />
      <span style={{ color: "#b0b0c0", fontFamily: "'IBM Plex Mono', monospace", fontSize: 13 }}>Claude is analyzing...</span>
    </div>
  );
}

function StatCard({ label, value, sub, accent = "#f72585" }) {
  return (
    <div style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: 12, padding: "20px 24px", minWidth: 160 }}>
      <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, color: "#666", textTransform: "uppercase", letterSpacing: 1.5, marginBottom: 8 }}>{label}</div>
      <div style={{ fontFamily: "'Space Grotesk', sans-serif", fontSize: 32, fontWeight: 700, color: accent, lineHeight: 1 }}>{value}</div>
      {sub && <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, color: "#555", marginTop: 6 }}>{sub}</div>}
    </div>
  );
}

function CompanyRow({ company, i }) {
  const statusColor = { Active: "#06d6a0", IPO: "#4cc9f0", Shutdown: "#ef476f" }[company.status] || "#666";
  return (
    <div style={{ display: "grid", gridTemplateColumns: "2fr 1.2fr 0.8fr 1fr 0.8fr", alignItems: "center", padding: "12px 16px", background: i % 2 === 0 ? "rgba(255,255,255,0.015)" : "transparent", borderRadius: 6, fontSize: 13, fontFamily: "'IBM Plex Mono', monospace", color: "#c0c0d0" }}>
      <div>
        <span style={{ color: "#fff", fontWeight: 600 }}>{company.name}</span>
        <span style={{ color: "#555", marginLeft: 8, fontSize: 11 }}>{company.batch}</span>
      </div>
      <div style={{ color: "#888" }}>{company.sector}</div>
      <div><span style={{ color: statusColor, background: `${statusColor}15`, padding: "2px 8px", borderRadius: 4, fontSize: 11 }}>{company.status}</span></div>
      <div style={{ color: "#f72585" }}>${company.funding >= 1000 ? `${(company.funding / 1000).toFixed(1)}B` : `${company.funding}M`}</div>
      <div style={{ color: "#666" }}>{company.stage}</div>
    </div>
  );
}

// ─── Main App ────────────────────────────────────────────────────────────────
export default function YCIntelligence() {
  const [tab, setTab] = useState("dashboard");
  const [query, setQuery] = useState("");
  const [aiResponse, setAiResponse] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [chatHistory, setChatHistory] = useState([]);
  const [sectorFilter, setSectorFilter] = useState("All");
  const [sortBy, setSortBy] = useState("funding");
  const chatEndRef = useRef(null);

  const sectorStats = getSectorStats();
  const radarData = getRadarData();
  const pieData = sectorStats.map((s, i) => ({ name: s.sector, value: s.count, color: COLORS[i % COLORS.length] }));

  const filteredCompanies = YC_COMPANIES
    .filter(c => sectorFilter === "All" || c.sector === sectorFilter)
    .sort((a, b) => sortBy === "funding" ? b.funding - a.funding : sortBy === "name" ? a.name.localeCompare(b.name) : b.founded - a.founded);

  useEffect(() => { chatEndRef.current?.scrollIntoView({ behavior: "smooth" }); }, [chatHistory]);

  const analyzeWithClaude = async (prompt) => {
    setIsLoading(true);
    setChatHistory(prev => [...prev, { role: "user", text: prompt }]);
    setQuery("");

    const systemPrompt = `You are a Y Combinator startup analyst AI. You have deep knowledge of the YC ecosystem, startup funding patterns, and market trends.

Here is the current dataset you're analyzing (${YC_COMPANIES.length} companies from YC):
${JSON.stringify(YC_COMPANIES.map(c => ({ name: c.name, sector: c.sector, batch: c.batch, status: c.status, funding_M: c.funding, stage: c.stage, desc: c.desc })), null, 2)}

Sector summary:
${JSON.stringify(sectorStats, null, 2)}

When analyzing:
- Be specific with data points from the dataset
- Identify patterns, whitespace, and opportunities
- Give concrete startup ideas when asked
- Rate opportunities on fundability (1-10), market timing, and competition
- Be bold and opinionated, not wishy-washy
- Use short paragraphs, not walls of text
- Include specific numbers and percentages

Format with markdown-style bold using ** for emphasis. Keep responses focused and actionable.`;

    try {
      const response = await fetch("https://api.anthropic.com/v1/messages", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model: "claude-sonnet-4-20250514",
          max_tokens: 1000,
          system: systemPrompt,
          messages: [
            ...chatHistory.map(m => ({ role: m.role === "user" ? "user" : "assistant", content: m.text })),
            { role: "user", content: prompt }
          ],
        }),
      });
      const data = await response.json();
      const text = data.content?.map(b => b.text || "").join("\n") || "Analysis unavailable — check your API connection.";
      setChatHistory(prev => [...prev, { role: "assistant", text }]);
    } catch (err) {
      setChatHistory(prev => [...prev, { role: "assistant", text: "⚠ Could not reach Claude API. This app requires being run inside Claude.ai artifacts to use the built-in API. The dashboard and data explorer still work fully." }]);
    }
    setIsLoading(false);
  };

  const quickPrompts = [
    "What sector has the highest success rate and why?",
    "Give me 3 startup ideas in AI/ML with the best funding potential right now",
    "What patterns do you see in companies that went IPO vs shut down?",
    "Where is the biggest whitespace opportunity YC hasn't funded enough?",
    "If I wanted to start a B2B SaaS company today, what niche should I target?",
  ];

  const formatAIText = (text) => {
    return text.split("\n").map((line, i) => {
      const parts = line.split(/(\*\*[^*]+\*\*)/g);
      return (
        <p key={i} style={{ margin: "6px 0", lineHeight: 1.65 }}>
          {parts.map((part, j) =>
            part.startsWith("**") && part.endsWith("**")
              ? <strong key={j} style={{ color: "#f72585" }}>{part.slice(2, -2)}</strong>
              : part
          )}
        </p>
      );
    });
  };

  const navItems = [
    { id: "dashboard", label: "Dashboard" },
    { id: "explorer", label: "Explorer" },
    { id: "analyst", label: "AI Analyst" },
  ];

  return (
    <div style={{ minHeight: "100vh", background: "#0a0a0f", color: "#e0e0e8", fontFamily: "'IBM Plex Mono', monospace" }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap');
        @keyframes spin { to { transform: rotate(360deg) } }
        @keyframes fadeUp { from { opacity: 0; transform: translateY(12px) } to { opacity: 1; transform: translateY(0) } }
        @keyframes pulse { 0%, 100% { opacity: 0.4 } 50% { opacity: 1 } }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: #333; border-radius: 3px; }
        ::selection { background: #f7258540; }
      `}</style>

      {/* ── Header ─────────────────────────────────── */}
      <header style={{ borderBottom: "1px solid rgba(255,255,255,0.05)", padding: "20px 32px", display: "flex", alignItems: "center", justifyContent: "space-between", background: "rgba(10,10,15,0.9)", backdropFilter: "blur(20px)", position: "sticky", top: 0, zIndex: 100 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <div style={{ width: 36, height: 36, background: "linear-gradient(135deg, #f72585, #7209b7)", borderRadius: 8, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 18, fontWeight: 700, fontFamily: "'Space Grotesk', sans-serif" }}>Y</div>
          <div>
            <div style={{ fontFamily: "'Space Grotesk', sans-serif", fontSize: 18, fontWeight: 700, color: "#fff", letterSpacing: -0.5 }}>YC Intelligence</div>
            <div style={{ fontSize: 10, color: "#555", letterSpacing: 2, textTransform: "uppercase" }}>Startup Analysis Platform</div>
          </div>
        </div>
        <nav style={{ display: "flex", gap: 4, background: "rgba(255,255,255,0.03)", borderRadius: 8, padding: 3 }}>
          {navItems.map(n => (
            <button key={n.id} onClick={() => setTab(n.id)} style={{
              padding: "8px 20px", borderRadius: 6, border: "none", cursor: "pointer", fontSize: 12, fontFamily: "'IBM Plex Mono', monospace", fontWeight: 500, letterSpacing: 0.5,
              background: tab === n.id ? "rgba(247,37,133,0.15)" : "transparent",
              color: tab === n.id ? "#f72585" : "#666",
              transition: "all 0.2s"
            }}>{n.label}</button>
          ))}
        </nav>
      </header>

      <main style={{ padding: "32px", maxWidth: 1280, margin: "0 auto" }}>
        {/* ── Dashboard ─────────────────────────────── */}
        {tab === "dashboard" && (
          <div style={{ animation: "fadeUp 0.4s ease" }}>
            <div style={{ display: "flex", gap: 16, flexWrap: "wrap", marginBottom: 32 }}>
              <StatCard label="Total Companies" value={YC_COMPANIES.length} sub="In dataset" accent="#4cc9f0" />
              <StatCard label="Total Funding" value={`$${(YC_COMPANIES.reduce((a, c) => a + c.funding, 0) / 1000).toFixed(1)}B`} sub="Combined raised" accent="#f72585" />
              <StatCard label="IPOs" value={YC_COMPANIES.filter(c => c.status === "IPO").length} sub={`${Math.round(YC_COMPANIES.filter(c => c.status === "IPO").length / YC_COMPANIES.length * 100)}% of dataset`} accent="#06d6a0" />
              <StatCard label="Sectors" value={SECTORS.length} sub="Categories tracked" accent="#ffd166" />
              <StatCard label="Shutdowns" value={YC_COMPANIES.filter(c => c.status === "Shutdown").length} sub={`${Math.round(YC_COMPANIES.filter(c => c.status === "Shutdown").length / YC_COMPANIES.length * 100)}% failure rate`} accent="#ef476f" />
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24, marginBottom: 32 }}>
              {/* Funding by sector bar chart */}
              <div style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.05)", borderRadius: 12, padding: 24 }}>
                <div style={{ fontSize: 11, color: "#666", textTransform: "uppercase", letterSpacing: 1.5, marginBottom: 16 }}>Total Funding by Sector ($M)</div>
                <ResponsiveContainer width="100%" height={260}>
                  <BarChart data={sectorStats.slice(0, 8)} margin={{ left: -10 }}>
                    <XAxis dataKey="sector" tick={{ fill: "#555", fontSize: 10 }} axisLine={false} tickLine={false} interval={0} angle={-25} textAnchor="end" height={60} />
                    <YAxis tick={{ fill: "#444", fontSize: 10 }} axisLine={false} tickLine={false} />
                    <Tooltip contentStyle={{ background: "#16161e", border: "1px solid #333", borderRadius: 8, fontFamily: "'IBM Plex Mono', monospace", fontSize: 12 }} />
                    <Bar dataKey="totalFunding" radius={[4, 4, 0, 0]}>
                      {sectorStats.slice(0, 8).map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>

              {/* Sector distribution pie */}
              <div style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.05)", borderRadius: 12, padding: 24 }}>
                <div style={{ fontSize: 11, color: "#666", textTransform: "uppercase", letterSpacing: 1.5, marginBottom: 16 }}>Company Distribution</div>
                <ResponsiveContainer width="100%" height={260}>
                  <PieChart>
                    <Pie data={pieData} cx="50%" cy="50%" innerRadius={55} outerRadius={95} paddingAngle={2} dataKey="value">
                      {pieData.map((entry, i) => <Cell key={i} fill={entry.color} />)}
                    </Pie>
                    <Tooltip contentStyle={{ background: "#16161e", border: "1px solid #333", borderRadius: 8, fontFamily: "'IBM Plex Mono', monospace", fontSize: 12 }} />
                  </PieChart>
                </ResponsiveContainer>
                <div style={{ display: "flex", flexWrap: "wrap", gap: "6px 16px", marginTop: 8 }}>
                  {pieData.map((d, i) => (
                    <div key={i} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 10, color: "#888" }}>
                      <div style={{ width: 8, height: 8, borderRadius: 2, background: d.color }} />
                      {d.name}
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Sector Success Table */}
            <div style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.05)", borderRadius: 12, padding: 24 }}>
              <div style={{ fontSize: 11, color: "#666", textTransform: "uppercase", letterSpacing: 1.5, marginBottom: 16 }}>Sector Performance Breakdown</div>
              <div style={{ display: "grid", gridTemplateColumns: "1.5fr repeat(5, 1fr)", padding: "8px 16px", fontSize: 10, color: "#555", textTransform: "uppercase", letterSpacing: 1, borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
                <div>Sector</div><div>Companies</div><div>Avg Funding</div><div>IPOs</div><div>Shutdowns</div><div>Success %</div>
              </div>
              {sectorStats.map((s, i) => (
                <div key={i} style={{ display: "grid", gridTemplateColumns: "1.5fr repeat(5, 1fr)", padding: "10px 16px", fontSize: 12, color: "#b0b0c0", borderBottom: "1px solid rgba(255,255,255,0.02)" }}>
                  <div style={{ color: "#fff", fontWeight: 600 }}>{s.sector}</div>
                  <div>{s.count}</div>
                  <div style={{ color: "#f72585" }}>${s.avgFunding}M</div>
                  <div style={{ color: "#4cc9f0" }}>{s.ipos}</div>
                  <div style={{ color: "#ef476f" }}>{s.shutdowns}</div>
                  <div>
                    <span style={{ color: s.successRate > 85 ? "#06d6a0" : s.successRate > 70 ? "#ffd166" : "#ef476f" }}>{s.successRate}%</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ── Explorer ─────────────────────────────── */}
        {tab === "explorer" && (
          <div style={{ animation: "fadeUp 0.4s ease" }}>
            <div style={{ display: "flex", gap: 12, marginBottom: 24, flexWrap: "wrap" }}>
              <select value={sectorFilter} onChange={e => setSectorFilter(e.target.value)} style={{ background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 8, padding: "8px 16px", color: "#c0c0d0", fontFamily: "'IBM Plex Mono', monospace", fontSize: 12, cursor: "pointer", outline: "none" }}>
                <option value="All">All Sectors</option>
                {SECTORS.sort().map(s => <option key={s} value={s}>{s}</option>)}
              </select>
              <select value={sortBy} onChange={e => setSortBy(e.target.value)} style={{ background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 8, padding: "8px 16px", color: "#c0c0d0", fontFamily: "'IBM Plex Mono', monospace", fontSize: 12, cursor: "pointer", outline: "none" }}>
                <option value="funding">Sort by Funding</option>
                <option value="name">Sort by Name</option>
                <option value="founded">Sort by Newest</option>
              </select>
              <div style={{ marginLeft: "auto", fontSize: 12, color: "#555", padding: "8px 0" }}>{filteredCompanies.length} companies</div>
            </div>

            <div style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.05)", borderRadius: 12, overflow: "hidden" }}>
              <div style={{ display: "grid", gridTemplateColumns: "2fr 1.2fr 0.8fr 1fr 0.8fr", padding: "12px 16px", fontSize: 10, color: "#555", textTransform: "uppercase", letterSpacing: 1, borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
                <div>Company</div><div>Sector</div><div>Status</div><div>Funding</div><div>Stage</div>
              </div>
              <div style={{ maxHeight: 500, overflowY: "auto" }}>
                {filteredCompanies.map((c, i) => <CompanyRow key={c.name} company={c} i={i} />)}
              </div>
            </div>
          </div>
        )}

        {/* ── AI Analyst ─────────────────────────────── */}
        {tab === "analyst" && (
          <div style={{ animation: "fadeUp 0.4s ease", display: "flex", flexDirection: "column", height: "calc(100vh - 160px)" }}>
            <div style={{ fontSize: 11, color: "#555", textTransform: "uppercase", letterSpacing: 1.5, marginBottom: 12 }}>
              Claude-Powered Analysis · Ask anything about YC startups
            </div>

            {/* Quick prompts */}
            {chatHistory.length === 0 && (
              <div style={{ marginBottom: 24 }}>
                <div style={{ fontSize: 12, color: "#666", marginBottom: 12 }}>Quick analysis prompts:</div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                  {quickPrompts.map((p, i) => (
                    <button key={i} onClick={() => analyzeWithClaude(p)} style={{
                      background: "rgba(247,37,133,0.06)", border: "1px solid rgba(247,37,133,0.15)", borderRadius: 8, padding: "10px 16px",
                      color: "#c0c0d0", fontFamily: "'IBM Plex Mono', monospace", fontSize: 12, cursor: "pointer", textAlign: "left", lineHeight: 1.4,
                      transition: "all 0.2s", maxWidth: 340
                    }}
                    onMouseOver={e => { e.target.style.borderColor = "#f72585"; e.target.style.background = "rgba(247,37,133,0.12)"; }}
                    onMouseOut={e => { e.target.style.borderColor = "rgba(247,37,133,0.15)"; e.target.style.background = "rgba(247,37,133,0.06)"; }}
                    >{p}</button>
                  ))}
                </div>
              </div>
            )}

            {/* Chat area */}
            <div style={{ flex: 1, overflowY: "auto", marginBottom: 16, display: "flex", flexDirection: "column", gap: 16 }}>
              {chatHistory.map((msg, i) => (
                <div key={i} style={{
                  alignSelf: msg.role === "user" ? "flex-end" : "flex-start",
                  maxWidth: msg.role === "user" ? "70%" : "90%",
                  background: msg.role === "user" ? "rgba(247,37,133,0.1)" : "rgba(255,255,255,0.03)",
                  border: `1px solid ${msg.role === "user" ? "rgba(247,37,133,0.2)" : "rgba(255,255,255,0.05)"}`,
                  borderRadius: 12, padding: "14px 18px",
                  fontSize: 13, color: "#d0d0e0", lineHeight: 1.6
                }}>
                  {msg.role === "user" ? (
                    <div style={{ fontWeight: 500 }}>{msg.text}</div>
                  ) : (
                    <div>{formatAIText(msg.text)}</div>
                  )}
                </div>
              ))}
              {isLoading && (
                <div style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.05)", borderRadius: 12, padding: "14px 18px" }}>
                  <Loader />
                </div>
              )}
              <div ref={chatEndRef} />
            </div>

            {/* Input */}
            <div style={{ display: "flex", gap: 8 }}>
              <input
                value={query}
                onChange={e => setQuery(e.target.value)}
                onKeyDown={e => { if (e.key === "Enter" && query.trim() && !isLoading) analyzeWithClaude(query.trim()); }}
                placeholder="Ask Claude to analyze YC data, find opportunities, generate startup ideas..."
                style={{
                  flex: 1, background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 10,
                  padding: "14px 18px", color: "#e0e0e8", fontFamily: "'IBM Plex Mono', monospace", fontSize: 13, outline: "none",
                  transition: "border-color 0.2s"
                }}
                onFocus={e => e.target.style.borderColor = "rgba(247,37,133,0.4)"}
                onBlur={e => e.target.style.borderColor = "rgba(255,255,255,0.08)"}
              />
              <button
                onClick={() => { if (query.trim() && !isLoading) analyzeWithClaude(query.trim()); }}
                disabled={!query.trim() || isLoading}
                style={{
                  background: "linear-gradient(135deg, #f72585, #7209b7)", border: "none", borderRadius: 10, padding: "14px 24px",
                  color: "#fff", fontFamily: "'IBM Plex Mono', monospace", fontSize: 13, fontWeight: 600, cursor: "pointer",
                  opacity: !query.trim() || isLoading ? 0.4 : 1, transition: "opacity 0.2s"
                }}
              >Analyze</button>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
