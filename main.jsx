import React, { useEffect, useState } from 'react'
import { createRoot } from 'react-dom/client'
import './style.css'

const API = 'http://127.0.0.1:8000'

function App() {
  const [title, setTitle] = useState('')
  const [type, setType] = useState('Project Report')
  const [requirements, setRequirements] = useState('')
  const [extra, setExtra] = useState('')
  const [content, setContent] = useState('')
  const [history, setHistory] = useState([])
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')

  async function loadHistory() {
    try {
      const r = await fetch(`${API}/api/history`)
      if (r.ok) setHistory(await r.json())
    } catch { /* backend may not be running yet */ }
  }
  useEffect(() => { loadHistory() }, [])

  async function generate(e) {
    e.preventDefault()
    setBusy(true); setMessage('')
    try {
      const r = await fetch(`${API}/api/generate`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title, document_type: type, requirements, extra_context: extra })
      })
      const data = await r.json()
      if (!r.ok) throw new Error(data.detail || 'Generation failed')
      setContent(data.content)
      setMessage(data.retrieved_context ? 'Generated with retrieved reference context.' : 'Generated without matching local reference files.')
      loadHistory()
    } catch (err) { setMessage(err.message) }
    finally { setBusy(false) }
  }

  async function exportFile(format) {
    try {
      const r = await fetch(`${API}/api/export/${format}`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: title || 'DocuAI Document', content })
      })
      if (!r.ok) {
        const data = await r.json(); throw new Error(data.detail || 'Export failed')
      }
      const blob = await r.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url; a.download = `${(title || 'document').replace(/[^a-z0-9_-]/gi, '_')}.${format}`
      a.click(); URL.revokeObjectURL(url)
    } catch (err) { setMessage(err.message) }
  }

  return <div className="app">
    <aside className="sidebar">
      <div className="brand"><span className="brand-icon">D</span><div><b>DocuAI</b><small>Smart Document Studio</small></div></div>
      <div className="nav active">▦ &nbsp; Dashboard</div>
      <div className="nav">＋ &nbsp; Create Document</div>
      <div className="nav">▤ &nbsp; My Documents</div>
      <div className="nav">◷ &nbsp; Version History</div>
      <div className="side-bottom">AI DOCUMENT WORKSPACE<br/><small>Powered by local Llama 3.2</small></div>
    </aside>
    <main>
      <header><div><p className="eyebrow">USER DASHBOARD</p><h1>Welcome to DocuAI 👋</h1><p className="muted">Create structured documents with AI assistance.</p></div><span className="status">● Local workspace</span></header>
      <section className="hero"><div className="eyebrow light">RAG + OLLAMA + LLAMA 3.2</div><h2>Your local AI document workspace</h2><p>Enter your requirements, retrieve relevant context, generate a draft, edit it, and export it.</p></section>
      <div className="columns">
        <section className="panel">
          <h2>Create a document</h2>
          <form onSubmit={generate}>
            <label>Document type</label>
            <select value={type} onChange={e => setType(e.target.value)}><option>Project Report</option><option>Academic Report</option><option>Internship Report</option><option>Resume</option><option>Technical Documentation</option><option>Business Proposal</option></select>
            <label>Document title</label>
            <input required value={title} onChange={e => setTitle(e.target.value)} placeholder="e.g. Smart Parking Management System"/>
            <label>Requirements / topic</label>
            <textarea required rows="5" value={requirements} onChange={e => setRequirements(e.target.value)} placeholder="Describe what the document should contain..."/>
            <label>Additional context (optional)</label>
            <textarea rows="3" value={extra} onChange={e => setExtra(e.target.value)} placeholder="Add facts, notes, or instructions..."/>
            <button disabled={busy}>{busy ? 'Generating…' : '✦ Generate document'}</button>
          </form>
          {message && <p className="message">{message}</p>}
        </section>
        <section className="panel">
          <div className="result-head"><h2>Generated document</h2><span className="muted">Editable draft</span></div>
          <textarea className="editor" value={content} onChange={e => setContent(e.target.value)} placeholder="Your generated document will appear here. You can edit it before exporting."/>
          <div className="actions"><button className="secondary" disabled={!content} onClick={() => exportFile('pdf')}>Download PDF</button><button className="secondary" disabled={!content} onClick={() => exportFile('docx')}>Download DOCX</button></div>
        </section>
      </div>
      <section className="panel history"><h2>Recent document history</h2>{history.length ? history.slice(0,6).map(item => <div className="history-row" key={item.id}><div><b>{item.title}</b><small>{item.document_type} · {item.created_at}</small></div><button className="text-button" onClick={() => {setTitle(item.title);setType(item.document_type);setContent(item.content)}}>Open draft</button></div>) : <p className="muted">Your generated documents will appear here.</p>}</section>
      <footer>DocuAI · Full Stack Technologies Project</footer>
    </main>
  </div>
}

createRoot(document.getElementById('root')).render(<App />)
