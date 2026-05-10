import React, { useCallback, useEffect, useState } from "react";

const API = "/api";

// ----------------------
// Reusable UI Components
// ----------------------

const Card = ({ children, style, className = "", onClick, hoverable = false }) => {
  const [isHovered, setIsHovered] = useState(false);
  return (
    <div
      onClick={onClick}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      className={className}
      style={{
        background: isHovered && hoverable ? "var(--bg-card-hover)" : "var(--bg-card)",
        border: `1px solid ${isHovered && hoverable ? "var(--border-color-hover)" : "var(--border-color)"}`,
        borderRadius: "12px",
        padding: "1.25rem",
        backdropFilter: "blur(12px)",
        transition: "all 0.2s ease-in-out",
        cursor: onClick ? "pointer" : "default",
        ...style,
      }}
    >
      {children}
    </div>
  );
};

const Badge = ({ children, variant = "neutral", style }) => {
  const colors = {
    low: { c: "var(--badge-low)", bg: "var(--badge-low-bg)" },
    medium: { c: "var(--badge-medium)", bg: "var(--badge-medium-bg)" },
    high: { c: "var(--badge-high)", bg: "var(--badge-high-bg)" },
    critical: { c: "var(--badge-critical)", bg: "var(--badge-critical-bg)" },
    neutral: { c: "var(--badge-neutral)", bg: "var(--badge-neutral-bg)" },
  };
  const theme = colors[variant.toLowerCase()] || colors.neutral;

  return (
    <span
      style={{
        color: theme.c,
        backgroundColor: theme.bg,
        padding: "0.25rem 0.5rem",
        borderRadius: "6px",
        fontSize: "0.75rem",
        fontWeight: "600",
        textTransform: "capitalize",
        whiteSpace: "nowrap",
        ...style,
      }}
    >
      {children}
    </span>
  );
};

const Button = ({ children, onClick, variant = "primary", disabled = false, style }) => {
  const [isHovered, setIsHovered] = useState(false);
  const isPrimary = variant === "primary";
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      style={{
        background: isPrimary ? "var(--accent-color)" : "transparent",
        color: isPrimary ? "#fff" : "var(--text-primary)",
        border: isPrimary ? "none" : "1px solid var(--border-color)",
        padding: "0.5rem 1rem",
        borderRadius: "8px",
        fontWeight: "500",
        cursor: disabled ? "not-allowed" : "pointer",
        opacity: disabled ? 0.5 : 1,
        transition: "all 0.2s ease",
        transform: isHovered && !disabled ? "translateY(-1px)" : "none",
        boxShadow: isHovered && isPrimary && !disabled ? "0 4px 12px rgba(99, 102, 241, 0.3)" : "none",
        ...(isHovered && !isPrimary && !disabled ? { background: "var(--bg-card-hover)" } : {}),
        ...style,
      }}
    >
      {children}
    </button>
  );
};

// ----------------------
// Main Application
// ----------------------

export default function App() {
  const [dash, setDash] = useState(null);
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);
  const [selectedId, setSelectedId] = useState(null);
  const [detail, setDetail] = useState(null);
  const [query, setQuery] = useState("");
  const [answer, setAnswer] = useState("");
  const [draft, setDraft] = useState(null);
  const [completingTaskIds, setCompletingTaskIds] = useState(new Set());

  const loadDash = useCallback(async () => {
    setErr("");
    try {
      const r = await fetch(`${API}/dashboard`);
      if (!r.ok) {
        setErr(await r.text());
        return;
      }
      setDash(await r.json());
    } catch (e) {
      setErr("Failed to load dashboard data: " + e.message);
    }
  }, []);

  useEffect(() => {
    loadDash();
  }, [loadDash]);

  useEffect(() => {
    if (!selectedId) {
      setDetail(null);
      return;
    }
    (async () => {
      try {
        const r = await fetch(`${API}/contracts/${selectedId}`);
        if (r.ok) setDetail(await r.json());
      } catch (e) {
        setErr("Failed to load contract details.");
      }
    })();
  }, [selectedId]);

  async function onUpload(e) {
    const f = e.target.files?.[0];
    if (!f) return;
    setLoading(true);
    setErr("");
    const fd = new FormData();
    fd.append("file", f);
    try {
      const r = await fetch(`${API}/upload`, { method: "POST", body: fd });
      const data = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(data.detail || JSON.stringify(data));
      await loadDash();
      setSelectedId(data.id);
    } catch (x) {
      setErr(String(x.message || x));
    } finally {
      setLoading(false);
      e.target.value = "";
    }
  }

  async function runMonitor() {
    setLoading(true);
    setErr("");
    try {
      const r = await fetch(`${API}/monitor/run`, { method: "POST" });
      if (!r.ok) {
        const text = await r.text();
        setErr(`Monitor error: ${text}`);
      } else {
        await loadDash();
      }
    } catch (e) {
      setErr("Failed to run monitor: " + e.message);
    } finally {
      setLoading(false);
    }
  }

  async function askRag() {
    if (!selectedId || !query.trim()) return;
    setAnswer("Searching...");
    try {
      const r = await fetch(`${API}/contracts/${selectedId}/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: query }),
      });
      const data = await r.json();
      setAnswer(data.answer || JSON.stringify(data));
    } catch (e) {
      setAnswer("Error fetching answer.");
    }
  }

  async function emailDraft(alertId) {
    try {
      const r = await fetch(`${API}/alerts/${alertId}/draft-email`, { method: "POST" });
      setDraft(await r.json());
    } catch (e) {
      setErr("Failed to generate draft.");
    }
  }

  async function handleResolveTask(taskId) {
    setCompletingTaskIds((prev) => new Set(prev).add(taskId));
    
    // Allow animation to play out
    setTimeout(async () => {
      try {
        await fetch(`${API}/tasks/${taskId}/resolve`, { method: "POST" });
        const r = await fetch(`${API}/contracts/${selectedId}`);
        if (r.ok) setDetail(await r.json());
        loadDash();
      } catch (e) {
        setErr("Failed to resolve task.");
      } finally {
        setCompletingTaskIds((prev) => {
          const next = new Set(prev);
          next.delete(taskId);
          return next;
        });
      }
    }, 400); // 400ms matches CSS animation
  }

  function copyDraft() {
    if (draft) {
      navigator.clipboard.writeText(`Subject: ${draft.subject}\n\n${draft.body}`);
    }
  }

  const hist = dash?.risk_histogram || {};
  const maxBar = Math.max(1, ...Object.values(hist));

  // Determine risk color logic
  const getRiskVariant = (score) => {
    if (score <= 30) return "low";
    if (score <= 60) return "medium";
    return "critical"; // 61-100
  };

  // Group alerts by contract for the dashboard
  const alertsByContract = dash?.recent_alerts.reduce((acc, alert) => {
    // Find contract filename
    const contract = dash.contracts.find((c) => c.id === alert.contract_id);
    const contractName = contract ? contract.filename : `Contract #${alert.contract_id}`;
    if (!acc[contractName]) acc[contractName] = [];
    acc[contractName].push(alert);
    return acc;
  }, {}) || {};

  return (
    <div style={{ maxWidth: "1280px", margin: "0 auto", padding: "2rem" }} className="animate-fade-in">
      <header style={{ marginBottom: "2.5rem", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <h1 style={{ fontSize: "2rem", letterSpacing: "-0.02em" }}>Contract Intelligence</h1>
          <p style={{ color: "var(--text-secondary)", marginTop: "0.25rem", fontSize: "1rem" }}>
            Automated tracking, risk assessment, and deadline monitoring.
          </p>
        </div>
        <div style={{ display: "flex", gap: "1rem" }}>
          <div>
            <input id="file-upload" type="file" accept=".pdf,.docx" hidden disabled={loading} onChange={onUpload} />
            <Button disabled={loading} onClick={() => document.getElementById('file-upload').click()}>
              <span style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                {loading ? (
                  "Processing..."
                ) : (
                  <>
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12"/></svg>
                    Upload Document
                  </>
                )}
              </span>
            </Button>
          </div>
          <Button variant="secondary" disabled={loading} onClick={runMonitor}>Check Deadlines</Button>
        </div>
      </header>

      {err && (
        <Card style={{ borderColor: "var(--badge-critical)", background: "var(--badge-critical-bg)", color: "#fca5a5", marginBottom: "1.5rem" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>
            <strong>Error:</strong> {err}
          </div>
        </Card>
      )}

      {/* Email Draft Modal Overlay */}
      {draft && (
        <div style={{ position: "fixed", inset: 0, backgroundColor: "rgba(0,0,0,0.6)", backdropFilter: "blur(4px)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000 }} className="animate-fade-in">
          <Card style={{ width: "100%", maxWidth: "600px", background: "var(--bg-gradient)", boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.5)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "1.5rem", borderBottom: "1px solid var(--border-color)", paddingBottom: "1rem" }}>
              <h2 style={{ fontSize: "1.25rem", margin: 0 }}>Draft Email</h2>
              <button 
                onClick={() => setDraft(null)}
                style={{ background: "transparent", border: "none", color: "var(--text-secondary)", cursor: "pointer", padding: "0.25rem" }}
              >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
              </button>
            </div>
            
            <div style={{ marginBottom: "1rem" }}>
              <strong style={{ color: "var(--text-secondary)", fontSize: "0.85rem", textTransform: "uppercase", letterSpacing: "0.05em" }}>Subject</strong>
              <div style={{ background: "rgba(0,0,0,0.2)", padding: "0.75rem", borderRadius: "8px", marginTop: "0.25rem", fontSize: "1rem", fontWeight: 600, color: "#fff" }}>
                {draft.subject}
              </div>
            </div>

            <div style={{ marginBottom: "1.5rem" }}>
              <strong style={{ color: "var(--text-secondary)", fontSize: "0.85rem", textTransform: "uppercase", letterSpacing: "0.05em" }}>Body</strong>
              <pre style={{ 
                whiteSpace: "pre-wrap", 
                background: "rgba(0,0,0,0.2)", 
                padding: "1rem", 
                borderRadius: "8px", 
                marginTop: "0.25rem",
                fontFamily: "var(--font-family)",
                fontSize: "0.95rem",
                lineHeight: "1.6",
                maxHeight: "300px",
                overflowY: "auto"
              }} className="custom-scrollbar">
                {draft.body}
              </pre>
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.75rem" }}>
              <Button variant="secondary" onClick={() => setDraft(null)}>Close</Button>
              <Button onClick={copyDraft}>
                <span style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
                  Copy to Clipboard
                </span>
              </Button>
            </div>
          </Card>
        </div>
      )}

      {!dash ? (
        <div style={{ display: "flex", justifyContent: "center", padding: "4rem" }}>
          <div style={{ width: "40px", height: "40px", borderRadius: "50%", border: "3px solid var(--border-color)", borderTopColor: "var(--accent-color)", animation: "spin 1s linear infinite" }} />
          <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
        </div>
      ) : (
        <>
          {/* Key Metrics Grid */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "1rem", marginBottom: "2rem" }}>
            {[
              { label: "Total Contracts", val: dash.total_contracts },
              { label: "Open Tasks", val: dash.open_tasks },
              { label: "Upcoming (7d)", val: dash.upcoming_deadlines },
              { label: "Overdue", val: dash.overdue_tasks, color: dash.overdue_tasks > 0 ? "var(--badge-critical)" : "" },
              { label: "Open Alerts", val: dash.open_alerts, color: dash.open_alerts > 0 ? "var(--badge-high)" : "" },
              { label: "Avg Risk Score", val: dash.avg_risk_score.toFixed(1) },
            ].map((m, i) => (
              <Card key={i} style={{ display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
                <span style={{ color: "var(--text-secondary)", fontSize: "0.85rem", fontWeight: 500 }}>{m.label}</span>
                <span style={{ fontSize: "2rem", fontWeight: 700, marginTop: "0.5rem", color: m.color || "#fff" }}>{m.val}</span>
              </Card>
            ))}
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: "1.5rem", alignItems: "start" }}>
            {/* Left Column: Contract List AND Selected Contract Detail */}
            <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
              
              {/* Contracts Nav */}
              <Card style={{ padding: 0, overflow: "hidden", display: "flex", flexDirection: "column" }}>
                <div style={{ padding: "1.25rem", borderBottom: "1px solid var(--border-color)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                   <h2 style={{ fontSize: "1.15rem", margin: 0 }}>Contract Documents</h2>
                   <Badge variant="neutral">{dash.contracts.length} Total</Badge>
                </div>
                <div style={{ maxHeight: "300px", overflowY: "auto", padding: "0.5rem" }} className="custom-scrollbar">
                  <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
                    {dash.contracts.map((c) => (
                      <button
                        key={c.id}
                        onClick={() => setSelectedId(c.id)}
                        style={{
                          flex: "1 1 calc(50% - 0.5rem)",
                          minWidth: "250px",
                          textAlign: "left",
                          padding: "1rem",
                          borderRadius: "8px",
                          background: selectedId === c.id ? "rgba(99, 102, 241, 0.1)" : "transparent",
                          border: `1px solid ${selectedId === c.id ? "var(--accent-color)" : "transparent"}`,
                          cursor: "pointer",
                          transition: "all 0.2s",
                        }}
                        onMouseEnter={(e) => { if (selectedId !== c.id) e.currentTarget.style.background = "var(--bg-card-hover)"; }}
                        onMouseLeave={(e) => { if (selectedId !== c.id) e.currentTarget.style.background = "transparent"; }}
                      >
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "0.5rem" }}>
                          <span style={{ fontWeight: 600, color: "#fff", wordBreak: "break-all" }}>{c.filename}</span>
                          <Badge variant={getRiskVariant(c.overall_risk_score)} style={{ padding: "0.15rem 0.4rem", fontSize: "0.7rem" }}>
                            {'Risk ' + (c.overall_risk_score?.toFixed(1) || 0)}
                          </Badge>
                        </div>
                        <div style={{ display: "flex", gap: "1rem", color: "var(--text-secondary)", fontSize: "0.8rem" }}>
                           <span style={{ display: "flex", alignItems: "center", gap: "0.25rem" }}><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 20h9"></path><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"></path></svg>{c.task_count} Tasks</span>
                           <span style={{ display: "flex", alignItems: "center", gap: "0.25rem", color: c.open_alert_count > 0 ? "var(--badge-high)" : "" }}><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"></path><path d="M13.73 21a2 2 0 0 1-3.46 0"></path></svg>{c.open_alert_count} Alerts</span>
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
              </Card>

              {/* Selected Contract Details */}
              {detail && (
                <div className="animate-slide-up">
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
                    <h2 style={{ fontSize: "1.5rem", margin: 0, wordBreak: "break-all" }}>{detail.filename}</h2>
                    <Badge variant={getRiskVariant(detail.overall_risk_score)} style={{ fontSize: "1rem", padding: "0.35rem 0.75rem" }}>
                      Risk Score: {detail.overall_risk_score?.toFixed(1) || 0}
                    </Badge>
                  </div>

                  {/* Tasks Section */}
                  <Card style={{ marginBottom: "1.5rem" }}>
                    <h3 style={{ margin: "0 0 1rem 0", fontSize: "1.1rem" }}>Task Tracking</h3>
                    
                    {/* Open Tasks */}
                    <div style={{ marginBottom: "1.5rem" }}>
                      <h4 style={{ color: "var(--text-secondary)", margin: "0 0 0.75rem 0", fontSize: "0.85rem", textTransform: "uppercase" }}>Open Tasks</h4>
                      <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                        {detail.tasks.filter(t => t.status === "open").length === 0 && <span style={{ color: "var(--text-secondary)", fontSize: "0.9rem" }}>No open tasks.</span>}
                        {detail.tasks.filter(t => t.status === "open").map((t) => (
                          <div 
                            key={t.id} 
                            className={completingTaskIds.has(t.id) ? "task-completing" : ""}
                            style={{ 
                              display: "flex", justifyContent: "space-between", alignItems: "center", 
                              background: "rgba(0,0,0,0.15)", padding: "0.75rem 1rem", borderRadius: "8px",
                              borderLeft: `3px solid var(--badge-${t.priority.toLowerCase() === 'critical' ? 'critical' : t.priority.toLowerCase() === 'high' ? 'high' : t.priority.toLowerCase() === 'low' ? 'low' : 'medium'})`,
                              overflow: "hidden"
                            }}
                          >
                            <div>
                               <div style={{ fontWeight: 600, fontSize: "0.95rem", marginBottom: "0.25rem" }}>{t.task_name}</div>
                               <div style={{ display: "flex", gap: "0.75rem", fontSize: "0.8rem", color: "var(--text-secondary)" }}>
                                  <span style={{ display: "flex", alignItems: "center", gap: "0.25rem" }}><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect><line x1="16" y1="2" x2="16" y2="6"></line><line x1="8" y1="2" x2="8" y2="6"></line><line x1="3" y1="10" x2="21" y2="10"></line></svg> {t.due_date ? new Date(t.due_date).toLocaleDateString() : "No deadline"}</span>
                                  <Badge variant={t.priority} style={{ padding: "0.1rem 0.3rem", fontSize: "0.65rem", backgroundColor: "transparent", border: "1px solid" }}>{t.priority}</Badge>
                               </div>
                            </div>
                            <Button 
                              onClick={() => handleResolveTask(t.id)} 
                              style={{ display: "flex", alignItems: "center", gap: "0.25rem", fontSize: "0.85rem", padding: "0.4rem 0.75rem" }}
                            >
                              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="20 6 9 17 4 12"></polyline></svg>
                              Mark Done
                            </Button>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Completed Tasks */}
                    {detail.tasks.filter(t => t.status === "done").length > 0 && (
                      <div>
                        <h4 style={{ color: "var(--badge-low)", margin: "0 0 0.75rem 0", fontSize: "0.85rem", textTransform: "uppercase", display: "flex", alignItems: "center", gap: "0.35rem" }}>
                           <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="20 6 9 17 4 12"></polyline></svg> Completed
                        </h4>
                        <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem", opacity: 0.65 }}>
                          {detail.tasks.filter(t => t.status === "done").map((t) => (
                            <div key={t.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", background: "rgba(255,255,255,0.02)", padding: "0.5rem 1rem", borderRadius: "8px" }}>
                              <span style={{ textDecoration: "line-through", fontSize: "0.9rem" }}>{t.task_name}</span>
                              <Badge variant="neutral" style={{ background: "transparent" }}>Done</Badge>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </Card>

                  {/* Risks Structured Area */}
                  <Card style={{ marginBottom: "1.5rem" }}>
                    <h3 style={{ margin: "0 0 1rem 0", fontSize: "1.1rem" }}>Identified Risks</h3>
                    {detail.risks.length === 0 ? (
                      <span style={{ color: "var(--text-secondary)" }}>No specific risks flagged.</span>
                    ) : (
                      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))", gap: "1rem" }}>
                        {detail.risks.map((r) => (
                           <div key={r.id} style={{ background: "rgba(0,0,0,0.15)", borderRadius: "8px", padding: "1rem", borderTop: `3px solid var(--badge-${getRiskVariant(r.score)})` }}>
                              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "0.5rem" }}>
                                 <strong style={{ fontSize: "0.95rem" }}>{r.title}</strong>
                                 <Badge variant={getRiskVariant(r.score)} style={{ padding: "0.15rem 0.35rem", fontSize: "0.7rem", flexShrink: 0, marginLeft: "0.5rem" }}>Score: {r.score}</Badge>
                              </div>
                              <Badge variant="neutral" style={{ display: "inline-block", background: "transparent", border: "1px solid var(--border-color)", padding: "0.1rem 0.35rem", fontSize: "0.65rem", marginBottom: "0.5rem" }}>{r.category}</Badge>
                              <p style={{ margin: 0, fontSize: "0.85rem", color: "var(--text-secondary)", lineHeight: "1.4" }}>{r.description}</p>
                           </div>
                        ))}
                      </div>
                    )}
                  </Card>

                  {/* RAG Query Area */}
                  <Card>
                    <h3 style={{ margin: "0 0 0.75rem 0", fontSize: "1.1rem", display: "flex", alignItems: "center", gap: "0.5rem" }}>
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--accent-color)" strokeWidth="2"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
                      Ask the Contract
                    </h3>
                    <div style={{ display: "flex", gap: "0.5rem" }}>
                      <input
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        placeholder="e.g., What are the termination conditions?"
                        onKeyDown={(e) => e.key === 'Enter' && askRag()}
                        style={{ 
                          flex: 1, padding: "0.75rem 1rem", borderRadius: "8px", 
                          border: "1px solid var(--border-color)", background: "rgba(0,0,0,0.2)", 
                          color: "#fff", fontSize: "0.95rem", outline: "none",
                          boxShadow: "inset 0 2px 4px rgba(0,0,0,0.1)"
                        }}
                      />
                      <Button onClick={askRag}>Search</Button>
                    </div>
                    {answer && (
                      <div className="animate-fade-in" style={{ marginTop: "1rem", padding: "1rem", background: "var(--bg-card)", borderLeft: "3px solid var(--accent-color)", borderRadius: "0 8px 8px 0", fontSize: "0.95rem", lineHeight: 1.5 }}>
                        {answer}
                      </div>
                    )}
                  </Card>
                </div>
              )}
            </div>

            {/* Right Column: Risk Histogram & Dashboard Alerts (Grouped) */}
            <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
              
              {/* Refactored Risk Histogram */}
              <Card>
                <h3 style={{ margin: "0 0 1rem 0", fontSize: "1.1rem" }}>Risk Distribution</h3>
                <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
                  {Object.entries(hist).map(([label, count]) => {
                    const widthPct = maxBar > 0 ? (count / maxBar) * 100 : 0;
                    return (
                      <div key={label} style={{ display: "flex", alignItems: "center", gap: "0.75rem", cursor: "crosshair" }} title={`${count} Contracts`}>
                        <div style={{ width: "45px", fontSize: "0.75rem", color: "var(--text-secondary)", textAlign: "right", fontFamily: "monospace" }}>{label}</div>
                        <div style={{ flex: 1, background: "rgba(0,0,0,0.3)", borderRadius: "4px", height: "16px", overflow: "hidden" }}>
                           <div style={{ 
                             width: `${widthPct}%`, 
                             height: "100%", 
                             background: "linear-gradient(90deg, var(--accent-color), #818cf8)", 
                             borderRadius: "4px",
                             transition: "width 0.5s ease-out" 
                           }} />
                        </div>
                        <div style={{ width: "20px", fontSize: "0.85rem", fontWeight: 600, textAlign: "left" }}>{count}</div>
                      </div>
                    )
                  })}
                </div>
              </Card>

              {/* Grouped Alerts Area */}
              <Card style={{ padding: 0, overflow: "hidden", display: "flex", flexDirection: "column", maxHeight: "600px" }}>
                <div style={{ padding: "1.25rem", borderBottom: "1px solid var(--border-color)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                   <h2 style={{ fontSize: "1.15rem", margin: 0, display: "flex", alignItems: "center", gap: "0.5rem" }}>
                     <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--badge-high)" strokeWidth="2"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"></path><path d="M13.73 21a2 2 0 0 1-3.46 0"></path></svg>
                     Actionable Alerts
                   </h2>
                   <Badge variant="high">{dash.open_alerts}</Badge>
                </div>
                
                <div style={{ padding: "1.25rem", overflowY: "auto" }} className="custom-scrollbar">
                  {Object.keys(alertsByContract).length === 0 ? (
                    <div style={{ textAlign: "center", color: "var(--text-secondary)", padding: "2rem 0" }}>All clear. No outstanding alerts.</div>
                  ) : (
                    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
                      {Object.entries(alertsByContract).map(([contractName, alerts]) => (
                        <div key={contractName}>
                          <h4 style={{ margin: "0 0 0.5rem 0", fontSize: "0.85rem", color: "var(--text-secondary)", display: "flex", alignItems: "center", gap: "0.4rem", wordBreak: "break-all" }}>
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline></svg>
                            {contractName}
                          </h4>
                          <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                            {alerts.map((a) => (
                              <div key={a.id} style={{ background: "rgba(0,0,0,0.15)", padding: "0.75rem", borderRadius: "8px", border: "1px solid var(--border-color)", borderLeft: `3px solid var(--badge-${a.alert_type === 'overdue' ? 'critical' : 'medium'})` }}>
                                <div style={{ marginBottom: "0.5rem", fontSize: "0.9rem", lineHeight: 1.4 }}>
                                   {a.message}
                                </div>
                                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                                  <Badge variant={a.alert_type === 'overdue' ? 'critical' : 'medium'} style={{ padding: "0.15rem 0.4rem", fontSize: "0.65rem", backgroundColor: "transparent", border: "1px solid" }}>{a.alert_type}</Badge>
                                  <Button 
                                    variant="secondary" 
                                    onClick={() => emailDraft(a.id)} 
                                    style={{ padding: "0.25rem 0.5rem", fontSize: "0.75rem", display: "flex", alignItems: "center", gap: "0.25rem" }}
                                  >
                                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>
                                    Draft Email
                                  </Button>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </Card>

            </div>
          </div>
        </>
      )}
    </div>
  );
}
