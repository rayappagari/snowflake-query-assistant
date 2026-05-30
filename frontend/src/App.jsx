import { useState, useRef, useEffect } from 'react'

function SqlBlock({ sql }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="sql-block">
      <button className="sql-toggle" onClick={() => setOpen(!open)}>
        {open ? '▾' : '▸'} SQL
      </button>
      {open && <pre><code>{sql}</code></pre>}
    </div>
  )
}

function ResultsTable({ rows, rowCount }) {
  if (!rows || rows.length === 0) return null
  const cols = Object.keys(rows[0])
  return (
    <div className="results-block">
      <div className="results-header">
        {rowCount.toLocaleString()} row{rowCount !== 1 ? 's' : ''}
        {rowCount > rows.length ? ` — showing first ${rows.length}` : ''}
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>{cols.map(c => <th key={c}>{c}</th>)}</tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr key={i}>
                {cols.map(c => <td key={c}>{String(row[c] ?? '')}</td>)}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function UserMessage({ text }) {
  return <div className="bubble user">{text}</div>
}

function AssistantMessage({ data }) {
  const { answer, sql, rows, row_count, error } = data
  return (
    <div className="assistant-card">
      <p className="answer">{error ? `⚠ ${error}` : answer}</p>
      {sql && <SqlBlock sql={sql} />}
      {rows && rows.length > 0 && <ResultsTable rows={rows} rowCount={row_count} />}
    </div>
  )
}

export default function App() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  async function send() {
    const q = input.trim()
    if (!q || loading) return
    setInput('')
    setMessages(prev => [...prev, { role: 'user', text: q }])
    setLoading(true)
    try {
      const res = await fetch('http://localhost:8000/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: q }),
      })
      if (!res.ok) throw new Error(`Server error ${res.status}`)
      const data = await res.json()
      setMessages(prev => [...prev, { role: 'assistant', data }])
    } catch (err) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        data: { answer: `Could not reach the API: ${err.message}`, sql: '', rows: [], row_count: 0 },
      }])
    } finally {
      setLoading(false)
    }
  }

  function onKey(e) {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() }
  }

  return (
    <div className="app">
      <header className="app-header">
        <span className="logo">❄</span> Snowflake Query Assistant
      </header>

      <main className="chat">
        {messages.length === 0 && !loading && (
          <div className="empty">Ask anything about your Snowflake data.</div>
        )}
        {messages.map((msg, i) =>
          msg.role === 'user'
            ? <UserMessage key={i} text={msg.text} />
            : <AssistantMessage key={i} data={msg.data} />
        )}
        {loading && (
          <div className="assistant-card loading-card">
            <span className="dot" /><span className="dot" /><span className="dot" />
          </div>
        )}
        <div ref={bottomRef} />
      </main>

      <footer className="input-bar">
        <textarea
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={onKey}
          placeholder="Ask a question about your data… (Enter to send)"
          rows={1}
          disabled={loading}
        />
        <button onClick={send} disabled={loading || !input.trim()}>Send</button>
      </footer>
    </div>
  )
}
