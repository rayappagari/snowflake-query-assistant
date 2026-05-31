import { useState, useRef, useEffect } from 'react'
import hljs from 'highlight.js/lib/core'
import sql from 'highlight.js/lib/languages/sql'
import 'highlight.js/styles/atom-one-dark.css'

hljs.registerLanguage('sql', sql)

const THEMES = [
  { id: 'dark',     name: 'Dark',     bg: '#0b0f19', accent: '#29B5E8' },
  { id: 'midnight', name: 'Midnight', bg: '#0d0a1a', accent: '#a78bfa' },
  { id: 'ocean',    name: 'Ocean',    bg: '#071218', accent: '#2dd4bf' },
  { id: 'sunset',   name: 'Sunset',   bg: '#100804', accent: '#f59e0b' },
  { id: 'light',    name: 'Light',    bg: '#f8fafc', accent: '#1d4ed8' },
]

const EXAMPLES = [
  'Top 5 customers by revenue',
  'Total orders per region last quarter',
  'Which products have the highest return rate?',
  'Give me a list of all tables',
]

function SnowflakeLogo({ size = 22 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <line x1="12" y1="1"     x2="12" y2="23"    stroke="#29B5E8" strokeWidth="2.2" strokeLinecap="round"/>
      <line x1="1"  y1="12"    x2="23" y2="12"    stroke="#29B5E8" strokeWidth="2.2" strokeLinecap="round"/>
      <line x1="4.22" y1="4.22" x2="19.78" y2="19.78" stroke="#29B5E8" strokeWidth="2.2" strokeLinecap="round"/>
      <line x1="19.78" y1="4.22" x2="4.22" y2="19.78" stroke="#29B5E8" strokeWidth="2.2" strokeLinecap="round"/>
      {[
        [12,1],[12,23],[1,12],[23,12],
        [4.22,4.22],[19.78,19.78],[19.78,4.22],[4.22,19.78],
      ].map(([cx,cy], i) => <circle key={i} cx={cx} cy={cy} r="2" fill="#29B5E8"/>)}
    </svg>
  )
}

function Snowflakes() {
  const flakes = Array.from({ length: 14 }, (_, i) => ({
    id: i,
    left: `${(i * 7.3 + 2) % 100}%`,
    delay: `-${(i * 0.6) % 6}s`,
    duration: `${7 + (i % 5)}s`,
    fontSize: `${12 + (i % 4) * 5}px`,
    opacity: 0.06 + (i % 3) * 0.03,
  }))
  return (
    <div className="snowflakes" aria-hidden="true">
      {flakes.map(f => (
        <div key={f.id} className="snowflake" style={{
          left: f.left, animationDelay: f.delay,
          animationDuration: f.duration, fontSize: f.fontSize, opacity: f.opacity,
        }}>❄</div>
      ))}
    </div>
  )
}

function SqlBlock({ sql: sqlText }) {
  const [open, setOpen] = useState(false)
  const highlighted = hljs.highlight(sqlText, { language: 'sql' }).value
  return (
    <div className="sql-block">
      <button className="sql-toggle" onClick={() => setOpen(o => !o)}>
        {open ? '▾' : '▸'} SQL
      </button>
      {open && (
        <pre className="sql-pre">
          <code className="hljs language-sql" dangerouslySetInnerHTML={{ __html: highlighted }} />
        </pre>
      )}
    </div>
  )
}

function downloadCSV(rows) {
  const cols = Object.keys(rows[0])
  const header = cols.map(c => JSON.stringify(c)).join(',')
  const body = rows.map(row => cols.map(c => JSON.stringify(row[c] ?? '')).join(',')).join('\n')
  const blob = new Blob([header + '\n' + body], { type: 'text/csv' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url; a.download = 'results.csv'; a.click()
  URL.revokeObjectURL(url)
}

function ResultsTable({ rows, rowCount }) {
  if (!rows || rows.length === 0) return null
  const cols = Object.keys(rows[0])
  return (
    <div className="results-block">
      <div className="results-header">
        <span>
          {rowCount.toLocaleString()} row{rowCount !== 1 ? 's' : ''}
          {rowCount > rows.length ? ` — showing first ${rows.length}` : ''}
        </span>
        <button className="csv-btn" onClick={() => downloadCSV(rows)}>↓ CSV</button>
      </div>
      <div className="table-wrap">
        <table>
          <thead><tr>{cols.map(c => <th key={c}>{c}</th>)}</tr></thead>
          <tbody>
            {rows.map((row, i) => (
              <tr key={i}>{cols.map(c => <td key={c}>{String(row[c] ?? '')}</td>)}</tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function UserMessage({ text }) {
  return <div className="bubble user msg-in">{text}</div>
}

function AssistantMessage({ data }) {
  const { answer, sql, rows, row_count, error, cache_hit, pii_detected } = data
  return (
    <div className="assistant-card msg-in">
      <div className="answer-header">
        {cache_hit && <span className="badge badge--cache">⚡ cached</span>}
      </div>
      <p className="answer">{error ? `⚠ ${error}` : answer}</p>
      {pii_detected && pii_detected.length > 0 && (
        <div className="pii-warning">
          ⚠ Results may contain PII: {pii_detected.join(', ')}
        </div>
      )}
      {sql && <SqlBlock sql={sql} />}
      {rows && rows.length > 0 && <ResultsTable rows={rows} rowCount={row_count} />}
    </div>
  )
}

function AuditLog({ password }) {
  const [entries, setEntries] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch('/audit?limit=100', { headers: { 'X-App-Password': password } })
      .then(r => r.json())
      .then(setEntries)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [password])

  if (loading) return <p className="sidebar-empty">Loading…</p>
  if (!entries.length) return <p className="sidebar-empty">No queries logged yet</p>

  return (
    <div className="audit-list">
      {entries.map(e => (
        <div key={e.id} className={`audit-entry${e.success ? '' : ' audit-entry--fail'}`}>
          <div className="audit-row">
            <span className="audit-status">{e.success ? '✓' : '✗'}</span>
            <span className="audit-q">{e.question}</span>
          </div>
          <div className="audit-meta">
            <span>{new Date(e.ts).toLocaleTimeString()}</span>
            {e.latency_ms != null && <span>{e.latency_ms}ms</span>}
            {e.row_count != null && <span>{e.row_count} rows</span>}
            {e.error_message && <span className="audit-err">{e.error_message}</span>}
          </div>
        </div>
      ))}
    </div>
  )
}

function Sidebar({ history, onSelect, isOpen, onToggle, password }) {
  const [tab, setTab] = useState('history')

  return (
    <>
      <div className={`sidebar-overlay${isOpen ? ' sidebar-overlay--on' : ''}`} onClick={onToggle} />
      <aside className={`sidebar${isOpen ? ' sidebar--open' : ''}`}>
        <div className="sidebar-header">
          <div className="sidebar-tabs">
            <button
              className={`sidebar-tab${tab === 'history' ? ' sidebar-tab--active' : ''}`}
              onClick={() => setTab('history')}
            >History</button>
            <button
              className={`sidebar-tab${tab === 'audit' ? ' sidebar-tab--active' : ''}`}
              onClick={() => setTab('audit')}
            >Audit</button>
          </div>
          <button className="sidebar-close" onClick={onToggle}>✕</button>
        </div>
        <div className="sidebar-list">
          {tab === 'history' ? (
            history.length === 0
              ? <p className="sidebar-empty">No queries yet</p>
              : history.map((item, i) => (
                  <button key={i} className="sidebar-item" onClick={() => onSelect(item.question)}>
                    <span className="sidebar-q">{item.question}</span>
                    <span className="sidebar-time">{item.time}</span>
                  </button>
                ))
          ) : (
            <AuditLog password={password} />
          )}
        </div>
      </aside>
    </>
  )
}

function Toast({ message }) {
  return <div className="toast">{message}</div>
}

function ThemePanel({ current, onChange, onClose }) {
  return (
    <div className="theme-panel">
      <div className="theme-panel-header">
        <span>Theme</span>
        <button className="theme-panel-close" onClick={onClose}>✕</button>
      </div>
      <div className="theme-grid">
        {THEMES.map(t => (
          <button
            key={t.id}
            className={`theme-swatch${current === t.id ? ' theme-swatch--active' : ''}`}
            onClick={() => onChange(t.id)}
            title={t.name}
          >
            <div className="swatch-preview" style={{ background: t.bg }}>
              <div className="swatch-accent" style={{ background: t.accent }} />
            </div>
            <span className="swatch-label">{t.name}</span>
          </button>
        ))}
      </div>
    </div>
  )
}

function PasswordGate({ onUnlock }) {
  const [value, setValue] = useState('')
  const [error, setError] = useState(false)
  const [checking, setChecking] = useState(false)
  const inputRef = useRef(null)
  useEffect(() => { inputRef.current?.focus() }, [])

  async function submit(e) {
    e.preventDefault()
    setChecking(true)
    try {
      const res = await fetch('/verify', { headers: { 'X-App-Password': value } })
      if (res.ok) { onUnlock(value) }
      else { setError(true); setValue(''); inputRef.current?.focus() }
    } finally { setChecking(false) }
  }

  return (
    <div className="gate-wrap">
      <Snowflakes />
      <form className="gate-card" onSubmit={submit}>
        <SnowflakeLogo size={38} />
        <h1 className="gate-title">Snowflake Query Assistant</h1>
        <p className="gate-subtitle">Enter the password to continue</p>
        <input
          ref={inputRef}
          type="password"
          className={`gate-input${error ? ' gate-input--error' : ''}`}
          placeholder="Password"
          value={value}
          onChange={e => { setValue(e.target.value); setError(false) }}
        />
        {error && <p className="gate-error">Incorrect password — try again</p>}
        <button className="gate-btn" type="submit" disabled={!value || checking}>
          {checking ? 'Checking…' : 'Continue →'}
        </button>
      </form>
    </div>
  )
}

export default function App() {
  const [password, setPassword] = useState(null)
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [history, setHistory] = useState([])          // sidebar display history
  const [convHistory, setConvHistory] = useState([])  // API conversation memory
  const [toast, setToast] = useState(null)
  const [theme, setTheme] = useState(() => localStorage.getItem('theme') || 'dark')
  const bottomRef = useRef(null)
  const textareaRef = useRef(null)
  const toastTimerRef = useRef(null)

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    localStorage.setItem('theme', theme)
  }, [theme])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  useEffect(() => {
    if (!toast) return
    const t = setTimeout(() => setToast(null), 4000)
    return () => clearTimeout(t)
  }, [toast])

  if (!password) return <PasswordGate onUnlock={setPassword} />

  function resizeTextarea() {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 180) + 'px'
  }

  async function send(question) {
    const q = (question ?? input).trim()
    if (!q || loading) return
    setInput('')
    if (textareaRef.current) textareaRef.current.style.height = 'auto'
    setMessages(prev => [...prev, { role: 'user', text: q }])
    setLoading(true)
    clearTimeout(toastTimerRef.current)
    toastTimerRef.current = setTimeout(() => setToast('Still working on it…'), 6000)

    try {
      const res = await fetch('/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-App-Password': password },
        body: JSON.stringify({ question: q, history: convHistory }),
      })
      clearTimeout(toastTimerRef.current); setToast(null)
      if (res.status === 401) { setPassword(null); return }
      if (!res.ok) throw new Error(`Server error ${res.status}`)
      const data = await res.json()
      setMessages(prev => [...prev, { role: 'assistant', data }])
      setHistory(prev => [
        { question: q, time: new Date().toLocaleTimeString() },
        ...prev,
      ].slice(0, 50))
      if (!data.error) {
        setConvHistory(prev => [
          ...prev,
          { question: q, sql: data.sql, answer: data.answer },
        ].slice(-10))
      }
    } catch (err) {
      clearTimeout(toastTimerRef.current); setToast(null)
      setMessages(prev => [...prev, {
        role: 'assistant',
        data: { answer: `Could not reach the API: ${err.message}`, sql: '', rows: [], row_count: 0 },
      }])
    } finally { setLoading(false) }
  }

  function onKey(e) {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() }
  }

  function fillExample(q) {
    setInput(q)
    textareaRef.current?.focus()
  }

  return (
    <div className="app">
      <header className="app-header">
        <button className="menu-btn" onClick={() => setSidebarOpen(o => !o)} aria-label="Toggle history">
          <span className="menu-icon">☰</span>
        </button>
        <div className="header-brand">
          <SnowflakeLogo size={20} />
          <span>Snowflake Query Assistant</span>
        </div>
        <div className="header-right">
          {convHistory.length > 0 && (
            <button
              className="clear-btn"
              onClick={() => { setConvHistory([]); setMessages([]); setHistory([]) }}
              title="Clear conversation memory"
            >
              New chat
            </button>
          )}
          <button className="settings-btn" onClick={() => setSettingsOpen(o => !o)} aria-label="Settings">
            ⚙
          </button>
          {settingsOpen && (
            <ThemePanel
              current={theme}
              onChange={t => { setTheme(t); setSettingsOpen(false) }}
              onClose={() => setSettingsOpen(false)}
            />
          )}
        </div>
      </header>

      <div className="app-body">
        <Sidebar
          history={history}
          onSelect={q => { fillExample(q); setSidebarOpen(false) }}
          isOpen={sidebarOpen}
          onToggle={() => setSidebarOpen(o => !o)}
          password={password}
        />

        <div className="chat-wrap">
          <main className="chat">
            {messages.length === 0 && !loading && (
              <div className="empty">
                <SnowflakeLogo size={44} />
                <p className="empty-title">Ask anything about your Snowflake data</p>
                <div className="examples">
                  {EXAMPLES.map((ex, i) => (
                    <button key={i} className="example-chip" onClick={() => fillExample(ex)}>
                      {ex}
                    </button>
                  ))}
                </div>
              </div>
            )}
            {messages.map((msg, i) =>
              msg.role === 'user'
                ? <UserMessage key={i} text={msg.text} />
                : <AssistantMessage key={i} data={msg.data} />
            )}
            {loading && (
              <div className="assistant-card loading-card msg-in">
                <span className="dot" /><span className="dot" /><span className="dot" />
              </div>
            )}
            <div ref={bottomRef} />
          </main>

          <footer className="input-bar">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={e => { setInput(e.target.value); resizeTextarea() }}
              onKeyDown={onKey}
              placeholder="Ask a question about your data… (Enter to send)"
              rows={1}
              disabled={loading}
            />
            <button onClick={() => send()} disabled={loading || !input.trim()}>Send</button>
          </footer>
        </div>
      </div>

      {toast && <Toast message={toast} />}
    </div>
  )
}
